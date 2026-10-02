"use client";
import { useState } from "react";
import { Play, Download } from "lucide-react";
import {
  Line,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { Analysis, Patient, Report, Visit } from "@/types";
import { post } from "@/lib/api";
import { Button } from "./ui/button";
import { ErrorState } from "./common";

const regionLabel = (name: string) =>
  name
    .replace(/(?:_mm3|Mm3)$/, "")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replaceAll("_", " ")
    .toLowerCase();

export function AnatomyPanel({
  patient,
  visit,
  reload,
}: {
  patient: Patient;
  visit: Visit;
  reload: () => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [reviewConfirmed, setReviewConfirmed] = useState(false);
  const job = patient.latestAnatomy;
  const anatomy = patient.completedAnatomy?.resultJson?.anatomy;
  const selected = anatomy?.visits.find((v) => v.visitId === visit.id);
  const active = job?.status === "queued" || job?.status === "processing";
  const included = patient.visits.filter(
    (v) => v.daysFromBaseline <= visit.daysFromBaseline,
  );
  const eligible = included.length <= 5 && included.every((v) => v.hasMri);
  const ratings = selected?.ratings;
  const includedIds = new Set(included.map((v) => v.id));
  const visibleChanges = anatomy?.changes.filter(
    (v) => includedIds.has(v.earlierVisitId) && includedIds.has(v.laterVisitId),
  );
  const observations = included.map((v) => ({
    day: v.daysFromBaseline,
    nWBV: v.metadata.nWBV ?? null,
    MMSE: v.metadata.MMSE ?? null,
    CDR: v.metadata.CDR ?? null,
  }));
  return (
    <section
      className="panel anatomy-panel"
      aria-label="Longitudinal anatomical measurements"
    >
      <div className="panel-heading">
        <div>
          <div className="eyebrow">
            LONGITUDINAL ANATOMY · RESEARCH ESTIMATES
          </div>
          <h2>Anatomy and atrophy estimates</h2>
          <p>
            Separate from observed-CDR classification and baseline conversion
            forecasting.
          </p>
        </div>
        <Button
          disabled={busy || active || !eligible}
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              await post<Analysis>(`/analysis/${visit.id}`, {
                outputMode: "anatomy",
              });
              reload();
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <Play size={15} />
          {active
            ? "Processing anatomy…"
            : busy
              ? "Queuing…"
              : "Run anatomical analysis"}
        </Button>
      </div>
      <div className="prediction-panel">
        <p>
          Native-resolution T1 segmentation; one measured visit or two-to-five
          chronological visits through the selected cutoff. No 64³ proxy,
          rule-based ratings or fabricated future brain.
        </p>
        {!eligible && (
          <p role="status">
            Upload all included MRIs and select a cutoff with at most five
            visits.
          </p>
        )}
        {error && <ErrorState message={error} />}
        {job && (
          <p role="status">
            Anatomy job: {job.status} · {job.stage} · {job.progress}%{" "}
            {job.error}
          </p>
        )}
        <div className="stats-grid">
          {[
            ["MTA left (0–4)", ratings?.mtaLeft],
            ["MTA right (0–4)", ratings?.mtaRight],
            ["Koedam PA (0–3; single estimate)", ratings?.posteriorAtrophy],
          ].map(([label, value]) => (
            <div className="stat-card" key={String(label)}>
              <span className="stat-top">{label}</span>
              <strong className="stat-value">
                {ratings?.status === "ok" && typeof value === "number"
                  ? value.toFixed(2)
                  : "Unavailable"}
              </strong>
              <p>Automatic model estimate · not a diagnosis</p>
            </div>
          ))}
          <div className="stat-card">
            <span className="stat-top">Anatomy QC</span>
            <strong>
              {selected?.qc === "passed"
                ? "Reviewed"
                : selected
                  ? "Pending visual review"
                  : "Not processed"}
            </strong>
            <p>Automated geometry checks are not visual approval.</p>
          </div>
        </div>
        {(
          ratings?.warnings || [
            "AVRA runtime/weights and AC–PC alignment quality have not been verified locally. No scores are substituted.",
          ]
        ).map((w) => (
          <p className="warning-text" key={w}>
            {w}
          </p>
        ))}
        <h3>Regional measurements (mm³)</h3>
        {selected ? (
          <>
            <p>
              {selected.method} · dictionary {selected.dictionaryVersion} · QC{" "}
              {selected.qc}. Mask and partial-volume statistics are different
              estimators.
            </p>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Region</th>
                    <th>Stats mm³</th>
                    <th>Conformed hard-label mask mm³</th>
                    <th>Stats / eTIV</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(selected.volumesMm3).map(([name, value]) => (
                    <tr key={name}>
                      <td>{regionLabel(name)}</td>
                      <td>{value.toFixed(1)}</td>
                      <td>
                        {selected.maskVolumesMm3[name]?.toFixed(1) ??
                          "Unavailable"}
                      </td>
                      <td>
                        {selected.headSizeRatios[name]?.toFixed(6) ??
                          "Unavailable"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              Hippocampal asymmetry:{" "}
              {selected.hippocampalAsymmetryPercent.toFixed(2)}% · 200 × (left −
              right) / (left + right).
            </p>
            <p>
              eTIV head-size reference:{" "}
              {selected.etivMm3 == null
                ? "Unavailable; source unit unverified or missing"
                : `${selected.etivMm3.toFixed(0)} mm³ (source cm³ × 1000)`}
              . Ratios are descriptive, not age-adjusted atrophy norms.
            </p>
          </>
        ) : (
          <p>
            Not processed for this visit. Native FastSurfer outputs are
            required; source nWBV is not a segmented regional volume.
          </p>
        )}
        {selected?.qc === "pending_review" && (
          <div className="notice">
            <div>
              <p>
                Inspect the anatomical overlays against this source MRI in all
                three planes before confirming. This reviews segmentation, not
                patient atrophy scores.
              </p>
              <label className="volume-check">
                <input
                  type="checkbox"
                  checked={reviewConfirmed}
                  onChange={(e) => setReviewConfirmed(e.target.checked)}
                />
                I have visually inspected this segmentation and accept its
                anatomical QC.
              </label>
              <Button
                variant="outline"
                disabled={!reviewConfirmed || busy}
                onClick={async () => {
                  setBusy(true);
                  setError("");
                  try {
                    await post(
                      `/analysis/${patient.completedAnatomy!.id}/anatomy-qc/${visit.id}`,
                      { visualReviewConfirmed: true },
                    );
                    setReviewConfirmed(false);
                    reload();
                  } catch (e) {
                    setError((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Record visual segmentation review
              </Button>
            </div>
          </div>
        )}
        <h3>Measured change history</h3>
        <h4>Automatic score history through selected cutoff</h4>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Elapsed day</th>
                <th>MTA left</th>
                <th>MTA right</th>
                <th>Single Koedam PA</th>
                <th>Alignment QC</th>
              </tr>
            </thead>
            <tbody>
              {anatomy?.visits
                .filter((v) => v.daysFromBaseline <= visit.daysFromBaseline)
                .map((v) => (
                  <tr key={v.visitId}>
                    <td>{v.daysFromBaseline}</td>
                    <td>
                      {v.ratings.status === "ok"
                        ? v.ratings.mtaLeft?.toFixed(2)
                        : "Unavailable"}
                    </td>
                    <td>
                      {v.ratings.status === "ok"
                        ? v.ratings.mtaRight?.toFixed(2)
                        : "Unavailable"}
                    </td>
                    <td>
                      {v.ratings.status === "ok"
                        ? v.ratings.posteriorAtrophy?.toFixed(2)
                        : "Unavailable"}
                    </td>
                    <td>{v.ratings.status}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        <p>
          Later minus earlier; negative means volume loss. Annualization uses
          actual elapsed days / 365.25. No spatial registration is implied.
        </p>
        {visibleChanges?.length ? (
          visibleChanges.map((change) => (
            <details key={change.laterVisitId}>
              <summary>
                {change.elapsedDays} days · {change.status}
              </summary>
              {change.status !== "ok" ? (
                <p>
                  Both segmentations must pass visual review before changes are
                  reported.
                </p>
              ) : (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Region</th>
                        <th>Δ mm³</th>
                        <th>Δ %</th>
                        <th>%/year</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(change.regions).map(([name, value]) => (
                        <tr key={name}>
                          <td>{regionLabel(name)}</td>
                          <td>{value.absoluteMm3.toFixed(1)}</td>
                          <td>{value.percent.toFixed(2)}</td>
                          <td>{value.annualizedPercent.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </details>
          ))
        ) : (
          <p>
            At least two consistently processed, reviewed visits are required.
          </p>
        )}
        <h3>Source-provided observations through selected cutoff</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Elapsed day</th>
                <th>nWBV</th>
                <th>MMSE</th>
                <th>CDR</th>
              </tr>
            </thead>
            <tbody>
              {observations.map((v) => (
                <tr key={v.day}>
                  <td>{v.day}</td>
                  <td>{v.nWBV ?? "Missing"}</td>
                  <td>{v.MMSE ?? "Missing"}</td>
                  <td>{v.CDR ?? "Missing"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {observations.some((v) => v.nWBV != null) && (
          <div className="trajectory-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={observations}>
                <CartesianGrid stroke="#223141" />
                <XAxis
                  dataKey="day"
                  type="number"
                  domain={["dataMin", "dataMax"]}
                />
                <YAxis domain={[0, 1]} />
                <Tooltip />
                <Line
                  name="Observed source nWBV"
                  dataKey="nWBV"
                  stroke="#66dfd2"
                  connectNulls={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
        <p>
          No later scan/Group field enters a forecast input. Rating agreement
          and structural prediction accuracy are unverified; no evaluated
          uncertainty bands are available.
        </p>
        <Button
          variant="outline"
          disabled={!anatomy || busy}
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              setReport(
                await post<Report>(
                  `/reports/${patient.id}?analysis_id=${patient.completedAnatomy!.id}`,
                ),
              );
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <Download size={15} />
          Generate anatomy research report
        </Button>
        {report && (
          <a className="text-link" href={report.downloadUrl} download>
            Download anatomy PDF
          </a>
        )}
      </div>
    </section>
  );
}
