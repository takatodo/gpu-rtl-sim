import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVortexKernelCallbackPreflightTest(HybridCliTestCase):
    def test_missing_artifact_does_not_claim_runtime_authority(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_kernel_callback_preflight import build_preflight

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = build_preflight(root, obj_dir=Path("artifacts/obj_dir"))

        self.assertEqual(report["status"], "missing_kernel_artifact_or_metadata")
        self.assertFalse(report["artifact_ready"])
        self.assertFalse(report["runtime_authority"])
        self.assertFalse(report["timing_measured"])
        self.assertIn("vl_batch_gpu.meta.json", report["missing_prerequisites"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_prelaunch_rejection_blocks_callback_wiring(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_kernel_callback_preflight import build_preflight

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            obj = root / "artifacts" / "obj_dir"
            obj.mkdir(parents=True)
            (obj / "vl_batch_gpu.ptx").write_text("// ptx", encoding="utf-8")
            (obj / "vl_batch_gpu.meta.json").write_text(
                json.dumps(
                    {
                        "cubin": "vl_batch_gpu.ptx",
                        "cuda_module_format": "ptx",
                        "kernel": "vl_eval_batch_gpu",
                        "storage_size": 71488,
                        "hierarchy_state": {
                            "root_storage_size": 71488,
                            "syms_storage_size": 80768,
                            "unsafe_syms_gep_count": 3358,
                            "prelaunch_rejection_required": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            (obj / "Vsim__main.cpp").write_text(
                "static VortexCuResult rtlmeter_vortex_real_cuda_noop_kernel(void*, VortexRuntimeBuffer*, unsigned) { return 0; }\n"
                "vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);\n",
                encoding="utf-8",
            )

            report = build_preflight(root, obj_dir=Path("artifacts/obj_dir"))

        self.assertEqual(report["status"], "blocked_by_gpu_artifact_prelaunch_rejection")
        self.assertTrue(report["artifact_ready"])
        self.assertEqual(report["artifact"], "artifacts/obj_dir/vl_batch_gpu.ptx")
        self.assertEqual(report["kernel_name"], "vl_eval_batch_gpu")
        self.assertEqual(report["storage_size"], 71488)
        self.assertTrue(report["prelaunch_rejection_required"])
        self.assertEqual(report["unsafe_syms_gep_count"], 3358)
        self.assertTrue(report["noop_callback_observed"])
        self.assertTrue(report["materialized_runtime_call_observed"])
        self.assertFalse(report["callback_wiring_ready"])
        self.assertIn("safe_root_or_syms_storage_launch_abi", report["missing_prerequisites"])
        self.assertEqual(
            report["next_required_boundary"],
            "clear_vortex_gpu_artifact_prelaunch_rejection_or_build_root_syms_storage_launch_abi",
        )

    def test_safe_artifact_still_requires_root_storage_launch_callback(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_kernel_callback_preflight import build_preflight

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            obj = root / "artifacts" / "obj_dir"
            obj.mkdir(parents=True)
            (obj / "vl_batch_gpu.cubin").write_bytes(b"cubin")
            (obj / "vl_batch_gpu.meta.json").write_text(
                json.dumps(
                    {
                        "cubin": "vl_batch_gpu.cubin",
                        "kernel": "vl_eval_batch_gpu",
                        "storage_size": 128,
                        "hierarchy_state": {
                            "root_storage_size": 128,
                            "syms_storage_size": 128,
                            "unsafe_syms_gep_count": 0,
                            "prelaunch_rejection_required": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            (obj / "Vsim__main.cpp").write_text(
                "static VortexCuResult rtlmeter_vortex_real_cuda_noop_kernel(void*, VortexRuntimeBuffer*, unsigned) { return 0; }\n"
                "vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);\n",
                encoding="utf-8",
            )

            report = build_preflight(root, obj_dir=Path("artifacts/obj_dir"))

        self.assertEqual(report["status"], "blocked_by_missing_root_storage_launch_callback")
        self.assertTrue(report["artifact_ready"])
        self.assertFalse(report["prelaunch_rejection_required"])
        self.assertFalse(report["root_storage_launch_abi_observed"])
        self.assertIn("root_storage_backed_kernel_launch_callback", report["missing_prerequisites"])

    def test_root_storage_callback_wiring_is_ready_for_smoke_not_authority(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_kernel_callback_preflight import build_preflight

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            obj = root / "artifacts" / "obj_dir"
            obj.mkdir(parents=True)
            (obj / "vl_batch_gpu.ptx").write_text("// ptx", encoding="utf-8")
            (obj / "vl_batch_gpu.meta.json").write_text(
                json.dumps(
                    {
                        "cubin": "vl_batch_gpu.ptx",
                        "cuda_module_format": "ptx",
                        "kernel": "vl_eval_batch_gpu",
                        "storage_size": 80768,
                        "hierarchy_state": {
                            "root_storage_size": 71488,
                            "syms_storage_size": 80768,
                            "unsafe_syms_gep_count": 3358,
                            "prelaunch_rejection_required": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            (obj / "Vsim__main.cpp").write_text(
                "static VortexCuResult rtlmeter_vortex_real_cuda_launch_root_storage_kernel(void*, VortexRuntimeBuffer*, unsigned) {\n"
                "  RtlmeterVortexCuDeviceptr rtlmeter_vortex_root_storage = 0;\n"
                "  cuModuleLoad(0, \"vl_batch_gpu.ptx\");\n"
                "  cuModuleGetFunction(0, 0, \"vl_eval_batch_gpu\");\n"
                "  cuLaunchKernel(0, 1, 1, 1, 256, 1, 1, 0, 0, 0, 0);\n"
                "  return 0;\n"
                "}\n"
                "vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);\n",
                encoding="utf-8",
            )

            report = build_preflight(root, obj_dir=Path("artifacts/obj_dir"))

        self.assertEqual(report["status"], "ready_to_run_real_kernel_callback_smoke")
        self.assertTrue(report["callback_wiring_ready"])
        self.assertTrue(report["root_storage_callback_observed"])
        self.assertTrue(report["root_storage_launch_abi_observed"])
        self.assertFalse(report["noop_callback_observed"])
        self.assertFalse(report["runtime_authority"])
        self.assertEqual(
            report["next_required_boundary"],
            "run_real_vortex_kernel_callback_smoke_and_observable_export",
        )

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            out = root / "reports" / "callback_preflight.json"
            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_kernel_callback_preflight.py",
                "--repo-root",
                root.as_posix(),
                "--obj-dir",
                "artifacts/obj_dir",
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_kernel_callback_preflight")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
