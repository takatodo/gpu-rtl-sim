import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_non_veer_hybrid_next_queue import build_queue  # noqa: E402


class RtlmeterNonVeerHybridNextQueueTest(HybridCliTestCase):
    def _write_summary(self, root: Path) -> Path:
        path = root / "reports" / "summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "surface": "rtlmeter_non_veer_hybrid_measurement_summary",
                    "nvdla": {
                        "measured_shape_count": 2,
                        "gpu_favorable_shape_count": 2,
                        "favorable_ratio": 1.0,
                        "best_wall_speedup": {
                            "shape": "1024x64",
                            "target": "nvdla_cmac_a2cacc",
                            "cpu_to_hybrid_wall_speedup_ratio": 100.0,
                        },
                        "shape_buckets": {
                            "state_batch": {
                                "best_wall_speedup": {
                                    "shape": "256x1",
                                    "target": "nvdla_cmac_a2cacc",
                                    "cpu_to_hybrid_wall_speedup_ratio": 50.0,
                                }
                            },
                            "state_batch_and_repeated_step": {
                                "best_wall_speedup": {
                                    "shape": "1024x64",
                                    "target": "nvdla_cmac_a2cacc",
                                    "cpu_to_hybrid_wall_speedup_ratio": 100.0,
                                }
                            },
                        },
                    },
                    "vortex": {
                        "first_gate": "Vortex:mini:hello",
                        "hybrid_measurement_status": "fail_closed_first_gate_no_cpu_vs_hybrid_measurement",
                        "cpu_vs_hybrid_timing_present": False,
                        "missing_prerequisites": [
                            "cpu_vs_hybrid_timing_report.vortex",
                            "generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
                            "runtime_execution_reports_vortex_observable_authority",
                        ],
                        "bridge_quantities": {
                            "host_to_device_bytes": 37224,
                            "device_to_host_initial_bytes": 88,
                            "dcr_write_count": 9,
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_queue_prioritizes_measured_nvdla_before_unmeasured_vortex(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary_path = self._write_summary(root)

            queue = build_queue(root, summary_path=summary_path)

        self.assertEqual(queue["surface"], "rtlmeter_non_veer_hybrid_next_queue")
        self.assertEqual(queue["queue_count"], 2)
        self.assertEqual(queue["top_priority"], "nvdla_hot_ss_measurement_extension")
        self.assertEqual(queue["queue"][0]["target_family"], "NVDLA")
        self.assertEqual(queue["queue"][0]["status"], "ready_to_extend_measured_hot_ss")
        self.assertEqual(queue["queue"][0]["next_measurement"]["preferred_bucket"], "state_batch_and_repeated_step")
        self.assertEqual(queue["queue"][0]["next_measurement"]["preferred_shape"], "1024x64")
        self.assertFalse(queue["queue"][0]["claim_policy"]["speedup_claim_allowed"])
        self.assertEqual(queue["queue"][1]["target_family"], "Vortex")
        self.assertEqual(queue["queue"][1]["status"], "blocked_until_runtime_authority_and_observable_export")
        self.assertEqual(
            queue["queue"][1]["next_measurement"]["first_blocker"],
            "generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
        )
        self.assertIn(
            "generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            queue["queue"][1]["next_measurement"]["required_before_timing"],
        )
        self.assertFalse(queue["queue"][1]["claim_policy"]["speedup_claim_allowed"])
        self.assert_no_local_absolute_paths(json.dumps(queue, sort_keys=True))

    def test_cli_writes_report_from_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary_path = self._write_summary(root)
            out = root / "reports" / "queue.json"
            result = self.run_python_tool(
                "src/tools/rtlmeter_non_veer_hybrid_next_queue.py",
                "--repo-root",
                root.as_posix(),
                "--summary",
                summary_path.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_non_veer_hybrid_next_queue")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
