import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { yellowBounds } from "./volume-pixels";

const env = fs.readFileSync(path.resolve(__dirname, "../../../.env"), "utf8");
const value = (key: string) =>
  env
    .split(/\r?\n/)
    .find((line) => line.startsWith(`${key}=`))
    ?.slice(key.length + 1) || "";

test("saved research preview renders the original subject and actual +229-day artifacts", async ({
  page,
}) => {
  test.setTimeout(180000);
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
  const login = await page.request.post("/api/auth/login", {
    data: { email: value("SEED_EMAIL"), password: value("SEED_PASSWORD") },
  });
  expect(login.status()).toBe(200);
  const metadata = await (
    await page.request.get("/api/anatomy-preview")
  ).json();
  expect(metadata.status).toBe("available");
  expect(metadata.intervalDays).toBe(229);
  expect(metadata.promoted).toBe(false);
  expect(metadata.observedLabelsUrl).toMatch(
    /^\/api\/analysis\/[^/]+\/visits\/[^/]+\/anatomy\/regions$/,
  );
  await page.setViewportSize({ width: 1536, height: 1000 });
  await page.goto("/preview");
  await expect(
    page.getByRole("heading", { name: "Saved future anatomy examples" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "+229 days · held-out example" })
    .click();
  await expect(page.getByText("OAS2_0073", { exact: true })).toBeVisible();
  await expect(page.getByText("+229 days", { exact: true })).toBeVisible();
  await expect(page.locator('[data-volume-ready="true"]')).toHaveCount(2, {
    timeout: 90000,
  });
  await page.screenshot({
    path: "test-results/saved-anatomy-preview.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "3D volume", exact: true }).click();
  await expect(page.locator('[data-volume-ready="true"]')).toHaveCount(2);
  const canvases = page.locator(".volume-card canvas");
  for (const canvas of [canvases.first(), canvases.last()]) {
    await expect
      .poll(async () => (await yellowBounds(canvas)).count)
      .toBeGreaterThan(20);
  }
  const pixels = await page.locator(".volume-card canvas").last().screenshot();
  expect(pixels.byteLength).toBeGreaterThan(15000);
  await page.screenshot({
    path: "test-results/saved-anatomy-preview-3d.png",
    fullPage: true,
  });
  await page.getByLabel("Hippocampus highlight").uncheck();
  await expect(page.locator('[data-volume-ready="true"]')).toHaveCount(2, {
    timeout: 60000,
  });
  for (const canvas of [canvases.first(), canvases.last()]) {
    await expect.poll(async () => (await yellowBounds(canvas)).count).toBe(0);
  }
  await page.getByLabel("Hippocampus highlight").check();
  await expect(page.locator('[data-volume-ready="true"]')).toHaveCount(2, {
    timeout: 60000,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
});
