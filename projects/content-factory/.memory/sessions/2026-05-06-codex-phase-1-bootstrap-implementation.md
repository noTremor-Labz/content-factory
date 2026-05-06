# Handoff: Content Factory Phase 1 — Workspace Bootstrap

**Date:** 2026-05-06
**Agent:** Codex
**Phase:** implementation / phase-1-bootstrap

---

## Goal
Поднять первый рабочий срез `Phase 1`, чтобы у проекта появилась проверяемая техническая основа: monorepo topology, web/api/worker baseline, local infra, health endpoints и pipeline генерации API contracts.

## Approach
Вместо попытки закрыть весь `Phase 1` за один проход реализован первый завершенный slice из плана: `Workspace Bootstrap And Shared Tooling`. Это сохраняет scope контролируемым и дает основу для следующего среза с auth/domain API.

## Done
- [x] Созданы `pnpm-workspace.yaml`, root `package.json`, root `pyproject.toml`, `Makefile`
- [x] Поднят `apps/web` на `React 19 + Vite + TypeScript + Vitest + ESLint`
- [x] Поднят `apps/api` на `FastAPI + pydantic-settings` с config validation и endpoints `/`, `/api/meta`, `/health/live`, `/health/ready`
- [x] Поднят `apps/worker` bootstrap на `Dramatiq` с config validation и broker wiring
- [x] Добавлен `packages/contracts` и generation flow через OpenAPI -> `openapi-typescript`
- [x] Добавлен `infra/docker-compose.yml` для `Postgres`, `Redis`, `MinIO`
- [x] Обновлены `.env.example`, `.gitignore`, `README.md`
- [x] Добавлены и пройдены тесты для web/api/worker bootstrap
- [ ] Auth/RBAC
- [ ] Pilot domain entities and migrations
- [ ] Signed upload initiation/finalization
- [ ] Review queue and audit trail

## Current Problem / Next Step
Следующий шаг — продолжить `Phase 1` на подэтапе `Domain Model, Auth, And Control-Plane API` из `.memory/sessions/plans/2026-05-06-content-factory-phase-1-control-plane.md`.

## Key Files
- `Makefile` — единые команды установки, проверки и генерации contracts
- `pyproject.toml` — Python baseline и tool configuration
- `apps/web/*` — web bootstrap и тесты
- `apps/api/src/content_factory_api/*` — FastAPI bootstrap
- `apps/worker/src/content_factory_worker/*` — worker bootstrap
- `packages/contracts/*` — generated OpenAPI contracts
- `infra/docker-compose.yml` — local data plane baseline

## Verification
- [x] `make lint-web`
- [x] `make typecheck-web`
- [x] `make test-web`
- [x] `make lint-api`
- [x] `make typecheck-api`
- [x] `make test-api`
- [x] `make generate-contracts`
- [x] `pnpm --dir packages/contracts typecheck`
- [x] `docker compose -f infra/docker-compose.yml config`

## Snapshot
- **Path:** `.memory/snapshots/2026-05-06-phase-1-bootstrap.md`
- **Generated:** 2026-05-06
- **Scope:** workspace bootstrap, health API, worker baseline, infra compose, contract generation

## Context Note
> Если контекст очистится, сначала прочитай этот handoff, затем snapshot, затем phase-1 plan и spec.
