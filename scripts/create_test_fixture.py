from pathlib import Path

import nibabel as nib
import numpy as np


def main() -> None:
    root = Path("data/fixtures")
    root.mkdir(parents=True, exist_ok=True)
    x, y, z = np.mgrid[-1:1:24j, -1:1:24j, -1:1:24j]
    rng = np.random.default_rng(42)
    voxels = (np.exp(-4 * (x * x + y * y + z * z)) + rng.random((24, 24, 24)) * 0.05).astype(np.float32)
    nib.save(nib.Nifti1Image(voxels, np.eye(4)), root / "synthetic.nii.gz")
    print("Synthetic test fixture created; no real subject data used.")


if __name__ == "__main__":
    main()
