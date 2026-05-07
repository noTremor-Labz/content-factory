# Spec: Phase 3 Compliance Gate

**Date:** 2026-05-07
**Task size:** M/L slice

## Problem

Content Factory can approve and package content without a persisted compliance assessment. For the Inflave pilot this is unsafe because vape/nicotine-adjacent content needs explainable risk memory and a hard export gate before manual publishing bundles are created.

## Goal

Implement the first compliance gate: deterministic policy checks, risk score persistence, reviewer-visible summaries, approval blocking, and export/package defense-in-depth.

## Scope

- Add persisted compliance rules/checks with statuses, risk flags, reason codes, and risk score.
- Run a compliance check when planned/rework content is submitted to review.
- Add a manual authenticated endpoint to rerun compliance checks for a content item.
- Block review approval when:
  - no compliance check exists;
  - latest check has hard failures;
  - latest check has soft flags and the reviewer does not provide an override reason.
- Persist reviewer override reason for soft-flag approval.
- Block publish-package creation/retry unless approved content has a final compliance decision.
- Block worker package processing with the same compliance decision rules.
- Show compliance summaries in the review/export cockpit.
- Regenerate OpenAPI and TypeScript contracts.

## Non-Goals

- No legal-advice automation claim.
- No social-platform API connectors.
- No image/video computer vision scan in this slice.
- No admin UI for editing compliance rules.
- No jurisdiction-specific production policy engine.

## Acceptance Criteria

- Hard-fail scripts cannot be approved.
- Soft-flag scripts require explicit reviewer override reason before approval.
- Passed scripts can be approved normally.
- Approved legacy content without a compliance decision cannot be packaged.
- Publish package worker fails queued packages if the final compliance decision is missing or invalid.
- Reviewer UI displays compliance status, risk score, flags, and override affordance.
- Export UI only offers succeeded approved renders with acceptable compliance decisions.
- Audit log records check execution and soft-flag overrides.

## Constraints

- Keep dependency footprint unchanged.
- Preserve the current human approval lifecycle.
- Do not weaken existing RBAC gates.
- Deterministic rules must be easy to test and adjust later.
