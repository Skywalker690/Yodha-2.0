import React from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { Analysis, AnatomyResult, Patient, Visit } from "@/types";
import { VolumeExplorer } from "@/components/volume-explorer";

const resources = vi.hoisted(() => ({
  model: {
    status: "available",
    intervalsDays: [0, 183, 365, 731],
    releaseSha256: "e".repeat(64),
  },
  cached: [] as Analysis[],
  post: vi.fn(),
}));
vi.mock("@/lib/use-resource", () => ({
  useResource: (path: string) => ({
    data: path.includes("readiness") ? resources.model : resources.cached,
    loading: false,
    error: "",
    reload: vi.fn(),
  }),
}));
vi.mock("@/lib/api", () => ({ post: resources.post }));
vi.mock("@/components/volume-canvas", () => ({
  VolumeCanvas: (props: {
    id: string;
    url: string;
    kind?: string;
    labelUrl?: string;
    meshes?: unknown[];
  }) => (
    <div
      data-testid={`canvas-${props.id}`}
      data-url={props.url}
      data-kind={props.kind || "observed"}
      data-labels={props.labelUrl}
      data-meshes={props.meshes?.length || 0}
    />
  ),
}));
const visits = [0, 600].map((day, index) => ({
  id: `v${index}`,
  label: `Visit ${index}`,
  daysFromBaseline: day,
  hasMri: true,
  previewUrl: null,
  metadata: {},
})) as Visit[];
const anatomy = {
  visits: visits.map((v) => ({
    visitId: v.id,
    daysFromBaseline: v.daysFromBaseline,
    qc: "passed",
    sourceSha256: "a".repeat(64),
    segmentationSha256: "b".repeat(64),
    statisticsSha256: "c".repeat(64),
    ratings: { status: "ok", provenanceSha256: "d".repeat(64) },
  })),
  forecast: {
    status: "unavailable",
    cutoffVisitId: "v1",
    intervalDays: 365,
    warnings: [],
    artifacts: [],
  },
} as unknown as AnatomyResult;
const measured = {
  id: "measurement",
  status: "completed",
  resultJson: { anatomy },
} as Analysis;
const patient = {
  id: "p",
  code: "SYNTHETIC",
  visits,
  completedAnatomy: measured,
} as Patient;
function future(intervalDays = 365): Analysis {
  return {
    id: "predicted",
    status: "completed",
    resultJson: {
      anatomy: {
        ...anatomy,
        forecast: {
          status: "available",
          cutoffVisitId: "v1",
          intervalDays,
          releaseSha256: "e".repeat(64),
          modelSha256: "f".repeat(64),
          artifacts: [
            { name: "brain_mesh", kind: "mesh", sha256: "1".repeat(64) },
            {
              name: "hippocampus_left_mm3",
              kind: "mesh",
              sha256: "2".repeat(64),
            },
          ],
          warnings: [],
        },
      },
    },
  } as unknown as Analysis;
}
beforeEach(() => {
  resources.cached = [];
  resources.post.mockReset().mockResolvedValue({ id: "job", status: "queued" });
});
afterEach(() => vi.unstubAllGlobals());

it("queues the selected supported interval and cutoff through the existing async API", async () => {
  render(
    <VolumeExplorer
      patient={patient}
      visit={visits[1]}
      analysis={null}
      anatomyAnalysis={measured}
      onSelectVisit={vi.fn()}
      reload={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByLabelText("Compare current vs predicted"));
  fireEvent.change(screen.getByLabelText("Future time after latest scan"), {
    target: { value: "24" },
  });
  expect(screen.getByText(/Requested interval: 731 days/)).toBeVisible();
  fireEvent.click(
    screen.getByRole("button", { name: "Generate evaluated future anatomy" }),
  );
  await waitFor(() =>
    expect(resources.post).toHaveBeenCalledWith(
      "/analysis/measurement/forecast",
      { intervalDays: 731, cutoffVisitId: "v1" },
    ),
  );
  expect(screen.queryByTestId("canvas-predicted")).not.toBeInTheDocument();
});

it("loads matching predicted NIfTI, labels and meshes while preserving the observed MRI", () => {
  resources.cached = [future()];
  render(
    <VolumeExplorer
      patient={patient}
      visit={visits[1]}
      analysis={null}
      anatomyAnalysis={measured}
      onSelectVisit={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByLabelText("Compare current vs predicted"));
  expect(screen.getByTestId("canvas-selected")).toHaveAttribute(
    "data-url",
    "/api/visits/v1/volume",
  );
  const predicted = screen.getByTestId("canvas-predicted");
  expect(predicted).toHaveAttribute(
    "data-url",
    "/api/analysis/predicted/future/mri",
  );
  expect(predicted).toHaveAttribute("data-kind", "predicted");
  expect(predicted).toHaveAttribute(
    "data-labels",
    "/api/analysis/predicted/future/labels",
  );
  fireEvent.click(screen.getByLabelText("Predicted mask-boundary meshes"));
  expect(screen.getByTestId("canvas-predicted")).toHaveAttribute(
    "data-meshes",
    "2",
  );
});

it("rejects cached predictions for different segmentation provenance or unsupported times", () => {
  const changed = future();
  changed.resultJson!.anatomy!.visits = changed.resultJson!.anatomy!.visits.map(
    (v) => ({ ...v, segmentationSha256: "0".repeat(64) }),
  );
  resources.cached = [changed];
  render(
    <VolumeExplorer
      patient={patient}
      visit={visits[1]}
      analysis={null}
      anatomyAnalysis={measured}
      onSelectVisit={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByLabelText("Compare current vs predicted"));
  expect(screen.getByText("Future anatomy unavailable")).toBeVisible();
  expect(screen.queryByTestId("canvas-predicted")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Future time after latest scan"), {
    target: { value: "36" },
  });
  expect(
    screen.getByRole("button", { name: "Generate evaluated future anatomy" }),
  ).toBeDisabled();
});

it("requires two reviewed and alignment-checked observations before enabling generation", () => {
  render(
    <VolumeExplorer
      patient={patient}
      visit={visits[0]}
      analysis={null}
      anatomyAnalysis={measured}
      onSelectVisit={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByLabelText("Compare current vs predicted"));
  expect(
    screen.getByRole("button", { name: "Generate evaluated future anatomy" }),
  ).toBeDisabled();
});
