"""Provision a local immutable AVRA candidate; no patient or automatic QC approval."""

import argparse
import json
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

from src.common import ROOT, sha256, write_json

COMMIT = "17e947606596e6594ec01d54ef38c992becf9395"
CODE_URL = f"https://api.github.com/repos/gsmartensson/avra_public/tarball/{COMMIT}"
WEIGHTS_URL = "https://github.com/gsmartensson/avra_public/releases/download/v0.8/0.8.tar.gz"


def unpack(archive: Path, destination: Path, *, strip_root: bool) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as stream:
        for member in stream.getmembers():
            if not member.isfile() and not member.isdir():
                raise ValueError("Archive links/devices are not accepted")
            relative = Path(member.name)
            if strip_root:
                relative = Path(*relative.parts[1:])
            path = (destination / relative).resolve()
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or not path.is_relative_to(destination.resolve())
            ):
                raise ValueError("Archive path escapes destination")
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with stream.extractfile(member) as source, path.open("wb") as target:
                    shutil.copyfileobj(source, target)


def provision(
    output: Path, *, licensed_fsl: bool, resume: bool = False, reuse_downloads: Path | None = None
) -> dict:
    if not licensed_fsl:
        raise ValueError("Review FSL license terms before provisioning this runtime")
    if output.exists() and not resume:
        raise ValueError("Provision attempts are immutable; use a new directory")
    if shutil.disk_usage(output.parent).free < 6 * 1024**3:
        raise ValueError("Six GiB free disk required before runtime provisioning")
    context = output / "build"
    if resume:
        state = json.loads((output / "status.json").read_text())
        if (
            state.get("stage") not in {"building", "build_failed"}
            or state.get("upstream_commit") != COMMIT
            or not state.get("fsl_terms_confirmed")
        ):
            raise ValueError("Only an interrupted prepared build may resume")
    else:
        output.mkdir(parents=True)
        write_json(
            output / "status.json",
            {"stage": "downloading", "fsl_terms_confirmed": True, "upstream_commit": COMMIT},
        )
        previous = json.loads((reuse_downloads / "runtime.json").read_text()) if reuse_downloads else None
        if previous and previous["upstream_commit"] != COMMIT:
            raise ValueError("Cached upstream commit differs")
        for name, url in (("source.tar.gz", CODE_URL), ("weights.tar.gz", WEIGHTS_URL)):
            if previous:
                key = "source_archive_sha256" if name == "source.tar.gz" else "weights_archive_sha256"
                cached = reuse_downloads / name
                if sha256(cached) != previous[key]:
                    raise ValueError("Cached released archive changed")
                shutil.copyfile(cached, output / name)
            else:
                with (
                    urllib.request.urlopen(
                        urllib.request.Request(url, headers={"User-Agent": "Yodha-local-research"}),
                        timeout=90,
                    ) as source,
                    (output / name).open("wb") as target,
                ):
                    shutil.copyfileobj(source, target)
        context.mkdir()
        unpack(output / "source.tar.gz", context / "upstream", strip_root=True)
        unpack(output / "weights.tar.gz", output / "weights-archive", strip_root=False)
    candidates = [
        p
        for p in (output / "weights-archive").rglob("mta")
        if p.is_dir() and (p.parent / "pa").is_dir() and (p.parent / "gca-f").is_dir()
    ]
    if len(candidates) != 1:
        raise ValueError("Unexpected upstream checkpoint archive layout")
    weights = candidates[0].parent
    # Audited mechanical compatibility fix: record the matrix ACTUALLY applied,
    # including upstream's alternate BET matrix, before upstream deletes it.
    misc = context / "upstream/utils/misc.py"
    original = misc.read_text()
    token = "        # apply transform"
    if original.count(token) != 1:
        raise ValueError("Pinned upstream alignment source changed")
    if not resume:
        misc.write_text(
            original.replace(
                token,
                "        # Preserve actual selected transform for owned alignment provenance.\n        if xfm_path != os.path.join(output_folder,guid + '_mni_dof_' + str(dof)+ '.mat'):\n            copyfile(xfm_path, os.path.join(output_folder,guid + '_mni_dof_' + str(dof)+ '.mat'))\n"
                + token,
            )
        )
    elif original.count("# Preserve actual selected transform for owned alignment provenance.") != 1:
        raise ValueError("Prepared alignment compatibility patch missing or duplicated")
    shutil.copyfile(ROOT / "infra/avra/Dockerfile", context / "Dockerfile")
    write_json(
        output / "status.json", {"stage": "building", "fsl_terms_confirmed": True, "upstream_commit": COMMIT}
    )
    image_name = "yodha-avra-local:" + sha256(output / "source.tar.gz")[:12]
    try:
        with (output / "build.log").open("a" if resume else "w", encoding="utf-8") as log:
            subprocess.run(
                ["docker", "build", "--progress=plain", "--tag", image_name, str(context)],
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=2400,
            )
    except subprocess.SubprocessError:
        write_json(
            output / "status.json",
            {"stage": "build_failed", "fsl_terms_confirmed": True, "upstream_commit": COMMIT},
        )
        raise
    image_id = subprocess.run(
        ["docker", "image", "inspect", image_name, "--format", "{{.Id}}"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout.strip()
    result = {
        "image": image_id,
        "weights_dir": str(weights.resolve()),
        "upstream_commit": COMMIT,
        "source_archive_sha256": sha256(output / "source.tar.gz"),
        "weights_archive_sha256": sha256(output / "weights.tar.gz"),
        "compatibility_patch_sha256": sha256(misc),
        "fsl_terms_confirmed": True,
        "weights_sha256": {p.relative_to(weights).as_posix(): sha256(p) for p in weights.rglob("*.pth.tar")},
    }
    write_json(output / "runtime.json", result)
    write_json(
        output / "status.json", {"stage": "built_candidate_requires_real_alignment_review", "image": image_id}
    )
    return {
        "stage": "built_candidate_requires_real_alignment_review",
        "checkpoints": len(result["weights_sha256"]),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--licensed-fsl", required=True, action="store_true")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an interrupted prepared build without redownloading weights",
    )
    parser.add_argument(
        "--reuse-downloads",
        type=Path,
        help="Verify and reuse released archives from an earlier built candidate",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            provision(
                args.output,
                licensed_fsl=args.licensed_fsl,
                resume=args.resume,
                reuse_downloads=args.reuse_downloads,
            )
        )
    )
