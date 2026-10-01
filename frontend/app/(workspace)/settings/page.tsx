"use client";
import { Database, FlaskConical, HardDrive, ShieldCheck } from "lucide-react";
import { PageTitle, Loading, ErrorState } from "@/components/common";
import { useResource } from "@/lib/use-resource";
import type { Health } from "@/types";

export default function Settings() {
  const { data, error, loading, reload } = useResource<Health>(
    "/health",
    10000,
  );
  const { data: user } = useResource<{ email: string }>("/auth/me");
  return (
    <>
      <PageTitle eyebrow="WORKSPACE SETTINGS" title="Local by design.">
        Your research environment, account, and model information.
      </PageTitle>
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : (
        <div className="settings-grid">
          <section className="panel settings-card">
            <ShieldCheck size={26} />
            <h2>Researcher account</h2>
            <p>{user?.email}</p>
            <dl>
              <dt>Authentication</dt>
              <dd>JWT · HTTP-only session cookie</dd>
              <dt>Session duration</dt>
              <dd>8 hours</dd>
              <dt>Patient access</dt>
              <dd>Restricted to this researcher</dd>
            </dl>
          </section>
          <section className="panel settings-card">
            <Database size={26} />
            <h2>Service status</h2>
            <dl>
              <dt>API</dt>
              <dd>{data?.status}</dd>
              <dt>PostgreSQL</dt>
              <dd>{data?.database}</dd>
              <dt>Analysis worker</dt>
              <dd className={data?.worker === "offline" ? "warning-text" : ""}>
                {data?.worker}
              </dd>
              <dt>Storage</dt>
              <dd>{data?.storage}</dd>
            </dl>
            {data?.worker === "offline" && (
              <p className="warning-text">
                The analysis worker is offline. Start the worker to process
                queued analyses.
              </p>
            )}
          </section>
          <section className="panel settings-card">
            <FlaskConical size={26} />
            <h2>Research model</h2>
            <dl>
              <dt>Version</dt>
              <dd>{data?.modelVersion}</dd>
              <dt>Method</dt>
              <dd>Pooled MRI feature deltas</dd>
              <dt>Explanation</dt>
              <dd>Intensity-difference visualization</dd>
              <dt>Confidence estimator</dt>
              <dd>Not available</dd>
            </dl>
            <p>
              Scores are uncalibrated change indices. They do not estimate the
              probability of Alzheimer’s disease.
            </p>
          </section>
          <section className="panel settings-card">
            <HardDrive size={26} />
            <h2>Data & provenance</h2>
            <p>
              MRI volumes and derived artifacts stay in local storage.
              Demographic observations retain their OASIS source.
            </p>
            <dl>
              <dt>Demo</dt>
              <dd>Illustrative scores</dd>
              <dt>Precomputed</dt>
              <dd>Cached baseline computation</dd>
              <dt>Inference</dt>
              <dd>Computed from the uploaded sequence</dd>
            </dl>
          </section>
        </div>
      )}
    </>
  );
}
