# Spec: Content Factory Pilot Implementation Rollout

**Date:** 2026-05-06
**Author:** Tomas + Codex
**Task size:** L

---

## Problem
У проекта уже есть сильный бизнес-контекст и общее техническое направление, но нет execution-ready плана, по которому можно последовательно запускать реализацию без повторного выбора стека, архитектуры и границ MVP на каждом шаге.

## Goal
Подготовить decision-complete rollout для пилотной версии Content Factory под Inflave: зафиксировать рекомендуемый стек, базовую инфраструктурную модель и разбить реализацию на независимые этапы с понятными deliverables, тестами, гейтами и зависимостями.

## Scope

### In Scope
- Выбор и фиксация рекомендуемого pilot stack и repo topology.
- Разделение системы на `web`, `api`, `worker`, `storage`, `render backend`.
- Планирование четырех этапов:
  - foundation/control plane;
  - production pipeline/render integration;
  - compliance/metrics/economics;
  - advanced operator tooling.
- Явная модель lifecycle для контента: от draft до analytics/playbook.
- Базовая infra-модель для local/dev и pilot environment.
- Тестовая стратегия и quality gates для каждого этапа.

### Out of Scope (not doing)
- Непосредственная реализация кода.
- Автопостинг в соцсети.
- Multi-brand/multi-tenant enterprise architecture.
- Переписывание ComfyUI или создание собственного workflow engine.
- Полноценный public marketing site, mobile app, billing и sales CRM.

## Acceptance Criteria
- [ ] В проекте есть research artifact с рекомендацией по стеку и архитектуре.
- [ ] В проекте есть ADR с зафиксированным рекомендуемым pilot stack.
- [ ] В проекте есть один master rollout plan и четыре отдельных phase-плана.
- [ ] Каждый phase-план содержит deliverables, предполагаемые кодовые области, TDD/test strategy, gates и prompt для запуска реализации.
- [ ] План учитывает compliance-first, human review и manual publish как элементы базового lifecycle, а не как будущие дополнения.
- [ ] План задает infra baseline для local/dev и pilot environment без привязки к одному vendor.

## Constraints
- Пилот рассчитан на одного главного human-like аватара.
- Целевая категория юридически и платформенно чувствительная; human approve обязателен.
- Публикация в MVP ручная; продукт должен готовить publish package, а не публиковать сам.
- Надо сохранить ComfyUI как workflow/render backend-кандидат.
- Нужно избегать преждевременной сложности и тяжелой service decomposition.

## Non-Goals
- Строить enterprise-platform "на вырост" раньше pilot validation.
- Вводить сложную оркестрацию уровня Kafka/Temporal/Kubernetes до появления подтвержденной нагрузки.
- Закладываться на полностью автономную генерацию и публикацию без человека в контуре.
