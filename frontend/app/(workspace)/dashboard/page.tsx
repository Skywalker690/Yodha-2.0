"use client";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  Brain,
  CheckCheck,
  Clock3,
  Plus,
  ScanLine,
  Users,
} from "lucide-react";
import {
  PageTitle,
  Loading,
  ErrorState,
  ModeBadge,
  Empty,
} from "@/components/common";
import { Button } from "@/components/ui/button";
import { PatientTable } from "@/components/patient-table";
import { PatientValuesPanel } from "@/components/patient-values-panel";
import { TrajectoryChart } from "@/components/trajectory-chart";
import { useResource } from "@/lib/use-resource";
import type { Patient } from "@/types";

export default function Dashboard() {
  const { data, error, loading, reload } = useResource<Patient[]>(
    "/patients",
    5000,
  );
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const patients = data || [];
  const featured =
    patients.find(
      (p) => (p.latestCompleted?.resultJson?.visitIds.length || 0) >= 3,
    ) || patients.find((p) => p.latestCompleted?.resultJson);
  const trainedFeatured =
    featured?.latestCompleted?.resultJson?.outputMode === "trained";
  const stats = [
    {
      label: "Research patients",
      value: patients.length,
      icon: Users,
      note: "In your local cohort",
    },
    {
      label: "MRI visits",
      value: patients.reduce((sum, p) => sum + p.visitCount, 0),
      icon: ScanLine,
      note: "Longitudinal observations",
    },
    {
      label: "Analyzed cases",
      value: patients.filter((p) => p.latestCompleted).length,
      icon: CheckCheck,
      note: "Results available for review",
    },
    {
      label: "Active analyses",
      value: patients.filter((p) =>
        ["processing", "queued"].includes(p.latestAnalysis?.status || ""),
      ).length,
      icon: Clock3,
      note: "Managed by your local worker",
    },
  ];
  return (
    <>
      <PageTitle
        eyebrow="RESEARCH OVERVIEW"
        title="A clearer view of change."
        action={
          <Button asChild>
            <Link href="/patients?new=1">
              <Plus size={16} /> Add patient
            </Link>
          </Button>
        }
      >
        Your longitudinal MRI research, connected in one workspace.
      </PageTitle>
      <div className="stats-grid">
        {stats.map((s) => (
          <div className="stat-card" key={s.label}>
            <div className="stat-top">
              <span>{s.label}</span>
              <s.icon size={18} />
            </div>
            <strong className="stat-value">
              {s.value.toString().padStart(2, "0")}
            </strong>
            <p>{s.note}</p>
          </div>
        ))}
      </div>
      <PatientValuesPanel patients={patients} />
      <div className="dashboard-middle">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">
                {trainedFeatured
                  ? "RETROSPECTIVE MODEL"
                  : "LONGITUDINAL INSIGHTS"}
              </div>
              <h2>
                {trainedFeatured
                  ? "Experimental sequence classification"
                  : "Progression-risk trajectory"}
              </h2>
            </div>
            {featured?.latestCompleted && (
              <ModeBadge mode={featured.latestCompleted.outputMode} />
            )}
          </div>
          {featured?.latestCompleted?.resultJson ? (
            <>
              <div className="chart-identity">
                <span className="mini-avatar">
                  <Brain size={17} />
                </span>
                <strong>{featured.code}</strong>
                <span>
                  {featured.latestCompleted.resultJson.visitIds.length} visits
                </span>
                <Link href={`/patients/${featured.id}`}>
                  Review case <ArrowUpRight size={14} />
                </Link>
              </div>
              <TrajectoryChart result={featured.latestCompleted.resultJson} />
            </>
          ) : (
            <Empty title="Your first research result starts here">
              Complete an analysis to review sequence classification or baseline
              image comparisons.
            </Empty>
          )}
        </section>
        <section className="panel quick-panel">
          <div className="eyebrow">FROM SCAN TO STORY</div>
          <h2>
            Built for the
            <br />
            longitudinal view.
          </h2>
          <p>
            Explore the same subject across visits, with the context that a
            single scan cannot provide.
          </p>
          <div className="workflow-step">
            <span>01</span>
            <div>
              <strong>Bring visits together</strong>
              <small>Organize MRI scans chronologically</small>
            </div>
          </div>
          <div className="workflow-step">
            <span>02</span>
            <div>
              <strong>Explore structural change</strong>
              <small>Review trajectories and image proxies</small>
            </div>
          </div>
          <div className="workflow-step">
            <span>03</span>
            <div>
              <strong>Keep the research traceable</strong>
              <small>Compare scans and export a report</small>
            </div>
          </div>
          <Link className="text-link" href="/analysis">
            Open MRI workspace <ArrowRight size={16} />
          </Link>
        </section>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Recent patients</h2>
            <p>Your latest research cases and analysis activity</p>
          </div>
          <Link className="text-link" href="/patients">
            View all patients <ArrowRight size={16} />
          </Link>
        </div>
        <PatientTable patients={patients.slice(0, 5)} />
      </section>
      <div className="notice">
        <Brain size={19} />
        <p>
          <strong>Designed for research.</strong> Every result includes its
          origin and limitations. Estimates require qualified review and
          independent validation.
        </p>
      </div>
    </>
  );
}
