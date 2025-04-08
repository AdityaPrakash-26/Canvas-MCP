# Canvas MCP Tool Tester

This is a comprehensive testing tool for the Canvas MCP server. It allows you to test all available tools, examine their input schemas, and interact with them directly.

## Features

- Connect to the Canvas MCP server
- List available tools with their input schemas
- Test all tools automatically with sample arguments
- Call individual tools with custom arguments
- Interactive command-line interface

## Prerequisites

- Python 3.8+
- Canvas MCP server

## Usage

### Basic Usage

```bash
python scripts/test_mcp_tools.py
```

This will connect to the default server at `src/canvas_mcp/server.py`.

### Specify Server Path

```bash
python scripts/test_mcp_tools.py --server path/to/server.py
```

## Interactive Commands

Once the tester is running, you can use the following commands:

- `help`: Show available commands
- `tools`: List available tools with their input schemas
- `test`: Run tests on all tools automatically
- `tool <name> [args]`: Call a tool with optional JSON arguments
  - Example: `tool get_course_list`
  - Example with args: `tool get_course_modules {"course_id": 123456}`
- `exit` or `quit`: Exit the tester

## Examples

### List Available Tools

```
> tools
```

This will show all available tools with their descriptions and input schemas.

### Run Automated Tests

```
> test
```

This will run tests on all available tools using sample arguments.

### Get Course List

```
> tool get_course_list
```

### Get Course Modules

```
> tool get_course_modules {"course_id": 146127}
```

### Get Upcoming Deadlines

```
> tool get_upcoming_deadlines {"days": 14}
```

## Troubleshooting

### Connection Issues

If you have trouble connecting to the server:

1. Make sure the server path is correct
2. Ensure the server is running or can be started by the tester
3. Check for any error messages in the console

### Tool Execution Errors

If a tool fails to execute:

1. Check the input schema to ensure you're providing the correct arguments
2. Verify that the database has the necessary data
3. Check the server logs for any errors

## Advanced Usage

### Testing Performance

You can test the performance of tools by running them multiple times:

```
> tool get_course_list
> tool get_course_list
> tool get_course_list
```

### Testing Error Handling

Test how tools handle invalid inputs:

```
> tool get_course_modules {"course_id": 999999}
```

### Testing Data Consistency

Compare the results of related tools:

```
> tool get_course_list
> tool get_course_modules {"course_id": 146127}
> tool get_course_assignments {"course_id": 146127}
```

## Contributing

Feel free to enhance this tester with additional features or improvements!
