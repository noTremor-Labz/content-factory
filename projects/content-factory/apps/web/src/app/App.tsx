import "./App.css";

import { startTransition, useCallback, useEffect, useState } from "react";

import { AuthPanel } from "../features/auth/AuthPanel";
import { AuditPanel } from "../features/audit/AuditPanel";
import { AvatarsPanel } from "../features/avatars/AvatarsPanel";
import { BrandsAssetsPanel } from "../features/brands-assets/BrandsAssetsPanel";
import { ContentPanel } from "../features/content/ContentPanel";
import { ExportPanel } from "../features/export/ExportPanel";
import { RenderPanel } from "../features/render/RenderPanel";
import { ReviewPanel } from "../features/review/ReviewPanel";
import { webEnv } from "../config/env";
import { apiClient, describeApiBase, isApiError } from "../shared/api/client";
import {
  emptyCockpitData,
  type AuthSession,
  type CockpitData,
  type RenderJob,
  type UserRole,
} from "../shared/api/types";
import { formatDateTime } from "../shared/format";
import { cockpitRoutes, normalizeCockpitRoute, toCockpitHash, type CockpitRouteId } from "./routes";

type SessionState =
  | { kind: "loading" }
  | { kind: "anonymous" }
  | { kind: "authenticated"; session: AuthSession };

interface RenderJobStatusEvent {
  event: "render_job.snapshot";
  render_job: RenderJob;
}

function canMutateRole(role: UserRole): boolean {
  return role === "owner" || role === "operator";
}

function canReviewRole(role: UserRole): boolean {
  return role === "owner" || role === "reviewer";
}

function canViewAuditRole(role: UserRole): boolean {
  return role === "owner" || role === "operator";
}

function messageFromError(error: unknown): string {
  if (isApiError(error)) {
    return error.detail;
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }

  return "Unexpected error";
}

