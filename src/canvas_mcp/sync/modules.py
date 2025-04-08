"""
Canvas Modules Sync

This module provides functionality for synchronizing module data between
the Canvas API and the local database.
"""

import logging
from datetime import datetime

from canvas_mcp.models import DBModule, DBModuleItem
from canvas_mcp.utils.db_manager import DatabaseManager

# Configure logging
logger = logging.getLogger(__name__)


def sync_modules(self, course_ids: list[int] | None = None) -> int:
    """
    Synchronize module data from Canvas to the local database.

    Args:
        course_ids: Optional list of local course IDs to sync

    Returns:
        Number of modules synced
    """
    if not self.api_adapter.is_available():
        logger.error("Canvas API adapter is not available")
        return 0

    # Get courses to sync
    courses_to_sync = self._get_courses_to_sync(course_ids)

    if not courses_to_sync:
        logger.warning("No courses found to sync modules")
        return 0

    # Process each course
    module_count = 0

    for course in courses_to_sync:
        local_course_id = course["id"]
        canvas_course_id = course["canvas_course_id"]

        logger.info(
            f"Syncing modules for course {canvas_course_id} (local ID: {local_course_id})"
        )

        # Fetch Stage
        canvas_course = self.api_adapter.get_course_raw(canvas_course_id)
        if not canvas_course:
            logger.error(f"Failed to get course {canvas_course_id} from Canvas API")
            continue

        raw_modules = self.api_adapter.get_modules_raw(canvas_course)
        if not raw_modules:
            logger.info(f"No modules found for course {canvas_course_id}")
            continue

        # Prepare/Validate Stage
        valid_modules = []
        module_items_map = {}

        for raw_module in raw_modules:
            try:
                # Prepare data for validation
                module_data = {
                    "id": raw_module.id,
                    "course_id": local_course_id,
                    "name": getattr(raw_module, "name", ""),
                    "description": getattr(raw_module, "description", None),
                    "unlock_at": getattr(raw_module, "unlock_at", None),
                    "position": getattr(raw_module, "position", None),
                    "require_sequential_progress": getattr(
                        raw_module, "require_sequential_progress", False
                    ),
                }

                # Validate using Pydantic model
                db_module = DBModule.model_validate(module_data)
                valid_modules.append(db_module)

                # Get module items
                raw_items = self.api_adapter.get_module_items_raw(raw_module)
                if raw_items:
                    module_items_map[db_module.canvas_module_id] = raw_items
            except Exception as e:
                logger.error(
                    f"Error validating module {getattr(raw_module, 'id', 'unknown')}: {e}"
                )

        # Persist modules and module items using the with_connection decorator
        module_count += self._persist_modules_and_items(
            local_course_id, valid_modules, module_items_map
        )

        logger.info(f"Successfully synced modules for course {canvas_course_id}")

    return module_count


def _persist_modules_and_items(
    self,
    conn,
    cursor,
    local_course_id: int,
    valid_modules: list[DBModule],
    module_items_map: dict[int, list],
) -> int:
    """
    Persist modules and module items in a single transaction.

    Args:
        conn: Database connection
        cursor: Database cursor
        local_course_id: Local course ID
        valid_modules: List of validated module models
        module_items_map: Map of canvas_module_id to raw module items

    Returns:
        Number of modules synced
    """
    module_count = 0
    module_id_map = {}

    # Persist modules
    for db_module in valid_modules:
        try:
            # Convert Pydantic model to dict
            module_dict = db_module.model_dump(exclude={"created_at", "updated_at"})
            module_dict["updated_at"] = datetime.now().isoformat()

            # Check if module exists
            cursor.execute(
                "SELECT id FROM modules WHERE course_id = ? AND canvas_module_id = ?",
                (local_course_id, db_module.canvas_module_id),
            )
            existing_module = cursor.fetchone()

            if existing_module:
                # Update existing module
                placeholders = ", ".join([f"{key} = ?" for key in module_dict.keys()])
                query = f"UPDATE modules SET {placeholders} WHERE course_id = ? AND canvas_module_id = ?"
                cursor.execute(
                    query,
                    list(module_dict.values())
                    + [local_course_id, db_module.canvas_module_id],
                )
                local_module_id = existing_module["id"]
            else:
                # Insert new module
                columns = ", ".join(module_dict.keys())
                placeholders = ", ".join(["?" for _ in module_dict.keys()])
                query = f"INSERT INTO modules ({columns}) VALUES ({placeholders})"
                cursor.execute(query, list(module_dict.values()))
                local_module_id = cursor.lastrowid

            module_id_map[db_module.canvas_module_id] = local_module_id
            module_count += 1
        except Exception as e:
            logger.error(f"Error persisting module {db_module.canvas_module_id}: {e}")
            # The decorator will handle rollback

    # Persist module items
    for canvas_module_id, raw_items in module_items_map.items():
        local_module_id = module_id_map.get(canvas_module_id)
        if not local_module_id:
            continue

        for raw_item in raw_items:
            try:
                # Prepare data for validation
                item_data = {
                    "id": raw_item.id,
                    "module_id": local_module_id,
                    "title": getattr(raw_item, "title", None),
                    "type": getattr(raw_item, "type", None),
                    "position": getattr(raw_item, "position", None),
                    "external_url": getattr(raw_item, "external_url", None),
                    "page_url": getattr(raw_item, "page_url", None),
                }

                # Convert content_details to string
                content_details = (
                    str(raw_item) if hasattr(raw_item, "__dict__") else None
                )

                # Validate using Pydantic model
                db_item = DBModuleItem.model_validate(item_data)

                # Convert Pydantic model to dict
                item_dict = db_item.model_dump(exclude={"created_at", "updated_at"})
                item_dict["content_details"] = content_details
                item_dict["updated_at"] = datetime.now().isoformat()

                # Check if module item exists
                cursor.execute(
                    "SELECT id FROM module_items WHERE module_id = ? AND canvas_item_id = ?",
                    (local_module_id, db_item.canvas_item_id),
                )
                existing_item = cursor.fetchone()

                if existing_item:
                    # Update existing module item
                    placeholders = ", ".join([f"{key} = ?" for key in item_dict.keys()])
                    query = f"UPDATE module_items SET {placeholders} WHERE module_id = ? AND canvas_item_id = ?"
                    cursor.execute(
                        query,
                        list(item_dict.values())
                        + [local_module_id, db_item.canvas_item_id],
                    )
                else:
                    # Insert new module item
                    columns = ", ".join(item_dict.keys())
                    placeholders = ", ".join(["?" for _ in item_dict.keys()])
                    query = (
                        f"INSERT INTO module_items ({columns}) VALUES ({placeholders})"
                    )
                    cursor.execute(query, list(item_dict.values()))
            except Exception as e:
                logger.error(
                    f"Error persisting module item {getattr(raw_item, 'id', 'unknown')}: {e}"
                )
                # The decorator will handle rollback

    return module_count
