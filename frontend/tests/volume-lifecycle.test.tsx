import React from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { VolumeCanvas, type VolumeSettings } from "@/components/volume-canvas";

const state = vi.hoisted(() => ({
  attach: vi.fn(),
  cleanup: vi.fn(),
  broadcast: vi.fn(),
  lose: vi.fn(),
  pending: Promise.resolve() as Promise<void>,
}));
vi.mock("@niivue/niivue", () => ({
  NVMesh: { readMesh: vi.fn() },
  Niivue: class {
    canvas: HTMLCanvasElement | null = null;
    volumes = [];
    meshes = [];
    cleanup = state.cleanup;
    broadcastTo = state.broadcast;
    async attachToCanvas(canvas: HTMLCanvasElement) {
      this.canvas = canvas;
      state.attach();
      await state.pending;
    }
  },
  SHOW_RENDER: { ALWAYS: 1 },
  MULTIPLANAR_TYPE: { GRID: 1 },
  SLICE_TYPE: { RENDER: 4 },
}));
const settings: VolumeSettings = {
  layout: "render",
  colormap: "gray",
  opacity: 1,
  lower: 12,
  upper: 100,
  clip: "off",
  depth: 0,
  camera: "oblique",
  zoom: 1,
  crosshair: true,
  outline: false,
  overlayOpacity: 0.45,
  differenceThreshold: 0.04,
  position: [50, 50, 50],
  positionRevision: 0,
  resetRevision: 0,
};
beforeEach(() => {
  vi.clearAllMocks();
  state.pending = Promise.resolve();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
    getExtension: () => ({ loseContext: state.lose }),
  } as unknown as WebGL2RenderingContext);
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it("cleans up a late async attachment without reviving an unmounted viewer", async () => {
  let finish!: () => void;
  state.pending = new Promise<void>((resolve) => {
    finish = resolve;
  });
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const onReady = vi.fn();
  const view = render(
    <VolumeCanvas
      id="v"
      url="/api/visits/v/volume"
      label="Visit"
      patientCode="CASE"
      settings={settings}
      onReady={onReady}
    />,
  );
  await waitFor(() => expect(state.attach).toHaveBeenCalledOnce());
  view.unmount();
  expect(state.cleanup).toHaveBeenCalledOnce();
  finish();
  await waitFor(() => expect(state.cleanup).toHaveBeenCalledTimes(2));
  expect(fetcher).not.toHaveBeenCalled();
  expect(onReady).toHaveBeenCalledExactlyOnceWith("v", null);
  expect(state.lose).toHaveBeenCalledTimes(2);
});

it("aborts an in-flight MRI download when the selected visit is unmounted", async () => {
  let signal: AbortSignal | undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn((_url: string, options: { signal: AbortSignal }) => {
      signal = options.signal;
      return new Promise<Response>((_resolve, reject) =>
        signal!.addEventListener("abort", () =>
          reject(new DOMException("Aborted", "AbortError")),
        ),
      );
    }),
  );
  const onReady = vi.fn();
  const view = render(
    <VolumeCanvas
      id="v"
      url="/api/visits/v/volume"
      label="Visit"
      patientCode="CASE"
      settings={settings}
      onReady={onReady}
    />,
  );
  await waitFor(() => expect(signal).toBeDefined());
  view.unmount();
  expect(signal!.aborted).toBe(true);
  expect(state.cleanup).toHaveBeenCalledOnce();
  expect(onReady).toHaveBeenCalledExactlyOnceWith("v", null);
});
