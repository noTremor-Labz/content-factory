# Handoff: Content Factory Phase 2 — Worker Orchestration

**Date:** 2026-05-07
**Agent:** Codex
**Phase:** implementation / phase-2-worker-orchestration

---

## Goal
Продолжить `Phase 2` после render contract layer и добавить минимальный, проверяемый server-side execution lifecycle: enqueue render jobs, process queued attempts, persist provider responses, enforce retry budget, and keep worker processing idempotent for terminal jobs.

## Approach
Не подключался реальный ComfyUI adapter в этом slice. Сначала добавлен устойчивый orchestration core в worker: typed executor protocol, deterministic attempt transitions, retry creation, terminal-state guard и Dramatiq actor wrapper. API теперь после создания `RenderJob`/первого `JobAttempt` отправляет сообщение в очередь `render-jobs`. `JobAttempt` получил `response_payload`, чтобы будущие provider adapters и export pipeline могли сохранять outputs без изменения базового lifecycle.

## Done
- [x] Добавлен `content_factory_worker.orchestration.process_render_job`
- [x] Добавлен typed `RenderExecutor` contract и `RenderExecutionResult`
- [x] Реализован lifecycle `queued -> running -> succeeded`
- [x] Реализован failure path с `retry_budget`
- [x] Provider exceptions переводятся в failed attempts вместо зависания job в `running`
- [x] При доступном бюджете создается следующая queued `JobAttempt`
- [x] При исчерпанном бюджете `RenderJob` становится `failed`
- [x] Терминальные jobs (`succeeded`, `failed`, `cancelled`) пропускаются idempotently
- [x] Добавлен Dramatiq actor `process_render_job_message`
- [x] `POST /api/render-jobs` теперь enqueue-ит сообщение после commit
- [x] Добавлена колонка `job_attempts.response_payload`
- [x] Обновлены OpenAPI и generated TypeScript contracts
- [x] Обновлены `.memory/context.md`, phase-2 plan и master rollout changelog

## Key Files
- `apps/worker/src/content_factory_worker/orchestration.py`
- `apps/worker/src/content_factory_worker/jobs/render.py`
- `apps/worker/src/content_factory_worker/queue.py`
- `apps/worker/src/content_factory_worker/main.py`
- `apps/worker/tests/test_render_orchestration.py`
- `apps/api/src/content_factory_api/modules/render.py`
- `apps/api/src/content_factory_api/modules/models.py`
- `apps/api/src/content_factory_api/modules/schemas.py`
- `apps/api/alembic/versions/20260506_0003_render_attempt_response_payload.py`
- `packages/contracts/openapi/content-factory.openapi.json`
- `packages/contracts/src/generated/api.ts`

## Verification
- [x] `make lint-api`
- [x] `make typecheck-api`
- [x] `make test-api`
- [x] `make generate-contracts`
- [x] `make lint-web`
- [x] `make typecheck-web`
- [x] `make test-web`

## Result
- Phase 2 теперь имеет реальный server-side async lifecycle поверх `RenderJob`/`JobAttempt`.
- Retry behavior покрыт worker tests: success, retry queueing, budget exhaustion, terminal idempotency.
- Provider response storage готов для ComfyUI adapter и export packaging.

## Remaining
- Real ComfyUI execution adapter вместо `UnconfiguredRenderExecutor`.
- SSE/live status endpoint и cockpit job detail/queue UI.
- Operator actions `retry`, `cancel`, `requeue`.
- Packaging/export pipeline через FFmpeg.

## Next Step
Перейти к `Phase 2 / Provider Adapter And Live Status`:
- добавить mock/testable ComfyUI execution adapter interface;
- подключить реальный/локальный provider config;
- добавить SSE endpoint для job status stream;
- добавить cockpit queue/job detail UI на generated contracts.

## Snapshot
- **Path:** `.memory/snapshots/2026-05-07-phase-2-worker-orchestration.md`
- **Generated:** 2026-05-07
- **Scope:** worker orchestration, retries, Dramatiq enqueue, attempt response payload

## Context Note
> Если контекст очистится, сначала прочитай этот handoff, затем snapshot, затем `.memory/context.md`, затем phase-2 plan.
