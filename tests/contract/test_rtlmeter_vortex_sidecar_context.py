import json
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_sidecar_context import build_context  # noqa: E402


class RtlmeterVortexSidecarContextTest(HybridCliTestCase):
    def _write_source_closure_report(self, root: Path) -> Path:
        path = root / "reports" / "rtlmeter_vortex_source_closure.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "descriptor_source_closure_complete",
                    "all_sources_exist": True,
                    "source_files": [
                        {
                            "descriptor_path": "src/tb.sv",
                            "path": "third_party/rtlmeter/designs/Vortex/src/tb.sv",
                        },
                        {
                            "descriptor_path": "src/Vortex.sv",
                            "path": "third_party/rtlmeter/designs/Vortex/src/Vortex.sv",
                        },
                    ],
                    "include_files": [
                        {
                            "descriptor_path": "src/VX_define.vh",
                            "path": "third_party/rtlmeter/designs/Vortex/src/VX_define.vh",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_builds_vortex_context_from_descriptor_source_closure_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self._write_source_closure_report(root)

            context = build_context(root, source_closure_report=report_path)

        self.assertEqual(context["status"], "vortex_sidecar_context_metadata_ready")
        self.assertEqual(context["target"], "rtlmeter_vortex_mini_hello")
        self.assertEqual(context["rtlmeter_case"], "Vortex:mini:hello")
        self.assertEqual(
            context["template_or_target_registry_entry"],
            "config/rtlmeter_sidecar_authorities/rtlmeter_vortex_mini_hello.json",
        )
        self.assertEqual(
            context["state_and_report_path_rules"]["artifact_root"],
            "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare",
        )
        self.assertEqual(context["source_closure"]["status"], "complete")
        self.assertIn("verilogSourceFiles/tb.sv", context["source_closure"]["filelist_entries"])
        self.assertIn("verilogIncludeFiles/VX_define.vh", context["source_closure"]["filelist_entries"])
        self.assertFalse(context["execution_authority"])
        self.assertFalse(context["sidecar_execution_invoked"])
        self.assert_no_local_absolute_paths(json.dumps(context, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self._write_source_closure_report(root)
            out = root / "reports" / "vortex_context.json"

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_sidecar_context.py",
                "--repo-root",
                root.as_posix(),
                "--source-closure-report",
                report_path.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_sidecar_context")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
