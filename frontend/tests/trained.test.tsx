import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { TrajectoryChart } from "@/components/trajectory-chart";
import { AnalysisWorkspace } from "@/components/analysis-workspace";
import { PatientTable } from "@/components/patient-table";
import Dashboard from "@/app/(workspace)/dashboard/page";
import { useResource } from "@/lib/use-resource";
import type {
  Analysis,
  Patient,
  Result,
  TrainedPrediction,
  Visit,
} from "@/types";

// Synthetic fixtures only: no MRI downloads, checkpoints or participant records.
vi.mock("@/components/volume-explorer", () => ({
  VolumeExplorer: () => <div>MRI viewer placeholder</div>,
}));
vi.mock("@/lib/use-resource", () => ({ useResource: vi.fn() }));
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  AreaChart: () => <div data-testid="baseline-chart" />,
  Area: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));

const prediction: TrainedPrediction = {
  target: "observed_cdr_increase",
  score: 0.62,
  decisionThreshold: 0.46,
  predictedIncrease: true,
  checkpointSha256: "a".repeat(64),
  cohortRole: "train",
  trainingSubjects: 40,
  trainingVisits: 132,
  testSubjects: 8,
  testAccuracy: 0.25,
  testBalancedAccuracy: 0.5,
  testRocAuc: 0.0833,
  majorityBaselineAccuracy: 0.75,
  qualityStatus: "experimental_poor_generalization",
};
const visits: Visit[] = [0, 365, 730].map((days, i) => ({
  id: `synthetic-v${i}`,
  label: `Visit ${i + 1}`,
  daysFromBaseline: days,
  hasMri: true,
  previewUrl: `/api/visits/synthetic-v${i}/preview`,
  metadata: {},
}));
const result: Result = {
  patientId: "synthetic-p",
  visitIds: visits.map((v) => v.id),
  riskScores: [],
  daysFromBaseline: visits.map((v) => v.daysFromBaseline),
  biomarkers: {
    foregroundFraction: [0.3, 0.32, 0.31],
    featureChange: [0, 0.02, 0.03],
  },
  outputMode: "trained",
  confidence: null,
  caveats: ["Synthetic test fixture."],
  modelVersion: "synthetic-multimodal-v1",
  selectedVisit: visits[2].id,
  prediction,
};
const analysis: Analysis = {
  id: "synthetic-a",
  patientId: result.patientId,
  visitId: result.selectedVisit,
  status: "completed",
  progress: 100,
  stage: "Completed",
  outputMode: "trained",
  modelVersion: result.modelVersion,
  score: prediction.score,
  confidence: null,
  resultJson: result,
  error: null,
  createdAt: "2026-10-01T00:00:00Z",
};
const patient: Patient = {
  id: result.patientId,
  code: "SYNTHETIC_CASE",
  age: null,
  sex: null,
  notes: "",
  source: "synthetic",
  createdAt: analysis.createdAt,
  visitCount: visits.length,
  visits,
  latestAnalysis: analysis,
  latestCompleted: analysis,
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("experimental trained sequence output", () => {
  it("renders one score and saved classification, not a fabricated neural trajectory", () => {
    const { container } = render(<TrajectoryChart result={result} />);
    expect(screen.getAllByText("0.6200")).toHaveLength(1);
    expect(screen.getByText("0.4600")).toBeVisible();
    expect(screen.getByText("Observed CDR increase")).toBeVisible();
    expect(
      screen.getByText(/One uncalibrated retrospective score/),
    ).toHaveTextContent("completed 3-visit sequence (day 0–730)");
    expect(
      screen.getByText(/not a future Alzheimer's probability/),
    ).toBeVisible();
    expect(screen.getByText(/Not a medical diagnosis/)).toBeVisible();
    expect(screen.queryByTestId("baseline-chart")).toBeNull();
    expect(screen.queryByRole("img")).toBeNull();
    expect(container).not.toHaveTextContent("NaN");
    expect(container).not.toHaveTextContent("undefined");
  });

  it("discloses poor held-out results, majority baseline and checkpoint provenance", () => {
    render(<TrajectoryChart result={result} />);
    expect(
      screen.getByText("Experimental · poor generalization"),
    ).toBeVisible();
    expect(
      screen.getByRole("heading", {
        name: "Recorded test evidence · 8 subjects",
      }),
    ).toBeVisible();
    expect(screen.getByText("25.0%")).toBeVisible();
    expect(screen.getByText("50.0%")).toBeVisible();
    expect(screen.getByText("0.0833")).toBeVisible();
    expect(screen.getByText("75.0%")).toBeVisible();
    expect(
      screen.getByText(/small test cohort is a reused holdout/),
    ).toBeVisible();
    expect(
      screen.getByText(/Trained on 40 subjects and 132 visits/),
    ).toBeVisible();
    expect(screen.getByText(prediction.checkpointSha256)).toBeVisible();
    expect(screen.getByText(result.modelVersion)).toBeVisible();
  });

  it.each([
    [
      "train",
      /Training member:.*in-sample demonstration, not accuracy evidence/,
    ],
    ["validation", /Validation member:.*selected the checkpoint and threshold/],
    ["test", /Test member:.*reused holdout/],
    [
      "unassigned",
      /Unassigned subject:.*different acquisition domain is unverified/,
    ],
  ] as const)(
    "labels %s membership without implying independent accuracy",
    (cohortRole, caveat) => {
      render(
        <TrajectoryChart
          result={{ ...result, prediction: { ...prediction, cohortRole } }}
        />,
      );
      expect(screen.getByText(caveat)).toBeVisible();
      expect(
        screen.getByText(
          /Other subjects and acquisition domains remain unvalidated/,
        ),
      ).toBeVisible();
    },
  );

  it("uses the saved decision rather than applying a hardcoded 0.5 threshold", () => {
    render(
      <TrajectoryChart
        result={{
          ...result,
          prediction: {
            ...prediction,
            score: 0.62,
            decisionThreshold: 0.7,
            predictedIncrease: false,
          },
        }}
      />,
    );
    expect(screen.getByText("No observed CDR increase")).toBeVisible();
    expect(screen.getByText("0.7000")).toBeVisible();
  });

  it("fails explicitly when trained metadata is missing, without substituting baseline scores", () => {
    render(
      <TrajectoryChart
        result={{
          ...result,
          prediction: undefined,
          riskScores: [0.1, 0.2, 0.3],
        }}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "no baseline score has been substituted",
    );
    expect(screen.queryByTestId("baseline-chart")).toBeNull();
  });

  it.each([NaN, Infinity, -0.1, 1.1])(
    "does not display an invalid trained score (%s)",
    (score) => {
      const { container } = render(
        <TrajectoryChart
          result={{ ...result, prediction: { ...prediction, score } }}
        />,
      );
      expect(screen.getByRole("alert")).toHaveTextContent(
        "prediction unavailable",
      );
      expect(container).not.toHaveTextContent(/NaN|Infinity/);
    },
  );

  it.each(["inference", "demo", "precomputed"] as const)(
    "preserves the explicit %s trajectory",
    (outputMode) => {
      render(
        <TrajectoryChart
          result={{
            ...result,
            outputMode,
            prediction: undefined,
            riskScores: [0.1, 0.2, 0.3],
          }}
        />,
      );
      expect(screen.getByTestId("baseline-chart")).toBeVisible();
      expect(screen.getByRole("img")).toHaveAccessibleName(
        "Progression-risk estimates: day 0: 10%, day 365: 20%, day 730: 30%",
      );
      expect(
        screen.queryByText("Experimental · poor generalization"),
      ).toBeNull();
    },
  );

  it("handles incomplete historical score series without NaN", () => {
    const { container } = render(
      <TrajectoryChart
        result={{ ...result, outputMode: "inference", prediction: undefined }}
      />,
    );
    expect(screen.getByText("Trajectory unavailable")).toBeVisible();
    expect(screen.queryByTestId("baseline-chart")).toBeNull();
    expect(container).not.toHaveTextContent("NaN");
  });
});

describe("trained mode integration", () => {
  it("distinguishes the trained score from baseline percentages in the patient list", () => {
    const baselinePatient = {
      ...patient,
      id: "synthetic-baseline",
      code: "BASELINE_CASE",
      latestCompleted: {
        ...analysis,
        outputMode: "inference" as const,
        score: 0.2,
        resultJson: null,
      },
    };
    render(<PatientTable patients={[patient, baselinePatient]} />);
    const trainedRow = screen.getByText(patient.code).closest("tr")!;
    expect(within(trainedRow).getByText("0.6200")).toBeVisible();
    expect(
      within(trainedRow).getByText(/Experimental observed-CDR-increase score/),
    ).toBeVisible();
    expect(
      within(trainedRow).getByText(/In-sample · not accuracy evidence/),
    ).toBeVisible();
    expect(within(trainedRow).queryByText("62.0%")).toBeNull();
    const baselineRow = screen.getByText("BASELINE_CASE").closest("tr")!;
    expect(within(baselineRow).getByText("20.0%")).toBeVisible();
    expect(
      within(baselineRow).getByText("Baseline structural-change index"),
    ).toBeVisible();
  });

  it("does not use analysis.score as a fallback for missing trained prediction metadata", () => {
    render(
      <PatientTable
        patients={[
          { ...patient, latestCompleted: { ...analysis, resultJson: null } },
        ]}
      />,
    );
    expect(screen.getByText("Unavailable")).toBeVisible();
    expect(screen.queryByText("0.6200")).toBeNull();
    expect(screen.queryByText("62.0%")).toBeNull();
  });

  it("keeps a completed sequence score fixed when selecting an earlier MRI", () => {
    const { container } = render(
      <AnalysisWorkspace patient={patient} reload={vi.fn()} />,
    );
    expect(
      screen.getByRole("heading", {
        name: "Experimental sequence classification",
      }),
    ).toBeVisible();
    expect(
      screen.getByText(/Changing the selected MRI only changes the image/),
    ).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /Visit 1 Day 0/ }));
    expect(screen.getAllByText("0.6200")).toHaveLength(1);
    expect(screen.getByText(/completed 3-visit sequence/)).toHaveTextContent(
      "day 0–730",
    );
    expect(screen.queryByTestId("baseline-chart")).toBeNull();
    expect(
      screen.queryByRole("heading", { name: "Progression-risk estimate" }),
    ).toBeNull();
    expect(container).not.toHaveTextContent(/NaN|undefined/);
    expect(
      screen.getByText(/Image proxies, not trained-model attribution/),
    ).toBeVisible();
  });

  it("sends the trained mode by default and retains explicit legacy choices", async () => {
    const fetcher = vi.fn().mockImplementation(
      async () =>
        new Response(JSON.stringify({ ...analysis, status: "queued" }), {
          status: 202,
        }),
    );
    vi.stubGlobal("fetch", fetcher);
    const reload = vi.fn();
    render(<AnalysisWorkspace patient={patient} reload={reload} />);
    const select = screen.getByRole("combobox", { name: "Analysis mode" });
    expect(select).toHaveValue("trained");
    expect(within(select).getAllByRole("option")).toHaveLength(4);
    fireEvent.click(screen.getByRole("button", { name: "Analyze MRI" }));
    await waitFor(() => expect(reload).toHaveBeenCalledOnce());
    expect(fetcher).toHaveBeenLastCalledWith(
      "/api/analysis/synthetic-v2",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ outputMode: "trained" }),
      }),
    );

    fireEvent.change(select, { target: { value: "inference" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze MRI" }));
    await waitFor(() => expect(reload).toHaveBeenCalledTimes(2));
    expect(fetcher).toHaveBeenLastCalledWith(
      "/api/analysis/synthetic-v2",
      expect.objectContaining({
        body: JSON.stringify({ outputMode: "inference" }),
      }),
    );
  });

  it("requires three included MRI visits for trained mode while allowing explicit baseline", () => {
    render(<AnalysisWorkspace patient={patient} reload={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Visit 1 Day 0/ }));
    expect(screen.getByRole("button", { name: "Analyze MRI" })).toBeDisabled();
    expect(screen.getByText(/Only 1 MRI visits are included/)).toBeVisible();
    fireEvent.change(screen.getByRole("combobox", { name: "Analysis mode" }), {
      target: { value: "inference" },
    });
    expect(screen.getByRole("button", { name: "Analyze MRI" })).toBeEnabled();
  });

  it("shows backend trained errors without retrying as baseline", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: "Required recorded covariates are unavailable.",
        }),
        { status: 422 },
      ),
    );
    vi.stubGlobal("fetch", fetcher);
    const reload = vi.fn();
    render(<AnalysisWorkspace patient={patient} reload={reload} />);
    fireEvent.click(screen.getByRole("button", { name: "Analyze MRI" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Required recorded covariates are unavailable.",
      ),
    );
    expect(fetcher).toHaveBeenCalledOnce();
    expect(reload).not.toHaveBeenCalled();
    expect(screen.getByRole("combobox", { name: "Analysis mode" })).toHaveValue(
      "trained",
    );
  });

  it("renders the dashboard trained panel with an accurate title, not a risk trajectory", () => {
    vi.mocked(useResource).mockReturnValue({
      data: [patient],
      error: "",
      loading: false,
      reload: vi.fn(),
    });
    render(<Dashboard />);
    expect(
      screen.getByRole("heading", {
        name: "Experimental sequence classification",
      }),
    ).toBeVisible();
    expect(
      screen.queryByRole("heading", { name: "Progression-risk trajectory" }),
    ).toBeNull();
    expect(screen.queryByTestId("baseline-chart")).toBeNull();
    expect(
      screen.getByText("Experimental · poor generalization"),
    ).toBeVisible();
    expect(screen.getByText(prediction.checkpointSha256)).toBeVisible();
  });
});
