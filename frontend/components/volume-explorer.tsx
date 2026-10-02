"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { post } from "@/lib/api";
import { useResource } from "@/lib/use-resource";

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

const FORECAST_DAYS: Record<number, number> = {
  0: 0,
  6: 183,
  12: 365,
  24: 731,
  36: 1096,
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
  anatomyAnalysis = null,
  onSelectVisit,
  reload,
}: {
  patient: Patient;
  visit: Visit;
  analysis: Analysis | null;
  anatomyAnalysis?: Analysis | null;
  onSelectVisit: (id: string) => void;
  reload?: () => void;
}) {
  const panel = useRef<HTMLElement>(null);
  const instances = useRef(new Map<string, Niivue>());
  const [settings, setSettings] = useState<VolumeSettings>(DEFAULTS);
  const [compare, setCompare] = useState(false);
  const [linked, setLinked] = useState(true);
  const linkedRef = useRef(linked);
  linkedRef.current = linked;
  const [difference, setDifference] = useState(false);
  const [regions, setRegions] = useState(true);
  const [futureCompare, setFutureCompare] = useState(false);
  const [futureMonths, setFutureMonths] = useState(12);
  const [selectedFutureMonth, setSelectedFutureMonth] = useState<number | null>(
    null,
  );
  const [alignment, setAlignment] = useState(false);
  const [meshes, setMeshes] = useState(false);
  const [animating, setAnimating] = useState(false);
  const [forecastBusy, setForecastBusy] = useState(false);
  const [forecastError, setForecastError] = useState("");
  const model = useResource<{
    status: string;
    intervalsDays: number[];
    releaseSha256?: string;
    reason?: string;
  }>("/anatomy-model/readiness", 10000);
  const cached = useResource<Analysis[]>(
    `/patients/${patient.id}/anatomy-forecasts`,
    2500,
  );
  const [closed, setClosed] = useState(false);
  const [fullscreenError, setFullscreenError] = useState("");
  const baseline = patient.visits.find((v) => v.hasMri);
  const cutoffVisit =
    patient.visits.filter((v) => v.hasMri).at(-1) ||
    patient.visits[patient.visits.length - 1];
  const selectedIndex = patient.visits.findIndex((v) => v.id === visit.id);
  const result = analysis?.resultJson;
  const anatomy = anatomyAnalysis?.resultJson?.anatomy;
  const anatomyVisit = anatomy?.visits.find((v) => v.visitId === visit.id);
  const labelUrl =
    !alignment && regions && anatomyVisit && anatomyAnalysis
      ? `/api/analysis/${anatomyAnalysis.id}/visits/${visit.id}/anatomy/regions`
      : undefined;
  const effectiveFutureMonths = selectedFutureMonth ?? futureMonths;
  const intervalDays = FORECAST_DAYS[effectiveFutureMonths] ?? 365;
  const matches = useMemo(
    () =>
      (cached.data || []).filter((a) => {
        const candidate = a.resultJson?.anatomy;
        return (
          candidate?.forecast.status === "available" &&
          (candidate.forecast.cutoffVisitId === visit.id ||
            candidate.forecast.cutoffVisitId === cutoffVisit?.id) &&
          candidate.forecast.releaseSha256 === model.data?.releaseSha256 &&
          candidate.visits.every(
            (v, i) =>
              v.sourceSha256 === anatomy?.visits[i]?.sourceSha256 &&
              v.segmentationSha256 === anatomy?.visits[i]?.segmentationSha256 &&
              v.statisticsSha256 === anatomy?.visits[i]?.statisticsSha256 &&
              v.ratings.provenanceSha256 ===
                anatomy?.visits[i]?.ratings.provenanceSha256,
          )
        );
      }),
    [
      cached.data,
      visit.id,
      cutoffVisit?.id,
      model.data?.releaseSha256,
      anatomy,
    ],
  );
  const futureAnalysis = matches.find(
    (a) => a.resultJson?.anatomy?.forecast.intervalDays === intervalDays,
  );
  const future = futureAnalysis?.resultJson?.anatomy?.forecast;
  const meshInputs = useMemo(
    () =>
      future?.artifacts
        .filter(
          (a) =>
            a.kind === "mesh" &&
            (a.name === "brain_mesh" || a.name.includes("hippocampus")),
        )
        .map((a) => ({
          url: `/api/analysis/${futureAnalysis!.id}/future/${a.name}`,
          color: (a.name.includes("hippocampus")
            ? [255, 220, 65, 255]
            : [200, 200, 200, 255]) as [number, number, number, number],
          opacity: a.name === "brain_mesh" ? 0.15 : 0.7,
        })),
    [future, futureAnalysis],
  );
  useEffect(() => {
    setSelectedFutureMonth(null);
    setAlignment(false);
    setAnimating(false);
    setForecastError("");
  }, [visit.id]);
  useEffect(() => {
    if (!animating || !futureCompare || closed || matches.length < 2) return;
    const days = [
      ...new Set(
        matches.map((a) => a.resultJson!.anatomy!.forecast.intervalDays),
      ),
    ].sort((a, b) => a - b);
    const timer = setInterval(
      () =>
        setFutureMonths((previous) => {
          const current = FORECAST_DAYS[previous];
          const next = days[(days.indexOf(current) + 1) % days.length];
          return (
            [0, 6, 12, 24, 36].find((m) => FORECAST_DAYS[m] === next) ??
            previous
          );
        }),
      2000,
    );
    return () => clearInterval(timer);
  }, [animating, futureCompare, matches, closed]);
  const cutoffHistory =
    anatomy?.visits.filter(
      (v) => v.daysFromBaseline <= visit.daysFromBaseline,
    ) || [];
  const reviewedCutoff =
    cutoffHistory.length >= 2 &&
    !!anatomyVisit &&
    cutoffHistory.every((v) => v.qc === "passed" && v.ratings.status === "ok");
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
          {patient.visits.length > 0 && (
            <div
              className="volume-timeline"
              role="navigation"
              aria-label="Longitudinal MRI timeline"
            >
              <div className="timeline">
                {patient.visits.map((v, i) => (
                  <button
                    key={v.id}
                    type="button"
                    onClick={() => {
                      setSelectedFutureMonth(null);
                      setDifference(false);
                      onSelectVisit(v.id);
                    }}
                    className={`timeline-visit ${selectedFutureMonth === null && visit.id === v.id ? "selected" : ""}`}
                  >
                    <div className="timeline-track">
                      <span>{(i + 1).toString().padStart(2, "0")}</span>
                      <i />
                    </div>
                    <strong>{v.label}</strong>
                    <small>
                      Day {v.daysFromBaseline.toLocaleString()}{" "}
                      {i === 0 && "· Baseline"}
                    </small>
                    <span
                      className={`visit-ready ${v.hasMri ? "" : "missing"}`}
                    >
                      {v.hasMri ? "MRI available" : "Awaiting upload"}
                    </span>
                  </button>
                ))}
                {[12, 24, 36].map((months) => {
                  const mInterval = FORECAST_DAYS[months];
                  const projDays =
                    (cutoffVisit?.daysFromBaseline ?? 0) + mInterval;
                  const isSelected = selectedFutureMonth === months;
                  return (
                    <button
                      key={`future-${months}`}
                      type="button"
                      onClick={() => {
                        setSelectedFutureMonth(months);
                        setFutureMonths(months);
                        setDifference(false);
                      }}
                      className={`timeline-visit future ${isSelected ? "selected" : ""}`}
                    >
                      <div className="timeline-track">
                        <span>+{months}m</span>
                        <i />
                      </div>
                      <strong>+{months}m Predicted</strong>
                      <small>
                        Day {projDays.toLocaleString()} · from{" "}
                        {cutoffVisit?.label || "cutoff"}
                      </small>
                      <span className="visit-experimental">
                        Experimental (unsupported horizon)
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          <div className="volume-body">
            <div className="volume-main">
              <div
                className={`volume-viewers ${futureCompare || (compare && baseline && baseline.id !== visit.id) ? "volume-compare" : ""}`}
              >
                {selectedFutureMonth !== null && !futureCompare ? (
                  futureAnalysis && future ? (
                    <VolumeCanvas
                      key={`predicted:single:${cutoffVisit?.id || visit.id}:${intervalDays}:${future.modelSha256}`}
                      id="predicted"
                      kind="predicted"
                      label={`Predicted anatomy · ${selectedFutureMonth} months after cutoff (Experimental · unsupported horizon)`}
                      patientCode={patient.code}
                      url={`/api/analysis/${futureAnalysis.id}/future/mri`}
                      labelUrl={
                        regions
                          ? `/api/analysis/${futureAnalysis.id}/future/labels`
                          : undefined
                      }
                      meshes={meshInputs}
                      settings={settings}
                      onReady={onReady}
                    />
                  ) : (
                    <div className="volume-card" role="status">
                      <div className="volume-card-heading">
                        <strong>
                          Predicted anatomy · {selectedFutureMonth} months after
                          cutoff
                        </strong>
                        <span className="visit-experimental">
                          Experimental (unsupported horizon)
                        </span>
                      </div>
                      <div className="empty">
                        <h3>Future anatomy unavailable</h3>
                        <p>
                          No matching evaluated prediction is available for this
                          cutoff and interval. No acquired scan, crossfade or
                          uniformly shrunken mesh is substituted.
                        </p>
                        <p>
                          Requested interval: {intervalDays} days. All future
                          artifacts remain unavailable.
                        </p>
                      </div>
                    </div>
                  )
                ) : (
                  <>
                    {compare && baseline && baseline.id !== visit.id && (
                      <VolumeCanvas
                        key={`baseline:${baseline.id}`}
                        id="baseline"
                        label={`Baseline · ${baseline.label}`}
                        patientCode={patient.code}
                        url={
                          baseline.volumeUrl ||
                          `/api/visits/${baseline.id}/volume`
                        }
                        settings={settings}
                        onReady={onReady}
                      />
                    )}
                    <VolumeCanvas
                      key={`${visit.id}:${overlayUrl || "original"}`}
                      id="selected"
                      label={
                        alignment
                          ? "Automatic rating alignment · inspect three planes"
                          : `Selected · ${visit.label}`
                      }
                      patientCode={patient.code}
                      url={
                        alignment
                          ? `/api/analysis/${anatomyAnalysis!.id}/visits/${visit.id}/rating-alignment`
                          : visit.volumeUrl || `/api/visits/${visit.id}/volume`
                      }
                      overlayUrl={alignment ? undefined : overlayUrl}
                      labelUrl={labelUrl}
                      settings={settings}
                      onReady={onReady}
                      onLocation={onLocation}
                    />
                    {futureCompare && futureAnalysis && future ? (
                      <VolumeCanvas
                        key={`predicted:${visit.id}:${intervalDays}:${future.modelSha256}`}
                        id="predicted"
                        kind="predicted"
                        label={`Predicted anatomy · ${futureMonths} months after cutoff (Experimental · unsupported horizon)`}
                        patientCode={patient.code}
                        url={`/api/analysis/${futureAnalysis.id}/future/mri`}
                        labelUrl={
                          regions
                            ? `/api/analysis/${futureAnalysis.id}/future/labels`
                            : undefined
                        }
                        meshes={meshes ? meshInputs : undefined}
                        settings={settings}
                        onReady={onReady}
                      />
                    ) : (
                      futureCompare && (
                        <div className="volume-card" role="status">
                          <div className="volume-card-heading">
                            <strong>
                              Predicted anatomy · {futureMonths} months after
                              latest input
                            </strong>
                            <span className="visit-experimental">
                              Experimental (unsupported horizon)
                            </span>
                          </div>
                          <div className="empty">
                            <h3>Future anatomy unavailable</h3>
                            <p>
                              No matching evaluated prediction is available for
                              this cutoff and interval. No acquired scan,
                              crossfade or uniformly shrunken mesh is
                              substituted.
                            </p>
                            <p>
                              Requested interval: {intervalDays} days. All
                              future artifacts remain unavailable.
                            </p>
                          </div>
                        </div>
                      )
                    )}
                  </>
                )}
              </div>
              <div className="volume-navigation">
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={
                    selectedFutureMonth === null ? selectedIndex <= 0 : false
                  }
                  onClick={() => {
                    setDifference(false);
                    if (selectedFutureMonth === null) {
                      if (selectedIndex > 0) {
                        onSelectVisit(patient.visits[selectedIndex - 1].id);
                      }
                    } else if (selectedFutureMonth === 12) {
                      setSelectedFutureMonth(null);
                      if (cutoffVisit) onSelectVisit(cutoffVisit.id);
                    } else if (selectedFutureMonth === 24) {
                      setSelectedFutureMonth(12);
                      setFutureMonths(12);
                    } else if (selectedFutureMonth === 36) {
                      setSelectedFutureMonth(24);
                      setFutureMonths(24);
                    }
                  }}
                >
                  <ChevronLeft size={15} />
                  Earlier MRI
                </Button>
                <span>
                  {selectedFutureMonth === null
                    ? `Day ${visit.daysFromBaseline.toLocaleString()} · ${selectedIndex + 1} / ${patient.visits.length}`
                    : `Day ${((cutoffVisit?.daysFromBaseline ?? 0) + intervalDays).toLocaleString()} · +${selectedFutureMonth}m Predicted · Experimental`}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={selectedFutureMonth === 36}
                  onClick={() => {
                    setDifference(false);
                    if (selectedFutureMonth === null) {
                      if (selectedIndex < patient.visits.length - 1) {
                        onSelectVisit(patient.visits[selectedIndex + 1].id);
                      } else {
                        setSelectedFutureMonth(12);
                        setFutureMonths(12);
                      }
                    } else if (selectedFutureMonth === 12) {
                      setSelectedFutureMonth(24);
                      setFutureMonths(24);
                    } else if (selectedFutureMonth === 24) {
                      setSelectedFutureMonth(36);
                      setFutureMonths(36);
                    }
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
              {anatomyAnalysis && (
                <>
                  <label className="volume-check">
                    <input
                      type="checkbox"
                      checked={regions}
                      disabled={!anatomyVisit}
                      onChange={(e) => setRegions(e.target.checked)}
                    />
                    Hippocampus highlight
                  </label>
                  <small className="volume-note">
                    Hippocampus yellow. QC: {anatomyVisit?.qc ?? "unavailable"};
                    nearest-neighbour label rendering.
                  </small>
                </>
              )}
              <label className="volume-check">
                <input
                  type="checkbox"
                  checked={futureCompare}
                  onChange={(e) => {
                    setFutureCompare(e.target.checked);
                    setAlignment(false);
                    if (e.target.checked) setCompare(false);
                  }}
                />
                Compare current vs predicted
              </label>
              {futureCompare && (
                <>
                  <label>
                    Future time after latest scan
                    <select
                      aria-label="Future time after latest scan"
                      value={futureMonths}
                      onChange={(e) => {
                        setAnimating(false);
                        setFutureMonths(Number(e.target.value));
                      }}
                    >
                      {[0, 6, 12, 24, 36].map((m) => (
                        <option key={m} value={m}>
                          {m} months
                        </option>
                      ))}
                    </select>
                  </label>
                  <Button
                    variant="outline"
                    disabled={
                      forecastBusy ||
                      patient.latestAnatomy?.status === "queued" ||
                      patient.latestAnatomy?.status === "processing" ||
                      !anatomyAnalysis ||
                      !reviewedCutoff ||
                      model.data?.status !== "available" ||
                      !model.data.intervalsDays.includes(intervalDays) ||
                      !!future
                    }
                    onClick={async () => {
                      setForecastBusy(true);
                      setForecastError("");
                      try {
                        await post(
                          `/analysis/${anatomyAnalysis!.id}/forecast`,
                          { intervalDays, cutoffVisitId: visit.id },
                        );
                        reload?.();
                      } catch (e) {
                        setForecastError((e as Error).message);
                      } finally {
                        setForecastBusy(false);
                      }
                    }}
                  >
                    {forecastBusy
                      ? "Queuing prediction…"
                      : "Generate evaluated future anatomy"}
                  </Button>
                  <p className="volume-note">
                    {model.data?.reason ||
                      `Cutoff ${visit.label}; model ${future?.spatialModelVersion || "not yet generated"}. Unsupported times stay unavailable.`}
                  </p>
                  {forecastError && <p role="alert">{forecastError}</p>}
                  <label className="volume-check">
                    <input
                      type="checkbox"
                      checked={meshes}
                      onChange={(e) => setMeshes(e.target.checked)}
                    />
                    Predicted brain and hippocampus boundaries
                  </label>
                  <Button
                    variant="outline"
                    disabled={matches.length < 2}
                    onClick={() => setAnimating((v) => !v)}
                  >
                    {animating
                      ? "Pause forecast timeline"
                      : "Play generated forecast timeline"}
                  </Button>
                  <small>
                    Discrete model-generated intervals only; no crossfade or
                    mesh scaling.
                  </small>
                </>
              )}
              {anatomyVisit &&
                ["pending_alignment_qc", "ok"].includes(
                  anatomyVisit.ratings.status,
                ) && (
                  <label className="volume-check">
                    <input
                      type="checkbox"
                      checked={alignment}
                      onChange={(e) => {
                        setAlignment(e.target.checked);
                        setFutureCompare(false);
                        setCompare(false);
                        setDifference(false);
                        if (e.target.checked) update("layout", "multiplanar");
                      }}
                    />
                    Inspect automatic rating alignment
                  </label>
                )}
              <label className="volume-check">
                <input
                  type="checkbox"
                  checked={compare}
                  disabled={!baseline || baseline.id === visit.id}
                  onChange={(e) => {
                    setCompare(e.target.checked);
                    if (e.target.checked) setFutureCompare(false);
                  }}
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
            <strong>
              Observed MRI research visualization
              {labelUrl
                ? " with yellow hippocampus highlighting"
                : ", not segmented anatomy (no segmentation layer selected)"}
              .
            </strong>{" "}
            MRI includes non-brain head tissue. Linked views are not registered.
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
