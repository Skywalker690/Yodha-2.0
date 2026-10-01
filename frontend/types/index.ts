export type Mode = "demo" | "precomputed" | "inference";
export type Result = {
  patientId: string;
  visitIds: string[];
  riskScores: number[];
  daysFromBaseline: number[];
  biomarkers: { foregroundFraction: number[]; featureChange: number[] };
  outputMode: Mode;
  confidence: number | null;
  caveats: string[];
  modelVersion: string;
  selectedVisit: string;
  volumeOverlaysReady?: boolean;
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
  status: string;
  database: string;
  worker: string;
  modelVersion: string;
  storage: string;
};
