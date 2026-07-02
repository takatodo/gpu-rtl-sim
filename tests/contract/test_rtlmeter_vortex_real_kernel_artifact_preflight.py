import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVortexRealKernelArtifactPreflightTest(HybridCliTestCase):
    def test_reports_missing_artifact_without_runtime_claims(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_real_kernel_artifact_preflight import build_preflight

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = build_preflight(root, search_roots=[Path("artifacts/vortex")])

        self.assertEqual(report["status"], "real_vortex_kernel_artifact_missing")
        self.assertFalse(report["kernel_artifact_ready"])
        self.assertIsNone(report["kernel_artifact_format"])
        self.assertEqual(report["cubin_count"], 0)
        self.assertEqual(
            report["next_required_boundary"],
            "build_real_vortex_kernel_artifact_for_materialized_runtime_callback",
        )
        self.assertFalse(report["runtime_authority"])
        self.assertFalse(report["timing_measured"])
        self.assertIn("missing_artifact_preflight_is_not_timing_evidence", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_reports_cubin_artifact_ready(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_real_kernel_artifact_preflight import build_preflight

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cubin = root / "artifacts" / "vortex" / "obj_dir" / "vl_batch_gpu.cubin"
            meta = cubin.with_name("vl_batch_gpu.meta.json")
            cubin.parent.mkdir(parents=True)
            cubin.write_bytes(b"cubin")
            meta.write_text("{}", encoding="utf-8")

            report = build_preflight(root, search_roots=[Path("artifacts/vortex")])

        self.assertEqual(report["status"], "real_vortex_kernel_artifact_ready")
        self.assertTrue(report["kernel_artifact_ready"])
        self.assertEqual(report["kernel_artifact_format"], "cubin")
        self.assertEqual(report["cubin_count"], 1)
        self.assertEqual(report["metadata_count"], 1)
        self.assertEqual(
            report["next_required_boundary"],
            "wire_real_vortex_kernel_artifact_into_materialized_runtime_callback",
        )
        self.assertIn("artifacts/vortex/obj_dir/vl_batch_gpu.cubin", report["kernel_artifacts"])

    def test_reports_ptx_with_metadata_artifact_ready(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_real_kernel_artifact_preflight import build_preflight

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ptx = root / "artifacts" / "vortex" / "obj_dir" / "vl_batch_gpu.ptx"
            meta = ptx.with_name("vl_batch_gpu.meta.json")
            ptx.parent.mkdir(parents=True)
            ptx.write_text("// ptx", encoding="utf-8")
            meta.write_text("{}", encoding="utf-8")

            report = build_preflight(root, search_roots=[Path("artifacts/vortex")])

        self.assertEqual(report["status"], "real_vortex_kernel_artifact_ready")
        self.assertTrue(report["kernel_artifact_ready"])
        self.assertEqual(report["kernel_artifact_format"], "ptx")
        self.assertEqual(report["ptx_count"], 1)
        self.assertEqual(report["metadata_count"], 1)
        self.assertEqual(
            report["next_required_boundary"],
            "wire_real_vortex_kernel_artifact_into_materialized_runtime_callback",
        )

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            out = root / "reports" / "preflight.json"
            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_real_kernel_artifact_preflight.py",
                "--repo-root",
                root.as_posix(),
                "--search-root",
                "artifacts/vortex",
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_real_kernel_artifact_preflight")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
