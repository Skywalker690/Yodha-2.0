from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Schema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class Login(Schema):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class PatientCreate(Schema):
    code: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{1,63}$")
    age: int | None = Field(default=None, ge=18, le=120)
    sex: Literal["Female", "Male", "Other", "Unspecified"] | None = None
    notes: str = Field(default="", max_length=1000)


class VisitCreate(Schema):
    label: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9 _-]+$")
    days_from_baseline: int = Field(ge=0, le=36500)


class AnalysisCreate(Schema):
    output_mode: Literal["demo", "precomputed", "inference", "trained"] = "inference"


class AnalysisOut(Schema):
    id: str
    patient_id: str
    visit_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    progress: int
    stage: str
    output_mode: str
    model_version: str
    score: float | None
    confidence: float | None
    result_json: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime
