"use client";
import { useEffect, useRef, useState } from "react";
import type { Niivue, NiiVueLocation } from "@niivue/niivue";
import { Download } from "lucide-react";
import { Button } from "./ui/button";
import { ErrorState, Loading } from "./common";
import {
  CAMERA_PRESETS,
  clipPlane,
  fetchVolume,
  fetchMesh,
  releaseViewer,
  saveResearchSnapshot,
  applyVolumeAppearance,
} from "@/lib/volume-viewer";
import type { CameraPreset, ClipAxis, VolumeLayout } from "@/lib/volume-viewer";

export type VolumeSettings = {
  layout: VolumeLayout;
  colormap: string;
  opacity: number;
  lower: number;
  upper: number;
  clip: ClipAxis;
  depth: number;
  camera: CameraPreset;
  zoom: number;
  crosshair: boolean;
  outline: boolean;
  overlayOpacity: number;
  differenceThreshold: number;
  position: [number, number, number];
  positionRevision: number;
  resetRevision: number;
};

type Props = {
  id: string;
  url: string;
  overlayUrl?: string;
  labelUrl?: string;
  meshes?: {
    url: string;
    color: [number, number, number, number];
    opacity: number;
  }[];
  kind?: "observed" | "predicted";
  label: string;
  patientCode: string;
  settings: VolumeSettings;
  onReady: (id: string, viewer: Niivue | null) => void;
  onLocation?: (value: NiiVueLocation) => void;
};

