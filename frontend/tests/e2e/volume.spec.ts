import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";

const env = fs.readFileSync(path.resolve(__dirname, "../../../.env"), "utf8");
const value = (key: string) =>
  env
    .split(/\r?\n/)
    .find((line) => line.startsWith(`${key}=`))
    ?.slice(key.length + 1) || "";
async function openCase(page: Page) {
  const login = await page.request.post("/api/auth/login", {
    data: { email: value("SEED_EMAIL"), password: value("SEED_PASSWORD") },
  });
  expect(login.status()).toBe(200);
  const response = await page.request.get("/api/patients");
  const patient = (await response.json()).find(
    (p: { source: string; visitCount: number }) =>
      p.source === "oasis-2" && p.visitCount >= 3,
  );
  expect(patient.latestCompleted.resultJson.volumeOverlaysReady).toBe(true);
  await page.goto(`/patients/${patient.id}`);
}
async function ready(page: Page, count = 1) {
  await expect(page.locator('[data-volume-ready="true"]')).toHaveCount(count, {
    timeout: 60000,
  });
}
async function renderHash(page: Page) {
  const screenshot = await page
    .locator(".volume-card canvas")
    .last()
    .screenshot();
  expect(screenshot.byteLength).toBeGreaterThan(15000);
  return createHash("sha256").update(screenshot).digest("hex");
}

test("real MRI WebGL rendering, cutaways, slices, comparison and annotated export", async ({
  page,
}) => {
  test.setTimeout(180000);
  await page.setViewportSize({ width: 1536, height: 1100 });
  const errors: string[] = [];
  const external: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (
      /^https?:/.test(request.url()) &&
      !/^http:\/\/(localhost|127\.0\.0\.1):3000\//.test(request.url())
    )
      external.push(request.url());
  });
  await openCase(page);
  await ready(page);
  const section = page.getByRole("region", { name: "3D brain exploration" });
  await section.scrollIntoViewIfNeeded();
  const original = await renderHash(page);
  await section.screenshot({ path: "test-results/brain-3d.png" });
  const canvas = page.locator(".volume-card canvas").last();
  const rect = await canvas.boundingBox();
  expect(rect).not.toBeNull();
  await page.mouse.move(rect!.x + rect!.width / 2, rect!.y + rect!.height / 2);
  await page.mouse.down();
  await page.mouse.move(
    rect!.x + rect!.width / 2 + 70,
    rect!.y + rect!.height / 2 + 45,
    { steps: 8 },
  );
  await page.mouse.up();
  await expect.poll(() => renderHash(page)).not.toBe(original);
  await page.getByLabel("Camera preset").selectOption("superior");
  await page.getByLabel("3D zoom", { exact: true }).fill("1.3");
  await page.getByLabel("Cutaway plane").selectOption("coronal");
  await page.getByLabel("Cutaway depth").fill("0.1");
  await section.screenshot({ path: "test-results/brain-cutaway.png" });
  await page.getByRole("button", { name: "Slices + 3D", exact: true }).click();
  await page.getByLabel("X / left–right").fill("60");
  await page.getByLabel("Y / posterior–anterior").fill("55");
  await page.getByLabel("Z / inferior–superior").fill("45");
  await page.getByLabel("Volume colormap").selectOption("bone");
  await page.getByLabel("MRI opacity").fill("0.8");
  await page.getByLabel("Window lower (%)", { exact: true }).fill("18");
  await page.getByLabel("Window upper (%)", { exact: true }).fill("90");
  await page.getByLabel("Silhouette shading").check();
  await page.getByLabel("3D difference overlay", { exact: true }).check();
  await ready(page);
  await page.getByLabel("Difference opacity").fill("0.5");
  await page.getByLabel("Difference threshold").fill("0.08");
  await expect(
    page.getByText("MRI + difference proxy", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Compare with baseline").check();
  await ready(page, 2);
  await expect(page.locator(".volume-card canvas")).toHaveCount(2);
  await page.getByLabel("Link cameras & crosshairs").uncheck();
  await page.getByLabel("Link cameras & crosshairs").check();
  await section.screenshot({ path: "test-results/brain-comparison.png" });
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Save PNG" }).last().click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toMatch(/-RESEARCH\.png$/);
  await download.saveAs("test-results/brain-snapshot.png");
  expect(
    fs
      .readFileSync("test-results/brain-snapshot.png")
      .subarray(1, 4)
      .toString(),
  ).toBe("PNG");
  await page.getByRole("button", { name: "Fullscreen", exact: true }).click();
  await expect
    .poll(() => page.evaluate(() => !!document.fullscreenElement))
    .toBe(true);
  await page.getByRole("button", { name: "Fullscreen", exact: true }).click();
  await page.getByRole("button", { name: "Earlier MRI", exact: true }).click();
  await ready(page, 2);
  await expect(page.locator(".volume-navigation")).toContainText("2 / 3");
  await page.getByRole("button", { name: "Pause 3D viewer" }).click();
  await expect(page.locator(".volume-card canvas")).toHaveCount(0);
  await page.getByRole("button", { name: "Open 3D viewer" }).click();
  await ready(page, 2);
  await page.getByLabel("Compare with baseline").uncheck();
  await ready(page);
  await page.getByRole("button", { name: "Reset 3D", exact: true }).click();
  await ready(page);
  await page.locator(".volume-card canvas").evaluate((element) => {
    (element as HTMLCanvasElement)
      .getContext("webgl2")
      ?.getExtension("WEBGL_lose_context")
      ?.loseContext();
  });
  await expect(section.getByRole("alert")).toContainText(
    "graphics context was lost",
  );
  await section.getByRole("button", { name: "Try again" }).click();
  await ready(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await section.screenshot({ path: "test-results/brain-mobile.png" });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(external).toEqual([]);
  expect(errors).toEqual([]);
});

test("unavailable WebGL has a clear recovery message and an intact 2D fallback", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      ...args: Parameters<typeof original>
    ) {
      if ((args[0] as string) === "webgl2") return null;
      return original.apply(this, args);
    } as typeof original;
  });
  await openCase(page);
  await expect(
    page.locator(".volume-explorer").getByRole("alert"),
  ).toContainText("WebGL2 is unavailable", {
    timeout: 30000,
  });
  await expect(page.locator(".mri-stage img")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save PNG" })).toBeDisabled();
  await page.getByRole("button", { name: "Pause 3D viewer" }).click();
  await expect(page.locator(".volume-card canvas")).toHaveCount(0);
});
