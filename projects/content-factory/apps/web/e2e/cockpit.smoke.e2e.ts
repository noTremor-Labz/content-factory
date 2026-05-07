import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";

const ownerEmail = "owner@inflave.test";
const ownerPassword = "very-secure-password";
const ownerDisplayName = "Owner";

async function ensureOwnerSession(page: Page): Promise<void> {
  const signOutButton = page.getByRole("button", { name: "Sign out" });

  await page.goto("/");

  if (await signOutButton.isVisible().catch(() => false)) {
    await signOutButton.click();
    await expect(page.getByRole("tab", { name: "Login" })).toBeVisible();
  }

  await page.getByRole("tab", { name: "Login" }).click();
  await page.getByLabel("Email").fill(ownerEmail);
  await page.getByLabel("Password").fill(ownerPassword);
  await page.getByRole("button", { name: "Sign in" }).click();

  try {
    await expect(signOutButton).toBeVisible({ timeout: 3_000 });
    return;
  } catch {
    await page.getByRole("tab", { name: "Bootstrap owner" }).click();
  }

  await page.getByLabel("Owner email").fill(ownerEmail);
  await page.getByLabel("Display name").fill(ownerDisplayName);
  await page.getByLabel("Password").fill(ownerPassword);
  await page.getByRole("button", { name: "Create first owner" }).click();

  await expect(signOutButton).toBeVisible();
}

test("phase 1 cockpit smoke covers brand, asset, avatar, content, review, and audit", async ({
  page,
}, testInfo) => {
  const runId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const brandName = `Smoke Brand ${runId}`;
  const avatarName = `Smoke Avatar ${runId}`;
  const identityPackName = `Smoke Pack ${runId}`;
  const contentTitle = `Smoke Content ${runId}`;
  const assetName = `smoke-asset-${runId}.txt`;
  const assetPath = testInfo.outputPath(assetName);
  const plannedPublishAt = "2026-05-08T09:45";
  const cockpitNav = page.getByRole("navigation", { name: "Cockpit navigation" });

  writeFileSync(assetPath, `content-factory smoke asset ${runId}\n`, "utf8");

  await ensureOwnerSession(page);

  await cockpitNav.getByRole("button", { name: "Brands & Assets" }).click();
  await page.getByLabel("Brand name").fill(brandName);
  await page
    .getByLabel("Voice notes")
    .fill("Pilot-safe voice notes for the browser smoke flow.");
  await page.getByRole("button", { name: "Create brand" }).click();

  await expect(page.getByText("Brand created.")).toBeVisible();
  await expect(page.getByRole("heading", { name: brandName })).toBeVisible();

  const assetsPanel = page.locator("section.surface.panel-stack").filter({
    has: page.getByRole("heading", { name: "Upload source material" }),
  });

  await assetsPanel.getByRole("combobox", { name: "Brand" }).selectOption({ label: brandName });
  await assetsPanel.locator('input[type="file"]').setInputFiles(assetPath);
  await assetsPanel.getByRole("button", { name: "Upload asset" }).click();

  await expect(page.getByText("Asset uploaded and finalized.")).toBeVisible();
  await expect(assetsPanel.getByRole("heading", { name: assetName })).toBeVisible();
  await expect(assetsPanel).toContainText("ready");

  await cockpitNav.getByRole("button", { name: "Avatars" }).click();

  const avatarsPanel = page.locator("section.surface.panel-stack").filter({
    has: page.getByRole("heading", { name: "Anchor the pilot persona" }),
  });

  await avatarsPanel.getByRole("combobox", { name: "Brand" }).selectOption({ label: brandName });
  await avatarsPanel.getByLabel("Avatar name").fill(avatarName);
  await avatarsPanel
    .getByLabel("Persona notes")
    .fill("Smoke-test persona bound to the generated brand.");
  await avatarsPanel.getByRole("button", { name: "Create avatar" }).click();

  await expect(page.getByText("Avatar created.")).toBeVisible();
  await expect(page.getByRole("heading", { name: avatarName })).toBeVisible();

  const identityPanel = page.locator("section.surface.panel-stack").filter({
    has: page.getByRole("heading", { name: "Store references and performance-safe variants" }),
  });

  await identityPanel.getByRole("combobox", { name: "Avatar" }).selectOption({ label: avatarName });
  await identityPanel.getByLabel("Identity pack name").fill(identityPackName);
  await identityPanel
    .getByLabel("Description")
    .fill("Smoke identity pack for the pilot avatar.");
  await identityPanel.getByLabel("Storage prefix").fill(`smoke/${runId}/identity-pack`);
  await identityPanel.getByRole("button", { name: "Create identity pack" }).click();

  await expect(page.getByText("Identity pack created.")).toBeVisible();
  await expect(identityPanel.getByRole("heading", { name: identityPackName })).toBeVisible();

  await cockpitNav.getByRole("button", { name: "Content" }).click();

  const draftingPanel = page.locator("section.surface.panel-stack").filter({
    has: page.getByRole("heading", { name: "Turn scripts into reviewable items" }),
  });

  await draftingPanel.getByRole("combobox", { name: "Brand" }).selectOption({ label: brandName });
  await draftingPanel.getByRole("combobox", { name: "Avatar" }).selectOption({ label: avatarName });
  await draftingPanel.getByLabel("Content title").fill(contentTitle);
  await draftingPanel
    .getByLabel("Script")
    .fill("Open with a pilot hook, explain the managed review loop, and close with a CTA.");
  await draftingPanel.getByRole("button", { name: "Create content item" }).click();

  await expect(page.getByText("Content item created.")).toBeVisible();

  const lifecycleCard = page.locator("article").filter({
    has: page.getByRole("heading", { name: contentTitle }),
  });

  await lifecycleCard.getByLabel("Planned publish at").fill(plannedPublishAt);
  await lifecycleCard.getByRole("button", { name: "Plan" }).click();

  await expect(page.getByText("Content item planned.")).toBeVisible();
  await expect(lifecycleCard).not.toContainText("Planned Not scheduled");
  await lifecycleCard.getByRole("button", { name: "Send to review" }).click();

  await expect(page.getByText("Content item submitted for review.")).toBeVisible();

  await cockpitNav.getByRole("button", { name: "Review", exact: true }).click();

  const reviewCard = page.locator("article").filter({
    has: page.getByRole("heading", { name: contentTitle }),
  });

  await reviewCard.getByLabel("Decision notes").fill("Approved for manual publishing.");
  await reviewCard.getByRole("button", { name: "Approve" }).click();

  await expect(page.getByText("Review task approved.")).toBeVisible();
  await expect(reviewCard).toContainText("approved");
  await expect(reviewCard).toContainText("Approved for manual publishing.");

  await cockpitNav.getByRole("button", { name: "Audit" }).click();

  const auditPanel = page.locator("section.surface.panel-stack").filter({
    has: page.getByRole("heading", { name: "Recent control-plane actions" }),
  });

  await expect(auditPanel).toContainText("review.approved");
  await expect(auditPanel).toContainText("content.planned");
  await expect(auditPanel).toContainText("asset.upload_finalized");
});
