import json
from pathlib import Path
from backend.app.db.session import SessionLocal
from backend.app.models import Analysis, Patient
from backend.app.services.anatomy_forecast import execute_forecast, readiness
from backend.app.services.storage import resolve_key

print("Checking readiness...")
state = readiness()
print("Readiness state:", state)

with SessionLocal() as db:
    patient = db.query(Patient).filter_by(code="OAS2_0048").first()
    source = db.query(Analysis).filter_by(patient_id=patient.id, output_mode="anatomy", status="completed").first()
    print("Found patient:", patient.code, "source analysis:", source.id)

    output_dir = resolve_key(f"derived/forecast_test_{patient.code}_12m")
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)

    print("Running execute_forecast for 365 days (+12 months)...")
    result = execute_forecast(
        source_payload=source.result_json,
        source_inputs=source.input_json,
        source_root=resolve_key(f"derived/{source.id}"),
        output=output_dir,
        subject_id=patient.code,
        interval=365,
        expected_release=state["releaseSha256"],
        cutoff_id=source.visit_id,
        allow_unreviewed_research=state.get("isResearchCandidate", False),
        candidate_dir=state.get("candidateDir"),
    )
    print("Forecast completed successfully!")
    print("Status:", result.anatomy.forecast.status)
    print("Volumes predicted:", result.anatomy.forecast.volumes_mm3)
    future_dir = output_dir / "future"
    print("Generated files in future/:", [f.name for f in future_dir.iterdir()])
