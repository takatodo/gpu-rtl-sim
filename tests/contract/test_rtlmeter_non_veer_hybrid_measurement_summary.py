import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_non_veer_hybrid_measurement_summary import build_measurement_summary  # noqa: E402


class RtlmeterNonVeerHybridMeasurementSummaryTest(HybridCliTestCase):
    def _write_descriptor(
        self,
        root: Path,
        design: str,
        *,
        top: str,
        tests: list[str],
        cpp_sources: list[str] | None = None,
    ) -> None:
        path = root / "third_party" / "rtlmeter" / "designs" / design / "descriptor.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        test_lines = "\n".join(f"    {name}: {{}}" for name in tests)
        cpp_lines = "\n".join(f"    - {source}" for source in (cpp_sources or []))
        cpp_block = ["  cppSourceFiles:"] + ([cpp_lines] if cpp_lines else [])
        path.write_text(
            "\n".join(
                [
                    "compile:",
                    "  verilogSourceFiles:",
                    "    - src/top.sv",
                    *cpp_block,
                    f"  topModule: {top}",
                    "  mainClock: tb.clk",
                    "execute:",
                    "  tests:",
                    test_lines,
                    "configurations:",
                    "  mini:",
                    "    execute:",
                    "      tests:",
                    "        hello: {}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_nvdla_gate(self, root: Path) -> None:
        path = root / "records" / "scaling_gates" / "nvdla_cmac_core_mac_minimal_build_run_compare_gate.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "target_full_name": "NVDLA.nvdla_cmac_core_mac",
                    "measured_shapes": [
                        {
                            "name": "minimum_1x1",
                            "nstates": 1,
                            "steps": 1,
                            "coverage_output_equivalence_passed": True,
                            "coverage_output_mismatch_count": 0,
                            "cpu_elapsed_ms": 4.0,
                            "hybrid_wall_time_ms": 1.0,
                            "hybrid_gpu_kernel_time_ms_total": 0.5,
                        },
                        {
                            "name": "batch_8x4",
                            "nstates": 8,
                            "steps": 4,
                            "coverage_output_equivalence_passed": True,
                            "coverage_output_mismatch_count": 0,
                            "cpu_elapsed_ms": 40.0,
                            "hybrid_wall_time_ms": 2.0,
                            "hybrid_gpu_kernel_time_ms_total": 1.0,
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_summary_quantifies_measured_nvdla_and_unmeasured_vortex(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_descriptor(root, "NVDLA", top="tb_top", tests=["sanity"])
            self._write_descriptor(root, "Vortex", top="tb", tests=["hello", "sgemm", "saxpy"], cpp_sources=["src/dpi/memory.cpp"])
            self._write_nvdla_gate(root)

            summary = build_measurement_summary(root)

        self.assertEqual(summary["surface"], "rtlmeter_non_veer_hybrid_measurement_summary")
        self.assertEqual(summary["counts"]["measured_design_count"], 1)
        self.assertEqual(summary["counts"]["measured_shape_count"], 2)
        self.assertEqual(summary["counts"]["gpu_favorable_shape_count"], 2)
        self.assertEqual(summary["nvdla"]["favorable_ratio"], 1.0)
        self.assertEqual(summary["nvdla"]["shape_buckets"]["single_state_single_step"]["best_wall_speedup"]["cpu_to_hybrid_wall_speedup_ratio"], 4.0)
        self.assertEqual(summary["nvdla"]["shape_buckets"]["state_batch_and_repeated_step"]["best_wall_speedup"]["cpu_to_hybrid_wall_speedup_ratio"], 20.0)
        self.assertEqual(summary["vortex"]["hybrid_measurement_status"], "descriptor_only_no_cpu_vs_hybrid_measurement")
        self.assertFalse(summary["vortex"]["cpu_vs_hybrid_timing_present"])
        self.assertIn("generated_lowered_tb_invocation_missing", summary["vortex"]["observed_blocking_features"])
        self.assertEqual(
            summary["hybrid_recommendation"]["recommended_next"],
            "extend_nvdla_hot_ss_measurement_before_claiming_broader_rtlmeter_gpu_usefulness",
        )
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            out = root / "reports" / "non_veer_hybrid_measurement.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            self._write_descriptor(root, "NVDLA", top="tb_top", tests=["sanity"])
            self._write_descriptor(root, "Vortex", top="tb", tests=["hello"], cpp_sources=["src/dpi/memory.cpp"])
            self._write_nvdla_gate(root)

            result = self.run_python_tool(
                "src/tools/rtlmeter_non_veer_hybrid_measurement_summary.py",
                "--repo-root",
                root.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_non_veer_hybrid_measurement_summary")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
