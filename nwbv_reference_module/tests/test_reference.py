"""Checks for reference provenance, sparse bins and unsupported clinical claims."""

import math
import unittest
from copy import deepcopy

from az_nwbv_reference import DEFAULT_USE, NwbvReference, OASIS2_NWBV_METHOD


class ReferenceContractTests(unittest.TestCase):
    def setUp(self):
        self.reference = NwbvReference.bundled()

    def test_baseline_reference_and_example(self):
        profile = self.reference.profile
        self.assertEqual(profile["reference_subjects"], 85)
        self.assertEqual([b["n"] for b in profile["bins"]], [6, 16, 16, 19, 13, 13, 2])
        result = self.reference.evaluate(age=73, nwbv=0.690,
                                         measurement_method=OASIS2_NWBV_METHOD)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["intended_use"], DEFAULT_USE)
        self.assertFalse(result["feature_use_allowed"])
        self.assertTrue(math.isclose(result["z_score"], -1.666255, rel_tol=1e-5))
        self.assertEqual(result["relative_volume_band"], "between_1_and_2_sd_below_reference_mean")
        self.assertIsNone(result["clinical_risk"])
        self.assertNotIn("percentile", result)

    def test_sparse_bins_and_method_mismatch_have_no_score(self):
        for age in (60, 64, 90, 94):
            with self.subTest(age=age):
                result = self.reference.evaluate(age=age, nwbv=.70,
                                                 measurement_method=OASIS2_NWBV_METHOD)
                self.assertEqual(result["status"], "insufficient_reference")
                self.assertIsNone(result["z_score"])
        mismatch = self.reference.evaluate(age=73, nwbv=.70,
                                           measurement_method="fastsurfer_brain_over_etiv")
        self.assertEqual(mismatch["status"], "method_mismatch")
        self.assertIsNone(mismatch["z_score"])
        edge = self.reference.evaluate(age=95, nwbv=.70,
                                       measurement_method=OASIS2_NWBV_METHOD)
        self.assertEqual(edge["status"], "unsupported_age")

    def test_new_measurement_method_requires_its_own_profile(self):
        alternate = deepcopy(self.reference.profile)
        alternate["profile_id"] = "example_synmri_v1"
        alternate["measurement_method"] = "example_synmri_nwbv_fraction_v1"
        alternate_reference = NwbvReference(alternate)
        self.assertEqual(
            alternate_reference.evaluate(age=73, nwbv=.69,
                                         measurement_method=OASIS2_NWBV_METHOD)["status"],
            "method_mismatch",
        )
        self.assertEqual(
            alternate_reference.evaluate(age=73, nwbv=.69,
                                         measurement_method="example_synmri_nwbv_fraction_v1")["status"],
            "ok",
        )


if __name__ == "__main__":
    unittest.main()
