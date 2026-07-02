import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from hybrid_template_repeat_median import run_repeat_median, summarize_samples  # noqa: E402
from hybrid_template_types import HybridTemplatePlan  # noqa: E402


class HybridTemplateRepeatMedianTest(HybridCliTestCase):
    def _plan(self, root: Path) -> HybridTemplatePlan:
        template = root / "config" / "slice_launch_templates" / "demo.json"
        template.parent.mkdir(parents=True, exist_ok=True)
        template.write_text("{}", encoding="utf-8")
        reports = root / "reports"
        mdir = root / "artifacts" / "demo"
        reports.mkdir()
        mdir.mkdir(parents=True)
        return HybridTemplatePlan(
            template_path=template,
            target="Demo.demo",
            target_name="demo",
            top_module="tb",
            mdir=mdir,
            host_probe_target="demo_host_probe",
            source_gate=None,
            source_files=[],
            source_closure={"status": "complete"},
            verilator_defines=[],
            verilator_args=[],
            cpu_init_state=mdir / "demo_cpu_repeat_1x1.bin",
            cpu_reference_state=mdir / "demo_cpu_repeat_2x1.bin",
            gpu_candidate_state=mdir / "demo_gpu_from_cpu_init_2x1.bin",
            cpu_init_report=reports / "demo_cpu_repeat_1x1.json",
            cpu_report=reports / "demo_cpu_repeat_2x1.json",
            hybrid_report=reports / "demo_hybrid_2x1.txt",
            compare_report=reports / "demo_cpu_vs_hybrid_2x1_coverage_output_compare.json",
            nstates=2,
            steps=1,
            cfg_batch_length=64,
            cfg_reset_cycles=2,
            cfg_drain_cycles=8,
            cfg_seed=1,
        )

    def _write_sample_reports(self, plan: HybridTemplatePlan, *, cpu_ms: float, wall_ms: float, kernel_ms: float) -> None:
        plan.cpu_report.write_text(json.dumps({"elapsed_ms": cpu_ms}), encoding="utf-8")
        plan.hybrid_report.write_text(
            "\n".join(
                [
                    f"gpu_kernel_time_ms: total={kernel_ms}  per_launch={kernel_ms}",
                    "gpu_kernel_time: per_state=1.0 us",
                    f"wall_time_ms: {wall_ms}",
                ]
            ),
            encoding="utf-8",
        )
        plan.compare_report.write_text(
            json.dumps(
                {
                    "coverage_output_equivalence_passed": True,
                    "coverage_output_mismatch_count": 0,
                    "coverage_output_compared_word_count": 58,
                    "coverage_output_compared_byte_count": 232,
                }
            ),
            encoding="utf-8",
        )

    def test_run_repeat_median_collects_samples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = self._plan(Path(temp_dir))
            values = iter([(10.0, 2.0, 1.0), (12.0, 3.0, 2.0), (14.0, 4.0, 2.0)])

            def runner(current_plan: HybridTemplatePlan) -> None:
                cpu, wall, kernel = next(values)
                self._write_sample_reports(current_plan, cpu_ms=cpu, wall_ms=wall, kernel_ms=kernel)

            summary = run_repeat_median(plan, repeat_count=3, runner=runner)

        self.assertEqual(summary["status"], "measured")
        self.assertEqual(summary["repeat_count"], 3)
        self.assertTrue(summary["coverage_output_equivalence_all_passed"])
        self.assertEqual(summary["median"]["cpu_elapsed_ms"], 12.0)
        self.assertEqual(summary["median"]["hybrid_wall_ms"], 3.0)
        self.assertEqual(summary["median"]["cpu_to_hybrid_wall_speedup"], 4.0)
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_run_repeat_median_accepts_compare_schema_v2_coverage_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = self._plan(Path(temp_dir))
            plan.cpu_report.write_text(json.dumps({"elapsed_ms": 10.0}), encoding="utf-8")
            plan.hybrid_report.write_text(
                "\n".join(
                    [
                        "gpu_kernel_time_ms: total=1.0  per_launch=1.0",
                        "gpu_kernel_time: per_state=1.0 us",
                        "wall_time_ms: 2.0",
                    ]
                ),
                encoding="utf-8",
            )
            plan.compare_report.write_text(
                json.dumps(
                    {
                        "match": False,
                        "mismatch_count": 10,
                        "coverage_output_policy": {
                            "passed": True,
                            "mismatch_count": 0,
                            "compared_word_count": 58,
                            "compared_byte_count": 232,
                        },
                        "selected_acceptance_policy": {
                            "name": "coverage_output_equivalence",
                            "passed": True,
                        },
                    }
                ),
                encoding="utf-8",
            )

            summary = run_repeat_median(plan, repeat_count=1, runner=lambda current_plan: None)

        self.assertTrue(summary["coverage_output_equivalence_all_passed"])
        coverage = summary["samples"][0]["coverage_output"]
        self.assertFalse(coverage["match"])
        self.assertEqual(coverage["mismatch_count"], 10)
        self.assertTrue(coverage["coverage_output_equivalence_passed"])
        self.assertEqual(coverage["coverage_output_mismatch_count"], 0)
        self.assertEqual(coverage["selected_acceptance_policy"], "coverage_output_equivalence")
        self.assertTrue(coverage["selected_acceptance_passed"])

    def test_summarize_samples_handles_empty_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = self._plan(Path(temp_dir))
            summary = summarize_samples(plan, [])

        self.assertEqual(summary["status"], "no_samples")
        self.assertFalse(summary["coverage_output_equivalence_all_passed"])


if __name__ == "__main__":
    unittest.main()
