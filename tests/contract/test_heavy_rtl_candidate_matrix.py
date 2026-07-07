import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import heavy_rtl_candidate_matrix as matrix  # noqa: E402


class HeavyRtlCandidateMatrixTest(HybridCliTestCase):
    def _write_template(self, root: Path, name: str, *, first_pass: bool = False, profile: bool = False) -> str:
        path = root / "config" / "slice_launch_templates" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "target": f"Demo.{name}",
            "status": "active",
            "source_files": ["rtl.sv"],
            "source_closure": {"status": "complete"},
            "runner_args_template": {
                "top_module": f"{name}_tb",
                "rtl_path": f"third_party/demo/{name}.sv",
                "coverage_tb_path": f"overlays/demo/{name}_tb.sv",
                "coverage_manifest_path": f"overlays/demo/{name}.json",
            },
            "static_features": {"region_count": 3, "required_output_count": 8},
        }
        if first_pass:
            payload["first_pass_result"] = {"status": "passed", "mismatch_count": 0}
        if profile:
            payload["execution_profiles"] = {
                "multi_step": {
                    "status": "frozen",
                    "scenario": "multi_step_medium",
                    "nstates": 32,
                    "sequential_steps": 56,
                    "median_cpu_ms_per_rep": 10.0,
                    "median_gpu_ms_per_rep": 2.0,
                    "compact_match": True,
                }
            }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path.relative_to(root).as_posix()

    def _write_measurement(self, root: Path, name: str) -> tuple[str, str, str]:
        reports = root / "reports"
        reports.mkdir(exist_ok=True)
        cpu = reports / f"{name}_cpu.json"
        hybrid = reports / f"{name}_hybrid.txt"
        compare = reports / f"{name}_compare.json"
        cpu.write_text(json.dumps({"elapsed_ms": 12.0}), encoding="utf-8")
        hybrid.write_text(
            "\n".join(
                [
                    "gpu_kernel_time_ms: total=1.0  per_launch=1.0",
                    "gpu_kernel_time: per_state=1.0 us",
                    "wall_time_ms: 3.0",
                ]
            ),
            encoding="utf-8",
        )
        compare.write_text(
            json.dumps(
                {
                    "coverage_output_policy": {
                        "passed": True,
                        "mismatch_count": 0,
                        "compared_word_count": 16,
                        "compared_byte_count": 64,
                    }
                }
            ),
            encoding="utf-8",
        )
        return cpu.relative_to(root).as_posix(), hybrid.relative_to(root).as_posix(), compare.relative_to(root).as_posix()

    def test_build_matrix_classifies_promote_measure_and_template_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pulp_template = self._write_template(root, "pulp_demo")
            cpu, hybrid, compare = self._write_measurement(root, "pulp_demo")
            tlul_template = self._write_template(root, "tlul_demo", first_pass=True)
            fifo_template = self._write_template(root, "fifo_demo", profile=True)
            candidates = [
                {
                    "name": "pulp_demo",
                    "family": "PULP_ITA",
                    "class": "attention_mha",
                    "template": pulp_template,
                    "source_parallel_shape": "64x1",
                    "single_state_shape": "1x64",
                    "cpu_report": cpu,
                    "hybrid_report": hybrid,
                    "compare_report": compare,
                    "next_measure_command": "measure pulp",
                },
                {
                    "name": "tlul_demo",
                    "family": "OpenTitan_TLUL",
                    "class": "fanout_socket",
                    "template": tlul_template,
                    "source_parallel_shape": "32x1",
                    "single_state_shape": "1x56",
                    "next_measure_command": "measure tlul",
                },
                {
                    "name": "fifo_demo",
                    "family": "OpenTitan_TLUL",
                    "class": "protocol_fifo",
                    "template": fifo_template,
                    "source_parallel_shape": "32x1",
                    "single_state_shape": "1x56",
                    "next_measure_command": "measure fifo",
                },
                {
                    "name": "noc_demo",
                    "family": "BlackParrot_BaseJump_NoC",
                    "class": "wormhole_router",
                    "source": "third_party/demo/noc.sv",
                    "source_parallel_shape": "packet_batch",
                    "single_state_shape": "single_packet_stream",
                    "next_measure_command": "create template",
                },
            ]
            with mock.patch.object(matrix, "REPO_ROOT", root):
                report = matrix.build_matrix(candidates)

        by_name = {row["name"]: row for row in report["rows"]}
        self.assertEqual(report["status"], "heavy_rtl_candidate_matrix_ready")
        self.assertEqual(by_name["pulp_demo"]["policy"]["decision"], "promote_state_parallel_measurement")
        self.assertEqual(by_name["tlul_demo"]["policy"]["decision"], "measure_repeat_median_next")
        self.assertEqual(by_name["fifo_demo"]["policy"]["decision"], "resident_or_shape_sweep_required")
        self.assertEqual(by_name["noc_demo"]["policy"]["decision"], "template_required_before_measurement")
        for row in report["rows"]:
            self.assertIn("source_closure", row)
            self.assertIsInstance(row["source_closure"].get("status"), str)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_default_candidate_matrix_schema_and_counts(self) -> None:
        report = matrix.build_matrix()
        by_name = {row["name"]: row for row in report["rows"]}

        self.assertEqual(report["row_count"], 6)
        self.assertEqual(report["pulp_row_count"], 2)
        self.assertEqual(report["noc_tlul_row_count"], 4)
        self.assertEqual(
            report["policy_counts"],
            {
                "promote_state_parallel_measurement": 5,
                "resident_or_shape_sweep_required": 1,
            },
        )
        self.assertEqual(
            by_name["pulp_paged_attention_kv_score"]["policy"]["decision"],
            "promote_state_parallel_measurement",
        )
        self.assertEqual(by_name["tlul_socket_1n"]["policy"]["decision"], "promote_state_parallel_measurement")
        self.assertEqual(by_name["tlul_socket_m1"]["policy"]["decision"], "promote_state_parallel_measurement")
        self.assertEqual(by_name["blackparrot_bsg_wormhole_router"]["family"], "BlackParrot_BaseJump_NoC")
        self.assertEqual(by_name["blackparrot_bsg_wormhole_router"]["source_parallel_shape"], "packet_batch")
        self.assertEqual(
            by_name["blackparrot_bsg_wormhole_router"]["single_state_repeated_step_shape"],
            "single_packet_stream",
        )
        blackparrot_plan = by_name["blackparrot_bsg_wormhole_router"]["source_closure_plan"]
        self.assertEqual(
            blackparrot_plan["status"],
            "source_backed_shape_sweep_promote_256x1_resident_template_surface_defined_patch_script_next",
        )
        self.assertEqual(
            blackparrot_plan["coverage_overlay"],
            "overlays/rtlmeter/designs/BlackParrot/src/bsg_wormhole_router_gpu_cov_tb.sv",
        )
        self.assertEqual(
            blackparrot_plan["resident_multistep_definition_gate"],
            "config/scaling_gates/blackparrot_bsg_wormhole_router_resident_multistep_definition.json",
        )
        blackparrot_timing = by_name["blackparrot_bsg_wormhole_router"]["timing_evidence"]
        self.assertEqual(
            blackparrot_timing["repeat_report"],
            "reports/blackparrot_bsg_wormhole_router_256x1_median.json",
        )
        self.assertEqual(blackparrot_timing["shape"], "256x1")
        self.assertEqual(blackparrot_timing["repeat_count"], 3)
        self.assertEqual(blackparrot_timing["cpu_to_hybrid_wall_speedup"], 651.817697228145)
        blackparrot_shape_sweep = by_name["blackparrot_bsg_wormhole_router"]["shape_sweep_evidence"]
        self.assertEqual(
            [item["shape"] for item in blackparrot_shape_sweep],
            ["32x1", "64x1", "128x1", "256x1"],
        )
        self.assertEqual(
            [item["cpu_to_hybrid_wall_speedup"] for item in blackparrot_shape_sweep],
            [32.76216804527645, 158.28447339847992, 259.4919886899152, 651.817697228145],
        )
        self.assertTrue(all(item["coverage_output_equivalence_all_passed"] for item in blackparrot_shape_sweep))
        self.assertTrue(
            by_name["blackparrot_bsg_wormhole_router"]["compare_evidence"][
                "coverage_output_equivalence_passed"
            ]
        )
        self.assertEqual(
            by_name["blackparrot_bsg_wormhole_router"]["policy"]["decision"],
            "promote_state_parallel_measurement",
        )
        for row in report["rows"]:
            self.assertIn("source_closure", row)
            self.assertIsInstance(row["source_closure"].get("status"), str)
            self.assertEqual(row["source_closure_status"], row["source_closure"]["status"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_selection_summary_matches_default_matrix(self) -> None:
        report = matrix.build_matrix()
        selection = json.loads((matrix.REPO_ROOT / "config" / "selection.json").read_text(encoding="utf-8"))
        summary = selection["heavy_rtl_candidate_matrix"]
        report_by_name = {row["name"]: row for row in report["rows"]}
        summary_by_name = {row["name"]: row for row in summary["rows"]}

        self.assertEqual(summary["row_count"], report["row_count"])
        self.assertEqual(summary["pulp_row_count"], report["pulp_row_count"])
        self.assertEqual(summary["noc_tlul_row_count"], report["noc_tlul_row_count"])
        self.assertEqual(summary["policy_counts"], report["policy_counts"])
        for name, report_row in report_by_name.items():
            self.assertIn(name, summary_by_name)
            summary_row = summary_by_name[name]
            self.assertEqual(summary_row["family"], report_row["family"])
            self.assertEqual(summary_row["source_parallel_shape"], report_row["source_parallel_shape"])
            self.assertEqual(
                summary_row["single_state_repeated_step_shape"],
                report_row["single_state_repeated_step_shape"],
            )
            self.assertEqual(summary_row["source_closure_status"], report_row["source_closure_status"])
            self.assertEqual(summary_row["policy"], report_row["policy"]["decision"])

    def test_cli_writes_report(self) -> None:
        report = matrix.build_matrix(
            [
                {
                    "name": "noc_demo",
                    "family": "BlackParrot_BaseJump_NoC",
                    "class": "wormhole_router",
                    "source": "third_party/demo/noc.sv",
                    "source_parallel_shape": "packet_batch",
                    "single_state_shape": "single_packet_stream",
                    "next_measure_command": "create template",
                }
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(matrix, "build_matrix", return_value=report):
            out = Path(temp_dir) / "matrix.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                rc = matrix.main(["--write-report", "--report-out", out.as_posix()])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertEqual(payload["status"], "heavy_rtl_candidate_matrix_ready")
        self.assert_no_local_absolute_paths(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
