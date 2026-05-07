# Cross-Agent Handoff: Content Factory — Phase 2 Publish Package Export

**Date:** 2026-05-07
**From Agent:** Codex
**To Agent:** any
**Mode:** Bulletproof M slice

---

## Mission Status

### What was the goal?
Continue Phase 2 after provider/live-status by closing the manual publishing loop: `approved content + succeeded render job -> publish package export`.

### What got done?
- [x] Added slice research and plan:
  - `.memory/sessions/research/2026-05-07-publish-package-export-slice.md`
  - `.memory/sessions/plans/2026-05-07-content-factory-phase-2-publish-package-export-slice.md`
- [x] Added `PublishPackage` domain status, SQLAlchemy model, Alembic migration, and OpenAPI schemas.
- [x] Added publish package API:
  - `POST /api/publish-packages`
  - `GET /api/publish-packages`
  - `GET /api/publish-packages/{package_id}`
  - `GET /api/publish-packages/{package_id}/download`
- [x] Enforced export gates:
  - render job must be `succeeded`;
  - content item must be `approved`;
  - package creation is idempotent per render job.
- [x] Added worker packaging:
  - ZIP manifest bundle with `manifest.json`, `title.txt`, `caption.txt`, `hashtags.txt`, `provider-output.json`;
  - S3-compatible upload through worker settings;
  - explicit failed state for missing render outputs;
  - `publish-packages` Dramatiq actor and enqueue helper.
- [x] Added cockpit Export route:
  - lists eligible succeeded/approved renders;
  - queues publish packages;
  - shows package status/object key/errors;
  - fetches signed download URL for ready packages.
- [x] Regenerated OpenAPI and TypeScript contracts.
- [x] Migrated the running local dev Postgres through `20260507_0004_publish_packages`.
- [x] Updated `.memory/context.md`, parent Phase 2 plan, master rollout plan, and generated snapshot.

### What's blocked?
- [ ] Nothing blocks the completed package export slice.

### What's left?
- [ ] Operator retry/cancel/requeue actions for render jobs and package jobs.
- [ ] Actual FFmpeg binary media normalization/remuxing inside the package worker. The local machine currently has no `ffmpeg` binary.
- [ ] Richer ComfyUI output mapping into package artifacts.
- [ ] Compliance engine, metrics, and economics remain Phase 3.

---

## Current State

### Branch
`codex/content-factory-phase-1-control-plane-ui`

### Last Commit
`cf28c2c`

### Key Files Modified

| File | Change | Why |
|------|--------|-----|
| `apps/api/src/content_factory_api/modules/exports.py` | New publish package API | Operator package creation/list/detail/download |
| `apps/api/src/content_factory_api/modules/models.py` | Added `PublishPackage` | Persist package lifecycle |
| `apps/api/alembic/versions/20260507_0004_publish_packages.py` | New migration | Add `publish_packages` table |
| `apps/worker/src/content_factory_worker/packaging.py` | New package orchestration and ZIP builder | Build manifest bundle from successful render attempt |
| `apps/worker/src/content_factory_worker/jobs/packaging.py` | New Dramatiq actor and S3 storage | Async package processing |
| `apps/web/src/features/export/ExportPanel.tsx` | New Export UI | Operator package flow |
| `apps/web/src/app/App.tsx` | Fetches packages and renders Export route | Wire cockpit data |
| `packages/contracts/*` | Regenerated | Keep API/web types aligned |

### Tests Status
- `make generate-contracts` ✅
- `make lint-api` ✅
- `make typecheck-api` ✅
- `make test-api` ✅
- `make lint-web` ✅
- `make typecheck-web` ✅
- `make test-web` ✅
- `PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173 pnpm --dir apps/web test:e2e` ✅

### Browser Smoke Note
The first Playwright run failed with `Internal Server Error` after brand creation because the live dev API had reloaded new code while the local Postgres schema had not yet been migrated. Running `make migrate-api` applied `20260507_0004_publish_packages`; the repeated smoke passed.

---

## Architecture Decisions Made

1. **Decision:** package export is worker-driven, not synchronous in the API.
   **Why:** media/package generation belongs with existing async render processing.
   **Consequence:** API creates queued packages and the worker moves them to ready/failed.

2. **Decision:** first package format is a deterministic ZIP manifest bundle.
   **Why:** `ffmpeg` is not installed locally, and tests should not depend on an external binary.
   **Consequence:** binary media normalization remains a contained enhancement inside `ZipPublishPackager`/future FFmpeg packager.

3. **Decision:** one publish package per render job.
   **Why:** keeps idempotency simple for the pilot and avoids duplicate active exports.
   **Consequence:** a failed package currently requires a new render job or future operator retry/requeue action.

---

## Context for Next Agent

### Read First
1. `.memory/context.md`
2. `.memory/sessions/2026-05-07-codex-phase-2-publish-package-export.md`
3. `.memory/snapshots/2026-05-07-phase-2-publish-package-export.md`
4. `.memory/sessions/plans/2026-05-06-content-factory-phase-2-production-pipeline.md`
5. `.memory/sessions/plans/2026-05-07-content-factory-phase-2-publish-package-export-slice.md`

### Recommended Next Step
Implement operator retry/cancel/requeue actions, starting with render jobs and then package jobs. Keep the actions role-gated and idempotent; start with API/worker tests for state transitions.

### Environment Notes
- Local dev stack is still intended to run on:
  - frontend `http://127.0.0.1:5173/`;
  - API `http://localhost:8000`;
  - Postgres/Redis/MinIO `5432`/`6379`/`9000`/`9001`.
- The local dev database has been migrated to include `publish_packages`.
- Python gates use `.venv/bin/python`; web gates use `pnpm --dir apps/web`.

## Snapshot
- `.memory/snapshots/2026-05-07-phase-2-publish-package-export.md`
