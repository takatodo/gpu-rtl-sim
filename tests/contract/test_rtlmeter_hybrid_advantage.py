import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_hybrid_advantage import aggregate_reports  # noqa: E402


class RtlmeterHybridAdvantageTest(HybridCliTestCase):
    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _cpu_parallel_report(self, path: Path) -> None:
        self._write_json(
            path,
            {
                "status": "passed",
                "summary": {
                    "case_count": 16,
                    "parallel_wall_s": 2.218887,
                    "serial_sum_case_wall_s": 14.409478,
                    "parallel_speedup_vs_serial_sum": 6.494012,
                    "parallel_efficiency": 0.405876,
                    "all_runs_passed": True,
                    "all_observables_match": True,
                },
            },
        )

    def _gpu_timing_report(self, path: Path, *, nstates: int, wall_s: float, ratio: float) -> None:
        self._write_json(
            path,
            {
                "case": "VeeR-EL2:default:hello",
                "status": "passed",
                "speedup_claimed": False,
                "cpu_as_gpu_fallback": False,
                "methodology": {"sidecar_nstates_override": nstates},
                "summary": {
                    "sidecar_wall_s_median": wall_s,
                    "gpu_kernel_ms_total_median": 262.026245,
                    "sidecar_vs_cpu_parallel_ratio": ratio,
                },
            },
        )

    def _launch_blocked_report(self, path: Path) -> None:
        self._write_json(
            path,
            {
                "status": "blocked_launch_count_feasibility",
                "speedup_claimed": False,
                "launch_count_feasibility": {
                    "status": "blocked_pair_cycle_launch_count",
                    "estimated_actual_timed_launches": 5_276_412,
                    "threshold": 100_000,
                },
            },
        )

    def _bounded_progress_report(self, path: Path) -> None:
        self._write_json(
            path,
            {
                "status": "passed",
                "bounded_progress_evidence": True,
                "gpu_execution_claimed": True,
                "timing_measured": False,
                "speedup_claimed": False,
                "report_count": 3,
                "passed_report_count": 3,
            },
        )

    def test_aggregates_advantage_and_disadvantage_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpu = root / "reports" / "cpu.json"
            timing16 = root / "reports" / "timing16.json"
            timing32 = root / "reports" / "timing32.json"
            blocked = root / "reports" / "blocked.json"
            bounded = root / "reports" / "bounded.json"
            self._cpu_parallel_report(cpu)
            self._gpu_timing_report(timing16, nstates=16, wall_s=0.641226, ratio=3.460382)
            self._gpu_timing_report(timing32, nstates=32, wall_s=0.950341, ratio=4.468648)
            self._launch_blocked_report(blocked)
            self._bounded_progress_report(bounded)

            aggregate = aggregate_reports([cpu, timing16, timing32, blocked, bounded], repo_root=root)

        self.assertEqual(aggregate["status"], "analyzed")
        self.assertEqual(aggregate["counts"]["cpu_parallel_favorable"], 1)
        self.assertEqual(aggregate["counts"]["gpu_sidecar_unfavorable"], 2)
        self.assertEqual(aggregate["counts"]["gpu_sidecar_favorable"], 0)
        self.assertEqual(aggregate["counts"]["launch_feasibility_blocked"], 1)
        self.assertEqual(aggregate["counts"]["gpu_bounded_progress"], 1)
        self.assertEqual(
            aggregate["hybrid_recommendation"]["recommended_action"],
            "prefer_cpu_parallel_control_with_gpu_bounded_batch_probes",
        )
        self.assertEqual(aggregate["best_gpu_total_wall"]["source"], "reports/timing16.json")
        self.assertEqual(aggregate["best_gpu_per_state_wall"]["source"], "reports/timing32.json")
        self.assertEqual(aggregate["best_cpu_parallel_speedup"]["source"], "reports/cpu.json")
        self.assert_no_local_absolute_paths(json.dumps(aggregate, sort_keys=True))

    def test_cli_writes_same_aggregate_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpu = root / "reports" / "cpu.json"
            timing = root / "reports" / "timing.json"
            out = root / "reports" / "advantage.json"
            self._cpu_parallel_report(cpu)
            self._gpu_timing_report(timing, nstates=16, wall_s=0.641226, ratio=3.460382)

            result = self.run_python_tool(
                "src/tools/rtlmeter_hybrid_advantage.py",
                "--report",
                cpu.as_posix(),
                "--report",
                timing.as_posix(),
                "--repo-root",
                root.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["counts"]["gpu_sidecar_unfavorable"], 1)
        self.assert_no_local_absolute_paths(result.stdout)
        self.assert_no_local_absolute_paths(json.dumps(report_payload, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
