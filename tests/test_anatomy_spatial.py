"""Physical and held-out learning regressions using synthetic anatomy only."""

import json

import nibabel as nib
import numpy as np
import pytest
import torch

from ml.anatomy.evaluation import calibrate_intervals, geometry_metrics, interval_coverage
from ml.anatomy.forecasting import native_field, release
from ml.anatomy.model import FeatureScaler, SpatialPredictor, field_jacobians, spatial_loss
from ml.anatomy.registration import as_sitk, nifti, resample
from ml.anatomy.spatial import jacobians
from ml.anatomy.training import development_roles
from ml.anatomy.study import VERSION as STUDY_VERSION
from ml.anatomy.registration import VERSION as REGISTRATION_VERSION
from src.common import sha256, write_json
from tests.test_anatomy import measured
from src.fastsurfer.regions import REGIONS


def labels(size=24):
    values = np.zeros((size,) * 3, np.int16)
    for index, (identifier, _) in enumerate(REGIONS.values()):
        x, y, z = 2 + index % 3 * 6, 2 + index // 3 % 3 * 6, 2 + index // 9 * 8
        values[x : x + 4, y : y + 4, z : z + 4] = identifier
    return values


def test_ras_lps_roundtrip_with_permuted_flipped_anisotropic_grid():
    import SimpleITK as sitk

    affine = np.array([[0, -2, 0, 10], [3, 0, 0, -20], [0, 0, 4, 30], [0, 0, 0, 1]], float)
    data = np.arange(12**3, dtype=np.int16).reshape((12,) * 3)
    source = nifti(data, affine)
    itk = as_sitk(source)
    point = np.array(itk.TransformIndexToPhysicalPoint((2, 3, 4)))
    assert point == pytest.approx(nib.affines.apply_affine(affine, [2, 3, 4]) * [-1, -1, 1])
    mapped = resample(source, source, sitk.Transform(3, sitk.sitkIdentity), categorical=True)
    assert np.array_equal(mapped.dataobj, data)
    assert mapped.affine == pytest.approx(affine)
    sheared = affine.copy()
    sheared[0, 0] = 0.4
    with pytest.raises(ValueError, match="Sheared"):
        as_sitk(nifti(data, sheared))


def test_torch_physical_jacobian_agrees_with_numpy_and_zero_time_is_identity():
    torch.set_num_threads(2)
    affine = np.array([[0, -2, 0, 0], [3, 0, 0, 0], [0, 0, 4, 0], [0, 0, 0, 1]], np.float32)
    grid = np.indices((16,) * 3).transpose(1, 2, 3, 0).astype(np.float32)
    field = grid @ affine[:3, :3].T * 0.01
    tensor = torch.from_numpy(field.transpose(3, 0, 1, 2))[None]
    actual = field_jacobians(tensor, torch.from_numpy(affine)[None]).numpy()[0]
    assert actual == pytest.approx(jacobians(field, affine), abs=1e-6)
    model = SpatialPredictor(8)
    batch = torch.randn(1, 6, 16, 16, 16)
    result = model(batch, torch.zeros(1, 8), torch.zeros(1))
    assert torch.count_nonzero(result) == 0
    with pytest.raises(ValueError, match="Invalid spatial inputs"):
        model(batch, torch.zeros(1, 8), torch.tensor([-1.0]))


def test_native_vector_resampling_preserves_ras_mm_and_never_scales_twice():
    field = np.ones((12, 12, 12, 3), np.float32) * [1, 2, 3]
    reference = nifti(np.zeros((24,) * 3, np.float32), np.eye(4))
    actual = native_field(field, np.diag([2.0, 2.0, 2.0, 1.0]), reference)
    assert actual.shape == (24, 24, 24, 3)
    assert np.asarray(actual.dataobj) == pytest.approx(np.broadcast_to([1.0, 2.0, 3.0], actual.shape))
    assert actual.header.get_intent()[0] == "vector"
    assert actual.header.get_xyzt_units()[0] == "mm"


def test_identity_spatial_loss_and_geometry_are_real_and_differentiable():
    torch.set_num_threads(2)
    categorical = labels()
    field = torch.zeros(1, 3, 24, 24, 24, requires_grad=True)
    images = torch.rand(1, 6, 24, 24, 24)
    loss, metrics = spatial_loss(
        field,
        torch.zeros_like(field),
        images,
        images[:, :1],
        torch.from_numpy(categorical)[None],
        torch.eye(4)[None],
        torch.ones(1, len(REGIONS)),
    )
    assert float(loss.detach()) == pytest.approx(0, abs=1e-6)
    loss.backward()
    assert field.grad is not None and torch.isfinite(field.grad).all()
    assert metrics["folding"] == 0
    physical = nifti(categorical, np.diag([2.0, 3.0, 4.0, 1.0]))
    for region in geometry_metrics(physical, physical).values():
        assert region == {"dice": 1.0, "assd_mm": 0.0, "hd95_mm": 0.0, "absolute_volume_error_mm3": 0.0}
    with pytest.raises(ValueError, match="common physical"):
        geometry_metrics(physical, nifti(categorical, np.eye(4)))


