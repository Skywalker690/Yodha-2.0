"""Install an existing evaluation example for the read-only research preview."""

import argparse
import json
import shutil
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.services.anatomy_preview import ARTIFACTS
from ml.anatomy.integrity import checked_file
from src.common import sha256, write_json


def prepare(case_path: Path, manifest_path: Path, evaluation_path: Path, output: Path) -> None:
    case = json.loads(case_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    report = json.loads(evaluation_path.read_text())
    if (
        report["synthetic"] is not False
        or report["version"] != manifest["version"]
        or case["interval_days"] != manifest["interval_days"]
        or case["history"][-1]["visit_id"] != manifest["cutoff_visit_id"]
        or [v["source_sha256"] for v in case["history"]] != manifest["source_sha256"]
    ):
        raise ValueError("Preview must match the original real evaluation case")
    files = {}
    for name, kind in ARTIFACTS.items():
        entry = manifest["artifacts"][name]
        suffix = ".gii" if kind == "mesh" else ".nii.gz"
        if entry["relative_path"] != name + suffix or entry["kind"] != kind:
            raise ValueError("Unexpected preview artifact")
        files[name + suffix] = checked_file(manifest_path.parent, entry)
    output.mkdir(parents=True, exist_ok=False)
    descriptor = {"version": "saved-anatomy-preview-v1"}
    for key, source, filename in (
        ("case", case_path, "case.json"),
        ("manifest", manifest_path, "future-artifacts.json"),
        ("evaluation", evaluation_path, "evaluation.json"),
    ):
        shutil.copyfile(source, output / filename)
        descriptor[key] = {"relative_path": filename, "sha256": sha256(output / filename)}
    for filename, source in files.items():
        shutil.copyfile(source, output / filename)
        entry = manifest["artifacts"][filename.split(".")[0]]
        checked_file(output, entry)
    write_json(output / "preview.json", descriptor)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=get_settings().anatomy_preview_dir)
    args = parser.parse_args()
    prepare(args.case, args.manifest, args.evaluation, args.output)
    print("Saved experimental preview installed. No inference or model promotion performed.")


if __name__ == "__main__":
    main()
