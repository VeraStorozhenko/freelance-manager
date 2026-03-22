# Submission Draft

## Title

Freelance OS Copilot: A Notion MCP-Powered Operations System for Freelancers

## One-line pitch

Freelance OS Copilot uses the official Notion MCP server to turn a freelancer's Notion workspace into an AI operations system that detects project risk, builds recovery plans, drafts client updates, and supports direct write-back actions.

## Problem

Freelancers often already keep work in Notion, but the workspace still behaves mostly like storage.

The hard part is not where the information lives.  
The hard part is knowing:

- what needs attention today
- which project is slipping
- what to tell the client
- what action to take next

That is usually where time, confidence, and delivery quality are lost.

## Solution

Freelance OS Copilot turns Notion into an operational workspace instead of a passive database.

The product combines:

- project health dashboard
- deadline and budget risk signals
- copilot quick actions
- weekly review generation
- write-back actions for project creation, hour logging, and follow-up notes
- **Project Rescue Mode**, the signature workflow

## Signature feature: Project Rescue Mode

Project Rescue Mode is the strongest product workflow in the app.

When a project is risky, the app does not just flag it visually.
It creates a structured intervention:

- explains why the project is risky
- proposes an internal recovery plan
- drafts a client-safe update
- highlights the immediate next move

This turns the app from “chat with your data” into an actual decision-support tool.

## Why Notion MCP matters

This project now uses the **official Notion MCP server** as part of the live workspace layer.

That matters because it means the copilot is not only working on static local context.  
When connected, it can use official MCP tools against the user's real Notion workspace.

In this project, Notion MCP is important for two reasons:

1. It makes the workspace live and agent-friendly.
2. It keeps the product aligned with the idea that Notion is operational memory, not just storage.

## Technical highlights

- FastAPI backend with modular services and typed schemas
- React + Vite frontend
- official Notion MCP OAuth connect flow with PKCE
- MCP session handling and tool transport
- Gemini-backed copilot with MCP-aware tool loops
- risk analysis, weekly review, and rescue planning workflows
- demo mode fallback for reliable judging and local iteration
- automated backend tests and verified frontend production build

## Demo flow

1. Open the dashboard and show urgent and at-risk projects.
2. Show that the official Notion MCP connection is active.
3. Ask: `What needs attention today?`
4. Open **Project Rescue Mode** for the riskiest project.
5. Show the recovery plan and client-safe update.
6. Save a follow-up note or log hours.
7. Export the weekly review.

## What makes it practical

This is not a generic chatbot attached to Notion.

It is a workflow-focused operations layer for freelancers:

- it helps interpret project reality
- it highlights delivery risk
- it proposes recovery actions
- it supports acting immediately inside the same product

## Why it stands out

The most important difference is that the product has a clear operational point of view.

It is not built around “ask AI anything”.
It is built around:

**Detect -> Explain -> Recover -> Write Back**

That product logic is what makes Freelance OS Copilot feel more like a real system than a thin AI wrapper.
