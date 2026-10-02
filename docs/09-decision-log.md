# Decision Log

## D073: Import remote cognitive assessment through reviewed diffs

Status: Accepted and implemented (2026-10-03, explicit user request)

Fetch `origin/chatbot` at `bd61b54` and review its changes since the previously
integrated `7165081`. Import the assessment feature from commits `8ba84db` and
`bd61b54` through targeted patches and code edits, without a branch merge or
cherry-pick. Include the clinician-guided English demo, eleven task groups,
server-calculated totals, draft/resume, versioned immutable completion, owned
visit APIs, authorized-protocol configuration and separate dashboard/chat context.
The default demo score remains `cognitiveDemoScore`, never an MMSE model input.
Imported OASIS observations remain read-only. Preserve current patient codes,
required age/nWBV, paired MRI uploads, hidden unavailable dashboard cards and
axial viewer defaults. Reuse the existing refreshed visit row lock for assessment
writes and MRI metadata preservation; prevent pending-visit deletion when an
assessment record exists. No database migration, model retraining, new service,
automated test import/run or branch integration is included. Document the feature
as document 22 to retain existing training/assistant documents and decision IDs.

## D072: Default axial MRI view and explain hippocampus mask availability

Status: Accepted (2026-10-03, explicit user request)

Open patient spatial MRI workspaces in axial mode, including direct experimental
forecast links. Initialize the canvas in axial mode and retain later manual layout
choices; resetting the view returns to axial. Keep measured hippocampus labels
enabled by default when a matching segmentation is available. Always show the
highlight control, disabled/unchecked when no displayed mask exists, and explain
that uploaded MRI voxels alone do not identify hippocampus tissue. Show an
actionable FastSurfer segmentation message, distinguishing a pending anatomy job
and missing earlier MRI visits. Preserve the existing source-grid mask, geometry
and ownership gates. No approximate overlay or new segmentation pipeline is added.

## D071: Upload paired MRI header/image acquisitions

Status: Accepted (2026-10-03, explicit user request)

Accept matching uncompressed `.hdr`/`.img` files, including the supplied
`mpr-1.nifti.hdr`/`mpr-1.nifti.img` naming, through the patient MRI uploader.
The file picker accepts multiple complete pairs and offers one acquisition per
visit, defaulting to `mpr-1` when available. Repeated acquisitions are not treated
as longitudinal visits or averaged. Keep single `.nii`/`.nii.gz` uploads.
Validate pairing, content, shape, finite voxels and spatial geometry, use generated
staging paths, and convert the selected pair to managed `.nii.gz` while preserving
scaled voxel values and spatial metadata. Bound the combined selected inputs and
managed volume to 100 MiB; clean staging/failure artifacts. Age/nWBV remain required.
Continue the existing preview/viewer and asynchronous analysis serving policy;
format support does not add a new service or bypass anatomy/model release gates.

## D070: Automatic patient codes and required MRI metadata

Status: Accepted (2026-10-03, explicit user request)

Generate uploaded research patient codes on the backend using the existing
`RESEARCH_001` pattern, incrementing the highest existing research code for that
owner while locking the owner row. Imported OASIS identifiers remain source IDs.
Require age (18–120 years) and finite nWBV (a fraction greater than zero and at
most one) when creating a patient. Create its pending day-zero baseline visit
with those values, then open the existing MRI upload flow. Each MRI upload also
requires scan-time age and nWBV, prefilled from that visit when available.
Preserve clinical metadata when adding validated image metadata. Mark entered
nWBV as researcher supplied with an unverified measurement method; collecting it
does not establish OASIS method compatibility or unlock a model release.
Use existing patient/visit storage without a database migration.

## D069: Remove Settings from sidebar navigation

Status: Accepted (2026-10-03, explicit user request)

Remove Settings from the shared desktop/mobile sidebar. The navigation contains
Dashboard, Patients and Reports. Direct access to the settings page retains its
existing behavior and breadcrumb title.

## D068: Hide removed and unavailable dashboard measurements

Status: Accepted (2026-10-03, explicit user request)

Remove the BMI, total hippocampus and hippocampal volume change cards from the
dashboard snapshot. Render the remaining measurement/source cards only when a
valid value exists, preserving numerical zero and valid recorded sex/handedness.
Keep research provenance for available estimates. Hide empty measurement sections,
missing regional columns/cells and unavailable trajectory/result cards. Preserve
the existing dashboard styling and patient/visit selection. This updates D036's
dashboard presentation; stored measurements, models and other pages retain their
existing contracts.

## D067: Integrate the combined ML branch into main

Status: Accepted (2026-10-03, explicit user merge request)

Merge `feat/ml` at `5eb3818` into `main` with a dedicated merge commit and push
the result to GitHub. This includes the anatomy/forecast implementation, local
hippocampus illustrations, patient workspace changes and the merged chatbot
features. The integration adds no new product behavior beyond the documented
branch changes. Git integration does not promote a forecast model release or
change the recorded training/evaluation status. Record the combined build checks
in documents 07 and 10.

## D066: Merge remote chatbot features into the ML branch

Status: Accepted (2026-10-03, explicit user merge/build request)

Merge `origin/chatbot` at `7165081` into `feat/ml`, retaining its authenticated
Gemini endpoint, floating Alzhio Bot widget, temporary follow-up history, research
references, retry/clear actions and Alzhio branding. Preserve the ML branch's
anatomy contracts, experimental forecast controls, local hippocampus illustrations,
pending visit deletion and current patient/sidebar choices. The assistant context
identifies the separate scalar-guided illustration when that display mode is used.
No new inference provider call is made by merging or building the application.

Reconcile both documentation histories: incoming chatbot D042/D043/D044 become
D063/D064/D065 below, and its clinical assistant document becomes 21 because
the ML branch already uses 19 and 20 for anatomy runs. Historical branch evidence
remains attributed to that branch; record the actual combined build separately.

## D065: Alzhio text-only product and bot branding

Status: Accepted (2026-10-03, explicit user request)

Use a CSS-styled text wordmark, `Alzhio`, for public product branding and `Alzhio Bot`
for the contextual chat. Remove the brain icon marks from those brand areas rather than
adding a graphical logo. Public browser, API, report and export labels use Alzhio; routes,
database identifiers and package names remain unchanged for compatibility.

## D064: Floating assistant widget preserves workspace space

Status: Accepted (2026-10-03, explicit user request)

Render Alzhio Bot as a fixed launcher and overlay drawer rather than an
in-flow patient-workspace panel. It stays scoped to the selected patient, has keyboard
Escape, backdrop and Close controls, and does not alter backend behavior or send data
until the clinician submits a question.

## D063: Gemini assistant for the five-hour hackathon

Status: Accepted (2026-10-03, explicit user implementation request)

Implement one stateless authenticated patient assistant endpoint and one chat panel shared
by both workspace modes. Use the existing httpx dependency with Gemini generateContent
REST, optional Google Search grounding, backend-only SecretStr API key and configurable
model. No local training, database migrations, SDK installation or worker changes.

