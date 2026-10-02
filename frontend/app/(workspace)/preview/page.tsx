"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { useResource } from "@/lib/use-resource";
import { VolumeCanvas, type VolumeSettings } from "@/components/volume-canvas";
import { Button } from "@/components/ui/button";

type Preview = {
  status: string;
  reason?: string;
  subjectCode: string;
  patientId: string;
  cutoffVisitId: string;
  cutoffDay: number;
  observedLabelsUrl?: string | null;
  intervalDays: number;
  modelVersion: string;
  modelSha256: string;
  evaluationStatus: string;
  studySubjectCount: number;
  gradientTrainingSubjectCount: number;
  trainingExampleCount?: number;
  trainingEpochs: number;
  warnings: string[];
};

const PREVIEW_INTERVALS = [
  { days: 229, label: "+229 days · held-out example" },
  { days: 365, label: "12 months · 365 days" },
  { days: 731, label: "24 months · 731 days" },
  { days: 1096, label: "36 months · 1,096 days" },
];

export default function AnatomyPreviewPage() {
  const [intervalDays, setIntervalDays] = useState(365);
  const preview = useResource<Preview>(
    `/anatomy-preview?intervalDays=${intervalDays}`,
  );
  const [regions, setRegions] = useState(true);
  const [settings, setSettings] = useState<VolumeSettings>({
    layout: "multiplanar",
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
  });
  const onReady = useCallback(() => {}, []);
  const data = preview.data;
  return (
    <section
      className="panel volume-explorer"
      aria-label="Saved experimental anatomy preview"
    >
      <div className="panel-heading">
        <div>
          <div className="eyebrow">EXPERIMENTAL VISUAL PREVIEW</div>
          <h1>Saved future anatomy examples</h1>
          <p>Small-cohort model · Unvalidated research prototype</p>
        </div>
        <span className="badge">Not a medical diagnosis</span>
      </div>
      {preview.loading ? (
        <p role="status">Checking the saved preview…</p>
      ) : preview.error || data?.status !== "available" ? (
        <div className="empty" role="status">
          <h2>Saved preview unavailable</h2>
          <p>{preview.error || data?.reason}</p>
          <Button onClick={() => void preview.reload()}>Retry</Button>
        </div>
      ) : (
        <>
          <p className="volume-help">
            Example subject <strong>{data.subjectCode}</strong> · Input cutoff
            day {data.cutoffDay} · Generated interval{" "}
            <strong>+{data.intervalDays} days</strong> · saved prototype output.
            This six-subject research candidate is unvalidated and was not
            promoted for patient forecasting.
          </p>
          <div className="volume-toolbar">
            <p className="volume-note">
              Select a pre-generated interval below. The 365-, 731- and
              1,096-day outputs are model extrapolations from the same four-scan
              cutoff history; no matching acquired scan exists at those exact
              horizons. They are for prototype demonstration only.
            </p>
            <p className="volume-note">
              For another patient, open their MRI workspace, enable Experimental
              forecasts (small-cohort model), select a future time and generate
              a forecast. At least two prepared scans are required.{" "}
              <Link href="/patients">Open patient directory</Link>.
            </p>
            <div
              className="volume-layouts"
              role="group"
              aria-label="Generated forecast interval"
            >
              {PREVIEW_INTERVALS.map((item) => (
                <button
                  key={item.days}
                  className={intervalDays === item.days ? "selected" : ""}
                  aria-pressed={intervalDays === item.days}
                  onClick={() => setIntervalDays(item.days)}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <div
              className="volume-layouts"
              role="group"
              aria-label="Preview display layout"
            >
              {(["multiplanar", "render"] as const).map((layout) => (
                <button
                  key={layout}
                  aria-pressed={settings.layout === layout}
                  onClick={() => setSettings((s) => ({ ...s, layout }))}
                >
                  {layout === "multiplanar" ? "Slices + 3D" : "3D volume"}
                </button>
              ))}
            </div>
            <label className="volume-check">
              <input
                type="checkbox"
                checked={regions}
                onChange={(e) => setRegions(e.target.checked)}
              />
              Hippocampus highlight
            </label>
            <Link href={`/patients/${data.patientId}`}>
              Open example patient
            </Link>
          </div>
          {regions && !data.observedLabelsUrl && (
            <p role="status">
              Measured hippocampus labels unavailable for the acquired MRI.
            </p>
          )}
          <div className="volume-viewers volume-compare">
            <VolumeCanvas
              key={`observed-${data.cutoffVisitId}`}
              id="preview-observed"
              kind="observed"
              patientCode={data.subjectCode}
              label={`Acquired MRI · cutoff day ${data.cutoffDay}`}
              url={`/api/visits/${data.cutoffVisitId}/volume`}
              labelUrl={
                regions ? data.observedLabelsUrl || undefined : undefined
              }
              settings={settings}
              onReady={onReady}
            />
            <VolumeCanvas
              key={`predicted-${data.intervalDays}-${data.modelSha256}`}
              id="preview-predicted"
              kind="predicted"
              patientCode={data.subjectCode}
              label={`Experimental model output · +${data.intervalDays} days · not validated`}
              url={`/api/anatomy-preview/mri?intervalDays=${data.intervalDays}`}
              labelUrl={
                regions
                  ? `/api/anatomy-preview/labels?intervalDays=${data.intervalDays}`
                  : undefined
              }
              meshes={
                regions
                  ? ["hippocampus_left_mm3", "hippocampus_right_mm3"].map(
                      (name) => ({
                        url: `/api/anatomy-preview/${name}?intervalDays=${data.intervalDays}`,
                        color: [255, 220, 65, 255] as [
                          number,
                          number,
                          number,
                          number,
                        ],
                        opacity: 0.7,
                      }),
                    )
                  : undefined
              }
              settings={settings}
              onReady={onReady}
            />
          </div>
          <details className="volume-help">
            <summary>Model provenance and release limitations</summary>
            <p>
              {data.modelVersion} · Model fingerprint {data.modelSha256}
            </p>
            <p>
              Training run: {data.studySubjectCount} subjects total (
              {data.gradientTrainingSubjectCount} assigned to gradient
              training), {data.trainingExampleCount ?? "recorded"} longitudinal
              examples, {data.trainingEpochs} epochs. Requested-interval status:{" "}
              {data.evaluationStatus.replace(/_/g, " ")}.
            </p>
            <ul>
              {data.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </section>
  );
}
