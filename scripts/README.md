# Canvas-MCP Test Scripts

This directory contains diagnostic and test scripts for the Canvas-MCP application. These scripts are designed to help identify and fix issues in the codebase, particularly focusing on synchronization, data integrity, and error handling.

## Available Scripts

### Master Test Script

- **run_all_tests.py**: Runs all tests and generates a comprehensive report.
  ```
  python scripts/run_all_tests.py [--verbose] [--fix] [--term_id TERM_ID]
  ```
  - `--verbose`: Enable verbose logging
  - `--fix`: Attempt to fix identified issues
  - `--term_id`: Specify a term ID to sync (default: -1, most recent term)

### Individual Test Scripts

- **test_full_sync_process.py**: Tests the full synchronization process with detailed logging.
  ```
  python scripts/test_full_sync_process.py [--verbose] [--term_id TERM_ID]
  ```

- **check_database_relationships.py**: Checks database integrity and relationships.
  ```
  python scripts/check_database_relationships.py [--database PATH] [--fix]
  ```
  - `--database`: Path to the database file (default: data/canvas_mcp.db)
  - `--fix`: Attempt to fix identified issues

- **test_error_handling.py**: Tests error handling and edge cases.
  ```
  python scripts/test_error_handling.py [--verbose]
  ```

- **test_tools_integration.py**: Tests the integration between different tools.
  ```
  python scripts/test_tools_integration.py [--verbose]
  ```

## Usage Examples

### Running All Tests

To run all tests with default settings:

```bash
python scripts/run_all_tests.py
```

To run all tests with verbose logging and fix identified issues:

```bash
python scripts/run_all_tests.py --verbose --fix
```

### Checking Database Integrity

To check the integrity of a specific database:

```bash
python scripts/check_database_relationships.py --database path/to/your/database.db
```

To check and fix database integrity issues:

```bash
python scripts/check_database_relationships.py --fix
```

### Testing Synchronization

To test the synchronization process for a specific term:

```bash
python scripts/test_full_sync_process.py --term_id 123
```

## Interpreting Results

Each script generates detailed logs that can help identify issues in the codebase. The master test script (`run_all_tests.py`) generates a comprehensive Markdown report with:

- A summary of all tests run
- Detailed results for each test
- Error details for failed tests
- Recommendations for addressing identified issues

Look for these reports in the project root directory with names like `canvas_mcp_test_report_YYYYMMDD_HHMMSS.md`.

## Troubleshooting

If you encounter issues with the test scripts:

1. Ensure your Canvas API credentials are set in the environment variables:
   ```bash
   export CANVAS_API_KEY=your_api_key
   export CANVAS_API_URL=your_canvas_url
   ```

2. Check that the database path exists and is writable.

3. Run the scripts with the `--verbose` flag for more detailed logging.

4. If a test fails, check the generated report for specific error details.

## Adding New Tests

When adding new tests to these scripts, follow these guidelines:

1. Use proper error handling and logging
2. Include detailed comments explaining the purpose of each test
3. Add appropriate command-line arguments for configuration
4. Update this README with information about the new tests
