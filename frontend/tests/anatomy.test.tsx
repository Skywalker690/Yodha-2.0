import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AnatomyPanel } from "@/components/anatomy-panel";
import { fetchMesh } from "@/lib/volume-viewer";
import type { Patient, Analysis, AnatomyResult } from "@/types";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  LineChart: () => <div>Observed nWBV chart</div>,
  Line: () => null,
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
}));
const patient = {
  id: "p",
  code: "SYNTHETIC",
  visits: [
    {
      id: "v0",
      label: "Baseline",
      daysFromBaseline: 0,
      hasMri: true,
      previewUrl: null,
      metadata: {},
    },
  ],
} as Patient;
const anatomy = {
  version: "longitudinal-anatomy-v1",
  signConvention: "later minus earlier",
  visits: [
    {
      visitId: "v0",
      daysFromBaseline: 0,
      qc: "pending_review",
      method: "FastSurfer",
      fastsurferVersion: "2.5.4",
      dictionaryVersion: "dkt-longitudinal-v1",
      sourceSha256: "a".repeat(64),
      segmentationSha256: "b".repeat(64),
      statisticsSha256: "c".repeat(64),
      containerDigest: "deepmi/fastsurfer@sha256:" + "d".repeat(64),
      volumesMm3: { hippocampusLeftMm3: 4000 },
      maskVolumesMm3: { hippocampusLeftMm3: 3900 },
      hippocampalAsymmetryPercent: 1,
      etivMm3: 1500000,
      headSizeRatios: { hippocampusLeftMm3: 4000 / 1500000 },
      ratings: {
        status: "pending_alignment_qc",
        method: "AVRA-v0.8",
        mtaLeft: null,
        mtaRight: null,
        posteriorAtrophy: null,
        warnings: ["Alignment review required"],
      },
    },
  ],
  changes: [],
  forecast: {
    status: "unavailable",
    cutoffVisitId: "v0",
    intervalDays: 365,
    warnings: [],
    artifacts: [],
  },
} as AnatomyResult;
const completed = {
  id: "anatomy-a",
  status: "completed",
  progress: 100,
  stage: "Measured",
  resultJson: { anatomy },
} as Analysis;
afterEach(() => vi.unstubAllGlobals());

it("requires explicit visual review and shows no substituted atrophy ratings", () => {
  render(
    <AnatomyPanel
      patient={{
        ...patient,
        latestAnatomy: completed,
        completedAnatomy: completed,
      }}
      visit={patient.visits[0]}
      reload={vi.fn()}
    />,
  );
  expect(screen.getAllByText("Unavailable").length).toBeGreaterThanOrEqual(3);
  expect(screen.getByText("Alignment review required")).toBeInTheDocument();
  const confirm = screen.getByRole("button", {
    name: "Record visual segmentation review",
  });
  expect(confirm).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox"));
  expect(confirm).toBeEnabled();
  expect(screen.getByText("0.002667")).toBeInTheDocument();
});

it("requests the selected anatomy report explicitly instead of replacing the legacy report", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue(
      new Response(
        JSON.stringify({ id: "r", downloadUrl: "/api/reports/r/download" }),
        { status: 201 },
      ),
    );
  vi.stubGlobal("fetch", fetcher);
  render(
    <AnatomyPanel
      patient={{ ...patient, completedAnatomy: completed }}
      visit={patient.visits[0]}
      reload={vi.fn()}
    />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Generate anatomy research report" }),
  );
  await waitFor(() => expect(fetcher).toHaveBeenCalled());
  expect(fetcher.mock.calls[0][0]).toBe("/api/reports/p?analysis_id=anatomy-a");
});

it("loads bounded owned GIFTI buffers and rejects unsafe URLs", async () => {
  const signal = new AbortController().signal;
  const fetcher = vi.fn().mockResolvedValue(new Response("<GIFTI/>"));
  vi.stubGlobal("fetch", fetcher);
  await expect(
    fetchMesh("/api/analysis/a/mesh", signal),
  ).resolves.toBeInstanceOf(ArrayBuffer);
  expect(fetcher).toHaveBeenCalledWith(
    "/api/analysis/a/mesh",
    expect.objectContaining({
      credentials: "same-origin",
      cache: "no-store",
      signal,
    }),
  );
  for (const url of [
    "https://outside.test/mesh",
    "/api/../private",
    "/api/%2e%2e/private",
  ])
    await expect(fetchMesh(url, signal)).rejects.toThrow("Invalid local mesh");
});

it("rejects oversized mesh headers before streaming", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response("<GIFTI/>", {
        headers: { "content-length": String(31 * 1024 * 1024) },
      }),
    ),
  );
  await expect(
    fetchMesh("/api/analysis/a/mesh", new AbortController().signal),
  ).rejects.toThrow("loading limit");
});
