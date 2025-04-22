"""
Canvas Modules Sync

This module provides functionality for synchronizing module and module item data
between the Canvas API and the local database asynchronously.
"""

import asyncio
import logging
import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING, Any

from canvas_mcp.models import DBModule, DBModuleItem
from canvas_mcp.utils.db_manager import run_db_persist_in_thread

if TYPE_CHECKING:
    from canvas_mcp.sync.service import SyncService

# Configure logging
logger = logging.getLogger(__name__)


async def sync_modules(
    sync_service: "SyncService", course_ids: list[int] | None = None
) -> int:
    """
    Synchronize module and module item data from Canvas to the local database asynchronously.

    Args:
        sync_service: The sync service instance.
        course_ids: List of local course IDs to sync modules for.

    Returns:
        Number of modules synced/updated.
    """
    if not sync_service.api_adapter.is_available():
        logger.error("Canvas API adapter is not available for module sync")
        return 0
    if not course_ids:
        logger.warning("No course IDs provided for module sync.")
        return 0

    # Get course mapping (canvas_id -> local_id)
    conn_map, cursor_map = sync_service.db_manager.connect()
    try:
        placeholders = ", ".join("?" * len(course_ids))
        cursor_map.execute(
            f"SELECT id, canvas_course_id FROM courses WHERE id IN ({placeholders})",
            course_ids,
        )
        courses_to_sync = {
            row["canvas_course_id"]: row["id"] for row in cursor_map.fetchall()
        }
    except Exception as e:
        logger.error(f"Failed to fetch course mapping for modules: {e}")
        return 0
    finally:
        conn_map.close()

    if not courses_to_sync:
        logger.warning("No matching courses found in DB for module sync.")
        return 0

    # --- Parallel Fetch Stage (Modules) ---
    module_tasks = []
    course_context = []  # Store (local_id, canvas_id) for context

    logger.info(
        f"Creating tasks to fetch modules for {len(courses_to_sync)} courses..."
    )
    for canvas_course_id, local_course_id in courses_to_sync.items():
        task = asyncio.create_task(
            _fetch_modules_for_course(sync_service, canvas_course_id, local_course_id)
        )
        module_tasks.append(task)
        course_context.append((local_course_id, canvas_course_id))

    logger.info(f"Gathering module data for {len(module_tasks)} tasks...")
    module_results_or_exceptions = await asyncio.gather(
        *module_tasks, return_exceptions=True
    )
    logger.info("Finished gathering module data.")

    # --- Process & Validate Modules, Prepare Item Fetch ---
    all_valid_modules: list[DBModule] = []
    module_item_fetch_tasks = []
    raw_module_map: dict[
        int, Any
    ] = {}  # canvas_module_id -> raw_module object (for item fetching)
    module_context_map: dict[int, int] = {}  # canvas_module_id -> local_course_id

    total_raw_modules = 0
    for i, result in enumerate(module_results_or_exceptions):
        local_course_id, canvas_course_id = course_context[i]
        if isinstance(result, Exception):
            logger.error(
                f"Failed fetching modules for course {local_course_id} (Canvas ID: {canvas_course_id}): {result}"
            )
            continue
        if result is None:
            logger.warning(f"No module data returned for course {local_course_id}")
            continue

        raw_modules = result
        total_raw_modules += len(raw_modules)

        for raw_module in raw_modules:
            try:
                canvas_module_id = getattr(raw_module, "id", None)
                if not canvas_module_id:
                    continue

                module_data = {
                    "id": canvas_module_id,  # Alias for canvas_module_id
                    "course_id": local_course_id,
                    "name": getattr(raw_module, "name", "Untitled Module"),
                    "description": getattr(raw_module, "description", None),
                    "unlock_at": getattr(
                        raw_module, "unlock_at", None
                    ),  # Alias for unlock_date
                    "position": getattr(raw_module, "position", None),
                    "require_sequential_progress": getattr(
                        raw_module, "require_sequential_progress", False
                    ),
                }
                db_module = DBModule.model_validate(module_data)
                all_valid_modules.append(db_module)

                # Prepare task to fetch items for this module
                raw_module_map[canvas_module_id] = raw_module
                module_context_map[canvas_module_id] = local_course_id
                item_task = asyncio.create_task(
                    _fetch_module_items(
                        sync_service, raw_module
                    )  # Pass raw module object
                )
                module_item_fetch_tasks.append(item_task)

            except Exception as e:
                logger.error(
                    f"Validation error for module {getattr(raw_module, 'id', 'N/A')} in course {local_course_id}: {e}",
                    exc_info=True,
                )

    logger.info(
        f"Processed {total_raw_modules} raw modules, {len(all_valid_modules)} valid modules found."
    )

    # --- Parallel Fetch Stage (Module Items) ---
    logger.info(
        f"Gathering module item data for {len(module_item_fetch_tasks)} modules..."
    )
    item_results_or_exceptions = await asyncio.gather(
        *module_item_fetch_tasks, return_exceptions=True
    )
    logger.info("Finished gathering module item data.")

    # --- Process & Validate Module Items ---
    all_valid_module_items: list[DBModuleItem] = []
    total_raw_items = 0
    # We need to map item results back to their modules
    # The order of item_results matches module_item_fetch_tasks, which were created iterating valid modules
    valid_module_canvas_ids = [m.canvas_module_id for m in all_valid_modules]

    for i, result in enumerate(item_results_or_exceptions):
        # Find the corresponding module canvas ID based on the task order
        if i < len(valid_module_canvas_ids):
            canvas_module_id = valid_module_canvas_ids[i]
            local_course_id = module_context_map.get(
                canvas_module_id
            )  # Get course context
        else:
            logger.error(f"Index mismatch processing module item results ({i})")
            continue  # Should not happen

        if isinstance(result, Exception):
            logger.error(
                f"Failed fetching items for module {canvas_module_id}: {result}"
            )
            continue
        if result is None:
            logger.debug(f"No items returned for module {canvas_module_id}")
            continue

        raw_items = result
        total_raw_items += len(raw_items)

        for raw_item in raw_items:
            try:
                canvas_item_id = getattr(raw_item, "id", None)
                if not canvas_item_id:
                    continue

                # Prepare data for validation
                item_data = {
                    "id": canvas_item_id,  # Alias for canvas_item_id
                    # We need the *local* module_id, which we don't have yet.
                    # We'll add it during persistence. Store canvas_module_id temporarily.
                    "canvas_module_id": canvas_module_id,  # Temporary field
                    "title": getattr(raw_item, "title", "Untitled Item"),
                    "type": getattr(raw_item, "type", None),  # Alias for item_type
                    "position": getattr(raw_item, "position", None),
                    "external_url": getattr(
                        raw_item, "external_url", None
                    ),  # Alias for url
                    "page_url": getattr(raw_item, "page_url", None),
                    # Content details might be large, consider storing selectively or hashing
                    "content_details": str(vars(raw_item))
                    if hasattr(raw_item, "__dict__")
                    else None,
                }

                # Validate using Pydantic model (excluding module_id for now)
                # Need to adjust DBModuleItem model or validation temporarily
                # Option: Add canvas_module_id to DBModuleItem model temporarily
                # Option: Validate later during persistence
                # Let's assume DBModuleItem is adjusted to accept canvas_module_id
                db_item = DBModuleItem.model_validate(item_data)
                all_valid_module_items.append(db_item)
            except Exception as e:
                logger.error(
                    f"Validation error for item {getattr(raw_item, 'id', 'N/A')} in module {canvas_module_id}: {e}",
                    exc_info=True,
                )

    logger.info(
        f"Processed {total_raw_items} raw module items, {len(all_valid_module_items)} valid items found."
    )

    # --- Persist Stage ---
    # We need to pass both modules and items to the persistence function
    data_to_persist = (all_valid_modules, all_valid_module_items)

    persisted_module_count = await run_db_persist_in_thread(
        sync_service.db_manager,
        _persist_modules_and_items,
        sync_service,
        data_to_persist,  # Pass tuple of lists
    )

    logger.info(
        f"Finished module sync. Persisted/updated {persisted_module_count} modules and their items."
    )
    return persisted_module_count


