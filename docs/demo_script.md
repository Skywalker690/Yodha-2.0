# Baseline forecast demonstration

Start the local study dashboard on loopback port 8501 with the command in
[architecture guide](15-fastsurfer-architecture.md). Alternatively open an imported
OASIS patient in the existing authenticated application and use its separate baseline
forecast panel. Historical retrospective outputs remain separate.

Select a de-identified baseline case. Show recorded baseline demographics, MRI source
availability, FastSurfer QC and anatomy availability. Run the clinical reference:
12/24 months currently show Unavailable; 36 months may show an experimental,
uncalibrated estimate. Explain the sparse follow-up and missing test events. Do not
show fabricated anatomy or describe this as diagnosing Alzheimer disease.

Clinical+FastSurfer remains unavailable until processing and reviewed feature extraction
complete. A meaningful added-value comparison requires the clinical matched cohort;
full-clinical metrics are not a substitute. Never run bulk processing during the demo.
