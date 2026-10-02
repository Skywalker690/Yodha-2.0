# Clinical Assistant

The patient workspace includes a Gemini-powered chat card with four suggested questions,
temporary follow-up history and optional Google Search references. This is a hackathon
research demonstration; use synthetic/OASIS de-identified cases and omit identifiers in
questions. The application sends structured values and recent messages to Google.

## Setup

Add these settings to the ignored root `.env` locally:

```text
GEMINI_API_KEY=your-key-from-google-ai-studio
GEMINI_MODEL=gemini-2.5-flash
GEMINI_SEARCH_ENABLED=true
```

Do not place the key in `NEXT_PUBLIC_*`, frontend configuration, screenshots or commits.
The key is optional: the existing app starts without it, and chat returns a helpful 503
configuration error. The model name is configurable; choose a model available in your
project that supports generateContent and Google Search grounding. Internet/quota are
required. No added Python/Node dependency is needed; the backend already uses httpx.

For Docker, build the backend/frontend images and recreate only those services:

```powershell
docker compose build backend frontend
docker compose up -d --no-deps backend frontend
```

This intentionally leaves the existing MRI worker running. On host development, restart
the FastAPI process after updating the environment and start/restart Next.js normally.

## Data and API

`POST /patients/{patient_id}/assistant` uses current_user and owned_patient. The request
accepts `question` (1–1000 characters), `history` (up to six user/assistant messages,
12000 characters each) and `useResearchSources` (default false). Extra fields and system
roles are rejected. The synchronous FastAPI handler runs external I/O in the normal thread
pool, releases its read transaction first and does no MRI inference or database writes.

The context contains age/sex, finite numeric source covariates, chronological observation
numbers/days, completed anatomy and its QC/automatic-rating status, and the existing
forecast adapter's availability. Up to 20 visits are included (baseline plus newest 19
for longer histories). Unreviewed measurements remain visibly experimental. Forecast
probabilities remain null when the existing release gates do not permit serving. Archived
historical classifiers are excluded in ML-only mode. Raw MRI, UUIDs, codes, visit labels,
notes, owner email, reviewer IDs, paths and storage keys are excluded.

Responses include plain text, HTTPS sources from grounding metadata, source-supported
passages, optional provider search suggestions, context summary, model and a review
disclaimer. Provider HTML is limited to Google's search-suggestion widget in a sandboxed
iframe with scripts and same-origin access disabled. Model answers are escaped text.
Search results can include non-paper web pages; the UI calls them Web references.

Chat is held only in React state. Polling keeps the conversation, while leaving the page,
switching patients or Clear resets it. Pending browser requests are aborted on unmount;
the backend/provider may finish an already-started request. Failed questions stay editable
and retry without adding a duplicate history turn. There are no database chat tables,
provider file uploads or application logs of prompt bodies. Gemini's own retention still
applies; unpaid services must not receive real patient/sensitive data.

## Failure behavior

Missing key/disabled search or rejected configuration returns 503; quota exhaustion 429;
provider/network/malformed/blocked responses 502; timeout 504. Responses hide provider
bodies and credentials. Provider call timeout is 40 seconds, browser deadline 50 seconds.
No automatic retries or fabricated fallback answers. Empty grounding displays an explicit
no-reference message. A token-limited answer is marked truncated.

## Verification

```powershell
python -m pytest tests/test_assistant_api.py -q
python -m ruff check backend tests/test_assistant_api.py
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
```

Backend tests use synthetic records, isolated SQLite and mocked HTTP transport. They cover
authorization, filtered context, missingness, ML-only policy, bounded inputs, optional
configuration, history, source resolution, safe errors and timeout. UI checks cover
follow-up history, polling stability, sources, retry, late replies on patient switches
and Clear. Live generation requires a configured key and available quota; mocked results
are never displayed as live model output.

Official references: [generateContent REST](https://ai.google.dev/api/generate-content),
[Google Search grounding](https://ai.google.dev/gemini-api/docs/generate-content/google-search),
[Gemini data policy](https://ai.google.dev/gemini-api/docs/zdr).

## Verification evidence (2026-10-03)

Frontend: 61 unit tests, strict TypeScript, production build and the Edge assistant
workflow passed. The browser workflow uses synthetic fixtures, checks follow-up history,
returned reference links, provider configuration errors, Clear and a 390px mobile layout;
desktop/mobile screenshots were inspected. All 76 selected backend regression tests
passed, including 21 assistant tests; Ruff passed.
The broader selected Python run passed 116 tests but failed 16 existing reference/trained
tests because the runtime lacks the bundled nWBV JSON, SimpleITK or `src.data` modules.
The full suite also cannot collect the existing anatomy/forecast tests without those
dependencies. This feature does not change those files or model behaviors.

The current backend was rebuilt and activated; PostgreSQL and the existing MRI worker
remained running. Live Gemini generation is pending local API-key configuration. No
provider call or real patient content was sent during verification.
