"use client";
import { useEffect, useState } from "react";
import { Play, Download } from "lucide-react";
import {
  Line,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Area,
  ComposedChart,
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
  useEffect(() => {
    setReport(null);
    setError("");
  }, [visit.id, patient.completedAnatomy?.id]);
  const [region, setRegion] = useState("");
  const job = patient.latestAnatomy;
  const anatomy = patient.completedAnatomy?.resultJson?.anatomy;
  const selected = anatomy?.visits.find((v) => v.visitId === visit.id);
  const active = job?.status === "queued" || job?.status === "processing";
  const included = patient.visits.filter(
    (v) => v.daysFromBaseline <= visit.daysFromBaseline,
  );
  const eligible = included.length <= 5 && included.every((v) => v.hasMri);
  const ratings = selected?.ratings;
  const ratingsVisible =
    ratings?.status === "ok" || ratings?.status === "unreviewed_research";
  const ratingStatusLabel = !selected
    ? "Not processed"
    : ratings?.status === "invalid"
      ? "Scoring failed"
      : "Unavailable";
  const forecast = anatomy?.forecast;
  const matchingForecast =
    forecast?.status === "available" && forecast.cutoffVisitId === visit.id
      ? forecast
      : null;
  const selectedRegion = region || Object.keys(selected?.volumesMm3 || {})[0];
  const volumeSeries =
    anatomy?.visits
      .filter((v) => v.daysFromBaseline <= visit.daysFromBaseline)
      .map((v) => ({
        day: v.daysFromBaseline,
        measured: v.volumesMm3[selectedRegion],
        predicted:
          v.visitId === visit.id && matchingForecast
            ? v.volumesMm3[selectedRegion]
            : null,
        band: null as [number, number] | null,
      })) || [];
  if (matchingForecast && matchingForecast.intervalDays > 0)
    volumeSeries.push({
      day: visit.daysFromBaseline + matchingForecast.intervalDays,
      measured: undefined!,
      predicted: matchingForecast.volumesMm3?.[selectedRegion] ?? null,
      band: matchingForecast.predictionIntervals?.[selectedRegion] ?? null,
    });
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
                {ratingsVisible && typeof value === "number"
                  ? value.toFixed(2)
                  : ratingStatusLabel}
              </strong>
              <p>
                {ratings?.status === "unreviewed_research"
                  ? "Automatic, unreviewed research estimate · not a diagnosis"
                  : !selected
                    ? "Run anatomical analysis to create an estimate."
                    : "Automatic model estimate · not a diagnosis"}
              </p>
            </div>
          ))}
          <div className="stat-card">
            <span className="stat-top">Measurement status</span>
            <strong>
              {selected?.qc === "passed"
                ? "Reviewed"
                : selected?.qc === "automated_checks_only"
                  ? "Automated checks only"
                  : selected
                    ? "Not visually reviewed"
                    : "Not processed"}
            </strong>
            <p>
              {selected?.qc === "automated_checks_only"
                ? "Measurements are available as unreviewed research estimates."
                : "QC and provenance are reported separately from the numeric estimates."}
            </p>
          </div>
        </div>
        {(
          ratings?.warnings || [
            "No AVRA estimate is available for this visit. No substitute score was generated.",
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
        {selected && (
          <>
            <h3>Observed versus model-predicted regional anatomy</h3>
            <label>
              Region
              <select
                aria-label="Anatomy chart region"
                value={selectedRegion}
                onChange={(e) => setRegion(e.target.value)}
              >
                {Object.keys(selected.volumesMm3).map((name) => (
                  <option key={name} value={name}>
                    {regionLabel(name)}
                  </option>
                ))}
              </select>
            </label>
            <div className="trajectory-chart">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={volumeSeries}>
                  <CartesianGrid stroke="#223141" />
                  <XAxis
                    dataKey="day"
                    type="number"
                    domain={["dataMin", "dataMax"]}
                  />
                  <YAxis domain={[0, "auto"]} />
                  <Tooltip />
                  <Area
                    dataKey="band"
                    name="Evaluated structural prediction interval (mm³)"
                    fill="#66dfd2"
                    fillOpacity={0.2}
                    stroke="none"
                    connectNulls={false}
                    isAnimationActive={false}
                  />
                  <Line
                    dataKey="measured"
                    name="Observed FastSurfer stats (mm³)"
                    stroke="#66dfd2"
                    connectNulls={false}
                    isAnimationActive={false}
                  />
                  <Line
                    dataKey="predicted"
                    name="Model-generated stats estimate (mm³)"
                    stroke="#b99bff"
                    strokeDasharray="5 4"
                    connectNulls={false}
                    isAnimationActive={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            {matchingForecast ? (
              <>
                <p>
                  Model-generated estimate at +{matchingForecast.intervalDays}{" "}
                  days · {matchingForecast.spatialModelVersion}. Not an acquired
                  measurement.
                </p>
                <p>
                  Release {matchingForecast.releaseSha256?.slice(0, 12)} ·
                  checkpoint {matchingForecast.modelSha256?.slice(0, 12)}.
                </p>
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Region</th>
                        <th>Predicted mm³</th>
                        <th>Evaluated interval mm³</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(matchingForecast.volumesMm3 || {}).map(
                        ([name, value]) => (
                          <tr key={name}>
                            <td>{regionLabel(name)}</td>
                            <td>{value.toFixed(1)}</td>
                            <td>
                              {matchingForecast.predictionIntervals?.[name]
                                ?.map((v) => v.toFixed(1))
                                .join(" – ") || "Unavailable"}
                            </td>
                          </tr>
                        ),
                      )}
                    </tbody>
                  </table>
                </div>
                <p>
                  {matchingForecast.intervalEvidence
                    ? `${matchingForecast.intervalEvidence.level * 100}% target coverage; evaluated on ${matchingForecast.intervalEvidence.subjects} held-out subjects (${matchingForecast.intervalEvidence.method}). Small-cohort research evidence only.`
                    : "Intervals are unavailable: physical bounds or held-out coverage gates were not satisfied."}
                </p>
              </>
            ) : (
              <p>
                No matching evaluated structural forecast exists for this
                cutoff. Observations above are not extrapolated.
              </p>
            )}
          </>
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
                <th>AVRA research status</th>
              </tr>
            </thead>
            <tbody>
              {anatomy?.visits
                .filter((v) => v.daysFromBaseline <= visit.daysFromBaseline)
                .map((v) => (
                  <tr key={v.visitId}>
                    <td>{v.daysFromBaseline}</td>
                    <td>
                      {(v.ratings.status === "ok" ||
                        v.ratings.status === "unreviewed_research") &&
                      typeof v.ratings.mtaLeft === "number"
                        ? v.ratings.mtaLeft?.toFixed(2)
                        : "Unavailable"}
                    </td>
                    <td>
                      {(v.ratings.status === "ok" ||
                        v.ratings.status === "unreviewed_research") &&
                      typeof v.ratings.mtaRight === "number"
                        ? v.ratings.mtaRight?.toFixed(2)
                        : "Unavailable"}
                    </td>
                    <td>
                      {(v.ratings.status === "ok" ||
                        v.ratings.status === "unreviewed_research") &&
                      typeof v.ratings.posteriorAtrophy === "number"
                        ? v.ratings.posteriorAtrophy.toFixed(2)
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
              {change.status !== "ok" &&
              change.status !== "automated_checks_only" ? (
                <p>
                  Regional changes are unavailable because paired measurements
                  did not pass the required processing checks.
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
          requires independent reference ratings; model-specific structural
          evidence is displayed only for an evaluated release.
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
