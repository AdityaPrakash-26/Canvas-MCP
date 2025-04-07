"""
Script to initialize the database schema using SQLAlchemy models.
"""
import sys

from .database import engine, init_db

if __name__ == "__main__":
    print("Running database initialization script...")
    # This import ensures models are registered before create_all

    init_db(engine)
    print("Database initialization complete.")
    sys.exit(0)
