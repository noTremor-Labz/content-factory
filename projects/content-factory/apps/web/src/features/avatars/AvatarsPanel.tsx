import { useState } from "react";

import { formatDateTime, formatStatus } from "../../shared/format";
import type {
  Avatar,
  AvatarCreateRequest,
  Brand,
  IdentityPack,
  IdentityPackCreateRequest,
} from "../../shared/api/types";

interface AvatarsPanelProps {
  brands: Brand[];
  avatars: Avatar[];
  identityPacks: IdentityPack[];
  canMutate: boolean;
  busy: boolean;
  onCreateAvatar: (payload: AvatarCreateRequest) => Promise<void>;
  onCreateIdentityPack: (avatarId: string, payload: IdentityPackCreateRequest) => Promise<void>;
}

export function AvatarsPanel({
  brands,
  avatars,
  identityPacks,
  canMutate,
  busy,
  onCreateAvatar,
  onCreateIdentityPack,
}: AvatarsPanelProps) {
  const [avatarForm, setAvatarForm] = useState<AvatarCreateRequest>({
    brand_id: "",
    name: "",
    persona_notes: "",
  });
  const [identityForm, setIdentityForm] = useState<IdentityPackCreateRequest>({
    name: "",
    description: "",
    storage_prefix: "",
  });
  const [selectedAvatarId, setSelectedAvatarId] = useState("");
  const avatarBrandId = avatarForm.brand_id || brands[0]?.id || "";
  const identityAvatarId = selectedAvatarId || avatars[0]?.id || "";

  return (
    <div className="panel-grid two-up">
      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Avatars</p>
            <h2>Anchor the pilot persona</h2>
          </div>
          <span className="count-pill">{avatars.length} avatars</span>
        </div>

        {canMutate ? (
          <form
            className="stack-form"
            onSubmit={async (event) => {
              event.preventDefault();
              await onCreateAvatar({ ...avatarForm, brand_id: avatarBrandId });
              setAvatarForm((current) => ({ ...current, name: "", persona_notes: "" }));
            }}
          >
            <label>
              <span>Brand</span>
              <select
                value={avatarBrandId}
                onChange={(event) =>
                  setAvatarForm((current) => ({ ...current, brand_id: event.target.value }))
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
              <span>Avatar name</span>
              <input
                value={avatarForm.name}
                onChange={(event) =>
                  setAvatarForm((current) => ({ ...current, name: event.target.value }))
                }
              />
            </label>
            <label>
              <span>Persona notes</span>
              <textarea
                rows={4}
                value={avatarForm.persona_notes ?? ""}
                onChange={(event) =>
                  setAvatarForm((current) => ({ ...current, persona_notes: event.target.value }))
                }
              />
            </label>
            <button className="primary-button" disabled={busy || !avatarBrandId} type="submit">
              Create avatar
            </button>
          </form>
        ) : null}

        <div className="list-stack">
          {avatars.length === 0 ? (
            <p className="empty-state">No avatars yet. Add the pilot host before drafting content.</p>
          ) : (
            avatars.map((avatar) => (
              <article className="list-card" key={avatar.id}>
                <div className="list-card-header">
                  <h3>{avatar.name}</h3>
                  <span className="status-badge">{formatStatus(avatar.status)}</span>
                </div>
                <p>{avatar.persona_notes || "No persona notes yet."}</p>
                <p className="meta-copy">Updated {formatDateTime(avatar.updated_at)}</p>
                <div className="tag-row">
                  {identityPacks
                    .filter((identityPack) => identityPack.avatar_id === avatar.id)
                    .map((identityPack) => (
                      <span className="tag" key={identityPack.id}>
                        {identityPack.name}
                      </span>
                    ))}
                </div>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Identity packs</p>
            <h2>Store references and performance-safe variants</h2>
          </div>
          <span className="count-pill">{identityPacks.length} packs</span>
        </div>

        {canMutate ? (
          <form
            className="stack-form"
            onSubmit={async (event) => {
              event.preventDefault();
              if (!identityAvatarId) {
                return;
              }

              await onCreateIdentityPack(identityAvatarId, identityForm);
              setIdentityForm({ name: "", description: "", storage_prefix: "" });
            }}
          >
            <label>
              <span>Avatar</span>
              <select
                value={identityAvatarId}
                onChange={(event) => setSelectedAvatarId(event.target.value)}
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
              <span>Identity pack name</span>
              <input
                value={identityForm.name}
                onChange={(event) =>
                  setIdentityForm((current) => ({ ...current, name: event.target.value }))
                }
              />
            </label>
            <label>
              <span>Description</span>
              <textarea
                rows={4}
                value={identityForm.description ?? ""}
                onChange={(event) =>
                  setIdentityForm((current) => ({ ...current, description: event.target.value }))
                }
              />
            </label>
            <label>
              <span>Storage prefix</span>
              <input
                value={identityForm.storage_prefix}
                onChange={(event) =>
                  setIdentityForm((current) => ({
                    ...current,
                    storage_prefix: event.target.value,
                  }))
                }
              />
            </label>
            <button
              className="primary-button"
              disabled={busy || !identityAvatarId}
              type="submit"
            >
              Create identity pack
            </button>
          </form>
        ) : null}

        <div className="list-stack">
          {identityPacks.length === 0 ? (
            <p className="empty-state">Identity packs will appear here after the first persona bundle is registered.</p>
          ) : (
            identityPacks.map((identityPack) => (
              <article className="list-card" key={identityPack.id}>
                <div className="list-card-header">
                  <h3>{identityPack.name}</h3>
                  <span className="status-badge">{formatStatus(identityPack.status)}</span>
                </div>
                <p>{identityPack.description || "No description yet."}</p>
                <p className="meta-copy">
                  {identityPack.storage_prefix} · Updated {formatDateTime(identityPack.updated_at)}
                </p>
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
