import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const env = fs.readFileSync(path.resolve(__dirname, "../../../.env"), "utf8");
const value = (key: string) =>
  env
    .split(/\r?\n/)
    .find((line) => line.startsWith(`${key}=`))
    ?.slice(key.length + 1) || "";

test("trained checkpoint runs asynchronously and displays one honest sequence prediction", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const login = await page.request.post("/api/auth/login", {
    data: { email: value("SEED_EMAIL"), password: value("SEED_PASSWORD") },
  });
  expect(login.status()).toBe(200);
  const patients = await (await page.request.get("/api/patients")).json();
  const patient = patients.find(
    (p: {
      latestCompleted?: {
        resultJson?: { prediction?: { cohortRole: string } };
      };
    }) => p.latestCompleted?.resultJson?.prediction?.cohortRole === "train",
  );
  expect(patient).toBeTruthy();
  await page.goto(`/patients/${patient.id}`);
  await expect(page.getByLabel("Analysis mode")).toHaveValue("trained");
  await expect(page.locator(".prediction-panel")).toContainText(
    "in-sample demonstration",
  );
  await expect(page.locator(".prediction-panel")).toContainText(
    "poor generalization",
  );
  await expect(page.locator(".prediction-panel")).toContainText(
    "not a future Alzheimer",
  );
  await expect(page.locator(".trajectory-chart")).toHaveCount(0);
  const started = page.waitForResponse(
    (r) =>
      r.url().includes("/api/analysis/") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Analyze MRI", exact: true }).click();
  const response = await started;
  expect(response.status()).toBe(202);
  const queued = await response.json();
  expect(queued.outputMode).toBe("trained");
  expect(queued.status).toBe("queued");
  expect(queued.modelVersion).toMatch(/^multimodal-cdr-retrospective-v2-/);
  // The old completed case can still be visible before the next resource poll.
  // Wait for this exact new job, not a momentarily enabled button from old data.
  await expect
    .poll(
      async () => {
        const job = await (
          await page.request.get(`/api/analysis/${queued.id}`)
        ).json();
        return job.status;
      },
      { timeout: 60000 },
    )
    .toBe("completed");
  await expect(
    page.getByRole("button", { name: "Analyze MRI", exact: true }),
  ).toBeEnabled({ timeout: 60000 });
  const completed = await (
    await page.request.get(`/api/analysis/${queued.id}`)
  ).json();
  expect(completed.status).toBe("completed");
  expect(completed.resultJson.prediction.cohortRole).toBe("train");
  expect(completed.resultJson.riskScores).toEqual([]);
  expect(completed.resultJson.prediction.testAccuracy).toBe(0.25);
  expect(completed.resultJson.prediction.checkpointSha256).toMatch(
    /^[a-f0-9]{64}$/,
  );
  await page.screenshot({
    path: "test-results/trained-patient.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Generate research report" }).click();
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download PDF", exact: true }).click();
  await (await downloadEvent).saveAs("test-results/trained-report.pdf");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "test-results/trained-patient-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});
