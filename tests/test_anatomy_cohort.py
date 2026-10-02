"""Rich-history membership and candidate-only review policy, using synthetic data."""

import pandas as pd
import pytest

from ml.anatomy.cohort import create_cohort
from ml.anatomy.contracts import RatingEstimate
from ml.anatomy.structural import StructuralExample, history_features
from ml.anatomy.training import development_roles
from tests.test_anatomy import measured


def test_scan_count_cohort_is_frozen_without_using_disease_outcomes(tmp_path, monkeypatch):
    from ml.anatomy import cohort

    records = []
    for count, number in ((3, 43), (4, 9), (5, 4)):
        for subject in range(number):
            for visit in range(count):
                records.append(
                    {
                        "Subject ID": f"S{count}_{subject:02}",
                        "MRI ID": f"S{count}_{subject:02}_V{visit}",
                        "MR Delay": visit * 500,
                        "Visit": visit + 1,
                        "CDR": 0,
                        "Group": "not a splitting feature",
                    }
                )
    metadata = tmp_path / "metadata.csv"
    pd.DataFrame(records).to_csv(metadata, index=False)
    monkeypatch.setattr(cohort, "_find_volume", lambda root, identity: tmp_path / f"{identity}.hdr")
    first = create_cohort(metadata, tmp_path, tmp_path / "study-a")
    roles = {s["subject_id"]: s["role"] for s in first["subjects"]}
    assert first["counts"] == {"train": 44, "selection": 4, "calibration": 4, "test": 4}
    assert development_roles(roles) == roles
    assert sum(len(s["visits"]) for s in first["subjects"]) == 185
    assert len(first["subjects"][0]["visits"]) == 5
    assert sum(s["role"] == "train" and len(s["visits"]) == 5 for s in first["subjects"]) == 3
    pd.DataFrame(records).assign(CDR=2, Group="changed future outcome").to_csv(metadata, index=False)
    second = create_cohort(metadata, tmp_path, tmp_path / "study-b")
    assert [(s["subject_id"], s["role"]) for s in first["subjects"]] == [
        (s["subject_id"], s["role"]) for s in second["subjects"]
    ]
    with pytest.raises(ValueError, match="immutable"):
        create_cohort(metadata, tmp_path, tmp_path / "study-a")


def test_unreviewed_scores_are_private_research_inputs_and_default_training_rejects_them():
    visits = [measured(day, reviewed=False) for day in (0, 400, 800)]
    for visit in visits:
        visit.qc = "automated_checks_only"
        visit.ratings = RatingEstimate(
            status="unreviewed_research", mta_left=1.1, mta_right=1.2, posterior_atrophy=0.8
        )
    with pytest.raises(ValueError, match="Reviewed anatomy"):
        history_features(visits[:2], 400, True)
    row, names = history_features(visits[:2], 400, True, require_review=False)
    assert row[names.index("mta_left")] == 1.1
    assert row[names.index("posterior_atrophy")] == 0.8
    assert StructuralExample("synthetic", visits[:2], visits[-1], True).interval_days == 400
    with pytest.raises(ValueError, match="hidden, reviewed"):
        StructuralExample("synthetic", visits[:2], visits[-1]).interval_days
    assert all(v.qc != "passed" and v.reviewer_id is None for v in visits)