function readHashRoute(): CockpitRouteId {
  if (typeof window === "undefined") {
    return "overview";
  }

  return normalizeCockpitRoute(window.location.hash.replace(/^#/, ""));
}

function countByStatus<TItem extends { status: string }>(items: TItem[], status: string): number {
  return items.filter((item) => item.status === status).length;
}

function nextStepForData(data: CockpitData): string {
  if (data.brands.length === 0) {
    return "Create the first brand to open the intake and drafting loop.";
  }

  if (data.avatars.length === 0) {
    return "Add the pilot avatar so drafts can be attached to a concrete host persona.";
  }

  if (data.contentItems.length === 0) {
    return "Draft the first short-form content item and push it into review.";
  }

  if (countByStatus(data.reviewTasks, "open") > 0) {
    return "Review queue has open decisions waiting for a human approver.";
  }

  if (countByStatus(data.contentItems, "approved") > 0 && data.renderJobs.length === 0) {
    return "Approved content is ready for its first render job.";
  }

  if (
    data.renderJobs.some((renderJob) => renderJob.status === "succeeded") &&
    data.publishPackages.length === 0
  ) {
    return "Succeeded renders are ready for export packaging.";
  }

  return "Cockpit is ready for the next operator pass.";
}

export function App() {
  const [route, setRoute] = useState<CockpitRouteId>(readHashRoute);
  const [sessionState, setSessionState] = useState<SessionState>({ kind: "loading" });
  const [cockpitData, setCockpitData] = useState<CockpitData>(emptyCockpitData);
  const [busyLabel, setBusyLabel] = useState<string | null>(null);
  const [screenError, setScreenError] = useState<string | null>(null);
  const [flashMessage, setFlashMessage] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [liveRenderJobId, setLiveRenderJobId] = useState<string | null>(null);

  const refreshCockpit = useCallback(async (role: UserRole) => {
    const [
      brandsResponse,
      avatarsResponse,
      assetsResponse,
      contentResponse,
      reviewResponse,
      workflowPresetsResponse,
      renderJobsResponse,
      publishPackagesResponse,
    ] =
      await Promise.all([
        apiClient.listBrands(),
        apiClient.listAvatars(),
        apiClient.listAssets(),
        apiClient.listContentItems(),
        apiClient.listReviewTasks(),
        apiClient.listWorkflowPresets(),
        apiClient.listRenderJobs(),
        apiClient.listPublishPackages(),
      ]);

    const identityPackLists = await Promise.all(
      avatarsResponse.items.map((avatar) => apiClient.listIdentityPacks(avatar.id)),
    );

    let auditLogs = emptyCockpitData.auditLogs;
    if (canViewAuditRole(role)) {
      try {
        auditLogs = (await apiClient.listAuditLogs()).items;
      } catch (error) {
        if (!isApiError(error) || error.status !== 403) {
          throw error;
        }
      }
    }

    startTransition(() => {
      setCockpitData({
        brands: brandsResponse.items,
        avatars: avatarsResponse.items,
        identityPacks: identityPackLists.flatMap((response) => response.items),
        assets: assetsResponse.items,
        contentItems: contentResponse.items,
        reviewTasks: reviewResponse.items,
        auditLogs,
        workflowPresets: workflowPresetsResponse.items,
        renderJobs: renderJobsResponse.items,
        publishPackages: publishPackagesResponse.items,
      });
    });
  }, []);

  const loadSession = useCallback(async () => {
    setScreenError(null);
    setFlashMessage(null);
    setIsRefreshing(true);

    try {
      const session = await apiClient.getSession();
      startTransition(() => {
        setSessionState({ kind: "authenticated", session });
      });
      await refreshCockpit(session.user.role);
    } catch (error) {
      if (isApiError(error) && error.status === 401) {
        startTransition(() => {
          setSessionState({ kind: "anonymous" });
          setCockpitData(emptyCockpitData);
        });
      } else {
        startTransition(() => {
          setSessionState({ kind: "anonymous" });
          setCockpitData(emptyCockpitData);
        });
        setScreenError(messageFromError(error));
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [refreshCockpit]);

  useEffect(() => {
    let cancelled = false;
    void Promise.resolve().then(() => {
      if (!cancelled) {
        void loadSession();
      }
    });
    return () => {
      cancelled = true;
    };
  }, [loadSession]);

  useEffect(() => {
    const syncRoute = () => {
      setRoute(readHashRoute());
    };

    syncRoute();
    window.addEventListener("hashchange", syncRoute);
    return () => window.removeEventListener("hashchange", syncRoute);
  }, []);

  useEffect(() => {
    if (
      sessionState.kind !== "authenticated" ||
      liveRenderJobId === null ||
      typeof EventSource === "undefined"
    ) {
      return;
    }

    const source = new EventSource(apiClient.renderJobEventsUrl(liveRenderJobId), {
      withCredentials: true,
    });
    const handleSnapshot = (event: MessageEvent<string>) => {
      const payload = JSON.parse(event.data) as RenderJobStatusEvent;
      setCockpitData((current) => ({
        ...current,
        renderJobs: [
          payload.render_job,
          ...current.renderJobs.filter((renderJob) => renderJob.id !== payload.render_job.id),
        ],
      }));

      if (["succeeded", "failed", "cancelled"].includes(payload.render_job.status)) {
        source.close();
      }
    };

    source.addEventListener("render_job.snapshot", handleSnapshot as EventListener);
    source.onerror = () => source.close();
    return () => source.close();
  }, [liveRenderJobId, sessionState.kind]);

  async function completeAuthentication(session: AuthSession, successMessage: string) {
    setScreenError(null);
    setFlashMessage(successMessage);
    setIsRefreshing(true);
    startTransition(() => {
      setSessionState({ kind: "authenticated", session });
    });

    try {
      await refreshCockpit(session.user.role);
    } catch (error) {
      setScreenError(messageFromError(error));
    } finally {
      setIsRefreshing(false);
    }
  }

  async function runSessionAction(
    label: string,
    action: () => Promise<AuthSession>,
    successMessage: string,
  ) {
    setBusyLabel(label);
    setScreenError(null);
    setFlashMessage(null);

    try {
      const session = await action();
      await completeAuthentication(session, successMessage);
    } catch (error) {
      setScreenError(messageFromError(error));
    } finally {
      setBusyLabel(null);
    }
  }

  async function runCockpitMutation(
    label: string,
    action: () => Promise<unknown>,
    successMessage: string,
  ) {
    if (sessionState.kind !== "authenticated") {
      return;
    }

    setBusyLabel(label);
    setScreenError(null);
    setFlashMessage(null);

    try {
      await action();
      setIsRefreshing(true);
      await refreshCockpit(sessionState.session.user.role);
      setFlashMessage(successMessage);
    } catch (error) {
      setScreenError(messageFromError(error));
    } finally {
      setBusyLabel(null);
      setIsRefreshing(false);
    }
  }

  if (sessionState.kind === "loading") {
    return (
      <main className="loading-shell">
        <div className="surface loading-card">
          <p className="eyebrow">Phase 1 cockpit</p>
          <h1>Loading session</h1>
          <p className="panel-copy">Checking the current operator cookie and restoring the cockpit.</p>
        </div>
      </main>
    );
  }

  if (sessionState.kind === "anonymous") {
    return (
      <main className="shell">
        <AuthPanel
          appName={webEnv.VITE_APP_NAME}
          apiBaseLabel={describeApiBase()}
          busy={busyLabel !== null}
          error={screenError}
          onLogin={(payload) =>
            runSessionAction("login", () => apiClient.login(payload), "Session opened.")
          }
          onBootstrapOwner={(payload) =>
            runSessionAction(
              "bootstrap owner",
              () => apiClient.bootstrapOwner(payload),
              "Owner bootstrapped and signed in.",
            )
          }
          onAcceptInvite={(payload) =>
            runSessionAction(
              "accept invite",
              () => apiClient.acceptInvite(payload),
              "Invite accepted and session opened.",
            )
          }
        />
      </main>
    );
  }

  const { session } = sessionState;
  const canMutate = canMutateRole(session.user.role);
  const canReview = canReviewRole(session.user.role);
  const canViewAudit = canViewAuditRole(session.user.role);
  const readyAssets = countByStatus(cockpitData.assets, "ready");
  const openReviewTasks = countByStatus(cockpitData.reviewTasks, "open");

  return (
    <main className="shell cockpit-shell">
      <section className="hero surface">
        <div>
          <p className="eyebrow">Protected control plane</p>
          <h1>{webEnv.VITE_APP_NAME}</h1>
          <p className="lede">{nextStepForData(cockpitData)}</p>
        </div>

        <div className="hero-side">
          <article className="session-card">
            <span className="meta-label">Signed in as</span>
            <strong>{session.user.display_name}</strong>
            <p>
              {session.user.email} · {session.user.role}
            </p>
            <p>Session expires {formatDateTime(session.expires_at)}</p>
            <button
              className="ghost-button"
              disabled={busyLabel !== null}
              type="button"
              onClick={async () => {
                setBusyLabel("logout");
                setScreenError(null);
                setFlashMessage(null);

                try {
                  await apiClient.logout();
                  startTransition(() => {
                    setSessionState({ kind: "anonymous" });
                    setCockpitData(emptyCockpitData);
                  });
                } catch (error) {
                  setScreenError(messageFromError(error));
                } finally {
                  setBusyLabel(null);
                }
              }}
            >
              Sign out
            </button>
          </article>

          <article className="session-card">
            <span className="meta-label">Integration target</span>
            <strong>{describeApiBase()}</strong>
            <p>Role gates: mutate {canMutate ? "enabled" : "disabled"} · review {canReview ? "enabled" : "disabled"}</p>
          </article>
        </div>
      </section>

      <section className="summary-grid">
        <article className="metric-card surface">
          <span className="metric-label">Brands</span>
          <strong>{cockpitData.brands.length}</strong>
          <p>Voice context ready for drafting and review.</p>
        </article>
        <article className="metric-card surface">
          <span className="metric-label">Ready assets</span>
          <strong>{readyAssets}</strong>
          <p>Source material finalized after signed uploads.</p>
        </article>
        <article className="metric-card surface">
          <span className="metric-label">Open review</span>
          <strong>{openReviewTasks}</strong>
          <p>Human decisions waiting in the approval queue.</p>
        </article>
        <article className="metric-card surface">
          <span className="metric-label">Drafts in system</span>
          <strong>{cockpitData.contentItems.length}</strong>
                  <p>Content items across lifecycle states. Render jobs: {cockpitData.renderJobs.length}.</p>
        </article>
      </section>

      {screenError ? (
        <p className="banner error" role="alert">
          {screenError}
        </p>
      ) : null}
      {flashMessage ? (
        <p className="banner success" role="status">
          {flashMessage}
        </p>
      ) : null}
      {isRefreshing ? (
        <p className="banner info" role="status">
          Syncing cockpit data...
        </p>
      ) : null}

      <div className="workspace-grid">
        <nav className="surface nav-card" aria-label="Cockpit navigation">
          {cockpitRoutes.map((navigationItem) => (
            <button
              key={navigationItem.id}
              className={navigationItem.id === route ? "nav-link active" : "nav-link"}
              type="button"
              onClick={() => {
                window.location.hash = toCockpitHash(navigationItem.id);
              }}
            >
              {navigationItem.label}
            </button>
          ))}
        </nav>

        <section className="workspace-panel">
          {route === "overview" ? (
            <section className="surface panel-stack">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Overview</p>
                  <h2>Operator command posture</h2>
                </div>
                <span className="count-pill">Phase 1 slice</span>
              </div>
              <p className="panel-copy">
                This cockpit deliberately stays narrow: bootstrap session, collect assets,
                connect avatars, move drafts through review, and preserve an audit trail.
              </p>
              <div className="list-stack">
                <article className="list-card">
                  <div className="list-card-header">
                    <h3>Current operator role</h3>
                    <span className="status-badge neutral">{session.user.role}</span>
                  </div>
                  <p>Signed in as {session.user.display_name}. Permissions are derived from the backend RBAC contract.</p>
                </article>
                <article className="list-card">
                  <div className="list-card-header">
                    <h3>Immediate next step</h3>
                    <span className="status-badge neutral">guided</span>
                  </div>
                  <p>{nextStepForData(cockpitData)}</p>
                </article>
                <article className="list-card">
                  <div className="list-card-header">
                    <h3>Review pressure</h3>
                    <span className="status-badge neutral">{openReviewTasks} open</span>
                  </div>
                  <p>Approved items move toward manual publishing, while rework loops stay visible to operators.</p>
                </article>
              </div>
            </section>
          ) : null}

          {route === "brands-assets" ? (
            <BrandsAssetsPanel
              assets={cockpitData.assets}
              brands={cockpitData.brands}
              busy={busyLabel !== null}
              canMutate={canMutate}
              onCreateBrand={(payload) =>
                runCockpitMutation("create brand", () => apiClient.createBrand(payload), "Brand created.")
              }
              onUploadAsset={(brandId, file) =>
                runCockpitMutation(
                  "upload asset",
                  () =>
                    apiClient.uploadAsset(file, {
                      brand_id: brandId,
                      filename: file.name,
                      content_type: file.type || "application/octet-stream",
                      byte_size: file.size,
                    }),
                  "Asset uploaded and finalized.",
                )
              }
            />
          ) : null}

          {route === "avatars" ? (
            <AvatarsPanel
              avatars={cockpitData.avatars}
              brands={cockpitData.brands}
              busy={busyLabel !== null}
              canMutate={canMutate}
              identityPacks={cockpitData.identityPacks}
              onCreateAvatar={(payload) =>
                runCockpitMutation("create avatar", () => apiClient.createAvatar(payload), "Avatar created.")
              }
              onCreateIdentityPack={(avatarId, payload) =>
                runCockpitMutation(
                  "create identity pack",
                  () => apiClient.createIdentityPack(avatarId, payload),
                  "Identity pack created.",
                )
              }
            />
          ) : null}

          {route === "content" ? (
            <ContentPanel
              avatars={cockpitData.avatars}
              brands={cockpitData.brands}
              busy={busyLabel !== null}
              canMutate={canMutate}
              contentItems={cockpitData.contentItems}
              onCreateContent={(payload) =>
                runCockpitMutation(
                  "create content",
                  () => apiClient.createContentItem(payload),
                  "Content item created.",
                )
              }
              onPlanContent={(contentItemId, plannedPublishAt) =>
                runCockpitMutation(
                  "plan content",
                  () => apiClient.planContentItem(contentItemId, { planned_publish_at: plannedPublishAt }),
                  "Content item planned.",
                )
              }
              onSubmitReview={(contentItemId) =>
                runCockpitMutation(
                  "submit review",
                  () => apiClient.submitContentForReview(contentItemId),
                  "Content item submitted for review.",
                )
              }
            />
          ) : null}

          {route === "review" ? (
            <ReviewPanel
              busy={busyLabel !== null}
              canReview={canReview}
              contentItems={cockpitData.contentItems}
              onApprove={(taskId, decisionNotes) =>
                runCockpitMutation(
                  "approve review",
                  () => apiClient.approveReviewTask(taskId, { decision_notes: decisionNotes }),
                  "Review task approved.",
                )
              }
              onRequestRework={(taskId, decisionNotes) =>
                runCockpitMutation(
                  "request rework",
                  () => apiClient.requestReviewRework(taskId, { decision_notes: decisionNotes }),
                  "Rework requested.",
                )
              }
              reviewTasks={cockpitData.reviewTasks}
            />
          ) : null}

          {route === "render" ? (
            <RenderPanel
              busy={busyLabel !== null}
              canMutate={canMutate}
              contentItems={cockpitData.contentItems}
              identityPacks={cockpitData.identityPacks}
              onCreateRenderJob={(payload) =>
                runCockpitMutation(
                  "create render job",
                  () => apiClient.createRenderJob(payload),
                  "Render job created.",
                )
              }
              onCancelRenderJob={(renderJobId) =>
                runCockpitMutation(
                  "cancel render job",
                  () => apiClient.cancelRenderJob(renderJobId),
                  "Render job cancelled.",
                )
              }
              onRetryRenderJob={(renderJobId) =>
                runCockpitMutation(
                  "retry render job",
                  () => apiClient.retryRenderJob(renderJobId),
                  "Render job retried.",
                )
              }
              onRequeueRenderJob={(renderJobId) =>
                runCockpitMutation(
                  "requeue render job",
                  () => apiClient.requeueRenderJob(renderJobId),
                  "Render job requeued.",
                )
              }
              onSelectRenderJob={setLiveRenderJobId}
              renderJobs={cockpitData.renderJobs}
              workflowPresets={cockpitData.workflowPresets}
            />
          ) : null}

          {route === "export" ? (
            <ExportPanel
              busy={busyLabel !== null}
              canMutate={canMutate}
              contentItems={cockpitData.contentItems}
              onCreatePackage={(renderJobId) =>
                runCockpitMutation(
                  "create publish package",
                  () => apiClient.createPublishPackage({ render_job_id: renderJobId }),
                  "Publish package queued.",
                )
              }
              onCancelPackage={(packageId) =>
                runCockpitMutation(
                  "cancel publish package",
                  () => apiClient.cancelPublishPackage(packageId),
                  "Publish package cancelled.",
                )
              }
              onGetDownload={async (packageId) => {
                const response = await apiClient.getPublishPackageDownload(packageId);
                return response.download.url;
              }}
              onRetryPackage={(packageId) =>
                runCockpitMutation(
                  "retry publish package",
                  () => apiClient.retryPublishPackage(packageId),
                  "Publish package retried.",
                )
              }
              onRequeuePackage={(packageId) =>
                runCockpitMutation(
                  "requeue publish package",
                  () => apiClient.requeuePublishPackage(packageId),
                  "Publish package requeued.",
                )
              }
              publishPackages={cockpitData.publishPackages}
              renderJobs={cockpitData.renderJobs}
            />
          ) : null}

          {route === "audit" ? (
            <AuditPanel auditLogs={cockpitData.auditLogs} canView={canViewAudit} />
          ) : null}
        </section>
      </div>
    </main>
  );
}
