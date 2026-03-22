*This is a submission for the [Notion MCP Challenge](https://dev.to/challenges/notion-2026-03-04)*

# Freelance OS Copilot: A Notion MCP-Powered Operations System for Freelancers

## What I Built

I built **Freelance OS Copilot**, a product that turns a freelancer's Notion workspace into an AI operations system.

Instead of treating Notion like passive storage, the app helps answer practical questions like:

- What needs attention today?
- Which project is slipping?
- What should I tell the client?
- What should I do next?

The product combines:

- a dashboard with urgent and at-risk project signals
- copilot quick actions for daily priorities and weekly reviews
- write-back actions for project creation, logging hours, and saving follow-up notes
- **Project Rescue Mode**, the signature workflow

Project Rescue Mode is the standout feature. When a project is risky, the app does not just flag it visually. It:

- explains why the project is risky
- proposes an internal recovery plan
- drafts a client-safe update
- highlights the immediate next move

That turns the app from “chat with your data” into a workflow-focused operating layer for freelancers.

## Video Demo

Video walkthrough: `<ADD_VIDEO_LINK_HERE>`

## Show us the code

Code repository: [https://github.com/VeraStorozhenko/freelance-manager](https://github.com/VeraStorozhenko/freelance-manager)

## How I Used Notion MCP

This project uses the **official Notion MCP server** as part of the live workspace layer.

The app includes an MCP connect flow with OAuth + PKCE, so the user can connect their Notion workspace and let the copilot work with live MCP tools instead of only local app context.

That matters because it makes Notion an active operational memory layer, not just a storage backend.

When MCP is connected, the product can:

- use live workspace context during copilot interactions
- stay aligned with the user's current Notion state
- support a more authentic AI workflow inside the product

I used MCP in a way that supports the core product thesis:

**Detect -> Explain -> Recover -> Write Back**

That shows up most clearly in **Project Rescue Mode**, where the app uses workspace context to help recover risky work before it slips further.

## Tech Stack

- **Frontend:** React + Vite
- **Backend:** FastAPI
- **AI layer:** Gemini
- **Workspace layer:** Notion API + official Notion MCP server
- **Testing:** Python `unittest`
- **Styling:** custom CSS

## Why I think this stands out

I did not want to build another generic “chat with Notion” experience.

I wanted to build a workflow product with a clear operational point of view.

Freelance OS Copilot is built around:

- detecting project risk
- explaining what is going wrong
- helping recover the work
- supporting direct action in the same interface

That is the difference between an AI wrapper and a usable system.
