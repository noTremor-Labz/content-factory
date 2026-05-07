import { useState } from "react";

import { formatDateTime, formatStatus } from "../../shared/format";
import type { ComplianceCheck, ContentItem, ReviewTask } from "../../shared/api/types";

interface ReviewPanelProps {
  reviewTasks: ReviewTask[];
  complianceChecks: ComplianceCheck[];
  contentItems: ContentItem[];
  canReview: boolean;
  busy: boolean;
  onApprove: (
    taskId: string,
    decisionNotes: string | null,
    complianceOverrideReason: string | null,
  ) => Promise<void>;
  onRequestRework: (taskId: string, decisionNotes: string | null) => Promise<void>;
  onRerunCompliance: (contentItemId: string) => Promise<void>;
}

export function ReviewPanel({
  reviewTasks,
  complianceChecks,
  contentItems,
  canReview,
  busy,
  onApprove,
  onRequestRework,
  onRerunCompliance,
}: ReviewPanelProps) {
  const [notesByTaskId, setNotesByTaskId] = useState<Record<string, string>>({});
  const [overrideReasonsByTaskId, setOverrideReasonsByTaskId] = useState<Record<string, string>>(
    {},
  );

  return (
    <section className="surface panel-stack">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Review queue</p>
          <h2>Human approvals stay in the loop</h2>
        </div>
        <span className="count-pill">{reviewTasks.length} tasks</span>
      </div>

      <div className="list-stack">
        {reviewTasks.length === 0 ? (
          <p className="empty-state">Nothing is waiting for review right now.</p>
        ) : (
          reviewTasks.map((task) => {
            const contentItem = contentItems.find((item) => item.id === task.content_item_id);
            const complianceCheck = latestComplianceCheckForContent(
              complianceChecks,
              task.content_item_id,
            );
            const overrideReason = overrideReasonsByTaskId[task.id] ?? "";
            const canApprove =
              complianceCheck?.status === "passed" ||
              (complianceCheck?.status === "flagged" && overrideReason.trim().length > 0);

            return (
              <article className="list-card" key={task.id}>
                <div className="list-card-header">
                  <div>
                    <h3>{contentItem?.title ?? task.content_item_id}</h3>
                    <p className="meta-copy">Created {formatDateTime(task.created_at)}</p>
                  </div>
                  <span className="status-badge">{formatStatus(task.status)}</span>
                </div>
                <p>{contentItem?.script ?? "Content details unavailable."}</p>
                <p className="meta-copy">
                  Decision notes: {task.decision_notes || "Pending reviewer decision"}
                </p>
                <ComplianceSummary
                  check={complianceCheck}
                  overrideReason={task.compliance_override_reason}
                />

                {canReview && task.status === "open" ? (
                  <div className="stack-form">
                    <label>
                      <span>Decision notes</span>
                      <textarea
                        rows={3}
                        value={notesByTaskId[task.id] ?? ""}
                        onChange={(event) =>
                          setNotesByTaskId((current) => ({
                            ...current,
                            [task.id]: event.target.value,
                          }))
                        }
                      />
                    </label>
                    {complianceCheck?.status === "flagged" ? (
                      <label>
                        <span>Compliance override reason</span>
                        <textarea
                          rows={3}
                          value={overrideReason}
                          onChange={(event) =>
                            setOverrideReasonsByTaskId((current) => ({
                              ...current,
                              [task.id]: event.target.value,
                            }))
                          }
                        />
                      </label>
                    ) : null}
                    <div className="inline-action-row">
                      <button
                        className="primary-button"
                        disabled={busy || !canApprove}
                        type="button"
                        onClick={() =>
                          onApprove(
                            task.id,
                            notesByTaskId[task.id] || null,
                            overrideReason.trim() || null,
                          )
                        }
                      >
                        Approve
                      </button>
                      <button
                        className="secondary-button"
                        disabled={busy}
                        type="button"
                        onClick={() => onRequestRework(task.id, notesByTaskId[task.id] || null)}
                      >
                        Request rework
                      </button>
                      {contentItem ? (
                        <button
                          className="secondary-button"
                          disabled={busy}
                          type="button"
                          onClick={() => onRerunCompliance(contentItem.id)}
                        >
                          Rerun compliance
                        </button>
                      ) : null}
                    </div>
                  </div>
                ) : null}
              </article>
            );
          })
        )}
      </div>
    </section>
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

function ComplianceSummary({
  check,
  overrideReason,
}: {
  check: ComplianceCheck | null;
  overrideReason: string | null;
}) {
  if (check === null) {
    return <p className="banner error">Compliance check missing.</p>;
  }

  return (
    <div className="compliance-summary">
      <div className="list-card-header">
        <div>
          <span className="meta-label">Compliance</span>
          <p className="meta-copy">
            Risk {check.risk_score}/100 · {check.summary}
          </p>
        </div>
        <span className="status-badge">{formatStatus(check.status)}</span>
      </div>
      {check.flags.length > 0 ? (
        <ul className="flag-list">
          {check.flags.map((flag) => (
            <li key={`${flag.rule_key}-${flag.reason_code}`}>
              <strong>{formatStatus(flag.severity)}</strong>
              <span>{flag.message}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {overrideReason ? <p className="meta-copy">Override: {overrideReason}</p> : null}
    </div>
  );
}
