# Next.js UI Specification

## Product feel

The application should feel like a clinical research platform, not an ML notebook. Use dark navy surfaces, restrained cyan accents, clear typography, accessible contrast, and dense but readable data views.

## Authentication screen

Provide a researcher login screen with email, password, validation, loading state, and error state. Use JWT access tokens. Never expose secrets in browser code.

## Application layout

```
Header: NeuroPredict AI | Researcher | Online
Sidebar: Dashboard, Patients, MRI Analysis, Reports, Settings
Dashboard: overview metrics and recent patients
Patient page: summary, MRI timeline, risk chart, biomarkers, Analyze MRI
Analysis workspace: visit selector, MRI, heatmap, navigation, risk, confidence
Reports page: generated reports and download action
```

## Core interactions

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
