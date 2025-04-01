# AI Coding Agent Setup

## Setup

### Requirements

Claude Desktop

The following MCPs:
- wcgw 
- codemcp
- fetch


Here's my current setup, for reference:
```json
{
  "mcpServers": {
    "codemcp": {
      "command": "/Users/darin/.cargo/bin/uvx",
      "args": [
        "--from",
        "git+https://github.com/ezyang/codemcp@prod",
        "codemcp"
      ]
    },
    "wcgw": {
      "command": "/Users/darin/.cargo/bin/uv",
      "args": [
        "tool",
        "run",
        "--from",
        "wcgw@latest",
        "--with",
        "tree-sitter",
        "--with",
        "tree-sitter-bash",
        "--python",
        "3.12",
        "wcgw_mcp"
      ]
    },
    "fetch": {
      "command": "/Users/darin/.cargo/bin/uvx",
      "args": [
        "mcp-server-fetch"
      ]
    },
    "think-tool": {
      "command": "npx",
      "args": [
        "-y",
        "@cgize/mcp-think-tool"
      ],
      "type": "stdio",
      "pollingInterval": 30000,
      "startupTimeout": 30000,
      "restartOnFailure": true
    },
    "Canvas MCP": {
      "command": "/Users/darin/.cargo/bin/uv",
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
        "/Users/darin/Projects/Canvas-MCP",
        "src/canvas_mcp/server.py"
      ]
    },
  },
  "globalShortcut": ""
}
```

## Start Coding

1. Make sure you're using the `thinking` version of clade 3.7 sonnet.  
   1. Look at the settings icon in the bottom left when you start a chat. Enable `extended thinking`. 
2. 