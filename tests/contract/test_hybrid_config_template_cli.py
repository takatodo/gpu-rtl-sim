import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT, HybridCliTestCase


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
        self.assertIn('"source_closure"', result.stdout)
        self.assertIn('"status": "unknown"', result.stdout)
        self.assertIn('"provenance": "refused_or_unknown"', result.stdout)
        self.assertIn('"explicit_source_closure_required_for_execution": true', result.stdout)

    def test_gen_hybrid_config_dry_run_marks_incomplete_ita_leaf_source_closure(self) -> None:
        result = self.run_python_tool(
            "src/tools/gen_hybrid_config.py",
            "--target",
            "PULP_ITA.filelist_paged_attention_kv_score",
            "--top-module",
            "pulp_paged_attention_kv_score_gpu_cov_tb",
            "--source",
            "third_party/ITA/src/ita.sv",
            "--overlay",
            "overlays/ITA/src/pulp_paged_attention_kv_score_gpu_cov_tb.sv",
            "--dry-run",
        )

        self.assertIn('"source_closure"', result.stdout)
        self.assertIn('"status": "incomplete"', result.stdout)
        self.assertIn('"provenance": "refused_or_unknown"', result.stdout)
        self.assertIn('"third_party/ITA/src/ita_package.sv"', result.stdout)
        self.assertIn('"third_party/common_cells/src/cf_math_pkg.sv"', result.stdout)
        self.assertIn('"automatic_dependency_inference_for_arbitrary_rtl_implemented": false', result.stdout)

    def test_gen_hybrid_config_dry_run_accepts_complete_ita_source_closure(self) -> None:
        template = json.loads(
            (REPO_ROOT / "config" / "slice_launch_templates" / "filelist_paged_attention_kv_score.json").read_text(
                encoding="utf-8"
            )
        )
        source_args = []
        for source_file in template["source_files"]:
            source_args.extend(["--source", source_file])

        result = self.run_python_tool(
            "src/tools/gen_hybrid_config.py",
            "--target",
            "PULP_ITA.filelist_paged_attention_kv_score",
            "--top-module",
            "pulp_paged_attention_kv_score_gpu_cov_tb",
            *source_args,
            "--dry-run",
        )

        self.assertIn('"source_closure"', result.stdout)
        self.assertIn('"status": "complete"', result.stdout)
        self.assertIn('"provenance": "operator_supplied_complete_source_list"', result.stdout)
        self.assertIn('"source_file_count": 29', result.stdout)
        self.assertIn('"missing_required_sources": []', result.stdout)

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

    def test_run_hybrid_template_refuses_known_incomplete_source_closure_non_dry_run(self) -> None:
        self.add_tools_to_path()
        from hybrid_config_generator import HybridConfigSpec, generated_payloads

        spec = HybridConfigSpec(
            target="PULP_ITA.filelist_paged_attention_kv_score",
            top_module="pulp_paged_attention_kv_score_gpu_cov_tb",
            source_files=["third_party/ITA/src/ita.sv"],
            overlay="overlays/ITA/src/pulp_paged_attention_kv_score_gpu_cov_tb.sv",
            gate_name="filelist_paged_attention_kv_score_first_hybrid_benchmark_gate",
            host_probe_target=None,
            mdir=None,
            work_dir=None,
            verilator_args=["--flatten"],
        )
        payloads = generated_payloads(spec)
        template = payloads["config/slice_launch_templates/filelist_paged_attention_kv_score.json"]
        self.assertEqual(template["source_closure"]["status"], "incomplete")

        with tempfile.TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "incomplete_source_closure.json"
            template_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")

            dry_run = self.run_python_tool(
                "src/tools/run_hybrid_template.py",
                str(template_path),
                "--shape",
                "1x1",
                "--dry-run",
            )
            self.assertIn("verilator --cc --timing", dry_run.stdout)

            result = self.run_python_tool(
                "src/tools/run_hybrid_template.py",
                str(template_path),
                "--shape",
                "1x1",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_closure.status=incomplete refuses non-dry-run execution", result.stderr)
        self.assertIn("third_party/ITA/src/ita_package.sv", result.stderr)
        self.assertNotIn("verilator --cc --timing", result.stdout)

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

    def test_run_hybrid_template_resident_dry_run_requires_explicit_patch_script(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_template.py",
            "config/slice_launch_templates/blackparrot_bsg_wormhole_router.json",
            "--shape",
            "256x4",
            "--resident-steps",
            "--dry-run",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--resident-steps requires --patch-script", result.stderr)

    def test_run_hybrid_template_patch_script_requires_resident_steps(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_template.py",
            "config/slice_launch_templates/blackparrot_bsg_wormhole_router.json",
            "--shape",
            "256x4",
            "--patch-script",
            "artifacts/blackparrot_bsg_wormhole_router_packet_pattern_256x4.patch",
            "--dry-run",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--patch-script requires --resident-steps", result.stderr)

    def test_run_hybrid_template_resident_dry_run_prints_resident_command_plan(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_template.py",
            "config/slice_launch_templates/blackparrot_bsg_wormhole_router.json",
            "--shape",
            "256x4",
            "--resident-steps",
            "--patch-script",
            "artifacts/blackparrot_bsg_wormhole_router_packet_pattern_256x4.patch",
            "--dry-run",
        )

        stdout = result.stdout
        self.assertIn("--resident-steps", stdout)
        self.assertIn(
            "--patch-script artifacts/blackparrot_bsg_wormhole_router_packet_pattern_256x4.patch",
            stdout,
        )
        self.assertIn("bsg_wormhole_router_gpu_resident_multistep_256x4.bin", stdout)
        self.assertIn("bsg_wormhole_router_cpu_vs_resident_multistep_256x4_coverage_output_compare.json", stdout)

    def test_run_hybrid_template_resident_non_dry_run_requires_existing_patch_script(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_template.py",
            "config/slice_launch_templates/blackparrot_bsg_wormhole_router.json",
            "--shape",
            "256x4",
            "--resident-steps",
            "--patch-script",
            "artifacts/blackparrot_bsg_wormhole_router_packet_pattern_256x4.patch",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resident patch script does not exist", result.stderr)
        self.assertNotIn("verilator --cc --timing", result.stdout)
