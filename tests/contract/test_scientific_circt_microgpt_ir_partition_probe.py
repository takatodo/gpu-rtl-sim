import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from scientific_circt_microgpt_ir_partition_probe import build_probe  # noqa: E402


class ScientificCirctMicrogptIrPartitionProbeTest(HybridCliTestCase):
    def _policy(self) -> dict[str, object]:
        return {
            "surface": "scientific_circt_gpu_selection_policy",
            "candidates": {
                "dense_matmul_tile": {
                    "recommended_action": "select_gpu_state_parallel",
                    "min_gpu_nstates": 256,
                    "required_steps": 1,
                },
                "batched_reduction": {
                    "recommended_action": "select_gpu_state_parallel",
                    "min_gpu_nstates": 256,
                    "required_steps": 1,
                },
                "softmax_exp_pipeline": {
                    "recommended_action": "select_gpu_state_parallel",
                    "min_gpu_nstates": 256,
                    "required_steps": 1,
                },
            },
        }

    def test_build_probe_selects_regular_math_ops_at_measured_boundary(self) -> None:
        report = build_probe(self._policy(), 256, 1, Path("reports/policy.json"))

        actions = {op["op"]: op["recommended_action"] for op in report["ops"]}
        self.assertEqual(actions["qkv_projection"], "select_gpu_state_parallel")
        self.assertEqual(actions["attention_softmax"], "select_gpu_state_parallel")
        self.assertEqual(actions["layernorm_reduction"], "select_gpu_state_parallel")
        self.assertEqual(actions["token_loop_and_sampling_control"], "select_cpu_or_new_mapping")
        self.assertEqual(actions["kv_cache_update"], "select_cpu_or_new_mapping")
        self.assertEqual(report["counts"]["gpu_state_parallel_op_count"], 8)
        self.assertIn("not_microgpt_execution", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_build_probe_selects_cpu_below_boundary(self) -> None:
        report = build_probe(self._policy(), 64, 1)
        actions = {op["op"]: op["recommended_action"] for op in report["ops"]}

        self.assertEqual(actions["qkv_projection"], "select_cpu_below_measured_boundary")
        self.assertEqual(actions["attention_softmax"], "select_cpu_below_measured_boundary")
        self.assertEqual(report["counts"]["gpu_state_parallel_op_count"], 0)

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy = root / "policy.json"
            out = root / "probe.json"
            policy.write_text(json.dumps(self._policy()), encoding="utf-8")
            result = self.run_python_tool(
                "src/tools/scientific_circt_microgpt_ir_partition_probe.py",
                "--policy",
                policy.as_posix(),
                "--nstates",
                "256",
                "--steps",
                "1",
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(json.loads(result.stdout), report_payload)
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
