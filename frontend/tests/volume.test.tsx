import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import {
  CAMERA_PRESETS,
  clipPlane,
  fetchVolume,
  releaseViewer,
  applyVolumeAppearance,
} from "@/lib/volume-viewer";
import { VolumeExplorer } from "@/components/volume-explorer";
import type { Analysis, Patient, Visit } from "@/types";
import type { Niivue } from "@niivue/niivue";
import type { VolumeSettings } from "@/components/volume-canvas";

vi.mock("@/components/volume-canvas", () => ({
  VolumeCanvas: ({
    label,
    overlayUrl,
    settings,
  }: {
    label: string;
    overlayUrl?: string;
    settings: VolumeSettings;
  }) => (
    <div data-testid="viewer">
      {label}
      <output data-testid="settings">{JSON.stringify(settings)}</output>
      {overlayUrl && <span>Difference loaded</span>}
    </div>
  ),
}));
const visits = [0, 365, 730].map((days, i) => ({
  id: `v${i}`,
  label: `Visit ${i + 1}`,
  daysFromBaseline: days,
  hasMri: true,
  previewUrl: `/api/visits/v${i}/preview`,
  metadata: {},
})) satisfies Visit[];
const patient = { id: "p", code: "RESEARCH", visits } as Patient;
const analysis = {
  id: "a",
  outputMode: "inference",
  resultJson: {
    visitIds: visits.map((v) => v.id),
    volumeOverlaysReady: true,
  },
} as Analysis;
afterEach(() => vi.unstubAllGlobals());

describe("volume safety and geometry controls", () => {
  it("preserves explicit windows and thresholds after colormap recalibration", () => {
    const createImage = () => ({
      colormap: "gray",
      cal_min: 0,
      cal_max: 1,
      opacity: 1,
      setColormap(name: string) {
        this.colormap = name;
        this.cal_min = 0;
        this.cal_max = 99;
      },
    });
    const images = [createImage(), createImage()];
    const updateGLVolume = vi.fn();
    applyVolumeAppearance(
      { volumes: images, updateGLVolume } as unknown as Niivue,
      [10, 110],
      {
        colormap: "bone",
        lower: 20,
        upper: 90,
        opacity: 0.8,
        overlayOpacity: 0.45,
        differenceThreshold: 0.04,
      },
    );
    expect(images[0].cal_min).toBe(30);
    expect(images[0].cal_max).toBe(100);
    expect(images[1].cal_min).toBe(0.04);
    expect(images[1].cal_max).toBe(0.3);
    expect(images[1].colormap).toBe("warm");
    expect(images[1].opacity).toBe(0.45);
    expect(updateGLVolume).toHaveBeenCalledOnce();
  });
  it("clamps clipping and uses an explicit disabled plane", () => {
    expect(clipPlane("off", 0)).toEqual([2, 0, 0]);
    expect(clipPlane("axial", 5)).toEqual([1, 0, 90]);
    expect(clipPlane("sagittal", -5)).toEqual([-1, 90, 0]);
    expect(Object.keys(CAMERA_PRESETS)).toHaveLength(6);
  });
  it("rejects non-local and traversal URLs before fetching", async () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    for (const url of [
      "https://external.test/scan.nii",
      "/api/../secrets",
      "//external.test/api/a",
    ])
      await expect(
        fetchVolume(url, new AbortController().signal),
      ).rejects.toThrow("Invalid local");
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("loads authenticated buffers and identifies gzip by content", async () => {
    const signal = new AbortController().signal;
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(new Uint8Array([31, 139, 0])));
    vi.stubGlobal("fetch", fetcher);
    const value = await fetchVolume("/api/visits/v/volume", signal);
    expect(value.name).toBe("volume.nii.gz");
    expect(value.buffer.byteLength).toBe(3);
    expect(fetcher).toHaveBeenCalledWith("/api/visits/v/volume", {
      signal,
      credentials: "same-origin",
      cache: "no-store",
    });
  });
  it("rejects expired sessions and oversized downloads", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        new Response(null, { headers: { "content-length": "104857601" } }),
      )
      .mockResolvedValueOnce(new Response(null));
    vi.stubGlobal("fetch", fetcher);
    const signal = new AbortController().signal;
    await expect(fetchVolume("/api/a", signal)).rejects.toThrow(
      "Session expired",
    );
    await expect(fetchVolume("/api/a", signal)).rejects.toThrow(
      "loading limit",
    );
    await expect(fetchVolume("/api/a", signal)).rejects.toThrow(
      "Invalid or oversized",
    );
  });
  it("releases broadcasts, image data and the GPU context, including failed attachment", () => {
    const loseContext = vi.fn();
    const cleanup = vi.fn();
    const broadcastTo = vi.fn();
    const viewer = {
      cleanup,
      broadcastTo,
      volumes: [1],
      meshes: [1],
      canvas: {
        getContext: () => ({ getExtension: () => ({ loseContext }) }),
      },
    } as unknown as Niivue;
    releaseViewer(viewer);
    expect(broadcastTo).toHaveBeenCalledWith([], { "2d": false, "3d": false });
    expect(cleanup).toHaveBeenCalledOnce();
    expect(loseContext).toHaveBeenCalledOnce();
    expect(viewer.volumes).toEqual([]);
    expect(viewer.meshes).toEqual([]);
    expect(() =>
      releaseViewer({
        cleanup: vi.fn(),
        broadcastTo: vi.fn(),
      } as unknown as Niivue),
    ).not.toThrow();
  });
});

