import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class HybridSimAccelShapeCliTest(HybridCliTestCase):
    def test_sim_accel_shape_alone_dry_run_enters_sidecar_preview(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--sim-accel-shape",
            "64x1",
            "--dry-run",
        )

        stdout = result.stdout
        self.assertIn("# verilator_option_preview", stdout)
        self.assertIn("--sim-accel sidecar-gpu", stdout)
        self.assertIn("estimate_command:\nverilator --cc", stdout)
        self.assertIn("--sim-accel-estimate-efficiency", stdout)
        self.assertIn(
            "requested_compatibility_entrypoint: "
            "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1",
            stdout,
        )
        self.assertIn("+ python3 src/tools/run_hybrid_template.py", stdout)
        self.assertIn("# efficiency_estimate", stdout)

    def test_sim_accel_shape_preflight_records_effective_sidecar_entrypoint(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--sim-accel-shape",
            "64x1",
            "--preflight",
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["execution_mode"], "preflight")
        self.assertEqual(report["operator_entrypoint"]["surface"], "sim_accel_compat")
        self.assertTrue(report["operator_entrypoint"]["sidecar_gpu_requested"])
        self.assertIsNone(report["operator_entrypoint"]["sim_accel"])
        self.assertEqual(report["operator_entrypoint"]["effective_sim_accel"], "sidecar-gpu")
        self.assertEqual(report["operator_entrypoint"]["sim_accel_source"], "sim_accel_shape_spelling")
        self.assertEqual(report["operator_entrypoint"]["shape_source"], "sim_accel_shape")
        self.assertEqual(report["verilator_option_preview"]["status"], "planned")
        self.assertEqual(
            report["verilator_option_preview"]["requested_compatibility_entrypoint"],
            "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1",
        )
        self.assertEqual(
            report["discovery_hint"]["requested_compatibility_entrypoint"],
            "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1",
        )
        self.assertEqual(report["discovery_hint"]["requested_shape"], "64x1")
        self.assertEqual(report["efficiency_estimate"]["shape"], "64x1")

    def test_sidecar_gpu_print_verilator_estimate_command_stays_command_only(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--sim-accel-shape",
            "64x1",
            "--print-verilator-estimate-command",
        )

        stdout = result.stdout
        self.assertIn("verilator --cc", stdout)
        self.assertIn("--sim-accel sidecar-gpu", stdout)
        self.assertIn("--sim-accel-estimate-efficiency", stdout)
        self.assertNotIn("requested_compatibility_entrypoint", stdout)
        self.assertNotIn("# efficiency_estimate", stdout)
        self.assertNotIn("schema_version", stdout)

    def test_plain_verilator_command_rejects_ignored_estimate_flag(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--sim-accel-shape",
            "64x1",
            "--print-verilator-command",
            "--sim-accel-estimate-efficiency",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("use --print-verilator-estimate-command", result.stderr)

    def test_summary_records_sim_accel_shape_as_compat_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "summary.json"
            self.run_python_tool(
                "src/tools/run_hybrid_benchmark.py",
                "paged_attention_kv_score",
                "--sim-accel-shape",
                "64x1",
                "--dry-run",
                "--summary-out",
                str(summary_path),
            )

            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["operator_entrypoint"]["surface"], "sim_accel_compat")
        self.assertTrue(summary["operator_entrypoint"]["sidecar_gpu_requested"])
        self.assertIsNone(summary["operator_entrypoint"]["sim_accel"])
        self.assertEqual(summary["operator_entrypoint"]["effective_sim_accel"], "sidecar-gpu")
        self.assertEqual(summary["operator_entrypoint"]["sim_accel_source"], "sim_accel_shape_spelling")
        self.assertEqual(summary["operator_entrypoint"]["shape_source"], "sim_accel_shape")
        self.assertEqual(summary["verilator_option_preview"]["status"], "planned")
        self.assertEqual(
            summary["verilator_option_preview"]["requested_compatibility_entrypoint"],
            "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1",
        )
        self.assertNotIn("--sim-accel-estimate-efficiency", summary["verilator_option_preview"]["command"])
        self.assertIn("--sim-accel-estimate-efficiency", summary["verilator_option_preview"]["estimate_command"])
        self.assertEqual(
            summary["verilator_option_preview"]["estimate_command_argv"],
            [*summary["verilator_option_preview"]["command_argv"], "--sim-accel-estimate-efficiency"],
        )
        self.assertEqual(summary["efficiency_estimate"]["shape"], "64x1")
        self.assertEqual(summary["discovery_hint"]["requested_shape"], "64x1")
        self.assertEqual(summary["discovery_hint"]["recommended_entrypoint"], "--sim-accel-shape <NxS>")
        self.assertEqual(
            summary["discovery_hint"]["requested_compatibility_entrypoint"],
            "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1",
        )
        self.assertIn(
            summary["discovery_hint"]["requested_compatibility_entrypoint"],
            summary["verilator_option_preview"]["command"],
        )

    def test_operator_plan_json_separates_requested_shape_from_discovery_hint(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--sim-accel-shape",
            "1x64",
            "--operator-plan-json",
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["operator_entrypoint"]["shape"], "1x64")
        self.assertEqual(report["efficiency_estimate"]["shape"], "1x64")
        self.assertEqual(report["handoff_contract"]["shape"], "1x64")
        self.assertEqual(report["discovery_hint"]["requested_shape"], "1x64")
        self.assertEqual(report["discovery_hint"]["recommended_shape"], "64x1")
        self.assertFalse(report["discovery_hint"]["recommended_shape_matches_request"])
        self.assertEqual(
            report["discovery_hint"]["requested_compatibility_entrypoint"],
            "--sim-accel sidecar-gpu --sim-accel-states 1 --sim-accel-steps 64",
        )
