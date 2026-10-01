import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from src.common import CLINICAL, VERSION, write_json
from src.contracts import PredictionRequest, PredictionResult
from src.data.labels import label_sequence
from src.data.preprocess_mri import convert_native, inspect_mri
from src.data.split import split_patients
from src.fastsurfer.feature_map import FEATURE_SET, VOLUME_LABELS
from src.fastsurfer.parse_stats import parse_stats
from src.fastsurfer.runner import docker_command
from src.risk.baseline import fit_head, monotonic, score
from src.risk.evaluate import evaluate, metrics
from src.risk.predict import predict
from src.risk.train import train


@pytest.mark.parametrize(
    "days,cdr,expected",
    [
        ([0, 100], [0, 0.5], (1, 1, 1)),
        ([0, 400], [0, 0.5], (None, 1, 1)),
        ([0, 800], [0, 0.5], (None, None, 1)),
        ([0, 400, 1000], [0, 0, 0.5], (0, None, 1)),
        ([0, 1200], [0, 0], (0, 0, 0)),
        ([0, 200], [0, 0], (None, None, None)),
        ([0, 365.25], [0, 0.5], (1, 1, 1)),
        ([0, 365.26], [0, 0.5], (None, 1, 1)),
        ([0, 100, 400], [0, 0.5, 0], (1, 1, 1)),
    ],
)
def test_censoring(days, cdr, expected):
    result = label_sequence(days, cdr)
    assert tuple(result[f"y{h}"] for h in (12, 24, 36)) == expected


@pytest.mark.parametrize(
    "days,cdr", [([0, 0], [0, 0]), ([0, -1], [0, 0]), ([1], [0]), ([0], [0.5]), ([0, 100], [0, 9])]
)
def test_invalid_labels(days, cdr):
    with pytest.raises(ValueError):
        label_sequence(days, cdr)


def test_split_deterministic_and_complete():
    labels = pd.DataFrame(
        {"patient_id": [f"S{i}" for i in range(30)], "event_observed": [i % 2 for i in range(30)]}
    )
    one = split_patients(labels, 123)
    assert one.equals(split_patients(labels.sample(frac=1), 123))
    assert not one.patient_id.duplicated().any()
    assert set(one.patient_id) == set(labels.patient_id)
    assert set(one.split) == {"train", "validation", "test"}


def test_model_serialization_uses_training_statistics():
    x = np.array([[1, 2], [2, np.nan], [5, 8], [6, 9]])
    y = np.array([0, 0, 1, 1])
    head = fit_head(x, y, 0.1, 123)
    assert head["medians"] == [3.5, 8]
    saved = json.loads(json.dumps(head))
    assert np.array_equal(score(head, x), score(saved, x))
    assert np.isfinite(score(head, np.array([[1000, np.nan]]))).all()


def test_monotonic_nulls():
    assert monotonic({"12": 0.8, "24": None, "36": 0.2}) == {"12": 0.8, "24": None, "36": 0.8}


def stats_text():
    header = "# TableCol 4 ColHeader Volume_mm3\n# TableCol 4 Units mm^3\n# ColHeaders Index SegId NVoxels Volume_mm3 StructName\n"
    return header + "\n".join(
        f"{i} {label} 100 1000 {name}" for i, (label, name) in enumerate(VOLUME_LABELS.values())
    )


def test_stats_exact_labels_units_and_total(tmp_path):
    path = tmp_path / "aseg.stats"
    path.write_text(stats_text())
    assert parse_stats(path)["hippocampus_total_mm3"] == 2000


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s.replace("mm^3", "unitless"),
        lambda s: s.replace("Left-Hippocampus", "Left-Amygdala"),
        lambda s: s.replace("100 1000", "100 nan"),
        lambda s: s.replace("100 1000", "100 -1"),
        lambda s: "\n".join(s.splitlines()[:-1]),
        lambda s: s + "\n0 17 100 1000 Left-Hippocampus",
    ],
)
def test_stats_fail_closed(tmp_path, mutation):
    path = tmp_path / "stats"
    path.write_text(mutation(stats_text()))
    with pytest.raises(ValueError):
        parse_stats(path)


