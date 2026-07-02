import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVortexTimingTest(HybridCliTestCase):
    def _write_executable(self, path: Path, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        path.chmod(path.stat().st_mode | 0o111)

    def _write_cpu_reference(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "status": "cpu_reference_passed",
                    "cpu_reference_ready_for_hybrid_compare": True,
                    "metrics": {
                        "execute_elapsed_s": 0.25,
                        "execute_clocks": 40897,
                    },
                }
            ),
            encoding="utf-8",
        )

    def test_builds_cpu_vs_hybrid_timing_report_from_authority_smoke(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_timing import build_timing_report

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpu = root / "reports" / "cpu.json"
            vsim = root / "artifacts" / "case" / "obj_dir" / "Vsim"
            module = root / "artifacts" / "kernel" / "vl_eval_batch_gpu.cubin"
            module.parent.mkdir(parents=True)
            module.write_bytes(b"cubin")
            self._write_cpu_reference(cpu)
            self._write_executable(
                vsim,
                "echo rtlmeter_vortex_root_storage_kernel_stage stage=after_cuCtxSynchronize >&2\n"
                "echo rtlmeter_vortex_root_storage_relocation_count count=65 >&2\n"
                "echo rtlmeter_vortex_runtime_authority authority_report_ready=1 authority_passed=1 "
                "authority_source=memory_post_condition memory_post_condition_passed=1 "
                "stdout_test_passed_observed=0 observable_export_invoked=1 kernel_launch_invoked=1 "
                "dcr_applied_count=9 >&2\n"
                'exec "$RTLMETER_VSIM_SIDECAR_PROXY"\n',
            )

            report = build_timing_report(
                root,
                cpu_reference_report=cpu,
                vsim=vsim,
                module=module,
                repeats=2,
                timeout_seconds=5,
            )

        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["timing_measured"])
        self.assertTrue(report["correctness_passed"])
        self.assertTrue(report["runtime_authority"])
        self.assertEqual(report["repeats"], 2)
        self.assertEqual(report["cpu_elapsed_s"], 0.25)
        self.assertIsInstance(report["hybrid_wall_s_median"], float)
        self.assertIsInstance(report["hybrid_vs_cpu_ratio"], float)
        self.assertEqual(report["authority_source"], "memory_post_condition")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpu = root / "reports" / "cpu.json"
            vsim = root / "artifacts" / "case" / "obj_dir" / "Vsim"
            module = root / "artifacts" / "kernel" / "vl_eval_batch_gpu.cubin"
            module.parent.mkdir(parents=True)
            module.write_bytes(b"cubin")
            self._write_cpu_reference(cpu)
            self._write_executable(
                vsim,
                "echo rtlmeter_vortex_runtime_authority authority_report_ready=1 authority_passed=1 "
                "authority_source=memory_post_condition memory_post_condition_passed=1 "
                "stdout_test_passed_observed=0 observable_export_invoked=1 kernel_launch_invoked=1 "
                "dcr_applied_count=9 >&2\n"
                'exec "$RTLMETER_VSIM_SIDECAR_PROXY"\n',
            )
            out = root / "reports" / "timing.json"

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_timing.py",
                "--repo-root",
                root.as_posix(),
                "--cpu-reference-report",
                cpu.as_posix(),
                "--vsim",
                vsim.as_posix(),
                "--module",
                module.as_posix(),
                "--repeats",
                "1",
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_timing")
        self.assertEqual(report_payload["status"], "passed")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