export function VolumeCanvas({
  id,
  url,
  overlayUrl,
  labelUrl,
  meshes,
  kind = "observed",
  label,
  patientCode,
  settings,
  onReady,
  onLocation,
}: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const viewer = useRef<Niivue | null>(null);
  const callbacks = useRef({ onReady, onLocation });
  callbacks.current = { onReady, onLocation };
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [readout, setReadout] = useState("");
  const [snapshotBusy, setSnapshotBusy] = useState(false);
  const range = useRef<[number, number]>([0, 1]);
  const meshSpec = JSON.stringify(meshes || []);

  useEffect(() => {
    const controller = new AbortController();
    let alive = true;
    let instance: Niivue | null = null;
    const element = canvas.current;
    function contextLost() {
      if (!alive) return;
      setLoaded(false);
      setError(
        "The 3D graphics context was lost. Retry to reopen it, or use the 2D MRI viewer below.",
      );
      callbacks.current.onReady(id, null);
    }
    element?.addEventListener("webglcontextlost", contextLost);
    function wasDisposed(): boolean {
      if (alive) return false;
      // Async attachment/loading can finish after the first unmount cleanup.
      if (instance) releaseViewer(instance);
      return true;
    }
    setLoaded(false);
    setError("");
    async function initialize() {
      try {
        const { Niivue, NVMesh, SHOW_RENDER, MULTIPLANAR_TYPE, SLICE_TYPE } =
          await import("@niivue/niivue");
        if (!alive || !canvas.current) return;
        const gl = canvas.current.getContext("webgl2", { antialias: true });
        if (!gl)
          throw new Error(
            "WebGL2 is unavailable. Enable browser graphics acceleration, or use the 2D MRI viewer below.",
          );
        instance = new Niivue({
          backColor: [0.025, 0.045, 0.075, 1],
          fontColor: [0.75, 0.85, 0.93, 1],
          crosshairColor: [0.28, 0.9, 0.8, 1],
          crosshairWidth: 1,
          show3Dcrosshair: true,
          isOrientCube: true,
          isRadiologicalConvention: false,
          multiplanarLayout: MULTIPLANAR_TYPE.GRID,
          multiplanarShowRender: SHOW_RENDER.ALWAYS,
          multiplanarEqualSize: true,
          sliceType: SLICE_TYPE.RENDER,
          dragAndDropEnabled: false,
          drawingEnabled: false,
          scrollRequiresFocus: true,
          isRuler: false,
          isColorbar: false,
          // Apply the MRI cutaway to segmentation/difference volumes as well.
          // NiiVue otherwise leaves the entire overlay visible through removed tissue.
          isClipAllVolumes: true,
          logLevel: "error",
          forceDevicePixelRatio: 1,
        });
        await instance.attachToCanvas(canvas.current);
        if (wasDisposed()) return;
        instance.onLocationChange = (value) => {
          if (!alive || !value || typeof value !== "object") return;
          const location = value as NiiVueLocation;
          if (
            !location.frac ||
            !location.mm ||
            !Array.from(location.mm).slice(0, 3).every(Number.isFinite)
          )
            return;
          setReadout(
            `Header XYZ: ${Array.from(location.mm)
              .slice(0, 3)
              .map((v) => v.toFixed(1))
              .join(" / ")}`,
          );
          callbacks.current.onLocation?.(location);
        };
        const source = await fetchVolume(url, controller.signal);
        if (wasDisposed()) return;
        await instance.loadFromArrayBuffer(source.buffer, source.name);
        if (wasDisposed()) return;
        const volume = instance.volumes[0];
        if (!volume) throw new Error("The MRI volume could not be parsed.");
        const low = Number(volume.robust_min ?? volume.cal_min);
        const high = Number(volume.robust_max ?? volume.cal_max);
        range.current =
          Number.isFinite(low) && high > low ? [low, high] : [0, 1];
        if (overlayUrl) {
          const overlay = await fetchVolume(overlayUrl, controller.signal);
          if (wasDisposed()) return;
          await instance.loadFromArrayBuffer(overlay.buffer, overlay.name);
          if (wasDisposed()) return;
        }
        if (labelUrl) {
          const labels = await fetchVolume(labelUrl, controller.signal);
          if (wasDisposed()) return;
          await instance.loadFromArrayBuffer(labels.buffer, labels.name);
          if (wasDisposed()) return;
          const numbers = [
            0, 4, 17, 43, 53, 1006, 1008, 1009, 1015, 1025, 1029, 1030, 2006,
            2008, 2009, 2015, 2025, 2029, 2030,
          ];
          const colors = numbers.map((n) =>
            n === 17 || n === 53 ? [220, 216, 20, 255] : [0, 0, 0, 0],
          );
          instance.volumes[instance.volumes.length - 1].setColormapLabel({
            I: numbers,
            R: colors.map((c) => c[0]),
            G: colors.map((c) => c[1]),
            B: colors.map((c) => c[2]),
            A: colors.map((c) => c[3]),
          });
          instance.setInterpolation(true); // categorical overlays must not blend labels
        }
        const selectedMeshes: NonNullable<Props["meshes"]> =
          JSON.parse(meshSpec);
        if (selectedMeshes.length > 20)
          throw new Error("Too many region meshes.");
        for (const [index, item] of selectedMeshes.entries()) {
          if (
            item.color.length !== 4 ||
            item.color.some((v) => !Number.isInteger(v) || v < 0 || v > 255) ||
            !Number.isFinite(item.opacity) ||
            item.opacity < 0 ||
            item.opacity > 1
          )
            throw new Error("Invalid mesh appearance.");
          const buffer = await fetchMesh(item.url, controller.signal);
          if (wasDisposed()) return;
          const loadedMesh = await NVMesh.readMesh(
            buffer,
            `anatomy-${index}.gii`,
            instance.gl,
            item.opacity,
            new Uint8Array(item.color),
          );
          if (wasDisposed()) return;
          if (!loadedMesh)
            throw new Error("The GIFTI mesh could not be parsed.");
          instance.addMesh(loadedMesh);
        }
        viewer.current = instance;
        setLoaded(true);
        callbacks.current.onReady(id, instance);
      } catch (e) {
        if (alive && !controller.signal.aborted)
          setError(
            e instanceof Error
              ? e.message
              : "The 3D viewer could not be initialized.",
          );
      }
    }
    void initialize();
    return () => {
      alive = false;
      controller.abort();
      element?.removeEventListener("webglcontextlost", contextLost);
      callbacks.current.onReady(id, null);
      viewer.current = null;
      if (instance) releaseViewer(instance);
    };
  }, [id, url, overlayUrl, labelUrl, meshSpec, retry]);

  useEffect(() => {
    const nv = viewer.current;
    if (!loaded || !nv) return;
    const types = {
      axial: nv.sliceTypeAxial,
      coronal: nv.sliceTypeCoronal,
      sagittal: nv.sliceTypeSagittal,
      render: nv.sliceTypeRender,
      multiplanar: nv.sliceTypeMultiplanar,
    };
    nv.setSliceType(types[settings.layout]);
    nv.opts.show3Dcrosshair = settings.crosshair;
    nv.setCrosshairWidth(settings.crosshair ? 1 : 0);
  }, [loaded, settings.layout, settings.crosshair, settings.resetRevision]);

  useEffect(() => {
    if (loaded)
      viewer.current?.setClipPlane(clipPlane(settings.clip, settings.depth));
  }, [loaded, settings.clip, settings.depth, settings.resetRevision]);
  useEffect(() => {
    if (loaded)
      viewer.current?.setRenderAzimuthElevation(
        ...CAMERA_PRESETS[settings.camera],
      );
  }, [loaded, settings.camera, settings.resetRevision]);
  useEffect(() => {
    if (loaded) viewer.current?.setScale(settings.zoom);
  }, [loaded, settings.zoom, settings.resetRevision]);

  useEffect(() => {
    const nv = viewer.current;
    if (!loaded || !nv?.volumes[0]) return;
    applyVolumeAppearance(nv, range.current, {
      ...settings,
      anatomyIndex: labelUrl ? (overlayUrl ? 2 : 1) : undefined,
    });
  }, [
    loaded,
    settings.lower,
    settings.upper,
    settings.colormap,
    settings.opacity,
    settings.overlayOpacity,
    settings.differenceThreshold,
    labelUrl,
    overlayUrl,
  ]);

  useEffect(() => {
    const nv = viewer.current;
    if (!loaded || !nv) return;
    void nv
      .setGradientOpacity(
        settings.outline ? 0.4 : 0,
        settings.outline ? 0.35 : 0,
      )
      .catch(() => {
        if (viewer.current === nv)
          setError(
            "Surface shading is unavailable. Turn off silhouette shading or reset the viewer.",
          );
      });
  }, [loaded, settings.outline]);

  const positionRef = useRef(settings.position);
  positionRef.current = settings.position;
  useEffect(() => {
    const nv = viewer.current;
    if (!loaded || !nv) return;
    nv.scene.crosshairPos = positionRef.current.map((v) => v / 100) as [
      number,
      number,
      number,
    ];
    nv.drawScene();
    nv.createOnLocationChange();
  }, [loaded, settings.positionRevision, settings.resetRevision]);

  return (
    <div
      className="volume-card"
      data-volume-ready={loaded && !error ? "true" : "false"}
    >
      <div className="volume-card-heading">
        <strong>{label}</strong>
        <span className="badge">
          {kind === "predicted"
            ? "Predicted anatomy · not acquired MRI"
            : labelUrl
              ? "Observed MRI + measured regions"
              : overlayUrl
                ? "MRI + difference proxy"
                : "Observed source MRI"}
        </span>
      </div>
      <div className="volume-canvas-wrap">
        <canvas
          key={`${url}|${overlayUrl || ""}|${labelUrl || ""}|${meshSpec}|${retry}`}
          ref={canvas}
          tabIndex={0}
          aria-label={`Interactive brain MRI for ${label}`}
        />
        {!loaded && !error && (
          <div className="volume-state">
            <Loading text="Loading local MRI into 3D…" />
          </div>
        )}
        {error && (
          <div className="volume-state">
            <ErrorState
              message={error}
              onRetry={() => setRetry((v) => v + 1)}
            />
          </div>
        )}
      </div>
      <div className="volume-readout">
        <small>
          {loaded
            ? readout || "Select a slice location to inspect header coordinates"
            : "Research visualization"}
        </small>
        <Button
          variant="ghost"
          size="sm"
          disabled={!loaded || !!error || snapshotBusy}
          onClick={async () => {
            if (!viewer.current) return;
            setSnapshotBusy(true);
            try {
              await saveResearchSnapshot(
                viewer.current,
                `NeuroPredict-${patientCode}-${id}-RESEARCH.png`,
                `${patientCode} | ${label} | ${kind === "predicted" ? "Predicted anatomy - not acquired MRI" : labelUrl ? "Observed MRI / measured regions - verify QC" : overlayUrl ? "Intensity-difference proxy" : "Observed source MRI"}`,
                kind === "predicted"
                  ? "Predicted anatomy - not acquired MRI"
                  : "Not registered anatomy",
              );
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setSnapshotBusy(false);
            }
          }}
        >
          <Download size={14} />
          Save PNG
        </Button>
      </div>
    </div>
  );
}
