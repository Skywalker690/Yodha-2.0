"use client";
import { useState } from "react";
import { useResource } from "@/lib/use-resource";
import { ErrorState, Loading } from "./common";

type Forecast = {
  prediction: {
    status: string;
    mode: string;
    modelVersion: string;
    usedMri: boolean;
    fastsurferVersion: string | null;
    probabilities: Record<string, number | null>;
    calibration: Record<string, string>;
    warnings: string[];
    explanation: Record<string, unknown>;
  };
  qc: string;
  anatomy: Record<string, number> | null;
};

export function BaselineForecast({ patientId }: { patientId: string }) {
  const [kind, setKind] = useState("clinical");
  const { data, loading, error, reload } = useResource<Forecast>(
    `/patients/${patientId}/forecast?model_kind=${kind}`,
  );
  return (
    <section className="panel" style={{ padding: "1.5rem", marginTop: "1rem" }}>
      <h2>Baseline-only outcome forecast</h2>
      <p>
        Separate experiment: first observed CDR conversion after a CDR-zero
        baseline. Not MCI-to-Alzheimer forecasting or a medical diagnosis. Later
        visits are labels only.
      </p>
      <label>
        Forecast model
        <select value={kind} onChange={(event) => setKind(event.target.value)}>
          <option value="clinical">Clinical reference</option>
          <option value="clinical_matched">
            Clinical on matched MRI cohort
          </option>
          <option value="clinical_fastsurfer">Clinical + FastSurfer</option>
        </select>
      </label>
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : (
        data?.prediction && (
          <>
            <p>
              Mode: {data.prediction.mode} · Model:{" "}
              {data.prediction.modelVersion} · Anatomy used:{" "}
              {data.prediction.usedMri ? "Yes" : "No"} · FastSurfer QC:{" "}
              {data.qc}
            </p>
            <dl>
              {["12", "24", "36"].map((horizon) => (
                <div key={horizon}>
                  <dt>{horizon}-month experimental risk</dt>
                  <dd>
                    {data.prediction.probabilities[horizon] == null
                      ? "Unavailable"
                      : `${(data.prediction.probabilities[horizon]! * 100).toFixed(1)}%`}
                  </dd>
                </div>
              ))}
            </dl>
            <p>
              Uncalibrated estimates; no independently validated forecast model
              is available.
            </p>
            {data.prediction.warnings.map((warning) => (
              <p className="warning-text" key={warning}>
                {warning}
              </p>
            ))}
            {data.anatomy && (
              <details>
                <summary>Reviewed anatomical volumes (mm³)</summary>
                <dl>
                  {Object.entries(data.anatomy).map(([name, value]) => (
                    <div key={name}>
                      <dt>{name}</dt>
                      <dd>{value.toFixed(1)} mm³</dd>
                    </div>
                  ))}
                </dl>
              </details>
            )}
            <details>
              <summary>Feature associations, not causal explanations</summary>
              <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
                {JSON.stringify(data.prediction.explanation, null, 2)}
              </pre>
            </details>
          </>
        )
      )}
    </section>
  );
}
