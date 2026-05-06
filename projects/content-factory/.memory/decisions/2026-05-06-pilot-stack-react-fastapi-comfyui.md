# ADR: Recommended Pilot Stack For Content Factory

## Context

Проект Content Factory находится на стадии product/pilot definition. Бизнес-контекст и ограничения уже понятны: regulated category, один основной аватар, manual publish, обязательный human review, ComfyUI-like backend, analytics loop и контроль экономики.

Для следующего этапа нужен не просто список технологий, а такой набор, который:
- быстро приводит к pilot-ready control plane;
- не заставляет переписывать ComfyUI;
- позволяет вынести media generation в async/render слой;
- не вводит лишнюю platform complexity слишком рано.

## Decision

Использовать для пилотной реализации следующую базовую архитектуру и стек:

- Monorepo с директориями:
  - `apps/web` — `React 19 + TypeScript + Vite + TanStack Router + TanStack Query + React Hook Form + Zod + Tailwind + shadcn/Radix`
  - `apps/api` — `Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic`
  - `apps/worker` — `Python 3.12 + Dramatiq + Redis`
  - `packages/contracts` — OpenAPI-generated клиент, shared API contracts и typed DTO helpers
- Data plane:
  - `PostgreSQL` как system of record
  - `Redis` для async-очередей и transient job state
  - `S3-compatible object storage` для ассетов, промежуточных файлов и финальных роликов
- Render plane:
  - отдельный `ComfyUI`-совместимый backend как workflow/render engine
  - `FFmpeg` для packaging и технической обработки видео
- Infra baseline:
  - local/dev через `Docker Compose`
  - pilot environment как containerized control plane (`web`, `api`, `worker`) + managed data services + отдельный GPU render node
- Auth и доступ:
  - invite-only email/password auth
  - backend-managed cookie sessions
  - роли `owner`, `marketing_manager`, `producer`, `operator`, `reviewer`
- Metrics ingest:
  - на старте manual import/CSV + provider interface для будущих автоматизированных коннекторов

## Rationale

1. **Соответствие продукту.**
   Продукту нужен не SSR-heavy сайт, а операторская SPA с очередями, ревью, статусами и media workflows.

2. **Явное разделение control plane и render plane.**
   Продукт хранит проекты, ассеты, версии, review и аналитику; ComfyUI отвечает за граф/рендер.

3. **Умеренная сложность.**
   FastAPI + Dramatiq + Postgres + Redis достаточно для пилота и дешевле по ops-нагрузке, чем microservices/Temporal/Kafka.

4. **Готовность к regulated workflow.**
   Такой стек позволяет встроить audit log, review gates, compliance scoring и cost tracking как first-class domain concepts.

## Consequences

### Positive
- Быстрый путь к working pilot без архитектурного долга в зоне async-media workloads.
- Понятные boundaries между UI, API, worker-слоем и GPU/render backend.
- Возможность поэтапно усиливать продукт без переписывания базовой модели.

### Tradeoffs
- Два основных runtime: TypeScript и Python.
- Придется дисциплинированно поддерживать API contracts и генерацию клиентов.
- Понадобится отдельная стратегия локальной работы с ComfyUI и моками render backend.

### Deferred Decisions
- Конкретный cloud vendor для pilot environment.
- Набор автоматических интеграций с метриками площадок после manual import версии.
- Нужен ли production SSO после пилота.
