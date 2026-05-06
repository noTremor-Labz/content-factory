# Research: Content Factory Pilot Architecture & Rollout

**Date:** 2026-05-06
**Task size:** L
**Agent:** Codex

---

## Current Architecture
Проект находится на pre-code стадии: в репозитории есть бизнес-контекст, bootstrap-память проекта, базовые agent-инструкции и ADR о том, что стек пока не выбран. Исходного кода, runtime, базы данных, CI и инфраструктурных сервисов пока нет.

С бизнесовой стороны уже зафиксированы важные требования:
- пилот для Inflave и смежных брендов;
- один основной human-like аватар;
- manual publish для Reels и YouTube Shorts;
- human-in-the-loop review обязателен;
- compliance-first обязателен уже в MVP;
- ComfyUI должен оставаться render/workflow backend, а не объектом переписывания.

## Affected Areas
Какие части проекта нужно изменить, чтобы превратить общий архитектурный замысел в execution-ready план.

| # | File/Module | Why affected |
|---|-------------|--------------|
| 1 | `.memory/decisions/2026-05-06-pilot-stack-react-fastapi-comfyui.md` | Зафиксировать рекомендуемый стек и инфраструктурную модель |
| 2 | `.memory/sessions/research/2026-05-06-content-factory-pilot-architecture-rollout.md` | Сохранить bulletproof research artifact |
| 3 | `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md` | Зафиксировать spec/contract для этапной реализации |
| 4 | `.memory/sessions/plans/2026-05-06-content-factory-rollout-master.md` | Сохранить master-план по этапам |
| 5 | `.memory/sessions/plans/2026-05-06-content-factory-phase-1-control-plane.md` | Детализировать foundation/control-plane этап |
| 6 | `.memory/sessions/plans/2026-05-06-content-factory-phase-2-production-pipeline.md` | Детализировать pipeline/render этап |
| 7 | `.memory/sessions/plans/2026-05-06-content-factory-phase-3-compliance-metrics.md` | Детализировать compliance/analytics этап |
| 8 | `.memory/sessions/plans/2026-05-06-content-factory-phase-4-advanced-operator-tools.md` | Детализировать advanced operator этап |
| 9 | `.memory/context.md` | Обновить текущее состояние проекта и следующий шаг |
| 10 | `.memory/sessions/2026-05-06-codex-rollout-planning.md` | Оставить handoff для следующего агента |
| 11 | `.memory/snapshots/2026-05-06-rollout-planning.md` | Сохранить planning snapshot |

## Codebase Patterns
- Память проекта живет в `.memory/`, а архитектурные решения обязаны фиксироваться в `.memory/decisions/`.
- Бизнес-контекст в `.business/` нужно читать выборочно и не коммитить.
- Технический стек нельзя выбирать молча: для крупных решений нужен ADR.
- Проект явно ориентирован на boring/verifiable choices, минимум спекулятивных abstraction layers.
- Human review и compliance нельзя оставлять на "потом"; они должны быть встроены в основной lifecycle.

## Risks and Constraints
- Категория вейпов/никотина требует compliance gate уже на уровне MVP, а не отдельного позднего модуля.
- Пилот должен работать с одним аватаром и ручной публикацией; не стоит закладываться на multi-brand orchestration или autoposting.
- Полный ComfyUI-like canvas нужен только как advanced/operator mode; ежедневный пользовательский путь должен быть проще.
- В проекте пока нет кода, поэтому план должен одновременно выбрать repo topology, tooling, инфрастек и boundary между control plane и render plane.
- Бюджет и стадия проекта не оправдывают ранний переход к microservices/Kafka/Temporal/Kubernetes.

## Open Questions
- Какой конкретный cloud/vendor будет выбран для pilot environment: self-hosted VM + managed services или PaaS-набор.
- Нужен ли в пилоте production SSO, или достаточно invite-only email/password auth.
- Будет ли metrics ingest в первой версии идти через CSV/manual import, через API-коннекторы, или через гибрид.

Рекомендация для снятия этих вопросов в плане:
- cloud оставить vendor-neutral, но зафиксировать reference topology;
- auth взять invite-only email/password + role-based access;
- metrics начать с manual import и provider interface для будущей автоматизации.

## Best Practices Found
- [FastAPI official docs](https://fastapi.tiangolo.com/) подтверждают удобный путь для typed REST API, dependency injection, Pydantic v2 и OpenAPI-first contract.
- [ComfyUI docs](https://docs.comfy.org/index) и [workflow docs](https://docs.comfy.org/development/core-concepts/workflow) поддерживают подход, где продукт хранит workflow JSON и управляет execution извне.
- [Dramatiq guide](https://dramatiq.io/guide.html) подходит для простого async job orchestration с retries/backoff без преждевременного усложнения.
- [React Flow docs](https://reactflow.dev/learn) дают естественную основу для будущего operator-only workflow canvas, но не требуют строить его в фазе 1.
- [PostgreSQL docs](https://www.postgresql.org/docs/) и [MinIO docs](https://min.io/docs/minio/linux/index.html) хорошо ложатся на модель source-of-truth + object storage для media-heavy продукта.

## Conclusion & Recommendation
**Recommended approach:** строить pilot implementation как модульный монолит с monorepo-структурой: `apps/web` на React/Vite/TypeScript, `apps/api` на FastAPI, `apps/worker` на Dramatiq, `PostgreSQL` как source of truth, `Redis` для async-очередей, `S3-compatible storage` для ассетов, `ComfyUI` как отдельный render/workflow backend.

**Key reasons:**
1. Такой стек быстрее всего приведет к рабочему pilot control plane без premature complexity.
2. Control plane и render plane разделяются сразу, поэтому ComfyUI можно интегрировать как backend-сервис без переписывания.
3. Архитектура позволяет встроить review, compliance, cost tracking и analytics в основной lifecycle, а не приклеивать их поздно.

**Risks of this approach:** двухъязычный стек повышает coordination cost; потребуется аккуратно определить API-контракты, worker-idempotency и vendor-neutral инфраструктуру уже в фазе 1.
