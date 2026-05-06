import type { components } from "@content-factory/contracts";

export type User = components["schemas"]["UserRead"];
export type UserRole = User["role"];
export type AuthSession = components["schemas"]["AuthSessionRead"];
export type Brand = components["schemas"]["BrandRead"];
export type Avatar = components["schemas"]["AvatarRead"];
export type IdentityPack = components["schemas"]["IdentityPackRead"];
export type Asset = components["schemas"]["AssetRead"];
export type ReviewTask = components["schemas"]["ReviewTaskRead"];
export type ContentItem = components["schemas"]["ContentItemRead"];
export type ContentChannel = components["schemas"]["ContentChannel"];
export type AuditLog = components["schemas"]["AuditLogRead"];
export type InviteRole = components["schemas"]["InviteCreateRequest"]["role"];
export type Invite = components["schemas"]["InviteCreateResponse"];
export type InviteCreateResponse = components["schemas"]["InviteCreateResponse"];
export type UploadTarget = components["schemas"]["UploadTargetRead"];
export type AssetUploadInitiateResponse = components["schemas"]["AssetUploadInitiateResponse"];

export type BootstrapOwnerRequest = components["schemas"]["BootstrapOwnerRequest"];
export type LoginRequest = components["schemas"]["LoginRequest"];
export type InviteAcceptRequest = components["schemas"]["InviteAcceptRequest"];
export type InviteCreateRequest = components["schemas"]["InviteCreateRequest"];
export type BrandCreateRequest = components["schemas"]["BrandCreateRequest"];
export type AvatarCreateRequest = components["schemas"]["AvatarCreateRequest"];
export type IdentityPackCreateRequest = components["schemas"]["IdentityPackCreateRequest"];
export type AssetUploadInitiateRequest = components["schemas"]["AssetUploadInitiateRequest"];
export type AssetFinalizeRequest = components["schemas"]["AssetFinalizeRequest"];
export type ContentItemCreateRequest = components["schemas"]["ContentItemCreateRequest"];
export type ContentPlanRequest = components["schemas"]["ContentPlanRequest"];
export type ReviewDecisionRequest = components["schemas"]["ReviewDecisionRequest"];

export interface CockpitData {
  brands: Brand[];
  avatars: Avatar[];
  identityPacks: IdentityPack[];
  assets: Asset[];
  contentItems: ContentItem[];
  reviewTasks: ReviewTask[];
  auditLogs: AuditLog[];
}

export const emptyCockpitData: CockpitData = {
  brands: [],
  avatars: [],
  identityPacks: [],
  assets: [],
  contentItems: [],
  reviewTasks: [],
  auditLogs: [],
};
