import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from scientific_circt_gpu_selection_policy import build_policy  # noqa: E402


class ScientificCirctGpuSelectionPolicyTest(HybridCliTestCase):
    def _summary(self) -> dict[str, object]:
        return {
            "surface": "scientific_circt_hybrid_advantage",
            "by_candidate": {
                "dense_matmul_tile": {
                    "record_count": 3,
                    "gpu_kernel_favorable": 3,
                    "first_gpu_end_to_end_favorable_shape": "256x1",
                },
                "branchy_candidate": {
                    "record_count": 3,
                    "gpu_kernel_favorable": 1,
                    "first_gpu_end_to_end_favorable_shape": None,
                },
            },
        }

    def test_build_policy_selects_gpu_only_for_measured_favorable_candidates(self) -> None:
        policy = build_policy(self._summary())

        self.assertEqual(policy["status"], "policy_ready")
        self.assertEqual(policy["gpu_ready_candidate_count"], 1)
        dense = policy["candidates"]["dense_matmul_tile"]
        self.assertEqual(dense["recommended_action"], "select_gpu_state_parallel")
        self.assertEqual(dense["min_gpu_nstates"], 256)
        self.assertEqual(dense["required_steps"], 1)
        branchy = policy["candidates"]["branchy_candidate"]
        self.assertEqual(branchy["recommended_action"], "measure_more_before_gpu")
        self.assertIn("not_automatic_partitioning", policy["non_claims"])
        self.assertEqual(policy["source_variants"], [])

    def test_build_policy_integrates_hls_source_variant_decisions(self) -> None:
        hls_report = {
            "variants": [
                {
                    "candidate": "microgpt_mlp_slice",
                    "variant": "mlp4_hls_friendly",
                    "shape": "1024x1",
                    "cpu_vs_gpu_output_equal": True,
                    "cpu_vs_gpu_control_checksum_equal": True,
                    "comparison": {
                        "baseline_speedup": 2.0,
                        "variant_speedup": 6.0,
                        "speedup_delta": 4.0,
                        "speedup_improved": True,
                    },
                },
                {
                    "candidate": "microgpt_block_slice",
                    "variant": "block2_hls_friendly",
                    "shape": "1024x1",
                    "cpu_vs_gpu_output_equal": True,
                    "cpu_vs_gpu_control_checksum_equal": True,
                    "comparison": {
                        "baseline_speedup": 5.0,
                        "variant_speedup": 4.0,
                        "speedup_delta": -1.0,
                        "speedup_improved": False,
                    },
                },
            ]
        }
        policy = build_policy(self._summary(), [hls_report])

        self.assertEqual(policy["source_variant_ready_count"], 1)
        by_variant = {item["source_variant"]: item for item in policy["source_variants"]}
        self.assertEqual(by_variant["mlp4_hls_friendly"]["recommended_action"], "promote_to_hls_gpu")
        self.assertEqual(by_variant["block2_hls_friendly"]["recommended_action"], "keep_baseline_gpu_or_cpu")
        self.assertIn("not_automatic_hls_rewrite", policy["non_claims"])

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary = root / "summary.json"
            out = root / "policy.json"
            summary.write_text(json.dumps(self._summary()), encoding="utf-8")
            result = self.run_python_tool(
                "src/tools/scientific_circt_gpu_selection_policy.py",
                "--summary",
                summary.as_posix(),
                "--hls-variant-report",
                summary.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(json.loads(result.stdout), report_payload)
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
