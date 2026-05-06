# Content Factory — Agent Instructions

> Universal agent instructions for this project.
> Before work, read `/Users/tomasrabi/DEV/shared/identity.md`.

## Project Overview

Content Factory is an AI service for building a managed content-production pipeline around digital avatars, short-form video generation, human review, workflow canvas, and performance analytics.

## Stack

- **Type:** custom/minimal bootstrap
- **Framework:** not selected yet
- **Database:** not selected yet
- **Language:** not selected yet
- **Frontend:** likely needed later, not selected yet
- **AI/Workflow:** expected future integration with ComfyUI-like graph/canvas, exact architecture TBD

## Current State

See `.memory/context.md`.

## Business Context

Business context lives in `.business/` and is intentionally gitignored.

When working on business, pilot, product, pricing, audience, marketing, compliance, or strategy tasks:

1. Read `.business/INDEX.md`.
2. Read only the specific `.business/*` files relevant to the task.
3. Do not bulk-load the whole `.business/` folder.
4. Update `.business/` only when the user asks to preserve or change business context.

## Handoffs

See `.memory/sessions/`.

When finishing a phase or preparing for a context switch:

1. Self-audit the work.
2. Write a handoff file to `.memory/sessions/`.
3. Generate or update a snapshot in `.memory/snapshots/`.
4. Update `.memory/context.md`.

## Stack Rules

### General

- Follow existing conventions in the codebase.
- Document architecture decisions in `.memory/decisions/`.
- Write tests for new functionality.
- Keep dependencies minimal.
- Prefer boring, verifiable choices over speculative architecture.

### Project-Specific

- Do not choose a technical stack silently for major implementation work; record the decision in `.memory/decisions/`.
- Treat compliance as first-class for regulated categories such as vape/nicotine-related content.
- Keep ComfyUI integration as a workflow/render backend candidate, not something to rewrite from scratch unless explicitly decided.
- Use human-in-the-loop approval gates for generated content until product requirements say otherwise.
