import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const env = fs.readFileSync(path.resolve(__dirname, "../../../.env"), "utf8");
const value = (key: string) =>
  env
    .split(/\r?\n/)
    .find((line) => line.startsWith(`${key}=`))
    ?.slice(key.length + 1) || "";

test("baseline forecast distinguishes unavailable horizons and missing anatomy", async ({
  page,
}) => {
  const login = await page.request.post("/api/auth/login", {
    data: { email: value("SEED_EMAIL"), password: value("SEED_PASSWORD") },
  });
  expect(login.status()).toBe(200);
  const patients = await (await page.request.get("/api/patients")).json();
  let selected: { id: string } | undefined;
  for (const patient of patients.filter(
    (p: { source: string }) => p.source === "oasis-2",
  )) {
    const response = await page.request.get(
      `/api/patients/${patient.id}/forecast`,
    );
    expect(response.status()).toBe(200);
    if ((await response.json()).prediction.status === "partial") {
      selected = patient;
      break;
    }
  }
  expect(selected).toBeTruthy();
  await page.goto(`/patients/${selected!.id}`);
  const panel = page
    .locator("section")
    .filter({
      has: page.getByRole("heading", {
        name: "Baseline-only outcome forecast",
      }),
    });
  await expect(panel.getByText("Unavailable", { exact: true })).toHaveCount(2);
  await expect(panel).toContainText("no independently validated forecast");
  await expect(panel).toContainText(
    "36-month test set lacks adequate class support",
  );
  await panel.getByLabel("Forecast model").selectOption("clinical_fastsurfer");
  await expect(panel.getByText("Unavailable", { exact: true })).toHaveCount(3);
  await expect(panel).toContainText("no silent fallback");
});
