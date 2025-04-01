"""
Database configuration and session management using SQLAlchemy.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Configure paths
PROJECT_DIR = Path(__file__).parent.parent.parent
DB_DIR = PROJECT_DIR / "data"
DB_FILENAME = "canvas_mcp.db"
DB_PATH = DB_DIR / DB_FILENAME
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH.resolve()}"

# Ensure data directory exists
os.makedirs(DB_DIR, exist_ok=True)

# Create SQLAlchemy engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite
    echo=os.environ.get("SQLALCHEMY_ECHO", False),  # Set SQLALCHEMY_ECHO=True for debugging
)

# Enable foreign key support for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # pylint: disable=unused-argument
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()


def get_db():
    """
    Dependency function to get a database session.
    Ensures the session is closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(engine_to_init=engine):
    """Initialize the database by creating tables."""
    # Import models here to ensure they are registered with Base
    # pylint: disable=import-outside-toplevel, unused-import
    from . import models
    print(f"Initializing database schema at {engine_to_init.url}...")
    Base.metadata.create_all(bind=engine_to_init)
    print("Database schema initialized.")

# Check if the database file exists, initialize if not
if not DB_PATH.exists():
    print(f"Database file not found at {DB_PATH}. Initializing...")
    init_db()
elif os.path.getsize(DB_PATH) == 0:
    print(f"Database file at {DB_PATH} is empty. Initializing...")
    init_db()
else:
    print(f"Database file found at {DB_PATH}.")