# Existing theme
Next.js 16 / React 19, Tailwind 4, shadcn-style Button, Lucide, Recharts, NiiVue.
Background #0b121c; surface #111c29; surface-alt #142231; border #223141; text #e7eef6; muted #93a5b8; cyan #66dfd2; radius 12px. Inter/Segoe UI/Arial; body 14px/1.55; h1 31px/600, h2 17px/600, h3 15px/600. Buttons 40px minimum, 7px radius, 12px/650. Dark navy clinical-research workspace. CSS is authoritative for spacing/shadows/responsiveness. Tailwind 4 has no separate config.

Extend existing patient analysis; no new app/auth/viewer. Keep existing sidebar/topbar, original-MRI selection, baseline-conversion panel. New longitudinal anatomy feature: score estimates, measured region history and changes, QC, and current vs predicted-time viewer. Only synthetic placeholder cases; unavailable model outputs are null, not made-up scores/brains. Distinguish planned UI from functioning scientific pipeline. No external patient assets. Subtle transitions only; no crossfade presented as prediction.

