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
        result = self.run_command(
            [
                sys.executable,
                "src/tools/scientific_circt_source_variant_regression_cli.py",
                "--self-check",
                "--variant",
                "not_a_real_variant",
            ],
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed_unknown_variant", result.stdout)

    def test_self_check_function_importable_and_matches_cli_behavior(self) -> None:
        import scientific_circt_source_variant_regression as regression

        cases = regression.load_reference()
        summary = regression_cli.self_check(cases)
        self.assertEqual(summary["status"], "self_check_passed")
        self.assertTrue(summary["oracle_detected"])
        self.assertTrue(summary["speedup_detected"])


if __name__ == "__main__":
    unittest.main()
