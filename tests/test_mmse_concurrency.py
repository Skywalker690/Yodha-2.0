"""Optional real-PostgreSQL checks; use only the disposable named test container."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from backend.app.api.routes import locked_assessment_visit
from backend.app.db.session import Base
from backend.app.models import Patient, User, Visit
from backend.app.schemas.contracts import MMSEDraftSave
from backend.app.services import mmse

TEST_URL = os.environ.get("MMSE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_URL, reason="Requires isolated PostgreSQL assessment test database")


@pytest.mark.parametrize("assessment_first", [True, False])
def test_waiting_writer_refreshes_metadata_after_row_lock(assessment_first, monkeypatch):
    assert make_url(TEST_URL).host == "alzhio-mmse-concurrency-db"
    engine = create_engine(TEST_URL)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(mmse, "load_protocol", mmse.demo_protocol)
    with factory() as db:
        user = User(email=f"synthetic-{assessment_first}@example.test", password_hash="synthetic-unused")
        db.add(user)
        db.flush()
        patient = Patient(owner_id=user.id, code="PG_MMSE", source="uploaded")
        db.add(patient)
        db.flush()
        visit = Visit(patient_id=patient.id, label="Baseline", days_from_baseline=0, metadata_json={"MMSE": 24})
        db.add(visit)
        db.flush()
        attempt = mmse.start(visit, user.id)
        saved = mmse.save(visit, attempt["id"], MMSEDraftSave.model_validate({
            "revision": 0, "assessedAt": attempt["assessedAt"],
            "items": [{"itemId": key, "points": points} for key, points in mmse.DOMAINS],
        }))
        db.commit()
        visit_id, user_id, assessment_id, revision = visit.id, user.id, saved["id"], saved["revision"]
    reader_ready = Event()
    writer_done = Event()

    def waiting_writer():
        with factory() as db:
            # Deliberately populate an old identity-map value before acquiring the lock.
            stale = db.get(Visit, visit_id)
            assert stale.metadata_json.get("cognitiveDemoScore") is None
            reader_ready.set()
            assert writer_done.wait(10)
            refreshed = locked_assessment_visit(db, db.get(User, user_id), visit_id)
            if assessment_first:
                mmse.merge_scan_metadata(refreshed, {"shape": [24, 24, 24]})
            else:
                mmse.complete(refreshed, assessment_id, revision)
            db.commit()

    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(waiting_writer)
        assert reader_ready.wait(10)
        with factory() as db:
            locked = locked_assessment_visit(db, db.get(User, user_id), visit_id)
            if assessment_first:
                mmse.complete(locked, assessment_id, revision)
            else:
                mmse.merge_scan_metadata(locked, {"shape": [24, 24, 24]})
            db.commit()
        writer_done.set()
        pending.result(timeout=15)
    with factory() as db:
        metadata = db.get(Visit, visit_id).metadata_json
        assert metadata["cognitiveDemoScore"] == 30
        assert metadata["MMSE"] == 24
        assert metadata["shape"] == [24, 24, 24]
    engine.dispose()
