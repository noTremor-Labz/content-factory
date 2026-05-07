import { useEffect, useState } from "react";

import { formatDateTime, formatStatus } from "../../shared/format";
import type {
  ContentItem,
  IdentityPack,
  RenderJob,
  RenderJobCreateRequest,
  WorkflowPreset,
} from "../../shared/api/types";

interface RenderPanelProps {
  contentItems: ContentItem[];
  identityPacks: IdentityPack[];
  renderJobs: RenderJob[];
  workflowPresets: WorkflowPreset[];
  canMutate: boolean;
  busy: boolean;
  onCreateRenderJob: (payload: RenderJobCreateRequest) => Promise<void>;
  onSelectRenderJob: (renderJobId: string | null) => void;
}

const renderableStatuses = new Set(["planned", "review", "approved", "rework"]);

export function RenderPanel({
  contentItems,
  identityPacks,
  renderJobs,
  workflowPresets,
  canMutate,
  busy,
  onCreateRenderJob,
  onSelectRenderJob,
}: RenderPanelProps) {
  const [selectedJobId, setSelectedJobId] = useState(renderJobs[0]?.id ?? "");
  const [formState, setFormState] = useState({
    contentItemId: "",
    workflowPresetId: "",
    identityPackId: "",
    retryBudget: 3,
  });
  const renderableContentItems = contentItems.filter((item) => renderableStatuses.has(item.status));
  const contentItemId = formState.contentItemId || renderableContentItems[0]?.id || "";
  const workflowPresetId = formState.workflowPresetId || workflowPresets[0]?.id || "";
  const selectedJob = renderJobs.find((renderJob) => renderJob.id === selectedJobId) ?? renderJobs[0] ?? null;
  const selectedContentItem = selectedJob
    ? contentItems.find((item) => item.id === selectedJob.content_item_id)
    : null;

  useEffect(() => {
    onSelectRenderJob(selectedJob?.id ?? null);
  }, [onSelectRenderJob, selectedJob?.id]);

  return (
    <div className="panel-grid two-up">
      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Render queue</p>
            <h2>Render queue</h2>
          </div>
          <span className="count-pill">{renderJobs.length} jobs</span>
        </div>

        {canMutate ? (
          <form
            className="stack-form"
            onSubmit={async (event) => {
              event.preventDefault();
              await onCreateRenderJob({
                content_item_id: contentItemId,
                workflow_preset_id: workflowPresetId,
                identity_pack_id: formState.identityPackId || null,
                retry_budget: formState.retryBudget,
              });
            }}
          >
            <label>
              <span>Content item</span>
              <select
                value={contentItemId}
                onChange={(event) =>
                  setFormState((current) => ({ ...current, contentItemId: event.target.value }))
                }
              >
                <option value="">Select content item</option>
                {renderableContentItems.map((contentItem) => (
                  <option key={contentItem.id} value={contentItem.id}>
                    {contentItem.title} · {formatStatus(contentItem.status)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Workflow preset</span>
              <select
                value={workflowPresetId}
                onChange={(event) =>
                  setFormState((current) => ({ ...current, workflowPresetId: event.target.value }))
                }
              >
                <option value="">Select workflow preset</option>
                {workflowPresets.map((workflowPreset) => (
                  <option key={workflowPreset.id} value={workflowPreset.id}>
                    {workflowPreset.key} v{workflowPreset.version}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Identity pack</span>
              <select
                value={formState.identityPackId}
                onChange={(event) =>
                  setFormState((current) => ({ ...current, identityPackId: event.target.value }))
                }
              >
                <option value="">No identity pack</option>
                {identityPacks.map((identityPack) => (
                  <option key={identityPack.id} value={identityPack.id}>
                    {identityPack.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Retry budget</span>
              <input
                min={1}
                max={5}
                type="number"
                value={formState.retryBudget}
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    retryBudget: Number(event.target.value),
                  }))
                }
              />
            </label>
            <button
              className="primary-button"
              disabled={busy || !contentItemId || !workflowPresetId}
              type="submit"
            >
              Create render job
            </button>
          </form>
        ) : null}

        <div className="list-stack">
          {renderJobs.length === 0 ? (
            <p className="empty-state">No render jobs yet.</p>
          ) : (
            renderJobs.map((renderJob) => (
              <article className="list-card" key={renderJob.id}>
                <div className="list-card-header">
                  <div>
                    <h3>{renderJob.workflow_preset_key} v{renderJob.workflow_preset_version}</h3>
                    <p className="meta-copy">
                      {contentItems.find((item) => item.id === renderJob.content_item_id)?.title ?? "Content item"}
                    </p>
                  </div>
                  <span className="status-badge">{formatStatus(renderJob.status)}</span>
                </div>
                <p className="meta-copy">
                  {renderJob.attempts.length} attempts · Updated {formatDateTime(renderJob.updated_at)}
                </p>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setSelectedJobId(renderJob.id)}
                >
                  View job
                </button>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Job detail</p>
            <h2>{selectedJob ? selectedJob.workflow_preset_key : "No job selected"}</h2>
          </div>
          {selectedJob ? <span className="status-badge">{formatStatus(selectedJob.status)}</span> : null}
        </div>

        {selectedJob ? (
          <>
            <dl className="meta-list">
              <div>
                <dt>Content</dt>
                <dd>{selectedContentItem?.title ?? selectedJob.content_item_id}</dd>
              </div>
              <div>
                <dt>Provider</dt>
                <dd>{selectedJob.workflow_provider}</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{formatDateTime(selectedJob.created_at)}</dd>
              </div>
            </dl>

            <div className="list-stack">
              {selectedJob.attempts.map((attempt) => (
                <article className="list-card" key={attempt.id}>
                  <div className="list-card-header">
                    <h3>Attempt {attempt.attempt_number}</h3>
                    <span className="status-badge">{formatStatus(attempt.status)}</span>
                  </div>
                  <p className="meta-copy">
                    Provider job {attempt.provider_job_id ?? "not assigned"} · Started{" "}
                    {formatDateTime(attempt.started_at)} · Finished {formatDateTime(attempt.finished_at)}
                  </p>
                  {attempt.error_message ? <p className="banner error">{attempt.error_message}</p> : null}
                  <pre className="json-preview">
                    {JSON.stringify(attempt.response_payload, null, 2)}
                  </pre>
                </article>
              ))}
            </div>
          </>
        ) : (
          <p className="empty-state">Select a render job from the queue.</p>
        )}
      </section>
    </div>
  );
}
