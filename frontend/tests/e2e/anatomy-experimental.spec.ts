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

test("real patient-specific experimental forecast is visible only after opt-in", async ({
  page,
}) => {
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const login = await page.request.post("/api/auth/login", {
    data: { email: value("SEED_EMAIL"), password: value("SEED_PASSWORD") },
  });
  expect(login.status()).toBe(200);
  const strict = await (
    await page.request.get("/api/anatomy-model/readiness")
  ).json();
  expect(strict.status).toBe("unavailable");
  const candidate = await (
    await page.request.get("/api/anatomy-model/readiness?experimental=true")
  ).json();
  expect(candidate.trainingSubjectCount).toBe(4);
  expect(candidate.supportedIntervalsDays).toEqual([]);
  const jobs = JSON.parse(
    fs.readFileSync(
      path.resolve(
        __dirname,
        "../../../artifacts/experimental-forecast-365-jobs.json",
      ),
      "utf8",
    ),
  );
  const first = jobs.patients[0];
  const patient = await (
    await page.request.get(`/api/patients/${first.patient_id}`)
  ).json();
  const forecasts = await (
    await page.request.get(
      `/api/patients/${first.patient_id}/anatomy-forecasts`,
    )
  ).json();
  const prediction = forecasts.find(
    (a: { id: string }) => a.id === first.job_id,
  );
  expect(prediction.resultJson.anatomy.forecast.experimental).toBe(true);
  expect(prediction.resultJson.anatomy.forecast.intervalDays).toBe(365);
  expect(prediction.resultJson.anatomy.forecast.trainingSubjectCount).toBe(4);
  expect(prediction.resultJson.anatomy.forecast.predictionIntervals).toBeNull();
  const cutoff = patient.visits.find(
    (v: { id: string }) => v.id === first.cutoff_visit_id,
  );
  await page.setViewportSize({ width: 1536, height: 1100 });
  await page.goto(`/patients/${patient.id}`);
  const workspace = page.getByRole("region", { name: "3D brain exploration" });
  await workspace
    .getByRole("navigation", { name: "Longitudinal MRI timeline" })
    .getByRole("button")
    .filter({ hasText: cutoff.label })
    .first()
    .click();
  await workspace.getByLabel("Compare current vs predicted").check();
  await expect(
    workspace.getByText("Future anatomy unavailable", { exact: true }),
  ).toBeVisible();
  await expect(
    workspace.getByRole("button", {
      name: "Generate evaluated future anatomy",
    }),
  ).toBeDisabled();
  await workspace
    .getByRole("button", { name: "Show experimental forecast" })
    .click();
  await expect(
    workspace.getByLabel("Experimental forecasts (small-cohort model)"),
  ).toBeChecked();
  await expect(
    workspace.getByText(/Unvalidated historical model · 4 training subjects/),
  ).toBeVisible({ timeout: 30000 });
  await expect(workspace.locator('[data-volume-ready="true"]')).toHaveCount(2, {
    timeout: 90000,
  });
  await expect(
    workspace.getByText("Future anatomy unavailable", { exact: true }),
  ).toHaveCount(0);
  await workspace.getByText("Model limitations and output checks").click();
  await expect(
    workspace.getByText(/Historical fixed-reference model/),
  ).toBeVisible();
  await workspace.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: "test-results/patient-experimental-forecast.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  expect(errors).toEqual([]);
  await page.setViewportSize({ width: 1536, height: 1100 });
  await page.goto(
    `/patients/${patient.id}?experimentalForecast=365#anatomy-viewer`,
  );
  await expect(
    workspace.getByLabel("Experimental forecasts (small-cohort model)"),
  ).toBeChecked();
  await expect(workspace.locator('[data-volume-ready="true"]')).toHaveCount(2, {
    timeout: 90000,
  });
  await expect(
    workspace.getByText("Future anatomy unavailable", { exact: true }),
  ).toHaveCount(0);
  await expect(workspace.getByText(/unsupported horizon/)).toHaveCount(0);
  await expect(workspace.getByLabel("Hippocampus highlight")).toBeChecked();
  await expect(
    workspace.getByLabel("Predicted brain and hippocampus boundaries"),
  ).not.toBeChecked();
  await expect(
    workspace.getByRole("region", { name: "Actual forecast changes" }),
  ).toContainText("0.24 mm", { timeout: 30000 });
  await expect(
    workspace.getByRole("region", { name: "Actual forecast changes" }),
  ).toContainText("-5.21%");
  await expect(
    workspace.getByText("Input cutoff · " + cutoff.label, { exact: true }),
  ).toBeVisible();
  for (const canvas of [
    workspace.locator(".volume-card canvas").first(),
    workspace.locator(".volume-card canvas").last(),
  ]) {
    await expect
      .poll(async () => (await yellowBounds(canvas)).count)
      .toBeGreaterThan(20);
  }
  await workspace.screenshot({
    path: "test-results/patient-experimental-direct-view.png",
  });
  expect(errors).toEqual([]);
});
