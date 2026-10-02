import { test, expect } from "@playwright/test";

test("patient assistant: follow-up context, references, errors and mobile layout", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const requests: {
    question: string;
    history: unknown[];
    useResearchSources: boolean;
  }[] = [];
  let failNext = false;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let payload: unknown = {};
    if (path.endsWith("/auth/me")) payload = { email: "qa@example.test" };
    else if (path.endsWith("/health"))
      payload = {
        status: "online",
        database: "connected",
        worker: "online",
        modelVersion: "research-test",
        storage: "local filesystem",
      };
    else if (path.endsWith("/assistant")) {
      const body = route.request().postDataJSON();
      requests.push(body);
      if (failNext) {
        await route.fulfill({
          status: 503,
          json: {
            detail:
              "Clinical Assistant needs GEMINI_API_KEY in the backend environment.",
          },
        });
        return;
      }
      payload = {
        answer: body.useResearchSources
          ? "Research can help contextualize structural changes. These measurements require clinician review and cannot establish a diagnosis."
          : "Across three observations, recorded MMSE changed from 27 to 25. The record contains no reviewed anatomy; verify symptoms and examination findings before drawing conclusions.",
        sources: body.useResearchSources
          ? [
              {
                title: "Example research reference — automated test",
                url: "https://pubmed.ncbi.nlm.nih.gov/1/",
                supportedText: [
                  "Research can help contextualize structural changes.",
                ],
              },
            ]
          : [],
        searchSuggestions: body.useResearchSources
          ? "<div>Google Search suggestions — test fixture</div>"
          : null,
        researchRequested: body.useResearchSources,
        contextSummary: {
          visitCount: 3,
          clinicalFieldsUsed: ["Age", "MMSE", "CDR", "nWBV", "eTIV"],
          anatomyIncluded: false,
          anatomyReviewed: false,
          forecastIncluded: false,
          rawMriSent: false,
        },
        model: "test-fixture",
        disclaimer:
          "For clinician review; not a diagnosis or treatment recommendation.",
      };
    } else if (path.endsWith("/forecast"))
      payload = {
        prediction: {
          status: "unavailable",
          mode: "unavailable",
          modelVersion: "unavailable",
          usedMri: false,
          fastsurferVersion: null,
          probabilities: { "12": null, "24": null, "36": null },
          warnings: [],
          calibration: {},
          explanation: {},
        },
        anatomy: null,
        qc: "unavailable",
      };
    else if (path.endsWith("/patients/assistant-qa"))
      payload = {
        id: "assistant-qa",
        code: "SYNTHETIC_QA",
        age: 72,
        sex: "Female",
        notes: "",
        source: "uploaded",
        createdAt: "2026-10-03T00:00:00Z",
        servingPolicy: "ml_only",
        visitCount: 3,
        latestAnalysis: null,
        latestCompleted: null,
        latestAnatomy: null,
        completedAnatomy: null,
        visits: [0, 365, 730].map((day, i) => ({
          id: `qa-v${i}`,
          label: `Visit ${i + 1}`,
          daysFromBaseline: day,
          hasMri: false,
          previewUrl: null,
          metadata: { MMSE: 27 - i, CDR: 0 },
        })),
      };
    await route.fulfill({ json: payload });
  });
  await page.goto("/patients/assistant-qa");
  await expect(
    page.getByRole("heading", { name: "Clinical Assistant", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Patient context connected")).toBeVisible();
  await page.getByRole("button", { name: "Summarize the case" }).click();
  await expect(page.locator(".assistant-answer").last()).toContainText(
    "MMSE changed from 27 to 25",
  );
  await page
    .getByLabel("Ask about this patient")
    .fill("What information is missing?");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".assistant-message-assistant")).toHaveCount(2);
  expect(requests[1].history).toHaveLength(2);
  await page.getByRole("button", { name: "Explore research" }).click();
  await page.getByText("Web references (1)").click();
  await expect(
    page.getByRole("link", { name: /Example research reference/ }),
  ).toHaveAttribute("href", "https://pubmed.ncbi.nlm.nih.gov/1/");
  await expect(page.getByTitle("Google Search suggestions")).toBeVisible();
  await page.locator(".assistant-conversation").evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });
  await page.screenshot({
    path: "test-results/assistant-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByLabel("Ask about this patient")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/assistant-mobile.png",
    fullPage: true,
  });
  failNext = true;
  await page.getByLabel("Ask about this patient").fill("A failed question");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".assistant-error")).toContainText(
    "GEMINI_API_KEY",
  );
  await expect(page.getByLabel("Ask about this patient")).toHaveValue(
    "A failed question",
  );
  await page.getByRole("button", { name: "Clear", exact: true }).click();
  await expect(page.getByRole("log")).toHaveCount(0);
  expect(errors).toEqual([]);
});
