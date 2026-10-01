"""Loopback-only study dashboard. No GPU imports, processing or training in UI."""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import streamlit as st

from src.app.charts import trajectory
from src.common import CLINICAL, config, read_table, resolve
from src.fastsurfer.feature_map import ANATOMY, FEATURE_SET
from src.risk.predict import predict

st.set_page_config(page_title="NeuroPredict baseline forecast", layout="wide")
st.title("NeuroPredict baseline forecast")
st.warning(
    "Research Prototype — Not a medical diagnosis. Outcome: first observed CDR > 0 after a CDR-zero baseline."
)
cfg = config("configs/experiment.yaml")
directory = resolve(cfg["processed_dir"])
if not (directory / "baseline.csv").exists():
    st.info("Prepare the baseline cohort with the documented offline commands first.")
    st.stop()
baseline = read_table(directory / "baseline.csv")
aliases = {"CASE-" + hashlib.sha256(p.encode()).hexdigest()[:10]: p for p in baseline["patient_id"]}
case = st.selectbox("Local de-identified OASIS research case", list(aliases))
patient = aliases[case]
row = baseline[baseline["patient_id"] == patient].iloc[0]
st.subheader("Baseline clinical measurements")
st.dataframe(row[list(CLINICAL)].rename("Value"), use_container_width=True)
st.caption(
    "Sex encoding: 0 female, 1 male. eTIV mm³, nWBV unitless, ASF unitless. Later visits are not predictors."
)
manifest = read_table(directory / "manifest.csv")
scan = manifest[manifest["patient_id"] == patient].iloc[0]
st.subheader("MRI and FastSurfer quality control")
st.write("Baseline MRI availability:", "present" if isinstance(scan["source_mri_path"], str) else "missing")
request = {
    "patient_id": patient,
    "baseline": {f: None if np.isnan(row[f]) else float(row[f]) for f in CLINICAL},
}
if (directory / "fastsurfer_features.csv").exists():
    features = read_table(directory / "fastsurfer_features.csv")
    selected = features[features["patient_id"] == patient]
    if len(selected):
        anatomy = selected.iloc[0]
        st.write("FastSurfer version:", anatomy["fastsurfer_version"], "QC:", anatomy["qc"])
        if anatomy["qc"] in ("passed", "pending_review"):
            st.dataframe(anatomy[list(ANATOMY)].rename("Volume mm³"), use_container_width=True)
            request.update(
                fastsurfer_features={f: float(anatomy[f]) for f in ANATOMY},
                fastsurfer_version=str(anatomy["fastsurfer_version"]),
                feature_set_version=FEATURE_SET,
                scan_id=anatomy["scan_id"],
                qc=anatomy["qc"],
            )
        else:
            st.info("Anatomical measurements unavailable. No substitute values are generated.")
else:
    st.info("FastSurfer processing has not completed; anatomy is unavailable.")
kind = st.selectbox("Model tier", ["clinical", "clinical_matched", "clinical_fastsurfer"])
if st.button("Predict baseline outcome"):
    result = predict(request, kind, artifact_dir=resolve(cfg["artifact_dir"]))
    st.write(
        "Status:",
        result.status,
        "Mode:",
        result.mode,
        "Model:",
        result.model_version,
        "Uses anatomy:",
        result.used_mri,
    )
    columns = st.columns(3)
    for column, (horizon, value) in zip(columns, result.probabilities.items()):
        column.metric(f"{horizon} months", "Unavailable" if value is None else f"{value:.1%}")
    chart = trajectory(result.probabilities)
    if len(chart):
        st.line_chart(chart.set_index("Month"))
    for warning in result.warnings:
        st.caption(warning)
    st.write("Calibration:", result.calibration)
    if result.missing_fields:
        st.write("Missing recorded fields:", result.missing_fields)
    with st.expander("Feature explanations — associations, not causes"):
        st.json(result.explanation)
st.subheader("Held-out evidence")
for name in ("clinical", "clinical_matched", "clinical_fastsurfer"):
    evaluation = resolve(cfg["artifact_dir"]) / f"{name}_evaluation.json"
    if evaluation.exists():
        with st.expander(f"{name} metrics and sample counts"):
            st.json(json.loads(evaluation.read_text()))
st.caption(
    "Compare clinical_matched vs clinical_fastsurfer only on identical reviewed cases. No automatic best-model claim."
)