def test_docker_command_readonly_isolated_and_pinned(tmp_path):
    cfg = {
        "image": "deepmi/fastsurfer:cuda-v2.5.4",
        "output_dir": str(tmp_path),
        "device": "cuda",
        "viewagg_device": "cpu",
        "threads": 4,
        "surface": False,
    }
    command = docker_command(cfg, "SCAN_1", tmp_path / "native/t1.nii.gz", tmp_path)
    assert "--gpus" in command and "--seg_only" in command and "none" in command
    assert any("target=/input,readonly" in part for part in command)
    cfg["image"] = "deepmi/fastsurfer:latest"
    with pytest.raises(ValueError):
        docker_command(cfg, "SCAN_1", tmp_path / "t1.nii.gz", tmp_path)


def test_physical_conversion_preserves_source(mri, tmp_path):
    source = mri.read_bytes()
    assert inspect_mri(mri)["spacing_mm"] == [1, 1, 1]
    destination = tmp_path / "converted.nii.gz"
    convert_native(mri, destination)
    assert mri.read_bytes() == source
    assert destination.exists()


@pytest.fixture
def synthetic_study(tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir()
    baseline, labels, split, features = [], [], [], []
    for i in range(36):
        patient = f"SYNTHETIC_{i:02}"
        values = {
            "age_years": 65 + i % 20,
            "sex": i % 2,
            "education": 12,
            "ses": 2,
            "mmse": 29 - i % 4,
            "cdr": 0,
            "etiv": 1500,
            "nwbv": 0.75,
            "asf": 1.1,
        }
        baseline.append({"patient_id": patient, "scan_id": f"SCAN_{i}", **values})
        labels.append({"patient_id": patient, "y12": i % 2, "y24": i % 2, "y36": i % 2})
        split.append(
            {"patient_id": patient, "split": "train" if i < 24 else ("validation" if i < 30 else "test")}
        )
        features.append(
            {
                "patient_id": patient,
                "scan_id": f"SCAN_{i}",
                "qc": "passed",
                "feature_set_version": FEATURE_SET,
                "fastsurfer_version": "2.5.4",
                **{f: 1000 + i for f in VOLUME_LABELS},
            }
        )
    for name, rows in (
        ("baseline", baseline),
        ("labels", labels),
        ("split", split),
        ("fastsurfer_features", features),
    ):
        pd.DataFrame(rows).to_csv(processed / f"{name}.csv", index=False)
    return {
        "processed_dir": str(processed),
        "artifact_dir": str(tmp_path / "artifacts"),
        "target": "observed_cdr_conversion",
        "seed": 42,
        "regularization_c": 0.1,
        "min_train_per_class": 5,
        "min_validation_per_class": 2,
    }


def test_full_clinical_and_matched_training_evaluation(synthetic_study):
    cfg = synthetic_study
    assert train(cfg, "clinical")["available_horizons"] == ["12", "24", "36"]
    train(cfg, "clinical", matched=True)
    train(cfg, "clinical_fastsurfer")
    a = evaluate(cfg, "clinical", matched=True)
    b = evaluate(cfg, "clinical_fastsurfer")
    assert a["support"] == b["support"]
    assert a["split_metrics"]["test"]["12"]["subjects"] == 6
    row = pd.read_csv(Path(cfg["processed_dir"]) / "baseline.csv").iloc[0]
    request = {"patient_id": row["patient_id"], "baseline": {f: float(row[f]) for f in CLINICAL}}
    result = predict(request, artifact_dir=Path(cfg["artifact_dir"]))
    assert result.status == "ok" and result.mode == "live" and not result.used_mri
    assert "training cases are in-sample" in " ".join(result.warnings)
    request["baseline"]["future_mmse"] = 25
    assert predict(request, artifact_dir=Path(cfg["artifact_dir"])).status == "unavailable"


def test_unavailable_anatomy_never_falls_back(synthetic_study):
    cfg = synthetic_study
    train(cfg, "clinical_fastsurfer")
    row = pd.read_csv(Path(cfg["processed_dir"]) / "baseline.csv").iloc[0]
    request = {"patient_id": row["patient_id"], "baseline": {f: float(row[f]) for f in CLINICAL}}
    result = predict(request, "clinical_fastsurfer", artifact_dir=Path(cfg["artifact_dir"]))
    assert result.status == "unavailable" and all(v is None for v in result.probabilities.values())


def test_artifact_changed_source_refuses_evaluation(synthetic_study):
    cfg = synthetic_study
    train(cfg, "clinical")
    path = Path(cfg["processed_dir"]) / "baseline.csv"
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="source changed"):
        evaluate(cfg, "clinical")


