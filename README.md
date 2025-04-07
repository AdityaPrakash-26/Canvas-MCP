# Canvas MCP - AI Assistant for Canvas LMS

## Overview

Canvas MCP is a **Model Context Protocol (MCP) server** that integrates with the **Canvas** Learning Management System. This integration allows AI assistants like Claude to access structured course information—syllabi, assignments, deadlines, modules—helping students stay organized and succeed academically.

The project addresses the challenge of navigating Canvas for information by automating lookups and enabling an AI to answer queries like "What's due this week?" or "Show me notes for tomorrow's class."

![Canvas MCP Architecture](https://modelcontextprotocol.io/img/system-overview.png)

## Features

- **Canvas API Integration**: Sync courses, assignments, modules, and announcements
- **Syllabus Parsing**: Extract important information from course syllabi in various formats
- **PDF Extraction**: Process and extract text from PDF files in courses
- **Smart Filtering**: Term-based course filtering to focus on current semester
- **MCP Tools & Resources**: Comprehensive set of tools and resources for AI assistants
- **Opt-Out System**: Allow users to opt out of indexing specific courses
- **Robust Database Schema**: Structured SQLite database with 12 tables and views

## Tech Stack

- **Language**: Python 3.12+
- **Database**: SQLite for local data storage
- **Package Manager**: UV (not pip)
- **API Integration**: Canvas API via canvasapi
- **PDF Processing**: pdfplumber
- **MCP Framework**: Model Context Protocol for AI integration
- **Testing**: pytest for unit and integration tests

## Quick Start

### Prerequisites

- Python 3.12+
- [UV](https://astral.sh/uv) package manager
- [Claude Desktop](https://claude.ai/download) with MCP support
- Canvas API access token

### Installation

# Mac:

0. Install `uv` if you haven't already:
```bash
# if you're paranoid about piping to sh, go read the script by copy pasting the URL
curl -LsSf https://astral.sh/uv/install.sh | sh
```

# Mac:

0. Install `uv` if you haven't already:
```bash
uv venv --seed
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

4. Create a `.env` file with your Canvas credentials:

```bash
CANVAS_API_KEY=your_canvas_api_key_here
CANVAS_API_URL=your_canvas_instance_url # e.g., https://canvas.emory.edu
```

5. Initialize the database:

```bash
uv run python init_db.py
```

### Running the Server

1. Open Claude Desktop
2. Go to Settings > Advanced > Edit Configuration
3. (MAC ONLY) Add the following to your `claude_desktop_config.json` file in the `tools` section:
(it is a key under mcpServers)
4. (WINDOWS ONLY) See instructions below

```bash
uv run mcp dev src/canvas_mcp/server.py
```

REPLACE $DIR with the absolute path to the directory where you cloned this repo. (MANDATORY!!!!!)
REPLACE $DIR_uv with the uv path. (MANDATORY!!!!!) you can find it by running
```bash
which uv
```

### Installing to Claude Desktop

1. Open Claude Desktop
2. Go to Settings > Advanced > Edit Configuration
3. Add the following to your `claude_desktop_config.json` file in the `tools` section (under `mcpServers`):

```json
"Canvas MCP": {
  "command": "/path/to/uv",  # Replace with your UV path (run 'which uv')
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
    "/absolute/path/to/Canvas-MCP",  # Replace with your repo path
    "src/canvas_mcp/server.py"
  ]
}
```

## Development

# Windows

We recommend using WSL (Windows Subsystem for Linux) to use this software. Installation instructions can be founder [here](https://learn.microsoft.com/en-us/windows/wsl/install).
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

### Available Commands

```bash
# Run tests
uv run pytest

# Run a specific test
uv run pytest tests/test_server.py

# Run the server
uv run mcp dev src/canvas_mcp/server.py

# Install to Claude
uv run mcp install src/canvas_mcp/server.py

# Code formatting
uv run ruff format .

# Code linting
uv run ruff check .
uv run ruff check . --fix

# Type checking
uv run mypy src
```

## Testing

### Database Schema

The database includes tables for:

- Courses
- Syllabi
- Assignments
- Modules
- Module Items
- Calendar Events
- User Courses (for opt-out)
- Announcements
- And more...

See `docs/db_schema.md` for complete schema details.

## MCP Tools & Resources

### Tools

- `sync_canvas_data`: Synchronize data from Canvas to the local database
- `get_upcoming_deadlines`: Get assignments due in the next X days
- `get_course_list`: Get a list of all available courses
- `get_course_assignments`: Get assignments for a specific course
- `get_course_modules`: Get modules for a specific course
- `get_syllabus`: Get a course syllabus
- `get_course_announcements`: Get announcements for a course
- `get_course_pdf_files`: Get PDF files in a course
- `extract_text_from_course_pdf`: Extract text from a PDF file
- `search_course_content`: Search across all course content
- `opt_out_course`: Opt out of indexing a specific course

### Resources

- `course://{course_id}`: Course information
- `deadlines://{days}`: Upcoming deadlines
- `syllabus://{course_id}`: Course syllabus
- `pdfs://{course_id}`: PDF files in a course
- `assignments://{course_id}`: Course assignments

## Integration Testing

We've successfully tested integration with:

- Canvas API authentication
- Course retrieval with term filtering
- Assignment, module, and announcement synchronization
- PDF file extraction
- Syllabus parsing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

Please follow our coding style guidelines in `CLAUDE.md`.

## License

[MIT License](LICENSE)

## Authors

- Darin Kishore
- Aditya Prakash
- Team members

## Links

- [GitHub Repository](https://github.com/AdityaPrakash-26/Canvas-MCP)
- [Project Kanban](https://github.com/users/AdityaPrakash-26/projects/1)
- [MCP Documentation](https://modelcontextprotocol.io/)
- [Canvas API Documentation](https://canvas.instructure.com/doc/api/)