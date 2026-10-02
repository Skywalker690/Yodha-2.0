"""One local GPU slot shared by the existing worker and offline training."""

import time
from contextlib import contextmanager
from collections.abc import Iterator

from sqlalchemy import text

from backend.app.db.session import engine

GPU_LOCK = 202610024


@contextmanager
def gpu_slot(*, wait: bool = True) -> Iterator[bool]:
    if engine.dialect.name != "postgresql":
        yield True
        return
    with engine.connect() as connection:
        acquired = False
        try:
            while True:
                acquired = bool(
                    connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": GPU_LOCK}).scalar()
                )
                connection.commit()
                if acquired or not wait:
                    break
                time.sleep(1)
            yield acquired
        finally:
            if acquired:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": GPU_LOCK})
                connection.commit()
