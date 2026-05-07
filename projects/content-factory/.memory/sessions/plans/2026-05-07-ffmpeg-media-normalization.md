# Plan: FFmpeg Media Normalization For Publish Packages

**Spec:** `.memory/sessions/specs/2026-05-07-ffmpeg-media-normalization.md`
**Status:** completed

---

## Challenge Log

**Problem:** publish packages are metadata bundles, not actual manual-publish media bundles. Operators still need to locate raw render outputs and normalize video outside Content Factory.

**Chosen solution:** extend the existing `ZipPublishPackager` with an injectable storage downloader and `FfmpegMediaNormalizer`. The worker will resolve the mapped primary video artifact, download it from same-bucket S3-compatible storage, run FFmpeg to a temp MP4, include `video.mp4` in the ZIP, and record normalized artifact metadata in `manifest.json`.

**Alternatives considered:**
1. Add a separate media-normalization job/table before publish packaging — rejected because Phase 2 only needs one manual export bundle and a second lifecycle would add unnecessary queue/state complexity.
2. Store normalized MP4 as a separate S3 object and keep ZIP metadata-only — rejected because the pilot operator needs one download-ready package, and the current API already exposes one package download object.
3. Skip FFmpeg until Docker/runtime is settled — rejected because the code contract and tests can be implemented now with graceful runtime failure, while infra can install the binary later.

**Why chosen solution is better:** it directly completes the current package worker contract with minimal blast radius, keeps FFmpeg replaceable behind a protocol, and avoids creating new product surfaces before the pilot needs them.

### Challenge Loop

1. **Does this solve the problem?**
   - ZIP gets `video.mp4`: covered by tests for archive contents.
   - Manifest points to normalized media and source artifact: covered by manifest assertions.
   - Current S3 render references are downloadable: covered by storage fake and S3 storage implementation.
   - Missing FFmpeg fails cleanly: covered by fake/real normalizer error tests.

2. **Is this the most efficient solution?**
   - Separate normalization lifecycle would be more scalable later but is larger than needed for pilot exports.
   - Direct ZIP inclusion reuses the existing package download endpoint and keeps operator UX simple.
   - A protocol-based normalizer keeps tests fast and does not require installing FFmpeg locally.

3. **Is there code for code's sake?**
   - No API schema, web UI, or DB migration is needed for this slice.
   - No broad media ingestion abstraction is needed; support current same-bucket S3/object-key references only.
   - No platform upload integrations are included.

## Problems

| # | Problem | Solution | Status |
|---|---------|----------|--------|
| 1 | Package ZIP has no media file | Add normalized `video.mp4` to ZIP output | completed |
| 2 | Worker cannot download render output media | Extend package storage protocol with artifact download by same-bucket reference | completed |
| 3 | FFmpeg may be missing locally/runtime | Add injectable normalizer and explicit `PublishPackageError` failure path | completed |
| 4 | Manifest does not describe normalized media | Add `normalized_artifacts` metadata to manifest | completed |
| 5 | Tests must not require local FFmpeg | Use fake normalizer in package tests plus unit coverage for command/error construction | completed |

## Phases

### Phase 1: Worker Normalization Contract
- **Status:** completed
- **Files:** `apps/worker/src/content_factory_worker/packaging.py`, `apps/worker/src/content_factory_worker/jobs/packaging.py`, `apps/worker/src/content_factory_worker/config.py`, `apps/worker/tests/test_publish_package_orchestration.py`, `.env.example`
- **Changes:** introduce `MediaNormalizer` protocol, `FfmpegMediaNormalizer`, storage download protocol, primary video artifact selection, normalized ZIP inclusion, manifest enrichment, FFmpeg worker settings.
- **TDD:** first add failing tests for ZIP `video.mp4`, manifest normalized artifact metadata, storage download source, and normalizer failure -> package failed.
- **Gates:** `make lint-api` ✅ | `make typecheck-api` ✅ | `make test-api` ✅
- **Impact:** affects package worker runtime and package ZIP contents only; API/web contracts remain stable because `manifest_payload` is already JSON.
- **Prompt for launch:**
  ```text
  Read .memory/sessions/plans/2026-05-07-ffmpeg-media-normalization.md.
  Read spec at .memory/sessions/specs/2026-05-07-ffmpeg-media-normalization.md.
  Implement Phase 1 according to plan. Start with tests.
  Do not modify files outside of:
  - apps/worker/src/content_factory_worker/packaging.py
  - apps/worker/src/content_factory_worker/jobs/packaging.py
  - apps/worker/src/content_factory_worker/config.py
  - apps/worker/tests/test_publish_package_orchestration.py
  - .env.example
  - .memory/context.md and phase handoff/snapshot files after verification
  After completing:
  1. Self-audit against every acceptance criterion
  2. Verify bugs are real before fixing
  3. Impact analysis for package lifecycle and contracts
  4. Run the phase gates
  ```

## Changelog

| Date | Phase | Changes |
|------|-------|---------|
| 2026-05-07 | planning | Created Bulletproof research/spec/plan for FFmpeg normalization slice |
| 2026-05-07 | worker-normalization-contract | Added FFmpeg media normalizer, artifact download support, normalized `video.mp4` ZIP inclusion, manifest metadata, settings, and tests |
