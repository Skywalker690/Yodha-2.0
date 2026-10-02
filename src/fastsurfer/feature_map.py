"""Compact, explicit DKT feature map. No whole-brain/ICV substitutions."""

FEATURE_SET = "dkt-compact-seg-v1"
# Read the real v2.5.4 file; the aseg+DKT.stats Linux alias is not portable to Windows.
STATS_RELATIVE = "stats/aseg+DKT.VINN.stats"
# FreeSurfer labels checked against the supplied FastSurfer LUT.
VOLUME_LABELS = {
    "hippocampus_left_mm3": (17, "Left-Hippocampus"),
    "hippocampus_right_mm3": (53, "Right-Hippocampus"),
    "ventricle_left_mm3": (4, "Left-Lateral-Ventricle"),
    "ventricle_right_mm3": (43, "Right-Lateral-Ventricle"),
    "entorhinal_left_mm3": (1006, "ctx-lh-entorhinal"),
    "entorhinal_right_mm3": (2006, "ctx-rh-entorhinal"),
}
ANATOMY = tuple(VOLUME_LABELS)
