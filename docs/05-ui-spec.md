# Next.js UI Specification

## Guided English cognitive demo (D073)

Both patient workspace modes include Start/Resume assessment for the selected
uploaded-case visit. The dialog shows one clinician-administered task at a time,
numeric point choices, a scoring guide, draft saving and review/completion. Missing
answers remain null and block completion; administered zero points is valid.
Display MMSE-style demo and Demo cognitive score for default original demo content.
Imported OASIS observations remain read-only. Dashboard visit selection includes
recorded visits before anatomy processing, with available clinical/demo values
visible and unavailable cards still hidden. See [22](22-cognitive-assessment.md).

## Initial MRI layout and hippocampus highlights (D072)

Start the patient spatial MRI workspace in axial mode, including direct forecast
links. Preserve later manual layout selection and use axial for reset. The
hippocampus highlight is enabled by default when a matching measured/generated
mask exists. Always show its control; missing masks leave it disabled/unchecked
and explain that FastSurfer anatomical segmentation must be completed first.
For a new uploaded MRI, show a notice near the layout toolbar, with the existing
analysis action or missing-earlier-MRI prerequisite. Do not substitute an atlas
blob or guess a hippocampus region from the displayed head.

## Patient-specific experimental forecasts (D046)

D062 supersedes the whole-field magnifier below. The default experimental viewer
uses separate scalar-guided hippocampus illustrations with acquired head geometry
fixed. Yellow labels and local MRI use the same field. Identify the illustration
in the canvas title and show acquired/displayed mask volumes, displayed change and
the learned scalar estimate. Original spatial model measurements are expandable
diagnostics. Playback advances through the prepared 12/24/36-month illustrations.
No whole-head magnification control or raw mesh overlay is enabled in this view.
API regional keys use camel case; annual scalar values accept these keys correctly.

D061 selects experimental mode by default for the five pinned patients
(OAS2_0048/0070/0073/0127/0017). Forecast positions load their matching generated
12/24/36-month output without requiring a query parameter. Show actual changes;
increasing change is not guaranteed and monthly anatomy is not interpolated.
The annual scalar table shows bilateral hippocampus changes at the same cutoff.
The presentation magnifier is selected initially for these patients but uses
only separately generated artifacts passing scalar magnitude/geometry limits.
Display its gain and presentation status in the canvas title. At gain 1, explain
that enlargement failed those limits. The control can restore the original MRI;
yellow labels follow the chosen MRI and raw meshes appear only with the original.
Comparison measurements always describe the original forecast. Playback changes
both selected future position and time, cycling completed predictions only.

D049 opens explicit experimental links/actions in a side-by-side slice comparison
of the actual cutoff MRI and generated MRI. D050 restores yellow labels by default
following the user's clarification; separate mesh boundaries remain optional. Show
brain displacement and actual native hippocampus mask volume change separately
from scalar percent changes. Highlight layers are optional orientation aids.
The cutaway must clip label and difference volumes along with the MRI. Camera and
zoom act on MRI and labels together, with no stationary screen overlay.
D051 also loads measured labels in the baseline panel and acquired side of saved
previews. One highlight toggle controls both sides; acquired labels must match the
original cutoff source/segmentation. Missing measured labels stay unavailable.

D048 adds a visible `Show experimental forecast` action in the future panel. It
sets the existing opt-in. Explicit patient links with `experimentalForecast` set
to 183/365/731/1096 days open that experimental time at the prepared cutoff and
load matching saved artifacts; they do not start a job. D060 removes the repeated
`Unvalidated experimental preview` badges from the forecast timeline and unavailable
anatomy card. Experimental controls, model provenance and evaluation warnings remain.

The MRI workspace offers unchecked `Experimental forecasts (small-cohort model)`.
With at least two prepared scans, select a future timeline time or compare
current/predicted and press `Generate experimental forecast`. Queue asynchronously;
display only artifacts matching patient, cutoff, interval, mode, source hashes and
candidate fingerprint. Show training count, unvalidated language and expandable
evaluation/output warnings. Missing inputs stay unavailable. The +229-day saved
preview retains its original subject and interval on its separate page.

## Saved multi-horizon preview (D047)