This extends D007 with an explicit cloud text-processing exception for synthetic/OASIS
de-identified demonstration cases. Send only allowlisted structured clinical/anatomy
values, preserving unreviewed research status and unavailable forecasts; omit source
identifiers, patient/visit codes, free text, paths, raw MRI and owner data. User questions
and recent exchanges are sent to Gemini and must omit identifying details. No chat is
persisted by Alzhio; provider retention terms still apply. Preserve existing forecast
gates and user worktree changes. Record configuration and verification in doc 21.

## D062: Restore head geometry and show scalar-guided hippocampal progression

Status: Accepted (2026-10-03, user reports skull distortion)

Retire D061's whole-field magnification from the default forecast viewer. It
amplified displacement in the skull/head instead of focusing on hippocampal loss.
Generate a separate scalar-guided hippocampus illustration from the acquired
cutoff and its measured left/right masks. Fit a smooth local radial pull to each
learned scalar volume ratio, with categorical-mask quantization reported explicitly.
The field is zero outside an 8-mm hippocampal neighborhood and outside brain
labels. MRI and labels use the same local field. Require positive Jacobians,
source coverage and target volume agreement within 1% of the input mask volume;
preserve cutoff MRI exactly outside the affected neighborhood. No exaggerated
gain or whole-head motion is used. The five patients' scalar losses increase at
12/24/36 months; no direction is forced if a future scalar estimate predicts growth.

Identify this as a scalar-guided illustration, not the evaluated spatial CNN
prediction or a diagnosis/proof of increasing Alzheimer's severity. Preserve raw
forecasts, weights, sources and previous artifacts. New presentation analyses
contain separate files, explicit display mode, regional measurements and private
identity/geometry evidence. The default viewer uses these regional artifacts;
original spatial measurements remain separately identified diagnostics.

## D061: Open annual experimental forecasts for the five pinned patients

Status: Accepted (2026-10-03, explicit user request)

Enable the existing experimental mode by default for OAS2_0048, OAS2_0070,
OAS2_0073, OAS2_0127 and OAS2_0017 and prepare patient-specific forecasts at
365/731/1096 days from their measured cutoff. Explicit selection of evaluated
mode remains possible. Interpret progression as actual time-conditioned outputs;
do not force positive change or manufacture increasing atrophy. The saved model
and review/evaluation status remain unchanged. These five display-priority patients
are not a new training split. No monthly interpolated anatomy is implied.

The user clarifies that scalar estimates should bound a visibly enlarged display
for judges. Generate separate presentation MRI/labels/field with the learned field
multiplied by the largest passing gain in 3/2/1.5. Each region's absolute relative
volume change must stay within max(abs(scalar change), abs(original mask change))
plus the existing 12-percentage-point consistency tolerance as a display allowance.
The initial strict magnitude-only limit blocked enlargement in the annual batch.
This allowance is explicitly a presentation policy, not a calibrated uncertainty
interval or a claim that magnification passes scientific release gates. Reject folding,
missing coverage and disappearing regions. If no gain passes, show the original.
Scalar estimates are not confidence bounds. Identify magnification in the canvas
title and control, keep original measurements and allow switching back. This
supersedes D049's prohibition on a separately identified presentation view, never
its preservation of actual predictions. Playback advances the selected timeline
position together with the future time, showing completed artifacts only.

Presentation refinement creates a new analysis with preserved raw artifacts and
separate display files; completed earlier predictions and their results are immutable.

Experimental requests may coexist with queued native preprocessing for the same
patient, using the immutable completed source. Processing jobs or another queued
forecast still block requests. The existing worker/compute lock serializes work;
paused native jobs remain queued and the experimental-only worker ignores them.

Repair native marching-cubes volume loss in thin regional masks by retrying surface
extraction on a cropped, doubled categorical grid when the original surface misses
the existing 5% volume tolerance. Replication preserves occupied voxel cells; map
subvoxel centers back to the original affine. Retain all geometry checks, native
MRI/masks and earlier artifacts; record the surface sampling factor. This affects
mesh approximation only and does not change learned predictions.

## D060: Remove repeated experimental preview badges in the MRI workspace

Status: Accepted (2026-10-03, explicit user request)

Remove the `Unvalidated experimental preview` badge from the 12/24/36-month
forecast timeline positions and the unavailable future anatomy card. Forecast
selection and rendering retain their existing behavior. The workspace's
experimental mode controls, model provenance and evaluation warnings continue
to identify the research outputs. This supersedes D048's badge placement.

## D059: Remove MRI Analysis from sidebar navigation

Status: Accepted (2026-10-03, explicit user request)

Remove the MRI Analysis link from the shared desktop/mobile sidebar. The existing
analysis route remains accessible directly and retains its breadcrumb title and
default patient selection. Sidebar entries are Dashboard, Patients, Reports and
Settings.

## D058: Default MRI Analysis to OAS2_0048

Status: Accepted (2026-10-03, explicit user request)

The user subsequently changed the requested default from OAS2_0073 to OAS2_0048.
The MRI Analysis patient dropdown initially selects OAS2_0048 by patient code.
An explicit user selection takes precedence across polling updates. If that
patient is absent, use the existing first-patient/empty-state behavior.

## D057: Put pending visit deletion beside the MRI visit selector

Status: Accepted (2026-10-03, user marks the existing pending Visit 6 section)

Place `Delete visit` in the pending upload section header beside `MRI visit`,
where the selected entry is identified. Reuse the D056 deletion endpoint and
upload/delete busy state; the action sits outside the file upload form so no
file is required. Errors appear directly under the action. Selecting another
visit changes the deletion target through the keyed upload component.

## D056: Delete visits awaiting an MRI from the upload screen

Status: Accepted (2026-10-03, explicit user request)

Newly created visits await MRI upload and open their upload screen automatically.
Add `Delete visit` there to remove the owned empty visit and refresh selection.
The API rejects visits with MRI/preview files, analysis references or derived
heatmaps. Use the same row lock for deletion and upload, refreshing the loaded
row under the lock to handle concurrent requests. Disable upload/delete/file
selection during either action and display deletion failures. This operation
removes only an empty visit record; it performs no filesystem deletion.

## D055: Prioritize the requested patients in the directory

Status: Accepted (2026-10-03, user-provided patient codes)

The patient directory renders OAS2_0048, OAS2_0070, OAS2_0073, OAS2_0127 and
OAS2_0017 first, in that order. Apply this stable display ordering after the
existing search filter, preserving the server order for all remaining patients.
Missing or search-excluded priority patients do not create placeholder rows.
Sort the filtered array so the fetched patient data remains unchanged.

## D054: Remove the standalone patient MRI timeline section

Status: Accepted (2026-10-03, explicit user request)

Remove the standalone default patient `MRI timeline` section and its observation/
future cards, identified by `Select an observation or future prediction horizon`.
The MRI visit selector and the separate 3D viewer's navigation continue to provide
scan and forecast selection. No visits, acquired images or forecasts are deleted.

## D053: Remove the complete default patient baseline forecast section

Status: Accepted (2026-10-03, explicit user request; supersedes D052)

