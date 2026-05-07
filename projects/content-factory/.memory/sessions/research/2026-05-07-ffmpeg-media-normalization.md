# Research: FFmpeg Media Normalization For Publish Packages

**Date:** 2026-05-07
**Task size:** M
**Agent:** Codex

---

## Current Architecture

Phase 2 already has a publish package pipeline:

1. API creates one `PublishPackage` per succeeded approved `RenderJob`.
2. API enqueues `process_publish_package_message`.
3. Worker loads `PublishPackage`, `RenderJob`, `WorkflowPreset`, `ContentItem`, and the latest successful `JobAttempt`.
4. `ZipPublishPackager` resolves output artifacts from `workflow_preset.output_mapping` and `attempt.response_payload`.
5. The worker builds a ZIP with `manifest.json`, manual publishing text files, and `provider-output.json`.
6. The ZIP is uploaded to S3-compatible storage and `PublishPackage` becomes `ready`.

Current limitation: render output media is referenced in the manifest but not downloaded, normalized, or included as a platform-ready MP4 artifact.

Local runtime fact: `ffmpeg` is not installed on this machine (`which ffmpeg` returned no binary), so implementation must be testable without a local FFmpeg install and must fail gracefully when the binary is unavailable at runtime.

## Affected Areas

| # | File/Module | Why affected |
|---|-------------|--------------|
| 1 | `apps/worker/src/content_factory_worker/packaging.py` | Add media artifact resolution, storage download, injectable FFmpeg normalizer, ZIP media inclusion, manifest enrichment, failure handling |
| 2 | `apps/worker/src/content_factory_worker/jobs/packaging.py` | Wire S3 download support and FFmpeg normalizer from worker settings |
| 3 | `apps/worker/src/content_factory_worker/config.py` | Add FFmpeg binary path and normalization settings |
| 4 | `apps/worker/tests/test_publish_package_orchestration.py` | Add tests for normalized video inclusion, missing FFmpeg failure, and backward package state handling |
| 5 | `.env.example` | Document FFmpeg runtime settings |
| 6 | `.memory/*` | Record spec, plan, context, and handoff after implementation |

## Codebase Patterns

- Worker orchestration uses protocol-based dependencies (`PublishPackager`, `PackageStorage`) so tests can provide in-memory fakes.
- Domain failures are represented as `PublishPackageError`; `process_publish_package` catches these and marks the package `failed` with an explicit message.
- The package worker already guards terminal states (`ready`, `running`, `cancelled`) and refreshes state after long-running work.
- Tests are focused and use SQLite + in-memory protocol fakes.
- Generated contracts are only needed when API schemas change. A manifest shape change stored in JSON does not require OpenAPI regeneration unless API schema fields change.

## Risks and Constraints

- FFmpeg may not exist in local/dev/pilot runtime. This should produce a clear package failure, not an unhandled worker crash.
- Provider output values may be `s3://bucket/key`, object keys, or richer provider payloads in the future. The first slice should support current `s3://...` and same-bucket object-key references without broad URL fetching.
- Media bytes should not be loaded repeatedly. For pilot-sized shorts, downloading to a temp file and running FFmpeg through `subprocess.run([...])` is acceptable and simpler than streaming pipes.
- Do not fetch arbitrary HTTP URLs from provider payloads in this slice; that would create SSRF and auth questions.
- Do not implement direct social autoposting or platform-specific upload APIs.
- Do not weaken the existing approved-content and succeeded-render gates.

## Open Questions

- Which exact platform presets are required first: one shared vertical MP4 profile or separate Reels/Shorts profiles?
- Should package ZIPs include cover images now, or only normalize the primary video artifact in this slice?
- Should FFmpeg be installed into local Docker/runtime now or handled in a later infra slice?

These are not blockers for the first implementation: use one conservative vertical MP4 profile and include the normalized video in the ZIP.

## Best Practices Found

- Official FFmpeg docs describe `ffmpeg` as a universal converter that reads inputs via `-i` and writes output URLs/files; options apply to the next file, so command ordering matters: https://www.ffmpeg.org/ffmpeg.html
- Official FFmpeg formats docs state that `movflags +faststart` moves MP4 metadata to the beginning for better playback/startup, while noting it requires a second pass: https://ffmpeg.org/ffmpeg-formats.html
- Use argument lists with `subprocess.run` instead of shell strings to avoid shell injection from artifact paths.

## Conclusion & Recommendation

**Recommended approach:** add a small injectable `FfmpegMediaNormalizer` and storage download protocol inside the existing publish package worker. The packager should download the primary video artifact, run FFmpeg into a temp MP4 using a conservative short-form profile, include `video.mp4` in the ZIP, and enrich `manifest.json` with normalized artifact metadata.

**Key reasons:**
- This fits the existing protocol/fake-test pattern and keeps the change localized to packaging.
- It makes runtime failures explicit through existing `PublishPackageStatus.FAILED` handling.
- It avoids a premature media platform while producing an actual manual-publish bundle.

**Risks of this approach:**
- Requires FFmpeg in real worker runtime before the feature can produce ready packages with real video.
- Initial artifact resolution remains intentionally narrow; richer ComfyUI output mapping can be added later.
- Transcoding can be CPU-heavy, but pilot short-form usage makes synchronous worker execution acceptable for now.
