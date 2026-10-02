# Alzhio: Standard MMSE Assessment Implementation Plan

Date: 2026-10-03

Imported source-branch planning history. The current implementation is governed by D073 and document 22; this background plan does not replace current product or MRI requirements.

Status: Implemented as an original English MMSE-style demo after the user confirmed authorized questionnaire content is unavailable. Demo totals are saved separately from clinical MMSE. The original standard-content plan below is retained as background; D073 and [the implementation documentation](docs/22-cognitive-assessment.md) describe the delivered behavior and verified checks.

## 1. Agreed scope

Latest clarification: use original English demo tasks and clinician-recorded points,
with deterministic backend totals. The shipped demo publishes `cognitiveDemoScore`,
not `MMSE`. Authorized original-MMSE content can be configured separately, but is
not bundled. The domain/task limits are eleven groups and 30 total points, with no
claim that the demonstration is a standardized instrument. Backend, PostgreSQL,
frontend and browser integration checks are documented in doc 22.

Add a clinician-guided standard MMSE assessment to the existing patient visit workspace. The clinician administers the tasks and records item performance. Alzhio calculates the total on the backend and saves the result directly to the visit. There is no editable total-score field in this workflow.

Use the original standardized 30-point MMSE protocol and an authorized language version. The precise content, administration instructions, item order, point rules and permitted digital presentation must be confirmed before releasing the questionnaire. A different edition requires its own version identifier and reviewed scoring definition.

The earlier request for ten questions per area was clarified by the user in favor of standard MMSE. Do not add extra questions, choose random questions, change task order, generate questions with Gemini, or normalize a custom questionnaire to a supposed MMSE score.

