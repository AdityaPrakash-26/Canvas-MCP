# Canvas MCP Sync Package

This package provides synchronization functionality between the Canvas API and the local database.

## Architecture

The sync package follows a modular design with clear separation of concerns:

1. **SyncService**: The main orchestrator class that coordinates the synchronization process.
2. **CanvasApiAdapter**: A dedicated adapter for interacting with the Canvas API.
3. **Pydantic Models**: Data models for validation and transformation.
4. **DatabaseManager**: Manages database connections and transactions.

## Components

- **service.py**: Defines the main `SyncService` class that imports methods from other modules.
- **courses.py**: Handles synchronization of course data.
- **assignments.py**: Handles synchronization of assignment data.
- **modules.py**: Handles synchronization of module data.
- **announcements.py**: Handles synchronization of announcement data.
- **all.py**: Provides the `sync_all` method to synchronize all data.

## Database Handling

All database operations use the `@DatabaseManager.with_connection` decorator to ensure proper transaction handling:

1. Connections are automatically opened and closed.
2. Transactions are automatically committed on success.
3. Transactions are automatically rolled back on error.
4. Connection leaks are prevented.

## Usage

The `SyncService` is initialized in the application lifespan and made available to tools through the lifespan context:

```python
# Initialize the service
sync_service = SyncService(db_manager, api_adapter)

# Use the service in tools
sync_service.sync_all()
```

## Error Handling

All methods include comprehensive error handling:

1. API errors are caught and logged.
2. Database errors are caught and logged.
3. Validation errors are caught and logged.
4. Transactions are rolled back on error.

## Testing

The sync package is designed to be easily testable:

1. The `CanvasApiAdapter` can be mocked for unit tests.
2. The `SyncService` can be initialized with a test database for integration tests.
3. Each component can be tested in isolation.
