# Full product design preview: source inventory

Read-only source inventory for the design-only prototype requested 2026-10-03.
The application and API are unchanged. All preview identities, observations,
jobs, downloads and assistant replies must be synthetic or explicitly simulated.
Preserve the current source composition, copy, ordering, icon names and routes.

## Shared shell

Source: `frontend/components/shell.tsx`.

- Text-only **Alzhio** wordmark links to Dashboard; do not add a brain logo.
- Sidebar heading: **WORKSPACE**.
- Sidebar order: **Dashboard** (`LayoutDashboard`, 19), **Patients** (`Users`, 19),
  **Reports** (`FileText`, 19). Selected item ends with `ChevronRight`, 15.
- MRI Analysis and Settings are deliberately absent from the sidebar.
- Sidebar bottom: `ShieldCheck`, 17; **Local workspace**;
  **Your scans stay on this machine.**; green status dot and **Database connected**
  or **Checking connection**.
- Sidebar footer: `FlaskConical`, 15; **Research Prototype**; **v1.0**.
- Topbar: mobile **Open navigation** (`Menu`, 24); **Workspace**;
  `ChevronRight`, 14; active page name. `/analysis` names **MRI Analysis**;
  `/settings` names **Settings**; fallback **Patient review**.
- Topbar right: green dot **Local system online** or **Connecting**, divider,
  **R** avatar, **Researcher**, email, **Sign out** (`LogOut`, 17).
- Mobile navigation closes with **Close navigation** (`X`, 24) or link selection.
- Skip link **Skip to content**; footer **Alzhio** and
  **Research Prototype · Not a medical diagnosis**.
- Preserve existing desktop/mobile visibility behavior. The current 230px fixed
  sidebar, header and table arrangement are styling reference geometry.

## Login (`/login`)

Source: `frontend/app/login/page.tsx`.

- Existing two-part composition: story/brand left, access form right.
- Story eyebrow **A LONGITUDINAL PERSPECTIVE**; title **Every scan is a moment.**
  line break **See the whole story.**
- Copy **A focused research workspace to explore brain structure, compare MRI
  visits, and understand change over time.**
- Existing Alzhio orbit, **Baseline** (`ScanLine`, 15), **Follow-up** (`Check`, 15).
  Preserve this existing visual rather than inventing clinical images.
- Bottom **Locally stored. Research focused.** (`ShieldCheck`, 17).
- Access icon `LockKeyhole`, 24; eyebrow **RESEARCHER ACCESS**; heading
  **Welcome to your workspace**; **Sign in to continue your longitudinal research.**
- Required fields **Email address**, placeholder `researcher@neuropredict.local`;
  **Password**, placeholder **Enter your password**.
- Primary **Sign in to workspace** (`ArrowRight`, 17); pending **Signing in…**.
- **Use the researcher account configured during local setup.**
- `ShieldCheck`, 18; **Research Prototype**; **Not a medical diagnosis.
  Independent validation and qualified review are required.**
- Preview login uses a synthetic email and simulated session; no credentials.
- Error state remains accessible. Sign-out returns to this preview screen.

## Dashboard (`/dashboard`)

Source: `frontend/app/(workspace)/dashboard/page.tsx` and
`frontend/components/patient-values-panel.tsx`.

### Composition in existing order

1. Eyebrow **RESEARCH OVERVIEW**; title **A clearer view of change.**;
   **Your longitudinal MRI research, connected in one workspace.**
   Top-right **Add patient** (`Plus`, 16) opens patient creation.
2. Four stat cards, order preserved; values zero-padded:
   - **Research patients** (`Users`, 18): **In your local cohort**.
   - **MRI visits** (`ScanLine`, 18): **Longitudinal observations**.
   - **Analyzed cases** (`CheckCheck`, 18): **Results available for review**.
   - **Active analyses** (`Clock3`, 18): **Managed by your local worker**.
3. **PATIENT VALUE SNAPSHOT**; **Observed measures and anatomy**;
   **Source observations and measured regional volumes for one selected visit.**
   `ChartNoAxesCombined`, 19.
4. Conditional result card beside existing workflow card. Hide the result card
   entirely when no complete numeric result; workflow card becomes full width.
5. **Recent patients**; **Your latest research cases and analysis activity**;
   **View all patients** (`ArrowRight`, 16); first five rows of current PatientTable.
6. `Brain`, 19; **Designed for research.** **Every result includes its origin and
   limitations. Estimates require qualified review and independent validation.**

### Snapshot controls and data

