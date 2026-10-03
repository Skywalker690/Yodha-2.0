# Alzhio complete interactive design preview

Design only, requested 2026-10-03. Continue the premium light direction from the
patient-directory draft. The existing application is the source of truth for all
routes, copy, navigation, icons, positions, workflow and conditional behavior.

## Reference research

- [Linear UI redesign](https://linear.app/now/how-we-redesigned-the-linear-ui):
  adopt its attention to typographic hierarchy, aligned controls, neutral surface
  layers and readable density. Do not copy its navigation or product structure.
- [Attio product](https://attio.com/): use its calm record/table treatment,
  restrained separators and clear primary actions as visual inspiration.
- [OHIF UI and appearance](https://docs.ohif.org/configuration/ui/): maintain a
  focused imaging surface and consistent tokens for toolbars, controls and dialogs.
  This is visual inspiration only; the project continues to use its existing NiiVue.
- Superdesign style-library exploration: technical/light workspace references
  reinforced the need for clear data typography. Decorative landing-page styles,
  glass effects, large motion and invented scientific imagery were not selected.

These are design judgments based on the inspected references, not endorsements or
clinical claims. The supplied inspiration is the previous light preview and written
brief; no additional reference image was attached.

## Visual system

- Cool off-white `#F6F8FC`, white panels, muted cool separators `#E5EAF2`.
- Navy navigation/primary actions `#070C20`, text `#0C162B`, muted slate `#64748B`.
- Quiet violet accents `#7164BC`, selected navigation `#23223F`.
- Rounded panels 22px, sidebar 30px, controls 11px, pills 99px.
- Inter, primary headings 40px/750, panel headings 18px/650, table figures with
  tabular numerals. Keep the original layout padding and responsive structure.
- Gentle 180ms color/border/shadow changes, with reduced-motion support.
- MRI canvas stays near black, with yellow hippocampus labels. Only surrounding
  chrome changes; original NiiVue controls, camera/overlay alignment and modes stay.
- Assessment steps, selected point choices, draft status, review and dialogs share
  the same surfaces and focus treatment. Alzhio Bot keeps its existing placement.

Canonical visual artifact: `.superdesign/full-product-skin.css`.
Feature checklist: `.superdesign/full-product-feature-inventory.md`.

## Sidebar refinement (D078)

The requested sidebar-only refinement uses a straight navy frame, a 22px Alzhio
wordmark, tighter brand/navigation grouping, 13px navigation labels, a bordered
violet active state, and a compact local-workspace card with a green connection
pill. Secondary labels use readable slate colors. The existing mobile drawer and
three navigation destinations remain. Every override is scoped to `.sidebar`;
all other design rules are preserved. The standalone override is
`.superdesign/sidebar-refinement.css`, also appended to the canonical skin.

D079 changes only sidebar colors to a slate-blue tonal background
(`#29425F` → `#122638`), pale teal selection (`#C0E5E2`), cool off-white text,
and a muted teal connection pill. Geometry and all outside-sidebar styling stay.
The palette override is `.superdesign/sidebar-color-grade.css`.

## Patient dashboard template arrangement (D080)

The user selected the existing navy/teal patient workspace draft
`70c1a9a3-6b4c-40a9-97d5-eca28eb63375`. The default patient dashboard preview now
uses its compact patient header, grouped MRI visit/Add visit controls and four
section links. The original MRI workspace comes first, ahead of assessment and
anatomy details. The links scroll to existing sections and preserve their actions.
The selected draft contains a static screenshot of the synthetic NiiVue canvas;
the local preview retains the original interactive viewer. All viewer components,
stylesheets, camera/mask behavior and forecast controls are unchanged. The template
arrangement is `.superdesign/patient-template-arrangement.css`, imported separately
only in the isolated copy. Historical research-mode case layouts retain their
existing arrangement.

## Preview construction and boundaries

Copy the current source UI into `artifacts/alzhio-design-preview`; preserve its
components, routes, hooks, input validation and viewer implementation. Append the
visual stylesheet only in that isolated copy. The real `frontend/`, live backend,
data, model checkpoints and runtime configuration are untouched.

A separate local, in-memory sample service implements the UI contracts exclusively
for this design preview. It simulates login, patients, chronological visits,
uploads, asynchronous jobs, anatomy/forecast fixtures, original demo assessment
drafts/completion, canned assistant answers and clearly labeled sample reports.
The viewer receives deterministic synthetic volumes/masks, never a real patient
scan or a claimed prediction. The persistent design notice names these boundaries.

An outside-canvas preview guide links to all existing routes, including the direct
MRI Analysis, Settings and saved anatomy gallery routes. It does not add items to
the product sidebar. Preserve Dashboard, Patients and Reports navigation order.

No implementation of the real product is authorized by this design request.
