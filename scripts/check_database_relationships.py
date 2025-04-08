#!/usr/bin/env python3
"""
Database relationship integrity checker for Canvas-MCP.

This script performs comprehensive checks on the database to ensure
that all relationships between tables are maintained correctly.

Usage:
    python scripts/check_database_relationships.py [--database PATH] [--fix]

Options:
    --database      Path to the database file (default: data/canvas_mcp.db)
    --fix           Attempt to fix identified issues
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from src.canvas_mcp.utils.db_manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("db_checker")


def check_foreign_keys(db_path, fix=False):
    """Check if foreign key constraints are enabled and enforced."""
    logger.info("Checking foreign key constraints...")
    
    try:
        # Connect directly to check pragma settings
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if foreign keys are enabled
        cursor.execute("PRAGMA foreign_keys")
        foreign_keys_enabled = cursor.fetchone()[0]
        
        if not foreign_keys_enabled:
            logger.warning("Foreign key constraints are not enabled")
            if fix:
                cursor.execute("PRAGMA foreign_keys = ON")
                logger.info("Enabled foreign key constraints")
        else:
            logger.info("Foreign key constraints are enabled")
        
        # Check for foreign key violations
        cursor.execute("PRAGMA foreign_key_check")
        violations = cursor.fetchall()
        
        if violations:
            logger.error(f"Found {len(violations)} foreign key constraint violations")
            for violation in violations:
                logger.error(f"  Table: {violation['table']}, Row ID: {violation['rowid']}")
            
            if fix:
                logger.info("Attempting to fix foreign key violations...")
                # This is a destructive operation, so we'll ask for confirmation
                confirm = input("This will delete records that violate foreign key constraints. Continue? (y/n): ")
                if confirm.lower() == 'y':
                    for violation in violations:
                        table = violation['table']
                        rowid = violation['rowid']
                        cursor.execute(f"DELETE FROM {table} WHERE rowid = ?", (rowid,))
                    conn.commit()
                    logger.info("Fixed foreign key violations by deleting violating records")
                else:
                    logger.info("Skipped fixing foreign key violations")
        else:
            logger.info("No foreign key constraint violations found")
        
        conn.close()
        return not violations
    except Exception as e:
        logger.error(f"Error checking foreign keys: {e}")
        return False


def check_orphaned_records(db_manager, fix=False):
    """Check for orphaned records in related tables."""
    logger.info("Checking for orphaned records...")
    
    try:
        conn, cursor = db_manager.connect()
        
        # Define relationships to check
        relationships = [
            {
                "table": "assignments",
                "parent_table": "courses",
                "foreign_key": "course_id",
                "parent_key": "id",
            },
            {
                "table": "modules",
                "parent_table": "courses",
                "foreign_key": "course_id",
                "parent_key": "id",
            },
            {
                "table": "module_items",
                "parent_table": "modules",
                "foreign_key": "module_id",
                "parent_key": "id",
            },
            {
                "table": "announcements",
                "parent_table": "courses",
                "foreign_key": "course_id",
                "parent_key": "id",
            },
            {
                "table": "syllabi",
                "parent_table": "courses",
                "foreign_key": "course_id",
                "parent_key": "id",
            },
        ]
        
        all_clean = True
        
        for rel in relationships:
            query = f"""
                SELECT COUNT(*) as count FROM {rel['table']} t
                LEFT JOIN {rel['parent_table']} p ON t.{rel['foreign_key']} = p.{rel['parent_key']}
                WHERE p.{rel['parent_key']} IS NULL
            """
            cursor.execute(query)
            orphaned_count = cursor.fetchone()["count"]
            
            if orphaned_count > 0:
                all_clean = False
                logger.error(f"Found {orphaned_count} orphaned records in {rel['table']}")
                
                if fix:
                    # Get the orphaned records
                    cursor.execute(f"""
                        SELECT t.* FROM {rel['table']} t
                        LEFT JOIN {rel['parent_table']} p ON t.{rel['foreign_key']} = p.{rel['parent_key']}
                        WHERE p.{rel['parent_key']} IS NULL
                    """)
                    orphaned_records = cursor.fetchall()
                    
                    # Delete the orphaned records
                    cursor.execute(f"""
                        DELETE FROM {rel['table']}
                        WHERE {rel['foreign_key']} IN (
                            SELECT t.{rel['foreign_key']} FROM {rel['table']} t
                            LEFT JOIN {rel['parent_table']} p ON t.{rel['foreign_key']} = p.{rel['parent_key']}
                            WHERE p.{rel['parent_key']} IS NULL
                        )
                    """)
                    conn.commit()
                    logger.info(f"Deleted {orphaned_count} orphaned records from {rel['table']}")
            else:
                logger.info(f"No orphaned records found in {rel['table']}")
        
        conn.close()
        return all_clean
    except Exception as e:
        logger.error(f"Error checking orphaned records: {e}")
        return False


def check_duplicate_records(db_manager, fix=False):
    """Check for duplicate records based on unique constraints."""
    logger.info("Checking for duplicate records...")
    
    try:
        conn, cursor = db_manager.connect()
        
        # Define unique constraints to check
        unique_constraints = [
            {
                "table": "courses",
                "fields": ["canvas_course_id"],
                "description": "Canvas course ID",
            },
            {
                "table": "assignments",
                "fields": ["course_id", "canvas_assignment_id"],
                "description": "course and Canvas assignment ID",
            },
            {
                "table": "modules",
                "fields": ["course_id", "canvas_module_id"],
                "description": "course and Canvas module ID",
            },
            {
                "table": "module_items",
                "fields": ["module_id", "canvas_module_item_id"],
                "description": "module and Canvas module item ID",
            },
            {
                "table": "announcements",
                "fields": ["course_id", "canvas_announcement_id"],
                "description": "course and Canvas announcement ID",
            },
        ]
        
        all_clean = True
        
        for constraint in unique_constraints:
            # Build the query to find duplicates
            fields_str = ", ".join(constraint["fields"])
            query = f"""
                SELECT {fields_str}, COUNT(*) as count
                FROM {constraint['table']}
                GROUP BY {fields_str}
                HAVING count > 1
            """
            cursor.execute(query)
            duplicates = cursor.fetchall()
            
            if duplicates:
                all_clean = False
                logger.error(f"Found {len(duplicates)} sets of duplicate records in {constraint['table']} based on {constraint['description']}")
                
                for dup in duplicates:
                    # Build a where clause to identify this set of duplicates
                    where_clauses = []
                    params = []
                    for field in constraint["fields"]:
                        where_clauses.append(f"{field} = ?")
                        params.append(dup[field])
                    
                    where_str = " AND ".join(where_clauses)
                    
                    # Get the duplicate records
                    cursor.execute(f"SELECT * FROM {constraint['table']} WHERE {where_str}", params)
                    dup_records = cursor.fetchall()
                    
                    # Log details about the duplicates
                    logger.error(f"  Duplicate set with {dup['count']} records:")
                    for i, record in enumerate(dup_records):
                        logger.error(f"    Record {i+1}: ID={record['id']}")
                    
                    if fix:
                        # Keep the first record, delete the rest
                        # First, get the ID of the record to keep
                        keep_id = dup_records[0]["id"]
                        
                        # Delete all other records
                        cursor.execute(f"DELETE FROM {constraint['table']} WHERE {where_str} AND id != ?", params + [keep_id])
                        logger.info(f"  Kept record with ID {keep_id} and deleted {dup['count'] - 1} duplicates")
                
                if fix:
                    conn.commit()
                    logger.info(f"Fixed duplicate records in {constraint['table']}")
            else:
                logger.info(f"No duplicate records found in {constraint['table']} based on {constraint['description']}")
        
        conn.close()
        return all_clean
    except Exception as e:
        logger.error(f"Error checking duplicate records: {e}")
        return False


def check_null_values(db_manager):
    """Check for NULL values in critical fields."""
    logger.info("Checking for NULL values in critical fields...")
    
    try:
        conn, cursor = db_manager.connect()
        
        # Define critical fields to check
        critical_fields = [
            {"table": "courses", "field": "course_code", "description": "course code"},
            {"table": "courses", "field": "name", "description": "course name"},
            {"table": "assignments", "field": "title", "description": "assignment title"},
            {"table": "modules", "field": "name", "description": "module name"},
            {"table": "announcements", "field": "title", "description": "announcement title"},
        ]
        
        all_clean = True
        
        for field_info in critical_fields:
            query = f"""
                SELECT COUNT(*) as count
                FROM {field_info['table']}
                WHERE {field_info['field']} IS NULL
            """
            cursor.execute(query)
            null_count = cursor.fetchone()["count"]
            
            if null_count > 0:
                all_clean = False
                logger.error(f"Found {null_count} records in {field_info['table']} with NULL {field_info['description']}")
                
                # Get sample records with NULL values
                cursor.execute(f"""
                    SELECT id FROM {field_info['table']}
                    WHERE {field_info['field']} IS NULL
                    LIMIT 5
                """)
                samples = cursor.fetchall()
                
                logger.error(f"  Sample record IDs: {', '.join(str(s['id']) for s in samples)}")
            else:
                logger.info(f"No NULL values found for {field_info['description']} in {field_info['table']}")
        
        conn.close()
        return all_clean
    except Exception as e:
        logger.error(f"Error checking NULL values: {e}")
        return False


def check_data_consistency(db_manager):
    """Check for data consistency issues."""
    logger.info("Checking for data consistency issues...")
    
    try:
        conn, cursor = db_manager.connect()
        
        # Check for courses with no assignments
        cursor.execute("""
            SELECT c.id, c.course_code, c.name
            FROM courses c
            LEFT JOIN assignments a ON c.id = a.course_id
            WHERE a.id IS NULL
        """)
        courses_no_assignments = cursor.fetchall()
        
        if courses_no_assignments:
            logger.warning(f"Found {len(courses_no_assignments)} courses with no assignments")
            for course in courses_no_assignments:
                logger.warning(f"  Course {course['course_code']} ({course['name']}) has no assignments")
        else:
            logger.info("All courses have at least one assignment")
        
        # Check for courses with no modules
        cursor.execute("""
            SELECT c.id, c.course_code, c.name
            FROM courses c
            LEFT JOIN modules m ON c.id = m.course_id
            WHERE m.id IS NULL
        """)
        courses_no_modules = cursor.fetchall()
        
        if courses_no_modules:
            logger.warning(f"Found {len(courses_no_modules)} courses with no modules")
            for course in courses_no_modules:
                logger.warning(f"  Course {course['course_code']} ({course['name']}) has no modules")
        else:
            logger.info("All courses have at least one module")
        
        # Check for modules with no items
        cursor.execute("""
            SELECT m.id, m.name, c.course_code
            FROM modules m
            LEFT JOIN module_items mi ON m.id = mi.module_id
            LEFT JOIN courses c ON m.course_id = c.id
            WHERE mi.id IS NULL
        """)
        modules_no_items = cursor.fetchall()
        
        if modules_no_items:
            logger.warning(f"Found {len(modules_no_items)} modules with no items")
            for module in modules_no_items:
                logger.warning(f"  Module {module['name']} in course {module['course_code']} has no items")
        else:
            logger.info("All modules have at least one item")
        
        # Check for courses with no syllabus
        cursor.execute("""
            SELECT c.id, c.course_code, c.name
            FROM courses c
            LEFT JOIN syllabi s ON c.id = s.course_id
            WHERE s.id IS NULL
        """)
        courses_no_syllabus = cursor.fetchall()
        
        if courses_no_syllabus:
            logger.warning(f"Found {len(courses_no_syllabus)} courses with no syllabus")
            for course in courses_no_syllabus:
                logger.warning(f"  Course {course['course_code']} ({course['name']}) has no syllabus")
        else:
            logger.info("All courses have a syllabus")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error checking data consistency: {e}")
        return False


def main():
    """Main function to run the database relationship checker."""
    parser = argparse.ArgumentParser(description="Check database relationships")
    parser.add_argument("--database", default="data/canvas_mcp.db", help="Path to the database file")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix identified issues")
    args = parser.parse_args()
    
    db_path = args.database
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        sys.exit(1)
    
    logger.info(f"Checking database relationships for: {db_path}")
    
    # Create a database manager
    db_manager = DatabaseManager(db_path)
    
    # Run checks
    foreign_keys_ok = check_foreign_keys(db_path, args.fix)
    orphaned_records_ok = check_orphaned_records(db_manager, args.fix)
    duplicate_records_ok = check_duplicate_records(db_manager, args.fix)
    null_values_ok = check_null_values(db_manager)
    data_consistency_ok = check_data_consistency(db_manager)
    
    # Summarize results
    logger.info("\nDatabase relationship check summary:")
    logger.info(f"Foreign key constraints: {'OK' if foreign_keys_ok else 'ISSUES FOUND'}")
    logger.info(f"Orphaned records: {'OK' if orphaned_records_ok else 'ISSUES FOUND'}")
    logger.info(f"Duplicate records: {'OK' if duplicate_records_ok else 'ISSUES FOUND'}")
    logger.info(f"NULL values in critical fields: {'OK' if null_values_ok else 'ISSUES FOUND'}")
    logger.info(f"Data consistency: {'OK' if data_consistency_ok else 'ISSUES FOUND'}")
    
    if not all([foreign_keys_ok, orphaned_records_ok, duplicate_records_ok, null_values_ok]):
        logger.warning("Database has integrity issues that should be addressed")
        if not args.fix:
            logger.info("Run with --fix to attempt automatic fixes")
        sys.exit(1)
    else:
        logger.info("Database relationships check completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
