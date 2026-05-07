import { webEnv } from "../../config/env";
import { resolveUploadUrl } from "./upload";
import type {
  AssetFinalizeRequest,
  Asset,
  AssetUploadInitiateRequest,
  AssetUploadInitiateResponse,
  AuditLog,
  AuthSession,
  Avatar,
  AvatarCreateRequest,
  BootstrapOwnerRequest,
  Brand,
  BrandCreateRequest,
  ComplianceCheck,
  ContentItem,
  ContentItemCreateRequest,
  ContentPlanRequest,
  IdentityPack,
  IdentityPackCreateRequest,
  InviteAcceptRequest,
  LoginRequest,
  Invite,
  InviteCreateRequest,
  RenderJob,
  RenderJobCreateRequest,
  PublishPackage,
  PublishPackageCreateRequest,
  PublishPackageDownloadResponse,
  ReviewDecisionRequest,
  ReviewTask,
  User,
  WorkflowPreset,
} from "./types";

export class ApiError extends Error {
  status: number;

  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function isAbsoluteUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

function resolveApiUrl(path: string): string {
  if (isAbsoluteUrl(path)) {
    return path;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (isAbsoluteUrl(webEnv.VITE_API_BASE_URL)) {
    return new URL(normalizedPath, `${webEnv.VITE_API_BASE_URL.replace(/\/+$/, "")}/`).toString();
  }

  if (webEnv.VITE_API_BASE_URL === "/") {
    return normalizedPath;
  }

  return `${webEnv.VITE_API_BASE_URL.replace(/\/+$/, "")}${normalizedPath}`;
}

async function readResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type");

  if (contentType?.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

function errorDetailFromBody(body: unknown): string {
  if (typeof body === "string" && body.trim().length > 0) {
    return body;
  }

  if (
    body &&
    typeof body === "object" &&
    "detail" in body &&
    typeof body.detail === "string" &&
    body.detail.trim().length > 0
  ) {
    return body.detail;
  }

  if (body && typeof body === "object" && "detail" in body && Array.isArray(body.detail)) {
    return body.detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
          return item.msg;
        }

        return "Validation error";
      })
      .join("; ");
  }

  return "Request failed";
}

async function requestJson<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
  const response = await fetch(resolveApiUrl(path), {
    credentials: "include",
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
  });
  const body = await readResponseBody(response);

  if (!response.ok) {
    throw new ApiError(response.status, errorDetailFromBody(body));
  }

  return body as TResponse;
}

