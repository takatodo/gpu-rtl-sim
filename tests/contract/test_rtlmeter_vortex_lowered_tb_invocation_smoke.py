import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_lowered_tb_invocation_smoke import build_smoke  # noqa: E402


class RtlmeterVortexLoweredTbInvocationSmokeTest(HybridCliTestCase):
    def _write_inputs(self, root: Path, *, plan_ready: bool = True) -> None:
        header = root / "src" / "hybrid" / "vortex_lowered_tb_runtime_sequence.h"
        header.parent.mkdir(parents=True, exist_ok=True)
        header.write_text(
            "\n".join(
                [
                    "typedef struct { int runtime_sequence_called; int runtime_sequence_passed; int authority_report_ready; int authority_passed; const char *authority_source; } VortexLoweredTbRuntimeSummary;",
                    "void vortex_run_runtime_sequence(void);",
                    "void vortex_lowered_tb_invoke_runtime_sequence(void);",
                ]
            ),
            encoding="utf-8",
        )
        reports = root / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        (reports / "rtlmeter_vortex_runtime_invocation_plan.json").write_text(
            json.dumps(
                {
                    "status": "runtime_sequence_invocation_plan_ready_not_invoked" if plan_ready else "blocked",
                    "plan_ready": plan_ready,
                }
            ),
            encoding="utf-8",
        )

    def test_build_smoke_is_ready_but_not_generated_lowered_tb_integration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_inputs(root)

            summary = build_smoke(root)

        self.assertEqual(summary["status"], "lowered_tb_invocation_smoke_ready_not_integrated")
        self.assertTrue(summary["smoke_ready"])
        self.assertFalse(summary["runtime_launchable"])
        self.assertEqual(summary["missing_prerequisites"], [])
        self.assertIn(
            "generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            summary["still_missing_for_execution"],
        )
        self.assertIn("not_generated_lowered_tb_integration", summary["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_build_smoke_blocks_without_invocation_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_inputs(root, plan_ready=False)

            summary = build_smoke(root)

        self.assertEqual(summary["status"], "blocked_missing_lowered_tb_invocation_smoke")
        self.assertFalse(summary["smoke_ready"])
        self.assertIn("runtime_invocation_plan_ready", summary["missing_prerequisites"])

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_inputs(root)
            out = root / "reports" / "vortex_lowered_tb_invocation_smoke.json"

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_lowered_tb_invocation_smoke.py",
                "--repo-root",
                root.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_lowered_tb_invocation_smoke")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
