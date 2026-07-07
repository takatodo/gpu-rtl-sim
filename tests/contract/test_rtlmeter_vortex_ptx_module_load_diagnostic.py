import json
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVortexPtxModuleLoadDiagnosticTest(HybridCliTestCase):
    def test_reports_ptx_scale_without_runtime_claims(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_ptx_module_load_diagnostic import build_diagnostic

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ptx = root / "artifacts" / "vortex" / "obj_dir" / "vl_batch_gpu.ptx"
            meta = ptx.with_name("vl_batch_gpu.meta.json")
            ptx.parent.mkdir(parents=True)
            ptx.write_text(
                "\n".join(
                    [
                        ".version 8.0",
                        ".target sm_80",
                        ".address_size 64",
                        ".visible .entry vl_batch_gpu() {",
                        ".reg .b32 %r<4>;",
                        "}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            meta.write_text(json.dumps({"kernels": ["vl_batch_gpu"], "unsafe_syms_gep_count": 0}), encoding="utf-8")

            report = build_diagnostic(root, ptx_path=ptx, meta_path=meta)

        self.assertEqual(report["status"], "ptx_ready_ptxas_probe_not_run")
        self.assertEqual(report["ptx_lines"], 6)
        self.assertEqual(report["ptx_target"], "sm_80")
        self.assertEqual(report["visible_entry_count"], 1)
        self.assertEqual(report["meta_kernel_count"], 1)
        self.assertEqual(report["meta_unsafe_syms_gep_count"], 0)
        self.assertEqual(
            report["next_required_boundary"],
            "run_bounded_ptxas_probe_for_vortex_cuModuleLoad_jit_timeout",
        )
        self.assertFalse(report["runtime_authority"])
        self.assertFalse(report["kernel_execution_observed"])
        self.assertFalse(report["timing_measured"])
        self.assertIn("ptxas_probe_is_not_cpu_vs_hybrid_timing", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_classifies_bounded_ptxas_timeout(self) -> None:
        self.add_tools_to_path()
        import rtlmeter_vortex_ptx_module_load_diagnostic as diagnostic

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ptx = root / "artifacts" / "vortex" / "obj_dir" / "vl_batch_gpu.ptx"
            ptx.parent.mkdir(parents=True)
            ptx.write_text(".version 8.0\n.target sm_80\n.address_size 64\n", encoding="utf-8")
            with mock.patch.object(diagnostic.shutil, "which", return_value="/usr/local/cuda/bin/ptxas"):
                with mock.patch.object(
                    diagnostic.subprocess,
                    "run",
                    side_effect=subprocess.TimeoutExpired(
                        cmd=["ptxas"],
                        timeout=0.01,
                        output=b"partial stdout",
                        stderr=b"partial stderr",
                    ),
                ):
                    report = diagnostic.build_diagnostic(
                        root,
                        ptx_path=ptx,
                        meta_path=None,
                        run_ptxas=True,
                        ptxas_timeout_seconds=0.01,
                    )

        self.assertEqual(report["status"], "ptxas_timeout")
        self.assertTrue(report["ptxas_timed_out"])
        self.assertEqual(
            report["next_required_boundary"],
            "split_or_precompile_vortex_ptx_before_cuModuleLoad_retry",
        )
        self.assertIn("partial stdout", report["ptxas_stdout_tail"])
        self.assertIn("partial stderr", report["ptxas_stderr_tail"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_allows_veer_specific_case_surface_and_boundaries(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_ptx_module_load_diagnostic import build_diagnostic

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ptx = root / "artifacts" / "veer_eh2" / "vl_batch_gpu.ptx"
            ptx.parent.mkdir(parents=True)
            ptx.write_text(".version 8.0\n.target sm_89\n.address_size 64\n", encoding="utf-8")

            report = build_diagnostic(
                root,
                ptx_path=ptx,
                meta_path=None,
                case="VeeR-EH2:default:hello",
                surface="rtlmeter_veer_eh2_ptx_entry_slice_module_load_diagnostic",
                ptxas_not_run_boundary="run_bounded_ptxas_probe_on_veer_eh2_entry_slice",
            )

        self.assertEqual(report["case"], "VeeR-EH2:default:hello")
        self.assertEqual(report["surface"], "rtlmeter_veer_eh2_ptx_entry_slice_module_load_diagnostic")
        self.assertEqual(
            report["next_required_boundary"],
            "run_bounded_ptxas_probe_on_veer_eh2_entry_slice",
        )
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ptx = root / "artifacts" / "vortex" / "obj_dir" / "vl_batch_gpu.ptx"
            ptx.parent.mkdir(parents=True)
            ptx.write_text(".version 8.0\n.target sm_80\n.address_size 64\n", encoding="utf-8")
            out = root / "reports" / "diagnostic.json"
            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_ptx_module_load_diagnostic.py",
                "--repo-root",
                root.as_posix(),
                "--ptx",
                ptx.relative_to(root).as_posix(),
                "--no-meta",
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_ptx_module_load_diagnostic")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
