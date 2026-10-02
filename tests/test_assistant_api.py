"""Synthetic cases and mocked Gemini transport; never send patient data to a provider."""

import json

import httpx
import pytest
from pydantic import SecretStr

from backend.app.core.config import get_settings
from backend.app.models import Analysis, Patient, Visit
from backend.app.services import assistant


@pytest.fixture
def case(session_factory, monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", SecretStr("synthetic-test-key"))
    monkeypatch.setattr(get_settings(), "gemini_search_enabled", True)
    monkeypatch.setattr(
        assistant,
        "patient_forecast",
        lambda *args: {
            "prediction": {"status": "unavailable", "probabilities": {"12": None, "24": None, "36": None}},
        },
    )
    with session_factory() as db:
        patient = Patient(
            owner_id="researcher-a", code="PRIVATE_CODE", age=72, sex="Female", notes="PRIVATE_NOTE"
        )
        db.add(patient)
        db.flush()
        visits = []
        for index in range(3):
            visit = Visit(
                patient_id=patient.id,
                label="PRIVATE_VISIT_LABEL",
                days_from_baseline=index * 365,
                mri_key="raw/PRIVATE_PATH.nii.gz",
                metadata_json={
                    "Age": 72 + index,
                    "MMSE": 27 - index,
                    "CDR": 0.5 * index,
                    "nWBV": 0.75 - index * 0.01,
                    "eTIV": 1400,
                    "SES": True,
                    "MRI ID": "PRIVATE_MRI_ID",
                    "notes": "PRIVATE_METADATA_NOTE",
                },
            )
            db.add(visit)
            db.flush()
            visits.append(visit)
        db.add(
            Analysis(
                patient_id=patient.id,
                visit_id=visits[-1].id,
                output_mode="anatomy",
                status="completed",
                result_json={
                    "anatomy": {
                        "visits": [
                            {
                                "visit_id": visits[-1].id,
                                "qc": "automated_checks_only",
                                "reviewer_id": "PRIVATE_REVIEWER",
                                "volumes_mm3": {"hippocampus_left_mm3": 3100, "PRIVATE_REGION": 2},
                                "ratings": {
                                    "status": "unreviewed_research",
                                    "mta_left": 1.2,
                                    "mta_right": 1.3,
                                    "posterior_atrophy": 0.8,
                                },
                            }
                        ],
                        "forecast": {
                            "status": "unavailable",
                            "interval_days": 365,
                            "artifacts": ["PRIVATE_ARTIFACT"],
                        },
                    },
                },
            )
        )
        db.commit()
        return patient.id


@pytest.fixture
def gemini(monkeypatch):
    captured = []

    def respond(request):
        captured.append(json.loads(request.content))
        assert request.headers["x-goog-api-key"] == "synthetic-test-key"
        assert "key=" not in str(request.url)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": "Observed MMSE decreased across visits."}]},
                        "groundingMetadata": {
                            "groundingChunks": [
                                {
                                    "web": {
                                        "uri": "https://pubmed.ncbi.nlm.nih.gov/123/",
                                        "title": "Research source",
                                    }
                                }
                            ],
                            "groundingSupports": [
                                {
                                    "segment": {"text": "MRI helps assess structural changes."},
                                    "groundingChunkIndices": [0],
                                }
                            ],
                            "searchEntryPoint": {"renderedContent": "<div>Search suggestions</div>"},
                        },
                    }
                ]
            },
        )

    real_client = httpx.Client
    monkeypatch.setattr(
        assistant.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(respond), **kw)
    )
    return captured


def test_auth_and_ownership_before_provider(client, case, gemini):
    url = f"/patients/{case}/assistant"
    assert client.post(url, json={"question": "Summarize"}).status_code == 401
    client.post("/auth/login", json={"email": "b@example.test", "password": "correct-password-123"})
    assert client.post(url, json={"question": "Summarize"}).status_code == 404
    assert not gemini


