import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from scientific_circt_gpu_candidate_plan import build_plan  # noqa: E402


class ScientificCirctGpuCandidatePlanTest(HybridCliTestCase):
    def test_plan_lists_scientific_candidates_without_execution_claims(self) -> None:
        plan = build_plan(repeat=5)

        self.assertEqual(plan["surface"], "scientific_circt_gpu_candidate_plan")
        self.assertIn(plan["status"], {"planned_not_run", "blocked_circt_toolchain_missing"})
        self.assertGreaterEqual(plan["candidate_count"], 5)
        self.assertIn("no_gpu_execution", plan["non_claims"])
        self.assertIn("no_speedup_claim", plan["non_claims"])
        self.assertIn("require static suitability before GPU execution", plan["selection_policy"])
        self.assert_no_local_absolute_paths(json.dumps(plan, sort_keys=True))

        dense = plan["candidates"][0]
        self.assertEqual(dense["id"], "dense_matmul_tile")
        self.assertEqual(dense["expected_gpu_bucket"], "gpu_state_parallel")
        self.assertIn("regular_memory_access", dense["why"])
        self.assertEqual(
            [stage["stage"] for stage in dense["pipeline"]],
            [
                "author_mlir_or_circt_input",
                "circt_lower_to_systemverilog",
                "verilator_build",
                "emit_lowered_llvm_ir",
                "static_gpu_suitability",
                "measured_cpu_hybrid_repeat_median",
            ],
        )
        measurement_stage = dense["pipeline"][-1]
        self.assertEqual(measurement_stage["measurements"][0]["repeat"], 5)
        self.assertIn("hybrid_template_repeat_median.py", measurement_stage["measurements"][0]["command"])

    def test_candidate_filter_and_cli_report(self) -> None:
        plan = build_plan(candidate_filter="softmax_exp_pipeline", repeat=2)
        self.assertEqual(plan["candidate_count"], 1)
        self.assertEqual(plan["candidates"][0]["id"], "softmax_exp_pipeline")
        self.assertIn("exp_unit_like_hot_ss_candidate", plan["candidates"][0]["why"])

        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "scientific_plan.json"
            result = self.run_python_tool(
                "src/tools/scientific_circt_gpu_candidate_plan.py",
                "--candidate",
                "dense_matmul_tile",
                "--repeat",
                "4",
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["candidate_count"], 1)
        self.assertEqual(report_payload["candidates"][0]["id"], "dense_matmul_tile")
        self.assertEqual(report_payload["candidates"][0]["pipeline"][-1]["measurements"][0]["repeat"], 4)
        self.assert_no_local_absolute_paths(result.stdout)

    def test_unknown_candidate_fails_closed(self) -> None:
        result = self.run_python_tool(
            "src/tools/scientific_circt_gpu_candidate_plan.py",
            "--candidate",
            "unknown_kernel",
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown candidate id", result.stderr)


if __name__ == "__main__":
    unittest.main()
