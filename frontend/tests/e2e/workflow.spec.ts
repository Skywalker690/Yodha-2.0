import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const envText = fs.readFileSync(
  path.resolve(__dirname, "../../../.env"),
  "utf8",
);
function localValue(key: string) {
  return (
    envText
      .split(/\r?\n/)
      .find((line) => line.startsWith(`${key}=`))
      ?.slice(key.length + 1) || ""
  );
}

test("protected routes require researcher login", async ({ page }) => {
  await page.goto("/patients");
  await expect(page).toHaveURL(/\/login/);
  await expect(
    page.getByRole("heading", { name: "Welcome to your workspace" }),
  ).toBeVisible();
  await page.getByLabel("Email address").fill(localValue("SEED_EMAIL"));
  await page.getByLabel("Password", { exact: true }).fill("incorrect-password");
  await page.getByRole("button", { name: "Sign in to workspace" }).click();
  await expect(page.locator(".error-box")).toContainText(
    "Email or password is incorrect",
  );
});

test("cohort review, async analysis, overlays and report download", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/login");
  await page.getByLabel("Email address").fill(localValue("SEED_EMAIL"));
  await page
    .getByLabel("Password", { exact: true })
    .fill(localValue("SEED_PASSWORD"));
  await page.getByRole("button", { name: "Sign in to workspace" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(
    page.getByRole("heading", { name: "A clearer view of change." }),
  ).toBeVisible();
  await page.screenshot({ path: "test-results/dashboard.png", fullPage: true });
  // Exercise the preserved three-visit baseline cache rather than assuming the
  // featured case is still the original demo after frozen-cohort import.
  const cohort = await (await page.request.get("/api/patients")).json();
  const preparedCodes = [
    "OAS2_0002",
    "OAS2_0041",
    "OAS2_0078",
    "OAS2_0129",
    "OAS2_0186",
  ];
  const prepared = cohort.find(
    (p: { code: string; visitCount: number }) =>
      preparedCodes.includes(p.code) && p.visitCount === 3,
  );
  expect(prepared).toBeTruthy();
  await page.goto(`/patients/${prepared.id}`);
  await expect(
    page.getByRole("heading", { name: "MRI timeline" }),
  ).toBeVisible();
  await expect(page.locator(".timeline-visit")).toHaveCount(3);
  await expect(page.locator(".mri-stage img")).toBeVisible();
  await page.getByRole("button", { name: "Difference overlay" }).click();
  await expect(page.locator(".mri-stage img")).toHaveAttribute(
    "alt",
    /Research intensity-difference overlay/,
  );
  await page.getByRole("button", { name: "Previous", exact: true }).click();
  await expect(page.locator(".viewer-footer")).toContainText("2 of 3 visits");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByLabel("Analysis mode").selectOption("precomputed");
  const started = page.waitForResponse(
    (r) =>
      r.url().includes("/api/analysis/") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Analyze MRI", exact: true }).click();
  const response = await started;
  expect(response.status()).toBe(202);
  expect((await response.json()).status).toBe("queued");
  await expect(
    page.getByRole("button", { name: "Analyze MRI", exact: true }),
  ).toBeEnabled({ timeout: 60000 });
  await page.getByRole("button", { name: "Generate research report" }).click();
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download PDF", exact: true }).click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  await download.saveAs("test-results/research-report.pdf");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "test-results/patient.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".sidebar")).toBeHidden();
  await page.screenshot({
    path: "test-results/patient-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(page.locator(".sidebar")).toBeVisible();
  await page.getByRole("link", { name: "Reports", exact: true }).click();
  await expect(
    page.getByRole("link", { name: /Download PDF/ }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await expect(
    page.getByText("feature-delta-v1", { exact: true }),
  ).toBeVisible();
});

test("patient creation, visit upload and persistent records", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByLabel("Email address").fill(localValue("SEED_EMAIL"));
  await page
    .getByLabel("Password", { exact: true })
    .fill(localValue("SEED_PASSWORD"));
  await page.getByRole("button", { name: "Sign in to workspace" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await page.getByRole("link", { name: "Add patient" }).click();
  const code = `E2E_${Date.now()}`;
  await page.getByLabel("Patient code", { exact: true }).fill(code);
  await page.getByLabel("Age (optional)").fill("72");
  await page
    .getByRole("button", { name: "Create patient", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: code, exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Add visit", exact: true }).click();
  await page.getByRole("button", { name: "Save visit" }).click();
  await expect(
    page.getByRole("heading", { name: "Add the MRI for Visit 1" }),
  ).toBeVisible();
  await page
    .getByLabel("MRI file", { exact: true })
    .setInputFiles(
      path.resolve(__dirname, "../../../data/fixtures/synthetic.nii.gz"),
    );
  await page.getByRole("button", { name: "Upload MRI", exact: true }).click();
  await expect(page.locator(".mri-stage img")).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: code, exact: true }),
  ).toBeVisible();
  await expect(page.locator(".timeline-visit")).toHaveCount(1);
});
