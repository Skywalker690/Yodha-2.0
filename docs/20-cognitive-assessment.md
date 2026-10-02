# Guided Cognitive Assessment

## Delivered English demo

The user requested original English demo questions because authorized MMSE content
is not available. Alzhio provides an **MMSE-style demo** with eleven task groups and
a 30-point maximum. The prompts and rubrics are original demonstration material,
not the published MMSE. The result is a **Demo cognitive score**, never a clinical
MMSE measurement or diagnostic category.

Open an uploaded patient case, select a visit and click **Start assessment**. The
clinician administers the tasks, records the points earned for each task group,
and can open the scoring guide. The patient should not see the clinician's rubric.
Object naming uses real objects chosen by the clinician; writing, spoken responses
and drawing are observed rather than AI-graded. The drawing task displays original
overlapping rectangles. No raw answers, writing, drawings or audio are stored.

Tasks progress one at a time. **Save draft & close** persists progress; **Resume
assessment** loads the first unscored task. Closing with X or Escape discards edits
since the last save, but keeps the saved draft. Parent patient polling does not
reset local edits. Review all results and the assessment date/time before clicking
**Complete assessment**. The backend calculates the total; there is no editable
total field. Point controls offer numeric scores only. Unanswered tasks remain null
and block completion, unlike a valid administered zero-point result.

The controls are shared by ML-only and retained research workspaces. Imported OASIS
cases show their preserved recorded MMSE instead of offering assessment writes.
The dashboard now selects recorded visits independently of completed anatomy and
shows clinical and demo values before MRI processing.

## Storage and compatibility

The existing `Visit.metadata_json` stores `mmseAssessment.schemaVersion=1` and at
most ten attempts per visit. Each attempt stores a frozen definition/fingerprint,
instrument/version/language, authenticated clinician, assessed/completed timestamps,
draft revision, point map, calculated totals and superseded attempt ID. Completed
attempts are immutable; a new assessment supersedes the previous result explicitly.
A partial draft does not replace a completed score.

Demo completion writes `cognitiveDemoScore`; it does not create or modify `MMSE`.
Thus existing model inputs, OASIS observations, trained features and forecast gates
remain compatible. Patient/list payloads expose only a small assessment summary,
not rubric content, draft answers or clinician IDs. The owned start/resume endpoint
returns the saved draft/definition without clinician IDs.

Alzhio Bot receives the latest completed demo score in a separately labeled
`demoCognitiveAssessment` object, never in `recordedClinicalValues.MMSE`. No raw
task records or clinician IDs are included. Only newly requested replies use updated
context. Existing analysis input snapshots and generated reports are preserved;
new analyses capture their own current standard clinical inputs. Forecasting for
uploaded cases remains unavailable under the existing OASIS-only adapter.

MRI uploads merge shape/voxel-size metadata into existing clinical metadata using
a fresh JSON assignment. Both upload and assessment writes read refreshed state
after acquiring the visit row lock. This prevents a stale SQLAlchemy identity-map
value from erasing a concurrent write. Draft revisions reject stale saves with 409.

## API

- `POST /visits/{id}/mmse` with `{}` starts or resumes a draft.
- `PATCH /visits/{id}/mmse/{assessment_id}` saves `{revision, assessedAt, items}`.
  Each item is `{itemId, points}` with integer points or null. The assessment time
  must include a timezone and cannot be in the future. This replaces the draft's
  complete item map, not a partial patch of individual entries.
- `POST /visits/{id}/mmse/{assessment_id}/complete` with `{revision}` validates and
  calculates the saved result. Repeating completion returns the same record.

All endpoints require the existing session and patient ownership. Assessments are
checked against their requested visit; unknown/duplicate tasks, out-of-range or
non-integer points, browser-supplied totals and unexpected fields are rejected.
Browser CORS includes PATCH. Imported OASIS cases reject assessment writes with 409.

## Optional authorized original-MMSE protocol

The default demo needs no key, new service, migration or training. A clinician who
later obtains authorized digital questionnaire material can configure a local JSON
file through `MMSE_PROTOCOL_PATH`. The original-MMSE branch writes a completed
standard total to `MMSE`; this branch has only been exercised with synthetic fixtures.
This is a configuration option, not a claim that Alzhio has licensed or validated
questionnaire content. Do not relabel demo material as a standard instrument.

The JSON has `instrument: "mmse-original"`, a nonempty `version`, `language`,
`content_reference` and eleven `items`. Each item contains `id`, `title`,
`max_points`, the authorized `prompt` and authorized `rubric`. The exact ordered
ID/maximum pairs are:

```text
time_orientation:5, place_orientation:5, registration:3, attention:5,
recall:3, naming:2, repetition:1, comprehension:3, reading:1, writing:1,
drawing:1
```

Files are bounded to 64 KiB and invalid configuration returns 503. Resume uses the
definition frozen at assessment start, so later configuration changes cannot change
an existing attempt's content or scoring. The standard instrument's stimuli and
physical tasks must be administered from the authorized materials; the original
demo rectangle illustration is displayed only for the demo instrument.

In Docker, put the file under the existing local storage mount and use its container
path, for example `/app/storage/mmse/authorized-english.json`, in the ignored root
`.env`. Compose passes `.env` through to the backend. On host development use an
absolute local path. Do not commit questionnaire material or patient records.
Use the publisher's required permissions for digital formats/translations.
[MMSE](https://www.parinc.com/products/MMSE), [MMSE-2](https://www.parinc.com/products/MMSE-2).

## Verification evidence

On 2026-10-03, 54 focused backend tests passed, including the new assessment tests,
existing patient/upload/chatbot regressions and eight ML-only serving checks. Two additional real PostgreSQL
checks in a disposable isolated database verified stale writer refresh and data
preservation in both operation orders. All 67 frontend tests, TypeScript and the
production build passed. The Edge assessment workflow verified draft/resume,
eleven task groups, server completion and separate demo score display. Desktop and
390px mobile screenshots were reviewed; the review area scrolls inside the dialog.

Tests use synthetic patients, prompts and scoring fixtures. They establish arithmetic
and integration behavior, not cognitive-test validity or clinical accuracy.

The local backend image was rebuilt and activated; its health check and three live
assessment routes were verified. The existing MRI worker and PostgreSQL remained
running. Frontend host development serves the updated UI.

Run focused backend checks with:

```text
python -m pytest tests/test_mmse_api.py tests/test_assistant_api.py tests/test_api.py -q
python -m ruff check backend tests/test_mmse_api.py tests/test_mmse_concurrency.py
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e -- tests/e2e/mmse.spec.ts
```

`tests/test_mmse_concurrency.py` is optional and requires `MMSE_TEST_DATABASE_URL`
pointing only at the named disposable `alzhio-mmse-concurrency-db` container. It must
not run against the application database. The isolated test container was removed
after verification. No provider call or patient data was sent during tests.
