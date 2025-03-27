# Canvas AI Assistant with MCP

## Overview

This repository contains our project for building a **Model Context Protocol (MCP) server** that integrates with the **Canvas** learning management system (LMS). The goal is to provide an AI-driven assistant (e.g., Claude) with structured access to course information—assignments, due dates, lecture notes—so that it can help students stay organized and succeed academically.

## Getting Started

1. Clone the repository:

```bash
git clone https://github.com/AdityaPrakash-26/Canvas-MCP.git
```

1.5 Install `uv` if you haven't already:
```bash
# if you're paranoid about piping to sh, go read the script by copy pasting the URL
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install the dependencies:

```bash
uv sync
```


## Installing to Claude Desktop

If you don't have Claude Desktop MCP setup, you can follow the [Quickstart Guide](https://modelcontextprotocol.io/quickstart/user) to install it.


To install this MCP server in Claude Desktop:

1. Open Claude Desktop
2. Go to Settings > Advanced > Edit Configuration
3. Add the following to your `claude_desktop_config.json` file in the `tools` section:
(it is a key under mcpServers)


REPLACE $DIR with the absolute path to the directory where you cloned this repo. (MANDATORY!!!!!)
REPLACE $DIR_uv with the uv path. (MANDATORY!!!!!) you can find it by running
```bash
which uv
```


```json
"Canvas MCP": {
      "command": "$DIR_uv",
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
        "$DIR",
        "src/canvas_mcp/server.py"
      ]
    }
```




## Running

To run the mcp command with uv:

```bash
uv run mcp
```

You can install this server in [Claude Desktop](https://claude.ai/download) and interact with it right away by running:
```bash
mcp install src/canvas_mcp/server.py
```


## Testing

Alternatively, you can test it with the MCP Inspector:
```bash
mcp dev src/canvas_mcp/server.py
```

## Secrets

Clone .env.example to .env and add your Canvas API key.
Also change the variables in the .env file to match your Canvas instance.
"CANVAS_API_KEY"
"CANVAS_API_URL"



---


## Repository & Kanban

- This **public GitHub repository** contains our code, documentation, and issues/tasks.  
- We maintain a **Kanban board** under the “Projects” tab with tasks from our roadmap for the first sprint.  

**Link to the Repo**: (https://github.com/AdityaPrakash-26/Canvas-MCP)

**Link to the Kanban**: (https://github.com/users/AdityaPrakash-26/projects/1)

---

## License