Remove the entire baseline Clinical + FastSurfer forecast component from the
default ML-only patient workspace, including readiness action, CDR explanation,
blocked status, model/QC details, horizon cards and release warnings. Removing
the component also stops its forecast fetch on this page. This is a UI scope
change; anatomy measurements and the experimental future MRI workspace retain
their own controls. Baseline forecast services remain available to other consumers.

## D052: Remove the patient forecast heading label

Status: Accepted (2026-10-03, explicit user request)

Remove only the visible `Clinical + FastSurfer ML forecast` heading from the
default patient forecast panel. Retain its `Check prediction readiness` button,
forecast content, model selection policy and behavior. The separate research
panel's `Baseline-only outcome forecast` heading remains applicable.

## D051: Highlight measured hippocampus in acquired comparison panels

Status: Accepted (2026-10-02, user requests highlighting in the acquired/input MRI)

Use each acquired visit's measured regional mask in baseline/current comparisons,
not the forecast labels. The saved preview previously omitted the acquired label
layer altogether. Its metadata now exposes optional `observedLabelsUrl` from a
completed anatomy job for the owned original patient and cutoff, matching the
saved source and segmentation hashes. The existing authenticated artifact endpoint
checks the regional file hash. Absent matching acquired labels are explicitly
unavailable, never replaced with generated labels. The shared highlight toggle
controls acquired and predicted layers; D050 camera/zoom/clipping applies to both.
Browser checks must measure yellow pixels on both sides, not just a checked toggle.

## D050: Keep hippocampus highlighting attached to the MRI cutaway

Status: Accepted (2026-10-02, user clarifies the complaint was a stationary overlay)

The user wanted the yellow hippocampus to follow adjustments to the brain, not
its removal. Restore highlights on explicit experimental links/actions while
retaining the actual cutoff/generated comparison and measured-change summary.
NiiVue 0.69.0 defaults `isClipAllVolumes` to false, so our MRI cutaway removed
tissue but still rendered the entire categorical overlay. Set it to true for
every volume canvas. MRI and label volumes continue to share the same camera,
zoom, native spatial transform and clip plane; label rendering remains nearest
neighbour. A real-case browser regression must verify yellow pixels move/scale
with camera and zoom and disappear when their tissue is clipped, then return
when clipping is disabled. This fixes display behavior and does not change model
weights, predicted masks or scalar/mask disagreements documented in D049.

## D049: Show actual deformation and separate scalar/mask outputs

Status: Accepted (2026-10-02, user says the forecast looks like an overlay)

The prior isolated full-head 3D view with yellow hippocampus layers obscured the
small learned deformation. Explicit experimental view links/actions now open
matched slices of the actual input cutoff and generated MRI side by side, with
highlights and meshes off. Labels remain optional orientation aids, never forecast
evidence. Show native field displacement and independently measured input/future
hippocampal mask volumes alongside separate scalar-model percent changes. The
read-only comparison endpoint verifies source ownership and all artifact hashes;
it changes neither the forecast files nor weights. Do not exaggerate deformation
to make it look convincing. Subvoxel fields and categorical-mask/scalar disagreement
are model limitations, and no clinical accuracy is claimed.

## D048: Make the generated experimental view discoverable

Status: Accepted (2026-10-02, user-reported ready forecast still shown unavailable)

The ready +365-day image was hidden by default evaluated-only mode while its opt-in
was below the visible controls. Add `Show experimental forecast` to the future
unavailable panel, with explicit unvalidated wording. A patient link containing
`experimentalForecast=365` (also 183/731/1096) explicitly selects experimental mode
and the corresponding future time at the prepared cutoff. It loads existing
matching artifacts without queuing inference. Ordinary links retain default mode;
all ownership, input/fingerprint and exact cutoff/interval checks still apply.
Use `Unvalidated experimental preview` instead of hardcoded `unsupported horizon`
badges. Experimental availability does not imply validated horizon support.

## D046: Explicit patient-specific inference with the frozen small-cohort model

Status: Accepted (2026-10-02, user-requested experimental forecasts)

The user requests applying the existing six-subject experiment to other patients
despite insufficient accuracy evidence. Six means four training subjects, one
selection subject and one test subject. Expose the hash-bound v3 fixed-reference
checkpoint through opt-in experimental requests. Keep its 129 inputs, reference,
imputation, coefficients and spatial weights frozen. This adapter is separate from
current v4 fitting and default promoted-release serving. Generate each patient's
forecast from two-to-five prepared observations through the selected cutoff.

Allow automated segmentation and finite provisional AVRA scores, retaining their
unreviewed status. Disclose failed evaluation/review/support gates, historical
reference overlap and absent calibrated uncertainty. In explicit experimental mode,
scalar/mask disagreement is reported rather than blocking the visual preview;
positive Jacobians, coverage, region presence and mesh geometry remain mandatory.
Outputs neither promote the candidate nor establish predictive/medical accuracy.

When Docker preprocessing is unavailable, the serialized worker may run with
`--experimental-only` on CPU. It claims only experimental forecasts and does not
recover interrupted native preprocessing. One-worker/shared compute locks remain.
Queue +365-day estimates for all prepared owned OASIS histories; missing inputs
remain unavailable until preprocessing completes.

## D047: Add saved 12/24/36-month outputs to the prototype gallery

Status: Accepted (2026-10-02, explicit user request to demonstrate the small-data model)

Generate 365-, 731-, and 1,096-day images from the existing six-subject, 20-epoch
CUDA candidate (`conditioned-pull-cnn-v1`) and OAS2_0073's four-scan cutoff. The
experiment uses 16 longitudinal examples: three subjects for gradient training,
one for selection, one for calibration, and one held-out test subject. This corrects
the shorthand “trained on six”: six participated in the experiment, while three
contributed gradient updates. There are no acquired scans at the requested
365/731/1,096-day intervals. In the separate saved preview only, retain generated
outputs even when mask/scalar regional changes disagree by more than 12 percentage
points; store and display the measured discrepancies (18.7%, 33.3%, 54.0%) and
minimum Jacobians (0.942, 0.885, 0.832). Preserve input/artifact hashes and all
release status warnings. Keep the existing +229-day v3 example with its own model
provenance. Do not describe any gallery item as a validated or patient-specific
forecast; the default and D046 patient-specific path retain their own checkpoints.

## D045: Explicit saved experimental anatomy preview

Status: Accepted (2026-10-02, explicit request for immediate visual preview)

Expose the existing OAS2_0073 +229-day retrospective evaluation artifacts on a
separate `/preview` page. Show the original subject, cutoff, actual interval,
historical model and failed release status. Link to it from unavailable future
panels. A pinned local profile binds the case/evaluation/manifest and file hashes;
the API checks ownership and original source histories before serving any file.
Do not relabel the example as 365 days or as another patient's prediction.
Preview readiness describes already-generated files, not a training completion ETA.
This adds read-only visibility; it does not promote the historical candidate or
create forecasts. The current training-reference study retains its release gates.

## D044: Restore training-only anatomy reference

Status: Accepted (2026-10-02, latest explicit full workflow request)