The separate `/preview` page offers saved OAS2_0073 outputs at +229 days and
365/731/1,096 days. The 12/24/36-month outputs use the earlier six-subject,
20-epoch candidate (three gradient-training, one selection, one calibration,
one held-out test) and the same four-scan cutoff history. The +229-day output
remains the later fixed-reference candidate. Identify the model version for the
selected interval. Show that the longer horizons lack matched acquired scans,
and display the actual spatial-mask/scalar-volume discrepancy and experimental
status. This is a visualization gallery, not another patient's forecast.

## Saved experimental preview (D045)

Unavailable future panels link to `/preview`, a separate view of the saved
OAS2_0073 +229-day evaluation example. Compare acquired cutoff MRI and generated
MRI, support slices/3D and the yellow hippocampus highlight, and disclose the
original cutoff, exact day interval, historical model and failed release gates.
Show `Preview ready (pre-generated)` instead of inventing an ETA. Missing,
changed or unowned source/artifacts show an unavailable state. No 365-day or
current-patient forecast is inferred from this example.

The approved longitudinal anatomy direction is integrated into both existing workspace
variants; see [17](17-longitudinal-anatomy.md). It adds measured labels, QC provenance,
source observations, continuous-score availability/history, head-size ratios and a
separate report action. Current/future selection keeps unavailable future anatomy
explicit; there is no fabricated image or transition animation. The generic canvas
accepts owned GIFTI buffers, but the real model-to-artifact-to-viewer path is incomplete.

## Separate baseline forecast panel

D053 supersedes D052: the default ML-only patient workspace omits the complete
Clinical + FastSurfer baseline forecast panel, its readiness button, descriptions,
blocked status, risk cards and release warnings. It retains MRI viewing/upload,
anatomy measurements and the separate experimental future MRI workspace. Settings
still separates service health from model readiness. The retained UI modes below
apply only to explicit research opt-out.

Imported OASIS patient workspaces also display a separate baseline forecast panel.
Its clinical, clinical-matched and clinical+FastSurfer choices call the same adapter
as the requested local Streamlit workspace. Keep the retrospective analysis and
baseline-only CDR conversion target visibly separate. Unsupported horizons show
Unavailable, not 0%. Missing models/anatomy/QC never silently fall back. Show MRI
usage, versions, QC, uncalibrated status, missing test support and feature associations.
This panel does not rewrite the existing PDF report's retrospective result.

## Product feel

The application should feel like a clinical research platform, not an ML notebook. Use dark navy surfaces, restrained cyan accents, clear typography, accessible contrast, and dense but readable data views.

## Authentication screen

Provide a researcher login screen with email, password, validation, loading state, and error state. Use JWT access tokens. Never expose secrets in browser code.

## Application layout

D054 omits the standalone `MRI timeline` panel from the default patient page;
scan selection uses `MRI visit` and the 3D workspace's existing navigation.

```
Header: Alzhio | Researcher | Online
Sidebar: Dashboard, Patients, Reports
Dashboard: overview metrics and recent patients
Patient page: summary, MRI timeline, risk chart, biomarkers, Analyze MRI
Analysis workspace: visit selector, MRI, heatmap, navigation, risk, confidence
Reports page: generated reports and download action
```

The dashboard also provides a patient-value snapshot with patient and observed-visit
selectors. D068 removes the BMI, total hippocampus and hippocampal volume change
cards. It shows available recorded OASIS values, anatomy estimates and regional
volumes. Hide cards with missing/nonfinite values, empty measurement sections,
unavailable regional columns/cells and result panels without complete displayable
data. Zero remains a valid measurement. Display recorded sex/handedness as text.
Keep the research provenance of available MTA/Koedam estimates. Provide a link to
the full patient case for 3D MRI.

## Core interactions

The MRI file picker accepts one `.nii`/`.nii.gz` volume or complete `.hdr`/`.img`
pairs, including `.nifti.hdr`/`.nifti.img` names. Permit selecting all files from
several paired acquisitions, then show `MRI acquisition` and default to `mpr-1`
when present. Show which pair will be uploaded; one acquisition belongs to the
selected visit. Missing partners, duplicate files, mixed formats and oversized
acquisitions show actionable errors and disable upload. Keep required age/nWBV
and the pending visit delete action. Convert pairs locally for the existing MRI
viewer and processing policy; no archive extraction is introduced (D071).

