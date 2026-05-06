# ADR: Bootstrap Content Factory As Custom/Minimal

## Context

The project folder existed with business context but no application code, package manifest, runtime, database, or framework markers.

The product concept is an AI content factory with digital avatars, human-in-the-loop review, workflow canvas, analytics, and likely ComfyUI integration. The implementation stack has not been selected.

## Decision

Bootstrap the project as `custom/minimal` and add agent infrastructure without scaffolding application code.

## Rationale

- Avoids prematurely committing to Next.js, FastAPI, LangGraph, or another stack.
- Gives agents a stable place for context, decisions, handoffs, and snapshots.
- Preserves the business-context work already captured in `.business/`.
- Keeps the next step focused on PRD/pilot definition before technical implementation.

## Consequences

- Runtime setup is intentionally incomplete.
- Future stack selection must be recorded as a new ADR.
- Empty source/test directories exist for future implementation, but no code is created yet.