The standard domains are time orientation, place orientation, registration, attention/calculation, recall, naming, repetition, comprehension, reading, writing and drawing. These are task categories, not eleven equally weighted sections. The selected authorized protocol determines their exact items and points. [Official MMSE description](https://www.parinc.com/products/MMSE).

Modified formats and translations have a publisher permission process. Confirm permitted digital use and obtain the appropriate content; this plan does not reproduce the test questionnaire. [Publisher details](https://www.parinc.com/products/MMSE-2).

## 2. User flow

1. Create or open a patient and select an actual visit. A visit can exist before its MRI is uploaded.
2. Click **Start MMSE** next to the visit's MRI controls.
3. Open an accessible dialog showing one task at a time, progress, administration instructions and permitted item-scoring controls.
4. The clinician asks the patient to perform each task and records performance using the rubric. Spoken, physical, writing and drawing tasks are observed by the clinician; no speech recognition or AI grading is needed.
5. Save a draft if the assessment is interrupted. An unadministered item is distinct from an administered task earning zero points.
6. Review the recorded items, then click **Complete assessment**. The backend verifies the protocol and calculates the score.
7. Show **MMSE: N/30**, assessment date and instrument/language beside the selected visit. The score is saved automatically, and patient data reloads.
8. Upload MRI before or after the assessment. Both data sets remain attached to the same visit.

Use the same assessment component in the ML-only and retained research workspace. Keep the controls compact; there is no new dashboard page or patient-facing chat flow. Changing patients/visits must never transfer a draft to another record. Parent polling must not overwrite unsaved local item edits.

## 3. Deterministic scoring

- Keep the reviewed instrument definition in a backend module, including stable item IDs, version, required order, allowed scoring alternatives and maximum points. Expose only the permitted presentation content to the owned assessment UI.
- The browser sends item outcomes/points, not a trusted total. The backend checks them against that definition and computes section sums and the final total.
- The UI may preview a total, but the saved backend result is authoritative.
- Require all items needed by the selected protocol to be administered and scorable before publishing a standard total. If an item cannot be administered, preserve the reason and keep the result incomplete unless the official protocol explicitly supports that situation. Do not fill blanks with zero or prorate a total.
- Record test language and assessment time. Time/place answers are evaluated in the patient's assessment context, not the server's timezone or location.
- Completed records are immutable. A correction produces a new revision and explicitly supersedes the previous record; it does not silently edit an earlier result.
- Display the score and recorded change without inventing diagnostic thresholds, severity categories or model probabilities.

This automates total calculation and recording. The clinician still assesses performance according to the instrument instructions.

## 4. Persistence and API

Reuse `Visit.metadata_json`; the existing JSON column permits an MVP without an Alembic migration. Store a versioned `mmseAssessment` object containing the active assessment ID, draft, completed revisions and the selected completed result. Bound request sizes and retained revision counts so patient-list polling stays small. A dedicated assessment table can be considered later if assessment volume warrants it.

Each record includes:

- server-generated assessment ID, schema version and instrument/scoring version;
- language, clinical assessment timestamp and separate server completion timestamp;
- clinician ID taken from the authenticated session;
- draft/completed/incomplete status, optimistic revision number and optional superseded ID;
- item IDs, clinician-recorded item points and administered/unadministered state;
- backend-calculated domain totals and total, which is null until valid completion.

Avoid collecting verbatim answers, written sentences, drawings or audio for the MVP. Clinician item scoring is sufficient; storing these artifacts adds privacy, storage and interpretation work.

Proposed endpoints, using the existing authentication and `owned_visit` checks:

| Endpoint | Responsibility |
|---|---|
| `POST /visits/{visit_id}/mmse` | Start or resume the active draft using a supported protocol; return its ID, definition and owned saved draft. |
| `PATCH /visits/{visit_id}/mmse/{assessment_id}` | Save a bounded draft using an expected revision number. |
| `POST /visits/{visit_id}/mmse/{assessment_id}/complete` | Validate saved items, calculate the score and complete atomically. Repeating completion returns the same completed record. |

Reject unknown/duplicate item IDs, arbitrary score totals, unsupported protocols and invalid points. Verify the assessment belongs to the requested visit. Return 409 on stale revisions instead of overwriting newer edits.

For newly uploaded patient visits, atomically write the valid completed total to `metadata.MMSE` and include its assessment ID/version provenance. Draft saving must not change an existing completed score. Preserve imported OASIS scores and their source: the MVP should administer new tests on new uploaded-case visits, rather than replacing imported study observations. Retesting on the same visit creates an explicit new assessment revision.

The patient payload currently returns visit metadata directly. Add typed, sanitized assessment serialization so large drafts and internal clinician IDs are not unnecessarily repeated in patient-list responses. The owning clinician can retrieve the draft through the owned assessment API; the list/workspace payload needs only its status and completed summary.

## 5. Verified integration risks and required fixes

| Current behavior checked in code | Integration consequence | Required handling |
|---|---|---|
| `Visit.metadata_json` already stores clinical values; frontend `Visit.metadata.MMSE` exists. | Existing readers can consume a standard total. | Preserve the exact uppercase `MMSE` compatibility key; extend types with nullable score and optional assessment summary. |
| `VisitCreate` and `VisitForm` accept only label and days from baseline. | No clinical-entry UI/API exists yet. | Keep visit creation compatible and add the assessment action after a visit exists. |
| MRI upload assigns `visit.metadata_json = metadata` from `render_preview`. That metadata contains shape/voxel sizes. | A score saved before upload would be erased. | Merge scan fields into existing metadata and assign a fresh JSON object so SQLAlchemy persists it. |
| Upload reads the visit before requesting a row lock. | A concurrent assessment save may still be overwritten if the identity-map value is stale. | Lock and refresh the latest visit before the metadata merge. Assessment saves use the same visit-level lock and fresh state. |
| Dashboard source values are hidden unless a completed anatomy visit is selected. | New MMSE scores would not appear before MRI processing. | Select source visits independently of anatomy; render recorded clinical values even when anatomy is unavailable. |
| Both workspace modes share visit controls but have different layouts. | Wiring only one mode would leave the other unsupported. | Mount one shared assessment component in both modes and reuse the selected visit ID. |
| Alzhio Bot reads numeric `metadata.MMSE` server-side on every request. | Completed scores are available to new replies automatically. | Add only instrument/date/completion provenance to its allowlisted context if useful. Never transmit item answers, raw drafts or clinician IDs. Previous replies remain historical. |
| Analyses freeze clinical metadata into `Analysis.input_json`; anatomy reports use those snapshots. | A new or corrected assessment does not update an old report/result. | Show assessment dates and preserve old snapshots. Newly requested analyses/reports capture the completed score at their cutoff; an old report is not rewritten. |
| Forecasting rejects non-OASIS cases and reads `baseline.csv`, not current visit metadata. | MRI plus a new MMSE is insufficient to enable new-patient forecasts. | Keep forecast eligibility unchanged. Adding live uploaded-case prediction requires a separately scoped adapter and input/QC review. |
| Existing model contracts already consume MMSE alongside other covariates. | An invented or partial score would contaminate inputs. | Only completed standardized totals enter `metadata.MMSE`; no extra assessment item features, training or checkpoint changes. |
| Visits are unique by patient and days from baseline. | An additional same-day assessment cannot be modeled by creating a duplicate visit. | Associate repeat attempts with the existing visit; record assessment time separately. |

## 6. Files to change during implementation

| File | Planned change |
|---|---|
| `frontend/components/mmse-assessment.tsx` (new) | Guided dialog, item controls, progress, draft/resume, review and completion. |
| `frontend/components/analysis-workspace.tsx` | Selected-visit action and compact summary in both modes. |
| `frontend/components/patient-values-panel.tsx` | Display recorded clinical scores independently of completed anatomy. |
| `frontend/types/index.ts` | Typed assessment summary and nullable MMSE values. |
| `frontend/app/globals.css` | Scoped dialog styling consistent with Alzhio. |
| `backend/app/schemas/contracts.py` | Strict start/draft/completion/result contracts. |
| `backend/app/services/mmse.py` (new) | Instrument definition, deterministic scoring and metadata merge/persistence helpers. |
| `backend/app/api/routes.py` | Owned assessment endpoints, sanitized summaries and MRI metadata preservation. |
| `backend/app/services/assistant.py` | Small allowlisted completed-score provenance, if needed. |
| `tests/test_mmse_api.py` and `tests/test_mmse_scoring.py` (new) | Scoring, authorization, concurrency and persistence checks. |
| `frontend/tests/mmse-assessment.test.tsx` (new) | Guided completion, draft isolation, patient polling and error recovery. |
| `frontend/tests/e2e/mmse.spec.ts` (new) | Owned patient/visit assessment and MRI order workflow. |
| `docs/03-data-contract.md`, `docs/05-ui-spec.md`, `docs/07-testing-validation.md` | Update implemented contracts, UI behavior and verification evidence. |

No change is required to segmentation, training scripts, workers, checkpoint files, dataset splits or prediction feature definitions. Preserve existing unrelated workspace changes. The current checkout is `clinical-assistant`; the remote `chatbot` branch was published previously. Choose the target branch explicitly during implementation rather than assuming the checkout already changed.

## 7. Implementation order

1. Confirm the authorized original-MMSE content, language, scoring rules and permitted digital presentation. Keep synthetic fixture item IDs separate from real assessment content.
2. Add strict backend assessment contracts, scoring service and owned start/draft/complete endpoints.
3. Fix MRI metadata replacement and concurrency; verify both upload/assessment orders before UI integration.
4. Implement the compact guided dialog in both workspace modes and publish the completed summary after a successful backend response.
5. Show clinical values without an anatomy prerequisite; verify chatbot context and preserve snapshot/report dates.
6. Run focused regressions, production checks and a synthetic desktop/mobile walkthrough. Record the results and publish only after the actual feature is implemented.

## 8. Acceptance checks

- No user-entered total is accepted; the backend reproduces known rubric totals, including zero and maximum score.
- Missing, unadministered and zero-point items remain distinct. Invalid item points, duplicates and malformed content cannot produce a completed score.
- The original score remains untouched while a new draft is in progress. Completing twice does not duplicate a result.
- MRI first / assessment second and assessment first / MRI second preserve the MRI file, preview, shape, voxel sizes, assessment and score.
- Simultaneous upload/save and two stale draft edits do not silently lose data. Test real PostgreSQL locking in addition to isolated API tests.
- Assessment belongs to the correct patient/visit; unauthenticated and cross-owner reads/writes are rejected.
- Draft resumes after page reload, polling does not reset item edits, and switching patient/visit cannot save to the wrong record.
- Score is visible before any MRI/anatomy analysis and persists across backend restart.
- Newly generated chatbot context sees the completed score; drafts, raw responses and clinician IDs are excluded.
- Imported OASIS records, existing analysis snapshots, report artifacts and forecast eligibility remain unchanged.
- Keyboard navigation, focus handling, task progression, clinician review and desktop/mobile dialog layout work.

Planned commands: focused new pytest tests plus `tests/test_api.py`, `tests/test_assistant_api.py` and applicable ML-only/forecast regressions; Ruff; frontend TypeScript and unit tests; production build; the new Playwright workflow. The current import has check records in [doc 22](docs/22-cognitive-assessment.md); this original section records the source branch's planning checklist, not tests imported or run here.

## 9. Challenges and completion boundary

The highest-impact engineering challenge is shared visit-metadata writes; simply adding a score field would lose data during MRI upload. The proposed merge, fresh row locks and revision checks address it, but tests must confirm that behavior.

The assessment still needs clinician judgment for spoken and practical tasks, and an appropriate language/version. Full unattended grading would require substantial extra work and is outside this minimal feature. Repeated tests should follow the selected protocol's guidance; random task banks are not interchangeable standardized forms.

Authorized test content and digital presentation are prerequisites for a real MMSE questionnaire. A synthetic demo can verify navigation and scoring plumbing, but its total must be labeled synthetic rather than recorded as a patient MMSE.

The app can record and review a standard assessment using its existing services. It cannot promise conflict-free operation until the listed fixes and checks pass, and this assessment addition does not make the current new-patient forecasting pathway available or establish clinical validation.
