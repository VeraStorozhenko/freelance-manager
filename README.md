# Freelance OS Copilot

Freelance OS Copilot is a freelancer operations dashboard built with React and FastAPI. It combines project health signals, copilot workflows, direct write-back actions, and support for the official Notion MCP server.

## Core workflows

- Dashboard with urgent and at-risk projects
- Project Rescue Mode for recovery planning and client-safe updates
- Copilot prompts for daily focus and weekly review
- Write-back actions for creating projects, logging hours, and saving follow-up notes
- Optional Notion MCP connection for live MCP-powered workspace access

## Stack

- Frontend: React + Vite
- Backend: FastAPI
- AI: Gemini
- Workspace: Notion API + official Notion MCP server
- Tests: Python `unittest`

## Run locally

Backend:

```bash
./.venv/bin/uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Verify

Backend tests:

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

Frontend build:

```bash
cd frontend
npm run build
```

## Environment

Expected `.env` keys:

- `NOTION_TOKEN`
- `NOTION_DATABASE_ID`
- `GEMINI_API_KEY`
- `FRONTEND_URL=http://localhost:5173`
- `NOTION_MCP_URL` optional, defaults to `https://mcp.notion.com/mcp`
- `DEMO_MODE=true` optional

## Files

- [`app/agent.py`](/Users/vera/PycharmProjects/freelance-manager/app/agent.py)
- [`app/mcp.py`](/Users/vera/PycharmProjects/freelance-manager/app/mcp.py)
- [`app/notion_client.py`](/Users/vera/PycharmProjects/freelance-manager/app/notion_client.py)
- [`frontend/src/App.jsx`](/Users/vera/PycharmProjects/freelance-manager/frontend/src/App.jsx)
- [`SUBMISSION.md`](/Users/vera/PycharmProjects/freelance-manager/SUBMISSION.md)
- [`DEVTO_POST.md`](/Users/vera/PycharmProjects/freelance-manager/DEVTO_POST.md)
- [`DEMO_SCRIPT.md`](/Users/vera/PycharmProjects/freelance-manager/DEMO_SCRIPT.md)
