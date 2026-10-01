# Baseline forecast preprocessing

Clinical: use the source baseline only, explicit numeric sex encoding, missing SES/MMSE
preserved. Per horizon, median imputation and StandardScaler are fitted solely on
known-label training rows. Regularized logistic regression C=0.1 is fixed before
evaluation. All-missing training predictors fail rather than receiving invented values.
Serialized JSON includes medians, means, scales, coefficients, intercept, training IDs,
source hashes and development-selected thresholds. A numerical reload check matches
scikit-learn predictions. Inference does not import sklearn, PyTorch or GPU software.

MRI: validate bounded real finite 3D intensity data, invertible affine, nonconstant
volume, positive spacing and no axis beyond 1.5 mm. Preserve original full-head MRI
and physical geometry. Convert paired NIfTI using NiBabel to native .nii.gz, check
voxel/affine equality, and record hashes of both header and image. FastSurfer itself
performs its documented conforming; do not input the old 64-cube normalized tensor.

No visit registration, future-visit template, longitudinal delta or future clinical
covariate enters the primary baseline forecast. The optional `src/mri/model.py`
implements the 128³ tensor/fusion interface and masked loss only. No optional CNN
training/checkpoint/predictions have been completed, and the adapter reports it unavailable.
