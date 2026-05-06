# Plan: Content Factory Phase 1 — Foundation And Control Plane

**Spec:** `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md`
**Status:** in_progress

---

## Challenge Log

**Problem:** проект еще не имеет runtime, monorepo-структуры, API, UI и общего lifecycle для контента. Если сразу прыгнуть в pipeline/render часть, следующая работа пойдет без стабильных доменных контрактов.

**Chosen solution:** сначала собрать foundation/control plane: monorepo, local infra, auth, RBAC, asset intake, avatar/content CRUD, review queue skeleton и audit trail.

**Alternatives considered:**
1. Сначала сделать только frontend prototype без API — отвергнуто, потому что такой UI быстро станет throwaway.
2. Сразу интегрироваться с ComfyUI и worker-слоем — отвергнуто, потому что без control plane не будет устойчивых contracts и review lifecycle.

**Why chosen solution is better:** этот этап создает основу, на которую потом навешиваются render jobs, compliance и analytics без повторной перекройки модели данных.

## Problems

| # | Problem | Solution | Status |
|---|---------|----------|--------|
| 1 | Нет repo topology и общих команд | Ввести monorepo c `apps/web`, `apps/api`, `apps/worker`, `packages/contracts`, `infra` и root `Makefile` | completed |
| 2 | Нет модели пользователей и ролей | Ввести invite-only auth, cookie sessions и RBAC | completed |
| 3 | Нет asset ingress и media metadata | Сделать signed upload flow в S3-compatible storage и finalize endpoint | completed |
| 4 | Нет pilot domain model | Ввести сущности `Brand`, `Avatar`, `IdentityPack`, `Asset`, `ContentItem`, `ReviewTask`, `AuditLog` | completed |
| 5 | Нет базового operator UI | Сделать cockpit shell, auth flow, asset/avatar/content screens, review queue | in_progress |

## Phases

### Phase 1: Workspace Bootstrap And Shared Tooling
- **Status:** completed
- **Files:** root `Makefile`, `pnpm-workspace.yaml`, root `package.json`, root `pyproject.toml`, `apps/web/*`, `apps/api/*`, `apps/worker/*`, `packages/contracts/*`, `infra/docker-compose.yml`, `.env.example`, CI config
- **Changes:** создать monorepo-скелет, единые dev/test команды, env validation, health endpoints, DB/Redis/S3 local stack, OpenAPI client generation pipeline, базовое логирование и Sentry hooks
- **TDD:** tests на config parsing, app startup, health/readiness endpoints, contract generation smoke checks
- **Gates:** `make lint-web` ✅ | `make typecheck-web` ✅ | `make test-web` ✅ | `make lint-api` ✅ | `make typecheck-api` ✅ | `make test-api` ✅
- **Impact:** задает структуру всего репозитория и команды, которыми будут пользоваться все последующие этапы
- **Prompt for launch:**
  ```text
  Read this phase plan and the rollout spec.
  Implement only the repo bootstrap, shared tooling, and local infrastructure baseline.
  Start with tests for startup/config/health.
  Do not implement business features yet.
  ```

### Phase 2: Domain Model, Auth, And Control-Plane API
- **Status:** completed
- **Files:** `apps/api/src/content_factory_api/database.py`, `apps/api/src/content_factory_api/modules/*`, `apps/api/alembic/*`, `alembic.ini`, `packages/contracts/*`, API tests
- **Changes:** реализован invite-only auth, cookie sessions, роли, модели и миграция для основных pilot-сущностей, S3-compatible presigned upload initiation/finalization, content lifecycle `draft -> planned -> review -> approved | rework`, review task creation и audit log
- **TDD:** unit/integration tests на auth, RBAC, content transitions, signed upload contract, review transitions, audit entries
- **Gates:** `make lint-api` ✅ | `make typecheck-api` ✅ | `make test-api` ✅ | migration smoke test ✅
- **Impact:** формирует stable domain contracts, от которых зависят frontend и worker-интеграции
- **Prompt for launch:**
  ```text
  Read this phase plan and the rollout spec.
  Implement the pilot domain model and control-plane API.
  Start with auth/RBAC/content-transition tests.
  Keep the lifecycle small and pilot-specific; no multi-tenant abstractions.
  ```

### Phase 3: Cockpit Shell And Review Queue UI
- **Status:** in_progress
- **Files:** `apps/web/src/app/*`, `apps/web/src/app/routes.ts`, `apps/web/src/features/auth/*`, `apps/web/src/features/brands-assets/*`, `apps/web/src/features/avatars/*`, `apps/web/src/features/content/*`, `apps/web/src/features/review/*`, `apps/web/src/features/audit/*`, `apps/web/src/shared/api/*`, `apps/web/src/test/*`, `apps/api/src/content_factory_api/modules/avatars.py`, `apps/api/src/content_factory_api/modules/schemas.py`, `apps/api/tests/test_control_plane.py`
- **Changes:** protected cockpit shell, session bootstrap, hash navigation, asset upload UI через storage proxy, avatar identity screens, content lifecycle, review queue approve/rework flow и audit view реализованы; typed API client подключен к `packages/contracts`; backend дополнен identity-pack list endpoint
- **TDD:** Vitest component/integration tests покрывают auth bootstrap и полный pilot cockpit flow `brand -> asset -> avatar -> identity pack -> content -> plan -> review -> approve -> audit`; browser smoke в реальном браузере все еще pending
- **Gates:** `make lint-web` ✅ | `make typecheck-web` ✅ | `make test-web` ✅ | real-browser smoke scenario pending
- **Impact:** дает первый end-to-end control-plane контур без media generation
- **Prompt for launch:**
  ```text
  Read this phase plan, the rollout spec, and the phase 2 API contracts.
  Implement the cockpit shell and review queue UI.
  Start with route/component tests and finish with smoke E2E.
  Do not add canvas, metrics, or render execution yet.
  ```

## Changelog

| Date | Phase | Changes |
|------|-------|---------|
| 2026-05-06 | planning | Сформирован подробный plan для foundation/control-plane этапа |
| 2026-05-06 | workspace-bootstrap | Реализован bootstrap monorepo, web/api/worker baseline, infra compose и contract generation pipeline |
| 2026-05-06 | domain-control-plane-api | Реализованы SQLAlchemy/Alembic domain model, invite-only auth/RBAC, presigned asset upload, content/review lifecycle, audit logs и обновленные OpenAPI contracts |
| 2026-05-06 | cockpit-ui | Реализован защищенный cockpit UI, typed API client, Vite API/storage proxy, identity-pack list endpoint и Vitest flow через cockpit lifecycle |
