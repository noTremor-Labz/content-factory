import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { App } from "./App";

interface MockUser {
  id: string;
  email: string;
  display_name: string;
  role: "owner" | "operator" | "reviewer" | "viewer";
  status: "active";
  created_at: string;
}

interface MockSession {
  user: MockUser;
  expires_at: string;
}

interface MockBrand {
  id: string;
  name: string;
  voice_notes: string | null;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

interface MockAvatar {
  id: string;
  brand_id: string;
  name: string;
  persona_notes: string | null;
  status: "draft" | "active";
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

interface MockIdentityPack {
  id: string;
  avatar_id: string;
  name: string;
  description: string | null;
  storage_prefix: string;
  status: "draft" | "ready";
  created_at: string;
  updated_at: string;
}

interface MockAsset {
  id: string;
  brand_id: string;
  object_key: string;
  filename: string;
  content_type: string;
  byte_size: number | null;
  checksum_sha256: string | null;
  status: "pending_upload" | "ready" | "failed";
  upload_expires_at: string;
  created_at: string;
  updated_at: string;
}

interface MockContentItem {
  id: string;
  brand_id: string;
  avatar_id: string;
  title: string;
  script: string;
  channel: "instagram_reels" | "youtube_shorts";
  status: "draft" | "planned" | "review" | "approved" | "rework";
  planned_publish_at: string | null;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

interface MockReviewTask {
  id: string;
  content_item_id: string;
  assigned_to_user_id: string | null;
  status: "open" | "approved" | "rework" | "cancelled";
  decision_notes: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

interface MockAuditLog {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  payload: Record<string, unknown>;
  created_at: string;
}

interface MockWorkflowPreset {
  id: string;
  key: string;
  version: number;
  name: string;
  description: string | null;
  workflow_provider: "comfyui";
  voice_provider: "none";
  packaging_provider: "ffmpeg";
  workflow_definition: Record<string, unknown>;
  input_mapping: Record<string, unknown>;
  output_mapping: Record<string, unknown>;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

interface MockJobAttempt {
  id: string;
  render_job_id: string;
  attempt_number: number;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  provider_job_id: string | null;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown>;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

interface MockRenderJob {
  id: string;
  content_item_id: string;
  workflow_preset_id: string;
  workflow_preset_key: string;
  workflow_preset_version: number;
  workflow_provider: "comfyui";
  voice_provider: "none";
  packaging_provider: "ffmpeg";
  input_snapshot: Record<string, unknown>;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  retry_budget: number;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
  attempts: MockJobAttempt[];
}

interface MockPublishPackage {
  id: string;
  render_job_id: string;
  content_item_id: string;
  status: "queued" | "running" | "ready" | "failed" | "cancelled";
  package_object_key: string | null;
  manifest_payload: Record<string, unknown>;
  byte_size: number | null;
  error_message: string | null;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

interface MockApiState {
  session: MockSession | null;
  brands: MockBrand[];
  avatars: MockAvatar[];
  identityPacks: MockIdentityPack[];
  assets: MockAsset[];
  contentItems: MockContentItem[];
  reviewTasks: MockReviewTask[];
  auditLogs: MockAuditLog[];
  workflowPresets: MockWorkflowPreset[];
  renderJobs: MockRenderJob[];
  publishPackages: MockPublishPackage[];
}

type RouteHandler = (
  path: string,
  options: RequestInit | undefined,
  state: MockApiState,
) => Promise<Response> | Response;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function noContentResponse(status = 200): Response {
  return new Response(null, { status });
}

function nowIso(minuteOffset = 0): string {
  return new Date(Date.UTC(2026, 4, 6, 12, minuteOffset)).toISOString();
}

function createOwnerSession(): MockSession {
  return {
    user: {
      id: "user-owner",
      email: "owner@inflave.test",
      display_name: "Owner",
      role: "owner",
      status: "active",
      created_at: nowIso(0),
    },
    expires_at: nowIso(240),
  };
}

function createWorkflowPreset(): MockWorkflowPreset {
  return {
    id: "workflow-preset-1",
    key: "pilot-reels",
    version: 1,
    name: "Pilot Reels",
    description: "Primary short-form render preset.",
    workflow_provider: "comfyui",
    voice_provider: "none",
    packaging_provider: "ffmpeg",
    workflow_definition: { nodes: {} },
    input_mapping: { script_text: { source_type: "content_item", source_field: "script" } },
    output_mapping: { video_file: { artifact_type: "video", output_path: "outputs.video" } },
    created_by_user_id: "user-owner",
    created_at: nowIso(0),
    updated_at: nowIso(0),
  };
}

function installMockApi(initialState: Partial<MockApiState> = {}) {
  const state: MockApiState = {
    session: initialState.session ?? null,
    brands: initialState.brands ?? [],
    avatars: initialState.avatars ?? [],
    identityPacks: initialState.identityPacks ?? [],
    assets: initialState.assets ?? [],
    contentItems: initialState.contentItems ?? [],
    reviewTasks: initialState.reviewTasks ?? [],
    auditLogs: initialState.auditLogs ?? [],
    workflowPresets: initialState.workflowPresets ?? [],
    renderJobs: initialState.renderJobs ?? [],
    publishPackages: initialState.publishPackages ?? [],
  };

  let sequence = 0;

  function nextId(prefix: string): string {
    sequence += 1;
    return `${prefix}-${sequence}`;
  }

  function recordAudit(action: string, entityType: string, entityId: string) {
    state.auditLogs.unshift({
      id: nextId("audit"),
      actor_user_id: state.session?.user.id ?? null,
      action,
      entity_type: entityType,
      entity_id: entityId,
      payload: {},
      created_at: nowIso(sequence),
    });
  }

  const fetchMock = vi.fn(async (input: string | URL | Request, options?: RequestInit) => {
    const rawUrl =
      typeof input === "string" || input instanceof URL ? input.toString() : input.url;
    const url = new URL(rawUrl, window.location.origin);
    const method =
      options?.method ??
      (typeof input === "string" || input instanceof URL ? "GET" : input.method) ??
      "GET";
    const normalizedMethod = method.toUpperCase();
    const path = `${url.pathname}${url.search}`;

    const handlers: Array<[string, RegExp, RouteHandler]> = [
      [
        "GET",
        /^\/api\/auth\/session$/,
        async () =>
          state.session ? jsonResponse(state.session) : jsonResponse({ detail: "Authentication required" }, 401),
      ],
      [
        "POST",
        /^\/api\/auth\/bootstrap-owner$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          state.session = {
            user: {
              id: "user-owner",
              email: body.email,
              display_name: body.display_name,
              role: "owner",
              status: "active",
              created_at: nowIso(0),
            },
            expires_at: nowIso(240),
          };
          recordAudit("auth.bootstrap_owner", "user", state.session.user.id);
          return jsonResponse(state.session, 201);
        },
      ],
      [
        "POST",
        /^\/api\/auth\/login$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          state.session = {
            ...createOwnerSession(),
            user: {
              ...createOwnerSession().user,
              email: body.email,
            },
          };
          recordAudit("auth.login", "user", state.session.user.id);
          return jsonResponse(state.session);
        },
      ],
      [
        "POST",
        /^\/api\/auth\/invites\/accept$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          state.session = {
            user: {
              id: "user-reviewer",
              email: body.email,
              display_name: body.display_name,
              role: "reviewer",
              status: "active",
              created_at: nowIso(1),
            },
            expires_at: nowIso(240),
          };
          recordAudit("auth.invite_accepted", "user", state.session.user.id);
          return jsonResponse(state.session, 201);
        },
      ],
      [
        "POST",
        /^\/api\/auth\/logout$/,
        async () => {
          state.session = null;
          return jsonResponse({ status: "ok" });
        },
      ],
      ["GET", /^\/api\/brands$/, async () => jsonResponse({ items: state.brands })],
      [
        "POST",
        /^\/api\/brands$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          const brand: MockBrand = {
            id: nextId("brand"),
            name: body.name,
            voice_notes: body.voice_notes || null,
            created_by_user_id: state.session?.user.id ?? "system",
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.brands.unshift(brand);
          recordAudit("brand.created", "brand", brand.id);
          return jsonResponse(brand, 201);
        },
      ],
      ["GET", /^\/api\/avatars$/, async () => jsonResponse({ items: state.avatars })],
      [
        "POST",
        /^\/api\/avatars$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          const avatar: MockAvatar = {
            id: nextId("avatar"),
            brand_id: body.brand_id,
            name: body.name,
            persona_notes: body.persona_notes || null,
            status: "draft",
            created_by_user_id: state.session?.user.id ?? "system",
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.avatars.unshift(avatar);
          recordAudit("avatar.created", "avatar", avatar.id);
          return jsonResponse(avatar, 201);
        },
      ],
      [
        "GET",
        /^\/api\/avatars\/[^/]+\/identity-packs$/,
        async (matchedPath) => {
          const avatarId = matchedPath.split("/")[3];
          return jsonResponse({
            items: state.identityPacks.filter((identityPack) => identityPack.avatar_id === avatarId),
          });
        },
      ],
      [
        "POST",
        /^\/api\/avatars\/[^/]+\/identity-packs$/,
        async (matchedPath, requestOptions) => {
          const avatarId = matchedPath.split("/")[3];
          const body = JSON.parse(String(requestOptions?.body));
          const identityPack: MockIdentityPack = {
            id: nextId("identity"),
            avatar_id: avatarId,
            name: body.name,
            description: body.description || null,
            storage_prefix: body.storage_prefix,
            status: "draft",
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.identityPacks.unshift(identityPack);
          recordAudit("identity_pack.created", "identity_pack", identityPack.id);
          return jsonResponse(identityPack, 201);
        },
      ],
      ["GET", /^\/api\/assets$/, async () => jsonResponse({ items: state.assets })],
      [
        "POST",
        /^\/api\/assets\/uploads$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          const asset: MockAsset = {
            id: nextId("asset"),
            brand_id: body.brand_id,
            object_key: `uploads/${body.brand_id}/${body.filename}`,
            filename: body.filename,
            content_type: body.content_type,
            byte_size: body.byte_size ?? null,
            checksum_sha256: null,
            status: "pending_upload",
            upload_expires_at: nowIso(30),
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.assets.unshift(asset);
          recordAudit("asset.upload_initiated", "asset", asset.id);
          return jsonResponse(
            {
              asset,
              upload: {
                method: "PUT",
                url: `http://localhost:9000/content-factory-assets/${asset.object_key}?signature=demo`,
                headers: { "Content-Type": asset.content_type },
                expires_at: asset.upload_expires_at,
              },
            },
            201,
          );
        },
      ],
      ["PUT", /^\/__storage_proxy\/content-factory-assets\/.+$/, async () => noContentResponse(200)],
      [
        "POST",
        /^\/api\/assets\/[^/]+\/finalize$/,
        async (matchedPath, requestOptions) => {
          const assetId = matchedPath.split("/")[3];
          const body = JSON.parse(String(requestOptions?.body));
          const asset = state.assets.find((item) => item.id === assetId);

          if (!asset) {
            return jsonResponse({ detail: "Asset not found" }, 404);
          }

          asset.status = "ready";
          asset.byte_size = body.byte_size;
          asset.updated_at = nowIso(sequence);
          recordAudit("asset.upload_finalized", "asset", asset.id);
          return jsonResponse(asset);
        },
      ],
      ["GET", /^\/api\/content-items$/, async () => jsonResponse({ items: state.contentItems })],
      [
        "POST",
        /^\/api\/content-items$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          const contentItem: MockContentItem = {
            id: nextId("content"),
            brand_id: body.brand_id,
            avatar_id: body.avatar_id,
            title: body.title,
            script: body.script,
            channel: body.channel,
            status: "draft",
            planned_publish_at: null,
            created_by_user_id: state.session?.user.id ?? "system",
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.contentItems.unshift(contentItem);
          recordAudit("content.created", "content_item", contentItem.id);
          return jsonResponse(contentItem, 201);
        },
      ],
      [
        "POST",
        /^\/api\/content-items\/[^/]+\/plan$/,
        async (matchedPath, requestOptions) => {
          const contentItemId = matchedPath.split("/")[3];
          const body = JSON.parse(String(requestOptions?.body));
          const contentItem = state.contentItems.find((item) => item.id === contentItemId);

          if (!contentItem) {
            return jsonResponse({ detail: "Content item not found" }, 404);
          }

          contentItem.status = "planned";
          contentItem.planned_publish_at = body.planned_publish_at ?? null;
          contentItem.updated_at = nowIso(sequence);
          recordAudit("content.planned", "content_item", contentItem.id);
          return jsonResponse(contentItem);
        },
      ],
      [
        "POST",
        /^\/api\/content-items\/[^/]+\/submit-review$/,
        async (matchedPath) => {
          const contentItemId = matchedPath.split("/")[3];
          const contentItem = state.contentItems.find((item) => item.id === contentItemId);

          if (!contentItem) {
            return jsonResponse({ detail: "Content item not found" }, 404);
          }

          contentItem.status = "review";
          contentItem.updated_at = nowIso(sequence);
          const reviewTask: MockReviewTask = {
            id: nextId("review"),
            content_item_id: contentItem.id,
            assigned_to_user_id: null,
            status: "open",
            decision_notes: null,
            completed_at: null,
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.reviewTasks.unshift(reviewTask);
          recordAudit("content.submitted_for_review", "content_item", contentItem.id);
          return jsonResponse(reviewTask, 201);
        },
      ],
      ["GET", /^\/api\/review\/tasks$/, async () => jsonResponse({ items: state.reviewTasks })],
      [
        "POST",
        /^\/api\/review\/tasks\/[^/]+\/approve$/,
        async (matchedPath, requestOptions) => {
          const taskId = matchedPath.split("/")[4];
          const body = JSON.parse(String(requestOptions?.body));
          const reviewTask = state.reviewTasks.find((item) => item.id === taskId);

          if (!reviewTask) {
            return jsonResponse({ detail: "Review task not found" }, 404);
          }

          const contentItem = state.contentItems.find(
            (item) => item.id === reviewTask.content_item_id,
          );
          if (!contentItem) {
            return jsonResponse({ detail: "Content item not found" }, 404);
          }

          reviewTask.status = "approved";
          reviewTask.decision_notes = body.decision_notes ?? null;
          reviewTask.completed_at = nowIso(sequence);
          reviewTask.updated_at = nowIso(sequence);
          contentItem.status = "approved";
          contentItem.updated_at = nowIso(sequence);
          recordAudit("review.approved", "review_task", reviewTask.id);
          return jsonResponse(reviewTask);
        },
      ],
      [
        "POST",
        /^\/api\/review\/tasks\/[^/]+\/request-rework$/,
        async (matchedPath, requestOptions) => {
          const taskId = matchedPath.split("/")[4];
          const body = JSON.parse(String(requestOptions?.body));
          const reviewTask = state.reviewTasks.find((item) => item.id === taskId);

          if (!reviewTask) {
            return jsonResponse({ detail: "Review task not found" }, 404);
          }

          const contentItem = state.contentItems.find(
            (item) => item.id === reviewTask.content_item_id,
          );
          if (!contentItem) {
            return jsonResponse({ detail: "Content item not found" }, 404);
          }

          reviewTask.status = "rework";
          reviewTask.decision_notes = body.decision_notes ?? null;
          reviewTask.completed_at = nowIso(sequence);
          reviewTask.updated_at = nowIso(sequence);
          contentItem.status = "rework";
          contentItem.updated_at = nowIso(sequence);
          recordAudit("review.rework_requested", "review_task", reviewTask.id);
          return jsonResponse(reviewTask);
        },
      ],
      ["GET", /^\/api\/workflow-presets$/, async () => jsonResponse({ items: state.workflowPresets })],
      ["GET", /^\/api\/render-jobs$/, async () => jsonResponse({ items: state.renderJobs })],
      ["GET", /^\/api\/publish-packages$/, async () => jsonResponse({ items: state.publishPackages })],
      [
        "GET",
        /^\/api\/render-jobs\/[^/]+$/,
        async (matchedPath) => {
          const renderJobId = matchedPath.split("/")[3];
          const renderJob = state.renderJobs.find((item) => item.id === renderJobId);

          if (!renderJob) {
            return jsonResponse({ detail: "Render job not found" }, 404);
          }

          return jsonResponse(renderJob);
        },
      ],
      [
        "POST",
        /^\/api\/render-jobs$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          const contentItem = state.contentItems.find((item) => item.id === body.content_item_id);
          const workflowPreset = state.workflowPresets.find(
            (item) => item.id === body.workflow_preset_id,
          );

          if (!contentItem || !workflowPreset) {
            return jsonResponse({ detail: "Render job could not be created" }, 404);
          }

          const renderJobId = nextId("render");
          const attempt: MockJobAttempt = {
            id: nextId("attempt"),
            render_job_id: renderJobId,
            attempt_number: 1,
            status: "queued",
            provider_job_id: null,
            request_payload: { inputs: { script_text: contentItem.script } },
            response_payload: {},
            error_message: null,
            started_at: null,
            finished_at: null,
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          const renderJob: MockRenderJob = {
            id: renderJobId,
            content_item_id: contentItem.id,
            workflow_preset_id: workflowPreset.id,
            workflow_preset_key: workflowPreset.key,
            workflow_preset_version: workflowPreset.version,
            workflow_provider: workflowPreset.workflow_provider,
            voice_provider: workflowPreset.voice_provider,
            packaging_provider: workflowPreset.packaging_provider,
            input_snapshot: { script_text: contentItem.script },
            status: "queued",
            retry_budget: body.retry_budget ?? 3,
            created_by_user_id: state.session?.user.id ?? "system",
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
            attempts: [attempt],
          };
          state.renderJobs.unshift(renderJob);
          recordAudit("render_job.created", "render_job", renderJob.id);
          return jsonResponse(renderJob, 201);
        },
      ],
      [
        "POST",
        /^\/api\/render-jobs\/[^/]+\/cancel$/,
        async (matchedPath) => {
          const renderJobId = matchedPath.split("/")[3];
          const renderJob = state.renderJobs.find((item) => item.id === renderJobId);
          if (!renderJob) {
            return jsonResponse({ detail: "Render job not found" }, 404);
          }
          if (!["queued", "running", "cancelled"].includes(renderJob.status)) {
            return jsonResponse({ detail: "Render job cannot be cancelled from its current status" }, 409);
          }
          renderJob.status = "cancelled";
          renderJob.updated_at = nowIso(sequence);
          renderJob.attempts.forEach((attempt) => {
            if (attempt.status === "queued" || attempt.status === "running") {
              attempt.status = "cancelled";
              attempt.error_message = attempt.error_message ?? "Cancelled by operator";
              attempt.finished_at = attempt.finished_at ?? nowIso(sequence);
              attempt.updated_at = nowIso(sequence);
            }
          });
          recordAudit("render_job.cancelled", "render_job", renderJob.id);
          return jsonResponse(renderJob);
        },
      ],
      [
        "POST",
        /^\/api\/render-jobs\/[^/]+\/retry$/,
        async (matchedPath) => {
          const renderJobId = matchedPath.split("/")[3];
          const renderJob = state.renderJobs.find((item) => item.id === renderJobId);
          if (!renderJob) {
            return jsonResponse({ detail: "Render job not found" }, 404);
          }
          if (!["failed", "cancelled"].includes(renderJob.status)) {
            return jsonResponse({ detail: "Render job can only be retried after failure or cancellation" }, 409);
          }
          const latestAttempt = [...renderJob.attempts].sort(
            (left, right) => right.attempt_number - left.attempt_number,
          )[0];
          const nextAttempt: MockJobAttempt = {
            id: nextId("attempt"),
            render_job_id: renderJob.id,
            attempt_number: latestAttempt ? latestAttempt.attempt_number + 1 : 1,
            status: "queued",
            provider_job_id: null,
            request_payload: latestAttempt?.request_payload ?? { inputs: renderJob.input_snapshot },
            response_payload: {},
            error_message: null,
            started_at: null,
            finished_at: null,
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          renderJob.status = "queued";
          renderJob.updated_at = nowIso(sequence);
          renderJob.attempts.push(nextAttempt);
          recordAudit("render_job.retried", "render_job", renderJob.id);
          return jsonResponse(renderJob);
        },
      ],
      [
        "POST",
        /^\/api\/render-jobs\/[^/]+\/requeue$/,
        async (matchedPath) => {
          const renderJobId = matchedPath.split("/")[3];
          const renderJob = state.renderJobs.find((item) => item.id === renderJobId);
          if (!renderJob) {
            return jsonResponse({ detail: "Render job not found" }, 404);
          }
          if (renderJob.status !== "queued") {
            return jsonResponse({ detail: "Render job can only be requeued while queued" }, 409);
          }
          if (!renderJob.attempts.some((attempt) => attempt.status === "queued")) {
            const latestAttempt = [...renderJob.attempts].sort(
              (left, right) => right.attempt_number - left.attempt_number,
            )[0];
            renderJob.attempts.push({
              id: nextId("attempt"),
              render_job_id: renderJob.id,
              attempt_number: latestAttempt ? latestAttempt.attempt_number + 1 : 1,
              status: "queued",
              provider_job_id: null,
              request_payload: latestAttempt?.request_payload ?? { inputs: renderJob.input_snapshot },
              response_payload: {},
              error_message: null,
              started_at: null,
              finished_at: null,
              created_at: nowIso(sequence),
              updated_at: nowIso(sequence),
            });
          }
          recordAudit("render_job.requeued", "render_job", renderJob.id);
          return jsonResponse(renderJob);
        },
      ],
      [
        "POST",
        /^\/api\/publish-packages$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          const renderJob = state.renderJobs.find((item) => item.id === body.render_job_id);
          if (!renderJob || renderJob.status !== "succeeded") {
            return jsonResponse({ detail: "Render job must succeed before package export" }, 409);
          }

          const existingPackage = state.publishPackages.find(
            (publishPackage) => publishPackage.render_job_id === renderJob.id,
          );
          if (existingPackage) {
            return jsonResponse(existingPackage);
          }

          const publishPackage: MockPublishPackage = {
            id: nextId("package"),
            render_job_id: renderJob.id,
            content_item_id: renderJob.content_item_id,
            status: "queued",
            package_object_key: null,
            manifest_payload: {},
            byte_size: null,
            error_message: null,
            created_by_user_id: state.session?.user.id ?? "system",
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.publishPackages.unshift(publishPackage);
          recordAudit("publish_package.created", "publish_package", publishPackage.id);
          return jsonResponse(publishPackage, 201);
        },
      ],
      [
        "POST",
        /^\/api\/publish-packages\/[^/]+\/cancel$/,
        async (matchedPath) => {
          const packageId = matchedPath.split("/")[3];
          const publishPackage = state.publishPackages.find((item) => item.id === packageId);
          if (!publishPackage) {
            return jsonResponse({ detail: "Publish package not found" }, 404);
          }
          if (!["queued", "running", "cancelled"].includes(publishPackage.status)) {
            return jsonResponse({ detail: "Publish package cannot be cancelled from its current status" }, 409);
          }
          publishPackage.status = "cancelled";
          publishPackage.error_message = publishPackage.error_message ?? "Cancelled by operator";
          publishPackage.updated_at = nowIso(sequence);
          recordAudit("publish_package.cancelled", "publish_package", publishPackage.id);
          return jsonResponse(publishPackage);
        },
      ],
      [
        "POST",
        /^\/api\/publish-packages\/[^/]+\/retry$/,
        async (matchedPath) => {
          const packageId = matchedPath.split("/")[3];
          const publishPackage = state.publishPackages.find((item) => item.id === packageId);
          if (!publishPackage) {
            return jsonResponse({ detail: "Publish package not found" }, 404);
          }
          if (!["failed", "cancelled"].includes(publishPackage.status)) {
            return jsonResponse({ detail: "Publish package can only be retried after failure or cancellation" }, 409);
          }
          publishPackage.status = "queued";
          publishPackage.package_object_key = null;
          publishPackage.manifest_payload = {};
          publishPackage.byte_size = null;
          publishPackage.error_message = null;
          publishPackage.updated_at = nowIso(sequence);
          recordAudit("publish_package.retried", "publish_package", publishPackage.id);
          return jsonResponse(publishPackage);
        },
      ],
      [
        "POST",
        /^\/api\/publish-packages\/[^/]+\/requeue$/,
        async (matchedPath) => {
          const packageId = matchedPath.split("/")[3];
          const publishPackage = state.publishPackages.find((item) => item.id === packageId);
          if (!publishPackage) {
            return jsonResponse({ detail: "Publish package not found" }, 404);
          }
          if (publishPackage.status !== "queued") {
            return jsonResponse({ detail: "Publish package can only be requeued while queued" }, 409);
          }
          recordAudit("publish_package.requeued", "publish_package", publishPackage.id);
          return jsonResponse(publishPackage);
        },
      ],
      [
        "GET",
        /^\/api\/publish-packages\/[^/]+\/download$/,
        async (matchedPath) => {
          const packageId = matchedPath.split("/")[3];
          const publishPackage = state.publishPackages.find((item) => item.id === packageId);
          if (!publishPackage || publishPackage.status !== "ready") {
            return jsonResponse({ detail: "Publish package is not ready for download" }, 409);
          }
          return jsonResponse({
            package: publishPackage,
            download: {
              method: "GET",
              url: `http://localhost:9000/content-factory-assets/${publishPackage.package_object_key}?signature=demo`,
              headers: {},
              expires_at: nowIso(30),
            },
          });
        },
      ],
      [
        "GET",
        /^\/api\/audit\/logs$/,
        async () => {
          if (state.session?.user.role === "reviewer" || state.session?.user.role === "viewer") {
            return jsonResponse({ detail: "Forbidden" }, 403);
          }

          return jsonResponse({ items: state.auditLogs });
        },
      ],
    ];

    const handler = handlers.find(
      ([candidateMethod, pattern]) =>
        candidateMethod === normalizedMethod && pattern.test(url.pathname),
    );

    if (!handler) {
      throw new Error(`Unhandled request: ${normalizedMethod} ${path}`);
    }

    return handler[2](url.pathname, options, state);
  });

  vi.stubGlobal("fetch", fetchMock);
  return { state, fetchMock };
}

beforeEach(() => {
  window.location.hash = "";
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("App", () => {
  test("shows the auth gate and bootstraps the first owner", async () => {
    installMockApi();

    render(<App />);

    expect(await screen.findByRole("heading", { name: /content factory control plane/i })).toBeVisible();

    fireEvent.click(screen.getByRole("tab", { name: /bootstrap owner/i }));
    fireEvent.click(screen.getByRole("button", { name: /create first owner/i }));

    expect(await screen.findByText(/owner bootstrapped and signed in/i)).toBeVisible();
    expect(await screen.findByRole("heading", { name: /operator command posture/i })).toBeVisible();
    expect(
      (await screen.findAllByText(/create the first brand to open the intake and drafting loop/i))
        .length,
    ).toBeGreaterThan(0);
  });

  test("runs the pilot cockpit flow from brand creation to render queue", async () => {
    installMockApi({ session: createOwnerSession(), workflowPresets: [createWorkflowPreset()] });
    window.location.hash = "#brands-assets";

    render(<App />);

    expect(await screen.findByRole("heading", { name: /control voice and guardrails/i })).toBeVisible();

    fireEvent.change(screen.getByLabelText(/brand name/i), { target: { value: "Inflave" } });
    fireEvent.change(screen.getByLabelText(/voice notes/i), {
      target: { value: "Confident, compliant, concise." },
    });
    fireEvent.click(screen.getByRole("button", { name: /create brand/i }));

    expect(await screen.findByText(/brand created\./i)).toBeVisible();
    expect(await screen.findByRole("heading", { name: /^Inflave$/i })).toBeVisible();

    const file = new File(["pilot-reference"], "script-reference.png", { type: "image/png" });
    fireEvent.change(screen.getByLabelText(/upload file/i), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: /upload asset/i }));

    expect(await screen.findByText(/asset uploaded and finalized\./i)).toBeVisible();
    expect(await screen.findByText(/script-reference\.png/i)).toBeVisible();
    expect(await screen.findByText(/^ready$/i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /avatars/i }));
    expect(await screen.findByRole("heading", { name: /anchor the pilot persona/i })).toBeVisible();

    fireEvent.change(screen.getByLabelText(/avatar name/i), { target: { value: "Primary Host" } });
    fireEvent.change(screen.getByLabelText(/persona notes/i), {
      target: { value: "Human-like pilot avatar." },
    });
    fireEvent.click(screen.getByRole("button", { name: /create avatar/i }));

    expect(await screen.findByText(/avatar created\./i)).toBeVisible();
    await waitFor(() => {
      expect(screen.getAllByText("Primary Host").length).toBeGreaterThan(0);
    });

    fireEvent.change(screen.getByLabelText(/identity pack name/i), {
      target: { value: "Core identity" },
    });
    fireEvent.change(screen.getByLabelText(/^description$/i), {
      target: { value: "Pilot voice and look references." },
    });
    fireEvent.change(screen.getByLabelText(/storage prefix/i), {
      target: { value: "identity/core" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create identity pack/i }));

    expect(await screen.findByText(/identity pack created\./i)).toBeVisible();
    await waitFor(() => {
      expect(screen.getAllByText("Core identity").length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getByRole("button", { name: /content/i }));
    expect(await screen.findByRole("heading", { name: /turn scripts into reviewable items/i })).toBeVisible();

    fireEvent.change(screen.getByLabelText(/content title/i), { target: { value: "Pilot short" } });
    fireEvent.change(screen.getByLabelText(/^script$/i), {
      target: { value: "A careful, platform-safe short script." },
    });
    fireEvent.click(screen.getByRole("button", { name: /create content item/i }));

    expect(await screen.findByText(/content item created\./i)).toBeVisible();
    expect(await screen.findByRole("heading", { name: /^Pilot short$/i })).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /^plan$/i }));
    expect(await screen.findByText(/content item planned\./i)).toBeVisible();
    expect(await screen.findByText(/^planned$/i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /send to review/i }));
    expect(await screen.findByText(/content item submitted for review\./i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /^review$/i }));
    expect(await screen.findByRole("heading", { name: /human approvals stay in the loop/i })).toBeVisible();

