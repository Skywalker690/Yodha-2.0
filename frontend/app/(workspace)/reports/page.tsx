"use client";
import Link from "next/link";
import { Download, FileText } from "lucide-react";
import {
  Empty,
  ErrorState,
  Loading,
  ModeBadge,
  PageTitle,
} from "@/components/common";
import { Button } from "@/components/ui/button";
import { useResource } from "@/lib/use-resource";
import { date } from "@/lib/utils";
import type { Report } from "@/types";

export default function Reports() {
  const { data, error, loading, reload } = useResource<Report[]>("/reports");
  return (
    <>
      <PageTitle eyebrow="RESEARCH RECORDS" title="Reports">
        Traceable snapshots of your analysis, ready for research review.
      </PageTitle>
      <div className="notice">
        <FileText size={20} />
        <p>
          Generate a report from a completed patient analysis. Each PDF records
          the sequence, output provenance, methods, and limitations at the time
          of generation.
        </p>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <h2>
            Generated reports{" "}
            <span className="count-pill">{data?.length || 0}</span>
          </h2>
        </div>
        {loading ? (
          <Loading />
        ) : error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : !data?.length ? (
          <Empty title="No reports generated yet">
            Open a patient, complete an analysis, then select Generate research
            report.
          </Empty>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Research report</th>
                  <th>Generated</th>
                  <th>Output provenance</th>
                  <th>Download</th>
                </tr>
              </thead>
              <tbody>
                {data.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <Link
                        className="patient-link"
                        href={`/patients/${r.patientId}`}
                      >
                        <span className="patient-avatar">
                          <FileText size={18} />
                        </span>
                        <span>
                          <strong>{r.patientCode}</strong>
                          <small>
                            Analysis {r.analysisId.slice(0, 8)} · PDF
                          </small>
                        </span>
                      </Link>
                    </td>
                    <td>{date(r.createdAt)}</td>
                    <td>
                      <ModeBadge mode={r.outputMode} />
                    </td>
                    <td>
                      <Button asChild variant="outline" size="sm">
                        <a download href={r.downloadUrl}>
                          <Download size={15} /> Download PDF
                        </a>
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
