import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const env = fs.readFileSync(path.resolve(__dirname, "../../../.env"), "utf8");
const value = (key: string) =>
  env
    .split(/\r?\n/)
    .find((line) => line.startsWith(`${key}=`))
    ?.slice(key.length + 1) || "";

test("ML-only serving rejects old modes and shows no fallback forecast", async ({
  page,
}) => {
  const login = await page.request.post("/api/auth/login", {
    data: { email: value("SEED_EMAIL"), password: value("SEED_PASSWORD") },
  });
  expect(login.status()).toBe(200);
  const health = await (await page.request.get("/api/health")).json();
  expect(health.servingPolicy).toBe("ml_only");
  expect(health.forecastReadiness.ready).toBe(false);
  const patients = await (await page.request.get("/api/patients")).json();
  const patient = patients.find((p: { visits: { hasMri: boolean }[] }) =>
    p.visits.some((v) => v.hasMri),
  );
  expect(patient).toBeTruthy();
  expect(patient.latestCompleted).toBeNull();
  for (const mode of ["demo", "inference", "precomputed", "trained"]) {
    const response = await page.request.post(
      `/api/analysis/${patient.visits[0].id}`,
      { data: { outputMode: mode } },
    );
    expect(response.status()).toBe(409);
  }
  const fallback = await page.request.get(
    `/api/patients/${patient.id}/forecast?model_kind=clinical`,
  );
  expect(fallback.status()).toBe(409);
  await page.goto(`/patients/${patient.id}`);
  await expect(
    page.getByRole("heading", { name: "Clinical + FastSurfer ML forecast" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Check prediction readiness" }),
  ).toHaveCount(0);
  await expect(page.getByText(/first observed CDR conversion/)).toHaveCount(0);
  await expect(page.getByText(/No intact promoted Clinical \+ FastSurfer release/)).toHaveCount(0);
  const anatomyPanel = page.getByRole("region", {
    name: "Longitudinal anatomical measurements",
  });
  await expect(anatomyPanel).toBeVisible();
  await expect(
    anatomyPanel.getByRole("button", { name: /Run anatomical analysis|Processing anatomy…|Queuing…/ }),
  ).toBeVisible();
  const measured = patient.completedAnatomy?.resultJson?.anatomy?.visits.find(
    (v: { visitId: string }) => v.visitId === patient.visits[0].id,
  );
  const scores = measured?.ratings;
  const visibleScores = scores?.status === "ok" || scores?.status === "unreviewed_research";
  for (const [label, score] of [
    ["MTA left (0–4)", scores?.mtaLeft],
    ["MTA right (0–4)", scores?.mtaRight],
    ["Koedam PA (0–3; single estimate)", scores?.posteriorAtrophy],
  ] as const) {
    const expected = visibleScores && typeof score === "number"
      ? score.toFixed(2)
      : !measured ? "Not processed" : scores?.status === "invalid" ? "Scoring failed" : "Unavailable";
    await expect(anatomyPanel.getByText(label, { exact: true }).locator("..").locator("strong"))
      .toHaveText(expected);
  }
  await page.getByLabel("Compare current vs predicted").check();
  await page.getByLabel("Future time after latest scan").selectOption("24");
  await expect(
    page.getByText("Future anatomy unavailable", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Requested interval: 731 days/)).toBeVisible();
  await expect(
    page.getByText("Predicted anatomy · 24 months after latest input", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Generate evaluated future anatomy" }),
  ).toBeDisabled();
  await expect(page.getByLabel("Analysis mode")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Analyze MRI" })).toHaveCount(
    0,
  );
  await expect(page.getByText(/Prediction blocked until/)).toBeVisible();
  await page.goto("/settings");
  await expect(
    page.getByRole("heading", { name: "ML-only serving" }),
  ).toBeVisible();
  await expect(
    page.getByText("Prediction blocked", { exact: true }),
  ).toBeVisible();
});
