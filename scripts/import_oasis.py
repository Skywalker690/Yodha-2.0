"""Offline, idempotent OASIS import. Source volumes are never modified."""

import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from sqlalchemy import select

from backend.app.core.config import get_settings
from backend.app.db.session import SessionLocal
from backend.app.models import Analysis, Patient, User, Visit
from backend.app.services.analysis import enqueue
from backend.app.services.storage import new_key, resolve_key
from backend.app.workers.runner import execute
from ml.data import read_manifest, read_metadata
from ml.preprocessing import load_validated, render_preview
from scripts.create_manifest import create_manifest
from scripts.seed import main as seed


def import_manifest(manifest: Path, metadata: Path, source_root: Path, precompute: bool = False) -> None:
    df = read_manifest(manifest)
    observed = read_metadata(metadata).set_index("MRI ID")
    seed()
    for code, sequence in df.groupby("patient_id", sort=True):
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == get_settings().seed_email.lower()))
            patient = db.scalar(select(Patient).where(Patient.code == code, Patient.owner_id == user.id))
            first = observed.loc[sequence.iloc[0]["visit_id"]]
            if patient is None:
                patient = Patient(
                    owner_id=user.id,
                    code=code,
                    age=int(first["Age"]),
                    sex="Female" if first["M/F"] == "F" else "Male",
                    source="oasis-2",
                    notes="Longitudinal OASIS-2 research case. Demographic observations are provided by the source dataset.",
                )
                db.add(patient)
                db.flush()
            for _, row in sequence.iterrows():
                exists = db.scalar(
                    select(Visit).where(Visit.patient_id == patient.id, Visit.label == row["visit_id"])
                )
                if exists:
                    continue
                source = Path(row["mri_path"]).resolve()
                if not source.is_relative_to(source_root.resolve()):
                    raise ValueError("Manifest MRI path must stay inside dataset root")
                img = load_validated(source, allow_pair=True)
                voxels = np.squeeze(np.asanyarray(img.dataobj)).astype(np.float32)
                key, preview = new_key("raw", ".nii.gz"), new_key("derived", ".png")
                nib.save(nib.Nifti1Image(voxels, img.affine), resolve_key(key))
                meta = render_preview(resolve_key(key), resolve_key(preview))
                info = observed.loc[row["visit_id"]]
                for field in ["CDR", "MMSE", "nWBV", "eTIV", "ASF"]:
                    if field in info and pd.notna(info[field]):
                        meta[field] = float(info[field])
                meta["source"] = "OASIS-2 supplied demographics"
                db.add(
                    Visit(
                        patient_id=patient.id,
                        label=row["visit_id"],
                        days_from_baseline=int(row["days_from_baseline"]),
                        mri_key=key,
                        preview_key=preview,
                        metadata_json=meta,
                    )
                )
                db.flush()
            db.commit()
            if precompute:
                existing = db.scalar(
                    select(Analysis).where(Analysis.patient_id == patient.id, Analysis.status == "completed")
                )
                if existing:
                    print(f"{code}: imported; existing analysis preserved.")
                    continue
                last = db.scalar(
                    select(Visit)
                    .where(Visit.patient_id == patient.id)
                    .order_by(Visit.days_from_baseline.desc())
                )
                job = enqueue(db, patient, last, "inference")
                job.status = "processing"  # reserve for this offline process, not the polling worker
                db.commit()
                job_id = job.id
            else:
                job_id = None
        if job_id:
            execute(job_id)
            with SessionLocal() as db:
                job = db.get(Analysis, job_id)
                if job.status != "completed":
                    raise RuntimeError(f"Precomputation failed for {code}; inspect worker logs")
                job.output_mode = "precomputed"
                job.result_json = {**job.result_json, "output_mode": "precomputed"}
                db.commit()
        print(f"{code}: {len(sequence)} visits ready{' with precomputed results' if job_id else ''}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=get_settings().dataset_root)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--subjects", type=int, default=5, choices=range(3, 6))
    parser.add_argument(
        "--all", action="store_true", help="Offline full-cohort import; takes substantially longer"
    )
    parser.add_argument("--precompute", action="store_true")
    args = parser.parse_args()
    metadata = args.metadata or next(args.root.glob("*.xlsx"), None) or next(args.root.glob("*.csv"), None)
    if metadata is None:
        raise SystemExit("No demographics XLSX/CSV found. Supply --metadata.")
    manifest = args.manifest or Path("data/manifests/full.csv" if args.all else "data/manifests/demo.csv")
    if args.manifest is None:
        create_manifest(metadata, args.root, manifest, args.subjects, args.all)
    import_manifest(manifest, metadata, args.root, args.precompute)


if __name__ == "__main__":
    main()
