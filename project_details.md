
# Project Proposal

### 1. What Is the Project? 
We are creating an **MCP server** for Canvas. The MCP server provides a standardized way to expose functions and resources (like syllabi, assignment info, modules) that an AI model can call. The end result: 
- An AI assistant (Claude) can query and update the server to retrieve key information about courses, upcoming assignments, and other relevant data.

### 2. Problem It Solves
Students often find it **time-consuming** to navigate Canvas for upcoming deadlines, due dates, or class materials. Our project automates these lookups, letting an AI handle routine queries like “What’s due this week?” or “Show me lecture notes for class X.”

### 3. Intended Users
- **University students** who use Canvas and have access to an AI model (like Claude) that can interact with an MCP server.

### 4. Tech Stack
- **Language**: Python (with recommended tools/libraries such as `uv` for working with MCP).
- **Platform**: Runs locally (STDIO/JSON-RPC).
- **Database**: SQLite for storing the knowledge graph and internal calendar data.
- **Third-Party Tools**: 
  - **Canvas API** for retrieving assignment/module data. 
  - **Claude Desktop** (or any environment where Claude can connect to the MCP server).

### 5. Functionality Upon Completion
- **Core Features**:
  1. Parse each course’s syllabus to extract assignment due dates, exam dates, and other relevant info.
  2. Store all data in a structured database and maintain an internal calendar.
  3. Provide an **LLM-friendly** schema (MCP-compliant) for easy retrieval by Claude.
  4. Allow Claude to answer queries like “What’s due this week?” or “Show me lecture notes for tomorrow’s class.”
  5. Optionally pull assignment and module data directly from Canvas.
  6. Potential expansions: 
     - Assist with exam prep,
     - Track performance or grade goals,
     - Provide targeted study topics.

### 6. Handling Time Variations
- **If the project takes **more** time** than expected: 
  - We’ll reduce scope to ensure P1 tasks are completed (database, syllabus parsing, LLM schema).
- **If the project takes **less** time** than expected: 
  - We’ll implement additional features (e.g., “notes from recordings,” direct assignment feedback, more advanced analytics).

---

## Project Roadmap

Below is our high-level roadmap with tasks, priorities, and time estimates.
- P0 are the tasks that MUST get done for the project to be successful. We will complete all of our P1 tasks.
- P1 are the tasks that are important but not critical. We will get at least half of our P2 tasks done.
- P2 are the tasks that would be nice to complete but are not high-priority. We will only get substantial P2 work done if we are unexpectedly ahead of schedule.


|                        **Work Item**                        | **Priority** | **Estimated Duration** | **Notes**                                                                                                                   |
| :---------------------------------------------------------: | :----------: | :--------------------: | :-------------------------------------------------------------------------------------------------------------------------- |
|       **1. Getting started: Create a new MCP server**       |      P0      |         1 day          | - Create a new Python app that can setup an MCP server and achieve connection with an LLM (Claude).                         |
|       **2. Set up SQLite Database & Knowledge Graph**       |      P0      |        3–5 days        | - Initialize SQLite<br>- Define schema for each course’s knowledge graph<br>- Must handle all group members’ courses.       |
| **3. Parse Course Syllabi & Internal Calendar Integration** |      P0      |        4–6 days        | - Write parser for assignment/exam info<br>- Store due dates in an internal calendar (in the DB).                           |
|    **4. Integrate Assignment & Module Info from Canvas**    |      P0      |        4–6 days        | - Pull data via Canvas API<br>- Sync with DB<br>- Handle authentication, possible rate limits, etc.                         |
|                  **5. Assignment Helping**                  |      P0      |        4–6 days        | - Claude will be able to autonomously complete every assignment in our group member's computer science classes              |
|       **6. “Opt-Out” Indexing for Specific Classes**        |      P0      |        1–2 days        | - Let user skip indexing certain courses. (In case the course does not encourage AI usage)                                  |
|                 **7. Fetch Lecture Notes**                  |      P1      |        1–2 days        | - Retrived posted notes and structure them for clarity.                                                                     |
|         **8. Generate notes from video transcript**         |      P1      |        3–5 days        | - If posted notes are unavailable, fetch lecture recording (if available) and create notes from the transcript.             |
|                     **9. Study Ahead**                      |      P1      |        2–4 days        | - If available, retrieve the next day's slides and materials and help the user to study ahead.                              |
|                      **10. Exam Prep**                      |      P1      |        4–6 days        | - Help the student prepare for an upcoming exam based on the material taught so far.                                        |
|   **11. Analyze Weakness and generate remedial content**    |      P2      |        2–4 days        | - Analyze mistakes, instructor/TA comments on assignments and quizzes to identify weak areas.<br> - Create remedy material. |
|                  **12. Smart Flashcards**                   |      P2      |        3–5 days        | - Auto-generate spaced repetition flashcards from lecture notes, readings, and previous mistakes.                           |

