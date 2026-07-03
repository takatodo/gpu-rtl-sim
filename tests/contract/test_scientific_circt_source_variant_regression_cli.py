import sys
import unittest

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_source_variant_regression_cli as regression_cli  # noqa: E402

# The mutual-exclusion / import test noted in the M1 plan as deferrable lives
# here in M2, alongside the CLI module it actually exercises.


class ScientificCirctSourceVariantRegressionCliTest(HybridCliTestCase):
    def test_run_and_self_check_are_mutually_exclusive(self) -> None:
        result = self.run_command(
            [
                sys.executable,
                "src/tools/scientific_circt_source_variant_regression_cli.py",
                "--run",
                "--self-check",
            ],
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not allowed with argument", result.stderr)

    def test_missing_mode_argument_is_rejected(self) -> None:
        result = self.run_command(
            [sys.executable, "src/tools/scientific_circt_source_variant_regression_cli.py"],
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_self_check_cli_exits_zero_and_reports_both_detections(self) -> None:
        result = self.run_command(
            [sys.executable, "src/tools/scientific_circt_source_variant_regression_cli.py", "--self-check"],
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('"oracle_detected": true', result.stdout)
        self.assertIn('"speedup_detected": true', result.stdout)
        self.assertIn('"status": "self_check_passed"', result.stdout)
        self.assert_no_local_absolute_paths(result.stdout)

    def test_help_is_clean(self) -> None:
        result = self.run_command(
            [sys.executable, "src/tools/scientific_circt_source_variant_regression_cli.py", "--help"],
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--self-check", result.stdout)
        self.assertIn("--run", result.stdout)

    def test_unknown_variant_fails_closed(self) -> None:
        # --self-check ignores --variant entirely (see below), so unknown
        # variant fail-closed validation is exercised via --run instead: it
        # still fails there before any report is loaded.
        result = self.run_command(
            [
                sys.executable,
                "src/tools/scientific_circt_source_variant_regression_cli.py",
                "--run",
                "--variant",
                "not_a_real_variant",
            ],
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed_unknown_variant", result.stdout)

    def test_self_check_ignores_variant_and_still_exercises_promote_rows(self) -> None:
        # block2_hls_friendly is the only fallback row (zero promote rows in
        # this selection). Before the fix, --self-check would filter to this
        # selection and vacuously pass without checking anything.
        result = self.run_command(
            [
                sys.executable,
                "src/tools/scientific_circt_source_variant_regression_cli.py",
                "--self-check",
                "--variant",
                "block2_hls_friendly",
            ],
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('"oracle_detected": true', result.stdout)
        self.assertIn('"speedup_detected": true', result.stdout)
        self.assertIn('"status": "self_check_passed"', result.stdout)

    def test_self_check_fails_closed_with_zero_promote_rows_in_reference(self) -> None:
        import scientific_circt_source_variant_regression as regression

        block2_only = [case for case in regression.load_reference() if case.expected_policy != "promote_to_hls_gpu"]
        self.assertTrue(block2_only)
        summary = regression_cli.self_check(block2_only)
        self.assertEqual(summary["status"], "self_check_failed")
        self.assertEqual(summary["reason"], "no_promote_rows_in_reference")
        self.assertFalse(summary["oracle_detected"])
        self.assertFalse(summary["speedup_detected"])

    def test_self_check_function_importable_and_matches_cli_behavior(self) -> None:
        import scientific_circt_source_variant_regression as regression

        cases = regression.load_reference()
        summary = regression_cli.self_check(cases)
        self.assertEqual(summary["status"], "self_check_passed")
        self.assertTrue(summary["oracle_detected"])
        self.assertTrue(summary["speedup_detected"])

    def test_repeat_zero_fails_closed_with_structured_error(self) -> None:
        result = self.run_command(
            [
                sys.executable,
                "src/tools/scientific_circt_source_variant_regression_cli.py",
                "--run",
                "--repeat",
                "0",
            ],
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed_invalid_repeat", result.stdout)

    def test_run_regression_records_per_sample_speedups_and_statuses(self) -> None:
        from unittest import mock

        import scientific_circt_source_variant_regression as regression

        case = regression.RegressionCase(
            source_variant="synthetic_case",
            expected_policy="promote_to_hls_gpu",
            recorded_variant_speedup=10.0,
            recorded_baseline_speedup=1.0,
            relative_band=0.5,
            absolute_floor=0.05,
            min_improvement_margin=0.0,
            provenance={},
        )
        samples = [
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 9.5, "status": "runtime_handoff_boundary_measured"},
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 10.5, "status": "runtime_handoff_boundary_measured"},
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 10.0, "status": "runtime_handoff_boundary_measured"},
        ]
        metadata_report = {"rows": [{"source_variant": "synthetic_case", "candidate": "x", "shape": "1x1"}]}
        with mock.patch.object(regression_cli.regression, "run_variant_samples", return_value=samples):
            summary = regression_cli.run_regression(
                [case], metadata_report=metadata_report, matrix={}, hls_summary={}, repeat=3
            )
        result = summary["results"]["synthetic_case"]
        self.assertTrue(result["passed"])
        self.assertEqual(result["sample_observed_speedups"], [9.5, 10.5, 10.0])
        self.assertEqual(result["sample_statuses"], ["runtime_handoff_boundary_measured"] * 3)


if __name__ == "__main__":
    unittest.main()