The renewed request explicitly requires baseline-CDR-zero training subjects only
and forbids held-out reference overlap. This supersedes D043 for new anatomy
forecasts. Version the inputs as anatomy-input-v4-train-age-reference and save
the eligible baseline IDs, exclusions, bins, source hash and preprocessing state.
The descriptive bundled-table biomarker remains a separate historical support
value. Preserve every v2/v3 run; stop the waiting v3 coordinator before fitting
and create fresh v4 partial/full runs using verified existing registrations.
Keep the existing bins and never substitute raw nWBV. Missing Z uses training-only imputation
and a missingness indicator, with availability and the resulting limitation reported.

The subsequent explicit correction removes the ten-subject cutoff. Compute Z
when an age bin has at least two valid training baseline measurements and a
positive sample SD (ddof=1); two is the mathematical requirement to calculate
sample SD, not a new ten-subject support gate. Preserve counts and warn about
small reference groups. Singleton/empty groups and zero spread remain unavailable.

Freeze each run's ML and training-CLI source in a hash-verified read-only runtime
snapshot. Observed workspace rewrites restored the old demographic builder and
UTF-16 encoding while checks were running; preserve that evidence, restore the
requested contract, and isolate model fitting/native evaluation from later edits.
Runtime snapshots do not copy MRI data or credentials. Old runs remain unchanged.

## D043: Use the supplied fixed age-group constants

Status: Accepted (2026-10-02, explicit user correction)

The user clarified that age-bin means and SDs are supplied fixed values and must
not be recomputed from this training dataset. This supersedes D042's training-only
reference construction and the initial request's prohibition on reference overlap.
The new anatomy-input-v3-fixed-age-reference copies the supplied bundled table
exactly, freezes it with both checkpoints and uses the same equation at inference.
Only each patient's observed age and nWBV select/evaluate the fixed constants.
Retain the existing sparse-bin, unsupported-age and invalid-measurement states;
never substitute raw nWBV. Imputation/scaling still use actual training subjects only.

This table describes 85 OASIS-2 baseline-CDR-zero subjects. It is a user-supplied
fixed research reference, not an independently validated global population norm.
Its possible overlap with held-out subjects must be disclosed in evaluation and
forecast provenance. Preserve the v2 partial run and train a fresh v3 candidate.
Frozen forecast subject memberships and chronological input restrictions remain.

## D042: Frozen training-only age reference for future anatomy

Status: Accepted (2026-10-02, explicit user request)

The new anatomy-input-v2-age-reference contract replaces raw nWBV and demographic
conditioning with a training-baseline-CDR-zero age-reference Z-score and MMSE.
Age and raw nWBV remain source/provenance values only. Keep all 18 FastSurfer
statistics volumes, observed regional/rating changes and actual scan timing;
registered observed MRI and anatomical masks condition the separate spatial network.
Freeze the seven existing five-year bins, sample SD and minimum 10 reference subjects
per bin. Unsupported/invalid/sparse Z-scores stay unavailable, with training-only
imputation and missingness indicators; never substitute raw nWBV or held-out references.
Serialize the reference and feature schema with both models and reject older checkpoints.

Preserve the 44/4/4/4 frozen anatomy split. This supersedes D037's reassignment of
OAS2_0027 to calibration. Explicit partial research fitting may use completed
subjects in their original roles; absent calibration produces unavailable intervals,
not reassigned subjects. Preserve old runs and reuse hash-verified registered cases.
User-added visits outside the frozen source cohort do not alter study cutoffs.
Future inference retains acquired/predicted and experimental/support provenance.

## D041: Compact regional measurements and remove the regional comparison chart

Status: Accepted (2026-10-02, explicit user request)

Remove the observed-versus-model-predicted regional anatomy section from the MRI
analysis panel. Show its first four regional measurement rows initially, preserving
the existing order. Reveal the remaining rows with a keyboard-accessible dropdown
button; collapse again on visit/analysis changes. Measurements, forecast outputs,
3D timeline and reports remain available through their existing data paths.

## D040: Hide cyan regional highlights and keep the hippocampus visible

Status: Accepted (2026-10-02, explicit user request)

Keep the yellow hippocampal labels and boundaries visible in observed/predicted views.
Make temporal/parietal labels transparent and omit their cyan regional meshes. Keep
the hippocampus highlight control and a neutral gray complete brain boundary. Purple
ventricle highlighting remains hidden. Stored segmentation, regional meshes,
measurements and training inputs are unchanged; this is a visual change.

## D039: Hide ventricle highlighting in the MRI viewer

Status: Accepted (2026-10-02, explicit user request)

Make lateral-ventricle labels transparent in the shared anatomy overlay and omit
ventricle meshes from the predicted view. Remove the purple ventricle legend.
This is a display-only change: source MRI, segmentation labels, measurements,
stored meshes and model inputs remain unchanged.

## D038: Automatically expose unreviewed anatomy values for research use

Status: Accepted (2026-10-02, explicit user direction)

After automated checks complete, use the produced hippocampal volumes and AVRA
MTA-left/MTA-right/Koedam outputs directly in the dashboard and anatomy report;
remove manual visual confirmation controls from the value workflow. Label AVRA
scores and unreviewed measurements as unreviewed research estimates and preserve
raw regression outputs, including finite values outside nominal score bounds.
This does not claim visual QC, independent rating agreement, or clinical meaning.
Only display values after source, segmentation, rating CSV, transform and provenance
integrity checks pass. Missing, failed, or tampered artifacts remain unavailable.
Explicit forecast release/promotion and scientific evaluation gates remain unchanged.

This supersedes the dashboard display restriction in D036 and the app review
workflow for direct descriptive values. API review endpoints remain for historical
compatibility but the dashboard no longer asks the researcher to invoke them.

## D037: Provisional 6-subject research candidate training on CUDA

Status: Accepted (2026-10-02, explicit user direction)

Train the MTA/Koedam-conditioned 3D longitudinal anatomy model on the first 6 completed
subjects (16 registered longitudinal examples: OAS2_0048, OAS2_0070, OAS2_0073, OAS2_0127,
OAS2_0017, OAS2_0027) using the pinned CUDA container (`yodha-anatomy-training:20261002`)
for 20 epochs. For this provisional research run, OAS2_0027 serves as calibration while
OAS2_0048, OAS2_0070, and OAS2_0127 train, OAS2_0017 provides hyperparameter selection,
and OAS2_0073 evaluates holdout generalization. All predictions produced by this checkpoint
remain explicitly tagged with honest research provenance and labeled experimental.

## D036: Source-bound patient value snapshot on the dashboard

Status: Accepted (2026-10-02, user request)

Add a dashboard panel with patient and observed-visit selectors. Show source OASIS
demographics/clinical values, FastSurfer regional statistics, hard-label mask volumes,
eTIV ratios, bilateral hippocampal volume/asymmetry, MTA/Koedam estimates, and the
optional descriptive nWBV age reference when present. Show BMI only from an explicit
source BMI field; do not infer it without height and weight. Keep MTA/Koedam hidden
unless AVRA alignment is reviewed, and show longitudinal hippocampal volume change
only when both adjacent scans pass visual QC. State unavailability and provenance
beside each value. Distinguish pending scan QC from pending AVRA alignment QC and link
to the full patient workspace for the required review action. These values are
descriptive research measurements, not a diagnosis or atrophy norm.