- **Patient** dropdown; option suffix `· N measured visits` or
  `· no anatomy measurements yet`.
- **Observed visit** dropdown exists whenever recorded visits exist, independent
  of completed anatomy; switching patients resets selected visit.
- **Open full case** (`ArrowUpRight`, 15).
- Identity: `UserRound`, 17, patient code, visit; conditional QC badge
  **Visual QC reviewed** / **Automated checks only** / **Processing review pending**.
- **Recorded source values**: available entries only, ordered **Age at scan**,
  **Sex**, **Handedness**, **MMSE**, **Demo cognitive score**, **CDR**,
  **Source nWBV**, **eTIV**, **Education**, **SES**, **ASF**.
- Available anatomy cards only: **MTA left · 0–4**, **MTA right · 0–4**,
  **Koedam PA · 0–3**, **Hippocampal asymmetry**, **Age-matched nWBV reference**.
- No BMI, total hippocampus or hippocampal volume-change card.
- **Regional anatomy · mm³** table ordered **Region**, **Stats**,
  conditional **Hard-label mask**, conditional **Stats / eTIV**.
- Automatic unreviewed estimates keep their explicit research notes;
  missing data is hidden rather than represented by invented numbers.

### Conditional result and workflow panels

- Non-trained complete result: **LONGITUDINAL INSIGHTS** /
  **Progression-risk trajectory**; trained complete result:
  **RETROSPECTIVE MODEL** / **Experimental sequence classification**.
- Provenance badge **Output mode: ...**; identity `Brain`, 17, code, visit count;
  **Review case** (`ArrowUpRight`, 14).
- A trained result represents one retrospective classification, not a fabricated
  future trajectory. Only an explicitly synthetic illustrative preview fixture
  may demonstrate the historic non-trained chart, with mode **Demo**.
- Workflow card copy/order: **FROM SCAN TO STORY**;
  **Built for the / longitudinal view.**;
  **Explore the same subject across visits, with the context that a single scan
  cannot provide.**
  - 01 **Bring visits together** / **Organize MRI scans chronologically**.
  - 02 **Explore structural change** / **Review trajectories and image proxies**.
  - 03 **Keep the research traceable** / **Compare scans and export a report**.
- **Open MRI workspace** (`ArrowRight`, 16) reaches `/analysis`; keep this path.

## Reports (`/reports`)

Source: `frontend/app/(workspace)/reports/page.tsx`.

- Eyebrow **RESEARCH RECORDS**; title **Reports**;
  **Traceable snapshots of your analysis, ready for research review.**
- Notice `FileText`, 20: **Generate a report from a completed patient analysis.
  Each PDF records the sequence, output provenance, methods, and limitations at
  the time of generation.**
- Panel **Generated reports** and count pill.
- Four table columns, same order: **Research report**, **Generated**,
  **Output provenance**, **Download**.
- Report identity `FileText`, 18; patient-code link returns to case;
  subtitle **Analysis [first eight id characters] · PDF**.
- Provenance **Output mode: Demo / Precomputed / Inference / Trained · experimental**.
- **Download PDF** (`Download`, 15), outline small button.
- Empty **No reports generated yet**;
  **Open a patient, complete an analysis, then select Generate research report.**
- Preview report generation adds a synthetic report to this in-memory list;
  download can produce a clearly labeled sample file, never imply a real export.

## Settings (`/settings`, existing direct-only route)

Source: `frontend/app/(workspace)/settings/page.tsx`.

- Do not add a Settings sidebar item. Provide this existing screen through the
  preview's route navigation/catalog outside the application shell if needed.
- Eyebrow **WORKSPACE SETTINGS**; title **Local by design.**;
  **Your research environment, account, and model information.**
- Existing four-card grid:
  1. `ShieldCheck`, 26; **Researcher account**; email;
     **Authentication** / **JWT · HTTP-only session cookie**,
     **Session duration** / **8 hours**, **Patient access** /
     **Restricted to this researcher**.
  2. `Database`, 26; **Service status**; **API**, **PostgreSQL**,
     **Analysis worker**, **Storage**. Offline warning:
     **The analysis worker is offline. Start the worker to process queued analyses.**
  3. `FlaskConical`, 26; current **ML-only serving**:
     **Active method** / **Clinical + FastSurfer · trained logistic heads**,
     **Release readiness** / **Promoted research release** or **Prediction blocked**,
     **Fallback** / **Disabled · no demo, feature-delta or historical neural scores**,
     **Clinical validation** / **Not established**, then readiness reasons.
     Retained non-ML-only mode uses **Research model**, checkpoint version,
     availability, **3D CNN + demographic MLP + LSTM**, retrospective target,
     baseline version, intensity differences and no confidence estimator.
  4. `HardDrive`, 26; **Data & provenance**;
     **MRI volumes and derived artifacts stay in local storage. Demographic
     observations retain their OASIS source.**
     Current ML-only archived-analysis/release explanation. Retained mode lists
     **Demo**, **Precomputed**, **Inference**, **Trained** provenance definitions.