describe("research volume explorer", () => {
  it("does not present trained-mode intensity differences as neural attribution", () => {
    render(
      <VolumeExplorer
        patient={patient}
        visit={visits[2]}
        analysis={{ ...analysis, outputMode: "trained" }}
        onSelectVisit={vi.fn()}
      />,
    );
    expect(
      screen.getByText(/not attribution for the trained classifier/),
    ).toBeVisible();
    fireEvent.click(screen.getByLabelText("3D difference overlay"));
    expect(
      screen.getByText("Output mode: Trained · experimental"),
    ).toBeVisible();
  });
  it("keeps legacy results honest and navigation connected to the visit timeline", () => {
    const onSelectVisit = vi.fn();
    render(
      <VolumeExplorer
        patient={patient}
        visit={visits[2]}
        analysis={null}
        onSelectVisit={onSelectVisit}
      />,
    );
    expect(screen.getByLabelText("3D difference overlay")).toBeDisabled();
    expect(screen.getByText(/not segmented anatomy/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Earlier MRI" }));
    expect(onSelectVisit).toHaveBeenCalledWith("v1");
  });
  it("changes layouts, clipping, overlays and comparison without more than two viewers", () => {
    render(
      <VolumeExplorer
        patient={patient}
        visit={visits[2]}
        analysis={analysis}
        onSelectVisit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Slices + 3D" }));
    expect(screen.getByRole("button", { name: "Slices + 3D" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    fireEvent.change(screen.getByLabelText("Cutaway plane"), {
      target: { value: "axial" },
    });
    expect(screen.getByLabelText("Cutaway depth")).toBeVisible();
    fireEvent.click(screen.getByLabelText("3D difference overlay"));
    expect(screen.getByText("Difference loaded")).toBeVisible();
    expect(screen.getByText("Output mode: Inference")).toBeVisible();
    fireEvent.click(screen.getByLabelText("Compare with baseline"));
    expect(screen.getAllByTestId("viewer")).toHaveLength(2);
    expect(screen.getByLabelText("Link cameras & crosshairs")).toBeChecked();
    fireEvent.click(screen.getByRole("button", { name: "Reset 3D" }));
    expect(screen.queryByText("Difference loaded")).toBeNull();
    expect(screen.getByRole("button", { name: "3D volume" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
  it("unmounts GPU canvases when paused and restores the workspace", () => {
    render(
      <VolumeExplorer
        patient={patient}
        visit={visits[2]}
        analysis={analysis}
        onSelectVisit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Pause 3D viewer" }));
    expect(screen.queryByTestId("viewer")).toBeNull();
    expect(screen.getByText(/resources are released/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Open 3D viewer" }));
    expect(screen.getAllByTestId("viewer")).toHaveLength(1);
  });
});
