"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Niivue, NiiVueLocation } from "@niivue/niivue";
import {
  Box,
  Expand,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { VolumeCanvas } from "./volume-canvas";
import type { VolumeSettings } from "./volume-canvas";
import type { CameraPreset, ClipAxis, VolumeLayout } from "@/lib/volume-viewer";
import type { Analysis, Patient, Visit } from "@/types";
import { Button } from "./ui/button";
import { ModeBadge } from "./common";

const DEFAULTS: VolumeSettings = {
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

function RangeControl({
  label,
  value,
  min = 0,
  max = 100,
  step = 1,
  onChange,
}: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="volume-range">
      <span>
        {label}
        <span aria-hidden="true">{Number(value.toFixed(2))}</span>
      </span>
      <input
        type="range"
        aria-label={label}
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}

export function VolumeExplorer({
  patient,
  visit,
  analysis,
  onSelectVisit,
}: {
  patient: Patient;
  visit: Visit;
  analysis: Analysis | null;
  onSelectVisit: (id: string) => void;
}) {
  const panel = useRef<HTMLElement>(null);
  const instances = useRef(new Map<string, Niivue>());
  const [settings, setSettings] = useState<VolumeSettings>(DEFAULTS);
  const [compare, setCompare] = useState(false);
  const [linked, setLinked] = useState(true);
  const linkedRef = useRef(linked);
  linkedRef.current = linked;
  const [difference, setDifference] = useState(false);
  const [closed, setClosed] = useState(false);
  const [fullscreenError, setFullscreenError] = useState("");
  const baseline = patient.visits.find((v) => v.hasMri);
  const selectedIndex = patient.visits.findIndex((v) => v.id === visit.id);
  const result = analysis?.resultJson;
  const available =
    !!result?.volumeOverlaysReady && result.visitIds.includes(visit.id);
  const overlayUrl =
    difference && available
      ? `/api/analysis/${analysis!.id}/visits/${visit.id}/difference-volume`
      : undefined;
  const synchronize = useCallback(() => {
    const viewers = Array.from(instances.current.values());
    for (const viewer of viewers)
      viewer.broadcastTo(
        linkedRef.current ? viewers.filter((v) => v !== viewer) : [],
        {
          "2d": linkedRef.current,
          "3d": linkedRef.current,
        },
      );
  }, []);
  const onReady = useCallback(
    (id: string, viewer: Niivue | null) => {
      if (viewer) instances.current.set(id, viewer);
      else instances.current.delete(id);
      synchronize();
    },
    [synchronize],
  );
  useEffect(() => synchronize(), [linked, synchronize]);
  const onLocation = useCallback((location: NiiVueLocation) => {
    if (!Array.from(location.frac).every(Number.isFinite)) return;
    const position = Array.from(location.frac).map((v) =>
      Math.round(Math.max(0, Math.min(1, v)) * 100),
    ) as [number, number, number];
    setSettings((previous) =>
      previous.position.every((v, i) => v === position[i])
        ? previous
        : { ...previous, position },
    );
  }, []);
  const update = <K extends keyof VolumeSettings>(
    key: K,
    value: VolumeSettings[K],
  ) => setSettings((previous) => ({ ...previous, [key]: value }));
  return (
    <section
      ref={panel}
      className="panel volume-explorer"
      aria-label="3D brain exploration"
    >
      <div className="panel-heading">
        <div>
          <div className="eyebrow">SPATIAL MRI WORKSPACE</div>
          <h2>
            <Box size={20} />
            3D brain exploration
          </h2>
          <p>Actual scan voxels · Rotate, reveal, and compare across time</p>
        </div>
        <div className="volume-heading-actions">
          <span className="badge">NiiVue · WebGL2</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setClosed((v) => !v)}
          >
            {closed ? "Open 3D viewer" : "Pause 3D viewer"}
          </Button>
        </div>
      </div>
      {closed ? (
        <p className="volume-help">
          3D resources are released while paused. The lightweight 2D MRI viewer
          remains available below.
        </p>
      ) : (
        <>
          <div className="volume-toolbar">
            <div
              className="volume-layouts"
              role="group"
              aria-label="Volume display layout"
            >
              {(
                [
                  ["render", "3D volume"],
                  ["multiplanar", "Slices + 3D"],
                  ["axial", "Axial"],
                  ["coronal", "Coronal"],
                  ["sagittal", "Sagittal"],
                ] as [VolumeLayout, string][]
              ).map(([layout, label]) => (
                <button
                  key={layout}
                  aria-pressed={settings.layout === layout}
                  className={settings.layout === layout ? "selected" : ""}
                  onClick={() => update("layout", layout)}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="volume-utilities">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSettings((previous) => ({
                    ...DEFAULTS,
                    resetRevision: previous.resetRevision + 1,
                    positionRevision: previous.positionRevision + 1,
                  }));
                  setDifference(false);
                }}
              >
                {" "}
                <RotateCcw size={15} />
                Reset 3D
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={async () => {
                  try {
                    setFullscreenError("");
                    if (document.fullscreenElement)
                      await document.exitFullscreen();
                    else await panel.current?.requestFullscreen();
                  } catch {
                    setFullscreenError(
                      "Fullscreen is unavailable in this browser panel. Open the app in Edge or Chrome for fullscreen.",
                    );
                  }
                }}
              >
                <Expand size={15} />
                Fullscreen
              </Button>
            </div>
          </div>
          {fullscreenError && (
            <p className="volume-warning" role="status">
              {fullscreenError}
            </p>
          )}
          <div className="volume-body">
            <div className="volume-main">
              <div
                className={`volume-viewers ${compare && baseline && baseline.id !== visit.id ? "volume-compare" : ""}`}
              >
                {compare && baseline && baseline.id !== visit.id && (
                  <VolumeCanvas
                    key={`baseline:${baseline.id}`}
                    id="baseline"
                    label={`Baseline · ${baseline.label}`}
                    patientCode={patient.code}
                    url={
                      baseline.volumeUrl || `/api/visits/${baseline.id}/volume`
                    }
                    settings={settings}
                    onReady={onReady}
                  />
                )}
                <VolumeCanvas
                  key={`${visit.id}:${overlayUrl || "original"}`}
                  id="selected"
                  label={`Selected · ${visit.label}`}
                  patientCode={patient.code}
                  url={visit.volumeUrl || `/api/visits/${visit.id}/volume`}
                  overlayUrl={overlayUrl}
                  settings={settings}
                  onReady={onReady}
                  onLocation={onLocation}
                />
              </div>
              <div className="volume-navigation">
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={selectedIndex <= 0}
                  onClick={() => {
                    setDifference(false);
                    onSelectVisit(patient.visits[selectedIndex - 1].id);
                  }}
                >
                  <ChevronLeft size={15} />
                  Earlier MRI
                </Button>
                <span>
                  Day {visit.daysFromBaseline.toLocaleString()} ·{" "}
                  {selectedIndex + 1} / {patient.visits.length}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={selectedIndex >= patient.visits.length - 1}
                  onClick={() => {
                    setDifference(false);
                    onSelectVisit(patient.visits[selectedIndex + 1].id);
                  }}
                >
                  Later MRI
                  <ChevronRight size={15} />
                </Button>
              </div>
              <p className="volume-help">
                Drag to rotate in 3D; focus the canvas and scroll/pinch to zoom.
                In slice views, click to position the crosshair and scroll
                through slices. Header coordinates are display information, not
                validated clinical measurements.
              </p>
            </div>
            <aside className="volume-controls" aria-label="3D display controls">
              <h3>Explore the volume</h3>
              <label>
                Camera preset
                <select
                  aria-label="Camera preset"
                  value={settings.camera}
                  onChange={(e) =>
                    update("camera", e.target.value as CameraPreset)
                  }
                >
                  <option value="oblique">Oblique</option>
                  <option value="anterior">Anterior</option>
                  <option value="posterior">Posterior</option>
                  <option value="left">Left</option>
                  <option value="right">Right</option>
                  <option value="superior">Superior</option>
                </select>
              </label>
              <RangeControl
                label="3D zoom"
                min={0.5}
                max={2.5}
                step={0.05}
                value={settings.zoom}
                onChange={(v) => update("zoom", v)}
              />
              <label>
                Cutaway plane
                <select
                  aria-label="Cutaway plane"
                  value={settings.clip}
                  onChange={(e) => update("clip", e.target.value as ClipAxis)}
                >
                  <option value="off">No clipping</option>
                  <option value="axial">Axial cutaway</option>
                  <option value="coronal">Coronal cutaway</option>
                  <option value="sagittal">Sagittal cutaway</option>
                </select>
              </label>
              {settings.clip !== "off" && (
                <RangeControl
                  label="Cutaway depth"
                  min={-1}
                  max={1}
                  step={0.02}
                  value={settings.depth}
                  onChange={(v) => update("depth", v)}
                />
              )}
              <label>
                Volume colormap
                <select
                  aria-label="Volume colormap"
                  value={settings.colormap}
                  onChange={(e) => update("colormap", e.target.value)}
                >
                  <option value="gray">MRI grayscale</option>
                  <option value="bone">Bone / high contrast</option>
                  <option value="warm">Warm intensity</option>
                  <option value="viridis">Viridis intensity</option>
                </select>
              </label>
              <RangeControl
                label="MRI opacity"
                min={0.05}
                max={1}
                step={0.05}
                value={settings.opacity}
                onChange={(v) => update("opacity", v)}
              />
              <RangeControl
                label="Window lower (%)"
                max={settings.upper - 1}
                value={settings.lower}
                onChange={(v) => update("lower", v)}
              />
              <RangeControl
                label="Window upper (%)"
                min={settings.lower + 1}
                value={settings.upper}
                onChange={(v) => update("upper", v)}
              />
              <label className="volume-check">
                <input
                  type="checkbox"
                  checked={settings.outline}
                  onChange={(e) => update("outline", e.target.checked)}
                />
                Silhouette shading
              </label>
              <label className="volume-check">
                <input
                  type="checkbox"
                  checked={settings.crosshair}
                  onChange={(e) => update("crosshair", e.target.checked)}
                />
                Show crosshair
              </label>
              <div className="volume-control-divider">
                <h3>Crosshair position</h3>
                <small>Canonical XYZ fractions of the scan</small>
              </div>
              {(
                [
                  "X / left–right",
                  "Y / posterior–anterior",
                  "Z / inferior–superior",
                ] as const
              ).map((label, i) => (
                <RangeControl
                  key={label}
                  label={label}
                  value={settings.position[i]}
                  onChange={(v) =>
                    setSettings((previous) => {
                      const position = [...previous.position] as [
                        number,
                        number,
                        number,
                      ];
                      position[i] = v;
                      return {
                        ...previous,
                        position,
                        positionRevision: previous.positionRevision + 1,
                      };
                    })
                  }
                />
              ))}
              <div className="volume-control-divider">
                <h3>Longitudinal comparison</h3>
              </div>
              <label className="volume-check">
                <input
                  type="checkbox"
                  checked={compare}
                  disabled={!baseline || baseline.id === visit.id}
                  onChange={(e) => setCompare(e.target.checked)}
                />
                Compare with baseline
              </label>
              {compare && (
                <>
                  <small className="volume-note">
                    Display controls affect both panels. Linking also
                    synchronizes mouse navigation using header coordinates, not
                    registration.
                  </small>
                  <label className="volume-check">
                    <input
                      type="checkbox"
                      checked={linked}
                      onChange={(e) => setLinked(e.target.checked)}
                    />
                    Link cameras & crosshairs
                  </label>
                </>
              )}
              <label className="volume-check">
                <input
                  type="checkbox"
                  checked={difference && available}
                  disabled={!available}
                  onChange={(e) => setDifference(e.target.checked)}
                />
                3D difference overlay
              </label>
              {difference && available && (
                <>
                  <RangeControl
                    label="Difference opacity"
                    min={0.05}
                    max={1}
                    step={0.05}
                    value={settings.overlayOpacity}
                    onChange={(v) => update("overlayOpacity", v)}
                  />
                  <RangeControl
                    label="Difference threshold"
                    min={0.01}
                    max={0.29}
                    step={0.01}
                    value={settings.differenceThreshold}
                    onChange={(v) => update("differenceThreshold", v)}
                  />
                </>
              )}
              {!available && (
                <small className="volume-note">
                  Run trained or baseline inference on this sequence to prepare
                  the 3D difference overlay. Older cached results remain
                  available in 2D.
                </small>
              )}
              {difference && analysis && (
                <ModeBadge mode={analysis.outputMode} />
              )}
            </aside>
          </div>
          <div className="volume-disclaimer">
            <strong>Research visualization, not segmented anatomy.</strong> MRI
            includes non-brain head tissue. Linked views are not registered.
            Difference colors show shape-normalized intensity changes, not
            disease probability, atrophy or Grad-CAM.
            {analysis?.outputMode === "trained" &&
              " These differences are not attribution for the trained classifier."}
          </div>
        </>
      )}
    </section>
  );
}
