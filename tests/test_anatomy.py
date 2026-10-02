"""Synthetic engineering checks, not rating agreement or clinical validation."""

import json

import nibabel as nib
import numpy as np
import pytest
from pydantic import ValidationError

from ml.anatomy.contracts import AnatomyResult, AnatomyVisit, RatingEstimate, StructuralForecast
from ml.anatomy.masks import export_masks, geometry
from ml.anatomy.measurements import asymmetry, changes, etiv_mm3
from ml.anatomy.ratings import parse_avra_csv, run_rating
from ml.anatomy.spatial import jacobians, mesh, warp
from ml.anatomy.structural import RegularizedMixedEffects, StructuralExample, evaluate, history_features
from src.fastsurfer.regions import REGIONS


def measured(day: int, *, reviewed: bool = True, value: float = 4000) -> AnatomyVisit:
    volumes = {name: value + i * 20 for i, name in enumerate(REGIONS)}
    return AnatomyVisit(
        visit_id=f"v{day}",
        days_from_baseline=day,
        qc="passed" if reviewed else "pending_review",
        source_sha256="a" * 64,
        segmentation_sha256="b" * 64,
        statistics_sha256="c" * 64,
        container_digest="deepmi/fastsurfer@sha256:" + "d" * 64,
        volumes_mm3=volumes,
        mask_volumes_mm3=volumes,
        hippocampal_asymmetry_percent=0,
        observed_metadata={"Age": 72, "M/F": "F", "Group": "excluded", "CDR": 1},
        reviewer_id="synthetic-reviewer" if reviewed else None,
        reviewed_at="2026-10-02T00:00:00Z" if reviewed else None,
    )


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, 0, True])
def test_etiv_rejects_invalid(bad):
    with pytest.raises(ValueError):
        etiv_mm3(bad)


def test_units_irregular_changes_and_visual_gate():
    assert etiv_mm3(1500) == 1_500_000
    assert etiv_mm3(None) is None
    assert asymmetry(4500, 3500) == 25
    one, two = measured(0), measured(730, value=3600)
    delta = changes([one, two])[0]
    name = next(iter(REGIONS))
    assert delta["regions"][name]["absolute_mm3"] == -400
    assert delta["regions"][name]["annualized_percent"] == pytest.approx(-10 * 365.25 / 730)
    two.qc = "pending_review"
    assert changes([one, two])[0]["regions"] == {}
    with pytest.raises(ValueError):
        changes([one, one])


def test_result_prohibits_untrained_future_and_invalid_chronology():
    with pytest.raises(ValidationError):
        StructuralForecast(cutoff_visit_id="v0", interval_days=365, warnings=[], artifacts=[{"url": "fake"}])
    with pytest.raises(ValidationError):
        AnatomyResult(
            visits=[measured(0), measured(0)],
            changes=[],
            forecast=StructuralForecast(cutoff_visit_id="v0", interval_days=0, warnings=[]),
        )
    with pytest.raises(ValidationError):
        AnatomyVisit.model_validate(measured(0).model_dump() | {"reviewer_id": None})


@pytest.mark.parametrize(
    "values", [("2.25", "1.5", "1.75"), ("nan", "1", "1"), ("5", "1", "1"), ("1", "1", "4")]
)
def test_scores_continuous_single_pa_and_failed_alignment(tmp_path, values):
    path = tmp_path / "rating.csv"
    path.write_text("mta_left_mean,mta_right_mean,pa_mean\n" + ",".join(values) + "\n")
    pending = parse_avra_csv(path)
    assert pending.status == "pending_alignment_qc" and pending.mta_left is None
    result = parse_avra_csv(path, alignment_verified=True)
    if values[0] == "2.25":
        assert result.mta_left == 2.25 and result.posterior_atrophy == 1.75
        assert not result.agreement_validated
    else:
        assert result.status == "invalid" and result.posterior_atrophy is None
    with pytest.raises(ValidationError):
        RatingEstimate(status="unavailable", mta_left=2)


def test_rating_fails_closed_without_runtime(tmp_path):
    assert run_rating(tmp_path / "none.nii", tmp_path / "rating").status == "unavailable"
    config = tmp_path / "runtime.json"
    config.write_text(json.dumps({"image": "mutable:latest"}))
    assert run_rating(tmp_path / "none.nii", tmp_path / "rating", config).status == "invalid"


def image(data, affine=None):
    result = nib.Nifti1Image(data, np.eye(4) if affine is None else affine)
    result.header.set_xyzt_units("mm")
    return result


