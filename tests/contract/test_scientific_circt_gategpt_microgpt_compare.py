import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from scientific_circt_gategpt_microgpt_compare import build_comparison  # noqa: E402


class ScientificCirctGategptMicrogptCompareTest(HybridCliTestCase):
    def _micro_report(self, root: Path, shape: str, speedup: float, candidate: str = "microgpt_math_block") -> Path:
        path = root / f"{candidate}_{shape}.json"
        path.write_text(
            json.dumps(
                {
                    "status": "measured",
                    "candidate": candidate,
                    "shape": shape,
                    "median": {
                        "cpu_ms": 2.0,
                        "gpu_end_to_end_ms": 2.0 / speedup,
                        "gpu_kernel_ms": 0.25,
                        "cpu_to_gpu_end_to_end_speedup": speedup,
                        "cpu_to_gpu_kernel_speedup": 8.0,
                    },
                }
            ),
            encoding="utf-8",
        )
        return path

    def _selection(self) -> dict[str, object]:
        return {
            "external_testbench_candidates": {
                "gategpt": {
                    "checkout_path": "artifacts/external_gateGPT",
                    "gateGPT_cpu_output_manifest_testbench_count": 6,
                    "gpu_kernel_launch_smoke_status": "passed",
                    "gpu_kernel_launch_smoke_testbenches": ["tb_exp", "tb_core"],
                    "gateGPT_gpu_output_mapping_plan_status": "covered",
                    "gateGPT_gpu_output_mapping_plan_gpu_stdout_finish_export_claimed": False,
                    "gateGPT_pass_fail_equivalence_on_gpu": False,
                    "gateGPT_tb_exp_distinct_state_resident_repeat_median_case_count": 103,
                    "gateGPT_tb_exp_cpu_baseline_wall_ms_median": 28.0,
                    "gateGPT_tb_exp_distinct_state_resident_repeat_median_wall_ms_median": 1.0,
                    "gateGPT_tb_exp_distinct_resident_repeat_gpu_cpu_compare_wall_speedup_observed": 28.0,
                    "gateGPT_tb_exp_distinct_resident_repeat_gpu_cpu_compare_speedup_claimed": False,
                    "gateGPT_tb_core_cpu_baseline_wall_ms_median": 22.0,
                    "gateGPT_tb_core_distinct_state_pair_cycle_loop_repeat_cpu_compare_gpu_wall_ms_median": 286.0,
                    "gateGPT_tb_core_distinct_state_pair_cycle_loop_repeat_cpu_compare_wall_speedup_vs_cpu_observed": 0.08,
                    "gateGPT_tb_core_distinct_state_pair_cycle_loop_repeat_cpu_compare_speedup_claimed": False,
                }
            },
            "scientific_circt_gpu_candidate_search": {
                "microgpt_math_block": {
                    "systemverilog": "artifacts/scientific_circt/microgpt_math_block/microgpt_math_block.sv",
                    "verilator_cpu_reference": "cpu_reference_pass",
                },
                "microgpt_attention_head": {
                    "systemverilog": "artifacts/scientific_circt/microgpt_attention_head/microgpt_attention_head.sv",
                    "verilator_cpu_reference": "cpu_reference_pass",
                },
                "microgpt_block_slice": {
                    "systemverilog": "artifacts/scientific_circt/microgpt_block_slice/microgpt_block_slice.sv",
                    "verilator_cpu_reference": "cpu_reference_pass",
                },
                "microgpt_inference_slice": {
                    "systemverilog": "artifacts/scientific_circt/microgpt_inference_slice/microgpt_inference_slice.sv",
                    "verilator_cpu_reference": "cpu_reference_pass",
                }
            },
        }

    def _source(self, root: Path) -> Path:
        path = root / "microgpt.py"
        path.write_text(
            "\n".join(
                [
                    "import math",
                    "n_layer = 1",
                    "n_embd = 16",
                    "block_size = 16",
                    "n_head = 4",
                    "class Value: pass",
                    "def linear(x, w): return []",
                    "def softmax(logits): return [x.exp() for x in logits]",
                    "def rmsnorm(x): return x",
                    "def gpt(token_id, pos_id, keys, values):",
                    "    attn_wq = attn_wk = attn_wv = mlp_fc1 = mlp_fc2 = None",
                    "loss.backward()",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def test_build_comparison_prefers_microgpt_for_partition_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = [
                self._micro_report(root, "64x1", 0.5),
                self._micro_report(root, "256x1", 2.0),
                self._micro_report(root, "1024x1", 3.0, "microgpt_attention_head"),
                self._micro_report(root, "1024x1", 2.5, "microgpt_block_slice"),
                self._micro_report(root, "1024x1", 2.25, "microgpt_inference_slice"),
            ]
            result = build_comparison(self._selection(), reports, self._source(root))

        self.assertEqual(result["status"], "compared")
        self.assertEqual(result["comparison"]["gpu_partition_discovery_preference"], "microgpt_direct_ir_circt")
        self.assertEqual(result["comparison"]["integration_testbench_preference"], "gateGPT_rtl")
        self.assertEqual(result["microgpt_direct_circt_sv"]["best_end_to_end"]["shape"], "1024x1")
        self.assertEqual(
            result["microgpt_direct_circt_sv"]["systemverilog_by_candidate"]["microgpt_attention_head"],
            "artifacts/scientific_circt/microgpt_attention_head/microgpt_attention_head.sv",
        )
        self.assertEqual(
            result["microgpt_direct_circt_sv"]["systemverilog_by_candidate"]["microgpt_block_slice"],
            "artifacts/scientific_circt/microgpt_block_slice/microgpt_block_slice.sv",
        )
        self.assertEqual(
            result["microgpt_direct_circt_sv"]["systemverilog_by_candidate"]["microgpt_inference_slice"],
            "artifacts/scientific_circt/microgpt_inference_slice/microgpt_inference_slice.sv",
        )
        self.assertIn("two-token inference", result["microgpt_direct_circt_sv"]["interpretation"])
        self.assertTrue(result["microgpt_direct_circt_sv"]["source_scan"]["detected_kernel_shapes"]["attention"])
        self.assertEqual(result["gategpt_rtl"]["tb_core"]["classification"], "stateful_token_control_cpu_negative")
        self.assertIn("not_full_microgpt_execution", result["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(result, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selection = root / "selection.json"
            source = self._source(root)
            out = root / "compare.json"
            report = self._micro_report(root, "256x1", 2.0)
            selection.write_text(json.dumps(self._selection()), encoding="utf-8")
            result = self.run_python_tool(
                "src/tools/scientific_circt_gategpt_microgpt_compare.py",
                "--selection",
                selection.as_posix(),
                "--microgpt-source",
                source.as_posix(),
                "--microgpt-report",
                report.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(json.loads(result.stdout), report_payload)
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
