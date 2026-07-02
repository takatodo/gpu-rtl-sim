import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_non_veer_usefulness_candidates import build_summary  # noqa: E402


class RtlmeterNonVeerUsefulnessCandidatesTest(HybridCliTestCase):
    def _write_descriptor(self, root: Path, design: str, *, top: str, tests: list[str]) -> None:
        path = root / "third_party" / "rtlmeter" / "designs" / design / "descriptor.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        test_lines = "\n".join(f"    {name}: {{}}" for name in tests)
        path.write_text(
            "\n".join(
                [
                    "compile:",
                    "  verilogSourceFiles:",
                    "    - src/top.sv",
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
                    "measured_shape": {
                        "name": "minimum_1x1",
                        "nstates": 1,
                        "steps": 1,
                        "coverage_output_equivalence_passed": True,
                        "coverage_output_mismatch_count": 0,
                        "cpu_elapsed_ms": 4.0,
                        "hybrid_wall_time_ms": 1.0,
                        "hybrid_gpu_kernel_time_ms_total": 0.5,
                    },
                }
            ),
            encoding="utf-8",
        )

    def test_summary_prioritizes_measured_nvdla_over_descriptor_only_vortex(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_descriptor(root, "NVDLA", top="tb_top", tests=["sanity"])
            self._write_descriptor(root, "Vortex", top="tb", tests=["hello", "sgemm", "saxpy"])
            self._write_nvdla_gate(root)

            summary = build_summary(root)

        self.assertEqual(summary["status"], "analyzed")
        self.assertEqual(summary["nvdla"]["evidence"]["gpu_favorable_shape_count"], 1)
        self.assertEqual(summary["nvdla"]["evidence"]["best_wall_speedup"]["cpu_to_hybrid_wall_speedup_ratio"], 4.0)
        self.assertEqual(summary["vortex"]["status"], "descriptor_only_no_cpu_vs_hybrid_measurement")
        self.assertEqual(summary["vortex"]["first_gate_readiness"]["first_measurement_candidate"]["case"], "Vortex:mini:hello")
        self.assertIn(
            "slice_launch_template.vortex_mini_hello",
            summary["vortex"]["first_gate_readiness"]["missing_prerequisites"],
        )
        self.assertEqual(
            summary["recommendation"]["recommended_next"],
            "refresh_or_extend_nvdla_cmac_core_mac_repeat_median_before_vortex",
        )
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            out = root / "reports" / "non_veer.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            self._write_descriptor(root, "NVDLA", top="tb_top", tests=["sanity"])
            self._write_descriptor(root, "Vortex", top="tb", tests=["hello"])
            self._write_nvdla_gate(root)

            result = self.run_python_tool(
                "src/tools/rtlmeter_non_veer_usefulness_candidates.py",
                "--repo-root",
                root.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_non_veer_usefulness_candidates")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
