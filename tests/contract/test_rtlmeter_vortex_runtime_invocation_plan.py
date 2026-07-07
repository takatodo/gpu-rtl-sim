import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT, TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_runtime_invocation_plan import build_invocation_plan  # noqa: E402


class RtlmeterVortexRuntimeInvocationPlanTest(HybridCliTestCase):
    def _write_minimal_inputs(self, root: Path, *, helper_ready: bool = True) -> None:
        template = root / "config" / "slice_launch_templates" / "vortex_mini_hello.json"
        template.parent.mkdir(parents=True, exist_ok=True)
        template.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "candidate_fail_closed",
                    "runtime_launchable": False,
                    "source_closure": {
                        "status": "incomplete",
                        "missing_required_sources": [
                            "lowered_tb_runtime_sequence_helper_invocation",
                            "observable_authority_reporting",
                        ],
                    },
                    "planned_overlay": {
                        "runtime_sequence_header": "src/hybrid/vortex_runtime_sequence.h",
                        "runtime_sequence_invocation_plan": {
                            "status": "planned_not_invoked",
                            "entrypoint": "vortex_run_runtime_sequence",
                            "required_order": [
                                "vortex_upload_runtime_buffers",
                                "apply_ordered_dcr_writes_while_reset_asserted",
                                "vortex_kernel_launch_callback",
                                "vortex_export_observables",
                                "vortex_release_runtime_buffers",
                            ],
                        },
                    },
                    "acceptance": {
                        "next_gate_must_invoke_runtime_sequence_helper": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        reports = root / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        (reports / "rtlmeter_vortex_dpi_memory_bridge_review.json").write_text(
            json.dumps({"runtime_sequence_helper_ready": helper_ready}),
            encoding="utf-8",
        )
        header = root / "src" / "hybrid" / "vortex_runtime_sequence.h"
        header.parent.mkdir(parents=True, exist_ok=True)
        header.write_text(
            "\n".join(
                [
                    "void vortex_run_runtime_sequence(void);",
                    "void vortex_upload_runtime_buffers(void);",
                    "void vortex_export_observables(void);",
                    "void vortex_release_runtime_buffers(void);",
                    "typedef int (*VortexDcrApplyFn)(void);",
                    "typedef int (*VortexKernelLaunchFn)(void);",
                ]
            ),
            encoding="utf-8",
        )

    def test_build_invocation_plan_is_ready_but_not_runtime_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_inputs(root)

            summary = build_invocation_plan(root)

        self.assertEqual(summary["status"], "runtime_sequence_invocation_plan_ready_not_invoked")
        self.assertTrue(summary["plan_ready"])
        self.assertFalse(summary["runtime_launchable"])
        self.assertEqual(summary["entrypoint"], "vortex_run_runtime_sequence")
        self.assertEqual(summary["missing_prerequisites"], [])
        self.assertIn("lowered_tb_invokes_vortex_run_runtime_sequence", summary["still_missing_for_execution"])
        self.assertIn("not_runtime_invocation", summary["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_build_invocation_plan_blocks_without_bridge_helper_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_inputs(root, helper_ready=False)

            summary = build_invocation_plan(root)

        self.assertEqual(summary["status"], "blocked_missing_runtime_sequence_invocation_plan")
        self.assertFalse(summary["plan_ready"])
        self.assertIn("bridge_runtime_sequence_helper_ready", summary["missing_prerequisites"])

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_inputs(root)
            out = root / "reports" / "vortex_runtime_invocation_plan.json"

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_runtime_invocation_plan.py",
                "--repo-root",
                root.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_runtime_invocation_plan")
        self.assert_no_local_absolute_paths(result.stdout)

    def test_repo_template_names_runtime_sequence_as_next_gate(self) -> None:
        template = json.loads(
            (REPO_ROOT / "config" / "slice_launch_templates" / "vortex_mini_hello.json").read_text(encoding="utf-8")
        )
        source_closure = template["source_closure"]
        planned_overlay = template["planned_overlay"]
        invocation_plan = planned_overlay["runtime_sequence_invocation_plan"]
        self.assertEqual(source_closure["status"], "incomplete")
        self.assertIn("lowered_tb_runtime_sequence_helper_invocation", source_closure["missing_required_sources"])
        self.assertEqual(planned_overlay["runtime_sequence_header"], "src/hybrid/vortex_runtime_sequence.h")
        self.assertEqual(invocation_plan["status"], "planned_not_invoked")
        self.assertEqual(invocation_plan["entrypoint"], "vortex_run_runtime_sequence")
        self.assertTrue(template["acceptance"]["next_gate_must_invoke_runtime_sequence_helper"])
        self.assertFalse(template["runtime_launchable"])


if __name__ == "__main__":
    unittest.main()
