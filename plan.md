# NeuroPredict AI Context-Aware Chatbot — 5-Hour Hackathon Plan

Status: simplified implementation plan for a hackathon demo.

## 1. The demo story

When a doctor opens a patient in NeuroPredict AI, a **Clinical Assistant** panel already knows the structured context currently visible in the system:

- patient age and sex;
- available visits and their chronology;
- recorded MMSE, CDR, nWBV and eTIV values;
- completed MRI/anatomy measurements;
- forecast availability, model provenance and warnings.

The doctor can ask a question without copying the case into another chat application. The assistant responds with a concise answer, clearly states missing information, and can show current web references when “Research sources” is enabled.

The judge-facing message is:

> “NeuroPredict does not just produce a score. It gives the doctor a context-aware assistant that understands the current longitudinal case, explains what the system found, identifies missing information, and connects the case to cited research.”

## 2. Scope: build only this

### Must-have

1. A chat panel on the existing patient page.
2. Four impressive suggested questions:
   - “Summarize this patient’s longitudinal case.”
   - “What important information is missing?”
   - “Explain the MRI and anatomy findings in simple clinical language.”
   - “Find research relevant to these findings.”
3. One authenticated FastAPI endpoint that builds patient context and calls Gemini.
4. Recent chat context kept in browser memory for follow-up questions.
5. Optional Gemini Google Search grounding with clickable returned citations.
6. Visible safety/provenance banner:
   - de-identified structured context only;
   - raw MRI is not sent;
   - AI output requires doctor review.
7. Loading, configuration-error and retry states.

### Explicitly skip

- local model setup or training;
- fine-tuning;
- vector databases or RAG infrastructure;
- PubMed ingestion pipelines;
- new PostgreSQL tables or Alembic migrations;
- persistent chat history;
- streaming responses;
- PDF ingestion;
- voice input;
- agents, tools, function calling or chart modification;
- raw MRI upload to Gemini;
- a separate worker or queue.

These are possible future improvements, but they do not belong in a five-hour build.

## 3. Simple architecture

```text
Patient page
   |
   | question + last 6 chat turns + research toggle
   v
POST /patients/{patient_id}/assistant
   |
   |-- verify logged-in user owns patient
   |-- read current patient, visits and completed outputs
   |-- build small de-identified context JSON
   |-- add fixed safety/system instructions
   v
Gemini API
   |-- normal generation, or
   `-- Google Search grounding when research toggle is on
   v
answer + returned source links + context summary
   |
   v
