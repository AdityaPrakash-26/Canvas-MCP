# Installation Guide for Canvas MCP

This guide will walk you through the complete installation and setup process for the Canvas MCP server.

## Prerequisites

- Python 3.12 or higher
- UV package manager
- Canvas API access token
- Claude Desktop (for integration with Claude)

## Step 1: Install UV

If you don't have UV installed, run:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows, follow the [UV installation guide](https://astral.sh/uv/docs/installation).

## Step 2: Clone the Repository

```bash
git clone https://github.com/AdityaPrakash-26/Canvas-MCP.git
cd Canvas-MCP
```

## Step 3: Set Up Environment Variables

1. Create a `.env` file by copying the example:

```bash
cp .env.example .env
```

2. Edit the `.env` file and add your Canvas credentials:

```
CANVAS_API_KEY=your_canvas_api_key_here
CANVAS_API_URL=your_canvas_instance_url
```

To get your Canvas API key:
1. Log in to Canvas
2. Go to Account > Settings
3. Scroll down to "Approved Integrations"
4. Click "New Access Token"
5. Enter a purpose and expiration date
6. Copy the token provided

## Step 4: Install Dependencies

```bash
uv sync
```

## Step 5: Initialize the Database

```bash
uv run python init_db.py
```

## Step 6: Test the MCP Server

```bash
uv run mcp dev src/canvas_mcp/server.py
```

This should start the MCP Inspector at http://127.0.0.1:6274. Open this URL in your browser to test the server functionality.

## Step 7: Install to Claude Desktop

1. Download and install [Claude Desktop](https://claude.ai/download)

2. Open Claude Desktop

3. Go to Settings > Advanced > Edit Configuration

4. Add the following to your `claude_desktop_config.json` file in the `tools` section (under `mcpServers`):

```json
"Canvas MCP": {
  "command": "/path/to/uv",
  "args": [
    "run",
    "--with",
    "canvasapi>=3.3.0",
    "--with",
    "mcp[cli]",
    "--with",
    "python-dotenv>=1.0.1",
    "--with",
    "structlog>=24.1.0",
    "--directory",
    "/absolute/path/to/Canvas-MCP",
    "src/canvas_mcp/server.py"
  ]
}
```

Replace:
- `/path/to/uv` with the path to your UV executable (find it with `which uv` on Unix/macOS)
- `/absolute/path/to/Canvas-MCP` with the absolute path to your cloned repository

5. Save the configuration file and restart Claude Desktop

## Step 8: Sync Canvas Data

To verify everything is working, ask Claude:

> Can you sync my Canvas data?

Claude should call the `sync_canvas_data` function and start synchronizing your Canvas data to the local database.

## Troubleshooting

### Canvas API Connection Issues

- Double check your API key and URL in the `.env` file
- Ensure your Canvas account has the necessary permissions
- Check if your Canvas instance requires any additional authentication

### Database Errors

If you encounter database errors during initialization:

```bash
rm data/canvas_mcp.db
uv run python init_db.py
```

### MCP Server Connection Issues

If Claude can't connect to the MCP server:

1. Ensure the server is running
2. Check the configuration in `claude_desktop_config.json`
3. Verify the paths are correct and absolute

### Python Version Issues

If you encounter Python version errors:

```bash
python --version
```

Make sure you have Python 3.12 or higher installed and available in your PATH.

## Updating

To update to the latest version:

```bash
git pull
uv sync
```

## Advanced Usage

See the [README.md](README.md) file for advanced usage and development information.
