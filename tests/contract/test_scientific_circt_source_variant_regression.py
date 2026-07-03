import sys
import unittest
from typing import Any

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_source_variant_regression as regression  # noqa: E402

# Deviation from plan: the CLI (scientific_circt_source_variant_regression_cli.py)
# lands in M2, so the CLI mutual-exclusion import test lives in
# tests/contract/test_scientific_circt_source_variant_regression_cli.py alongside
# the CLI itself instead of in this M1 file.


class ScientificCirctSourceVariantRegressionTest(HybridCliTestCase):
    def test_load_reference_has_four_rows_with_three_promote_one_fallback_policy_split(self) -> None:
        cases = regression.load_reference()
        self.assertEqual(len(cases), 4)
        policies = [case.expected_policy for case in cases]
        self.assertEqual(policies.count("promote_to_hls_gpu"), 3)
        self.assertEqual(policies.count("fallback_baseline_no_speedup_improvement"), 1)
        variants = {case.source_variant for case in cases}
        self.assertEqual(
            variants,
            {
                "attention_head4_hls_friendly",
                "mlp4_hls_friendly",
                "inference2_hls_friendly",
                "block2_hls_friendly",
            },
        )

    def _attention_head4_case(self) -> Any:
        cases = regression.load_reference()
        return next(case for case in cases if case.source_variant == "attention_head4_hls_friendly")

    def _block2_case(self) -> Any:
        cases = regression.load_reference()
        return next(case for case in cases if case.source_variant == "block2_hls_friendly")

    def test_decide_promote_case_passes_on_in_band_synthetic_samples(self) -> None:
        case = self._attention_head4_case()
        samples = [
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 18.5, "status": "runtime_handoff_boundary_measured"},
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 19.0, "status": "runtime_handoff_boundary_measured"},
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 18.7, "status": "runtime_handoff_boundary_measured"},
        ]
        passed, reason = regression.decide_promote_case(case, samples)
        self.assertTrue(passed)
        self.assertEqual(reason, "passed")

    def test_decide_promote_case_fails_oracle_mismatch_on_corrupted_oracle_samples(self) -> None:
        case = self._attention_head4_case()
        samples = regression.inject_corrupted_samples("oracle")
        passed, reason = regression.decide_promote_case(case, samples)
        self.assertFalse(passed)
        self.assertEqual(reason, "oracle_mismatch")

    def test_decide_promote_case_fails_speedup_out_of_band_on_corrupted_speedup_samples(self) -> None:
        case = self._attention_head4_case()
        samples = regression.inject_corrupted_samples("speedup")
        passed, reason = regression.decide_promote_case(case, samples)
        self.assertFalse(passed)
        self.assertEqual(reason, "speedup_out_of_band")

    def test_decide_promote_case_fails_lost_improvement_margin_when_median_at_or_below_baseline(self) -> None:
        # A synthetic case (not one of the four reference rows) whose band is
        # wide enough that an at-baseline median stays in-band, isolating the
        # margin check from the band check.
        case = regression.RegressionCase(
            source_variant="synthetic_margin_case",
            expected_policy="promote_to_hls_gpu",
            recorded_variant_speedup=10.0,
            recorded_baseline_speedup=9.0,
            relative_band=0.5,
            absolute_floor=0.05,
            min_improvement_margin=0.0,
            provenance={},
        )
        samples = [
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 9.0, "status": "runtime_handoff_boundary_measured"}
            for _ in range(3)
        ]
        passed, reason = regression.decide_promote_case(case, samples)
        self.assertFalse(passed)
        self.assertEqual(reason, "lost_improvement_margin")

    def test_decide_promote_case_fails_speedup_out_of_band_on_nan_speedup(self) -> None:
        # NaN comparisons are always false, so a naive `> band` check would
        # silently let a NaN speedup through. It must fail closed instead.
        case = self._attention_head4_case()
        samples = [
            {"output_equal": True, "checksum_equal": True, "observed_speedup": float("nan"), "status": "runtime_handoff_boundary_measured"}
            for _ in range(3)
        ]
        passed, reason = regression.decide_promote_case(case, samples)
        self.assertFalse(passed)
        self.assertEqual(reason, "speedup_out_of_band")

    def test_decide_promote_case_fails_speedup_out_of_band_on_none_speedup(self) -> None:
        case = self._attention_head4_case()
        samples = [
            {"output_equal": True, "checksum_equal": True, "observed_speedup": None, "status": "runtime_handoff_boundary_measured"}
            for _ in range(3)
        ]
        passed, reason = regression.decide_promote_case(case, samples)
        self.assertFalse(passed)
        self.assertEqual(reason, "speedup_out_of_band")

    def test_decide_promote_case_fails_oracle_mismatch_on_failure_status_with_true_equality_fields(self) -> None:
        # Equality fields alone are not enough: a sample whose status shows
        # the run never actually dispatched/measured must still fail closed.
        case = self._attention_head4_case()
        samples = [
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 13.0, "status": "runtime_handoff_boundary_failed"}
            for _ in range(3)
        ]
        passed, reason = regression.decide_promote_case(case, samples)
        self.assertFalse(passed)
        self.assertEqual(reason, "oracle_mismatch")

    def test_decide_promote_case_fails_on_partial_sample_failure(self) -> None:
        case = self._attention_head4_case()
        samples = [
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 13.0, "status": "runtime_handoff_boundary_measured"},
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 13.2, "status": "runtime_handoff_boundary_measured"},
            {"output_equal": False, "checksum_equal": True, "observed_speedup": 13.1, "status": "runtime_handoff_boundary_measured"},
        ]
        passed, reason = regression.decide_promote_case(case, samples)
        self.assertFalse(passed)
        self.assertEqual(reason, "oracle_mismatch")

    def test_median_speedup_matches_statistics_median(self) -> None:
        samples = [
            {"observed_speedup": 1.0},
            {"observed_speedup": 3.0},
            {"observed_speedup": 2.0},
        ]
        self.assertEqual(regression.median_speedup(samples), 2.0)

    def test_median_speedup_none_when_no_numeric_samples(self) -> None:
        self.assertIsNone(regression.median_speedup([{"observed_speedup": None}]))

    def test_decide_fallback_case_passes_when_gate_rejected_and_never_dispatched(self) -> None:
        case = self._block2_case()
        run_report = {
            "status": "src_hybrid_verilator_metadata_gate_rejected",
            "commands": [{"stage": "resolve_verilator_root", "returncode": 0}],
            "metadata_gate": {"failed_checks": ["policy"]},
        }
        passed, reason = regression.decide_fallback_case(case, run_report)
        self.assertTrue(passed)
        self.assertEqual(reason, "passed")

    def test_decide_fallback_case_passes_when_gate_rejected_on_entrypoint_kind(self) -> None:
        case = self._block2_case()
        run_report = {
            "status": "src_hybrid_verilator_metadata_gate_rejected",
            "commands": [],
            "metadata_gate": {"failed_checks": ["entrypoint_kind"]},
        }
        passed, reason = regression.decide_fallback_case(case, run_report)
        self.assertTrue(passed)
        self.assertEqual(reason, "passed")

    def test_decide_fallback_case_fails_when_dispatched_by_status(self) -> None:
        case = self._block2_case()
        run_report = {
            "status": "runtime_handoff_boundary_measured",
            "commands": [{"stage": "source_variant_runtime_handoff_run", "returncode": 0}],
        }
        passed, reason = regression.decide_fallback_case(case, run_report)
        self.assertFalse(passed)
        self.assertEqual(reason, "fallback_variant_was_dispatched")

    def test_decide_fallback_case_fails_when_run_stage_present_even_with_other_status(self) -> None:
        case = self._block2_case()
        run_report = {
            "status": "runtime_handoff_boundary_failed",
            "commands": [{"stage": "source_variant_runtime_handoff_run", "returncode": 1}],
        }
        passed, reason = regression.decide_fallback_case(case, run_report)
        self.assertFalse(passed)
        self.assertEqual(reason, "fallback_variant_was_dispatched")

    def test_decide_fallback_case_fails_when_build_failed_past_gate(self) -> None:
        # A block2 run that got PAST the metadata gate and only died later, at
        # build. This must not be conflated with the intended fail-closed
        # metadata-gate rejection: it is a different failure point.
        case = self._block2_case()
        run_report = {
            "status": "src_hybrid_verilator_bridge_build_failed",
            "commands": [
                {"stage": "resolve_verilator_root", "returncode": 0},
                {"stage": "build_src_hybrid_verilator_bridge", "returncode": 1},
            ],
            "metadata_gate": {"checks": {"policy": True}},
        }
        passed, reason = regression.decide_fallback_case(case, run_report)
        self.assertFalse(passed)
        self.assertEqual(reason, "fallback_rejection_not_metadata_gate")

    def test_decide_fallback_case_fails_when_artifacts_missing_past_gate(self) -> None:
        case = self._block2_case()
        run_report = {
            "status": "runtime_handoff_artifacts_missing",
            "commands": [],
            "metadata_gate": {"checks": {"policy": True}},
        }
        passed, reason = regression.decide_fallback_case(case, run_report)
        self.assertFalse(passed)
        self.assertEqual(reason, "fallback_rejection_not_metadata_gate")

    def test_decide_fallback_case_fails_when_gate_rejected_for_unrelated_check(self) -> None:
        # Status matches the expected rejection point, but the failed check
        # is not policy/entrypoint_kind (e.g. a shape mismatch): still the
        # wrong rejection reason for a fallback-baseline row.
        case = self._block2_case()
        run_report = {
            "status": "src_hybrid_verilator_metadata_gate_rejected",
            "commands": [],
            "metadata_gate": {"failed_checks": ["shape"]},
        }
        passed, reason = regression.decide_fallback_case(case, run_report)
        self.assertFalse(passed)
        self.assertEqual(reason, "fallback_rejection_not_metadata_gate")

    def test_run_variant_samples_uses_injected_runner_as_di_seam(self) -> None:
        calls: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []

        def fake_runner(row: dict[str, Any], matrix: dict[str, Any], hls_summary: dict[str, Any]) -> dict[str, Any]:
            calls.append((row, matrix, hls_summary))
            return {
                "cpu_vs_gpu_output_equal": True,
                "cpu_vs_gpu_control_checksum_equal": True,
                "average": {"cpu_to_bridge_hybrid_wall_speedup": 12.0},
                "status": "runtime_handoff_boundary_measured",
            }

        row = {"source_variant": "attention_head4_hls_friendly", "candidate": "microgpt_attention_head", "shape": "1024x1"}
        samples = regression.run_variant_samples(row, {}, {}, 3, runner=fake_runner)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(samples), 3)
        for sample in samples:
            self.assertTrue(sample["output_equal"])
            self.assertTrue(sample["checksum_equal"])
            self.assertEqual(sample["observed_speedup"], 12.0)


if __name__ == "__main__":
    unittest.main()
