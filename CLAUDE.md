# Development Guidelines

This document contains critical information about working with this codebase. Follow these guidelines precisely.

## Build/Test/Lint Commands

- Run server: `uv run mcp dev src/canvas_mcp/server.py`
- Install to Claude: `uv run mcp install src/canvas_mcp/server.py`
- Run tests: `uv run pytest`
- Run single test: `uv run pytest path/to/test.py::test_function`
- Format code: `uv run ruff format .`
- Lint check: `uv run ruff check .`
- Lint fix: `uv run ruff check . --fix`
- Type check: `uv run mypy src`

## Code Style

- Line length: 88 chars max
- Type hints: Required for all code
- Docstrings: Required for public APIs
- Import style: Use absolute imports, sorted with `ruff`
- String quotes: Single quotes preferred
- Error handling: Use specific exception types, provide context
- Function size: Small, focused functions (< 50 lines)
- Naming: snake_case for variables/functions, PascalCase for classes

## Package Management

- ONLY use uv, NEVER pip
- Installation: `uv add package`
- Running tools: `uv run tool`
- Upgrading: `uv add --dev package --upgrade-package package`
- FORBIDDEN: `uv pip install`, `@latest` syntax

## Version Control Workflow

- Create feature branches before starting work
- Commit frequently with meaningful messages
- For issues: `git commit --trailer "Github-Issue:#<number>"`
- NEVER include "co-authored-by" or mention tooling
- Create detailed PR descriptions focusing on problem & solution

## MCP Server Requirements

- Use `FastMCP` from `mcp.server.fastmcp`
- Tools must be properly typed with docstrings
- Resources must have well-defined URI templates
- Follow existing patterns in `src/canvas_mcp`
- Document all APIs thoroughly

## Information Gathering

- Search `library_docs` for reference documentation
- Create new lessons in `lessons/` when you learn something
- Document mistakes for future reference