    fireEvent.change(screen.getByLabelText(/decision notes/i), {
      target: { value: "Approved for manual publishing." },
    });
    fireEvent.click(screen.getByRole("button", { name: /^approve$/i }));

    expect(await screen.findByText(/review task approved\./i)).toBeVisible();
    expect(await screen.findByText(/approved for manual publishing\./i)).toBeVisible();
    expect(await screen.findByText(/^approved$/i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /^audit$/i }));
    expect(await screen.findByRole("heading", { name: /recent control-plane actions/i })).toBeVisible();
    await waitFor(() => {
      expect(screen.getByText(/review\.approved/i)).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: /^render$/i }));
    expect(await screen.findByRole("heading", { name: /render queue/i })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /create render job/i }));

    expect(await screen.findByText(/render job created\./i)).toBeVisible();
    expect((await screen.findAllByText(/pilot-reels v1/i)).length).toBeGreaterThan(0);
    expect((await screen.findAllByText(/^queued$/i)).length).toBeGreaterThan(0);
  });

  test("runs render job operator actions", async () => {
    const contentItem: MockContentItem = {
      id: "content-planned",
      brand_id: "brand-1",
      avatar_id: "avatar-1",
      title: "Pilot short",
      script: "A careful, platform-safe short script.",
      channel: "youtube_shorts",
      status: "planned",
      planned_publish_at: null,
      created_by_user_id: "user-owner",
      created_at: nowIso(0),
      updated_at: nowIso(0),
    };
    const workflowPreset = createWorkflowPreset();
    const renderJob: MockRenderJob = {
      id: "render-queued",
      content_item_id: contentItem.id,
      workflow_preset_id: workflowPreset.id,
      workflow_preset_key: workflowPreset.key,
      workflow_preset_version: workflowPreset.version,
      workflow_provider: workflowPreset.workflow_provider,
      voice_provider: workflowPreset.voice_provider,
      packaging_provider: workflowPreset.packaging_provider,
      input_snapshot: { script_text: contentItem.script },
      status: "queued",
      retry_budget: 1,
      created_by_user_id: "user-owner",
      created_at: nowIso(1),
      updated_at: nowIso(2),
      attempts: [
        {
          id: "attempt-1",
          render_job_id: "render-queued",
          attempt_number: 1,
          status: "queued",
          provider_job_id: null,
          request_payload: { inputs: { script_text: contentItem.script } },
          response_payload: {},
          error_message: null,
          started_at: null,
          finished_at: null,
          created_at: nowIso(1),
          updated_at: nowIso(2),
        },
      ],
    };
    installMockApi({
      session: createOwnerSession(),
      contentItems: [contentItem],
      workflowPresets: [workflowPreset],
      renderJobs: [renderJob],
    });
    window.location.hash = "#render";

    render(<App />);

    expect(await screen.findByRole("heading", { name: /render queue/i })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /requeue job/i }));
    expect(await screen.findByText(/render job requeued\./i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /cancel job/i }));
    expect(await screen.findByText(/render job cancelled\./i)).toBeVisible();
    expect((await screen.findAllByText(/^cancelled$/i)).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /retry job/i }));
    expect(await screen.findByText(/render job retried\./i)).toBeVisible();
    expect((await screen.findAllByText(/^queued$/i)).length).toBeGreaterThan(0);
  });

  test("prepares a publish package from a succeeded approved render", async () => {
    const contentItem: MockContentItem = {
      id: "content-approved",
      brand_id: "brand-1",
      avatar_id: "avatar-1",
      title: "Pilot short",
      script: "A careful, platform-safe short script.",
      channel: "youtube_shorts",
      status: "approved",
      planned_publish_at: null,
      created_by_user_id: "user-owner",
      created_at: nowIso(0),
      updated_at: nowIso(0),
    };
    const workflowPreset = createWorkflowPreset();
    const renderJob: MockRenderJob = {
      id: "render-succeeded",
      content_item_id: contentItem.id,
      workflow_preset_id: workflowPreset.id,
      workflow_preset_key: workflowPreset.key,
      workflow_preset_version: workflowPreset.version,
      workflow_provider: workflowPreset.workflow_provider,
      voice_provider: workflowPreset.voice_provider,
      packaging_provider: workflowPreset.packaging_provider,
      input_snapshot: { script_text: contentItem.script },
      status: "succeeded",
      retry_budget: 3,
      created_by_user_id: "user-owner",
      created_at: nowIso(1),
      updated_at: nowIso(2),
      attempts: [
        {
          id: "attempt-1",
          render_job_id: "render-succeeded",
          attempt_number: 1,
          status: "succeeded",
          provider_job_id: "comfyui-1",
          request_payload: { inputs: { script_text: contentItem.script } },
          response_payload: {
            outputs: { video_file: "s3://content-factory-assets/renders/video.mp4" },
          },
          error_message: null,
          started_at: nowIso(1),
          finished_at: nowIso(2),
          created_at: nowIso(1),
          updated_at: nowIso(2),
        },
      ],
    };
    installMockApi({
      session: createOwnerSession(),
      contentItems: [contentItem],
      workflowPresets: [workflowPreset],
      renderJobs: [renderJob],
    });
    window.location.hash = "#export";

    render(<App />);

    expect(await screen.findByRole("heading", { name: /publish packages/i })).toBeVisible();
    expect((await screen.findAllByText(/pilot-reels v1/i)).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: /create package/i }));

    expect(await screen.findByText(/publish package queued\./i)).toBeVisible();
    expect(
      await screen.findByText(/no succeeded approved renders waiting for package export/i),
    ).toBeVisible();
    expect((await screen.findAllByText(/^queued$/i)).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /requeue package/i }));
    expect(await screen.findByText(/publish package requeued\./i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /cancel package/i }));
    expect(await screen.findByText(/publish package cancelled\./i)).toBeVisible();
    expect((await screen.findAllByText(/^cancelled$/i)).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /retry package/i }));
    expect(await screen.findByText(/publish package retried\./i)).toBeVisible();
    expect((await screen.findAllByText(/^queued$/i)).length).toBeGreaterThan(0);
  });
});
