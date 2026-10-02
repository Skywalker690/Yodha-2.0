from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
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
    output_mode: Literal["demo", "precomputed", "inference", "trained", "anatomy"] = "inference"
    future_interval_days: int = Field(default=365, ge=0, le=3650)


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


class AnatomyReview(Schema):
    visual_review_confirmed: Literal[True]


class AnatomyForecastCreate(Schema):
    interval_days: int = Field(ge=0, le=3650)
    cutoff_visit_id: str | None = Field(default=None, min_length=1, max_length=64)


class AssistantMessage(Schema):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class AssistantRequest(Schema):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=1000)
    history: list[AssistantMessage] = Field(default_factory=list, max_length=6)
    use_research_sources: bool = False

    @field_validator("question")
    @classmethod
    def nonempty_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Enter a question")
        return value.strip()


class AssistantSource(Schema):
    title: str
    url: str
    supported_text: list[str] = Field(default_factory=list)


class AssistantContextSummary(Schema):
    visit_count: int
    clinical_fields_used: list[str]
    anatomy_included: bool
    anatomy_reviewed: bool
    forecast_included: bool
    raw_mri_sent: Literal[False] = False


class AssistantResponse(Schema):
    answer: str
    sources: list[AssistantSource]
    search_suggestions: str | None = None
    research_requested: bool
    context_summary: AssistantContextSummary
    model: str
    disclaimer: str
