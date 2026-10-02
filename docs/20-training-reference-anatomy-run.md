# Training-reference future anatomy

D044 restores training-only baseline-CDR-zero reference construction; the next
user correction removes the ten-subject cutoff. Keep the seven five-year bins
60–64 through 90–94. Calculate `(observed nWBV - training-bin mean) / sample SD`
when n>=2 and SD>0. Two is necessary for sample SD, not clinical validation.
Unsupported/invalid/singleton/zero-spread states stay explicit. Never substitute
raw nWBV, widen bins or include held-out subjects to increase availability.

Check the original metadata file against the frozen cohort fingerprint. Only
original Visit=1, MR Delay=0 baselines in the training role can fit reference values.
There are 44 declared training subjects and 33 eligible CDR-zero baselines;
bin counts are 2,8,5,7,6,4,1. Both checkpoints save the same reference with exact
membership, values, exclusions and hash. Selection/calibration/test/inference
cannot refit it. A partial run distinguishes actually processed training subjects
from the wider declared training cohort used solely for baseline reference values.

Input version: `anatomy-input-v4-train-age-reference`. Spatial version:
`conditioned-pull-cnn-v4-train-age-reference`. Release version:
`anatomy-research-release-v5-train-age-reference`. Older checkpoints fail explicitly.
The same 129 columns described in [19](19-fixed-reference-anatomy-run.md) remain:
forecast interval/history duration/visit count/four actual scan gaps, six observed
volume/change/rate fields for each of 18 FastSurfer regions, latest Z and MMSE,
four observed estimate/change/rate fields for each of three AVRA outputs.
Training-only medians/scales plus 129 missingness indicators produce 258 inputs.
Six registered acquired-image/mask channels condition the spatial network.
Hidden future scans are supervision only. Age, raw nWBV and other demographics
never condition either model; statistics and mask-voxel volumes stay separate.

Preserve the frozen 44 train / 4 selection / 4 calibration / 4 test assignments.
The waiting v3 full coordinator was stopped before fitting; its files and handoff
are retained. Fresh runs use `artifacts/anatomy-train-reference-partial-20261002/`
and `artifacts/anatomy-train-reference-full-20261002/`, copying verified existing
registrations after physical source/measurement matching. No old run is overwritten.

The updated worker and offline coordinator share a PostgreSQL advisory GPU slot.
The one-off partial helper waits for the older worker's active job to finish,
temporarily holds queued rows, stops only the verified idle worker, performs GPU
training and restarts the updated worker. The full coordinator waits for all
native histories before fitting, then performs native evaluation automatically.

The ML and training CLI are copied to each run's `runtime/` with file hashes in
`runtime-manifest.json`. The GPU container mounts that code read-only at `/runtime`;
native evaluation uses the same snapshot. Workspace edits cannot silently change
an ongoing experiment. Source data and credentials are not copied to the snapshot.
The GPU launch was preflighted inside the pinned image: 129 features, raw nWBV
excluded, 33 eligible reference subjects, minimum two for a positive sample SD.
Two launch prerequisites initially failed (an already-exited Windows child process,
then an incorrectly registered CLI reference flag); both were repaired without
writing a checkpoint. Logs are preserved. A regression verifies CLI reference binding.

Append actual training/evaluation evidence from saved real reports. Previous v3
performance is history, not a measurement of v4. Software checks do not establish
forecast accuracy or clinical validation.

Actual source audit under this reference: 352 of 373 visits have numeric Z;
17 belong to the singleton 90–94 reference group and four are outside ages 60–94.
At baseline, 146 of 150 subjects have numeric Z, three have the singleton group
and one an unsupported age. These counts are saved in `reference-availability.json`.
Eight completed source histories have yielded 20 prepared examples: six training
subjects (OAS2_0048, OAS2_0070, OAS2_0127, OAS2_0027, OAS2_0034, OAS2_0036),
selection OAS2_0017 and test OAS2_0073. Calibration remains absent in this partial
run. Reference eligibility still comes exclusively from the 44 frozen training
subjects, not selection/test subjects and not the descriptive bundled table.

The scan schedule in the full frozen split also fails predeclared subject support
for 183/365/731/1096-day horizons (±90 days). Source counts for train/selection/test
are respectively 2/0/1, 5/0/0, 15/0/1 and 4/0/1. These counts predict a remaining
horizon-support blocker; processing more scans cannot change their recorded dates.
Do not resplit subjects or invent yearly scans to improve this evidence. Full
time-conditioned model evaluation can still run on actual hidden scan intervals.

This test cohort has already been evaluated in earlier experiments. New metrics
are reused-holdout research results, not independent validation. Visual segmentation,
registration and AVRA alignment checks and independent rating agreement are still
unverified. No clinical validation is claimed even when geometric checks pass.