async def _fetch_modules_for_course(
    sync_service: "SyncService", canvas_course_id: int, local_course_id: int
) -> list[Any] | None:
    """Helper async function to wrap the threaded API call for modules."""
    async with sync_service.api_semaphore:
        logger.debug(
            f"Semaphore acquired for fetching modules: course {local_course_id}"
        )
        try:
            raw_modules = await asyncio.to_thread(
                sync_service.api_adapter.get_modules_raw_by_id,
                canvas_course_id,
                per_page=100,
            )
            logger.debug(
                f"Fetched {len(raw_modules)} modules for course {local_course_id}"
            )
            return raw_modules
        except Exception as e:
            logger.error(
                f"Error in thread fetching modules for course {local_course_id}: {e}",
                exc_info=True,
            )
            return None


async def _fetch_module_items(
    sync_service: "SyncService", raw_module: Any
) -> list[Any] | None:
    """Helper async function to wrap the threaded API call for module items."""
    module_id = getattr(raw_module, "id", "N/A")
    async with sync_service.api_semaphore:
        logger.debug(f"Semaphore acquired for fetching items: module {module_id}")
        try:
            # Use the adapter method that takes the module object
            raw_items = await asyncio.to_thread(
                sync_service.api_adapter.get_module_items_raw,
                raw_module,  # Pass the module object
                per_page=100,
            )
            logger.debug(f"Fetched {len(raw_items)} items for module {module_id}")
            return raw_items
        except Exception as e:
            logger.error(
                f"Error in thread fetching items for module {module_id}: {e}",
                exc_info=True,
            )
            return None


