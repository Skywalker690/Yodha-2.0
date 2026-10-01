"""Inspect headers and metadata without loading or modifying all raw MRI volumes."""

import argparse
import json
from collections import Counter
from pathlib import Path

import nibabel as nib
import numpy as np

from ml.data import read_metadata


def inspect(root: Path, metadata: Path | None = None) -> dict:
    visits = sorted(path for path in root.glob("OAS2_RAW_PART*/OAS2_*_MR*") if path.is_dir())
    subjects = Counter(p.name.rsplit("_MR", 1)[0] for p in visits)
    headers = list(root.glob("OAS2_RAW_PART*/OAS2_*_MR*/RAW/*.hdr"))
    classes, shapes, issues = Counter(), Counter(), []
    for header in headers:
        try:
            image = nib.load(header)
            classes[type(image).__name__] += 1
            shapes[str(image.shape)] += 1
            pair = header.with_suffix(".img")
            expected = int(np.prod(image.shape)) * image.get_data_dtype().itemsize
            if not pair.exists() or pair.stat().st_size < expected:
                issues.append(f"Missing or truncated image: {header.relative_to(root)}")
        except Exception as exc:
            issues.append(f"{header.relative_to(root)}: {type(exc).__name__}")
    result = {
        "subjects": len(subjects),
        "visits": len(visits),
        "headerImagePairs": len(headers),
        "subjectsWithThreeOrMoreVisits": sum(c >= 3 for c in subjects.values()),
        "formats": dict(classes),
        "shapes": dict(shapes),
        "issues": issues,
        "validation": "Header readability and expected file sizes; not whole-volume voxel QC",
    }
    if metadata:
        df = read_metadata(metadata)
        actual, described = {p.name for p in visits}, set(df["MRI ID"])
        result.update(
            {
                "metadataRows": len(df),
                "metadataSubjects": df["Subject ID"].nunique(),
                "metadataWithoutMRI": sorted(described - actual),
                "mriWithoutMetadata": sorted(actual - described),
                "missingMetadataValues": {str(k): int(v) for k, v in df.isna().sum().items() if v},
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("dataset"))
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    metadata = args.metadata or next(args.root.glob("*.xlsx"), None)
    report = inspect(args.root, metadata)
    formatted = json.dumps(report, indent=2)
    print(formatted)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(formatted, encoding="utf-8")
    if report["issues"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
