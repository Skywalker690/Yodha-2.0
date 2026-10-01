"""Prepare/check local OASIS visualization artifacts without exporting private MRI."""

import argparse
import gzip
import time

import httpx
import nibabel as nib
import numpy as np

from backend.app.core.config import get_settings


def decode_volume(content: bytes) -> nib.Nifti1Image:
    if content.startswith(b"\x1f\x8b"):
        content = gzip.decompress(content)
    return nib.Nifti1Image.from_bytes(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--prepare", action="store_true", help="Queue inference for missing 3D artifacts")
    args = parser.parse_args()
    settings = get_settings()
    with httpx.Client(base_url=args.base_url, timeout=45, trust_env=False) as client:
        assert client.get("/visits/unknown/volume").status_code == 401
        assert client.get("/analysis/unknown/visits/unknown/difference-volume").status_code == 401
        client.post("/auth/login", json={
            "email": settings.seed_email, "password": settings.seed_password,
        }).raise_for_status()
        cohort_response = client.get("/patients")
        cohort_response.raise_for_status()
        cohort = [p for p in cohort_response.json() if p["source"] == "oasis-2"]
        assert cohort, "Import the prepared OASIS cohort first"
        checked = 0
        for patient in cohort:
            analysis = patient["latestCompleted"]
            if args.prepare and not (analysis and analysis["resultJson"].get("volumeOverlaysReady")):
                response = client.post(
                    f"/analysis/{patient['visits'][-1]['id']}", json={"outputMode": "inference"},
                )
                assert response.status_code == 202, "Wait for an active patient job to finish, then retry"
                analysis = response.json()
                started = time.monotonic()
                while time.monotonic() - started < 180:
                    analysis = client.get(f"/analysis/{analysis['id']}").json()
                    if analysis["status"] in {"completed", "failed"}:
                        break
                    time.sleep(0.5)
                assert analysis["status"] == "completed", analysis.get("error") or "Worker timeout"
            assert analysis and analysis["resultJson"].get("volumeOverlaysReady"), "Run with --prepare first"
            for visit in patient["visits"]:
                raw = client.get(f"/visits/{visit['id']}/volume")
                raw.raise_for_status()
                assert "research-mri" in raw.headers["content-disposition"]
                source = nib.as_closest_canonical(decode_volume(raw.content))
                difference = client.get(f"/analysis/{analysis['id']}/visits/{visit['id']}/difference-volume")
                difference.raise_for_status()
                assert "research-difference" in difference.headers["content-disposition"]
                image = decode_volume(difference.content)
                assert image.shape == (64, 64, 64)
                assert np.isfinite(image.get_fdata()).all()
                assert 0 <= image.get_fdata().min() <= image.get_fdata().max() <= 1
                for fraction in [0, 0.5, 1]:
                    raw_position = np.append(np.array(source.shape[:3]) * fraction - 0.5, 1)
                    diff_position = np.append(np.array(image.shape) * fraction - 0.5, 1)
                    assert np.allclose(source.affine @ raw_position, image.affine @ diff_position, atol=0.001)
                checked += 1
            print(f"{patient['code']}: source volumes, 3D artifacts and geometry PASS", flush=True)
        print(f"3D smoke PASS: {len(cohort)} subjects / {checked} MRI visits", flush=True)


if __name__ == "__main__":
    main()
