import json

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class HybridConfigTemplateCliTest(HybridCliTestCase):
    def test_gen_hybrid_config_dry_run_emits_gate_manifest_and_template(self) -> None:
        result = self.run_python_tool(
            "src/tools/gen_hybrid_config.py",
            "--target",
            "PULP_ITA.demo_cov",
            "--top-module",
            "demo_cov_tb",
            "--overlay",
            "overlays/demo/src/demo_cov_tb.sv",
            "--dry-run",
        )

        self.assertIn("write: overlays/generated/tests/demo_cov_coverage_regions.json", result.stdout)
        self.assertIn("write: config/slice_launch_templates/demo_cov.json", result.stdout)
        self.assertIn("write: config/scaling_gates/demo_cov_first_hybrid_benchmark_gate.json", result.stdout)
        self.assertIn('"target": "PULP_ITA.demo_cov"', result.stdout)
        self.assertIn('"top_module": "demo_cov_tb"', result.stdout)
        self.assertIn('"host_probe_builder": "src/tools/build_host_probe.py"', result.stdout)
        self.assertIn('"makefile": "not_required_for_generated_template"', result.stdout)
        self.assertIn('"acceptance_policy": "coverage_output_equivalence"', result.stdout)

    def test_run_hybrid_template_dry_run_uses_existing_template(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_template.py",
            "config/slice_launch_templates/pulp_paged_attention_kv_score.json",
            "--shape",
            "64x1",
            "--dry-run",
        )

        stdout = result.stdout
        self.assertIn("verilator --cc --timing", stdout)
        self.assertIn(
            "python3 src/tools/build_host_probe.py config/slice_launch_templates/pulp_paged_attention_kv_score.json",
            stdout,
        )
        self.assertNotIn("make -C src/hybrid pulp_paged_attention_kv_score_host_probe", stdout)
        self.assertIn("python3 src/tools/build_vl_gpu.py artifacts/pulp_paged_attention_kv_score_obj_dir --force", stdout)
        self.assertIn("python3 src/tools/run_vl_hybrid.py --mdir artifacts/pulp_paged_attention_kv_score_obj_dir", stdout)
        self.assertIn("python3 src/tools/compare_vl_hybrid_modes.py artifacts/pulp_paged_attention_kv_score_obj_dir", stdout)
        self.assertIn("--coverage-output-target pulp_paged_attention_kv_score", stdout)
        self.assertIn("pulp_paged_attention_kv_score_cpu_repeat_64x1.bin", stdout)

    def test_run_hybrid_template_dry_run_can_print_efficiency_estimate(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_template.py",
            "config/slice_launch_templates/pulp_paged_attention_kv_score.json",
            "--shape",
            "64x1",
            "--dry-run",
            "--estimate-efficiency",
        )

        stdout = result.stdout
        self.assertIn("# efficiency_estimate", stdout)
        self.assertIn("status: ", stdout)
        self.assertIn("shape: 64x1", stdout)
        self.assertIn("speedup_class: high", stdout)
        self.assertIn("not a broad speedup claim for arbitrary RTL", stdout)

    def test_run_hybrid_template_dry_run_can_print_efficiency_estimate_json(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_template.py",
            "config/slice_launch_templates/pulp_paged_attention_kv_score.json",
            "--shape",
            "64x1",
            "--dry-run",
            "--estimate-efficiency-json",
        )

        marker = "# efficiency_estimate_json\n"
        self.assertIn(marker, result.stdout)
        payload = json.loads(result.stdout.split(marker, 1)[1])
        self.assertIn(payload["status"], {"estimated", "observed_from_existing_reports"})
        self.assertEqual(payload["shape"], "64x1")
        self.assertEqual(payload["speedup_class"], "high")
        self.assertIn("not a broad speedup claim for arbitrary RTL", payload["non_claims"])