Clinical Assistant panel
```

The API key exists only in the FastAPI environment. The frontend never receives it.

## 4. Context sent to Gemini

Build the context fresh from the database for every question so it cannot become stale. Do not trust patient data submitted by the browser.

Example:

```json
{
  "patient": {
    "age": 72,
    "sex": "Female"
  },
  "visits": [
    {
      "label": "Visit 1",
      "daysFromBaseline": 0,
      "MMSE": 27,
      "CDR": 0.0,
      "nWBV": 0.74,
      "eTIV": 1480
    }
  ],
  "latestReviewedAnatomy": {
    "status": "available",
    "qualityStatus": "passed",
    "measurements": {}
  },
  "forecast": {
    "status": "unavailable",
    "reasons": ["No promoted model is available"]
  },
  "limitations": [
    "Research prototype",
    "Not a diagnosis",
    "Unavailable values must not be inferred"
  ]
}
```

### Include

- age and sex;
- chronological visit labels and days from baseline;
- allowlisted numeric clinical fields already stored by NeuroPredict;
- latest completed analysis/anatomy data;
- QC, review, model and availability status;
- existing caveats.

### Do not include

- patient database UUID;
- owner email;
- filesystem paths or storage keys;
- API tokens;
- raw MRI bytes;
- complete reports;
- unrelated patients;
- free-text notes by default, because they may contain names or other identifiers.

For the hackathon, use only OASIS, synthetic or properly de-identified cases. This version must not be presented as safe for real identifiable patient data.

## 5. Gemini integration

Use Gemini's official REST API through the existing httpx dependency in FastAPI.

Environment variables:

```text
GEMINI_API_KEY=
GEMINI_MODEL=
GEMINI_SEARCH_ENABLED=true
```

Keep the model configurable instead of hard-coding a preview model name. Select a currently available Flash-class model in the hackathon account for low latency.

### Request behavior

- maximum question length: 1,000 characters;
- maximum six recent messages;
- only text is sent;
- timeout after approximately 40 seconds;
- temperature kept low;
- no automatic retry storm;
- if the key/model is missing, return a clear `503` configuration message;
- if Gemini fails, show an error—never display a fake fallback answer.

### Fixed system instructions

The prompt should tell Gemini:

1. You assist a qualified doctor reviewing a NeuroPredict research case.
2. Use only the supplied patient facts for patient-specific statements.
3. Never invent missing measurements, diagnoses or events.
4. Clearly separate patient facts from general medical knowledge.
5. Do not prescribe, diagnose or give emergency instructions.
6. Mention uncertainty and important missing data.
7. Preserve warnings about experimental, unreviewed or unavailable outputs.
8. Be concise and clinically readable.
9. When search is enabled, prefer peer-reviewed, government, university and major medical sources.
10. End with: “For clinician review; not a diagnosis or treatment recommendation.”

### Research mode

When the doctor enables **Research sources**, add Gemini’s Google Search grounding tool. Parse the grounding metadata returned by the API and send safe source objects to the frontend:

```json
{
  "title": "Source title",
  "url": "https://..."
}
```

Render only URLs actually returned by Gemini. Do not ask the model to invent a bibliography. Label this feature “Web references” rather than “peer-reviewed papers,” because Google Search may return other reputable sources.

## 6. Minimal API contract

### Request

```http
POST /patients/{patient_id}/assistant
Content-Type: application/json
```

```json
{
  "question": "What changed across the visits?",
  "history": [
    {"role": "user", "content": "Summarize this case."},
    {"role": "assistant", "content": "..."}
  ],
  "useResearchSources": true
}
```

### Response

```json
{
  "answer": "...",
  "sources": [
    {"title": "...", "url": "https://..."}
  ],
  "contextSummary": {
    "visitCount": 3,
    "clinicalFieldsUsed": ["MMSE", "CDR", "nWBV", "eTIV"],
    "anatomyIncluded": true,
    "forecastIncluded": false,
    "rawMriSent": false
  },
  "model": "configured Gemini model",
  "disclaimer": "For clinician review; not a diagnosis or treatment recommendation."
}
```

No chat content is stored in the database. Refreshing or leaving the page clears the conversation.

## 7. Files to change

Keep the change small and aligned with the existing repository:

```text
backend/app/core/config.py
  Add Gemini configuration.

backend/app/schemas/contracts.py
  Add AssistantMessage, AssistantRequest, AssistantSource and AssistantResponse.

backend/app/services/assistant.py
  Build de-identified context, prepare the prompt, call Gemini and parse citations.

backend/app/api/routes.py
  Add the authenticated patient assistant endpoint using owned_patient().

backend/requirements.txt
  No change required; httpx is already installed.

.env.example
  Document Gemini variables without committing a key.

frontend/types/index.ts
  Add request/response/source types.

frontend/components/clinical-assistant.tsx
  Add chat UI, suggestion chips, research toggle, context badge and sources.

frontend/components/analysis-workspace.tsx
  Mount ClinicalAssistant inside both current workspace modes.

frontend/app/globals.css
  Add responsive assistant styling.

tests/test_assistant_api.py
frontend/tests/assistant.test.tsx
  Add focused mocked tests.
