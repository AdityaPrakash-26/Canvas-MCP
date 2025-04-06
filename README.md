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

1. Clone the repository:

```bash
git clone https://github.com/AdityaPrakash-26/Canvas-MCP.git
cd Canvas-MCP
```

2. Install UV if you haven't already:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install dependencies:

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

To run the MCP server in development mode:

```bash
uv run mcp dev src/canvas_mcp/server.py
```

This will start the MCP Inspector at http://127.0.0.1:6274, which you can use to test the server functionality.

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

### Project Structure

```
Canvas-MCP/
├── data/                   # Database files
├── docs/                   # Documentation files
│   └── db_schema.md        # Database schema documentation
├── src/                    # Source code
│   └── canvas_mcp/         # Main package
│       ├── utils/          # Utility modules
│       │   └── pdf_extractor.py # PDF handling utilities
│       ├── canvas_client.py # Canvas API client
│       └── server.py       # MCP server implementation
├── tests/                  # Test suite
│   ├── test_canvas_client.py
│   ├── test_init_db.py
│   └── test_server.py
├── .env                    # Environment variables (create from template)
├── init_db.py              # Database initialization script
├── pyproject.toml          # Project configuration
└── README.md               # Project documentation
```

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