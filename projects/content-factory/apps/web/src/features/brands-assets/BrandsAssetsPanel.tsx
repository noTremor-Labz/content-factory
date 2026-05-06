import { useState } from "react";

import { formatDateTime, formatStatus } from "../../shared/format";
import type { Asset, Brand, BrandCreateRequest } from "../../shared/api/types";

interface BrandsAssetsPanelProps {
  brands: Brand[];
  assets: Asset[];
  canMutate: boolean;
  busy: boolean;
  onCreateBrand: (payload: BrandCreateRequest) => Promise<void>;
  onUploadAsset: (brandId: string, file: File) => Promise<void>;
}

export function BrandsAssetsPanel({
  brands,
  assets,
  canMutate,
  busy,
  onCreateBrand,
  onUploadAsset,
}: BrandsAssetsPanelProps) {
  const [brandForm, setBrandForm] = useState<BrandCreateRequest>({ name: "", voice_notes: "" });
  const [selectedBrandId, setSelectedBrandId] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const uploadBrandId = selectedBrandId || brands[0]?.id || "";

  return (
    <div className="panel-grid two-up">
      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Brands</p>
            <h2>Control voice and guardrails</h2>
          </div>
          <span className="count-pill">{brands.length} total</span>
        </div>

        {canMutate ? (
          <form
            className="stack-form"
            onSubmit={async (event) => {
              event.preventDefault();
              await onCreateBrand(brandForm);
              setBrandForm({ name: "", voice_notes: "" });
            }}
          >
            <label>
              <span>Brand name</span>
              <input
                value={brandForm.name}
                onChange={(event) =>
                  setBrandForm((current) => ({ ...current, name: event.target.value }))
                }
              />
            </label>
            <label>
              <span>Voice notes</span>
              <textarea
                rows={4}
                value={brandForm.voice_notes ?? ""}
                onChange={(event) =>
                  setBrandForm((current) => ({ ...current, voice_notes: event.target.value }))
                }
              />
            </label>
            <button className="primary-button" disabled={busy} type="submit">
              Create brand
            </button>
          </form>
        ) : (
          <p className="panel-copy">Your current role can inspect brand context but cannot mutate it.</p>
        )}

        <div className="list-stack">
          {brands.length === 0 ? (
            <p className="empty-state">Create the first brand to unlock uploads, avatars, and content items.</p>
          ) : (
            brands.map((brand) => (
              <article className="list-card" key={brand.id}>
                <div className="list-card-header">
                  <h3>{brand.name}</h3>
                  <span className="status-badge neutral">brand</span>
                </div>
                <p>{brand.voice_notes || "No voice notes yet."}</p>
                <p className="meta-copy">Updated {formatDateTime(brand.updated_at)}</p>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Assets</p>
            <h2>Upload source material</h2>
          </div>
          <span className="count-pill">{assets.length} files</span>
        </div>

        {canMutate ? (
          <form
            className="stack-form"
            onSubmit={async (event) => {
              event.preventDefault();
              if (!uploadBrandId || !selectedFile) {
                return;
              }

              await onUploadAsset(uploadBrandId, selectedFile);
              setSelectedFile(null);
            }}
          >
            <label>
              <span>Brand</span>
              <select
                value={uploadBrandId}
                onChange={(event) => setSelectedBrandId(event.target.value)}
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
              <span>Upload file</span>
              <input
                type="file"
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              />
            </label>
            <button
              className="primary-button"
              disabled={busy || !uploadBrandId || !selectedFile}
              type="submit"
            >
              Upload asset
            </button>
          </form>
        ) : null}

        <div className="list-stack">
          {assets.length === 0 ? (
            <p className="empty-state">No files uploaded yet. Use assets to feed scripts, references, and review context.</p>
          ) : (
            assets.map((asset) => (
              <article className="list-card" key={asset.id}>
                <div className="list-card-header">
                  <h3>{asset.filename}</h3>
                  <span className="status-badge">{formatStatus(asset.status)}</span>
                </div>
                <p>{asset.content_type}</p>
                <p className="meta-copy">
                  Expires {formatDateTime(asset.upload_expires_at)} · {asset.byte_size ?? 0} bytes
                </p>
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
