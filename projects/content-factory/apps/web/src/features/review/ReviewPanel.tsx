import { useState } from "react";

import { formatDateTime, formatStatus } from "../../shared/format";
import type { ContentItem, ReviewTask } from "../../shared/api/types";

interface ReviewPanelProps {
  reviewTasks: ReviewTask[];
  contentItems: ContentItem[];
  canReview: boolean;
  busy: boolean;
  onApprove: (taskId: string, decisionNotes: string | null) => Promise<void>;
  onRequestRework: (taskId: string, decisionNotes: string | null) => Promise<void>;
}

export function ReviewPanel({
  reviewTasks,
  contentItems,
  canReview,
  busy,
  onApprove,
  onRequestRework,
}: ReviewPanelProps) {
  const [notesByTaskId, setNotesByTaskId] = useState<Record<string, string>>({});

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
                    <div className="inline-action-row">
                      <button
                        className="primary-button"
                        disabled={busy}
                        type="button"
                        onClick={() => onApprove(task.id, notesByTaskId[task.id] || null)}
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
