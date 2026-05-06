# Snapshot: Content Factory Phase 1 Bootstrap

**Date:** 2026-05-06
**Scope:** implementation baseline for `Phase 1 / Workspace Bootstrap And Shared Tooling`

## Files Added
- `pnpm-workspace.yaml`, `package.json`, `pyproject.toml`, `Makefile`
- `apps/web/*`
- `apps/api/src/content_factory_api/*`
- `apps/api/tests/*`
- `apps/worker/src/content_factory_worker/*`
- `apps/worker/tests/*`
- `packages/contracts/*`
- `infra/docker-compose.yml`

## Working Baseline
- Web app renders a bootstrap cockpit shell with validated Vite env defaults.
- API app validates config and serves root/meta/live/ready endpoints.
- Worker validates config and wires a `Dramatiq` broker baseline.
- OpenAPI schema exports into `packages/contracts/openapi/content-factory.openapi.json`.
- Generated TypeScript contract types live in `packages/contracts/src/generated/api.ts`.
- Local infra syntax is valid for `Postgres`, `Redis`, and `MinIO`.

## Verified Commands
- `make install-python BOOTSTRAP_PYTHON=/path/to/python3.12`
- `make lint-web`
- `make typecheck-web`
- `make test-web`
- `make lint-api`
- `make typecheck-api`
- `make test-api`
- `make generate-contracts`
- `pnpm --dir packages/contracts typecheck`
- `docker compose -f infra/docker-compose.yml config`

## Next Implementation Slice
- `Phase 1 / Domain Model, Auth, And Control-Plane API`
- Target areas:
  - `apps/api/app/modules/*` equivalent structure to be introduced
  - auth and session cookies
  - pilot entities and lifecycle transitions
  - upload contract endpoints
