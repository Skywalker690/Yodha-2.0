import argparse
import hashlib
from pathlib import Path

import pandas as pd

from ml.data import read_metadata


def create_manifest(
    metadata: Path, root: Path, output: Path, subjects: int = 5, full: bool = False
) -> pd.DataFrame:
    df = read_metadata(metadata)
    eligible = sorted(df.groupby("Subject ID").size().loc[lambda s: s >= 3].index)
    if not full:
        # Spread the prepared cohort over both dataset parts, retaining actual recorded visits.
        selected = [
            eligible[round(i * (len(eligible) - 1) / max(1, subjects - 1))]
            for i in range(min(subjects, len(eligible)))
        ]
        df = df[df["Subject ID"].isin(selected)].groupby("Subject ID").head(3)
    records = []
    for _, row in df.iterrows():
        candidates = sorted(root.glob(f"OAS2_RAW_PART*/{row['MRI ID']}/RAW/mpr-*.nifti.hdr"))
        if not candidates:
            raise ValueError(f"MRI pair missing for {row['MRI ID']}")
        path = next((p for p in candidates if p.name == "mpr-1.nifti.hdr"), candidates[0])
        bucket = int(hashlib.sha256(str(row["Subject ID"]).encode()).hexdigest()[:8], 16) % 10
        records.append(
            {
                "patient_id": row["Subject ID"],
                "visit_id": row["MRI ID"],
                "visit_index": int(row["Visit"]) - 1,
                "days_from_baseline": int(row["MR Delay"]),
                "mri_path": str(path.resolve()),
                "reference_path": "",
                "cdr": row["CDR"],
                "split": ("train" if bucket < 7 else "validation" if bucket == 7 else "test")
                if full
                else "demo",
                "output_mode": "inference" if full else "precomputed",
            }
        )
    result = pd.DataFrame(records)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("dataset"))
    parser.add_argument("--output", type=Path, default=Path("data/manifests/demo.csv"))
    parser.add_argument("--subjects", type=int, default=5, choices=range(3, 6))
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    df = create_manifest(args.input, args.root, args.output, args.subjects, args.all)
    print(f"Created manifest: {df.patient_id.nunique()} subjects, {len(df)} visits.")


if __name__ == "__main__":
    main()
