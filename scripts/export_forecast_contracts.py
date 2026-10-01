"""Mechanical export of the authoritative typed forecast schemas."""

from src.common import ROOT, write_json
from src.contracts import PredictionRequest, PredictionResult
from src.fastsurfer.feature_map import FEATURE_SET, VOLUME_LABELS


if __name__ == "__main__":
    write_json(ROOT / "contracts/prediction.schema.json", PredictionResult.model_json_schema())
    write_json(ROOT / "contracts/request.schema.json", PredictionRequest.model_json_schema())
    write_json(
        ROOT / "contracts/fastsurfer_feature_schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["patient_id", "scan_id", "fastsurfer_version", "feature_set_version", "qc"],
            "properties": {
                "patient_id": {"type": "string"},
                "scan_id": {"type": "string"},
                "fastsurfer_version": {"type": "string"},
                "feature_set_version": {"const": FEATURE_SET},
                "qc": {"enum": ["passed", "pending_review", "failed", "unavailable"]},
                **{
                    f: {"type": ["number", "null"], "exclusiveMinimum": 0, "description": "Volume mm^3"}
                    for f in VOLUME_LABELS
                },
            },
        },
    )
