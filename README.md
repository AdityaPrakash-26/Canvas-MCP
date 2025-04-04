# Canvas AI Assistant with MCP

## Overview

This repository contains our project for building a **Model Context Protocol (MCP) server** that integrates with the **Canvas** learning management system (LMS). The goal is to provide an AI-driven assistant (e.g., Claude) with structured access to course information—assignments, due dates, lecture notes—so that it can help students stay organized and succeed academically.

## Getting Started

# Mac:

0. Install `uv` if you haven't already:
```bash
# if you're paranoid about piping to sh, go read the script by copy pasting the URL
curl -LsSf https://astral.sh/uv/install.sh | sh
```

1. Clone the repository:

```bash
git clone https://github.com/AdityaPrakash-26/Canvas-MCP.git && cd Canvas-MCP
```


2. Create the virtual environment:

```bash
uv venv --seed
```

3. Activate the virtual environment:

```bash
source .venv/bin/activate
```

4. Install the dependencies:

```bash
uv sync
```


## Installing to Claude Desktop

If you don't have Claude Desktop MCP setup, you can follow the [Quickstart Guide](https://modelcontextprotocol.io/quickstart/user) to install it.


To install this MCP server in Claude Desktop:

1. Open Claude Desktop
2. Go to Settings > Advanced > Edit Configuration
3. (MAC ONLY) Add the following to your `claude_desktop_config.json` file in the `tools` section:
(it is a key under mcpServers)
4. (WINDOWS ONLY) See instructions below


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


# Windows

We recommend using WSL (Windows Subsystem for Linux) to use this software. Installation instructions can be founder [here](https://learn.microsoft.com/en-us/windows/wsl/install).

- Once installed, set up a new user in `/home/<username>`
- Once you have the virtual environment setup, modify your claude desktop app config to include the following:

```json
"Canvas MCP": {
  "command": "wsl.exe",
  "args": [
    "-d",
    "Ubuntu",
    "--exec",
    "/home/<USER>/.local/bin/uv",
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
    "/home/<USER>/Canvas-MCP",
    "src/canvas_mcp/server.py"
  ]
}
```

Replace `<USER>` with your username.


## Running

To run the mcp command with uv:

```bash
uv run mcp
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
