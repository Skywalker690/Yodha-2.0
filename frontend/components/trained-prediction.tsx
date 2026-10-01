"use client";
import { percent } from "@/lib/utils";
import type { Result, TrainedPrediction } from "@/types";
import { ErrorState } from "./common";

const cohortCaveats: Record<TrainedPrediction["cohortRole"], string> = {
  train:
    "Training member: this is an in-sample demonstration, not accuracy evidence.",
  validation:
    "Validation member: this cohort selected the checkpoint and threshold; this is not independent accuracy evidence.",
  test: "Test member: this is a reused holdout, not independent final validation.",
  unassigned:
    "Unassigned subject: outside the saved split; generalization to this subject or a different acquisition domain is unverified.",
};

export function formatModelScore(value: number | null | undefined): string {
  return typeof value === "number" &&
    Number.isFinite(value) &&
    value >= 0 &&
    value <= 1
    ? value.toFixed(4)
    : "Unavailable";
}

function metricPercent(value: number): string {
  return formatModelScore(value) === "Unavailable"
    ? "Unavailable"
    : percent(value);
}

export function TrainedPredictionPanel({ result }: { result: Result }) {
  const prediction = result.prediction;
  if (
    !prediction ||
    formatModelScore(prediction.score) === "Unavailable" ||
    formatModelScore(prediction.decisionThreshold) === "Unavailable"
  ) {
    return (
      <ErrorState message="Experimental trained prediction unavailable. Run trained analysis again; no baseline score has been substituted." />
    );
  }
  return (
    <div className="prediction-panel">
      <div className="prediction-warning" role="note">
        <strong>Experimental · poor generalization</strong>
        <p>
          Research Prototype · Not a medical diagnosis. This checkpoint does not
          establish reliable prediction accuracy.
        </p>
      </div>
      <dl className="prediction-summary">
        <div>
          <dt>Observed-CDR-increase model score (0–1)</dt>
          <dd className="current-risk">{formatModelScore(prediction.score)}</dd>
        </div>
        <div>
          <dt>Saved decision threshold</dt>
          <dd>{formatModelScore(prediction.decisionThreshold)}</dd>
        </div>
        <div>
          <dt>Model classification</dt>
          <dd>
            {prediction.predictedIncrease
              ? "Observed CDR increase"
              : "No observed CDR increase"}
          </dd>
        </div>
      </dl>
      <p>
        One uncalibrated retrospective score for the completed{" "}
        {result.visitIds.length}-visit sequence (day{" "}
        {result.daysFromBaseline[0]}–{result.daysFromBaseline.at(-1)}). It uses
        all included visits, not just the selected historical scan. It is not a
        future Alzheimer&apos;s probability; no per-visit neural trajectory is
        available.
      </p>
      <h3>Recorded test evidence · {prediction.testSubjects} subjects</h3>
      <dl className="prediction-evidence">
        <div>
          <dt>Test accuracy</dt>
          <dd>{metricPercent(prediction.testAccuracy)}</dd>
        </div>
        <div>
          <dt>Test balanced accuracy</dt>
          <dd>{metricPercent(prediction.testBalancedAccuracy)}</dd>
        </div>
        <div>
          <dt>Test ROC-AUC</dt>
          <dd>{formatModelScore(prediction.testRocAuc)}</dd>
        </div>
        <div>
          <dt>Majority-class baseline accuracy</dt>
          <dd>{metricPercent(prediction.majorityBaselineAccuracy)}</dd>
        </div>
      </dl>
      <p>
        This small test cohort is a reused holdout, not independent final
        validation. These metrics are not confidence in this individual result.
      </p>
      <h3>Checkpoint provenance</h3>
      <p>
        Trained on {prediction.trainingSubjects} subjects and{" "}
        {prediction.trainingVisits} visits. Cohort membership:{" "}
        <strong>{prediction.cohortRole}</strong>.
      </p>
      <p>{cohortCaveats[prediction.cohortRole]}</p>
      <p>
        Accuracy on training members does not demonstrate generalization. Other
        subjects and acquisition domains remain unvalidated. The saved cohort
        and checkpoint have not been changed to improve these numbers.
      </p>
      <p>
        Model version: <code>{result.modelVersion}</code>
        <br />
        Checkpoint SHA-256:{" "}
        <code className="checkpoint-hash">{prediction.checkpointSha256}</code>
      </p>
    </div>
  );
}
