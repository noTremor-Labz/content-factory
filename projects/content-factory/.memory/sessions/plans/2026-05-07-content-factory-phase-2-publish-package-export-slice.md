# Plan: Phase 2 Publish Package Export Slice

**Spec:** `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md`
**Parent plan:** `.memory/sessions/plans/2026-05-06-content-factory-phase-2-production-pipeline.md`
**Research:** `.memory/sessions/research/2026-05-07-publish-package-export-slice.md`
**Status:** completed

## Acceptance Criteria

- [x] API can create a publish package request for a succeeded render job whose content item is approved.
- [x] API rejects package creation when render did not succeed or content is not approved.
- [x] Package creation is idempotent for an existing queued/running/ready package for the same render job.
- [x] Worker can turn the package into a ready ZIP manifest bundle using the successful attempt payload.
- [x] Worker marks package failed with a useful error when required render outputs are missing.
- [x] API exposes package list/detail and a signed download target for ready packages.
- [x] Cockpit exposes an Export route to prepare and inspect publish packages.
- [x] OpenAPI and TypeScript contracts are regenerated.

## Verification

- `make generate-contracts` ✅
- `make lint-api` ✅
- `make typecheck-api` ✅
- `make test-api` ✅
- `make lint-web` ✅
- `make typecheck-web` ✅
- `make test-web` ✅
- `PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173 pnpm --dir apps/web test:e2e` ✅

## Notes

- Local dev Postgres was migrated with `make migrate-api` after the first browser smoke exposed an expected schema drift: the running API had new code, but the dev database did not yet have `publish_packages`.
- `ffmpeg` is not installed in the current local environment. This slice creates the durable package/export contract and ZIP manifest bundle; binary media normalization can be added inside the same worker packager when runtime availability is decided.

## Challenge Loop

### 1. Does this solve the problem?

Yes. The missing Phase 2 loop is `approved content + succeeded render -> publish package for manual publishing`. This plan adds the package record, async worker processing, download contract, and operator UI.

### 2. Is this the most efficient solution?

Alternatives:
- API synchronous package build: smaller, but wrong pressure point for media work.
- Full FFmpeg binary integration now: closer to final target, but the binary is absent locally and would make gates brittle.
- Worker-driven manifest ZIP: minimum durable slice that completes operator export flow and leaves a clear FFmpeg insertion point.

Chosen path is best because it reuses existing worker/S3/provider patterns and does not invent autoposting or a heavy orchestration service.

### 3. Is there code for code's sake?

No package retry/cancel UI, no direct social publishing, no canvas changes, no broad storage abstraction beyond the packager/storage protocol needed for tests and S3.

## Implementation Steps

1. **Backend contracts and model**
   - Add `PublishPackageStatus`.
   - Add `PublishPackage` model and Alembic migration.
   - Add schemas for create/read/list/download.

2. **API export route**
   - Add `POST /api/publish-packages`.
   - Add `GET /api/publish-packages`, `GET /api/publish-packages/{id}`.
   - Add `GET /api/publish-packages/{id}/download`.
   - Gate by approved content and succeeded render job.
   - Write audit logs and enqueue package job.

3. **Worker packaging**
   - Add packaging orchestration with a packager protocol.
   - Add ZIP/manifest package builder.
   - Add Dramatiq actor and queue helper.
   - Register packaging job import in worker bootstrap.

4. **Frontend**
   - Add typed client methods and `PublishPackage` types.
   - Add `ExportPanel` and route.
   - Fetch packages with cockpit data.
   - Let operators create package from eligible succeeded jobs and fetch download link for ready packages.

5. **Verification**
   - API tests for creation, gates, download target.
   - Worker tests for ready package and missing output failure.
   - Web test for export route flow.
   - Run contracts generation and gates.

## Impact Analysis Targets

- Render job creation/streaming should remain unchanged.
- Review approval remains mandatory before export.
- Existing smoke flow should still work without requiring a publish package.
- Package processing must be idempotent enough not to duplicate active packages for one render job.
