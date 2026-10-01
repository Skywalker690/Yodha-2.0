import os
import tempfile
from pathlib import Path

# Configure before importing the application; production data is never used for unit tests.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-only-" + "x" * 48
os.environ["SEED_PASSWORD"] = "test-only-password-1234"
os.environ["STORAGE_ROOT"] = tempfile.mkdtemp(prefix="neuropredict-tests-")

import nibabel as nib
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.security import hash_password
from backend.app.db.session import Base, get_db
from backend.app.main import app
from backend.app.models import User
from backend.app.workers import runner


@pytest.fixture
def session_factory(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add(
            User(
                id="researcher-a", email="a@example.test", password_hash=hash_password("correct-password-123")
            )
        )
        db.add(
            User(
                id="researcher-b", email="b@example.test", password_hash=hash_password("correct-password-123")
            )
        )
        db.commit()

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(runner, "SessionLocal", factory)
    yield factory
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def client(session_factory):
    from backend.app.api.routes import attempts

    attempts.clear()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated(client):
    response = client.post(
        "/auth/login", json={"email": "a@example.test", "password": "correct-password-123"}
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def mri(tmp_path: Path) -> Path:
    rng = np.random.default_rng(42)
    x, y, z = np.mgrid[-1:1:24j, -1:1:24j, -1:1:24j]
    data = (np.exp(-4 * (x * x + y * y + z * z)) + rng.random((24, 24, 24)) * 0.05).astype(np.float32)
    path = tmp_path / "scan.nii.gz"
    nib.save(nib.Nifti1Image(data, np.eye(4)), path)
    return path