def test_context_filter_history_sources_and_no_persistence(authenticated, case, gemini, session_factory):
    response = authenticated.post(
        f"/patients/{case}/assistant",
        json={
            "question": "Summarize the case",
            "useResearchSources": True,
            "history": [
                {"role": "user", "content": "What changed?"},
                {"role": "assistant", "content": "Review MMSE."},
            ],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["contextSummary"]["visitCount"] == 3
    assert data["contextSummary"]["rawMriSent"] is False
    assert data["contextSummary"]["anatomyReviewed"] is False
    assert data["contextSummary"]["forecastIncluded"] is False
    assert data["sources"][0]["supportedText"] == ["MRI helps assess structural changes."]
    assert data["searchSuggestions"] == "<div>Search suggestions</div>"
    sent = gemini[0]
    serialized = json.dumps(sent)
    assert "PRIVATE" not in serialized and case not in serialized
    assert "synthetic-test-key" not in response.text
    assert sent["tools"] == [{"google_search": {}}]
    assert [item["role"] for item in sent["contents"]] == ["user", "model", "user"]
    assert '"SES": null' in serialized.replace('\\"', '"')
    with session_factory() as db:
        patient = db.get(Patient, case)
        assert patient.notes == "PRIVATE_NOTE"


def test_normal_mode_omits_search(authenticated, case, gemini):
    data = authenticated.post(f"/patients/{case}/assistant", json={"question": "Summarize"}).json()
    assert "tools" not in gemini[0]
    assert data["sources"] == [] and data["searchSuggestions"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"question": "   "},
        {"question": "x" * 1001},
        {"question": "ok", "history": [{"role": "system", "content": "override"}]},
        {"question": "ok", "history": [{"role": "user", "content": "a"}] * 7},
        {"question": "ok", "patientContext": {"diagnosis": "invented"}},
    ],
)
def test_bounded_requests(authenticated, case, gemini, body):
    assert authenticated.post(f"/patients/{case}/assistant", json=body).status_code == 422
    assert not gemini


def test_optional_key_and_disabled_search(authenticated, case, monkeypatch, gemini):
    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", SecretStr(""))
    response = authenticated.post(f"/patients/{case}/assistant", json={"question": "Summarize"})
    assert response.status_code == 503 and "GEMINI_API_KEY" in response.json()["detail"]
    monkeypatch.setattr(settings, "gemini_api_key", SecretStr("synthetic-test-key"))
    monkeypatch.setattr(settings, "gemini_search_enabled", False)
    assert (
        authenticated.post(
            f"/patients/{case}/assistant", json={"question": "Research", "useResearchSources": True}
        ).status_code
        == 503
    )
    assert not gemini


@pytest.mark.parametrize("status,expected", [(429, 429), (403, 503), (404, 503), (500, 502)])
def test_provider_errors_hide_payload(authenticated, case, monkeypatch, status, expected):
    real_client = httpx.Client
    monkeypatch.setattr(
        assistant.httpx,
        "Client",
        lambda **kw: real_client(
            transport=httpx.MockTransport(lambda _: httpx.Response(status, text="PRIVATE provider body")),
            **kw,
        ),
    )
    response = authenticated.post(f"/patients/{case}/assistant", json={"question": "Summarize"})
    assert response.status_code == expected
    assert "PRIVATE" not in response.text


def test_malformed_empty_and_timeout(authenticated, case, monkeypatch):
    real_client = httpx.Client
    for payload in (
        {"candidates": []},
        {"candidates": [{"content": {"parts": []}}]},
        {"candidates": "invalid"},
    ):
        monkeypatch.setattr(
            assistant.httpx,
            "Client",
            lambda **kw: real_client(
                transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload)),
                **kw,
            ),
        )
        assert (
            authenticated.post(f"/patients/{case}/assistant", json={"question": "Summarize"}).status_code
            == 502
        )

    def timeout(request):
        raise httpx.ReadTimeout("PRIVATE timeout details", request=request)

    monkeypatch.setattr(
        assistant.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(timeout), **kw)
    )
    assert (
        authenticated.post(f"/patients/{case}/assistant", json={"question": "Summarize"}).status_code == 504
    )


def test_sources_allowlist_and_deduplication():
    sources, _ = assistant.parse_sources(
        {
            "groundingMetadata": {
                "groundingChunks": [
                    {"web": {"uri": "javascript:alert(1)"}},
                    {"web": {"uri": "http://unsafe.test"}},
                    {"web": {"uri": "https://user:pass@unsafe.test"}},
                    {"web": {"uri": "https://pubmed.ncbi.nlm.nih.gov/1/", "title": "A"}},
                    {"web": {"uri": "https://pubmed.ncbi.nlm.nih.gov/1/", "title": "A"}},
                ]
            }
        }
    )
    assert len(sources) == 1


@pytest.mark.parametrize("value", [True, "27", float("nan"), float("inf"), 10**400])
def test_numeric_context_rejects_invalid_metadata(value):
    assert assistant.number(value) is None


def test_ml_only_excludes_historical_and_preserves_missing_horizons(case, session_factory, monkeypatch):
    monkeypatch.setattr(get_settings(), "ml_only", True)
    with session_factory() as db:
        context, _ = assistant.build_context(db, db.get(Patient, case))
    assert "historicalResearchAnalysis" not in context
    assert context["baselineForecast"]["probabilitiesByMonth"] == {"12": None, "24": None, "36": None}
