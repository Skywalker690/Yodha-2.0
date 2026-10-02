"""Offline commands must preserve the importer account boundary."""

import json
import time
import sys

import pytest
import numpy as np

from backend.app.core.config import get_settings
from backend.app.models import Analysis, Patient, Visit
from backend.app.services.storage import resolve_key
from scripts.train_anatomy import export_study, queue_cohort
from src.common import write_json


def test_reuse_requires_unchanged_physical_source_and_target_records():
    import copy
    from scripts.train_anatomy import same_registration_sources

    original = [
        {
            "labels_sha256": "a" * 64,
            "mri_path": "same-source.nii.gz",
            "measurement": {
                "qc": "pending_review",
                "ratings": {"status": "pending_alignment_qc"},
                "source_sha256": "b" * 64,
                "volumes_mm3": {"region": 5000},
            },
        }
    ]
    current = copy.deepcopy(original)
    current[0]["measurement"].update(qc="passed", ratings={"status": "ok"}, reviewer_id="reviewer")
    assert same_registration_sources(original, current)
    current[0]["labels_sha256"] = "c" * 64
    assert not same_registration_sources(original, current)


def test_frozen_source_cutoff_excludes_user_added_visits(tmp_path):
    from scripts.train_anatomy import cohort_days
    from src.common import sha256

    split = tmp_path / "subject_split.csv"
    split.write_text("subject_id,split\nsubject,train\n")
    write_json(
        tmp_path / "cohort.json",
        {
            "split_sha256": sha256(split),
            "subjects": [
                {
                    "subject_id": "subject",
                    "visits": [
                        {"days_from_baseline": 0},
                        {"days_from_baseline": 500},
                        {"days_from_baseline": 1000},
                    ],
                }
            ],
        },
    )
    assert cohort_days(split, "subject") == {0, 500, 1000}
    split.write_text("changed")
    with pytest.raises(ValueError, match="split changed"):
        cohort_days(split, "subject")


def test_completed_history_preparation_preserves_full_cohort_indices(tmp_path, monkeypatch):
    from scripts import train_anatomy
    from ml.anatomy import study

    exported = {
        "synthetic": False,
        "allow_unreviewed_research": True,
        "split": {"not_finished": "train", "finished": "selection"},
        "blocked_subjects": ["not_finished"],
        "subjects": [{"subject_id": "finished", "visits": [{"scan": n} for n in range(3)]}],
    }
    export_path, output = tmp_path / "export.json", tmp_path / "study"
    write_json(export_path, exported)
    prepared = []

    def prepare(history, target, directory, size, **kwargs):
        directory.mkdir(parents=True)
        write_json(directory / "case.json", {"source_records": [*history, target]})
        prepared.append(directory.name)

    monkeypatch.setattr(study, "prepare_case", prepare)
    arguments = [
        "train_anatomy",
        "prepare",
        "--export",
        str(export_path),
        "--output",
        str(output),
        "--allow-unreviewed-research",
        "--completed-only",
        "--resume",
    ]
    monkeypatch.setattr(sys, "argv", arguments)
    train_anatomy.main()
    assert prepared == ["case-1-2"]
    assert not (output / "study.json").exists()
    progress = json.loads((output / "preparation-progress.json").read_text())
    assert progress["cases"][0]["relative_path"] == "case-1-2/case.json"
    monkeypatch.setattr(
        study,
        "load_case",
        lambda path, **kwargs: (
            {"source_records": exported["subjects"][0]["visits"], "allow_unreviewed_research": True},
            None,
            {"images": np.empty((6, 96, 96, 96), dtype=np.uint8)},
        ),
    )
    train_anatomy.main()
    assert prepared == ["case-1-2"]
    exported["subjects"][0]["visits"][0]["scan"] = 99
    write_json(export_path, exported)
    monkeypatch.setattr(
        study,
        "load_case",
        lambda path, **kwargs: (
            {"source_records": [{"scan": n} for n in range(3)], "allow_unreviewed_research": True},
            None,
            {"images": np.empty((6, 96, 96, 96), dtype=np.uint8)},
        ),
    )
    with pytest.raises(ValueError, match="immutable export"):
        train_anatomy.main()


def test_training_runtime_is_pinned_and_study_mount_is_read_only():
    from pathlib import Path
    from scripts.run_anatomy_training import gpu_training_command
    from src.common import ROOT

    with pytest.raises(ValueError, match="immutable"):
        gpu_training_command("mutable:tag", Path("study.json"), Path("candidate"), 20)
    command = gpu_training_command(
        "sha256:" + "a" * 64,
        ROOT / "artifacts/study/study.json",
        ROOT / "artifacts/run/candidate",
        20,
    )
    assert "none" == command[command.index("--network") + 1]
    assert f"type=bind,source={ROOT},target=/workspace,readonly" in command
    assert "/workspace/artifacts/study/study.json" in command
    assert "/output/candidate" in command
    assert "--device" in command and "cuda" in command


def test_frozen_cohort_ignores_duplicate_code_under_another_owner(session_factory, monkeypatch, tmp_path):
    from backend.app.db import session
    from backend.app.services import analysis
    from ml.anatomy import study

    monkeypatch.setattr(session, "SessionLocal", session_factory)
    monkeypatch.setattr(get_settings(), "seed_email", "a@example.test")
    monkeypatch.setattr(study, "frozen_split", lambda _: {"OAS2_SYNTHETIC": "train"})
    split_path = tmp_path / "synthetic.csv"
    split_path.write_text("subject_id,split\nOAS2_SYNTHETIC,train\n")
    with session_factory() as db:
        for owner, patient_id in (("researcher-b", "other-case"), ("researcher-a", "imported-case")):
            db.add(Patient(id=patient_id, owner_id=owner, code="OAS2_SYNTHETIC", source="oasis-2"))
            db.flush()
            for index in range(3):
                db.add(
                    Visit(
                        id=f"{patient_id}-{index}",
                        patient_id=patient_id,
                        label=f"Visit {index}",
                        days_from_baseline=index * 500,
                        mri_key=f"raw/{patient_id}-{index}.nii.gz",
                    )
                )
        db.flush()
        # This unparseable record must never be considered as the imported study.
        db.add(
            Analysis(
                id="other-completed",
                patient_id="other-case",
                visit_id="other-case-2",
                output_mode="anatomy",
                status="completed",
                result_json={"not": "an anatomy result"},
            )
        )
        db.add(
            Analysis(
                id="own-first-only",
                patient_id="imported-case",
                visit_id="imported-case-0",
                output_mode="anatomy",
                status="completed",
                result_json={"partial": "not a full history"},
            )
        )
        db.commit()
    from scripts import run_anatomy_training as coordinator

    monkeypatch.setattr(coordinator, "SessionLocal", session_factory)
    monkeypatch.setattr(coordinator, "frozen_split", study.frozen_split)
    state = coordinator.processing_state(split_path)
    assert state["counts"]["completed"] == 0
    assert state["counts"]["missing"] == 1
    queued = []
    monkeypatch.setattr(analysis, "enqueue", lambda db, patient, visit, mode: queued.append(patient.id))
    write_json(
        resolve_key("worker-capabilities.json"),
        {"timestamp": time.time(), "capabilities": ["longitudinal-anatomy-v1"]},
    )
    assert queue_cohort(split_path, limit=1)["queued_subjects"] == 1
    assert queued == ["imported-case"]
    destination = tmp_path / "export.json"
    assert export_study(split_path, destination)["ready_subjects"] == 0
    assert json.loads(destination.read_text())["blocked_subjects"] == ["OAS2_SYNTHETIC"]
