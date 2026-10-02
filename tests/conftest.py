import os
import tempfile
from pathlib import Path

# Configure before importing the application; production data is never used for unit tests.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ML_ONLY"] = "false"  # Retained legacy regression suite; strict serving has separate tests.
os.environ["JWT_SECRET"] = "test-only-" + "x" * 48
os.environ["SEED_PASSWORD"] = "test-only-password-1234"
os.environ["STORAGE_ROOT"] = tempfile.mkdtemp(prefix="neuropredict-tests-")

import nibabel as nib
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.security import hash_password
from backend.app.db.session import Base, get_db
from backend.app.main import app
from backend.app.models import User
from backend.app.workers import runner


@pytest.fixture
def session_factory(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add(
            User(
                id="researcher-a", email="a@example.test", password_hash=hash_password("correct-password-123")
            )
        )
        db.add(
            User(
                id="researcher-b", email="b@example.test", password_hash=hash_password("correct-password-123")
            )
        )
        db.commit()

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(runner, "SessionLocal", factory)
    yield factory
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def client(session_factory):
    from backend.app.api.routes import attempts

    attempts.clear()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated(client):
    response = client.post(
        "/auth/login", json={"email": "a@example.test", "password": "correct-password-123"}
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def mri(tmp_path: Path) -> Path:
    rng = np.random.default_rng(42)
    x, y, z = np.mgrid[-1:1:24j, -1:1:24j, -1:1:24j]
    data = (np.exp(-4 * (x * x + y * y + z * z)) + rng.random((24, 24, 24)) * 0.05).astype(np.float32)
    path = tmp_path / "scan.nii.gz"
    nib.save(nib.Nifti1Image(data, np.eye(4)), path)
    return path


@pytest.fixture
def trained_bundle_path(tmp_path: Path) -> Path:
    """Entirely synthetic bundle: never load production subjects in unit tests."""
    import hashlib
    import json

    import pandas as pd
    import torch

    from ml.multimodal import (
        EXCLUDED_FEATURES,
        MODEL_VERSION,
        DemographicPreprocessor,
        MultimodalClassifier,
        feature_names,
    )
    from ml.trained_inference import IMAGE_PREPROCESSING

    directory = tmp_path / "synthetic-trained-run"
    directory.mkdir()
    rows, counts, training_ids = [], {}, []
    for split, subjects, extra_visits, positives in [
        ("train", 40, 12, 6),
        ("validation", 8, 5, 2),
        ("test", 8, 0, 2),
    ]:
        count = 0
        for index in range(subjects):
            subject = f"SYNTH_{split}_{index}"
            if split == "train":
                training_ids.append(subject)
            for step in range(3 + int(index < extra_visits)):
                rows.append(
                    {
                        "subject_id": subject,
                        "visit_id": f"{subject}_V{step}",
                        "visit_index": step,
                        "days_from_baseline": step * 365,
                        "split": split,
                        "cdr": step * 0.5 if index < positives else 0.0,
                        "target": int(index < positives),
                    }
                )
                count += 1
        counts[split] = {"subjects": subjects, "visits": count, "positive_subjects": positives}
    manifest = directory / "subject_split.csv"
    pd.DataFrame(rows).to_csv(manifest, index=False)
    frame = pd.DataFrame(
        [
            {
                "Age": 70 + i,
                "EDUC": 12,
                "SES": 2,
                "MMSE": 28 - i,
                "eTIV": 1500,
                "nWBV": 0.75,
                "ASF": 1.1,
                "MR Delay": i * 365,
                "Visit": i + 1,
                "M/F": "F",
                "Hand": "R",
            }
            for i in range(3)
        ]
    )
    torch.manual_seed(42)
    model = MultimodalClassifier()
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "model_version": MODEL_VERSION,
        "target": "observed_cdr_increase",
        "feature_names": feature_names(),
        "image_preprocessing": IMAGE_PREPROCESSING,
        "excluded_input_fields": list(EXCLUDED_FEATURES),
        "demographic_preprocessor": DemographicPreprocessor.fit(frame).to_dict(),
        "split_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "metadata_sha256": "a" * 64,
        "split_counts": counts,
        "preprocessing_fit_subject_ids": training_ids,
        "preprocessing_fit_visits": 132,
        "decision_threshold": 0.51,
        "best_epoch": 1,
    }
    path = directory / "multimodal_model.pt"
    torch.save(checkpoint, path)
    metrics = {
        "model_version": MODEL_VERSION,
        "target": "observed_cdr_increase",
        "split_counts": counts,
        "best_epoch": 1,
        "epochs_completed": 15,
        "optimizer_steps": 150,
        "threshold_fit_split": "validation",
        "validation_selected_threshold": 0.51,
        "trainable_branch_weight_changes_l2": {
            name: 0.1 for name in ("encoder", "demographics", "lstm", "head")
        },
        "evaluation": {
            "test": {
                "at_validation_threshold": {
                    "subjects": 8,
                    "accuracy": 0.25,
                    "balanced_accuracy": 1 / 3,
                    "roc_auc": 1 / 12,
                }
            }
        },
        "majority_baseline": {"accuracy": 0.75},
    }
    (directory / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    (directory / "status.json").write_text(
        json.dumps({"status": "completed", "checkpoint_roundtrip": "passed"}), encoding="utf-8"
    )
    return path
