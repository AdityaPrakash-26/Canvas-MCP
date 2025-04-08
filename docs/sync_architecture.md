# Canvas-MCP Sync Architecture

This document outlines the architecture and implementation of the Canvas-MCP synchronization system, which handles data flow between the Canvas API and the local database.

## Architecture Overview

The sync system follows a layered architecture with clear separation of concerns:

1. **Models Layer**: Pydantic models for data validation and transformation
2. **API Adapter Layer**: Dedicated adapter for Canvas API interactions
3. **Service Layer**: Orchestration of data flow between API and database
4. **Persistence Layer**: Database operations using SQLite
5. **Tools Layer**: MCP tools that use the services

## Key Components

### 1. Pydantic Models (`models.py`)

- Define the structure and validation rules for data
- Handle type coercion and field transformations
- Provide clear data contracts between layers
- Use `Field(alias='...')` to map API field names to database column names
- Implement `@field_validator` for data transformation and validation

### 2. Canvas API Adapter (`canvas_api_adapter.py`)

- Responsible only for interacting with the Canvas API
- Handles API-specific errors and returns raw data
- Provides a clean interface for the service layer
- Implements methods for each distinct API call needed
- Returns raw data or `None`/`[]` on error

### 3. Sync Service (`sync/` package)

- Orchestrates data flow between API and database
- Uses Pydantic models for validation
- Implements business logic for synchronization
- Manages database transactions
- Organized into separate modules for each entity type:
  - `service.py`: Main service class
  - `courses.py`: Course synchronization
  - `assignments.py`: Assignment synchronization
  - `modules.py`: Module synchronization
  - `announcements.py`: Announcement synchronization
  - `all.py`: Orchestration of all sync operations

### 4. Database Manager (`db_manager.py`)

- Provides managed SQLite connections
- Implements transaction handling via decorators
- Offers utility methods for database operations
- Ensures proper connection lifecycle management

### 5. MCP Tools (`tools/*.py`)

- Use the service layer for operations
- Focus on request handling and response formatting
- Delegate business logic to services

## Implementation Details

### Database Handling

All database operations use the `@DatabaseManager.with_connection` decorator to ensure proper transaction handling:

1. Connections are automatically opened and closed
2. Transactions are automatically committed on success
3. Transactions are automatically rolled back on error
4. Connection leaks are prevented

### Sync Process Flow

The sync process follows a consistent pattern:

1. **Fetch**: Retrieve data from the Canvas API
2. **Filter**: Apply business rules to filter the data
3. **Validate**: Use Pydantic models to validate and transform the data
4. **Persist**: Store the validated data in the database

### Error Handling

Comprehensive error handling is implemented at each layer:

1. API errors are caught and logged
2. Validation errors are caught and logged
3. Database errors are caught and logged
4. Transactions are rolled back on error

## Completed Changes

1. **Created New Architecture**:
   - Created a modular sync package with separate files for each sync operation
   - Implemented Pydantic models for data validation and transformation
   - Created a dedicated CanvasApiAdapter for API interactions
   - Implemented proper transaction handling with the DatabaseManager.with_connection decorator

2. **Improved Database Handling**:
   - Replaced manual connection management with the decorator pattern
   - Ensured single transactions for related operations
   - Implemented proper error handling with automatic rollbacks
   - Prevented connection leaks

3. **Enhanced Code Organization**:
   - Separated concerns into distinct modules
   - Improved type annotations with modern Python syntax
   - Added comprehensive docstrings
   - Created README documentation

4. **Updated Server Integration**:
   - Updated server.py to use the new components
   - Updated sync.py tool to use the new SyncService

## Remaining Tasks

1. **Update Tests**:
   - Update unit tests to use the new architecture
   - Update integration tests to use the new architecture
   - Create new tests for the new components

2. **Remove Old Code**:
   - Remove canvas_client.py once all tests are updated
   - Remove sync_service.py and sync_service_methods.py

3. **Update Scripts**:
   - Update scripts that directly use canvas_client.py

4. **Documentation**:
   - Update main README.md with the new architecture
   - Add more examples and usage instructions

## Benefits

1. **Improved Maintainability**:
   - Smaller, focused modules are easier to understand and maintain
   - Clear separation of concerns makes the code more modular
   - Better error handling improves reliability

2. **Enhanced Testability**:
   - Components can be tested in isolation
   - Mocking is easier with clear boundaries
   - Transaction handling is more reliable

3. **Better Type Safety**:
   - Pydantic models provide runtime type checking
   - Modern type annotations improve IDE support
   - Explicit error handling prevents silent failures

4. **Cleaner Code**:
   - Consistent patterns throughout the codebase
   - Better organization of related functionality
   - Improved documentation

## Future Improvements

1. Add more comprehensive error handling
2. Implement caching for API responses
3. Add more unit tests for each layer
4. Improve documentation
5. Add more validation rules to Pydantic models
