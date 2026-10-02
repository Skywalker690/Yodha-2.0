"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, ChartNoAxesCombined, UserRound } from "lucide-react";
import type { Patient, Visit } from "@/types";

const finite = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);

const shown = (value: unknown, digits = 2) =>
  finite(value) ? value.toFixed(digits) : null;

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
  const ratingDisplay = (value: number | null | undefined) =>
    ratingsVisible ? shown(value) : null;
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
  const reference = analysis?.resultJson?.biomarkers.nwbvAgeReferenceV1;
  const referenceMatchesVisit = reference?.visitId === selected?.visitId;
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
  const availableObservedValues = observedValues.flatMap(
    ([label, value, unit]) => {
      if (finite(value)) {
        return [
          {
            label,
            value:
              label === "Source nWBV"
                ? value.toFixed(6)
                : value.toLocaleString(),
            unit,
          },
        ];
      }
      if (
        (label === "Sex" || label === "Handedness") &&
        typeof value === "string"
      ) {
        const text = value.trim();
        if (
          text &&
          !/^(unavailable|not available|unspecified|unknown|n\/a|none|null|nan|-|—)$/i.test(
            text,
          )
        ) {
          return [{ label, value: text, unit }];
        }
      }
      return [];
    },
  );
  const regionalVolumes = Object.entries(selected?.volumesMm3 ?? {}).filter(
    ([, value]) => finite(value),
  );
  const showMaskVolumes = regionalVolumes.some(([name]) =>
    finite(selected?.maskVolumesMm3[name]),
  );
  const showHeadSizeRatios = regionalVolumes.some(([name]) =>
    finite(selected?.headSizeRatios[name]),
  );

  if (!patients.length) return null;

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
            {sourceVisit && <span>{sourceVisit.label}</span>}
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

        {selected && (
          <>
            <div className="stats-grid patient-values-stats">
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
                label="Hippocampal asymmetry"
                value={
                  finite(selected.hippocampalAsymmetryPercent)
                    ? selected.hippocampalAsymmetryPercent.toFixed(2) + "%"
                    : null
                }
                note="200 × (left − right) / (left + right)"
              />
              <ValueCard
                label="Age-matched nWBV reference"
                value={
                  referenceMatchesVisit &&
                  reference?.status === "ok" &&
                  finite(reference.zScore)
                    ? `z ${reference.zScore.toFixed(2)}`
                    : null
                }
                note="Descriptive reference only · not diagnosis"
              />
            </div>
            {availableObservedValues.length > 0 && (
              <>
                <h3 className="patient-values-subtitle">
                  Recorded source values
                </h3>
                <div className="patient-values-source-grid">
                  {availableObservedValues.map(({ label, value, unit }) => (
                    <div key={label}>
                      <span>{label}</span>
                      <strong>{value}</strong>
                      <small>{unit}</small>
                    </div>
                  ))}
                </div>
              </>
            )}

            {regionalVolumes.length > 0 && (
              <>
                <h3 className="patient-values-subtitle">
                  Regional anatomy · mm³
                </h3>
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Region</th>
                        <th>Stats</th>
                        {showMaskVolumes && <th>Hard-label mask</th>}
                        {showHeadSizeRatios && <th>Stats / eTIV</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {regionalVolumes.map(([name, volume]) => (
                        <tr key={name}>
                          <td>{labelForRegion(name)}</td>
                          <td>
                            {volume.toLocaleString(undefined, {
                              maximumFractionDigits: 1,
                            })}
                          </td>
                          {showMaskVolumes && (
                            <td>
                              {finite(selected.maskVolumesMm3[name])
                                ? selected.maskVolumesMm3[name].toLocaleString(
                                    undefined,
                                    { maximumFractionDigits: 1 },
                                  )
                                : null}
                            </td>
                          )}
                          {showHeadSizeRatios && (
                            <td>
                              {finite(selected.headSizeRatios[name])
                                ? selected.headSizeRatios[name].toFixed(6)
                                : null}
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
            <p className="patient-values-disclaimer">
              {ratingsVisible
                ? ratings?.status === "unreviewed_research"
                  ? "AVRA values are automatically available as unreviewed research estimates; alignment and rating agreement were not reviewed."
                  : "Automatic MTA/Koedam estimates are not a diagnosis."
                : ""}{" "}
              Regional volumes and ratios are descriptive measurements, not
              age-adjusted atrophy norms.
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
  value: string | null;
  note: string;
}) {
  if (value === null) return null;
  return (
    <div className="stat-card">
      <span className="stat-top">{label}</span>
      <strong className="stat-value patient-value-number">{value}</strong>
      <p>{note}</p>
    </div>
  );
}