def test_train_only_scaler_serialization_and_subject_block_coverage():
    scaler = FeatureScaler.fit(np.array([[2.0, np.nan], [4.0, np.nan]]))
    before = scaler.to_dict()
    heldout = scaler.transform(np.array([1e6, np.nan]))
    assert heldout[-1] == 1 and scaler.to_dict() == before
    reloaded = FeatureScaler.from_dict(json.loads(json.dumps(before)))
    assert np.array_equal(heldout, reloaded.transform(np.array([1e6, np.nan])))
    with pytest.raises(ValueError, match="Invalid saved"):
        FeatureScaler.from_dict({"median": [0], "scale": [0]})
    errors = {f"subject{i}": [np.array([float(i + 1), 2.0])] for i in range(4)}
    calibrated = calibrate_intervals(errors)
    assert calibrated["radius_mm3"] == [4.0, 2.0]
    repeated = {**errors, "subject0": errors["subject0"] * 50}
    assert calibrate_intervals(repeated) == calibrated
    assert interval_coverage(calibrated, errors)["simultaneous"] == 1
    assert calibrate_intervals(dict(list(errors.items())[:3])) is None


def test_binary_saddle_contacts_export_closed_mesh_without_changing_mask(tmp_path):
    from skimage.measure import marching_cubes
    from ml.anatomy.spatial import mesh

    mask = np.zeros((32,) * 3, np.uint8)
    mask[2:30, 2:30, 2:30] = 1
    mask[12:18, 12:18, 12:18] = np.random.default_rng(42).integers(0, 2, (6,) * 3)
    original = mask.copy()
    _, faces, _, _ = marching_cubes(mask.astype(np.float32), 0.5, gradient_direction="ascent")
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    assert np.any(np.unique(edges, axis=0, return_counts=True)[1] == 4)
    destination = tmp_path / "saddle.gii"
    result = mesh(nifti(mask, np.eye(4)), destination)
    assert np.array_equal(mask, original)
    assert result["isovalue"] == 0.5001
    assert result["relative_volume_error"] < 0.05
    saved = nib.load(destination)
    faces = saved.darrays[1].data
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    assert np.all(np.unique(edges, axis=0, return_counts=True)[1] == 2)


def test_development_calibration_subjects_stay_separate_and_no_fake_release(tmp_path):
    split = {
        **{f"train{i}": "train" for i in range(40)},
        **{f"dev{i}": "validation" for i in range(8)},
        **{f"test{i}": "test" for i in range(8)},
    }
    roles = development_roles(split)
    assert list(roles.values()).count("selection") == 4
    assert list(roles.values()).count("calibration") == 4
    assert roles == development_roles(dict(reversed(list(split.items()))))
    (tmp_path / "release.json").write_text(
        json.dumps({"version": "anatomy-research-release-v1", "status": "promoted", "synthetic": True})
    )
    with pytest.raises(ValueError, match="real-data"):
        release(tmp_path)


def test_spatial_selection_weights_subjects_equally_despite_longer_histories(monkeypatch):
    from types import SimpleNamespace
    from ml.anatomy import training

    monkeypatch.setattr(training, "predict_field", lambda *args: np.zeros((16, 16, 16, 3)))
    monkeypatch.setattr(training, "warp", lambda image, *args, **kwargs: image)
    monkeypatch.setattr(
        training,
        "geometry_metrics",
        lambda predicted, target: {"region": {"dice": float(np.asarray(target.dataobj)[0, 0, 0])}},
    )

    def case(subject, value):
        return (
            {},
            SimpleNamespace(subject_id=subject),
            {
                "labels": np.ones((16,) * 3),
                "target_labels": np.full((16,) * 3, value),
                "affine": np.eye(4),
            },
        )

    short, long = case("short", 0.2), case("long", 0.8)
    one = training._spatial_evaluation(None, None, [short, long], True, "cpu")
    repeated = training._spatial_evaluation(None, None, [short, long, long, long], True, "cpu")
    assert one["mean"]["dice"] == pytest.approx(0.5)
    assert repeated["mean"] == pytest.approx(one["mean"])
    assert repeated["subjects"] == 2 and repeated["cases"] == 4


