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


## Running and Testing

To run the mcp command with uv:

```bash
uv run mcp
```

You can install this server in [Claude Desktop](https://claude.ai/download) and interact with it right away by running:
```bash
mcp install src/canvas_mcp/server.py
```

Alternatively, you can test it with the MCP Inspector:
```bash
mcp dev src/canvas_mcp/server.py
```

## Secrets

Clone .env.example to .env and add your Canvas API key.



---


## Repository & Kanban

- This **public GitHub repository** contains our code, documentation, and issues/tasks.  
- We maintain a **Kanban board** under the “Projects” tab with tasks from our roadmap for the first sprint.  

**Link to the Repo**: (https://github.com/AdityaPrakash-26/Canvas-MCP)

**Link to the Kanban**: (https://github.com/users/AdityaPrakash-26/projects/1)

---

## License