`Add patient` requires baseline age and nWBV (fraction). The patient code is
assigned automatically; show this as explanatory text, with no editable code
field. Creation opens the patient with its pending baseline MRI upload screen,
prefilling the entered values. Every upload requires age and nWBV alongside the
MRI file or header/image pair; follow-up visits collect their own scan-time values. Optional sex and
notes remain available. Display validation/request errors and disable submission
and fields while saving or uploading (D070).

MRI Analysis initially selects OAS2_0048 (D058). Preserve subsequent manual
patient selection across refresh polling; fall back to the first available
patient if OAS2_0048 is absent.

After `Save visit`, select the newly added visit's upload screen. Empty visits
offer `Delete visit` beside the `MRI visit` selector (D056/D057), refresh selection on success and show
errors on failure. Upload, deletion and file selection are disabled during either
request; deleting does not require an MRI selection or submit the upload form.

The patient directory defaults to OAS2_0048, OAS2_0070, OAS2_0073, OAS2_0127,
then OAS2_0017 at the top (D055). Search still filters every patient; remaining
rows retain their original order and absent priority patients are omitted.

In the MRI analysis anatomy panel, show the first four regional measurements by
default. A dropdown button reveals/collapses the remaining rows and resets on
visit/analysis changes. Omit the observed-versus-model-predicted regional anatomy
chart and its region selector (D041).

- Sign in as a researcher.
- List and select a patient.
- Create a patient and add a visit.
- Upload an MRI file.
- Start analysis and see queued, processing, completed, or failed states.
- Select visits from the MRI timeline.
- Toggle original MRI and explanation overlay.
- Navigate previous/current/next visit.
- Generate and download a research report.

## Required labels

- `Research Prototype`
- `Not a medical diagnosis`
- `Output mode: Demo`, `Precomputed`, or `Inference`
- `Output mode: Trained` for the explicitly experimental checkpoint, with one retrospective sequence score, poor-generalization evidence and in-sample cohort disclosure; no fabricated neural trajectory
- `Progression-risk estimate`
- `Model confidence` only when confidence is actually available

## MRI visualization

Preserve the rendered 2D MRI/overlay viewer as a lightweight fallback. The user explicitly requested interactive 3D exploration on 2026-10-01. Use NiiVue for client-only WebGL2 rendering of actual owner-authorized NIfTI volumes (D014), rather than building a new rendering engine.

The 3D workspace includes volume and multiplanar layouts, axial/coronal/sagittal views, camera presets, opacity/intensity/colormap controls, clipping, crosshair navigation, linked baseline-versus-selected-visit comparison, research difference overlays when available, fullscreen and PNG snapshots. Only the active scan and optional comparison scan are loaded; switching/unmounting releases GPU resources. Unsupported WebGL2 and failed downloads show explicit errors while the existing 2D viewer remains available.

Volumes contain the actual MRI, including non-brain head tissue. No cortical mesh, tissue segmentation, tractography or anatomical labels may be invented from this structural dataset. Difference volumes are shape-normalized intensity proxies, not registered changes, segmented atrophy or Grad-CAM. Viewer coordinates are not validated clinical measurements.

The lightweight 2D fallback uses a central axial slice in canonical RAS orientation, displayed neurologically (left label L, right R, anterior at the top). The difference overlay is explicitly a baseline intensity-difference proxy, not registered anatomy or Grad-CAM. Selecting another visit resets the overlay. Missing artifacts have an actionable unavailable state.

The dashboard prefers a completed analysis containing at least three visits for its featured longitudinal trajectory. Recent records and overview counts remain actual persisted data, including single-visit cases. Charts are static between updates; the mobile navigation is hidden from keyboard focus when closed. All screens provide empty, loading and error states.

Resource polling never overlaps an existing request for the same path. Switching patients hides the old data immediately and ignores late responses from the previous selection, so an earlier case cannot replace the currently selected case.

## Insight generation

Use constrained template-based text from computed results. Avoid unrestricted medical language. Every insight includes a caveat that qualified review and independent validation are required.
