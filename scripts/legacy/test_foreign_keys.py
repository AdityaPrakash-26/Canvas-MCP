#!/usr/bin/env python3
"""
Test script to verify SQLite foreign key behavior.
"""

import os
import sqlite3
from pathlib import Path

# Create a test database path
test_db_path = Path(__file__).parent / "test_foreign_keys.db"

# Remove the test database if it exists
if os.path.exists(test_db_path):
    os.remove(test_db_path)

print(f"Testing SQLite foreign key behavior with Python {sqlite3.sqlite_version}")
print(f"Using test database: {test_db_path}")

# Method 1: Using URI parameter
print("\nMethod 1: Using URI parameter")
conn1 = sqlite3.connect(f"file:{test_db_path}?foreign_keys=1", uri=True)
cursor1 = conn1.cursor()
cursor1.execute("PRAGMA foreign_keys")
result1 = cursor1.fetchone()[0]
print(f"Foreign keys enabled: {bool(result1)}")
conn1.close()

# Method 2: Using PRAGMA statement
print("\nMethod 2: Using PRAGMA statement")
conn2 = sqlite3.connect(test_db_path)
cursor2 = conn2.cursor()
cursor2.execute("PRAGMA foreign_keys = ON")
cursor2.execute("PRAGMA foreign_keys")
result2 = cursor2.fetchone()[0]
print(f"Foreign keys enabled: {bool(result2)}")
conn2.close()

# Method 3: Using both
print("\nMethod 3: Using both methods")
conn3 = sqlite3.connect(f"file:{test_db_path}?foreign_keys=1", uri=True)
cursor3 = conn3.cursor()
cursor3.execute("PRAGMA foreign_keys = ON")
cursor3.execute("PRAGMA foreign_keys")
result3 = cursor3.fetchone()[0]
print(f"Foreign keys enabled: {bool(result3)}")
conn3.close()

# Method 4: Check if setting persists across operations
print("\nMethod 4: Check if setting persists across operations")
conn4 = sqlite3.connect(test_db_path)
cursor4 = conn4.cursor()
cursor4.execute("PRAGMA foreign_keys = ON")
cursor4.execute("PRAGMA foreign_keys")
result4a = cursor4.fetchone()[0]
print(f"Foreign keys enabled (initial): {bool(result4a)}")

# Do some operations
cursor4.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
cursor4.execute("INSERT INTO test VALUES (1)")
conn4.commit()

# Check again
cursor4.execute("PRAGMA foreign_keys")
result4b = cursor4.fetchone()[0]
print(f"Foreign keys enabled (after operations): {bool(result4b)}")
conn4.close()

# Method 5: Check if setting persists across transactions
print("\nMethod 5: Check if setting persists across transactions")
conn5 = sqlite3.connect(test_db_path)
cursor5 = conn5.cursor()
cursor5.execute("PRAGMA foreign_keys = ON")
cursor5.execute("PRAGMA foreign_keys")
result5a = cursor5.fetchone()[0]
print(f"Foreign keys enabled (initial): {bool(result5a)}")

# Start a transaction
conn5.execute("BEGIN TRANSACTION")
cursor5.execute("INSERT INTO test VALUES (2)")
conn5.commit()

# Check again
cursor5.execute("PRAGMA foreign_keys")
result5b = cursor5.fetchone()[0]
print(f"Foreign keys enabled (after transaction): {bool(result5b)}")
conn5.close()

# Method 6: Check with journal mode
print("\nMethod 6: Check with different journal modes")
conn6 = sqlite3.connect(test_db_path)
cursor6 = conn6.cursor()

# Check default journal mode
cursor6.execute("PRAGMA journal_mode")
journal_mode = cursor6.fetchone()[0]
print(f"Default journal mode: {journal_mode}")

# Set foreign keys
cursor6.execute("PRAGMA foreign_keys = ON")
cursor6.execute("PRAGMA foreign_keys")
result6a = cursor6.fetchone()[0]
print(f"Foreign keys enabled (default journal): {bool(result6a)}")

# Change to WAL mode
cursor6.execute("PRAGMA journal_mode = WAL")
journal_mode = cursor6.fetchone()[0]
print(f"New journal mode: {journal_mode}")

# Check foreign keys again
cursor6.execute("PRAGMA foreign_keys")
result6b = cursor6.fetchone()[0]
print(f"Foreign keys enabled (WAL journal): {bool(result6b)}")

conn6.close()

# Clean up
os.remove(test_db_path)
if os.path.exists(f"{test_db_path}-wal"):
    os.remove(f"{test_db_path}-wal")
if os.path.exists(f"{test_db_path}-shm"):
    os.remove(f"{test_db_path}-shm")

print("\nTest completed.")
