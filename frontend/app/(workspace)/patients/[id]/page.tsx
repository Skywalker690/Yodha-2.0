"use client";
import { use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { AnalysisWorkspace } from "@/components/analysis-workspace";
import { ErrorState, Loading, PageTitle } from "@/components/common";
import { useResource } from "@/lib/use-resource";
import type { Patient } from "@/types";

export default function PatientPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data, error, loading, reload } = useResource<Patient>(
    `/patients/${id}`,
    2000,
  );
  return (
    <div
      className={`patient-case-page ${data?.servingPolicy !== "research" ? "patient-case-template" : ""}`}
    >
      <Link className="back-link" href="/patients">
        <ArrowLeft size={15} /> Patient directory
      </Link>
      <PageTitle
        eyebrow="LONGITUDINAL CASE REVIEW"
        title="Understand the change."
      >
        A connected view of MRI observations, research metrics, and context.
      </PageTitle>
      {loading && <Loading />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && <AnalysisWorkspace key={id} patient={data} reload={reload} />}
    </div>
  );
}