@pytest.mark.parametrize("unreviewed", [False, True])
def test_small_synthetic_training_exercises_saved_score_conditioned_model_without_promotion(
    tmp_path, unreviewed
):
    from ml.anatomy.contracts import RatingEstimate
    from ml.anatomy.training import train
    from ml.anatomy.forecasting import load_models
    from ml.anatomy.native_evaluation import promote

    split = {
        **{f"train{i}": "train" for i in range(40)},
        **{f"dev{i}": "validation" for i in range(8)},
        **{f"test{i}": "test" for i in range(8)},
    }
    subjects = ["train0", "train1", *[f"dev{i}" for i in range(8)], *[f"test{i}" for i in range(8)]]
    entries = []
    categorical = labels()
    for subject in subjects:
        directory = tmp_path / subject
        directory.mkdir()
        visits = [measured(day, value=4000 - index * 10) for index, day in enumerate((0, 365, 730))]
        for visit in visits:
            visit.ratings = RatingEstimate(
                status="unreviewed_research" if unreviewed else "ok",
                mta_left=1.2,
                mta_right=1.1,
                posterior_atrophy=0.8,
            )
            if unreviewed:
                visit.qc = "automated_checks_only"
                visit.reviewer_id = visit.reviewed_at = None
        images = np.zeros((6, 24, 24, 24), np.float32)
        images[0] = np.linspace(0, 1, 24)[None, None, :]
        tensor = directory / "example.npz"
        np.savez_compressed(
            tensor,
            images=images,
            affine=np.eye(4, dtype=np.float32),
            labels=categorical,
            target_labels=categorical,
            later=images[:1],
            target_field=np.zeros((3, 24, 24, 24), np.float32),
            target_ratios=np.ones(len(REGIONS), np.float32),
        )
        case = directory / "case.json"
        write_json(
            case,
            {
                "version": STUDY_VERSION,
                "registration_version": REGISTRATION_VERSION,
                "subject_id": subject,
                "history": [v.model_dump() for v in visits[:2]],
                "target": visits[-1].model_dump(),
                "interval_days": 365,
                "registration_qc": "pending_review" if unreviewed else "passed",
                "allow_unreviewed_research": unreviewed,
                "reviewer_id": None if unreviewed else "synthetic-fixture",
                "reviewed_at": None if unreviewed else "2026-10-02T00:00:00Z",
                "artifacts": {"example.npz": {"relative_path": "example.npz", "sha256": sha256(tensor)}},
            },
        )
        entries.append({"relative_path": f"{subject}/case.json", "sha256": sha256(case)})
    study = tmp_path / "study.json"
    write_json(study, {"synthetic": True, "split": split, "cases": entries})
    output = tmp_path / "candidate"
    report = train(study, output, epochs=1, synthetic=True, allow_unreviewed_research=unreviewed)
    assert report["synthetic"] is True
    assert report["review_complete"] is not unreviewed
    assert "Synthetic tests cannot be promoted" in report["release_failures"]
    assert set(report["test_volume"]) == {
        "with_scores",
        "no_change",
        "individual_linear_trend",
    }
    assert set(report["test_spatial"]) == {"with_scores"}
    assert not (output / "without_scores.pt").exists()
    assert not (output / "without_scores.json").exists()
    model, scaler, checkpoint, structural = load_models(output)
    assert not model.training and structural.with_scores and checkpoint["with_scores"]
    assert len(scaler.median) == len(checkpoint["feature_names"])
    # Exercise native registration, the saved model, warp and every physical mesh
    # exporter together. This zero-time synthetic run never creates a release.
    from ml.anatomy.forecasting import generate

    native_labels = np.zeros((32,) * 3, np.int16)
    for index, (identifier, _) in enumerate(REGIONS.values()):
        x, y, z = 1 + index % 3 * 10, 1 + index // 3 % 3 * 10, 1 + index // 9 * 10
        native_labels[x : x + 8, y : y + 8, z : z + 8] = identifier
    grid = np.indices(native_labels.shape).astype(np.float32)
    intensity = np.exp(-sum((grid[i] - (14 + i)) ** 2 for i in range(3)) / 150).astype(np.float32)
    raw = tmp_path / "synthetic-mri.nii.gz"
    categorical_path = tmp_path / "synthetic-labels.nii.gz"
    nib.save(nifti(intensity, np.eye(4)), raw)
    nib.save(nifti(native_labels, np.eye(4)), categorical_path)
    history = visits[:2]
    records = []
    for visit in history:
        visit.source_sha256 = sha256(raw)
        records.append(
            {
                "visit_id": visit.visit_id,
                "mri_path": str(raw),
                "source_units_verified": True,
                "labels_path": str(categorical_path),
                "labels_sha256": sha256(categorical_path),
            }
        )
    native_output = tmp_path / "synthetic-zero"
    exported = generate(
        output, "synthetic-heldout", history, records, 0, native_output, allow_unreviewed_research=unreviewed
    )
    assert len(exported["artifacts"]) == 40
    assert len(exported["mesh_checks"]) == 19
    assert np.array_equal(nib.load(native_output / "labels.nii.gz").dataobj, native_labels)
    assert np.allclose(nib.load(native_output / "mri.nii.gz").dataobj, intensity)
    for region, (identifier, _) in REGIONS.items():
        mask = nib.load(native_output / f"{region}_mask.nii.gz")
        assert mask.header.get_xyzt_units()[0] == "mm"
        assert np.array_equal(mask.dataobj, native_labels == identifier)
        assert exported["mesh_checks"][region]["relative_volume_error"] <= 0.05
    for entry in exported["artifacts"].values():
        assert sha256(native_output / entry["relative_path"]) == entry["sha256"]
    with pytest.raises(ValueError, match="Cannot promote"):
        promote(output)
