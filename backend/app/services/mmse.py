"""Owned, versioned assessment records and deterministic MMSE point calculation.

Questionnaire content is supplied locally by the clinician, not generated or bundled.
The fixed domain maxima are facts; the configured rubric governs item performance.
"""

import hashlib
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from backend.app.core.config import get_settings
from backend.app.models import Visit
from backend.app.schemas.contracts import MMSEDraftSave

DOMAINS = (
    ("time_orientation", 5),
    ("place_orientation", 5),
    ("registration", 3),
    ("attention", 5),
    ("recall", 3),
    ("naming", 2),
    ("repetition", 1),
    ("comprehension", 3),
    ("reading", 1),
    ("writing", 1),
    ("drawing", 1),
)
MAX_ATTEMPTS = 10
KEY = "mmseAssessment"


class ProtocolItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=100)
    max_points: int = Field(ge=1, le=5)
    prompt: str = Field(min_length=1, max_length=2000)
    rubric: str = Field(min_length=1, max_length=3000)


class Protocol(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    instrument: str = Field(pattern=r"^(mmse-original|alzhio-cognitive-demo)$")
    version: str = Field(min_length=1, max_length=64)
    language: str = Field(min_length=1, max_length=64)
    content_reference: str = Field(min_length=1, max_length=300)
    items: list[ProtocolItem] = Field(min_length=11, max_length=11)

    @model_validator(mode="after")
    def standard_allocation(self) -> "Protocol":
        if tuple((item.id, item.max_points) for item in self.items) != DOMAINS:
            raise ValueError("Use the original MMSE domain order and 30-point allocation")
        if any(not item.prompt.strip() or not item.rubric.strip() for item in self.items):
            raise ValueError("An authorized prompt and scoring rubric are required for every task")
        return self


def demo_protocol() -> dict:
    """Original demo prompts; not the published MMSE questionnaire or rubric."""
    tasks = (
        (
            "Time awareness",
            "Tell me the current year, month, date, weekday and approximate time of day.",
            "Give one point for each accurate component. Record the assessment's local time; allow an appropriate morning/afternoon/evening description.",
        ),
        (
            "Place awareness",
            "Describe where you are: the country, state or region, town, building or setting, and room or area.",
            "Give one point for each accurate component. The clinician establishes the actual location before administration.",
        ),
        (
            "Immediate memory",
            "Listen to these words: lantern, peach, bicycle. Repeat the three words now and keep them in mind for later.",
            "Record how many words were repeated correctly on the first attempt, from zero to three. This is a demo memory task.",
        ),
        (
            "Concentration",
            "Begin at 40. Subtract 3 repeatedly and tell me the next five numbers.",
            "The demo sequence is 37, 34, 31, 28, 25. Give one point for each correct position. This differs from standardized MMSE administration.",
        ),
        (
            "Delayed memory",
            "Tell me the three words from the earlier memory task, without looking back.",
            "Give one point for each recalled target word without hints: lantern, peach, bicycle. Order is not scored in this demo.",
        ),
        (
            "Object naming",
            "The clinician shows two familiar objects individually. Tell me what each object is called.",
            "Choose two real, visible objects and record one point for each correct name. Do not reveal their names in the patient prompt.",
        ),
        (
            "Sentence repetition",
            "Repeat this sentence: The small bird rested beside the window.",
            "Give one point when the complete spoken sentence is repeated correctly. Observe speech rather than asking the patient to copy visible text.",
        ),
        (
            "Following directions",
            "Touch your shoulder, point toward the door, then place your hands on your lap.",
            "Give one point for each action performed as instructed. Record an unadministered state if an action cannot safely be attempted.",
        ),
        (
            "Reading",
            "Read this instruction and perform it: Touch your chin.",
            "Give one point for performing the written instruction. Have the patient read the prompt rather than reading it aloud for them.",
        ),
        (
            "Writing",
            "Write one complete sentence about an activity you enjoyed recently.",
            "Give one point for an independently written sentence expressing a complete thought. This demo does not score spelling or punctuation.",
        ),
        (
            "Shape copying",
            "Copy the two overlapping rectangles shown in the drawing area.",
            "Give one point when two four-sided shapes overlap in the copy. This original demo shape and rubric are not the MMSE drawing task.",
        ),
    )
    result = {
        "instrument": "alzhio-cognitive-demo",
        "version": "english-demo-v1",
        "language": "English",
        "content_reference": "Original Alzhio demonstration tasks; not a standardized MMSE",
        "items": [
            {"id": item_id, "max_points": maximum, "title": task[0], "prompt": task[1], "rubric": task[2]}
            for (item_id, maximum), task in zip(DOMAINS, tasks)
        ],
    }
    result["fingerprint"] = hashlib.sha256(repr(result).encode()).hexdigest()
    return result


def load_protocol() -> dict:
    path: Path | None = get_settings().mmse_protocol_path
    if path is None:
        return demo_protocol()
    try:
        if path.stat().st_size > 65536:
            raise ValueError("Protocol too large")
        raw = path.read_bytes()
        protocol = Protocol.model_validate_json(raw)
    except (OSError, ValueError, ValidationError):
        raise HTTPException(
            503,
            "The configured MMSE questionnaire is missing or invalid. Check its version, language and scoring definition.",
        ) from None
    return {**protocol.model_dump(), "fingerprint": hashlib.sha256(raw).hexdigest()}


def store(visit: Visit) -> dict:
    value = (visit.metadata_json or {}).get(KEY)
    return deepcopy(value) if isinstance(value, dict) else {"schemaVersion": 1, "attempts": []}


def write(visit: Visit, value: dict) -> None:
    visit.metadata_json = {**(visit.metadata_json or {}), KEY: value}


def summary(visit: Visit) -> dict | None:
    attempts = store(visit).get("attempts", [])
    completed = next((item for item in reversed(attempts) if item["status"] == "completed"), None)
    draft = next((item for item in reversed(attempts) if item["status"] == "draft"), None)
    if completed is None and draft is None:
        return None
    result = {
        "status": "completed" if completed else "draft",
        "hasDraft": draft is not None,
        "completedCount": sum(item["status"] == "completed" for item in attempts),
    }
    if completed:
        result.update(
            {
                key: completed[key]
                for key in (
                    "id",
                    "total",
                    "sectionTotals",
                    "instrument",
                    "version",
                    "language",
                    "assessedAt",
                    "completedAt",
                )
            }
        )
    return result


def public_metadata(visit: Visit) -> dict:
    metadata = {key: value for key, value in (visit.metadata_json or {}).items() if key != KEY}
    if result := summary(visit):
        metadata[KEY] = result
    return metadata


def public_assessment(attempt: dict) -> dict:
    return {key: value for key, value in attempt.items() if key != "clinicianId"}


def ensure_editable_case(patient_source: str) -> None:
    if patient_source == "oasis-2":
        raise HTTPException(
            409,
            "Imported study scores are preserved. Administer a new assessment on an uploaded patient case.",
        )


def start(visit: Visit, clinician_id: str) -> dict:
    value = store(visit)
    for attempt in value["attempts"]:
        if attempt["status"] == "draft":
            return attempt
    if len(value["attempts"]) >= MAX_ATTEMPTS:
        raise HTTPException(
            409,
            "This visit has reached its ten-assessment limit. Add a new visit for subsequent assessments.",
        )
    protocol = load_protocol()
    previous = next((item for item in reversed(value["attempts"]) if item["status"] == "completed"), None)
    attempt = {
        "id": str(uuid4()),
        "status": "draft",
        "revision": 0,
        "instrument": protocol["instrument"],
        "version": protocol["version"],
        "language": protocol["language"],
        "definition": protocol,
        "clinicianId": clinician_id,
        "assessedAt": datetime.now(timezone.utc).isoformat(),
        "completedAt": None,
        "items": {},
        "sectionTotals": None,
        "total": None,
        "supersedes": previous["id"] if previous else None,
    }
    value = {**value, "attempts": [*value["attempts"], attempt]}
    write(visit, value)
    return attempt


def find(visit: Visit, assessment_id: str) -> tuple[dict, dict]:
    value = store(visit)
    attempt = next((item for item in value["attempts"] if item["id"] == assessment_id), None)
    if attempt is None:
        raise HTTPException(404, "Assessment not found on this visit.")
    return value, attempt


def check_revision(attempt: dict, revision: int) -> None:
    if attempt["revision"] != revision:
        raise HTTPException(
            409, "This assessment changed in another session. Reopen it to load the saved version."
        )


def save(visit: Visit, assessment_id: str, body: MMSEDraftSave) -> dict:
    value, attempt = find(visit, assessment_id)
    if attempt["status"] != "draft":
        raise HTTPException(409, "Completed assessments cannot be edited. Start a new assessment revision.")
    check_revision(attempt, body.revision)
    maxima = dict(DOMAINS)
    points = {}
    for item in body.items:
        if item.item_id not in maxima or item.item_id in points:
            raise HTTPException(422, "Unknown or duplicate assessment task.")
        if item.points is not None and item.points > maxima[item.item_id]:
            raise HTTPException(422, "Task points exceed the protocol maximum.")
        points[item.item_id] = item.points
    if body.assessed_at > datetime.now(timezone.utc):
        raise HTTPException(422, "Assessment time cannot be in the future.")
    attempt.update(items=points, assessedAt=body.assessed_at.isoformat(), revision=attempt["revision"] + 1)
    write(visit, value)
    return attempt


def score(points: dict) -> tuple[dict[str, int], int]:
    maxima = dict(DOMAINS)
    if set(points) != set(maxima) or any(points[key] is None for key in maxima):
        raise HTTPException(422, "Administer and score every required task before completing the assessment.")
    if any(type(points[key]) is not int or not 0 <= points[key] <= maximum for key, maximum in DOMAINS):
        raise HTTPException(422, "Invalid assessment points.")
    return dict(points), sum(points.values())


def complete(visit: Visit, assessment_id: str, revision: int) -> dict:
    value, attempt = find(visit, assessment_id)
    if attempt["status"] == "completed":
        return attempt
    check_revision(attempt, revision)
    sections, total = score(attempt["items"])
    attempt.update(
        status="completed",
        sectionTotals=sections,
        total=total,
        completedAt=datetime.now(timezone.utc).isoformat(),
        revision=revision + 1,
    )
    write(visit, value)
    score_key = "MMSE" if attempt["instrument"] == "mmse-original" else "cognitiveDemoScore"
    visit.metadata_json = {**visit.metadata_json, score_key: total}
    return attempt


def merge_scan_metadata(visit: Visit, scan: dict) -> None:
    # A fresh assignment is important: SQLAlchemy's plain JSON column is not mutable-tracked.
    visit.metadata_json = {**(visit.metadata_json or {}), **scan}
