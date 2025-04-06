# Troubleshooting Guide for Canvas MCP

This guide helps diagnose and resolve common issues with the Canvas MCP server.

## Canvas API Connection Issues

### Problem: Unable to authenticate with Canvas API

**Symptoms:**
- Error message: "Invalid API key" or "Unauthorized"
- Failed authentication during `sync_canvas_data`

**Solutions:**
1. Verify your API key in the `.env` file
2. Ensure the Canvas API URL is correct and doesn't have a trailing slash
3. Check if your API token has expired (generate a new one if needed)
4. Confirm your Canvas account has the necessary permissions

### Problem: Rate limiting from Canvas API

**Symptoms:**
- Error message: "Rate limit exceeded"
- Incomplete data synchronization

**Solutions:**
1. Reduce the scope of synchronization (sync fewer courses)
2. Add delay between API calls by modifying `canvas_client.py`
3. Request increased API rate limits from your Canvas administrator

## Database Issues

### Problem: Database corruption or schema errors

**Symptoms:**
- SQLite errors during operations
- Missing tables or columns
- "no such table" errors

**Solutions:**
1. Reset the database:
   ```bash
   rm data/canvas_mcp.db
   uv run python init_db.py
   ```
2. Verify database schema:
   ```bash
   sqlite3 data/canvas_mcp.db .schema
   ```
3. Check for SQLite version compatibility

### Problem: Data not showing up after sync

**Symptoms:**
- Successful sync but empty database tables
- No errors but missing data

**Solutions:**
1. Check course term filtering (you might be filtering out all courses)
2. Verify user permissions in Canvas (you may only have access to certain courses)
3. Run with debug logging:
   ```bash
   PYTHONPATH=. LOGLEVEL=DEBUG uv run python src/canvas_mcp/server.py
   ```

## PDF Extraction Issues

### Problem: Unable to extract text from PDFs

**Symptoms:**
- Empty text from PDF extraction
- Errors during PDF processing

**Solutions:**
1. Check if the PDF is scanned (OCR might be needed)
2. Verify PDF URLs are accessible
3. Update pdfplumber to the latest version:
   ```bash
   uv add --upgrade pdfplumber
   ```
4. Install additional PDF dependencies:
   ```bash
   uv add --dev setuptools wheel
   ```

## MCP Server Connection Issues

### Problem: Claude can't connect to the MCP server

**Symptoms:**
- Claude reports "unable to connect to tool"
- MCP server isn't recognized

**Solutions:**
1. Ensure the server is running:
   ```bash
   uv run mcp dev src/canvas_mcp/server.py
   ```
2. Verify Claude Desktop configuration:
   - Check paths in `claude_desktop_config.json`
   - Make sure all paths are absolute
   - Verify UV path is correct
3. Restart Claude Desktop after configuration changes
4. Check for conflicting MCP servers

### Problem: MCP server crashes

**Symptoms:**
- Server exits unexpectedly
- Error messages in terminal

**Solutions:**
1. Check for Python version compatibility (Python 3.12+ required)
2. Verify all dependencies are installed:
   ```bash
   uv sync
   ```
3. Run with minimal configuration:
   ```bash
   uv run mcp dev --minimal src/canvas_mcp/server.py
   ```

## Claude Integration Issues

### Problem: Claude cannot use MCP functions

**Symptoms:**
- Claude doesn't recognize MCP tools
- Function calls fail silently

**Solutions:**
1. Reinstall the MCP server to Claude:
   ```bash
   uv run mcp install src/canvas_mcp/server.py
   ```
2. Ask Claude to refresh tools:
   "Could you refresh your available tools and check if Canvas MCP is available?"
3. Verify Claude has the necessary permissions

### Problem: Claude cannot interpret results correctly

**Symptoms:**
- Claude misinterprets data formats
- Inconsistent responses about Canvas data

**Solutions:**
1. Use more specific prompts with Claude
2. Verify data formatting in resources
3. Check for inconsistencies in database schema

## Environment and Installation Issues

### Problem: UV command not found

**Symptoms:**
- "Command not found: uv" error

**Solutions:**
1. Install UV:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. Add UV to your PATH:
   ```bash
   export PATH="$HOME/.cargo/bin:$PATH"
   ```
3. Use the full path to UV

### Problem: Python version incompatibility

**Symptoms:**
- Syntax errors or runtime errors
- Package dependency issues

**Solutions:**
1. Install Python 3.12 or higher
2. Create a new virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate
   ```
3. Verify Python version:
   ```bash
   python --version
   ```

## Additional Assistance

If issues persist after trying these solutions:

1. Check the project GitHub issues: https://github.com/AdityaPrakash-26/Canvas-MCP/issues
2. Report a new issue with detailed information about the problem
3. Include logs, error messages, and steps to reproduce
