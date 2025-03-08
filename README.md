# Canvas AI Assistant with MCP

## Overview

This repository contains our project for building a **Model Context Protocol (MCP) server** that integrates with the **Canvas** learning management system (LMS). The goal is to provide an AI-driven assistant (e.g., Claude) with structured access to course information—assignments, due dates, lecture notes—so that it can help students stay organized and succeed academically.

---

## Project Proposal

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

| **Work Item**                                                                               | **Priority** | **Estimated Duration** | **Notes**                                                                                                                  |
|:-------------------------------------------------------------------------------------------:|:------------:|:----------------------:|:---------------------------------------------------------------------------------------------------------------------------|
| **1. Set up SQLite Database & Knowledge Graph**                                             | P1           | 2–3 days               | - Initialize SQLite<br>- Define schema for each course’s knowledge graph<br>- Must handle all group members’ courses.      |
| **2. Parse Course Syllabi & Internal Calendar Integration**                                 | P1           | 4–6 days               | - Write parser for assignment/exam info<br>- Store due dates in an internal calendar (in the DB).                          |
| **3. Design LLM-Friendly Schema (MCP Compliance)**                                          | P1           | 4–6 days               | - Key deliverable<br>- Must follow [Model Context Protocol specs](https://modelcontextprotocol.io/introduction).           |
| **4. Universal Course Info Handling**                                                       | P1           | 2–3 days               | - Ensure robust parsing for various syllabus formats<br>- Validate with real examples from group members’ classes.         |
| **5. “Opt-Out” Indexing for Specific Classes**                                              | P2           | 1–2 days               | - Let user skip indexing certain courses<br>- Minimal overhead to maintain.                                               |
| **6. Integrate Assignment & Module Info from Canvas**                                       | P2           | 4–6 days               | - Pull data via Canvas API<br>- Sync with DB<br>- Handle authentication, possible rate limits, etc.                        |

**Note**: 
- **P1** tasks are **must-haves**; they ensure the project meets the core vision.  
- **P2** tasks are important but not strictly required for the minimal viable product. We aim to complete at least half of them if time allows.

---

## Team Charter

(We will copy this info into our README for clarity, though the assignment says it may just be appended.)

### Communication Norms
1. **Team Meetings**: We plan to meet **twice a week** via Zoom/Google Meet (e.g., Mondays and Thursdays at 6 PM).
2. **Communication**: We use a **Slack channel** for day-to-day updates.  
3. **Response Time**: Team members strive to respond to Slack messages within **24 hours**.

### Operating Guidelines
1. **Decision-Making**: We decide by **majority vote** if consensus can’t be reached.  
2. **Performance Expectations**: Everyone should complete tasks on time and with acceptable quality.  
3. **Cooperation/Attitudes**: We maintain a positive environment, help each other with blocking issues.  
4. **Meeting Attendance**: Everyone attends or notifies the team if they must miss. Punctuality is expected.  
5. **Workload Distribution**: We will monitor tasks on our Kanban board to avoid one or two people doing the majority.  
6. **Procrastination Handling**: We’ll set internal deadlines 1–2 days before the actual due date to buffer.  

### Conflict Management
1. **Resolving Differences**: We discuss openly in Slack or in a meeting. If unresolved, we escalate to the instructor.  
2. **Non-Responsive Members**: We attempt direct contact. If still unresponsive, we reassign tasks and inform the instructor.  
3. **Unexpected Issues**: If someone faces an emergency, the rest of the team divides their tasks.  

### Outside Commitments
- We have typical student commitments, but no known major conflicts. If they arise, we’ll let the team know ASAP.

**Team Agreement**:  
All team members have read and agree to these norms.  
- *Aditya Prakash*  
- *Darin Kishore*    
- *Xiaofei Wang*
- *Zechery Chou*

---

## Repository & Kanban

- This **public GitHub repository** contains our code, documentation, and issues/tasks.  
- We maintain a **Kanban board** under the “Projects” tab with tasks from our roadmap for the first sprint.  

**Link to the Repo**: (https://github.com/AdityaPrakash-26/Canvas-MCP)
**Link to the Kanban**: (https://github.com/users/AdityaPrakash-26/projects/1)

---

## License