def test_insufficient_classes_never_become_probability(synthetic_study):
    cfg = synthetic_study
    path = Path(cfg["processed_dir"]) / "labels.csv"
    labels = pd.read_csv(path)
    labels["y12"] = 0
    labels.to_csv(path, index=False)
    result = train(cfg, "clinical")
    assert result["available_horizons"] == ["24", "36"]


def test_no_test_class_auc_is_null():
    result = metrics(np.array([0, 0]), np.array([0.1, 0.2]), 0.5)
    assert result["roc_auc"] is None and result["sensitivity"] is None


def test_predict_invalid_bundle(tmp_path):
    write_json(tmp_path / "clinical.json", {"version": VERSION})
    request = {"patient_id": "FAKE", "baseline": {f: 0 for f in CLINICAL}}
    assert predict(request, artifact_dir=tmp_path).status == "unavailable"


def test_request_nonfinite_and_result_monotonic():
    with pytest.raises(ValidationError):
        PredictionRequest(patient_id="fake", baseline={"mmse": float("inf")})
    with pytest.raises(ValidationError):
        PredictionResult(
            status="ok",
            mode="live",
            model_version=VERSION,
            preprocessing_version="test",
            probabilities={"12": 0.8, "24": 0.2, "36": None},
            raw_probabilities={"12": .8, "24": .2, "36": None},
            calibration={"12": "uncalibrated", "24": "uncalibrated", "36": "unavailable"},
        )


def test_forecast_endpoint_ownership_and_no_training(authenticated):
    patient = authenticated.post("/patients", json={"code": "FORECAST_SYNTHETIC"}).json()
    result = authenticated.get(f"/patients/{patient['id']}/forecast")
    assert result.status_code == 200 and result.json()["prediction"]["status"] == "unavailable"
    assert "source_mri_path" not in result.text
    authenticated.post("/auth/logout")
    assert authenticated.get(f"/patients/{patient['id']}/forecast").status_code == 401
    authenticated.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert authenticated.get(f"/patients/{patient['id']}/forecast").status_code == 404


def test_optional_cnn_masked_loss():
    import torch
    from src.mri.model import masked_loss

    logits = torch.zeros((1, 3), requires_grad=True)
    labels = torch.tensor([[1.0, float("nan"), 0.0]])
    loss = masked_loss(logits, labels)
    loss.backward()
    assert logits.grad[0, 1] == 0
    with pytest.raises(ValueError):
        masked_loss(logits, torch.full((1, 3), float("nan")))


def test_streamlit_calls_shared_adapter_with_synthetic_data(synthetic_study, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from src import common

    cfg = synthetic_study
    train(cfg, "clinical")
    baseline = pd.read_csv(Path(cfg["processed_dir"]) / "baseline.csv")
    baseline[["patient_id", "scan_id"]].assign(source_mri_path=None).to_csv(
        Path(cfg["processed_dir"]) / "manifest.csv", index=False
    )
    monkeypatch.setattr(common, "config", lambda path: cfg)
    application = AppTest.from_file(str(common.ROOT / "src/app/app.py"), default_timeout=15).run()
    assert not application.exception
    application.button[0].click().run()
    assert not application.exception
    assert len(application.metric) == 3
    assert all(m.value != "Unavailable" for m in application.metric)


def test_adapter_import_does_not_load_training_or_gpu_packages():
    import subprocess
    import sys

    command = (
        "import src.risk.predict,sys; assert 'torch' not in sys.modules; assert 'sklearn' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", command], check=True, capture_output=True, timeout=20)