## D035: Interactive 12/24/36-month future prediction timeline with explicit experimental provenance

Status: Accepted (2026-10-02, explicit user request)

The longitudinal anatomy model generates 3D displacement fields, warped T1 MRI volumes,
categorical segmentation masks, and 19 boundary meshes (`brain_mesh.gii` and 18 regional meshes)
at discrete horizons. The scan-count-selected frozen cohort split contains insufficient holdout
scans matching exact 12-, 24-, and 36-month intervals (±90 days) to meet formal holdout
validation thresholds.

Connect 12-, 24-, and 36-month prediction positions to the interactive 3D timeline strip
in `VolumeExplorer` and `MLWorkspace`, tied to the cutoff scan. Allow sequential navigation
(Earlier / Later MRI) past the cutoff scan into +12m, +24m, and +36m future brain positions.
When viewing future brain predictions, load the real model-generated NIfTI MRI, categorical labels,
and all 19 boundary meshes. Clearly label every 12-, 24-, and 36-month position and view
with an explicit "Experimental (unsupported horizon)" badge and honest provenance disclaimers.
Never fabricate synthetic holdout support, crossfade transitions, or uniformly scaled meshes.

## D034: Preserve unbounded AVRA outputs in provisional research training

Status: Accepted (2026-10-02, investigation of the user-reported training blocker)

