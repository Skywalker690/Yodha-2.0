export type Mode = "demo" | "precomputed" | "inference" | "trained" | "anatomy";
export type AnatomyVisit = {
  visitId: string;
  daysFromBaseline: number;
  qc: "pending_review" | "automated_checks_only" | "passed";
  method: string;
  fastsurferVersion: string;
  dictionaryVersion: string;
  sourceSha256: string;
  segmentationSha256: string;
  statisticsSha256: string;
  containerDigest: string;
  reviewerId?: string | null;
  reviewedAt?: string | null;
  volumesMm3: Record<string, number>;
  maskVolumesMm3: Record<string, number>;
  hippocampalAsymmetryPercent: number;
  etivMm3: number | null;
  headSizeRatios: Record<string, number>;
  ratings: {
    status: string;
    method: string;
    mtaLeft: number | null;
    mtaRight: number | null;
    posteriorAtrophy: number | null;
    warnings: string[];
    provenanceSha256?: string | null;
    reviewerId?: string | null;
    reviewedAt?: string | null;
  };
};
export type AnatomyResult = {
  version: string;
  visits: AnatomyVisit[];
  changes: {
    earlierVisitId: string;
    laterVisitId: string;
    elapsedDays: number;
    status: string;
    regions: Record<
      string,
      {
        absoluteMm3: number;
        percent: number;
        annualizedMm3: number;
        annualizedPercent: number;
      }
    >;
  }[];
  signConvention: string;
  forecast: {
    experimental?: boolean;
    displayMagnification?: number | null;
    displayMode?: "hippocampus_scalar" | null;
    displayRegions?: Record<string, {
      inputMaskMm3: number;
      displayMaskMm3: number;
      scalarChangePercent: number;
      displayChangePercent: number;
    }> | null;
    trainingSubjectCount?: number | null;
    status: "unavailable" | "available";
    cutoffVisitId: string;
    intervalDays: number;
    warnings: string[];
    volumesMm3?: Record<string, number> | null;
    predictionIntervals?: Record<string, [number, number]> | null;
    intervalEvidence?: {
      level: number;
      evaluated: boolean;
      subjects: number;
      method: string;
    } | null;
    spatialModelVersion?: string | null;
    modelSha256?: string | null;
    releaseSha256?: string | null;
    featureContract?: string | null;
    referenceSha256?: string | null;
    referenceProfileId?: string | null;
    featureAvailability?: {
      visitId: string;
      nwbvAgeZ: { status: string; zScore: number | null; referencePolicy?: string };
      MMSE: { status: string };
    }[] | null;
    artifacts: {
      name: string;
      kind: "mri" | "labels" | "field" | "mesh";
      sha256: string;
    }[];
  };
};
export type NwbvAgeReference = {
  visitId: string;
  status: string;
  ageYears: number | null;
  nwbvFraction: number | null;
  zScore: number | null;
  relativeVolumeBand: string | null;
  referenceBin?: { n: number } | null;
  reason?: string | null;
};
export type TrainedPrediction = {
  target: "observed_cdr_increase";
  score: number;
  decisionThreshold: number;
  predictedIncrease: boolean;
  checkpointSha256: string;
  cohortRole: "train" | "validation" | "test" | "unassigned";
  trainingSubjects: number;
  trainingVisits: number;
  testSubjects: number;
  testAccuracy: number;
  testBalancedAccuracy: number;
  testRocAuc: number;
  majorityBaselineAccuracy: number;
  qualityStatus: "experimental_poor_generalization";
};
export type Result = {
  patientId: string;
  visitIds: string[];
  riskScores: number[];
  daysFromBaseline: number[];
  biomarkers: {
    foregroundFraction: number[];
    featureChange: number[];
    nwbvAgeReferenceV1?: NwbvAgeReference;
  };
  outputMode: Mode;
  confidence: number | null;
  caveats: string[];
  modelVersion: string;
  selectedVisit: string;
  volumeOverlaysReady?: boolean;
  prediction?: TrainedPrediction;
  anatomy?: AnatomyResult | null;
};
export type Analysis = {
  id: string;
  patientId: string;
  visitId: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress: number;
  stage: string;
  outputMode: Mode;
  modelVersion: string;
  score: number | null;
  confidence: number | null;
  resultJson: Result | null;
  error: string | null;
  createdAt: string;
};
export type Visit = {
  id: string;
  label: string;
  daysFromBaseline: number;
  hasMri: boolean;
  previewUrl: string | null;
  volumeUrl?: string | null;
  metadata: {
    nWBV?: number;
    eTIV?: number;
    CDR?: number;
    MMSE?: number;
    shape?: number[];
    source?: string;
  };
};
export type Patient = {
  servingPolicy?: "ml_only" | "research";
  id: string;
  code: string;
  age: number | null;
  sex: string | null;
  notes: string;
  source: string;
  createdAt: string;
  visitCount: number;
  visits: Visit[];
  latestAnalysis: Analysis | null;
  latestCompleted: Analysis | null;
  latestAnatomy?: Analysis | null;
  completedAnatomy?: Analysis | null;
};
export type Report = {
  id: string;
  patientId: string;
  patientCode: string;
  analysisId: string;
  outputMode: Mode;
  createdAt: string;
  downloadUrl: string;
};
export type Health = {
  servingPolicy?: "ml_only" | "research";
  forecastReadiness?: {
    ready: boolean;
    reasons: string[];
    clinical_validation: boolean;
  };
  status: string;
  database: string;
  worker: string;
  modelVersion: string;
  baselineModelVersion?: string;
  trainedModelVersion?: string | null;
  trainedModelReady?: boolean;
  storage: string;
};
