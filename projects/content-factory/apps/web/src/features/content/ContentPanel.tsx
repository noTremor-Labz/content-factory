import { useState } from "react";

import { formatChannel, formatDateTime, formatStatus } from "../../shared/format";
import type {
  Avatar,
  Brand,
  ContentChannel,
  ContentItem,
  ContentItemCreateRequest,
} from "../../shared/api/types";

interface ContentPanelProps {
  brands: Brand[];
  avatars: Avatar[];
  contentItems: ContentItem[];
  canMutate: boolean;
  busy: boolean;
  onCreateContent: (payload: ContentItemCreateRequest) => Promise<void>;
  onPlanContent: (contentItemId: string, plannedPublishAt: string | null) => Promise<void>;
  onSubmitReview: (contentItemId: string) => Promise<void>;
}

const channels: ContentChannel[] = ["instagram_reels", "youtube_shorts"];

export function ContentPanel({
  brands,
  avatars,
  contentItems,
  canMutate,
  busy,
  onCreateContent,
  onPlanContent,
  onSubmitReview,
}: ContentPanelProps) {
  const [contentForm, setContentForm] = useState<ContentItemCreateRequest>({
    brand_id: "",
    avatar_id: "",
    title: "",
    script: "",
    channel: "youtube_shorts",
  });
  const [plannedDates, setPlannedDates] = useState<Record<string, string>>({});
  const contentBrandId = contentForm.brand_id || brands[0]?.id || "";
  const contentAvatarId = contentForm.avatar_id || avatars[0]?.id || "";

  return (
    <div className="panel-grid two-up">
      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Drafting</p>
            <h2>Turn scripts into reviewable items</h2>
          </div>
          <span className="count-pill">{contentItems.length} items</span>
        </div>

        {canMutate ? (
          <form
            className="stack-form"
            onSubmit={async (event) => {
              event.preventDefault();
              await onCreateContent({
                ...contentForm,
                brand_id: contentBrandId,
                avatar_id: contentAvatarId,
              });
              setContentForm((current) => ({ ...current, title: "", script: "" }));
            }}
          >
            <label>
              <span>Brand</span>
              <select
                value={contentBrandId}
                onChange={(event) =>
                  setContentForm((current) => ({ ...current, brand_id: event.target.value }))
                }
              >
                <option value="">Select brand</option>
                {brands.map((brand) => (
                  <option key={brand.id} value={brand.id}>
                    {brand.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Avatar</span>
              <select
                value={contentAvatarId}
                onChange={(event) =>
                  setContentForm((current) => ({ ...current, avatar_id: event.target.value }))
                }
              >
                <option value="">Select avatar</option>
                {avatars.map((avatar) => (
                  <option key={avatar.id} value={avatar.id}>
                    {avatar.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Content title</span>
              <input
                value={contentForm.title}
                onChange={(event) =>
                  setContentForm((current) => ({ ...current, title: event.target.value }))
                }
              />
            </label>
            <label>
              <span>Script</span>
              <textarea
                rows={6}
                value={contentForm.script}
                onChange={(event) =>
                  setContentForm((current) => ({ ...current, script: event.target.value }))
                }
              />
            </label>
            <label>
              <span>Channel</span>
              <select
                value={contentForm.channel}
                onChange={(event) =>
                  setContentForm((current) => ({
                    ...current,
                    channel: event.target.value as ContentChannel,
                  }))
                }
              >
                {channels.map((channel) => (
                  <option key={channel} value={channel}>
                    {formatChannel(channel)}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="primary-button"
              disabled={busy || !contentBrandId || !contentAvatarId}
              type="submit"
            >
              Create content item
            </button>
          </form>
        ) : null}
      </section>

      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Lifecycle</p>
            <h2>Plan and submit to review</h2>
          </div>
        </div>

        <div className="list-stack">
          {contentItems.length === 0 ? (
            <p className="empty-state">No content items yet. Draft the first short once brand and avatar exist.</p>
          ) : (
            contentItems.map((contentItem) => (
              <article className="list-card" key={contentItem.id}>
                <div className="list-card-header">
                  <div>
                    <h3>{contentItem.title}</h3>
                    <p className="meta-copy">{formatChannel(contentItem.channel)}</p>
                  </div>
                  <span className="status-badge">{formatStatus(contentItem.status)}</span>
                </div>
                <p>{contentItem.script}</p>
                <p className="meta-copy">
                  Planned {formatDateTime(contentItem.planned_publish_at)} · Updated{" "}
                  {formatDateTime(contentItem.updated_at)}
                </p>

                {canMutate ? (
                  <div className="inline-action-row">
                    <label className="compact-field">
                      <span>Planned publish at</span>
                      <input
                        type="datetime-local"
                        value={plannedDates[contentItem.id] ?? ""}
                        onChange={(event) =>
                          setPlannedDates((current) => ({
                            ...current,
                            [contentItem.id]: event.target.value,
                          }))
                        }
                      />
                    </label>
                    {(contentItem.status === "draft" || contentItem.status === "rework") && (
                      <button
                        className="secondary-button"
                        disabled={busy}
                        type="button"
                        onClick={() =>
                          onPlanContent(
                            contentItem.id,
                            plannedDates[contentItem.id]
                              ? new Date(plannedDates[contentItem.id]).toISOString()
                              : null,
                          )
                        }
                      >
                        Plan
                      </button>
                    )}
                    {(contentItem.status === "planned" || contentItem.status === "rework") && (
                      <button
                        className="primary-button"
                        disabled={busy}
                        type="button"
                        onClick={() => onSubmitReview(contentItem.id)}
                      >
                        Send to review
                      </button>
                    )}
                  </div>
                ) : null}
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
