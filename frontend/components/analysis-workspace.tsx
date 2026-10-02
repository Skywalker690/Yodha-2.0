"use client";
import { useState, type ReactNode } from "react";
import { ClinicalAssistant } from "@/components/clinical-assistant";
import {
  ArrowLeft,
  ArrowRight,
  Download,
  Layers,
  Play,
  Plus,
  ScanLine,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { api, post } from "@/lib/api";
import type { MriAcquisition } from "@/lib/mri-upload";
import { percent } from "@/lib/utils";
import type { Analysis, Mode, Patient, Report, Visit } from "@/types";
import { Button } from "./ui/button";
import { Empty, ErrorState, ModeBadge } from "./common";
import { TrajectoryChart } from "./trajectory-chart";
import { VolumeExplorer } from "./volume-explorer";
import { BaselineForecast } from "./baseline-forecast";
import { AnatomyPanel } from "./anatomy-panel";
import { MriMetadataFields } from "./mri-metadata-fields";
import { MriFilePicker } from "./mri-file-picker";

function VisitForm({
  patient,
  onDone,
}: {
  patient: Patient;
  onDone: (visitId?: string) => void;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <form
      className="visit-form"
      onSubmit={async (e) => {
        e.preventDefault();
        setError("");
        setBusy(true);
        const fd = new FormData(e.currentTarget);
        try {
          const updated = await post<Patient>(
            `/patients/${patient.id}/visits`,
            {
              label: fd.get("label"),
              daysFromBaseline: Number(fd.get("day")),
            },
          );
          onDone(
            updated.visits.find(
              (v) => !patient.visits.some((old) => old.id === v.id),
            )?.id,
          );
        } catch (e) {
          setError((e as Error).message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <div className="form-grid">
        <label>
          Visit label
          <input
            name="label"
            defaultValue={`Visit ${patient.visitCount + 1}`}
            required
            maxLength={64}
          />
        </label>
        <label>
          Days from baseline
          <input
            name="day"
            type="number"
            min={0}
            max={36500}
            defaultValue={
              patient.visitCount
                ? patient.visits[patient.visitCount - 1].daysFromBaseline + 365
                : 0
            }
            required
          />
        </label>
        <Button disabled={busy}>{busy ? "Saving…" : "Save visit"}</Button>
      </div>
      {error && <ErrorState message={error} />}
    </form>
  );
}

function UploadForm({
  visit,
  onDone,
  onDeleted,
  visitSelector,
  mlOnly = false,
}: {
  visit: Visit;
  onDone: () => void;
  onDeleted?: () => void;
  visitSelector?: ReactNode;
  mlOnly?: boolean;
}) {
  const [selection, setSelection] = useState<MriAcquisition | null>(null);
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");
  return (
    <>
      <div className="panel-heading">
        {visitSelector}
        {!visit.hasMri && (
          <Button
            type="button"
            variant="outline"
            disabled={busy}
            onClick={async () => {
              if (busy) return;
              setBusy(true);
              setDeleting(true);
              setError("");
              try {
                await api(`/visits/${visit.id}`, { method: "DELETE" });
                (onDeleted || onDone)();
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
                setDeleting(false);
              }
            }}
          >
            <Trash2 size={16} />
            {deleting ? "Deleting…" : "Delete visit"}
          </Button>
        )}
      </div>
      {error && <ErrorState message={error} />}
      <form
        className="upload-form"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!selection || busy) return;
          setBusy(true);
          setError("");
          const fd = new FormData(e.currentTarget);
          if (selection.kind === "volume") {
            fd.append("file", selection.file);
          } else {
            fd.append("header", selection.header);
            fd.append("image", selection.image);
          }
          try {
            await api<Analysis>(`/visits/${visit.id}/upload`, {
              method: "POST",
              body: fd,
            });
            onDone();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <Upload size={28} />
        <h3>Add the MRI for {visit.label}</h3>
        <p>
          NIfTI volume (.nii/.nii.gz) or a matching .hdr/.img pair, up to 100
          MiB per acquisition.
          <br />
          {mlOnly
            ? "Stored after validation; reviewed FastSurfer processing and trained model release are required before prediction."
            : "A local analysis job starts after validation."}
        </p>
        <MriMetadataFields
          age={visit.metadata.Age}
          nwbv={visit.metadata.nWBV}
          disabled={busy}
        />
        <MriFilePicker
          disabled={busy}
          onSelection={(selected) => {
            setSelection(selected);
            setError("");
          }}
        />
        <Button type="submit" disabled={!selection || busy}>
          {busy && !deleting ? "Uploading and validating…" : "Upload MRI"}
        </Button>
      </form>
    </>
  );
}

function LegacyAnalysisWorkspace({
  patient,
  reload,
}: {
  patient: Patient;
  reload: () => void;
}) {
  const [selectedId, setSelectedId] = useState("");
  const [overlay, setOverlay] = useState(false);
  const [addVisit, setAddVisit] = useState(false);
  const [mode, setMode] = useState<Mode>("trained");
  const [busy, setBusy] = useState(false);
  const [reportBusy, setReportBusy] = useState(false);
  const [error, setError] = useState("");
  const [imageError, setImageError] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const visits = patient.visits;
  const visit =
    visits.find((v) => v.id === selectedId) || visits[visits.length - 1];
  const selectedIndex = visits.findIndex((v) => v.id === visit?.id);
  const analysis = patient.latestCompleted;
  const result = analysis?.resultJson;
  const resultIndex = result?.visitIds.indexOf(visit?.id) ?? -1;
  const trainedResult = result?.outputMode === "trained";
  const showTrainedHeading = trainedResult || (!result && mode === "trained");
  const baselineScores =
    result &&
    !trainedResult &&
    result.visitIds.length > 0 &&
    result.riskScores.length === result.visitIds.length
      ? result.riskScores
      : null;
  const firstScore = baselineScores?.[0];
  const lastScore = baselineScores?.at(-1);
  const baselineChange =
    typeof firstScore === "number" &&
    typeof lastScore === "number" &&
    Number.isFinite(firstScore) &&
    Number.isFinite(lastScore)
      ? ((lastScore - firstScore) * 100).toFixed(1)
      : null;
  const inputMriCount = visits.filter(
    (v) => v.hasMri && v.daysFromBaseline <= (visit?.daysFromBaseline ?? -1),
  ).length;
  const needsMoreVisits = mode === "trained" && inputMriCount < 3;
  const job = patient.latestAnalysis;
  const running = !!job && ["queued", "processing"].includes(job.status);
  const selectVisit = (id: string) => {
    setSelectedId(id);
    setImageError("");
    setOverlay(false);
  };
  const imageUrl =
    overlay && analysis && resultIndex >= 0
      ? `/api/analysis/${analysis.id}/visits/${visit.id}/overlay`
      : visit?.previewUrl;
  return (
    <>
      <div className="patient-summary">
        <div className="summary-avatar">
          <ScanLine size={26} />
        </div>
        <div>
          <h2>{patient.code}</h2>
          <p>
            {patient.age ? `${patient.age} years` : "Age unspecified"} <b>·</b>{" "}
            {patient.sex || "Sex unspecified"} <b>·</b> {visits.length} research
            visits
          </p>
        </div>
        <div className="summary-badges">
          <span className="badge">
            {patient.source === "oasis-2" ? "OASIS-2 cohort" : "Research case"}
          </span>
          {analysis && <ModeBadge mode={analysis.outputMode} />}
        </div>
        <Button variant="outline" onClick={() => setAddVisit(!addVisit)}>
          {addVisit ? <X size={16} /> : <Plus size={16} />} Add visit
        </Button>
      </div>
      {patient.notes && <p className="patient-notes">{patient.notes}</p>}
      {patient.source === "oasis-2" && (
        <BaselineForecast key={patient.id} patientId={patient.id} research />
      )}
      {visit && (
        <AnatomyPanel
          key={`${patient.id}:${visit.id}:${patient.completedAnatomy?.id}`}
          patient={patient}
          visit={visit}
          reload={reload}
        />
      )}
      {addVisit && (
        <section className="panel form-panel">
          <h3>Add a chronological visit</h3>
          <VisitForm
            patient={patient}
            onDone={(visitId) => {
              if (visitId) selectVisit(visitId);
              setAddVisit(false);
              reload();
            }}
          />
        </section>
      )}
      <section className="panel timeline-panel">
        <div className="panel-heading">
          <div>
            <h2>MRI timeline</h2>
            <p>Select an observation to explore its place in the sequence</p>
          </div>
          <span className="muted small">DAYS FROM BASELINE</span>
        </div>
        <div className="timeline">
          {visits.length ? (
            visits.map((v, i) => (
              <button
                key={v.id}
                onClick={() => selectVisit(v.id)}
                className={`timeline-visit ${visit.id === v.id ? "selected" : ""}`}
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
                <span className={`visit-ready ${v.hasMri ? "" : "missing"}`}>
                  {v.hasMri ? "MRI available" : "Awaiting upload"}
                </span>
              </button>
            ))
          ) : (
            <Empty title="Begin the timeline">
              Add the baseline visit to start organizing this case.
            </Empty>
          )}
        </div>
      </section>
      {error && <ErrorState message={error} />}
      {job?.status === "failed" && (
        <ErrorState
          message={
            job.error || "Analysis failed. You can start a new analysis."
          }
        />
      )}
      {running && (
        <div className="job-progress" role="status">
          <div>
            <span className="pulse-dot" />
            <strong>
              {job.status === "queued"
                ? "Analysis queued"
                : "Analyzing MRI sequence"}
            </strong>
            <span>{job.stage}</span>
            <b>{job.progress}%</b>
          </div>
          <progress value={job.progress} max={100} />
          <small>
            You can continue browsing. Results are saved by the local worker.
          </small>
        </div>
      )}
      {visit?.hasMri && (
        <VolumeExplorer
          key={patient.id}
          patient={patient}
          visit={visit}
          analysis={analysis}
          anatomyAnalysis={patient.completedAnatomy ?? null}
          reload={reload}
          onSelectVisit={selectVisit}
        />
      )}
      <div className="analysis-grid">
        <section className="panel viewer-panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">MRI REVIEW</div>
              <h2>{visit?.label || "Scan workspace"}</h2>
            </div>
            <span className="badge">Axial · Center slice</span>
          </div>
          {visit?.hasMri ? (
            <>
              <div className="viewer-tabs">
                <button
                  className={!overlay ? "selected" : ""}
                  onClick={() => {
                    setOverlay(false);
                    setImageError("");
                  }}
                >
                  <ScanLine size={15} /> Original MRI
                </button>
                <button
                  className={overlay ? "selected" : ""}
                  onClick={() => {
                    setOverlay(true);
                    setImageError("");
                  }}
                  disabled={resultIndex < 0}
                >
                  <Layers size={15} /> Difference overlay
                </button>
              </div>
              <div className="mri-stage">
                <span className="orientation top">A</span>
                <span className="orientation left">L</span>
                <span className="orientation right">R</span>
                <span className="orientation bottom">P</span>
                {imageUrl && !imageError ? (
                  <img
                    key={imageUrl}
                    src={imageUrl}
                    alt={`${overlay ? "Research intensity-difference overlay" : "Axial MRI"} for ${patient.code}, ${visit.label}`}
                    onError={() =>
                      setImageError(
                        "Image unavailable. Select another visit or run analysis again.",
                      )
                    }
                  />
                ) : (
                  <Empty title="Image unavailable">
                    {imageError || "No image was generated for this visit."}
                  </Empty>
                )}
                <span className="image-corner">
                  {overlay ? "RESEARCH VISUALIZATION" : "CANONICAL ORIENTATION"}
                </span>
              </div>
              <div className="viewer-footer">
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={selectedIndex <= 0}
                  onClick={() => selectVisit(visits[selectedIndex - 1].id)}
                >
                  <ArrowLeft size={15} /> Previous
                </Button>
                <span>
                  {selectedIndex + 1} of {visits.length} visits
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={selectedIndex >= visits.length - 1}
                  onClick={() => selectVisit(visits[selectedIndex + 1].id)}
                >
                  Next <ArrowRight size={15} />
                </Button>
              </div>
              <p className="viewer-caption">
                {overlay
                  ? "Absolute intensity difference versus baseline. Not anatomically registered; not Grad-CAM. Baseline overlay has no differences by definition."
                  : "Research slice preview. Scans are reoriented for display; acquisition and alignment differences may remain."}
                {trainedResult &&
                  " Image differences are not attribution for the trained model."}
              </p>
            </>
          ) : visit ? (
            <UploadForm
              key={visit.id}
              visit={visit}
              onDone={reload}
              onDeleted={() => {
                selectVisit("");
                reload();
              }}
            />
          ) : (
            <Empty title="No MRI visits">
              Add a visit above, then upload a NIfTI scan.
            </Empty>
          )}
        </section>
        <div className="analysis-right">
          <section className="panel">
            <div className="panel-heading">
              <div>
                <div className="eyebrow">
                  {showTrainedHeading ? "RETROSPECTIVE MODEL" : "ACROSS TIME"}
                </div>
                <h2>
                  {showTrainedHeading
                    ? "Experimental sequence classification"
                    : "Progression-risk estimate"}
                </h2>
              </div>
              {!trainedResult &&
                resultIndex >= 0 &&
                result &&
                Number.isFinite(result.riskScores[resultIndex]) && (
                  <strong className="current-risk">
                    {percent(result.riskScores[resultIndex])}
                  </strong>
                )}
            </div>
            {result ? (
              <TrajectoryChart result={result} />
            ) : (
              <Empty title="Ready when your scans are">
                {mode === "trained"
                  ? "Start trained analysis for an experimental observed-CDR-increase classification. At least three MRI visits and recorded covariates are required."
                  : "Start an analysis to see the research trajectory."}
              </Empty>
            )}
          </section>
          <section className="panel metrics-panel">
            <div className="panel-heading">
              <div>
                <h2>Structural research metrics</h2>
                <p>
                  Selected visit · Change relative to earliest included scan
                  {trainedResult &&
                    " · Image proxies, not trained-model attribution"}
                </p>
              </div>
            </div>
            <div className="biomarker-grid">
              <div>
                <span>Foreground fraction</span>
                <strong>
                  {result && resultIndex >= 0
                    ? percent(result.biomarkers.foregroundFraction[resultIndex])
                    : "—"}
                </strong>
                <small>Intensity threshold proxy; not brain volume</small>
              </div>
              <div>
                <span>Pooled feature change</span>
                <strong>
                  {result && resultIndex >= 0
                    ? result.biomarkers.featureChange[resultIndex].toFixed(4)
                    : "—"}
                </strong>
                <small>Mean absolute difference from baseline</small>
              </div>
              <div>
                <span>Observed nWBV</span>
                <strong>{visit?.metadata.nWBV?.toFixed(4) || "—"}</strong>
                <small>OASIS demographics · Not inferred</small>
              </div>
              <div>
                <span>Observed eTIV</span>
                <strong>
                  {visit?.metadata.eTIV
                    ? `${Math.round(visit.metadata.eTIV).toLocaleString()} mL`
                    : "—"}
                </strong>
                <small>OASIS demographics · Not inferred</small>
              </div>
            </div>
            {!trainedResult && analysis?.confidence != null && (
              <p>Model confidence: {percent(analysis.confidence)}</p>
            )}
          </section>
        </div>
      </div>
      <section className="analysis-actions panel">
        <div>
          <h3>Analyze this sequence</h3>
          <p>
            Includes available visits up to{" "}
            {visit?.label || "the selected scan"}.
          </p>
          {mode === "trained" && (
            <p id="trained-mode-requirements">
              Experimental retrospective classification with poor
              generalization, not future Alzheimer&apos;s probability. Requires
              at least three chronological MRI visits and recorded
              demographic/visit covariates; unavailable trained inference fails
              explicitly, without baseline fallback.
              {needsMoreVisits &&
                ` Only ${inputMriCount} MRI visits are included at this selection.`}
            </p>
          )}
        </div>
        <label className="mode-select">
          <span>Analysis mode</span>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as Mode)}
          >
            <option value="trained">
              Trained · experimental observed CDR increase
            </option>
            <option value="inference">
              Local inference · feature-delta baseline
            </option>
            <option value="precomputed">
              Precomputed · matching cached result
            </option>
            <option value="demo">Demo · illustrative risk scores</option>
          </select>
        </label>
        <Button
          disabled={!visit?.hasMri || busy || running || needsMoreVisits}
          aria-describedby={
            mode === "trained" ? "trained-mode-requirements" : undefined
          }
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              await post(`/analysis/${visit.id}`, { outputMode: mode });
              reload();
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <Play size={16} />
          {busy ? "Starting…" : "Analyze MRI"}
        </Button>
      </section>
      {result && (
        <section className="panel insight-panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">RESEARCH INTERPRETATION</div>
              <h2>
                {trainedResult
                  ? "Retrospective model interpretation"
                  : "The longitudinal view"}
              </h2>
            </div>
            <ModeBadge mode={result.outputMode} />
          </div>
          <p className="insight-lead">
            {trainedResult ? (
              <>
                The model classifies observed first-to-last CDR increase using
                all {result.visitIds.length} visits in this completed sequence.
                Changing the selected MRI only changes the image and structural
                metrics shown, not the sequence classification. This is not
                future Alzheimer&apos;s forecasting or a medical diagnosis.
              </>
            ) : baselineChange !== null ? (
              <>
                Across {result.visitIds.length} visits, the index changed by{" "}
                {baselineChange} percentage points from baseline.
                {result.outputMode === "demo"
                  ? " These illustrative values are not computed predictions or accuracy evidence."
                  : " This describes structural image differences and does not establish disease progression."}
              </>
            ) : (
              "Per-visit index change is unavailable. Run analysis again; no values have been inferred."
            )}
          </p>
          <details>
            <summary>Methods, provenance & limitations</summary>
            <ul>
              {result.caveats.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
            <p>
              Model: {result.modelVersion}. Analysis {analysis?.id.slice(0, 8)}.{" "}
              {visits.length !== result.visitIds.length &&
                "This result covers a subset of the current patient visits."}
            </p>
          </details>
          <div className="report-row">
            <span>
              Qualified review and independent validation are required.
            </span>
            <Button
              variant="outline"
              disabled={reportBusy}
              onClick={async () => {
                setReportBusy(true);
                setError("");
                try {
                  const r = await post<Report>(`/reports/${patient.id}`);
                  setReport(r);
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setReportBusy(false);
                }
              }}
            >
              <Download size={16} />
              {reportBusy ? "Generating…" : "Generate research report"}
            </Button>
            {report && (
              <a href={report.downloadUrl} className="text-link" download>
                Download PDF <ArrowRight size={15} />
              </a>
            )}
          </div>
        </section>
      )}
    </>
  );
}

function MLWorkspace({
  patient,
  reload,
}: {
  patient: Patient;
  reload: () => void;
}) {
  const [selectedId, setSelectedId] = useState("");
  const [addVisit, setAddVisit] = useState(false);
  const visit =
    patient.visits.find((v) => v.id === selectedId) || patient.visits[0];
  const visitSelector = visit && (
    <label style={{ flex: 1, minWidth: 0 }}>
      MRI visit
      <select value={visit.id} onChange={(e) => setSelectedId(e.target.value)}>
        {patient.visits.map((item) => (
          <option key={item.id} value={item.id}>
            {item.label}
          </option>
        ))}
      </select>
    </label>
  );
  return (
    <>
      <section className="panel" style={{ padding: "1.5rem" }}>
        <h2>{patient.code}</h2>
        <p>
          ML-only research serving. Historical predictions remain archived, not
          reused as current forecasts. This is not clinical-production approval.
        </p>
        <Button variant="outline" onClick={() => setAddVisit(!addVisit)}>
          Add visit
        </Button>
        {addVisit && (
          <VisitForm
            patient={patient}
            onDone={(visitId) => {
              if (visitId) setSelectedId(visitId);
              setAddVisit(false);
              reload();
            }}
          />
        )}
      </section>
      {visit && (
        <AnatomyPanel
          key={`${patient.id}:${visit.id}:${patient.completedAnatomy?.id}`}
          patient={patient}
          visit={visit}
          reload={reload}
        />
      )}
      {visit ? (
        <section className="panel" style={{ padding: "1.5rem" }}>
          {visit.hasMri && visitSelector}
          <p>
            Follow-up MRI viewing does not change the baseline prediction or add
            future inputs.
          </p>
          {visit.hasMri ? (
            <>
              <VolumeExplorer
                key={patient.id}
                patient={patient}
                visit={visit}
                analysis={null}
                anatomyAnalysis={patient.completedAnatomy ?? null}
                reload={reload}
                onSelectVisit={setSelectedId}
              />
              {visit.previewUrl && (
                <img
                  src={visit.previewUrl}
                  alt={`Original MRI preview for ${visit.label}`}
                  style={{ maxWidth: "100%" }}
                />
              )}
            </>
          ) : (
            <UploadForm
              key={visit.id}
              visit={visit}
              visitSelector={visitSelector}
              onDone={reload}
              onDeleted={() => {
                setSelectedId("");
                reload();
              }}
              mlOnly
            />
          )}
        </section>
      ) : (
        <Empty title="No MRI visits">
          Add a visit to store an MRI. Prediction requires verified baseline
          metadata, reviewed anatomy and a promoted model.
        </Empty>
      )}
    </>
  );
}

export function AnalysisWorkspace(props: {
  patient: Patient;
  reload: () => void;
}) {
  return (
    <>
      <ClinicalAssistant patient={props.patient} />
      {props.patient.servingPolicy === "research" ? (
        <LegacyAnalysisWorkspace {...props} />
      ) : (
        <MLWorkspace {...props} />
      )}
    </>
  );
}
