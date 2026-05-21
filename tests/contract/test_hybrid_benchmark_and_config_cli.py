import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class HybridBenchmarkAndConfigCliTest(HybridCliTestCase):
    def test_run_hybrid_benchmark_dry_run_dispatches_template_targets(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "pulp_ita_mha",
            "--shape",
            "64x1",
            "--dry-run",
        )

        self.assertIn(
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1",
            result.stdout,
        )

        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--shape",
            "64x1",
            "--dry-run",
        )

        self.assertIn(
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_attention_kv_score.json --shape 64x1",
            result.stdout,
        )

    def test_run_hybrid_benchmark_mobile_vit_dry_run_dispatches_limit_128_flow(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "mobile_vit",
            "--limit",
            "128",
            "--dry-run",
        )

        stdout = result.stdout
        self.assertIn("src/tools/mobile_vit_imagenet_manifest.py", stdout)
        self.assertIn("--limit 128", stdout)
        self.assertIn("src/tools/mobile_vit_hybrid_imagenet_eval.py", stdout)
        self.assertIn("--hybrid-batch-size 128", stdout)

    def test_run_hybrid_benchmark_preflight_reports_commands_without_execution(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "pulp_ita_mha",
            "--shape",
            "64x1",
            "--preflight",
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["tool"], "src/tools/run_hybrid_benchmark.py")
        self.assertEqual(report["target"], "pulp_ita_mha")
        self.assertEqual(report["shape"], "64x1")
        self.assertEqual(report["execution_mode"], "preflight")
        self.assertIn("preflight does not execute benchmark commands", report["non_claims"])
        self.assertIn("run_hybrid_template.py", report["commands"][0])
        estimate = report["efficiency_estimate"]
        self.assertEqual(estimate["speedup_class"], "high")
        self.assertIn("state-parallel", estimate["reason"])
        self.assertIn("not a broad speedup claim for arbitrary RTL", estimate["non_claims"])

    def test_run_hybrid_benchmark_preflight_flags_single_state_repeated_step_as_low_efficiency(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "pulp_ita_mha",
            "--shape",
            "1x64",
            "--preflight",
        )

        estimate = json.loads(result.stdout)["efficiency_estimate"]
        self.assertEqual(estimate["status"], "estimated")
        self.assertEqual(estimate["speedup_class"], "low")
        self.assertIn("launch-overhead", estimate["reason"])
        self.assertIn("resident execution", estimate["next_action"])

    def test_run_hybrid_benchmark_dry_run_can_print_human_efficiency_estimate(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--shape",
            "64x1",
            "--dry-run",
            "--estimate-efficiency",
        )

        stdout = result.stdout
        self.assertIn("run_hybrid_template.py", stdout)
        self.assertIn("# efficiency_estimate", stdout)
        self.assertIn("target: paged_attention_kv_score", stdout)
        self.assertIn("shape: 64x1", stdout)
        self.assertIn("speedup_class: high", stdout)
        self.assertIn("next_action:", stdout)
        self.assertIn("coverage-output equivalence remains separate from performance", stdout)

    def test_run_hybrid_benchmark_sidecar_gpu_is_human_efficiency_alias(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--shape",
            "64x1",
            "--dry-run",
            "--sidecar-gpu",
        )

        stdout = result.stdout
        self.assertIn("run_hybrid_template.py", stdout)
        self.assertIn("# efficiency_estimate", stdout)
        self.assertIn("speedup_class: high", stdout)
        self.assertIn("next_action:", stdout)
        self.assertIn("coverage-output equivalence remains separate from performance", stdout)

    def test_run_hybrid_benchmark_accepts_verilator_style_sidecar_shape(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--dry-run",
        )

        stdout = result.stdout
        self.assertIn("run_hybrid_template.py", stdout)
        self.assertIn("--shape 64x1", stdout)
        self.assertIn("# efficiency_estimate", stdout)
        self.assertIn("speedup_class: high", stdout)

    def test_run_hybrid_benchmark_accepts_verilator_style_efficiency_alias(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--sim-accel-shape",
            "1x64",
            "--sim-accel-estimate-efficiency",
            "--dry-run",
        )

        stdout = result.stdout
        self.assertIn("--shape 1x64", stdout)
        self.assertIn("# efficiency_estimate", stdout)
        self.assertIn("speedup_class: low", stdout)

    def test_run_hybrid_benchmark_rejects_conflicting_shape_spellings(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--shape",
            "64x1",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--dry-run",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("use only one shape spelling", result.stderr)

    def test_run_hybrid_benchmark_dry_run_can_print_efficiency_estimate_json(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--shape",
            "64x1",
            "--dry-run",
            "--estimate-efficiency-json",
        )

        marker = "# efficiency_estimate_json\n"
        self.assertIn(marker, result.stdout)
        payload = json.loads(result.stdout.split(marker, 1)[1])
        self.assertIn(payload["status"], {"estimated", "observed_from_existing_reports"})
        self.assertEqual(payload["target"], "paged_attention_kv_score")
        self.assertEqual(payload["shape"], "64x1")
        self.assertEqual(payload["speedup_class"], "high")
        self.assertIn("not a broad speedup claim for arbitrary RTL", payload["non_claims"])

    def test_run_hybrid_benchmark_preflight_rejects_extra_efficiency_output(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "pulp_ita_mha",
            "--shape",
            "64x1",
            "--preflight",
            "--estimate-efficiency",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--estimate-efficiency cannot be combined with --preflight", result.stderr)

        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "pulp_ita_mha",
            "--shape",
            "64x1",
            "--preflight",
            "--sidecar-gpu",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--estimate-efficiency cannot be combined with --preflight", result.stderr)

    def test_run_hybrid_benchmark_summary_out_uses_unified_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "summary.json"
            result = self.run_python_tool(
                "src/tools/run_hybrid_benchmark.py",
                "pulp_ita_mha",
                "--shape",
                "64x1",
                "--dry-run",
                "--summary-out",
                str(summary_path),
            )

            self.assertIn("+ write", result.stdout)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["schema_version"], 1)
            self.assertEqual(summary["tool"], "src/tools/run_hybrid_benchmark.py")
            self.assertEqual(summary["target"], "pulp_ita_mha")
            self.assertEqual(summary["shape"], "64x1")
            self.assertEqual(summary["mode"], "template")
            self.assertEqual(summary["execution_mode"], "dry_run")
            self.assertIn("compare_report", summary["expected_reports"])
            self.assertEqual(summary["efficiency_estimate"]["speedup_class"], "high")
            self.assertEqual(summary["evidence"]["status"], "not_collected")
            self.assertIn("dry-run summaries are not correctness or timing evidence", summary["non_claims"])

    def test_run_hybrid_benchmark_rejects_missing_required_shape_or_limit(self) -> None:
        result = self.run_python_tool("src/tools/run_hybrid_benchmark.py", "pulp_ita_mha", "--dry-run", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires --shape", result.stderr)

        result = self.run_python_tool("src/tools/run_hybrid_benchmark.py", "mobile_vit", "--dry-run", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("supports --limit 128 only", result.stderr)