The pinned upstream AVRA model ends in an unconstrained `nn.Linear` layer, and its
runner writes the ensemble mean without clipping. OAS2_0070 MR4 has PA members
0.01023519, -0.048216164, 0.044799566, 0.0032413006 and -0.013011694;
the reported mean is -0.00059036014, with ensemble SD 0.030379687. Source/alignment
artifact hashes pass. This is a finite near-zero regression estimate outside the
nominal ordinal scale, not evidence of negative biological atrophy or a failed MRI.
Alignment remains pending visual review. Source:+[pinned output head](https://github.com/gsmartensson/avra_public/blob/17e947606596e6594ec01d54ef38c992becf9395/model/model.py).

Correct only the explicitly authorized provisional `--allow-unreviewed-research`
path: preserve finite out-of-scale raw estimates under status `unreviewed_research`,
method `AVRA-v0.8-ensemble-raw-regression-research`, and an explicit warning listing
the extrapolated values. Do not clip, round, replace with zero or discard the subject.
Default/reviewed parsing still enforces MTA 0–4 and PA 0–3; missing/nonfinite values,
source tampering and malformed artifacts still fail. This permits candidate training
and leaves app review/serving/promotion gates intact. Existing in-range examples retain
their exact values and metadata so immutable prepared cases can resume.

## D033: Optional source-matched nWBV age reference (user-provided module)

Status: Accepted (2026-10-02, explicit user request)

Extract and vendor the supplied `nwbv_reference_module` package at the repository
root, preserving its aggregate reference and README. Install with `python -m pip
install --no-deps ./nwbv_reference_module` in the backend environment and Docker image.
The existing worker calls `NwbvReference.bundled().evaluate` after inference, storing
the structured optional `biomarkers.nwbv_age_reference_v1` for the selected observed
visit in result JSON and the existing biomarker table. No migration is needed.

Freeze age, nWBV and measurement method at enqueue, separately from model covariates.
Use the OASIS method only for imported OASIS values; unknown/different methods,
missing/invalid values, unsupported ages and sparse bins remain explicit unavailable
states. Normalize integral numeric ages from the existing float-valued importer;
never coerce strings, impute missing values, derive nWBV from FastSurfer, or use
future/currently edited metadata. Older queued anatomy snapshots can use their
already-frozen OASIS metadata/provenance flags. Older results remain compatible.

Keep `task=descriptive_age_reference`, `intended_use=support_value`,
`feature_use_allowed=false`, and `clinical_risk=null`. This whole-cohort reference
does not alter model inputs, training, CDR risk, volumes, future MRI or review gates.
An earlier cutoff clears the parent's later-visit reference and the worker evaluates
the selected cutoff's observed inputs. Optional package/profile failures are logged
and stored explicitly, without substituting a disease or forecasting model.
The README's example UI card is context; the requested change is backend integration.
## D032: Resolve binary isosurface ties without changing categorical anatomy

Status: Accepted (2026-10-02, discovered on the first real five-scan history)

The source middle-temporal mask produced three edges with four incident faces at
marching-cubes level exactly 0.5, failing the existing closed two-manifold check.
Use a fixed 0.5001 binary isovalue and remove degenerate triangles. The 0.0001-voxel
interpolation offset resolves saddle ties without editing labels, smoothing, or
simplifying surfaces. Keep closure, non-degenerate faces, orientation and <=5%
physical volume checks mandatory; record the actual isovalue in mesh provenance.
A synthetic saddle fixture reproduces the four-face failure and verifies a closed
export and unchanged mask. Real source-mask checks are engineering evidence, not
forecast accuracy or segmentation approval.

## D031: Reuse the verified CUDA container for score-conditioned training

Status: Accepted (2026-10-02; supersedes D030's wheel-install approach)

Build `infra/anatomy/Dockerfile` from the locally verified pinned FastSurfer CUDA
base. Retain its CUDA PyTorch and add the required Pydantic and matching geometry
dependencies. Bind code/study read-only and the candidate output read-write, disable
network access during fitting, and record the immutable image ID in run status.
The host worker remains in its original Python environment. A synthetic CUDA
training/save/host-reload check passed with PyTorch 2.7.1+cu128 on the RTX 3050;
it is engineering evidence only. The coordinator will use this runtime after all
56 real histories finish processing. It never silently falls back to CPU.

Stopped the superseded isolated-wheel download and removed only its approximately
2 GB package scratch file. Kept its scripts, environment and logs. Raw MRI, earlier
model files and native analyses remain preserved. The full run needs additional
disk space; the user was asked to free 10 GB or provide another location while
processing continued. The drive subsequently has 77 GB free, which is sufficient.
A lossless LZX compression probe preserved the aligned MRI
digest and reduced one 28.9 MB file to 22.1 MB; it does not solve the full capacity need.

## D030: Isolated CUDA runtime for the active anatomy training run

Status: Superseded by D031 (2026-10-02)

The host has an RTX 3050 and a working NVIDIA driver, but the application's Python
environment contains PyTorch 2.14.0+cpu. The queued CUDA training run cannot fit
with that build. Install the matching 2.14.0+cu130 wheel from PyTorch's official
CUDA index in `artifacts/anatomy-cuda-runtime-20261002`, reusing the application's
non-Torch dependencies through a `.pth` path. Keep the running API and segmentation
worker in their original environment. Verify actual CUDA model forward/backward
execution before resuming only the waiting training coordinator with the isolated
interpreter. Preserve cohort, epochs, device, grid size and existing run artifacts.

## D029: Score-conditioned training on the richest MRI histories

Status: Accepted (2026-10-02, explicit user direction)

Train only the anatomy predictor with MTA-left/right and Koedam inputs. Remove
the no-score training/evaluation/release dependency. Keep inexpensive no-change and
individual-trend comparisons; they do not train another neural model. Retain prior
artifacts without treating their accuracy as evidence for the new study.

Create a separately frozen anatomy cohort using source scan count, not CDR, Group,
prediction outcomes or the old classifier's 40-subject assignment. All 56 supplied
subjects with at least three scans qualify: four have five scans, nine have four,
and 43 have three. Prioritize the longest histories for processing. Use 44 training,
four selection, four interval-calibration and four test subjects. Reserve one four-scan
subject for each held-out role and one five-scan subject for test, using a fixed seed;
all remaining longest histories enter training. Freeze membership before model fitting.
Old classifier/baseline splits remain unchanged. The new holdout is reused OASIS data,
not independent clinical validation. Explicit image review and source integrity remain
required; processing does not automatically become human approval.

Permit an explicitly marked unreviewed research candidate to complete actual fitting
after automated source/geometry/score checks. Private exports distinguish
`automated_checks_only` anatomy and `unreviewed_research` score inputs. They do not
modify application review records. Such training/evaluation remains provisional and
cannot promote or serve until real reviews and a reviewed retraining pass. This
separates the requested computation from the release approval gate.

Spatial selection/test metrics average within each subject before averaging across
subjects, matching structural and native evaluation. Extra examples from a five-scan
history therefore improve training coverage without giving that subject extra weight
in reported accuracy or checkpoint selection.

Prepare completed, integrity-checked histories incrementally while the single worker
processes later subjects. Stable case indices come from the full frozen split, not
completion order. Partial preparation writes only progress, never a final study
manifest; final export/preparation still requires all 56 subjects. Verified cases
are reused and interrupted partial directories are preserved before retrying.
The Windows coordinator holds a process-lifetime system-awake request during the
run, released on exit. Display sleep and persistent power settings are unchanged.

The local drive has limited headroom. Lossless NTFS compression was enabled for
`storage/derived`, including inherited compression for new analysis folders. This
preserves file bytes/hashes and formats, is reversible with `compact /U`, and leaves
raw MRI storage unchanged. Processing still enforces its disk-headroom guard.

## D028: Reviewed cutoff forecasts and reproducible licensed runtime

Status: Accepted (2026-10-02)

The user authorized non-commercial research use of FSL and asked this chat to
continue implementation while stopping the other overlapping chat. Preserve the
existing work and services. Provision AVRA from a pinned upstream commit and all
15 released checkpoints in an isolated container. Retain failed candidates and
logs; a successful real invocation still requires explicit alignment review.

Queue anatomy forecasts through the existing worker and persist optional JSON
fields. A selected earlier cutoff uses only its chronological prefix, with reviewed
segmentation and rating provenance. Bind parent result, actual inference files,
release, sources and generated artifacts by digest. Do not expose another owner's
artifacts or return observed anatomy for failed prediction. Generate and retrieve
18 separate regional masks in addition to labels, MRI, physical pull field and meshes.

Divide the frozen eight development subjects deterministically into four selection
and four calibration subjects; use subject-block 80% intervals with explicit limited
sample size. Keep original 40/8/8 membership and acknowledge reused holdout. Require
real native evaluation, matched score ablation and immutable promotion before serving.
Code/synthetic verification is complete enough to run the lifecycle; real segmentation,
review, model training and held-out release evidence remain outstanding. See
[18](18-anatomy-forecast-lifecycle.md) for commands and current execution status.

## D027: Cutoff-local spatial learning and evaluated anatomy release

Status: Accepted for implementation (2026-10-02, explicit completion request)

Train a bounded time-conditioned 3D displacement predictor from reviewed longitudinal
anatomy, not from the retrospective CDR checkpoint. Register each earlier observation
to its own latest-input cutoff; register the hidden future only to construct targets.
Never construct a template using hidden/future visits. Fields are physical RAS-mm pull
maps (future coordinates to current coordinates). MRI interpolation is continuous;
labels use nearest neighbour. Exact zero time, coverage and positive Jacobian checks
are mandatory. The learning grid is separate from native FastSurfer processing.

Freeze the existing 40/8/8 subject assignment. Fit preprocessing on training examples
only, select penalties/checkpoints on development subjects and evaluate once on held-out
subjects. Compare matched score/no-score structural and spatial candidates, no change,
and individual trend. Prediction intervals require held-out coverage evidence. Model
and artifact integrity, supported intervals, visual segmentation/alignment review and
explicit research release gates must pass before serving. Synthetic runs may exercise
the complete software path but can never create a serving release or accuracy claim.

## D026: Integrity-bound review and explicit anatomy report selection

Status: Accepted (2026-10-02)

Segmentation review binds source MRI, native segmentation, versioned statistics,
container digest, subject/scan identity and the complete owned artifact set. Geometry
checks/recovered files do not grant visual approval. Keep conformed mask voxel counts
separate from partial-volume statistics and source-grid display masks. Reports require
explicit anatomy analysis selection; the legacy report default is preserved. Display
only measurement/score changes through the doctor's selected cutoff.

AVRA execution remains an isolated, hash-pinned optional runtime rather than an
unverified installation of old checkpoint dependencies into the app's Python
environment. Pending alignment hides numerical estimates. Mesh helpers verify closed
two-manifold surfaces, physical scaling and a 5% engineering volume tolerance; none
of these tests establishes future-anatomy accuracy or clinical validation.

## D025: Separate longitudinal anatomy analysis and structural forecast

Status: Accepted (2026-10-02, explicit pasted user request)

Reuse existing imported/uploaded MRIs, chronological MR Delay, PostgreSQL jobs,
JSON result persistence, owned artifacts and NiiVue. Add an explicit anatomy job
without reopening legacy predictions in ML-only serving. Baseline manifests, splits,
labels and old models remain immutable. Full-resolution FastSurfer processing is
separate per longitudinal analysis; automated geometry checks never imply visual QC.
The extended DKT dictionary is separate from the compact baseline feature set.
Measured stats and discrete-mask voxel volumes are different estimators; preserve
both, and eTIV cm3 converts to mm3 by multiplication by 1000 before head-size ratios.

AVRA v0.8 is the first rating candidate: verify upstream preprocessing/weights and
license; no qualitative score is synthesized from volume thresholds. Its released
PA model uses ReturnStackedPA (axial/coronal/sagittal slices) and one global
posterior output. Missing FSL/runtime, failed alignment or invalid scores remain
explicit unavailable states. Future-score transitions and 3D geometry stay blocked
until their own held-out evaluation/release evidence exists. Structural baselines
are research comparisons, never a fallback pretending to be a trained spatial model.

## D024: ML-only serving, not a clinical-production claim

Status: Accepted (2026-10-02, explicit user request)

Default serving policy is `ML_ONLY=true`: a single Clinical + FastSurfer forecast,
requiring reviewed real anatomy, trained saved parameters, matched clinical-reference
evaluation and an explicitly promoted, hash-verified artifact release. Do not expose
Demo, feature-delta, precomputed baseline or the poorly generalizing retrospective
checkpoint as new predictions. Preserve historical records and archived reports.
Uploads still validate/store MRI but do not silently enqueue a rule-based analysis.

Processing/training remains explicit offline work, with durable stage status and a
human visual-QC pause. Do not train on unknown labels, relax class-support gates,
resplit after evaluation or substitute clinical-only inference when anatomy fails.
Serving requires all three horizon heads and both classes in development/test
evaluation; the present OASIS data cannot pass. `ML_ONLY=false` is an explicit local
research/test opt-out, not a deployed fallback. This improves serving discipline;
it does not remove research disclaimers or establish clinical production readiness.

Predeclared development gates: ROC-AUC >= 0.7, balanced accuracy >= 0.6 and Brier
no worse than the matched clinical reference. Never choose these thresholds by
inspecting final test results. Require finite metrics and at least 5 training and
2 development/test examples per class; these are execution guards, not power analysis.

User explicitly approved a targeted recoverable Docker repair. Individual socket
operations failed without changes; with Docker stopped, preserve the two-socket `run`
directory as `run.before-repair-20261002` and create an empty replacement. Linux
engine readiness then passed. No factory reset or container/database-volume changes.

The real container required explicit non-root UID/GID (its placeholder UID 999 is
rejected). Configure `1000:1000` for this Windows host, pin the downloaded registry
digest, and keep any surface license requirement unchanged. A source-unit audit also
corrected an earlier documentation/UI label: OASIS-2 eTIV is source cm³/mL, while
FastSurfer anatomical features are mm³. Keep numeric source values unchanged; do not
silently rescale saved inputs or invalidate old checkpoints under the same identity.

## D023 Baseline OASIS forecast with pinned FastSurfer

Accepted 2026-10-02 following the user-supplied FastSurfer Rewired v2 PRD.
The new `src/` study uses baseline CDR-zero subjects and first observed later CDR>0,
named `observed_cdr_conversion`, not MCI-to-Alzheimer diagnosis. MR Delay establishes
observation timing, not biological onset or exact clinical diagnosis dates. Unknown
horizons remain null. Historical 40/8/8 experiments and the functioning full-stack
application are preserved; the PRD's local Streamlit study workspace is added separately.
FastSurfer is an isolated, release-pinned anatomical processor, not another patient dataset.
Tier A/B models are compact logistic regressions with training-only preprocessing and
matched-subject comparisons. Tier C remains optional and unavailable until viable.
Missing runtime, insufficient event support, absent anatomy or unreviewed segmentation
must block the affected output, never silently generate a measurement or probability.

## D001: Full-stack product architecture

Status: Accepted

The product uses Next.js, FastAPI, PostgreSQL, local filesystem or S3-compatible storage, and a Python ML pipeline. It runs entirely locally.

## D002: ML remains in Python

Status: Accepted

Use FastAPI, PyTorch, MONAI, NiBabel, NumPy, Pandas, and PyTest for backend and ML work. Use Next.js, TypeScript, Tailwind, shadcn/ui, Recharts, and Lucide for the frontend.

## D003: Prepared demo cohort

Status: Accepted

Use 3–5 prepared OASIS-2 subjects with three visits each for a fast, deterministic demonstration.

## D004: Asynchronous analysis

Status: Accepted

MRI analysis is represented as a job. The API returns `202 Accepted`, and the frontend observes status through polling or WebSocket updates. A simple FastAPI background task is sufficient initially.

## D005: Demo and inference modes

Status: Accepted

The app supports instant demo outputs and local inference when available. The UI must disclose which mode produced the current result.

## D006: No clinical claims

Status: Accepted

The system is a research prototype. It does not diagnose Alzheimer's disease and has no independent clinical validation.

## D007: Local-only deployment

Status: Accepted

There is no AWS deployment target. The supported deployment environment is local Docker Compose with local PostgreSQL and local filesystem or S3-compatible object storage. Kubernetes, Kafka, Redis, service mesh, and cloud infrastructure are out of scope.

## D008: Local filesystem storage and durable worker

Status: Accepted

Use generated object keys on the local filesystem and a single local Python worker polling PostgreSQL. Jobs snapshot their ordered inputs and are persisted before returning 202. Interrupted processing jobs become explicitly failed on worker restart and can be retried. This implements D004's local-worker option without an additional queue service. Patient ownership is tied to researcher accounts. Reports are stored as filesystem artifacts; the six specified database tables remain sufficient.

The worker holds a PostgreSQL advisory lock for its lifetime; accidental duplicate starts fail before recovery can touch live jobs. Host PostgreSQL connections use 127.0.0.1 and a five-second connection timeout to avoid long IPv6 localhost connection attempts on Windows. Container connections use the Compose service hostname.

## D009: OASIS import and metadata

Status: Accepted

Inspect both extracted parts with NiBabel. Import one deterministic acquisition (mpr-1 where present) per visit; repeated acquisitions are not additional visits. Convert the paired header/image volumes to .nii.gz in managed storage while preserving affine and voxel data. Public uploads accept .nii and .nii.gz. Read the supplied demographics XLSX or equivalent CSV, matching by MRI ID, using MR Delay for chronology. CDR, MMSE, eTIV and nWBV are observed research metadata, never invented inference outputs. Prepare 3-5 subjects with at least three actual visits. Full-dataset import is an explicit offline command.

## D010: Transparent feature-delta baseline

Status: Accepted

The first usable inference model is the transparent baseline permitted in docs/04: canonical orientation, percentile intensity scaling, MONAI resize, PyTorch pooled spatial features and ordered deltas from baseline. Scores are uncalibrated structural-change indices displayed with the required progression-risk estimate label and caveat; they are not probabilities of disease. No untrained neural weights are used to produce risk. A small CNN and LSTM interface is provided for future trained checkpoints, but training performance is not an MVP acceptance condition. Confidence remains null until a defensible estimator exists.

## D011: Explanation and metric semantics

Status: Accepted

Use per-visit absolute intensity differences versus the first scan as a research visualization, explicitly not Grad-CAM or a temporal explanation. Canonical orientation and resizing are not anatomical registration; overlays can reflect motion, acquisition and alignment differences. Foreground fraction and pooled-feature change are image proxies, not segmented brain volumes or atrophy. Observed nWBV/eTIV from the demographic workbook are presented with source labels. Demo scores use fixed synthetic values and visibly differ from computed outputs. Precomputed mode reuses a versioned cache of the same baseline calculation and never silently falls back to demo.

## D012: Reproducible frontend installation

Status: Accepted

Keep a committed npm lockfile and explicitly declare the Recharts `react-is` and React Testing Library DOM peers. The Windows npm resolver required `legacy-peer-deps`; the project `.npmrc` applies the same installation behavior to local and Docker builds. Vitest is updated to the patched 4.x line; clean-install checks include type checking, unit tests, a production build and npm audit. Prettier formats source without changing application behavior.

## D013: Longitudinal dashboard selection

Status: Accepted

Prefer a completed three-or-more-visit analysis for the dashboard's featured trajectory, falling back to the most recent completed analysis when none exists. Browser retesting after creating single-visit cases exposed that recency alone replaced the prepared longitudinal demonstration with one observation. Overview totals and recent-patient rows continue to include all owned records.

## D014: User-requested 3D MRI workspace

Status: Accepted (2026-10-01)

The user explicitly expanded the 2D MVP to interactive 3D visualization. After comparing official NiiVue, vtk.js/ITK-Wasm and Cornerstone3D documentation, select pinned NiiVue 0.69.0 (BSD-2-Clause): native NIfTI parsing, orientation-aware slices, WebGL2 volume rendering, clipping, overlays and linked viewers match this local structural-MRI application with less integration than a general renderer or DICOM-oriented tool stack. No new service is introduced. See docs/11-3d-visualization.md for research and acceptance criteria.

Serve source volumes through owner-checked APIs with generated download names, never filesystem paths. Fetch with same-origin authenticated requests and bundle the viewer/assets locally, without external patient-data transfer or CDN dependencies. Keep the existing 2D fallback. 3D research differences are optional versioned visualization artifacts attached to completed analyses; old cached results remain readable, but cannot claim a 3D overlay until recomputed. Original voxels are immutable and prediction mathematics/model version remain unchanged. Cap simultaneous viewers at two and release GPU/event resources on navigation. Do not invent segmentation, cortical surfaces, tractography or anatomical registration.

Display defaults use a normalized difference threshold of 0.04, upper display value 0.3 and overlay opacity 0.45; threshold/opacity are user-adjustable visualization settings, not calibrated clinical cutoffs. Below-threshold values are transparent. Comparison display controls affect both panels; optional interactive linking uses header coordinates and does not imply registration. Apply explicit windows after NiiVue colormap recalibration. Support retry after graphics-context loss and dispose late asynchronous attachment/loading after navigation.

## D015: Local login convenience

Status: Accepted (2026-10-01)

The login form may prefill the local seed email and password from the ignored `frontend/.env.local` via `NEXT_PUBLIC_LOCAL_LOGIN_EMAIL` and `NEXT_PUBLIC_LOCAL_LOGIN_PASSWORD`. This is a local-development convenience only; credentials remain absent from tracked frontend source and documentation, and the defaults must not be enabled for a deployed environment.

## D016: Existing host PostgreSQL for local development

Status: Accepted (2026-10-01)

For this local Windows development environment, use the existing PostgreSQL 17 service on `127.0.0.1:5432` instead of the Compose PostgreSQL container. The project-owned `neuropredict` role and database are created there, while Docker remains available as the packaged deployment option. The ignored local `.env` is the source of the active connection string.

## D017: Demonstration training split and target

Status: Accepted (2026-10-01)

The first trained demonstration model uses the 56 subjects with at least three visits. A seeded, stratified subject-level split assigns 40 subjects to training, 8 to validation, and 8 to testing. The binary target is an observed increase in source CDR from the first to the last available visit. It is a research target, not a diagnosis or a validated clinical endpoint. The model is a small 3D SpatialEncoder plus LSTM and is saved outside Git under `data/training/`.

## D018: Multimodal demonstration model

Status: Accepted (2026-10-01)

The multimodal experiment uses the same subject split and combines MRI features with non-leaking visit metadata: age, education, SES, MMSE, eTIV, nWBV, ASF, MR Delay, sex and handedness. CDR and Group are excluded because CDR defines the target and Group is derived from disease status. Numeric missing values are imputed from training visits only with missingness indicators. The trained artifact is saved under ignored `data/training_multimodal/` and remains experimental until held-out evaluation supports integration.

## D019: Audited multimodal retraining

Status: Accepted (2026-10-01)

Retraining reads and validates the saved 40/8/8 subject manifest rather than generating new assignments. All 132 visits belonging to the 40 training subjects contribute each epoch; 29 validation visits and 24 test visits stay outside gradient updates. Include every usable workbook covariate, including the recorded visit number. Subject/MRI IDs are join keys only; CDR defines the target and Group is excluded as an outcome-derived label. Fit numeric medians/scales on training visits only, preserve missingness, and encode missing/unknown categories explicitly.

Train the MRI encoder, demographic MLP, LSTM and head together from fresh seeded weights using bounded batches. Encode actual visits only and use packed sequences. Select the best checkpoint using class-weighted validation BCE, with a minimum training duration and early stopping; set any decision threshold from validation predictions only. Save immutable run directories with per-epoch subject coverage, source fingerprints, preprocessing, weights, prediction CSVs, full metrics and optimizer state. Test results are withheld from training decisions but this same test cohort has already been evaluated in earlier experiments, so it is a reused holdout, not an independent final validation.

Using MRI/MMSE/nWBV from every visit makes the target retrospective recognition of observed first-to-last CDR increase. It does not establish forecasting ability. Checkpoints remain offline experiment artifacts until a separately requested integration.

## D020: Strict diagnostic forecasting objective

Status: Superseded by D028 (2026-10-02)

An earlier request proposed a distinct documented-MCI-to-Alzheimer-dementia
endpoint. OASIS-2 CDR and `Group` fields do not provide this diagnosis target.
This endpoint is outside the current OASIS-2-only scope and must not be represented
as trained or supported by the supplied data.

## D022: Explicit experimental trained-model integration

Status: Accepted (2026-10-01, user-requested integration)

Expose the audited 40-subject multimodal checkpoint through an explicit `trained` analysis mode, selected by default in the workspace. Preserve the old baseline/demo/cache modes and historical analyses. Freeze the original 40/8/8 subjects; never replace difficult candidates, tune on test results, or promise improved accuracy. This supersedes D018's offline-only restriction solely for experimental research use, not clinical deployment or Alzheimer-specific forecasting.

Return one uncalibrated sequence-classification score for observed CDR increase, with its validation-selected decision threshold, checkpoint fingerprint, cohort membership and recorded reused-holdout performance. Do not manufacture per-visit neural scores or future Alzheimer probabilities. Keep intensity-difference images and structural proxies explicitly separate from model attribution. Trained inference must load validated saved weights and train-only preprocessing, require at least three chronological MRI visits and the documented covariate schema, and fail explicitly instead of silently falling back to the baseline. Missing recorded SES/MMSE use the checkpoint's training-only imputation; absent covariate ingestion must not masquerade as complete demographics.

Import the exact saved training cohort and all of its visits through an explicit offline command, adding source covariates without replacing existing MRI, accounts, splits, checkpoints or reports. Predictions on these 40 subjects are in-sample demonstrations, not accuracy evidence. The selected checkpoint's poor generalization remains prominently disclosed; this integration does not improve its measured performance or satisfy a diagnostic Alzheimer forecasting target.

## D028: OASIS-2 is the sole project dataset

Status: Accepted (2026-10-02, explicit user direction)

Use only the OASIS-2 MRI data and its supplied demographics workbook/CSV. Do not
acquire or combine another cohort. Clinical and demographic predictors must come
from recorded OASIS-2 fields available at the prediction cutoff; later observations
are outcome labels only. The supported baseline forecast endpoint is observed CDR
conversion at horizons with adequate frozen-cohort support. CDR and `Group` do not
establish Alzheimer-specific diagnosis, so the UI and reports must not claim one.
Preserve OASIS-2 raw data, source values, subject splits and existing checkpoints.
