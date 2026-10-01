import argparse
from pathlib import Path

import nibabel as nib
import numpy as np

from ml.data import read_manifest
from ml.preprocessing import load_validated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    df = read_manifest(args.manifest)
    for index, row in df.iterrows():
        img = load_validated(Path(row.mri_path), allow_pair=True)
        # Generated index-based names avoid trusting manifest IDs as filesystem paths.
        target = args.output / f"volume-{index:05d}.nii.gz"
        nib.save(nib.Nifti1Image(np.squeeze(img.get_fdata(dtype=np.float32)), img.affine), target)
        df.loc[index, "mri_path"] = str(target.resolve())
    df.to_csv(args.output / "manifest.csv", index=False)
    print(f"Converted {len(df)} volumes to {args.output}; source files unchanged.")


if __name__ == "__main__":
    main()