```

Do not refactor existing MRI, forecast, anatomy or worker code during this task.

## 8. Five-hour execution schedule

### 0:00–0:30 — Gemini setup and request spike

- create/configure the Gemini API project;
- enable billing if real sensitive data is ever considered;
- add environment settings and an httpx REST call;
- run one backend-only test prompt;
- confirm the chosen model supports Google Search grounding.

Stop early and switch to a supported model if grounding behavior differs from the documentation.

### 0:30–1:30 — Backend endpoint

- add request/response schemas;
- implement deterministic context builder;
- add the authenticated endpoint;
- call Gemini with timeout and safe error handling;
- parse returned citations;
- verify the prompt contains no UUID, path, raw MRI or owner data.

### 1:30–2:45 — Chat interface

- build the chat card;
- add four suggested-question chips;
- keep the last six messages in component state;
- add the research-source toggle;
- show loading, retry and empty states;
- render clickable sources;
- show context/provenance badges.

### 2:45–3:30 — Integration and styling

- mount the panel in the patient workspace;
- make it work in ML-only and research workspace modes;
- make it responsive;
- visually separate user messages, AI responses and sources;
- add a polished header: “Clinical Assistant · Patient context connected.”

### 3:30–4:15 — Focused testing

- ownership test: another user receives `404`;
- missing API key returns `503`;
- mocked Gemini response renders correctly;
- context excludes identifiers and raw paths;
- history and question limits are enforced;
- citations are taken only from returned grounding metadata;
- existing patient page still loads.

### 4:15–5:00 — Demo preparation

- prepare one strong three-visit case;
- pre-write the four questions in the UI;
- confirm the API key, internet and model quota;
- rehearse normal and research answers;
- capture a screenshot as backup;
- run the shortest relevant backend/frontend tests;
- prepare a 90-second judge narrative.

## 9. UI details that create judge impact

Use one polished card rather than many features.

Header:

```text
Clinical Assistant                    Patient context connected
Understands 3 visits · Anatomy available · Raw MRI not shared
```

Show the four question chips immediately. After an answer, show:

- the response;
- a compact “Context used” row;
- “Web references” cards when research mode was enabled;
- the doctor-review disclaimer.

Use the existing NeuroPredict visual language so it looks native rather than pasted into the product.

Useful details:

- animate the loading text through “Reading patient context” and “Reviewing evidence”;
- show `3 visits`, `4 clinical fields`, and `reviewed anatomy` as small badges;
- collapse citations under “Sources used (N)”;
- provide a “Clear conversation” button;
- disable send while a request is running;
- preserve the question on failure so the doctor can retry.

## 10. Privacy statement for the hackathon

Be transparent with judges:

> “This hackathon version sends a minimal, de-identified structured case summary to Gemini. It never uploads raw MRI data and does not persist the chat. We use synthetic/OASIS cases for the demonstration. A clinical deployment would require an approved paid/enterprise data arrangement, organizational privacy review and stronger deployment controls.”

Important Gemini policy implication:

- Google states that unpaid Gemini API services may use submitted content to improve products and may involve human review.
- Google states that paid services do not use prompts/responses to improve products, although limited retention and other conditions can still apply.
- Therefore, **do not use the free tier with real patient or sensitive data**. For guaranteed zero-data-retention or enterprise processing requirements, evaluate Vertex AI and the applicable agreement.

This is not legal or compliance certification.

## 11. Focused acceptance criteria

The MVP is complete when:

- the assistant appears within an existing patient page;
- it answers a suggested question using server-built patient context;
- a follow-up question uses recent conversation history;
- research mode displays at least one API-returned clickable citation when grounding succeeds;
- the UI visibly says raw MRI was not sent;
- another authenticated user cannot query the patient;
- no Gemini key appears in browser code or network responses;
- missing Gemini configuration produces a useful error;
- the current patient workflow remains functional;
- the demo uses only synthetic or de-identified data.

## 12. What to say during the demo

1. Open a patient with three visits.
2. Point to “Patient context connected.”
3. Click “Summarize this patient’s longitudinal case.”
4. Highlight that the answer references the values already in NeuroPredict without manual copying.
5. Ask “What important information is missing?” as a follow-up.
6. Enable Research sources and ask for relevant research.
7. Open one returned citation.
8. Point out: raw MRI not shared, chat not stored, and doctor review required.

Closing line:

> “The prediction model tells us what it calculated; the assistant helps the doctor understand the whole case and verify the evidence without leaving the workflow.”

## 13. Immediate fallback plan

If Google Search grounding consumes too much setup time:

1. keep normal Gemini chat working;
2. hide or disable the Research sources toggle;
3. do not fabricate citations;
4. demonstrate case summary, missing-data detection and model explanation;
5. describe grounded literature search as the next increment.

Three reliable features will impress judges more than a larger unreliable demo.

## 14. Official references

- [Gemini API text generation](https://ai.google.dev/gemini-api/docs/generate-content/text-generation)
- [Grounding with Google Search](https://ai.google.dev/gemini-api/docs/google-search/)
- [Gemini API data and zero-retention guidance](https://ai.google.dev/gemini-api/docs/zdr)
- [Gemini API terms](https://ai.google.dev/gemini-api/terms)
