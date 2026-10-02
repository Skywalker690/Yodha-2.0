import React from "react";
import { expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import AnatomyPreviewPage from "@/app/(workspace)/preview/page";

const state = vi.hoisted(() => ({
  data: {
    status: "available",
    subjectCode: "OAS2_0073",
    patientId: "sample",
    cutoffVisitId: "cutoff",
    cutoffDay: 2288,
    observedLabelsUrl: "/api/analysis/measured/visits/cutoff/anatomy/regions",
    intervalDays: 229,
    modelVersion: "historical-candidate",
    modelSha256: "e".repeat(64),
    evaluationStatus: "saved_retrospective_example",
    studySubjectCount: 6,
    gradientTrainingSubjectCount: 4,
    trainingEpochs: 20,
    warnings: ["Candidate failed release checks"],
  },
}));
vi.mock("@/lib/use-resource", () => ({
  useResource: () => ({
    data: state.data,
    loading: false,
    error: "",
    reload: vi.fn(),
  }),
}));
vi.mock("@/components/volume-canvas", () => ({
  VolumeCanvas: (props: {
    id: string;
    url: string;
    label: string;
    labelUrl?: string;
  }) => (
    <div
      data-testid={props.id}
      data-url={props.url}
      data-labels={props.labelUrl}
    >
      {props.label}
    </div>
  ),
}));

it("shows the actual saved interval and subject with separate acquired/predicted resources", () => {
  render(<AnatomyPreviewPage />);
  expect(screen.getByText("+229 days")).toBeVisible();
  expect(screen.getByText("OAS2_0073")).toBeVisible();
  expect(screen.getByTestId("preview-observed")).toHaveAttribute(
    "data-url",
    "/api/visits/cutoff/volume",
  );
  expect(screen.getByTestId("preview-predicted")).toHaveAttribute(
    "data-url",
    "/api/anatomy-preview/mri?intervalDays=229",
  );
  expect(screen.getByTestId("preview-observed")).toHaveAttribute(
    "data-labels",
    "/api/analysis/measured/visits/cutoff/anatomy/regions",
  );
  expect(screen.getByText(/unvalidated and was not/)).toBeVisible();
  fireEvent.click(
    screen.getByRole("checkbox", { name: "Hippocampus highlight" }),
  );
  expect(screen.getByTestId("preview-predicted")).not.toHaveAttribute(
    "data-labels",
  );
  expect(screen.getByTestId("preview-observed")).not.toHaveAttribute(
    "data-labels",
  );
});

it("renders no substituted volume when the saved example is unavailable", () => {
  const previous = state.data;
  state.data = { ...previous, status: "unavailable" };
  try {
    render(<AnatomyPreviewPage />);
    expect(screen.getByText("Saved preview unavailable")).toBeVisible();
    expect(screen.queryByTestId("preview-predicted")).not.toBeInTheDocument();
  } finally {
    state.data = previous;
  }
});