function postJson<TRequest, TResponse>(path: string, body: TRequest): Promise<TResponse> {
  return requestJson<TResponse>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

function getList<TItem>(path: string): Promise<{ items: TItem[] }> {
  return requestJson<{ items: TItem[] }>(path);
}

export function describeApiBase(): string {
  return webEnv.VITE_API_BASE_URL === "/" ? "Same-origin proxy (/api)" : webEnv.VITE_API_BASE_URL;
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export const apiClient = {
  getSession() {
    return requestJson<AuthSession>("/api/auth/session");
  },
  login(payload: LoginRequest) {
    return postJson<LoginRequest, AuthSession>("/api/auth/login", payload);
  },
  bootstrapOwner(payload: BootstrapOwnerRequest) {
    return postJson<BootstrapOwnerRequest, AuthSession>("/api/auth/bootstrap-owner", payload);
  },
  acceptInvite(payload: InviteAcceptRequest) {
    return postJson<InviteAcceptRequest, AuthSession>("/api/auth/invites/accept", payload);
  },
  logout() {
    return requestJson<{ status: string }>("/api/auth/logout", { method: "POST" });
  },
  createInvite(payload: InviteCreateRequest) {
    return postJson<InviteCreateRequest, Invite>("/api/auth/invites", payload);
  },
  listUsers() {
    return getList<User>("/api/users");
  },
  listBrands() {
    return getList<Brand>("/api/brands");
  },
  createBrand(payload: BrandCreateRequest) {
    return postJson<BrandCreateRequest, Brand>("/api/brands", payload);
  },
  listAvatars() {
    return getList<Avatar>("/api/avatars");
  },
  createAvatar(payload: AvatarCreateRequest) {
    return postJson<AvatarCreateRequest, Avatar>("/api/avatars", payload);
  },
  listIdentityPacks(avatarId: string) {
    return getList<IdentityPack>(`/api/avatars/${avatarId}/identity-packs`);
  },
  createIdentityPack(avatarId: string, payload: IdentityPackCreateRequest) {
    return postJson<IdentityPackCreateRequest, IdentityPack>(
      `/api/avatars/${avatarId}/identity-packs`,
      payload,
    );
  },
  listAssets() {
    return getList<Asset>("/api/assets");
  },
  initiateUpload(payload: AssetUploadInitiateRequest) {
    return postJson<AssetUploadInitiateRequest, AssetUploadInitiateResponse>("/api/assets/uploads", payload);
  },
  finalizeUpload(assetId: string, payload: AssetFinalizeRequest) {
    return postJson<AssetFinalizeRequest, Asset>(`/api/assets/${assetId}/finalize`, payload);
  },
  listContentItems() {
    return getList<ContentItem>("/api/content-items");
  },
  createContentItem(payload: ContentItemCreateRequest) {
    return postJson<ContentItemCreateRequest, ContentItem>("/api/content-items", payload);
  },
  planContentItem(contentItemId: string, payload: ContentPlanRequest) {
    return postJson<ContentPlanRequest, ContentItem>(`/api/content-items/${contentItemId}/plan`, payload);
  },
  submitContentForReview(contentItemId: string) {
    return requestJson<ReviewTask>(`/api/content-items/${contentItemId}/submit-review`, { method: "POST" });
  },
  submitContentItemForReview(contentItemId: string) {
    return requestJson<ReviewTask>(`/api/content-items/${contentItemId}/submit-review`, { method: "POST" });
  },
  listReviewTasks() {
    return getList<ReviewTask>("/api/review/tasks");
  },
  listComplianceChecks() {
    return getList<ComplianceCheck>("/api/compliance/checks");
  },
  rerunComplianceCheck(contentItemId: string) {
    return requestJson<ComplianceCheck>(`/api/compliance/content-items/${contentItemId}/checks`, {
      method: "POST",
    });
  },
  listWorkflowPresets() {
    return getList<WorkflowPreset>("/api/workflow-presets");
  },
  listRenderJobs() {
    return getList<RenderJob>("/api/render-jobs");
  },
  getRenderJob(renderJobId: string) {
    return requestJson<RenderJob>(`/api/render-jobs/${renderJobId}`);
  },
  createRenderJob(payload: RenderJobCreateRequest) {
    return postJson<RenderJobCreateRequest, RenderJob>("/api/render-jobs", payload);
  },
  cancelRenderJob(renderJobId: string) {
    return requestJson<RenderJob>(`/api/render-jobs/${renderJobId}/cancel`, { method: "POST" });
  },
  retryRenderJob(renderJobId: string) {
    return requestJson<RenderJob>(`/api/render-jobs/${renderJobId}/retry`, { method: "POST" });
  },
  requeueRenderJob(renderJobId: string) {
    return requestJson<RenderJob>(`/api/render-jobs/${renderJobId}/requeue`, { method: "POST" });
  },
  renderJobEventsUrl(renderJobId: string) {
    return resolveApiUrl(`/api/render-jobs/${renderJobId}/events`);
  },
  listPublishPackages() {
    return getList<PublishPackage>("/api/publish-packages");
  },
  createPublishPackage(payload: PublishPackageCreateRequest) {
    return postJson<PublishPackageCreateRequest, PublishPackage>("/api/publish-packages", payload);
  },
  cancelPublishPackage(packageId: string) {
    return requestJson<PublishPackage>(`/api/publish-packages/${packageId}/cancel`, { method: "POST" });
  },
  retryPublishPackage(packageId: string) {
    return requestJson<PublishPackage>(`/api/publish-packages/${packageId}/retry`, { method: "POST" });
  },
  requeuePublishPackage(packageId: string) {
    return requestJson<PublishPackage>(`/api/publish-packages/${packageId}/requeue`, { method: "POST" });
  },
  getPublishPackageDownload(packageId: string) {
    return requestJson<PublishPackageDownloadResponse>(`/api/publish-packages/${packageId}/download`);
  },
  approveReviewTask(taskId: string, payload: ReviewDecisionRequest) {
    return postJson<ReviewDecisionRequest, ReviewTask>(`/api/review/tasks/${taskId}/approve`, payload);
  },
  requestReviewRework(taskId: string, payload: ReviewDecisionRequest) {
    return postJson<ReviewDecisionRequest, ReviewTask>(
      `/api/review/tasks/${taskId}/request-rework`,
      payload,
    );
  },
  requestRework(taskId: string, payload: ReviewDecisionRequest) {
    return postJson<ReviewDecisionRequest, ReviewTask>(
      `/api/review/tasks/${taskId}/request-rework`,
      payload,
    );
  },
  listAuditLogs(limit = 100) {
    return getList<AuditLog>(`/api/audit/logs?limit=${limit}`);
  },
  async uploadAsset(file: File, payload: AssetUploadInitiateRequest): Promise<Asset> {
    const initiated = await postJson<AssetUploadInitiateRequest, AssetUploadInitiateResponse>(
      "/api/assets/uploads",
      payload,
    );

    const uploadResponse = await fetch(resolveUploadUrl(initiated.upload.url), {
      method: initiated.upload.method,
      headers: initiated.upload.headers,
      body: file,
    });

    if (!uploadResponse.ok) {
      throw new ApiError(uploadResponse.status, "Asset upload could not be completed");
    }

    return postJson<AssetFinalizeRequest, Asset>(`/api/assets/${initiated.asset.id}/finalize`, {
      byte_size: file.size || initiated.asset.byte_size || 1,
      checksum_sha256: null,
    });
  },
};