- Read-only screen; no invented configuration controls.

## MRI Analysis (`/analysis`, existing non-sidebar route)

Source: `frontend/app/(workspace)/analysis/page.tsx`.

- Accessible via Dashboard **Open MRI workspace**. Do not re-add sidebar item.
- Eyebrow **MRI ANALYSIS**; title **Your research workspace.**;
  **Compare scans, explore differences, and build a longitudinal view.**
- **Select patient** dropdown at heading right; default matching OAS2_0048 when
  available, then first patient. Prototype uses a synthetic equivalent.
- Reuses complete AnalysisWorkspace, including upload, assessment, anatomy, MRI
  and assistant; selection must hide previous patient data immediately.
- Empty **No research cases available**;
  **Add a patient from the Patients page to begin.**

## Saved anatomy gallery (`/preview`, existing non-sidebar route)

Source: `frontend/app/(workspace)/preview/page.tsx`.

- Eyebrow **EXPERIMENTAL VISUAL PREVIEW**;
  title **Saved future anatomy examples**;
  **Small-cohort model · Unvalidated research prototype**;
  badge **Not a medical diagnosis**.
- Loading **Checking the saved preview…**; unavailable
  **Saved preview unavailable**, reason, **Retry**.
- Available example keeps original subject, cutoff day, exact generated interval
  and unpromoted status. Preview-only synthetic artifact must identify itself.
- Interval choices in order: **+229 days · held-out example**,
  **12 months · 365 days**, **24 months · 731 days**,
  **36 months · 1,096 days**. Default 365.
- Existing **Slices + 3D** and **3D volume** controls; default multiplanar.
- Checked **Hippocampus highlight**; **Open example patient**;
  explanatory **Open patient directory** link.
- Two matched canvases: **Acquired MRI · cutoff day ...** and
  **Experimental model output · +... days · not validated**.
- Yellow hippocampus layers must remain spatially linked; no standalone screen
  overlay. Synthetic visual controls may demonstrate chrome without model/MRI.
- Conditional **Measured hippocampus labels unavailable for the acquired MRI.**
- Expandable **Model provenance and release limitations** displays model version,
  fingerprint, total/gradient-training subjects, examples, epochs, status, warnings.
- Never describe a synthetic design image as trained or evaluated anatomy.

## Cognitive assessment in both workspace modes

Source: `frontend/components/mmse-assessment.tsx`,
`backend/app/services/mmse.py` (`demo_protocol()`), `docs/22-cognitive-assessment.md`.

- Existing card: eyebrow **COGNITIVE ASSESSMENT**; heading
  **Demo cognitive score: N/30**, **MMSE: N/30**, **Recorded MMSE: N/30**,
  or **No completed assessment** according to available provenance.
- Visit + date/time + language; or visit +
  **Score is calculated from task performance.**
- Imported OASIS case: **Imported study observation** and no assessment button.
- Uploaded synthetic case: **Start assessment** or **Resume assessment**
  (`ClipboardList`, 16).
- Dialog header visit **· CLINICIAN-GUIDED**; **MMSE-style demo**;
  **Close assessment** (`X`, 20). Loading **Loading assessment…**;
  error **Reopen the assessment to try again.**
- **English demonstration tasks · not a standardized MMSE. The demo score is
  recorded separately from clinical MMSE.**
- **N/11 tasks scored**, **English**, progress meter.
- Each task: **TASK N OF 11**, title, exact original prompt, expandable
  **Clinician scoring guide**, score-help sentence, numeric radio options.
- Help: **Select the points earned to continue. Choose 0 if the administered
  task earned no points.**
- Legend **Points earned · maximum N**; labels **0 points**, **1 point**,
  **2 points** etc. No default score, null/unanswered preserved.
- Actions: **Save draft & close**, **Back** (`ArrowLeft`, 15),
  **Next** / **Review** (`ArrowRight`, 15). Next/Review disabled until score chosen.
