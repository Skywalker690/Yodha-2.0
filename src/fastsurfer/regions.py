"""Separate dictionary: never expand the baseline model feature set implicitly."""

from src.fastsurfer.feature_map import VOLUME_LABELS

VERSION = "dkt-longitudinal-v1"
REGIONS = dict(VOLUME_LABELS)
for side, offset in (("left", 1000), ("right", 2000)):
    hemi = "lh" if side == "left" else "rh"
    for number, name in (
        (8, "inferiorparietal"),
        (9, "inferiortemporal"),
        (15, "middletemporal"),
        (25, "precuneus"),
        (29, "superiorparietal"),
        (30, "superiortemporal"),
    ):
        REGIONS[f"{name}_{side}_mm3"] = (offset + number, f"ctx-{hemi}-{name}")
