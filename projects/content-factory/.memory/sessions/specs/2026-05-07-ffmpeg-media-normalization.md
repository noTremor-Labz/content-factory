# Spec: FFmpeg Media Normalization For Publish Packages

**Date:** 2026-05-07
**Author:** Tomas + Codex
**Task size:** M

---

## Problem

Publish packages are currently manifest ZIPs that reference render output media but do not include a normalized video file. This leaves the manual publish package incomplete for a pilot operator: the operator can download metadata, but still needs to find and process raw render outputs outside the product.

## Goal

Make the publish package worker produce a download-ready ZIP that includes a normalized MP4 video artifact for manual Reels/Shorts publishing, while preserving existing package lifecycle semantics and graceful worker failure behavior.

## Scope

### In Scope

- Resolve the primary video artifact from the existing workflow output mapping and successful render attempt payload.
- Download same-bucket render output media from S3-compatible storage references.
- Normalize the primary video with FFmpeg into an MP4 suitable for short-form manual publishing.
- Include the normalized `video.mp4` in the ZIP publish package.
- Enrich `manifest.json` with normalized video metadata such as package path, source artifact, container, and profile.
- Add worker settings for FFmpeg binary path and timeout/profile defaults.
- Fail the package with a clear error when FFmpeg is unavailable, source media cannot be resolved, or normalization fails.
- Cover the behavior with worker tests using injectable fakes so the test suite does not require local FFmpeg.

### Out of Scope (not doing)

- Installing FFmpeg on the local machine or changing Docker images.
- Direct autoposting to Instagram, YouTube, TikTok, or any other platform.
- Provider-native media fetching from arbitrary HTTP URLs.
- Full platform-specific validation against every Reels/Shorts upload constraint.
- Advanced ComfyUI output-to-node mutation or richer provider output mapping.
- A new media service, separate queue, or Temporal/Kafka-style orchestration.

## Acceptance Criteria

- [ ] A ready publish package ZIP includes `video.mp4` in addition to manifest/manual publishing files.
- [ ] `manifest.json` includes a normalized video artifact entry that points to `video.mp4` and records the source render artifact.
- [ ] The worker downloads current `s3://{bucket}/{key}` render output references through the package storage dependency.
- [ ] The worker can be tested without a real FFmpeg binary by injecting a fake normalizer.
- [ ] If FFmpeg is missing or returns an error, the publish package becomes `failed` with a useful `error_message`.
- [ ] Existing package lifecycle guards still hold: ready packages are skipped, running packages are skipped, and cancelled packages are not processed.
- [ ] Existing API/web contracts remain compatible unless an explicit schema field changes.
- [ ] The phase gates pass: `make lint-api`, `make typecheck-api`, `make test-api`, and targeted worker packaging tests.

## Constraints

- Keep changes localized to the publish package worker unless settings or documentation need a small update.
- Use `subprocess.run` with an argument list, not shell command strings.
- Use temp files for media normalization and clean them up automatically.
- Do not fetch arbitrary external URLs from provider payloads.
- Preserve human approval and succeeded-render gates before package creation.
- The current local machine has no FFmpeg binary, so real-binary tests must not be mandatory.

## Non-Goals

- Building a complete media asset management subsystem.
- Adding a browser preview player or frontend package inspection UI.
- Transcoding every possible output artifact type.
- Designing a final production deployment image for FFmpeg.