- Review: **Review assessment**; complete **Calculated preview: N/30. The backend
  verifies the final total.**; missing count and
  **Return to first unanswered task** when incomplete.
- Every review row links to its task, showing **Unanswered** or points/max.
- **Assessment date and time** (datetime-local); **Complete assessment**;
  pending **Saving…**. Completion disabled for unanswered tasks/missing date.
- Draft/resume, Back, per-task review editing and completion should be simulated
  in preview state. X/Escape discards edits since last saved draft. Successful
  synthetic completion updates demo score, never clinical MMSE/model inputs.

### Original demo task order, max points and prompts

1. **Time awareness** (5): Tell me the current year, month, date, weekday and
   approximate time of day.
2. **Place awareness** (5): Describe where you are: the country, state or region,
   town, building or setting, and room or area.
3. **Immediate memory** (3): Listen to these words: lantern, peach, bicycle.
   Repeat the three words now and keep them in mind for later.
4. **Concentration** (5): Begin at 40. Subtract 3 repeatedly and tell me the next
   five numbers. Clinician guide sequence 37, 34, 31, 28, 25.
5. **Delayed memory** (3): Tell me the three words from the earlier memory task,
   without looking back.
6. **Object naming** (2): The clinician shows two familiar objects individually.
   Tell me what each object is called.
7. **Sentence repetition** (1): Repeat this sentence: The small bird rested
   beside the window.
8. **Following directions** (3): Touch your shoulder, point toward the door,
   then place your hands on your lap.
9. **Reading** (1): Read this instruction and perform it: Touch your chin.
10. **Writing** (1): Write one complete sentence about an activity you enjoyed
    recently.
11. **Shape copying** (1): Copy the two overlapping rectangles shown in the
    drawing area. Existing original two-rectangle SVG appears only for demo.

These are the original Alzhio demonstration tasks, not a licensed MMSE form.
Full source scoring guides are available in `backend/app/services/mmse.py`.

## Alzhio Bot (floating patient workspace widget)

Source: `frontend/components/clinical-assistant.tsx`, `docs/21-clinical-assistant.md`.

- Launcher is text-only **Alzhio Bot**, floating; does not occupy workspace space.
- Overlay heading **Alzhio Bot**; **Close Alzhio Bot** (`X`, 18); Escape/backdrop
  also closes it. Conversation remains until Erase memory, patient switch or leave.
- Suggestions in order: **Summarize the case** (`Sparkles`, 15),
  **What am I missing?** (`Sparkles`, 15), **Explore research** (`BookOpen`, 15).
  Each ends `ArrowUpRight`, 13. Research suggestion enables sources.
- Messages labeled **You** / **Alzhio Bot**; accessible live conversation.
- Pending **Reading the case…** or **Reading the case and reviewing evidence…**.
- Error message with **Retry question**, restores editable failed question.
- Textarea placeholder **Ask about this case…**; maximum 1000 characters.
- **Research sources** checkbox (`BookOpen`, 14), **N/1000** count,
  **Send** (`Send`, 14); Enter sends, Shift+Enter inserts newline.
- **Erase memory** (`Trash2`, 13) disabled with no history or pending response.
- Expandable **Web references (N)** (`BookOpen`, 14); title links end
  `ArrowUpRight`, 13; supporting passages. No source output state:
  **No web references were returned for this response.**
- Optional provider **Google Search suggestions** iframe exists in live app;
  preview can display an explicitly simulated example without remote provider call.
- Preview assistant replies must visibly be canned design demonstration output.
  No Gemini calls or real data. Use project-appropriate source links only.

## Shared resource and boundary states

- Loading `LoaderCircle`, 22, **Loading your workspace…**.
- Shell auth loading **Opening secure workspace…**.
- Error `AlertCircle`, 18, message, **Try again** when reload is supported.
- Empty `ScanLine`, 34, state-specific heading/copy.
- Mode badge exact prefix **Output mode:**; trained **Trained · experimental**.
- `/` redirects to Dashboard.
- Not-found **Page not found**; **This workspace page is unavailable.**;
  **Back to dashboard**.
- Preview's own navigation catalog/state selector may sit outside app canvas;
  do not add a product sidebar item, button, screen/tab or clinical feature.

## Scope checks

- Preserve existing API/model labels, MRI controls and actual source ordering.
- No new risk claims, invented learned values, animation of disease or substitute MRI.
- Synthetic prototype state may connect existing controls to demonstrate journeys.
- Existing application code, routes, schema, business/state logic and MRI assets
  remain unchanged; no tests or runtime mutations are needed for this inventory.
