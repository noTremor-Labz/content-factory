# Plan: Phase 3 Compliance Gate

**Spec:** `.memory/sessions/specs/2026-05-07-compliance-gate.md`
**Status:** completed

## Challenge Loop

1. **Does this solve the problem?**
   - Yes. The plan adds persisted checks, blocks approval/export/package without acceptable compliance state, and surfaces the result to reviewers/operators.

2. **Is this efficient?**
   - Chosen: deterministic seeded rules + persisted checks + reviewer override.
   - Alternative manual-only review is faster but fails risk memory and export gating.
   - Alternative full policy engine is more flexible but too large for this pilot slice.
   - Alternative worker-only compliance would be too late because reviewers need the result before approval.

3. **Any code for code's sake?**
   - Excluded admin rule editor, platform API import, computer vision, and jurisdiction matrix.
   - Only add data/contracts needed by approval/export gates and UI summary.

## Implementation Steps

1. API domain/data
   - Add compliance enums, `ComplianceRule`, `ComplianceCheck`, review override fields, and Alembic migration.
   - Add Pydantic schemas.

2. Compliance service/router
   - Seed default rules idempotently.
   - Evaluate title/script with deterministic hard/soft keyword rules.
   - Expose list/rerun endpoints and helper functions for latest/final decision.

3. Lifecycle gates
   - Run compliance check during `submit-review`.
   - Block `approve` based on latest check.
   - Store `compliance_check_id` and `compliance_override_reason` on review approval.
   - Use a shared helper in publish package creation/retry.

4. Worker gate
   - Reuse compliance decision helper in package processing validation.

5. Tests
   - API tests for hard fail, soft override, passed approval, missing-check package block.
   - Worker packaging test for compliance gate.
   - Migration/openapi tests.

6. Web
   - Regenerate contracts.
   - Add compliance types/client/list to cockpit data.
   - Display compliance summary and soft-override field in review UI.
   - Filter export candidates by compliance decision.

7. Verification
   - Targeted tests first, then `make test-api`, `make lint-api`, `make typecheck-api`, `make test-web`, `make typecheck-web`.

## File Boundaries

- `apps/api/src/content_factory_api/modules/*`
- `apps/api/alembic/versions/*`
- `apps/api/tests/*`
- `apps/worker/src/content_factory_worker/packaging.py`
- `apps/worker/tests/*`
- `apps/web/src/*`
- `packages/contracts/*`
- `.memory/*`
