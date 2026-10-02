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
            <h2>
              {data?.servingPolicy === "ml_only"
                ? "ML-only serving"
                : "Research model"}
            </h2>
            {data?.servingPolicy === "ml_only" ? (
              <>
                <dl>
                  <dt>Active method</dt>
                  <dd>Clinical + FastSurfer · trained logistic heads</dd>
                  <dt>Release readiness</dt>
                  <dd>
                    {data.forecastReadiness?.ready
                      ? "Promoted research release"
                      : "Prediction blocked"}
                  </dd>
                  <dt>Fallback</dt>
                  <dd>
                    Disabled · no demo, feature-delta or historical neural
                    scores
                  </dd>
                  <dt>Clinical validation</dt>
                  <dd>Not established</dd>
                </dl>
                {data.forecastReadiness?.reasons.map((reason) => (
                  <p className="warning-text" key={reason}>
                    {reason}
                  </p>
                ))}
              </>
            ) : (
              <>
                <dl>
                  <dt>Experimental trained checkpoint</dt>
                  <dd>{data?.trainedModelVersion || "Unavailable"}</dd>
                  <dt>Trained bundle availability</dt>
                  <dd>
                    {data?.trainedModelReady
                      ? "Available for experimental inference"
                      : "Unavailable"}
                  </dd>
                  <dt>Method</dt>
                  <dd>3D CNN + demographic MLP + LSTM</dd>
                  <dt>Target</dt>
                  <dd>Retrospective observed CDR increase</dd>
                  <dt>Legacy baseline version</dt>
                  <dd>{data?.baselineModelVersion || data?.modelVersion}</dd>
                  <dt>Image visualization</dt>
                  <dd>Intensity differences, not trained-model attribution</dd>
                  <dt>Confidence estimator</dt>
                  <dd>Not available</dd>
                </dl>
                <p>
                  The trained checkpoint has poor measured generalization. Its
                  uncalibrated sequence score is not a future Alzheimer’s
                  probability. Legacy baseline scores remain image-change
                  indices.
                </p>
              </>
            )}
          </section>
          <section className="panel settings-card">
            <HardDrive size={26} />
            <h2>Data & provenance</h2>
            <p>
              MRI volumes and derived artifacts stay in local storage.
              Demographic observations retain their OASIS source.
            </p>
            {data?.servingPolicy === "ml_only" ? (
              <p>
                Historical analyses and reports are preserved as archives. New
                predictions require a promoted combined model and reviewed
                baseline MRI anatomy.
              </p>
            ) : (
              <dl>
                <dt>Demo</dt>
                <dd>Illustrative scores</dd>
                <dt>Precomputed</dt>
                <dd>Cached baseline computation</dd>
                <dt>Inference</dt>
                <dd>Legacy feature-delta baseline</dd>
                <dt>Trained</dt>
                <dd>
                  Experimental saved neural checkpoint and recorded covariates
                </dd>
              </dl>
            )}
          </section>
        </div>
      )}
    </>
  );
}
