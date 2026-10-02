# 3D MRI Visualization

User-requested extension, 2026-10-01. This expands the original 2D MVP without changing its research-only status or inference method.

## Library research and selection

| Library | Fit | Decision |
|---|---|---|
| NiiVue | Native NIfTI loading, MRI orientation, multiplanar slices, GPU volume rendering, clip planes, overlays and viewer synchronization | Selected: one MRI-focused browser package; BSD-2-Clause; pin 0.69.0 |
| vtk.js + ITK-Wasm | General scientific rendering and image IO; flexible custom pipelines | Suitable alternative, but more conversion, scene/controller and asset integration for this app |
| Cornerstone3D | Medical rendering, tools, caching and separately registered NIfTI/DICOM loaders and metadata providers | Suitable for a broader imaging workstation; more packages/integration than the present NIfTI-only workflow |

The selection is an engineering judgment for this dataset and stack, not a universal benchmark or clinical certification.

Primary sources inspected:

- [NiiVue installation and React integration](https://niivue.com/docs/)
- [NIfTI, volume and mesh loading](https://niivue.com/docs/loading/)
- [Layouts, slice types and 3D rendering](https://niivue.com/docs/layouts/)
- [Clip planes](https://niivue.com/docs/clip/)
- [Linked viewers and alignment caveats](https://niivue.com/docs/syncing/)
- [NiiVue source and license](https://github.com/niivue/niivue)
- [vtk.js overview and ITK-Wasm integration](https://kitware.github.io/vtk-js/docs/)
- [ITK-Wasm](https://docs.itk.org/projects/wasm/en/latest/)
- [Cornerstone3D scope, loaders and browser support](https://www.cornerstonejs.org/docs/getting-started/scope/)

## Product behavior

- Default axial view on patient entry and reset, with the existing alternative
  layouts available for manual selection (D072). Uploaded scans without measured
  masks show a FastSurfer segmentation prerequisite; valid masks remain highlighted
  by default. MRI volume rendering alone does not perform this segmentation.
- Actual selected MRI voxels, not a stock brain illustration.
- Rotatable/zoomable 3D rendering and orthogonal axial, coronal and sagittal slices.
- Four-up slice/volume layout and individual view modes.
- Orientation/camera presets, intensity window, colormap, opacity and cutaway plane controls.
- Accessible crosshair/slice navigation controls and coordinate readout.
- Optional baseline comparison with linked 2D navigation and 3D camera; linked views are not anatomical registration.
- Optional volumetric intensity-difference overlay from a completed analysis, with explicit provenance and non-registration caveat.
- Adjustable difference opacity and visualization threshold (normalized intensity, not a clinical cutoff); values below threshold are transparent so source anatomy stays visible.
- Reset, fullscreen and local PNG snapshot export.
- Loading/error/WebGL2-unavailable states and the existing 2D image fallback.
- Yellow hippocampus highlighting remains available in observed and predicted views;
  cyan temporal/parietal and purple ventricle highlighting are hidden. Predicted
  boundaries show the hippocampus and neutral gray complete brain mesh. Regional
  masks and meshes remain stored for analysis (D039, D040).

## Data and honesty boundaries

The supplied structural MRI contains brain and other head tissue. Volume rendering and clipping do not perform skull stripping, tissue segmentation or cortical reconstruction. No white-matter tracts or atlas regions are inferred or fabricated. Those require appropriate data and validated processing outside this visualization request.

Authenticated API endpoints serve immutable source NIfTI and generated difference-volume artifacts without exposing storage keys. Visualization uses existing researcher ownership. At most two active WebGL contexts are retained; cleanup aborts stale downloads and disposes viewer resources. No source MRI is sent to third-party services.

Display controls apply to both comparison panels; the Link option additionally synchronizes interactive mouse navigation by header coordinates. Camera rotation is retained when changing cutaways or windows. Lost GPU contexts show an explicit recovery error; Retry constructs a fresh canvas. Intensity windows/thresholds are applied after NiiVue colormap recalibration, with a regression test for that ordering.

D050 enables `isClipAllVolumes` in each canvas: NiiVue's default otherwise leaves
segmentation/difference overlays visible when MRI tissue is clipped away. Yellow
hippocampus highlighting is restored on experimental links/actions and shares the
MRI camera, zoom and clipping. This does not alter the saved anatomy prediction.

Difference artifacts contain absolute differences on the pipeline's normalized 64-cube grid, with an affine mapping that grid into the selected scan's canonical field of view. This is display geometry, not baseline-to-follow-up registration. Affine handling and finite values must be tested. Existing cached analyses without these artifacts remain valid 2D results and require new inference for 3D differences.

## Acceptance checks

Test unauthenticated/cross-researcher volume access, safe filenames, intact source data, difference shape/affine/provenance and unavailable old-cache artifacts. Type-check and unit-test controls and lifecycle. In a real WebGL2 browser, load an OASIS scan, rotate/zoom, change layouts and slice coordinates, apply clipping/window/opacity, toggle differences, compare baseline, export a PNG and navigate to another visit. Check cleanup, browser errors, canvas pixels, mobile layout and the no-WebGL fallback. Re-run the original login/analysis/report workflow.

## Verified implementation

The feature is integrated into the patient/analysis workspace and the packaged local stack. All five prepared OASIS cases (15 visits) have checked source/difference volume endpoints and display geometry. Automated checks pass: 23 Python tests, 19 frontend tests, 5 Microsoft Edge workflow tests, strict TypeScript, production Docker builds, Ruff, Alembic schema check and npm audit. Browser checks include actual varied volume pixels/rotation, context-loss recovery, no-WebGL fallback and no external HTTP requests. Desktop, mobile and annotated PNG exports were visually reviewed. These verify the software, not clinical validity; see [10 Implementation status](10-implementation-status.md).
