# Patient directory — visual skin proposal

Scope: design artifact only. The current `frontend/app/(workspace)/patients/page.tsx`,
`PatientTable` and `Shell` define all structure, labels, icons and positions.
Keep the title/action row, inline creation form, directory heading/search row,
six table columns and footer in that order. Preserve current responsive breakpoints.
Do not add tabs, metrics, filters, pagination, icons, actions or navigation items.
Current branding is the Alzhio text wordmark; the pasted brief's historical
NeuroPredict name does not authorize changing the application's identity.

## Proposed visual tokens

- Background: #F8FAFC. Cards/header: #FFFFFF. Secondary surfaces: #F4F6FA.
- Navigation/primary buttons: #050B1D. Text: #07101F. Muted: #68778D.
- Borders: #E8EDF3. Selected-navigation fill: #20203D; text: #C8C2F4.
- Accent: #7770B7. Restrained cyan: #5DABB8. Success: #347D61.
- Pending: #906F38 on #FBF7ED. Error: #A25358 on #FCF2F3.
- Inter, primary title 40px/700, card title 18px/650, body 14px, supporting 12px.
- Card radius 22px; sidebar radius 32px; button/input radius 12px; status pills 99px.
- Card shadow: 0 8px 32px rgba(5,11,29,.035), 0 1px 2px rgba(5,11,29,.025).
- Subtle 180ms color/border/shadow transitions. No large movement or gradients.
- Preserve existing layout geometry: sidebar width, header height, gaps, padding,
  button locations, table column order, icon dimensions and ordering.

The missing reference image prevents exact screenshot matching. These tokens
follow the supplied textual direction. Preview rows use synthetic identifiers and
demographics; no real patient record or MRI pixels go to Superdesign. Use current
copy and all missing-output/status semantics without inventing results.

MRI guidance for this visual proposal: light surrounding panels/toolbars, unchanged
near-black image viewport, unchanged acquired pixels, segmentation color and NiiVue
controls in their current positions. No decorative brain image or replacement MRI.
