import json
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT, HybridCliTestCase
from tests.contract.hybrid_cli_tlul_cases import TLUL_CLOCK_RESET_DEFINE_CASES


class HybridVerilatorLikeConfigGenerationTest(HybridCliTestCase):
    def test_generated_payloads_are_importable_and_structured(self) -> None:
        self.add_tools_to_path()
        from hybrid_config_generator import HybridConfigSpec, generated_payloads

        spec = HybridConfigSpec(
            target="PULP_ITA.demo_cov",
            top_module="demo_cov_tb",
            source_files=[],
            overlay="overlays/demo/src/demo_cov_tb.sv",
            gate_name="demo_cov_gate",
            host_probe_target=None,
            mdir=None,
            work_dir=None,
            verilator_args=["--flatten"],
        )
        payloads = generated_payloads(spec)
        self.assertEqual(
            set(payloads),
            {
                "overlays/generated/tests/demo_cov_coverage_regions.json",
                "config/slice_launch_templates/demo_cov.json",
                "config/scaling_gates/demo_cov_gate.json",
            },
        )
        for payload in payloads.values():
            json.dumps(payload)
        template = payloads["config/slice_launch_templates/demo_cov.json"]
        gate = payloads["config/scaling_gates/demo_cov_gate.json"]
        self.assertEqual(template["build"]["host_probe_target"], "demo_cov_host_probe")
        self.assertEqual(template["build"]["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertEqual(template["build"]["host_probe"]["clock_field"], "demo_cov_tb__DOT__clk_i")
        self.assertEqual(template["build"]["host_probe"]["reset_field"], "demo_cov_tb__DOT__reset_like_w")
        self.assertEqual(template["build"]["mdir"], "artifacts/demo_cov_obj_dir")
        self.assertEqual(template["source_closure"]["status"], "unknown")
        self.assertEqual(template["source_closure"]["provenance"], "refused_or_unknown")
        self.assertEqual(gate["coverage_output_contract"]["total_words_per_state"], 29)
        self.assertFalse(gate["source_closure_policy"]["automatic_dependency_inference_for_arbitrary_rtl_implemented"])
        self.assertTrue(gate["acceptance_policy"]["host_probe_glue_generated_from_template"])
        self.assertFalse(gate["acceptance_policy"]["makefile_target_required"])

    def test_generated_payload_can_copy_known_template_source_closure(self) -> None:
        self.add_tools_to_path()
        from hybrid_config_generator import HybridConfigSpec, generated_payloads

        reference_template = "config/slice_launch_templates/filelist_paged_attention_kv_score.json"
        spec = HybridConfigSpec(
            target="PULP_ITA.demo_cov",
            top_module="demo_cov_tb",
            source_files=[],
            overlay="overlays/demo/src/demo_cov_tb.sv",
            gate_name="demo_cov_gate",
            host_probe_target=None,
            mdir=None,
            work_dir=None,
            verilator_args=["--flatten"],
            copy_source_closure_from_template=reference_template,
        )
        template = generated_payloads(spec)["config/slice_launch_templates/demo_cov.json"]
        source_closure = template["source_closure"]

        self.assertGreater(template["source_files"].index("third_party/ITA/src/ita_package.sv"), -1)
        self.assertIn("overlays/demo/src/demo_cov_tb.sv", template["source_files"])
        self.assertEqual(source_closure["status"], "complete")
        self.assertEqual(source_closure["provenance"], "copied_from_known_tracked_template")
        self.assertEqual(source_closure["reference_template"], reference_template)
        self.assertEqual(source_closure["copied_from_template"], reference_template)
        self.assertEqual(source_closure["source_file_count"], 29)
        self.assertRegex(source_closure["source_files_sha256"], r"^[0-9a-f]{64}$")
        self.assertFalse(
            source_closure["policy"]["automatic_dependency_inference_for_arbitrary_rtl_implemented"]
        )

    def test_generated_payload_copies_known_template_verilator_args(self) -> None:
        self.add_tools_to_path()
        from hybrid_config_generator import HybridConfigSpec, generated_payloads

        reference_template = "config/slice_launch_templates/pulp_ita_mha.json"
        spec = HybridConfigSpec(
            target="PULP_ITA.demo_cov",
            top_module="demo_cov_tb",
            source_files=[],
            overlay="overlays/demo/src/demo_cov_tb.sv",
            gate_name="demo_cov_gate",
            host_probe_target=None,
            mdir=None,
            work_dir=None,
            verilator_args=["--flatten"],
            copy_source_closure_from_template=reference_template,
        )
        template = generated_payloads(spec)["config/slice_launch_templates/demo_cov.json"]

        self.assertIn("-Wno-WIDTHEXPAND", template["verilator_args"])
        self.assertIn("-Wno-WIDTHTRUNC", template["verilator_args"])
        self.assertIn("-Wno-COMBDLY", template["verilator_args"])
        self.assertIn("+define+ITA_M=16", template["verilator_args"])
        self.assertEqual(template["verilator_args"].count("--flatten"), 1)

    def test_generated_payload_refuses_unknown_template_source_closure_copy(self) -> None:
        self.add_tools_to_path()
        from hybrid_config_generator import HybridConfigSpec, generated_payloads

        spec = HybridConfigSpec(
            target="PULP_ITA.demo_cov",
            top_module="demo_cov_tb",
            source_files=[],
            overlay="overlays/demo/src/demo_cov_tb.sv",
            gate_name="demo_cov_gate",
            host_probe_target=None,
            mdir=None,
            work_dir=None,
            verilator_args=["--flatten"],
            copy_source_closure_from_template="config/slice_launch_templates/pulp_paged_attention_kv_score.json",
        )

        with self.assertRaisesRegex(ValueError, "source_closure.status=complete"):
            generated_payloads(spec)

    def test_generated_payload_refuses_requested_source_missing_from_copied_closure(self) -> None:
        self.add_tools_to_path()
        from hybrid_config_generator import HybridConfigSpec, generated_payloads

        spec = HybridConfigSpec(
            target="PULP_ITA.demo_cov",
            top_module="demo_cov_tb",
            source_files=["third_party/ITA/src/not_in_known_closure.sv"],
            overlay="overlays/demo/src/demo_cov_tb.sv",
            gate_name="demo_cov_gate",
            host_probe_target=None,
            mdir=None,
            work_dir=None,
            verilator_args=["--flatten"],
            copy_source_closure_from_template="config/slice_launch_templates/filelist_paged_attention_kv_score.json",
        )

        with self.assertRaisesRegex(ValueError, "requested --source entries"):
            generated_payloads(spec)

    def test_gen_hybrid_config_cli_copies_known_template_source_closure_in_dry_run(self) -> None:
        result = self.run_python_tool(
            "src/tools/gen_hybrid_config.py",
            "--target",
            "PULP_ITA.demo_cov",
            "--top-module",
            "demo_cov_tb",
            "--overlay",
            "overlays/demo/src/demo_cov_tb.sv",
            "--source",
            "third_party/ITA/src/ita.sv",
            "--source-closure-from-template",
            "config/slice_launch_templates/filelist_paged_attention_kv_score.json",
            "--dry-run",
        )

        self.assertIn('"status": "complete"', result.stdout)
        self.assertIn('"provenance": "copied_from_known_tracked_template"', result.stdout)
        self.assertIn('"reference_template": "config/slice_launch_templates/filelist_paged_attention_kv_score.json"', result.stdout)

    def test_gen_hybrid_config_refuses_to_overwrite_existing_source_files(self) -> None:
        result = self.run_python_tool(
            "src/tools/gen_hybrid_config.py",
            "--target",
            "PULP_ITA.filelist_paged_attention_kv_score",
            "--top-module",
            "pulp_paged_attention_kv_score_gpu_cov_tb",
            "--overlay",
            "overlays/ITA/src/pulp_paged_attention_kv_score_gpu_cov_tb.sv",
            "--source-closure-from-template",
            "config/slice_launch_templates/filelist_paged_attention_kv_score.json",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite existing source-of-truth file", result.stderr)

    def test_materialized_known_template_copy_runs_hybrid_template_dry_run_plan(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_template.py",
            "config/slice_launch_templates/filelist_known_template_paged_attention_kv_score.json",
            "--shape",
            "1x1",
            "--dry-run",
        )
        lines = [line for line in result.stdout.splitlines() if line.startswith("+ ")]

        self.assertEqual(len(lines), 7)
        self.assertIn("verilator --cc", lines[0])
        self.assertIn("python3 src/tools/build_host_probe.py", result.stdout)
        self.assertIn("python3 src/tools/build_vl_gpu.py", result.stdout)
        self.assertIn("python3 src/tools/run_vl_hybrid.py", result.stdout)
        self.assertIn("--acceptance-policy coverage_output_equivalence", result.stdout)
        self.assertIn(
            "--coverage-output-gate records/scaling_gates/filelist_known_template_paged_attention_kv_score_first_hybrid_benchmark_gate.json",
            result.stdout,
        )

    def test_generated_template_uses_host_probe_builder_without_makefile_glue(self) -> None:
        self.add_tools_to_path()
        from hybrid_config_generator import HybridConfigSpec, generated_payloads
        from hybrid_template_runner import command_plan, load_template_plan
        from hybrid_host_probe_builder import host_probe_compile_command, load_host_probe_build_plan

        spec = HybridConfigSpec(
            target="PULP_ITA.demo_cov",
            top_module="demo_cov_tb",
            source_files=[],
            overlay="overlays/demo/src/demo_cov_tb.sv",
            gate_name="demo_cov_gate",
            host_probe_target=None,
            mdir="artifacts/demo_cov_obj_dir",
            work_dir=None,
            verilator_args=["--flatten"],
        )
        payloads = generated_payloads(spec)
        with tempfile.TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "demo_cov.json"
            template_path.write_text(
                json.dumps(payloads["config/slice_launch_templates/demo_cov.json"], indent=2) + "\n",
                encoding="utf-8",
            )

            commands = command_plan(load_template_plan(template_path, shape="1x1"))
            self.assertEqual(commands[1][0:2], ["python3", "src/tools/build_host_probe.py"])
            self.assertNotIn("make", commands[1])

            build_plan = load_host_probe_build_plan(template_path)
            compile_command = host_probe_compile_command(build_plan)
            joined = " ".join(compile_command)
            self.assertIn("-DMODEL_HEADER=\"Vdemo_cov_tb.h\"", joined)
            self.assertIn("-DROOT_CLK_FIELD=demo_cov_tb__DOT__clk_i", joined)
            self.assertIn("-DROOT_RST_FIELD=demo_cov_tb__DOT__reset_like_w", joined)
            self.assertIn("artifacts/demo_cov_obj_dir/*.cpp", joined)

    def test_legacy_tlul_template_normalizes_to_generated_template_plan(self) -> None:
        self.add_tools_to_path()
        from hybrid_host_probe_builder import host_probe_compile_command, load_host_probe_build_plan
        from hybrid_template_runner import command_plan, load_template_plan

        template_path = REPO_ROOT / "config" / "slice_launch_templates" / "tlul_fifo_sync.json"
        plan = load_template_plan(template_path, shape="1x1")
        commands = command_plan(plan)

        self.assertEqual(plan.target, "OpenTitan.tlul_fifo_sync")
        self.assertEqual(plan.top_module, "tlul_fifo_sync_gpu_cov_tb")
        self.assertEqual(plan.source_gate, REPO_ROOT / "config" / "scaling_gates" / "tlul_coverage_output_equivalence.json")
        self.assertIn(REPO_ROOT / "third_party" / "rtlmeter" / "designs" / "OpenTitan" / "src" / "top_pkg.sv", plan.source_files)
        self.assertIn(REPO_ROOT / "third_party" / "rtlmeter" / "designs" / "OpenTitan" / "src" / "tlul_pkg.sv", plan.source_files)
        self.assertIn("-Ioverlays/rtlmeter/designs/OpenTitan/src", commands[0])
        self.assertEqual(commands[1][0:2], ["python3", "src/tools/build_host_probe.py"])
        self.assertNotIn("make", commands[1])
        joined_compare = " ".join(commands[-1])
        self.assertIn("--acceptance-policy coverage_output_equivalence", joined_compare)
        self.assertIn("--coverage-output-target tlul_fifo_sync", joined_compare)

        build_plan = load_host_probe_build_plan(template_path)
        compile_command = " ".join(host_probe_compile_command(build_plan))
        self.assertIn("-DMODEL_HEADER=\"Vtlul_fifo_sync_gpu_cov_tb.h\"", compile_command)
        self.assertIn("-DROOT_CLK_FIELD=tlul_fifo_sync_gpu_cov_tb__DOT__clk_i", compile_command)
        self.assertIn("-DROOT_RST_FIELD=tlul_fifo_sync_gpu_cov_tb__DOT__reset_like_w", compile_command)

    def test_legacy_tlul_normalization_uses_target_specific_clock_reset_fields(self) -> None:
        self.add_tools_to_path()
        from hybrid_host_probe_builder import host_probe_compile_command, load_host_probe_build_plan

        for target, expected_defines in TLUL_CLOCK_RESET_DEFINE_CASES.items():
            template_path = REPO_ROOT / "config" / "slice_launch_templates" / f"{target}.json"
            compile_command = " ".join(host_probe_compile_command(load_host_probe_build_plan(template_path)))
            for expected in expected_defines:
                self.assertIn(expected, compile_command)

    def test_tlul_lc_gate_normalization_adds_lc_package_order(self) -> None:
        self.add_tools_to_path()
        from hybrid_template_runner import load_template_plan

        template_path = REPO_ROOT / "config" / "slice_launch_templates" / "tlul_lc_gate.json"
        plan = load_template_plan(template_path, shape="1x1")
        source_files = [str(path.relative_to(REPO_ROOT)) for path in plan.source_files]

        self.assertLess(
            source_files.index("third_party/rtlmeter/designs/OpenTitan/src/lc_ctrl_reg_pkg.sv"),
            source_files.index("third_party/rtlmeter/designs/OpenTitan/src/lc_ctrl_pkg.sv"),
        )
        self.assertLess(
            source_files.index("third_party/rtlmeter/designs/OpenTitan/src/lc_ctrl_pkg.sv"),
            source_files.index("third_party/rtlmeter/designs/OpenTitan/src/tlul_lc_gate.sv"),
        )

    def test_run_hybrid_template_passes_template_verilator_defines(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_template.py",
            "config/slice_launch_templates/nvdla_cmac_core_mac.json",
            "--shape",
            "1x1",
            "--dry-run",
        )

        first_line = result.stdout.splitlines()[0]
        self.assertIn("-DSYNTHESIS", first_line)
        self.assertIn("-DDESIGNWARE_NOEXIST", first_line)
        self.assertIn("--flatten", first_line)
        self.assertIn("third_party/rtlmeter/designs/NVDLA/src/NV_DW02_tree.v", first_line)
        self.assertIn("third_party/rtlmeter/designs/NVDLA/src/NV_DW_minmax.v", first_line)


if __name__ == "__main__":
    unittest.main()
