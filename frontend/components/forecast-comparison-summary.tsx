"use client";

import { useResource } from "@/lib/use-resource";

type Comparison = {
  deformation: { medianMm: number; p95Mm: number; maximumMm: number };
  regions: {
    region: string;
    observedMaskMm3: number;
    predictedMaskMm3: number;
    maskChangePercent: number;
    scalarChangePercent: number;
  }[];
};

export function ForecastComparisonSummary({
  analysisId,
}: {
  analysisId: string;
}) {
  const comparison = useResource<Comparison>(
    `/analysis/${analysisId}/forecast-comparison`,
  );
  const data = comparison.data;
  return (
    <section className="volume-help" aria-label="Actual forecast changes">
      <h3>What the model changed</h3>
      {comparison.loading ? (
        <p role="status">Measuring the saved deformation and masks…</p>
      ) : comparison.error || !data?.regions?.length ? (
        <p role="status">
          {comparison.error || "Change measurements unavailable."}
        </p>
      ) : (
        <>
          <p>
            Brain displacement: median{" "}
            <strong>{data.deformation.medianMm.toFixed(2)} mm</strong>; 95th
            percentile <strong>{data.deformation.p95Mm.toFixed(2)} mm</strong>.
            Small displacements can leave the categorical masks unchanged.
          </p>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Region</th>
                  <th>Input mask mm³</th>
                  <th>Predicted mask mm³</th>
                  <th>Mask volume change</th>
                  <th>Separate scalar estimate</th>
                </tr>
              </thead>
              <tbody>
                {data.regions.map((r) => (
                  <tr key={r.region}>
                    <td>
                      {r.region.includes("left")
                        ? "Left hippocampus"
                        : "Right hippocampus"}
                    </td>
                    <td>{r.observedMaskMm3.toFixed(1)}</td>
                    <td>{r.predictedMaskMm3.toFixed(1)}</td>
                    <td>{r.maskChangePercent.toFixed(2)}%</td>
                    <td>{r.scalarChangePercent.toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>
            Mask volume change describes the displayed spatial output. The
            scalar estimate is a different model output; disagreement is a model
            limitation. These are unvalidated estimates.
          </p>
        </>
      )}
    </section>
  );
}
