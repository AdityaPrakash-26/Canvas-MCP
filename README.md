# Canvas MCP Server

## Overview
The Canvas MCP Server helps AI assistants like Claude access Canvas LMS content (assignments, syllabi, deadlines), allowing students to quickly ask questions like:

- "What's due this week?"
- "Send me tomorrow's notes."

This simplifies finding course info by automatically syncing Canvas data to your AI assistant.

## Features
- **Canvas Integration:** Automatically sync courses, assignments, modules, announcements.
- **Flexible Parsing:** Extract syllabus details from PDFs, Word docs, HTML.
- **Term Filtering:** Only sync current-term courses.
- **Opt-Out:** Easily exclude courses you don't want indexed.

## Quick Tech Overview
- **Language:** Python 3.12+
- **Database:** SQLite (local storage, zero config)
- **Canvas API:** canvasapi
- **Document Parsing:** pdfplumber (PDF), python-docx (Word), BeautifulSoup4 (HTML)
- **AI Integration:** Model Context Protocol (MCP)
- **Package Management:** UV (faster pip alternative)

## Setup Instructions

### Prerequisites
- Python 3.12+
- [UV Package Manager](https://astral.sh/uv)
- Canvas API Key & URL
- Claude Desktop with MCP support ([download](https://claude.ai/download))

---

### Mac Installation

Install UV if needed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Set up Canvas MCP:
```bash
git clone https://github.com/AdityaPrakash-26/Canvas-MCP.git && cd Canvas-MCP
uv venv --seed
source .venv/bin/activate
uv sync
echo "CANVAS_API_KEY=your_canvas_api_key_here" > .env
echo "CANVAS_API_URL=https://canvas.yourschool.edu" >> .env
uv run init_db.py
```

#### Configure Claude Desktop (Mac)

Open `claude_desktop_config.json` (Claude > Settings > Advanced) and add:

```json
"Canvas MCP": {
  "command": "/path/to/uv",
  "args": [
    "run",
    "--directory",
    "/absolute/path/to/Canvas-MCP",
    "canvas-mcp"
  ]
}
```

Replace `/path/to/uv` with your UV executable path (`which uv`) and `/absolute/path/to/Canvas-MCP` with your cloned repository location.

---

### Windows Installation (WSL)

Please use [WSL](https://learn.microsoft.com/en-us/windows/wsl/install).

After installing WSL:

1. Clone the repository into your WSL home:
```bash
git clone https://github.com/AdityaPrakash-26/Canvas-MCP.git ~/Canvas-MCP
cd ~/Canvas-MCP
```

2. Install UV and dependencies:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --seed
source .venv/bin/activate
uv sync
echo "CANVAS_API_KEY=your_canvas_api_key_here" > .env
echo "CANVAS_API_URL=https://canvas.yourschool.edu" >> .env
uv run python init_db.py
```

#### Configure Claude Desktop (Windows/WSL)

Edit Claude Desktop's `claude_desktop_config.json` with:

```json
"Canvas MCP": {
  "command": "wsl.exe",
  "args": [
    "-d",
    "Ubuntu",
    "--exec",
    "/home/<USER>/.local/bin/uv", # REPLACE, run `which uv` to find ur `uv` install directory
    "run",
    "--directory",
    "/home/<USER>/Canvas-MCP", # REPLACE
    "canvas-mcp"
  ]
}
```

Replace `<USER>` with your WSL username. Also, verify your `uv` absolute path before copy pasting. 

---

## Development Commands

- Run the server in `inspector` mode so you can look at it:
```bash
uv run mcp dev --with . src/canvas_mcp/__main__.py
```

- Run tests:
```bash
uv run pytest
```

- Format/lint code:
```bash
uv run ruff format .
uv run ruff check . --fix
```

- Static type checking:
```bash
uv run mypy src
```

## Troubleshooting Quick Tips

- **Canvas API issues?** Verify `.env` keys/URLs.
- **Database issues?** Reset:
```bash
rm -f data/canvas_mcp.db && uv run python init_db.py
```

- **Claude Desktop not recognizing MCP tools?** Ensure paths in JSON config are absolute and correct.


## Resources
- [GitHub Repository](https://github.com/AdityaPrakash-26/Canvas-MCP)
- [Canvas API Documentation](https://canvas.instructure.com/doc/api/)
- [MCP Documentation](https://modelcontextprotocol.io/)
