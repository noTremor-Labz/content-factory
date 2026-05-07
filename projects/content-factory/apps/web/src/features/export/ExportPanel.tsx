import { useState } from "react";

import type {
  ComplianceCheck,
  ContentItem,
  PublishPackage,
  RenderJob,
} from "../../shared/api/types";
import { formatDateTime, formatStatus } from "../../shared/format";

interface ExportPanelProps {
  contentItems: ContentItem[];
  complianceChecks: ComplianceCheck[];
  publishPackages: PublishPackage[];
  renderJobs: RenderJob[];
  canMutate: boolean;
  busy: boolean;
  onCreatePackage: (renderJobId: string) => Promise<void>;
  onCancelPackage: (packageId: string) => Promise<void>;
  onGetDownload: (packageId: string) => Promise<string>;
  onRetryPackage: (packageId: string) => Promise<void>;
  onRequeuePackage: (packageId: string) => Promise<void>;
}

const cancelablePackageStatuses = new Set(["queued", "running"]);
const retryablePackageStatuses = new Set(["failed", "cancelled"]);
const requeueablePackageStatuses = new Set(["queued"]);

export function ExportPanel({
  contentItems,
  complianceChecks,
  publishPackages,
  renderJobs,
  canMutate,
  busy,
  onCreatePackage,
  onCancelPackage,
  onGetDownload,
  onRetryPackage,
  onRequeuePackage,
}: ExportPanelProps) {
  const [selectedRenderJobId, setSelectedRenderJobId] = useState("");
  const [downloadUrls, setDownloadUrls] = useState<Record<string, string>>({});
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const packagedRenderJobIds = new Set(
    publishPackages.map((publishPackage) => publishPackage.render_job_id),
  );
  const eligibleRenderJobs = renderJobs.filter((renderJob) => {
    const contentItem = contentItems.find((item) => item.id === renderJob.content_item_id);
    return (
      renderJob.status === "succeeded" &&
      contentItem !== undefined &&
      contentItem.status === "approved" &&
      hasFinalComplianceDecision(complianceChecks, contentItem.id) &&
      !packagedRenderJobIds.has(renderJob.id)
    );
  });
  const renderJobId = selectedRenderJobId || eligibleRenderJobs[0]?.id || "";

  return (
    <div className="panel-grid two-up">
      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Export</p>
            <h2>Publish packages</h2>
          </div>
          <span className="count-pill">{publishPackages.length} packages</span>
        </div>

        {canMutate ? (
          <form
            className="stack-form"
            onSubmit={async (event) => {
              event.preventDefault();
              if (!renderJobId) {
                return;
              }
              await onCreatePackage(renderJobId);
            }}
          >
            <label>
              <span>Render job</span>
              <select
                value={renderJobId}
                onChange={(event) => setSelectedRenderJobId(event.target.value)}
              >
                <option value="">Select render job</option>
                {eligibleRenderJobs.map((renderJob) => (
                  <option key={renderJob.id} value={renderJob.id}>
                    {renderJob.workflow_preset_key} v{renderJob.workflow_preset_version} ·{" "}
                    {contentItems.find((item) => item.id === renderJob.content_item_id)?.title ??
                      "Content item"}
                  </option>
                ))}
              </select>
            </label>
            <button className="primary-button" disabled={busy || !renderJobId} type="submit">
              Create package
            </button>
          </form>
        ) : null}

        <div className="list-stack">
          {eligibleRenderJobs.length === 0 ? (
            <p className="empty-state">No succeeded approved renders waiting for package export.</p>
          ) : (
            eligibleRenderJobs.map((renderJob) => {
              const contentItem = contentItems.find((item) => item.id === renderJob.content_item_id);
              const complianceCheck = contentItem
                ? latestComplianceCheckForContent(complianceChecks, contentItem.id)
                : null;

              return (
                <article className="list-card" key={renderJob.id}>
                <div className="list-card-header">
                  <div>
                    <h3>{renderJob.workflow_preset_key} v{renderJob.workflow_preset_version}</h3>
                    <p className="meta-copy">{contentItem?.title ?? renderJob.content_item_id}</p>
                  </div>
                  <span className="status-badge">{formatStatus(renderJob.status)}</span>
                </div>
                <p className="meta-copy">Updated {formatDateTime(renderJob.updated_at)}</p>
                {complianceCheck ? (
                  <p className="meta-copy">
                    Compliance {formatStatus(complianceCheck.status)} · Risk{" "}
                    {complianceCheck.risk_score}/100
                  </p>
                ) : null}
                </article>
              );
            })
          )}
        </div>
      </section>

      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Packages</p>
            <h2>Manual publish bundle</h2>
          </div>
        </div>

        {downloadError ? <p className="banner error">{downloadError}</p> : null}

        <div className="list-stack">
          {publishPackages.length === 0 ? (
            <p className="empty-state">No publish packages yet.</p>
          ) : (
            publishPackages.map((publishPackage) => {
              const contentItem = contentItems.find(
                (item) => item.id === publishPackage.content_item_id,
              );
              const downloadUrl = downloadUrls[publishPackage.id];
              return (
                <article className="list-card" key={publishPackage.id}>
                  <div className="list-card-header">
                    <div>
                      <h3>{contentItem?.title ?? publishPackage.content_item_id}</h3>
                      <p className="meta-copy">
                        {publishPackage.package_object_key ?? "Package object pending"}
                      </p>
                    </div>
                    <span className="status-badge">{formatStatus(publishPackage.status)}</span>
                  </div>
                  <p className="meta-copy">
                    {publishPackage.byte_size ?? 0} bytes · Updated{" "}
                    {formatDateTime(publishPackage.updated_at)}
                  </p>
                  {publishPackage.error_message ? (
                    <p className="banner error">{publishPackage.error_message}</p>
                  ) : null}
                  {publishPackage.status === "ready" ? (
                    <div className="inline-action-row">
                      <button
                        className="secondary-button"
                        disabled={busy}
                        type="button"
                        onClick={async () => {
                          setDownloadError(null);
                          try {
                            const url = await onGetDownload(publishPackage.id);
                            setDownloadUrls((current) => ({
                              ...current,
                              [publishPackage.id]: url,
                            }));
                          } catch (error) {
                            setDownloadError(error instanceof Error ? error.message : "Download failed");
                          }
                        }}
                      >
                        Get download
                      </button>
                      {downloadUrl ? (
                        <a className="secondary-button" href={downloadUrl}>
                          Open package
                        </a>
                      ) : null}
                    </div>
                  ) : null}
                  {canMutate ? (
                    <div className="inline-action-row">
                      {requeueablePackageStatuses.has(publishPackage.status) ? (
                        <button
                          className="secondary-button"
                          disabled={busy}
                          type="button"
                          onClick={() => onRequeuePackage(publishPackage.id)}
                        >
                          Requeue package
                        </button>
                      ) : null}
                      {cancelablePackageStatuses.has(publishPackage.status) ? (
                        <button
                          className="secondary-button"
                          disabled={busy}
                          type="button"
                          onClick={() => onCancelPackage(publishPackage.id)}
                        >
                          Cancel package
                        </button>
                      ) : null}
                      {retryablePackageStatuses.has(publishPackage.status) ? (
                        <button
                          className="secondary-button"
                          disabled={busy}
                          type="button"
                          onClick={() => onRetryPackage(publishPackage.id)}
                        >
                          Retry package
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                </article>
              );
            })
          )}
        </div>
      </section>
    </div>
  );
}

function latestComplianceCheckForContent(
  complianceChecks: ComplianceCheck[],
  contentItemId: string,
): ComplianceCheck | null {
  return (
    complianceChecks
      .filter((check) => check.content_item_id === contentItemId)
      .sort((left, right) => right.created_at.localeCompare(left.created_at))[0] ?? null
  );
}

function hasFinalComplianceDecision(
  complianceChecks: ComplianceCheck[],
  contentItemId: string,
): boolean {
  const check = latestComplianceCheckForContent(complianceChecks, contentItemId);
  return check?.status === "passed" || check?.status === "flagged";
}
