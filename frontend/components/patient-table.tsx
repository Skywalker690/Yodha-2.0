"use client";
import Link from "next/link";
import { ArrowUpRight, UserRound } from "lucide-react";
import type { Patient } from "@/types";
import { ModeBadge, Empty } from "./common";
import { percent } from "@/lib/utils";
import { formatModelScore } from "./trained-prediction";

export function PatientTable({ patients }: { patients: Patient[] }) {
  if (!patients.length)
    return (
      <Empty title="No patients yet">
        Create a patient or import your OASIS research cohort to get started.
      </Empty>
    );
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Patient</th>
            <th>Visits</th>
            <th>Latest research output</th>
            <th>Analysis status</th>
            <th>Provenance</th>
            <th>
              <span className="sr-only">Open</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {patients.map((p) => (
            <tr key={p.id}>
              <td>
                <Link className="patient-link" href={`/patients/${p.id}`}>
                  <span className="patient-avatar">
                    <UserRound size={18} />
                  </span>
                  <span>
                    <strong>{p.code}</strong>
                    <small>
                      {p.age ? `${p.age} years` : "Age unspecified"} <b>·</b>{" "}
                      {p.sex || "Unspecified"}
                    </small>
                  </span>
                </Link>
              </td>
              <td>
                <span className="numeric">
                  {p.visitCount.toString().padStart(2, "0")}
                </span>{" "}
                <span className="muted">visits</span>
              </td>
              <td className="research-score">
                {p.latestCompleted?.outputMode === "trained" ? (
                  <>
                    <strong className="numeric">
                      {formatModelScore(
                        p.latestCompleted.resultJson?.prediction?.score,
                      )}
                    </strong>
                    <small className="muted">
                      Experimental observed-CDR-increase score · not disease
                      probability
                    </small>
                    {p.latestCompleted.resultJson?.prediction?.cohortRole ===
                      "train" && (
                      <small className="muted">
                        In-sample · not accuracy evidence
                      </small>
                    )}
                  </>
                ) : p.latestCompleted?.score != null &&
                  Number.isFinite(p.latestCompleted.score) ? (
                  <>
                    <strong className="numeric">
                      {percent(p.latestCompleted.score)}
                    </strong>
                    <small className="muted">
                      {p.latestCompleted.outputMode === "demo"
                        ? "Illustrative index"
                        : "Baseline structural-change index"}
                    </small>
                  </>
                ) : (
                  <span className="muted">Not analyzed</span>
                )}
              </td>
              <td>
                <span
                  className={`state ${p.latestAnalysis?.status || "pending"}`}
                >
                  <i />
                  {p.latestAnalysis?.status || "Awaiting MRI"}
                </span>
              </td>
              <td>
                {p.latestCompleted ? (
                  <ModeBadge mode={p.latestCompleted.outputMode} />
                ) : (
                  <span className="muted">—</span>
                )}
              </td>
              <td>
                <Link
                  className="icon-button"
                  aria-label={`Open ${p.code}`}
                  href={`/patients/${p.id}`}
                >
                  <ArrowUpRight size={18} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