def test_native_masks_preserve_affine_and_physical_volume(tmp_path):
    shape = (12, 12, 12)
    labels = np.zeros(shape, np.int16)
    for i, label in enumerate(REGIONS.values()):
        labels[2 + i // 9, 2 + i % 9, 4] = label[0]
    affine = np.diag([2.0, 2.0, 2.0, 1.0])
    source, seg = tmp_path / "source.nii.gz", tmp_path / "seg.nii.gz"
    nib.save(image(np.ones(shape, np.float32), affine), source)
    nib.save(image(labels, affine), seg)
    volumes = export_masks(source, seg, tmp_path / "masks")
    assert all(v == pytest.approx(8) for v in volumes.values())
    mapped = nib.load(tmp_path / "masks/regions.nii.gz")
    assert np.array_equal(mapped.affine, affine)
    assert np.array_equal(mapped.get_fdata(), labels)
    assert (tmp_path / "masks/segmentation.nii.gz").exists()


def test_mask_unknown_units_and_fractional_labels_fail(tmp_path):
    source, seg = tmp_path / "source.nii", tmp_path / "seg.nii"
    nib.save(nib.Nifti1Image(np.ones((4, 4, 4), np.float32), np.eye(4)), source)
    nib.save(image(np.ones((4, 4, 4), np.float32)), seg)
    with pytest.raises(ValueError, match="units"):
        export_masks(source, seg, tmp_path / "out")
    nib.save(image(np.full((4, 4, 4), 1.5, np.float32)), seg)
    with pytest.raises(ValueError, match="categorical"):
        export_masks(source, seg, tmp_path / "out", source_units_verified=True)
    with pytest.raises(ValueError):
        geometry(image(np.zeros((1, 4, 4), np.float32)))


def test_zero_time_identity_categorical_sampling_and_invalid_deformation():
    data = np.arange(8**3, dtype=np.int16).reshape(8, 8, 8)
    source = image(data, np.diag([2.0, 3.0, 4.0, 1.0]))
    field = image(np.zeros((8, 8, 8, 3), np.float32), source.affine)
    assert np.array_equal(warp(source, field, categorical=True).get_fdata(), data)
    assert np.all(jacobians(field.get_fdata(), field.affine) == 1)
    outside = field.get_fdata()
    outside[..., 0] = 20
    with pytest.raises(ValueError, match="coverage"):
        warp(source, image(outside, source.affine), categorical=True)
    folded = field.get_fdata()
    folded[..., 0] = -4 * np.indices(data.shape)[0]
    with pytest.raises(ValueError, match="folding"):
        warp(source, image(folded, source.affine), categorical=True)


def test_mesh_affine_applied_once_closed_and_consistent(tmp_path):
    pytest.importorskip("skimage")
    data = np.zeros((24, 24, 24), np.uint8)
    data[4:20, 4:20, 4:20] = 1
    affine = np.diag([2.0, 3.0, 4.0, 1.0])
    affine[:3, 3] = [100, -40, 5]
    report = mesh(image(data, affine), tmp_path / "mask.gii")
    assert report["voxel_volume_mm3"] == pytest.approx(4096 * 24)
    assert report["relative_volume_error"] < 0.05
    vertices = nib.load(tmp_path / "mask.gii").darrays[0].data
    assert vertices[:, 0].min() == pytest.approx(107)
    assert report["components"] == 1
    data[0, 4, 4] = 1
    with pytest.raises(ValueError, match="boundary"):
        mesh(image(data, affine), tmp_path / "bad.gii")


def test_structural_training_only_preprocessing_subject_split_and_no_future():
    examples = [
        StructuralExample(subject, [measured(0), measured(500, value=3900)], measured(1000, value=3800))
        for subject in ("a", "b")
    ]
    splits = {"a": "train", "b": "train", "c": "test"}
    model = RegularizedMixedEffects().fit(examples, splits)
    _, features = history_features(examples[0].history, 500, False)
    assert "Group" not in features and "CDR" not in features
    with pytest.raises(ValueError, match="training subjects"):
        model.fit(examples, {"a": "train", "b": "test"})
    with pytest.raises(ValueError, match="score-conditioned"):
        history_features(examples[0].history, 500, True)
    test = StructuralExample("c", examples[0].history, measured(1000, value=3700))
    report = evaluate({"mixed_effects": model}, [test], splits)
    assert report["subjects"] == 1 and report["prediction_intervals"] is None
    with pytest.raises(ValueError, match="held-out"):
        evaluate({"mixed_effects": model}, examples, splits)
    with pytest.raises(ValueError, match="Target"):
        _ = StructuralExample("c", test.history, test.history[-1]).interval_days