def _persist_modules_and_items(
    conn: sqlite3.Connection,
    cursor: sqlite3.Cursor,
    sync_service: "SyncService",
    data_to_persist: tuple[list[DBModule], list[DBModuleItem]],
) -> int:
    """
    Persist modules and module items in a single transaction using batch operations.

    Args:
        conn: Database connection.
        cursor: Database cursor.
        sync_service: The sync service instance.
        data_to_persist: Tuple containing list of valid modules and list of valid module items.

    Returns:
        Number of modules synced/updated.
    """
    valid_modules, valid_module_items = data_to_persist
    if not valid_modules and not valid_module_items:  # Check both
        return 0

    processed_module_count = 0
    now_iso = datetime.now().isoformat()
    module_canvas_to_local_id: dict[
        int, int
    ] = {}  # canvas_module_id -> local_module_id

    # --- Module Persistence ---
    if valid_modules:
        # 1. Fetch existing module IDs
        existing_modules_map: dict[
            tuple[int, int], int
        ] = {}  # (canvas_module_id, course_id) -> local_module_id
        canvas_ids_in_batch = {m.canvas_module_id for m in valid_modules}
        course_ids_in_batch = {m.course_id for m in valid_modules}
        try:
            if canvas_ids_in_batch and course_ids_in_batch:
                canvas_phs = ",".join("?" * len(canvas_ids_in_batch))
                course_phs = ",".join("?" * len(course_ids_in_batch))
                sql = f"SELECT id, canvas_module_id, course_id FROM modules WHERE canvas_module_id IN ({canvas_phs}) AND course_id IN ({course_phs})"
                params = list(canvas_ids_in_batch) + list(course_ids_in_batch)
                cursor.execute(sql, params)
                for row in cursor.fetchall():
                    existing_modules_map[
                        (row["canvas_module_id"], row["course_id"])
                    ] = row["id"]
        except sqlite3.Error as e:
            logger.error(f"Failed to query existing modules: {e}")
            raise

        # 2. Prepare module data
        modules_to_insert_data = []
        modules_to_update_data = []
        for db_module in valid_modules:
            module_dict = db_module.model_dump(exclude={"created_at", "updated_at"})
            module_dict["updated_at"] = now_iso
            module_dict["unlock_date"] = module_dict.pop(
                "unlock_at", db_module.unlock_date
            )  # Handle alias

            key = (db_module.canvas_module_id, db_module.course_id)
            if key in existing_modules_map:
                local_id = existing_modules_map[key]
                module_dict["local_id"] = local_id
                modules_to_update_data.append(module_dict)
                module_canvas_to_local_id[db_module.canvas_module_id] = local_id
            else:
                insert_tuple = (
                    module_dict.get("course_id"),
                    module_dict.get("canvas_module_id"),
                    module_dict.get("name"),
                    module_dict.get("description"),
                    module_dict.get("position"),
                    module_dict.get("unlock_date"),
                    module_dict.get("require_sequential_progress"),
                    module_dict.get("updated_at"),
                )
                modules_to_insert_data.append(insert_tuple)

        # 3. Batch insert modules
        if modules_to_insert_data:
            cols = "course_id, canvas_module_id, name, description, position, unlock_date, require_sequential_progress, updated_at"
            phs = ", ".join(["?"] * len(modules_to_insert_data[0]))
            sql = f"INSERT INTO modules ({cols}) VALUES ({phs})"
            try:
                cursor.executemany(sql, modules_to_insert_data)

                # Re‑query to obtain reliable primary keys (rowcount/lastrowid are
                # undefined after executemany on SQLite).
                inserted_canvas_ids = [row[1] for row in modules_to_insert_data]
                phs = ",".join("?" * len(inserted_canvas_ids))
                cursor.execute(
                    f"SELECT id, canvas_module_id FROM modules "
                    f"WHERE canvas_module_id IN ({phs})",
                    inserted_canvas_ids,
                )
                rows = cursor.fetchall()

                inserted_count = len(rows)
                processed_module_count += inserted_count
                logger.debug(f"Batch inserted {inserted_count} modules.")

                # Build Canvas‑ID → local‑ID map
                for row in rows:
                    module_canvas_to_local_id[row["canvas_module_id"]] = row["id"]
            except sqlite3.Error as e:
                logger.error(f"Batch module insert failed: {e}")
                raise

        # 4. Looped update modules
        update_count = 0
        if modules_to_update_data:
            logger.debug(
                f"Updating {len(modules_to_update_data)} modules individually..."
            )
            for item_dict in modules_to_update_data:
                local_id = item_dict.pop("local_id")
                canvas_id = item_dict.get("canvas_module_id")
                course_id = item_dict.get("course_id")
                try:
                    # add the mapping so items link correctly
                    module_canvas_to_local_id[canvas_id] = local_id

                    set_clause = ", ".join(
                        [
                            f"{k} = ?"
                            for k in item_dict
                            if k not in ["canvas_module_id", "course_id"]
                        ]
                    )
                    values = [
                        v
                        for k, v in item_dict.items()
                        if k not in ["canvas_module_id", "course_id"]
                    ]
                    values.append(local_id)
                    sql = f"UPDATE modules SET {set_clause} WHERE id = ?"
                    cursor.execute(sql, values)
                    update_count += cursor.rowcount
                except sqlite3.Error as e:
                    logger.error(
                        f"Failed to update module {canvas_id} (local ID {local_id}) in course {course_id}: {e}"
                    )
            processed_module_count += update_count
            logger.debug(f"Updated {update_count} modules.")

    # --- Module Item Persistence (Simplified: INSERT OR REPLACE) ---
    if valid_module_items:
        items_to_persist = []
        for db_item in valid_module_items:
            if db_item.canvas_module_id not in module_canvas_to_local_id:
                logger.error(
                    "Invariant violated: missing module‑id mapping for item %s in module %s",
                    db_item.canvas_item_id,
                    db_item.canvas_module_id,
                )
                continue  # or raise CustomSyncError if you prefer

            # Get the local_module_id using the map populated during module persistence
            local_module_id = module_canvas_to_local_id.get(db_item.canvas_module_id)
            if not local_module_id:
                logger.warning(
                    f"Skipping item {db_item.canvas_item_id}: Cannot find local module ID for canvas module {db_item.canvas_module_id}"
                )
                continue

            item_dict = db_item.model_dump(
                exclude={"created_at", "updated_at", "canvas_module_id"}
            )  # Exclude temp field
            item_dict["updated_at"] = now_iso
            item_dict["module_id"] = local_module_id  # Set the correct foreign key
            item_dict["item_type"] = item_dict.pop(
                "type", db_item.item_type
            )  # Handle alias
            item_dict["url"] = item_dict.pop(
                "external_url", db_item.url
            )  # Handle alias

            # Prepare tuple for INSERT OR REPLACE
            persist_tuple = (
                item_dict.get("module_id"),
                item_dict.get("canvas_item_id"),
                item_dict.get("title"),
                item_dict.get("position"),
                None,  # content_type - not in model?
                item_dict.get("item_type"),
                None,  # content_id - not in model?
                item_dict.get("url"),
                item_dict.get("page_url"),
                item_dict.get("content_details"),
                item_dict.get("updated_at"),
            )
            items_to_persist.append(persist_tuple)

        if items_to_persist:
            logger.debug(
                f"Persisting {len(items_to_persist)} module items using INSERT OR REPLACE..."
            )
            # Using canvas_item_id and module_id as the key for replacement
            sql = """
                INSERT OR REPLACE INTO module_items
                (module_id, canvas_item_id, title, position, content_type, item_type, content_id, url, page_url, content_details, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            try:
                cursor.executemany(sql, items_to_persist)
                logger.debug(f"Persisted {cursor.rowcount} module items.")
            except sqlite3.Error as e:
                logger.error(f"Module item persistence failed: {e}")
                raise  # Rollback

    return processed_module_count  # Return count of modules processed
