import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVsimMainVortexRealCudaMaterializedRuntimeSmokeTest(HybridCliTestCase):
    def _write_executable(self, path: Path, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        path.chmod(path.stat().st_mode | 0o111)

    def test_passes_when_vsim_reaches_proxy_handoff_from_obj_dir_cwd(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke import run_smoke

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vsim = root / "artifacts" / "case" / "obj_dir" / "Vsim"
            marker = root / "artifacts" / "case" / "obj_dir" / "cwd_marker"
            self._write_executable(
                vsim,
                "\n".join(
                    [
                        "test -f cwd_marker || exit 21",
                        'exec "$RTLMETER_VSIM_SIDECAR_PROXY"',
                    ]
                ),
            )
            marker.write_text("ok\n", encoding="utf-8")

            report = run_smoke(root, vsim=vsim, proxy="/bin/true", timeout_seconds=5)

        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["returncode"], 0)
        self.assertTrue(report["materialized_runtime_args_probe_passed"])
        self.assertTrue(report["proxy_handoff_reached"])
        self.assertEqual(report["materialized_runtime_args_probe_status"], None)
        self.assertFalse(report["runtime_authority"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_extracts_materialized_probe_status_from_stderr(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke import run_smoke

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vsim = root / "artifacts" / "case" / "obj_dir" / "Vsim"
            self._write_executable(
                vsim,
                "echo rtlmeter_vortex_materialized_runtime_args_probe_status=21 >&2\nexit 123\n",
            )

            report = run_smoke(root, vsim=vsim, proxy="/bin/true", timeout_seconds=5)

        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["returncode"], 123)
        self.assertFalse(report["materialized_runtime_args_probe_passed"])
        self.assertFalse(report["proxy_handoff_reached"])
        self.assertEqual(report["materialized_runtime_args_probe_status"], 21)
        self.assertIn("rtlmeter_vortex_materialized_runtime_args_probe_status=21", report["stderr"])

    def test_extracts_runtime_sequence_failure_stage(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke import run_smoke

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vsim = root / "artifacts" / "case" / "obj_dir" / "Vsim"
            self._write_executable(
                vsim,
                "echo rtlmeter_vortex_root_storage_kernel_stage stage=before_cuModuleLoad >&2\n"
                "echo rtlmeter_vortex_root_storage_kernel_stage stage=after_cuModuleLoad >&2\n"
                "echo rtlmeter_vortex_root_storage_relocation_count count=42 >&2\n"
                "echo rtlmeter_vortex_root_storage_kernel_failed stage=cuModuleLoad result=218 >&2\n"
                "echo rtlmeter_vortex_runtime_sequence_failed stage=kernel_launch result=218 index=-1 >&2\n"
                "echo rtlmeter_vortex_materialized_runtime_args_probe_status=30 >&2\n"
                "exit 123\n",
            )

            report = run_smoke(root, vsim=vsim, proxy="/bin/true", timeout_seconds=5)

        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["runtime_sequence_failed_stage"], "kernel_launch")
        self.assertEqual(report["runtime_sequence_failed_result"], 218)
        self.assertEqual(
            report["runtime_sequence_failure"],
            {"stage": "kernel_launch", "result": 218, "index": -1},
        )
        self.assertEqual(report["root_storage_kernel_failed_stage"], "cuModuleLoad")
        self.assertEqual(report["root_storage_kernel_failed_result"], 218)
        self.assertEqual(
            report["root_storage_kernel_stage_trace"],
            ["before_cuModuleLoad", "after_cuModuleLoad"],
        )
        self.assertEqual(report["root_storage_kernel_last_stage"], "after_cuModuleLoad")
        self.assertEqual(report["root_storage_relocation_count"], 42)

    def test_extracts_runtime_authority_diagnostic_on_pass(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke import run_smoke

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vsim = root / "artifacts" / "case" / "obj_dir" / "Vsim"
            self._write_executable(
                vsim,
                "echo rtlmeter_vortex_root_storage_kernel_stage stage=after_cuCtxSynchronize >&2\n"
                "echo rtlmeter_vortex_runtime_authority authority_report_ready=1 authority_passed=1 "
                "authority_source=memory_post_condition memory_post_condition_passed=1 "
                "stdout_test_passed_observed=0 observable_export_invoked=1 kernel_launch_invoked=1 "
                "dcr_applied_count=9 >&2\n"
                'exec "$RTLMETER_VSIM_SIDECAR_PROXY"\n',
            )

            report = run_smoke(root, vsim=vsim, proxy="/bin/true", timeout_seconds=5)

        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["runtime_authority"])
        self.assertEqual(report["authority_report_ready"], 1)
        self.assertEqual(report["authority_passed"], 1)
        self.assertEqual(report["authority_source"], "memory_post_condition")
        self.assertEqual(report["memory_post_condition_passed"], 1)
        self.assertEqual(report["stdout_test_passed_observed"], 0)
        self.assertEqual(report["observable_export_invoked"], 1)
        self.assertEqual(report["kernel_launch_invoked"], 1)
        self.assertEqual(report["dcr_applied_count"], 9)

    def test_extracts_last_stage_from_timed_out_smoke(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke import run_smoke

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vsim = root / "artifacts" / "case" / "obj_dir" / "Vsim"
            self._write_executable(
                vsim,
                "echo rtlmeter_vortex_root_storage_kernel_stage stage=before_cuModuleLoad >&2\n"
                "sleep 2\n",
            )

            report = run_smoke(root, vsim=vsim, proxy="/bin/true", timeout_seconds=0.2)

        self.assertEqual(report["status"], "failed")
        self.assertTrue(report["timed_out"])
        self.assertEqual(report["root_storage_kernel_stage_trace"], ["before_cuModuleLoad"])
        self.assertEqual(report["root_storage_kernel_last_stage"], "before_cuModuleLoad")

    def test_passes_module_path_to_vsim_env(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke import run_smoke

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vsim = root / "artifacts" / "case" / "obj_dir" / "Vsim"
            module = root / "artifacts" / "slice" / "vl_eval_batch_gpu.cubin"
            module.parent.mkdir(parents=True)
            module.write_bytes(b"cubin")
            self._write_executable(
                vsim,
                'test "$RTLMETER_VORTEX_VL_BATCH_GPU_MODULE" = "' + module.as_posix() + '" || exit 44\n'
                'exec "$RTLMETER_VSIM_SIDECAR_PROXY"\n',
            )

            report = run_smoke(root, vsim=vsim, proxy="/bin/true", module=module, timeout_seconds=5)

        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["module"], "artifacts/slice/vl_eval_batch_gpu.cubin")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vsim = root / "artifacts" / "case" / "obj_dir" / "Vsim"
            self._write_executable(vsim, 'exec "$RTLMETER_VSIM_SIDECAR_PROXY"\n')
            out = root / "reports" / "smoke.json"

            result = self.run_python_tool(
                "src/tools/rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke.py",
                "--repo-root",
                root.as_posix(),
                "--vsim",
                vsim.as_posix(),
                "--proxy",
                "/bin/true",
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke")
        self.assert_no_local_absolute_paths(result.stdout)

    def test_cli_returns_nonzero_on_failed_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vsim = root / "artifacts" / "case" / "obj_dir" / "Vsim"
            self._write_executable(vsim, "echo rtlmeter_vortex_materialized_runtime_args_probe_status=7001 >&2\nexit 123\n")
            result = self.run_python_tool(
                "src/tools/rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke.py",
                "--repo-root",
                root.as_posix(),
                "--vsim",
                vsim.as_posix(),
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["materialized_runtime_args_probe_status"], 7001)


if __name__ == "__main__":
    import unittest

    unittest.main()
