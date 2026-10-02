import { expect, test } from "@playwright/test";

test("guided demo: draft, completion, independent clinical score and mobile layout", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const tasks = [5, 5, 3, 5, 3, 2, 1, 3, 1, 1, 1].map((maximum, index) => ({
    id: `task-${index}`,
    title: `Demo area ${index + 1}`,
    max_points: maximum,
    prompt: `Original synthetic demo prompt ${index + 1}`,
    rubric: "Clinician observes performance and records points.",
  }));
  const draft = {
    id: "assessment-a",
    instrument: "alzhio-cognitive-demo",
    version: "synthetic-v1",
    language: "English",
    status: "draft",
    revision: 0,
    total: null as number | null,
    assessedAt: "2026-10-01T12:00:00Z",
    items: {} as Record<string, number | null>,
    definition: { items: tasks },
  };
  let stored = false;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = {};
    if (path.endsWith("/auth/me")) json = { email: "qa@example.test" };
    else if (path.endsWith("/health"))
      json = { status: "online", database: "connected", worker: "online" };
    else if (path.endsWith("/forecast"))
      json = {
        prediction: {
          status: "unavailable",
          mode: "unavailable",
          probabilities: { "12": null, "24": null, "36": null },
          warnings: [],
        },
        qc: "unavailable",
      };
    else if (path.endsWith("/mmse")) json = draft;
    else if (path.endsWith("/mmse/assessment-a/complete")) {
      expect(Object.values(draft.items)).toHaveLength(11);
      draft.total = Object.values(draft.items).reduce<number>(
        (sum, points) => sum + (points ?? 0),
        0,
      );
      draft.status = "completed";
      draft.revision++;
      stored = true;
      json = draft;
    } else if (path.endsWith("/mmse/assessment-a")) {
      const body = route.request().postDataJSON();
      expect(body).not.toHaveProperty("total");
      expect(body.revision).toBe(draft.revision);
      draft.items = Object.fromEntries(
        body.items.map((item: { itemId: string; points: number | null }) => [
          item.itemId,
          item.points,
        ]),
      );
      draft.revision++;
      json = draft;
    } else if (path.endsWith("/patients/mmse-qa"))
      json = {
        id: "mmse-qa",
        code: "SYNTHETIC_DEMO",
        age: 72,
        sex: "Female",
        source: "uploaded",
        notes: "",
        servingPolicy: "ml_only",
        visitCount: 1,
        latestAnalysis: null,
        latestCompleted: null,
        latestAnatomy: null,
        completedAnatomy: null,
        visits: [
          {
            id: "visit-a",
            label: "Baseline",
            daysFromBaseline: 0,
            hasMri: false,
            previewUrl: null,
            metadata: {
              MMSE: 24,
              ...(stored ? { cognitiveDemoScore: draft.total } : {}),
              ...(draft.revision > 0
                ? {
                    mmseAssessment: {
                      status: draft.status,
                      hasDraft: !stored,
                      completedCount: stored ? 1 : 0,
                      ...(stored
                        ? {
                            total: draft.total,
                            assessedAt: draft.assessedAt,
                            instrument: draft.instrument,
                            language: "English",
                          }
                        : {}),
                    },
                  }
                : {}),
            },
          },
        ],
      };
    await route.fulfill({ json });
  });
  await page.goto("/patients/mmse-qa");
  await expect(page.getByText("Recorded MMSE: 24/30")).toBeVisible();
  await page.getByRole("button", { name: "Start assessment" }).click();
  const dialog = page.getByRole("dialog", { name: "MMSE-style demo" });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("radio", { name: "5 points", exact: true }).check();
  await dialog.getByRole("button", { name: "Save draft & close" }).click();
  await expect(dialog).not.toBeVisible();
  await page.getByRole("button", { name: "Resume assessment" }).click();
  await expect(
    dialog.getByRole("heading", { name: "Demo area 2" }),
  ).toBeVisible();
  for (let index = 1; index < tasks.length; index++) {
    const maximum = tasks[index].max_points;
    await dialog
      .getByRole("radio", {
        name: `${maximum} ${maximum === 1 ? "point" : "points"}`,
        exact: true,
      })
      .check();
    await dialog
      .getByRole("button", {
        name: index === tasks.length - 1 ? "Review" : "Next",
        exact: true,
      })
      .click();
  }
  await expect(dialog.getByText(/Calculated preview: 30\/30/)).toBeVisible();
  await page.screenshot({
    path: "test-results/mmse-desktop.png",
    fullPage: false,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    dialog.getByRole("button", { name: "Complete assessment" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/mmse-mobile.png",
    fullPage: false,
  });
  await dialog.getByRole("button", { name: "Complete assessment" }).click();
  await expect(page.getByText("Demo cognitive score: 30/30")).toBeVisible();
  expect(errors).toEqual([]);
});
