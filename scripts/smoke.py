"""Check the running local stack without displaying credentials or private paths."""

import argparse
import json
import time
from pathlib import Path

import httpx

from backend.app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--mode", choices=["precomputed", "inference", "demo"], default="precomputed")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--compare", type=Path)
    args = parser.parse_args()
    settings = get_settings()
    with httpx.Client(base_url=args.base_url, timeout=20, trust_env=False) as client:
        assert client.get("/patients").status_code == 401, "Unprotected patient endpoint"
        login = client.post(
            "/auth/login", json={"email": settings.seed_email, "password": settings.seed_password}
        )
        login.raise_for_status()
        assert "HttpOnly" in login.headers["set-cookie"]
        health = client.get("/health")
        health.raise_for_status()
        print("Services:", json.dumps(health.json()))
        response = client.get("/patients")
        response.raise_for_status()
        patients = response.json()
        prepared = [p for p in patients if p["source"] == "oasis-2"]
        assert len(prepared) >= 3, "Import the prepared cohort first"
        assert all(p["visitCount"] >= 3 for p in prepared)
        assert all(p["latestCompleted"] for p in prepared)
        snapshot = {p["id"]: [v["id"] for v in p["visits"]] for p in patients}
        if args.snapshot:
            args.snapshot.parent.mkdir(parents=True, exist_ok=True)
            args.snapshot.write_text(json.dumps(snapshot), encoding="utf-8")
        if args.compare:
            previous = json.loads(args.compare.read_text(encoding="utf-8"))
            assert snapshot == previous, "Patient/visit records changed across restart"
            print("Patient/visit persistence after restart: PASS")
        patient = prepared[0]
        for visit in patient["visits"]:
            preview = client.get(f"/visits/{visit['id']}/preview")
            assert preview.status_code == 200 and preview.headers["content-type"] == "image/png"
        if args.analyze:
            started = time.monotonic()
            response = client.post(f"/analysis/{patient['visits'][-1]['id']}", json={"outputMode": args.mode})
            assert response.status_code == 202, response.text
            item = response.json()
            assert item["status"] == "queued"
            print(f"Asynchronous start: 202 in {time.monotonic() - started:.2f}s")
            while time.monotonic() - started < 60:
                item = client.get(f"/analysis/{item['id']}").json()
                if item["status"] in {"completed", "failed"}:
                    break
                time.sleep(0.5)
            assert item["status"] == "completed", item.get("error") or "Worker timeout"
            assert item["outputMode"] == args.mode and item["confidence"] is None
            result = item["resultJson"]
            assert len(result["visitIds"]) == 3
            assert all(0 <= s <= 1 for s in result["riskScores"])
            assert (
                client.get(f"/analysis/{item['id']}/visits/{result['selectedVisit']}/overlay").status_code
                == 200
            )
            print(f"{args.mode.title()} analysis completed in {time.monotonic() - started:.2f}s")
        if args.report:
            response = client.post(f"/reports/{patient['id']}")
            response.raise_for_status()
            pdf = client.get(response.json()["downloadUrl"].removeprefix("/api"))
            assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
            output = Path("tmp/pdfs/research-report.pdf")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(pdf.content)
            print("Research report generated and downloaded: PASS")
        print(
            f"Prepared cohort: {len(prepared)} subjects / {sum(p['visitCount'] for p in prepared)} visits. Smoke checks PASS."
        )


if __name__ == "__main__":
    main()
