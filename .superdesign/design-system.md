# Alzhio workspace design system

Next.js 16 / React 19, Tailwind 4, shadcn-style Button, Lucide, Recharts, NiiVue. Tailwind 4 has no separate config.

## Existing visual tokens

Background #0b121c; surface #111c29; surface-alt #142231; border #223141; text #e7eef6; muted #93a5b8; cyan #66dfd2; radius 12px. Sidebar #0e1722; selected navigation #142c32 with #214047 border; selected viewer control #16383b with #28565a border; viewer background #080e18. Hippocampus annotation #dcd814 (the actual label-layer RGB 220/216/20); reserve this yellow for anatomy, not disease severity or decorative accents.

Inter/Segoe UI/Arial; body 14px/1.55; h1 31px/600, h2 17px/600, h3 15px/600. Muted supporting text 12px minimum in the proposed redesign. Buttons 40px minimum, 7px radius, 12px/650. Spacing scale 4/8/12/16/20/24/32px. Borders 1px; subdued shadows; subtle transitions. CSS is authoritative for existing appearance and responsive behavior.

## Identity and navigation

Use the current text-only Alzhio wordmark with its short teal underline. There is no selected graphic logo; do not invent a brain icon, initials, or a replacement mark. Sidebar navigation contains Dashboard, Patients, Reports only. Preserve the local workspace and research prototype identity. AlzhioBot must not cover viewer or assessment actions.

## Patient workspace design proposal

Compact patient header; proposed Overview / MRI Workspace / Assessment / Reports tabs. MRI Workspace is the initial visible design panel, with Axial selected by default. Preserve 3D volume, Slices + 3D, Coronal and Sagittal alternatives. Use a large viewer, compact acquired / 12 / 24 / 36-month controls, matched comparison, and collapsible advanced controls. No separate MRI timeline heading/card or prediction-readiness panel.

Yellow hippocampus labels belong to the matching image geometry in acquired and predicted views. They rotate, clip and move with their scan. An uploaded image without a corresponding segmentation cannot show real hippocampus anatomy: give one concise actionable processing state. Existing forecasts remain scalar-guided research illustrations where applicable; an available interval is not proof of clinical validation. Keep provenance available without repetitive unavailable cards.

Assessment uses the existing eleven-task MMSE-style demo protocol, visible progress, required explicit points (including valid zero), accessible choices, and fixed Back / Next / Save draft actions. Demo cognitive scores remain separate from clinical MMSE and model inputs. Do not invent real task prompts or clinical diagnoses.

## Preview data and assets

Use synthetic UI data only. An inline grayscale anatomical schematic is allowed solely as an explicitly labeled illustrative design asset, never a real acquired scan, segmentation, or forecast. Do not upload patient MRI, screenshots containing records, identifiers, or medical metadata. Unavailable model measurements remain absent; do not populate fake accuracy, risks, measured volumes, or processing ETAs. This is a design proposal, not a functioning inference pipeline.
