"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, ChartNoAxesCombined, UserRound } from "lucide-react";
import type { AnatomyVisit, Patient, Visit } from "@/types";

const finite = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);

const shown = (value: unknown, digits = 2) =>
  finite(value) ? value.toFixed(digits) : "Unavailable";

const labelForRegion = (name: string) =>
  name
    .replace(/_mm3$/i, "")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

const sourceValue = (metadata: Visit["metadata"], key: string) =>
  (metadata as Record<string, unknown>)[key];

function latestAnatomyDate(patient: Patient) {
  return patient.completedAnatomy?.createdAt || "";
}

export function PatientValuesPanel({ patients }: { patients: Patient[] }) {
  const [patientId, setPatientId] = useState("");
  const [visitId, setVisitId] = useState("");
  const defaultPatient = [...patients].sort((a, b) => {
    const visitsA = a.completedAnatomy?.resultJson?.anatomy?.visits.length || 0;
    const visitsB = b.completedAnatomy?.resultJson?.anatomy?.visits.length || 0;
    return (
      visitsB - visitsA ||
      latestAnatomyDate(b).localeCompare(latestAnatomyDate(a))
    );
  })[0];
  const patient =
    patients.find((item) => item.id === patientId) || defaultPatient;
  const analysis = patient?.completedAnatomy;
  const anatomy = analysis?.resultJson?.anatomy;
  const anatomyVisits = anatomy?.visits || [];
  const selected =
    anatomyVisits.find((item) => item.visitId === visitId) ||
    anatomyVisits[anatomyVisits.length - 1];
  const sourceVisit = patient?.visits.find(
    (item) => item.id === selected?.visitId,
  );
  const metadata = sourceVisit?.metadata || {};
  const ratings = selected?.ratings;
  const ratingsVisible =
    ratings?.status === "ok" || ratings?.status === "unreviewed_research";
  const ratingDisplay = (value: number | null | undefined) => {
    if (ratingsVisible) return shown(value);
    if (selected?.qc === "pending_review") return "Not visually reviewed";
    if (ratings?.status === "pending_alignment_qc")
      return "Pending alignment QC";
    if (ratings?.status === "invalid") return "Scoring failed";
    return "Not available";
  };
  const ratingNote =
    ratings?.status === "unreviewed_research"
      ? "Automatic research estimate · not visually reviewed"
      : ratings?.status === "ok"
        ? "Automatic estimate · not a diagnosis"
        : selected?.qc === "pending_review"
          ? "No reviewed visual QC is recorded."
          : ratings?.status === "pending_alignment_qc"
            ? "Automatic alignment output is pending."
            : "No numeric estimate was produced.";
  const left = selected?.volumesMm3.hippocampus_left_mm3;
  const right = selected?.volumesMm3.hippocampus_right_mm3;
  const totalHippocampus = finite(left) && finite(right) ? left + right : null;
  const reference = analysis?.resultJson?.biomarkers.nwbvAgeReferenceV1;
  const referenceMatchesVisit = reference?.visitId === selected?.visitId;
  const bmi =
    sourceValue(metadata, "BMI") ?? sourceValue(metadata, "Body Mass Index");
  const bmiValue = finite(bmi) && bmi > 0 ? bmi : null;
  const precedingChange = anatomy?.changes.find(
    (change) => change.laterVisitId === selected?.visitId,
  );
  const priorVisit = precedingChange
    ? anatomyVisits.find(
        (item) => item.visitId === precedingChange.earlierVisitId,
      )
    : undefined;
  const priorHippocampus = priorVisit
    ? priorVisit.volumesMm3.hippocampus_left_mm3 +
      priorVisit.volumesMm3.hippocampus_right_mm3
    : null;
  const hippoChangePercent =
    (precedingChange?.status === "ok" ||
      precedingChange?.status === "automated_checks_only") &&
    finite(totalHippocampus) &&
    finite(priorHippocampus) &&
    priorHippocampus > 0
      ? ((totalHippocampus - priorHippocampus) / priorHippocampus) * 100
      : null;
  const visitAge = sourceValue(metadata, "Age");
  const observedValues: [string, unknown, string][] = [
    ["Age at scan", visitAge, "years · OASIS source"],
    [
      "Sex",
      sourceValue(metadata, "M/F") ?? patient?.sex,
      "recorded source value",
    ],
    ["Handedness", sourceValue(metadata, "Hand"), "recorded source value"],
    ["MMSE", sourceValue(metadata, "MMSE"), "observed · /30"],
    ["CDR", sourceValue(metadata, "CDR"), "observed · source scale"],
    ["Source nWBV", sourceValue(metadata, "nWBV"), "observed fraction"],
    ["eTIV", sourceValue(metadata, "eTIV"), "source cm³ / mL"],
    ["Education", sourceValue(metadata, "EDUC"), "source years"],
    ["SES", sourceValue(metadata, "SES"), "source scale"],
    ["ASF", sourceValue(metadata, "ASF"), "source factor"],
  ];

  return (
    <section className="panel patient-values-panel" aria-label="Patient values">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">PATIENT VALUE SNAPSHOT</div>
          <h2>Observed measures and anatomy</h2>
          <p>
            Source observations and measured regional volumes for one selected
            visit.
          </p>
        </div>
        <ChartNoAxesCombined size={19} aria-hidden="true" />
      </div>
      <div className="patient-values-content">
        {patients.length ? (
          <div className="patient-values-controls">
            <label>
              Patient
              <select
                aria-label="Patient values patient"
                value={patient?.id || ""}
                onChange={(event) => {
                  setPatientId(event.target.value);
                  setVisitId("");
                }}
              >
                {patients.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.code}
                    {item.completedAnatomy?.resultJson?.anatomy?.visits.length
                      ? ` · ${item.completedAnatomy.resultJson.anatomy.visits.length} measured visits`
                      : " · no anatomy measurements yet"}
                  </option>
                ))}
              </select>
            </label>
            {anatomyVisits.length > 0 && (
              <label>
                Observed visit
                <select
                  aria-label="Patient values visit"
                  value={selected?.visitId || ""}
                  onChange={(event) => setVisitId(event.target.value)}
                >
                  {anatomyVisits.map((item) => (
                    <option key={item.visitId} value={item.visitId}>
                      {patient?.visits.find((v) => v.id === item.visitId)
                        ?.label || item.visitId}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {patient && (
              <Link
                className="text-link patient-values-link"
                href={`/patients/${patient.id}`}
              >
                Open full case <ArrowUpRight size={15} />
              </Link>
            )}
          </div>
        ) : (
          <p>No patient records are available yet.</p>
        )}

        {patient && (
          <div className="patient-values-identity">
            <span className="patient-avatar">
              <UserRound size={17} />
            </span>
            <strong>{patient.code}</strong>
            <span>{sourceVisit?.label || "No analyzed visit selected"}</span>
            {selected && (
              <span className="badge">
                {selected.qc === "passed"
                  ? "Visual QC reviewed"
                  : selected.qc === "automated_checks_only"
                    ? "Automated checks only"
                    : "Processing review pending"}
              </span>
            )}
          </div>
        )}

        {!selected ? (
          <div className="empty patient-values-empty">
            <h3>No anatomical measurements available</h3>
            <p>
              Select a patient with a completed anatomy analysis to see regional
              volumes and scores.
            </p>
          </div>
        ) : (
          <>
            <div className="stats-grid patient-values-stats">
              <ValueCard
                label="Body mass index (BMI)"
                value={bmiValue == null ? "Unavailable" : bmiValue.toFixed(1)}
                note={
                  bmiValue == null
                    ? "Height and weight are not in this OASIS record."
                    : "Source-provided kg/m²"
                }
              />
              <ValueCard
                label="MTA left · 0–4"
                value={ratingDisplay(ratings?.mtaLeft)}
                note={ratingNote}
              />
              <ValueCard
                label="MTA right · 0–4"
                value={ratingDisplay(ratings?.mtaRight)}
                note={ratingNote}
              />
              <ValueCard
                label="Koedam PA · 0–3"
                value={ratingDisplay(ratings?.posteriorAtrophy)}
                note={ratingNote}
              />
              <ValueCard
                label="Hippocampus · total"
                value={
                  totalHippocampus == null
                    ? "Unavailable"
                    : `${shown(totalHippocampus, 0)} mm³`
                }
                note="FastSurfer partial-volume statistics"
              />
              <ValueCard
                label="Hippocampal asymmetry"
                value={selected.hippocampalAsymmetryPercent.toFixed(2) + "%"}
                note="200 × (left − right) / (left + right)"
              />
              <ValueCard
                label="Hippocampal volume change"
                value={
                  hippoChangePercent == null
                    ? "Unavailable"
                    : `${hippoChangePercent > 0 ? "+" : ""}${hippoChangePercent.toFixed(2)}%`
                }
                note={
                  precedingChange?.status === "ok"
                    ? "Since previous reviewed scan"
                    : precedingChange?.status === "automated_checks_only"
                      ? "Since previous scan · automated estimates only"
                      : "No comparable adjacent measurements"
                }
              />
              <ValueCard
                label="Age-matched nWBV reference"
                value={
                  referenceMatchesVisit &&
                  reference?.status === "ok" &&
                  finite(reference.zScore)
                    ? `z ${reference.zScore.toFixed(2)}`
                    : "Unavailable"
                }
                note="Descriptive reference only · not diagnosis"
              />
            </div>
            <h3 className="patient-values-subtitle">Recorded source values</h3>
            <div className="patient-values-source-grid">
              {observedValues.map(([label, value, unit]) => (
                <div key={label}>
                  <span>{label}</span>
                  <strong>
                    {finite(value)
                      ? label === "Source nWBV"
                        ? value.toFixed(6)
                        : value.toLocaleString()
                      : "Unavailable"}
                  </strong>
                  <small>{unit}</small>
                </div>
              ))}
            </div>

            <h3 className="patient-values-subtitle">Regional anatomy · mm³</h3>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Region</th>
                    <th>Stats</th>
                    <th>Hard-label mask</th>
                    <th>Stats / eTIV</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(selected.volumesMm3).map(([name, volume]) => (
                    <tr key={name}>
                      <td>{labelForRegion(name)}</td>
                      <td>
                        {volume.toLocaleString(undefined, {
                          maximumFractionDigits: 1,
                        })}
                      </td>
                      <td>
                        {selected.maskVolumesMm3[name]?.toLocaleString(
                          undefined,
                          { maximumFractionDigits: 1 },
                        ) ?? "Unavailable"}
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
            <p className="patient-values-disclaimer">
              {ratingsVisible
                ? ratings?.status === "unreviewed_research"
                  ? "AVRA values are automatically available as unreviewed research estimates; alignment and rating agreement were not reviewed."
                  : "Automatic MTA/Koedam estimates are not a diagnosis."
                : `MTA/Koedam values unavailable (${ratings?.status || "not available"}).`}{" "}
              Regional volumes and ratios are descriptive measurements, not
              age-adjusted atrophy norms. Volume changes from automated checks
              are unreviewed research estimates.
            </p>
          </>
        )}
      </div>
    </section>
  );
}

function ValueCard({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note: string;
}) {
  return (
    <div className="stat-card">
      <span className="stat-top">{label}</span>
      <strong className="stat-value patient-value-number">{value}</strong>
      <p>{note}</p>
    </div>
  );
}
