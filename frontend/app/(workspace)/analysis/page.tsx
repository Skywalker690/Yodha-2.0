"use client";
import { useState } from "react";
import { AnalysisWorkspace } from "@/components/analysis-workspace";
import { PageTitle, Loading, ErrorState, Empty } from "@/components/common";
import { useResource } from "@/lib/use-resource";
import type { Patient } from "@/types";

export default function AnalysisPage() {
  const { data, error, loading, reload } = useResource<Patient[]>(
    "/patients",
    2000,
  );
  const [id, setId] = useState("");
  const selected = data?.find((p) => p.id === id) || data?.[0];
  return (
    <>
      <PageTitle
        eyebrow="MRI ANALYSIS"
        title="Your research workspace."
        action={
          data?.length ? (
            <label className="patient-selector">
              <span>Select patient</span>
              <select
                value={selected?.id || ""}
                onChange={(e) => setId(e.target.value)}
              >
                {data.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code}
                  </option>
                ))}
              </select>
            </label>
          ) : null
        }
      >
        Compare scans, explore differences, and build a longitudinal view.
      </PageTitle>
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : selected ? (
        <AnalysisWorkspace
          key={selected.id}
          patient={selected}
          reload={reload}
        />
      ) : (
        <Empty title="No research cases available">
          Add a patient from the Patients page to begin.
        </Empty>
      )}
    </>
  );
}
