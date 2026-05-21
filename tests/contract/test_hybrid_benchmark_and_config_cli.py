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
        sidecar_plan = report["sidecar_stage_plan"]
        self.assertEqual(sidecar_plan["status"], "planned")
        self.assertEqual(sidecar_plan["correctness_policy"], "coverage_output_equivalence")
        self.assertEqual(
            [stage["stage"] for stage in sidecar_plan["stages"]],
            [
                "verilator_build",
                "host_probe_build",
                "cpu_init_state",
                "cpu_reference_output",
                "gpu_artifact_build",
                "hybrid_sidecar_run",
                "coverage_output_compare",
            ],
        )
        self.assertIn("src/tools/build_vl_gpu.py", sidecar_plan["stages"][4]["command"])
        self.assertIn("src/tools/run_vl_hybrid.py", sidecar_plan["stages"][5]["command"])
        self.assertIn("--acceptance-policy coverage_output_equivalence", sidecar_plan["stages"][6]["command"])
        verilator_details = sidecar_plan["stages"][0]["details"]
        self.assertEqual(verilator_details["top_module"], "pulp_ita_mha_gpu_cov_tb")
        self.assertEqual(verilator_details["mdir"], "artifacts/pulp_ita_mha_obj_dir")
        self.assertIn("overlays/ITA/src/pulp_ita_mha_gpu_cov_tb.sv", verilator_details["source_files"])
        hybrid_details = sidecar_plan["stages"][5]["details"]
        self.assertEqual(hybrid_details["nstates"], 64)
        self.assertEqual(hybrid_details["steps"], 1)
        self.assertTrue(hybrid_details["sanitize_host_only_internals"])
        compare_details = sidecar_plan["stages"][6]["details"]
        self.assertEqual(compare_details["acceptance_policy"], "coverage_output_equivalence")
        self.assertEqual(compare_details["reference_label"], "cpu_repeat_64x1")
        self.assertEqual(compare_details["candidate_label"], "hybrid_from_cpu_init_64x1")
        readiness = sidecar_plan["verilator_option_readiness"]
        self.assertEqual(readiness["status"], "ready_for_verilator_option_shim")
        self.assertEqual(readiness["missing"], [])
        self.assertTrue(readiness["required_inputs"]["verilator_build_has_mdir"])
        self.assertTrue(readiness["required_inputs"]["verilator_build_has_top_module"])
        self.assertTrue(readiness["required_inputs"]["verilator_build_has_source_files"])
        self.assertTrue(readiness["required_inputs"]["hybrid_run_has_shape"])
        self.assertTrue(readiness["required_inputs"]["hybrid_run_has_state_io"])
        self.assertTrue(readiness["required_inputs"]["compare_uses_coverage_output_equivalence"])
        self.assertIn("readiness does not mean Verilator itself implements --sim-accel", readiness["non_claims"])

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

    def test_benchmark_sidecar_option_normalization_keeps_cli_entrypoint_thin(self) -> None:
        self.add_tools_to_path()
        from verilator_sidecar_options import normalize_benchmark_sidecar_options

        options = normalize_benchmark_sidecar_options(
            shape=None,
            sim_accel="sidecar-gpu",
            sim_accel_shape=None,
            sim_accel_states="64",
            sim_accel_steps="1",
            sim_accel_estimate_efficiency=False,
            sidecar_gpu=False,
            estimate_efficiency=False,
            estimate_efficiency_json=False,
        )

        self.assertEqual(options.shape, "64x1")
        self.assertTrue(options.sidecar_gpu)
        self.assertTrue(options.estimate_efficiency)
        self.assertFalse(options.estimate_efficiency_json)
        self.assertFalse(options.explicit_sidecar_gpu)

    def test_benchmark_sidecar_option_normalization_preserves_preflight_probe(self) -> None:
        self.add_tools_to_path()
        from verilator_sidecar_options import normalize_benchmark_sidecar_options

        options = normalize_benchmark_sidecar_options(
            shape=None,
            sim_accel="sidecar-gpu",
            sim_accel_shape=None,
            sim_accel_states="64",
            sim_accel_steps="1",
            sim_accel_estimate_efficiency=False,
            sidecar_gpu=False,
            estimate_efficiency=False,
            estimate_efficiency_json=False,
            preflight=True,
        )

        self.assertEqual(options.shape, "64x1")
        self.assertFalse(options.sidecar_gpu)
        self.assertFalse(options.estimate_efficiency)

    def test_run_hybrid_benchmark_preflight_accepts_verilator_style_sidecar_shape(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--preflight",
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["shape"], "64x1")
        self.assertEqual(report["sidecar_stage_plan"]["status"], "planned")
        self.assertEqual(report["sidecar_stage_plan"]["sim_accel"], "sidecar-gpu")
        self.assertEqual(report["sidecar_stage_plan"]["stages"][0]["stage"], "verilator_build")

    def test_run_hybrid_benchmark_can_print_operator_plan_without_execution(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--print-operator-plan",
        )

        stdout = result.stdout
        self.assertIn("# verilator_sidecar_operator_plan", stdout)
        self.assertIn("command:\nverilator --cc", stdout)
        self.assertIn("--sim-accel sidecar-gpu", stdout)
        self.assertIn("--sim-accel-states 64", stdout)
        self.assertIn("--sim-accel-steps 1", stdout)
        self.assertIn("correctness_policy: coverage_output_equivalence", stdout)
        self.assertIn("operator plan does not execute commands", stdout)
        self.assertIn("operator plan is not correctness or timing evidence", stdout)
        self.assertIn("# efficiency_estimate", stdout)
        self.assertIn("speedup_class: high", stdout)
        self.assertIn("coverage-output equivalence remains separate from performance", stdout)
        self.assertNotIn("schema_version", stdout)

    def test_run_hybrid_benchmark_can_print_operator_plan_json_without_execution(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--operator-plan-json",
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "planned")
        self.assertEqual(payload["correctness_policy"], "coverage_output_equivalence")
        self.assertIn("--sim-accel", payload["command_argv"])
        self.assertIn("--sim-accel sidecar-gpu", payload["command"])
        self.assertEqual(payload["efficiency_estimate"]["target"], "paged_attention_kv_score")
        self.assertEqual(payload["efficiency_estimate"]["shape"], "64x1")
        self.assertIn("operator plan does not execute commands", payload["non_claims"])

    def test_run_hybrid_benchmark_operator_plan_json_is_exclusive(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--operator-plan-json",
            "--print-operator-plan",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mutually exclusive", result.stderr)

    def test_run_hybrid_benchmark_operator_plan_rejects_execution_options(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--print-operator-plan",
            "--dry-run",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--print-operator-plan cannot be combined", result.stderr)

    def test_verilator_sidecar_shim_reports_ready_json_and_exit_zero(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "pulp_ita_mha",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["tool"], "src/tools/verilator_sidecar_shim.py")
        self.assertEqual(payload["status"], "ready_for_verilator_option_shim")
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["shape"], "64x1")
        self.assertEqual(payload["efficiency_estimate"]["speedup_class"], "high")
        readiness = payload["sidecar_stage_plan"]["verilator_option_readiness"]
        self.assertEqual(readiness["status"], "ready_for_verilator_option_shim")
        self.assertEqual(readiness["missing"], [])
        self.assertIn("coverage-output equivalence remains separate", payload["non_claims"][2])

    def test_verilator_sidecar_shim_reports_not_ready_exit_two_for_dataset_target(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "mobile_vit",
            "--limit",
            "128",
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "not_ready_for_verilator_option_shim")
        self.assertEqual(payload["exit_code"], 2)
        self.assertEqual(payload["sidecar_stage_plan"]["status"], "unsupported_for_stage_plan")
        self.assertIn("host preprocessing", payload["sidecar_stage_plan"]["reason"])

    def test_verilator_sidecar_shim_can_select_stage_and_emit_command_without_execution(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "pulp_ita_mha",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--stage",
            "hybrid_sidecar_run",
            "--emit-command",
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ready_for_verilator_option_shim")
        self.assertTrue(payload["command_emitted"])
        self.assertEqual(payload["selected_stage"]["stage"], "hybrid_sidecar_run")
        self.assertEqual(payload["emitted_stage"], "hybrid_sidecar_run")
        self.assertIn("src/tools/run_vl_hybrid.py", payload["emitted_command"])
        self.assertEqual(payload["selected_stage_command"], payload["emitted_command"])
        self.assertIn("--nstates 64 --steps 1", payload["emitted_command"])
        self.assertIn("emitted stage commands are printed but not executed", payload["non_claims"])

    def test_verilator_sidecar_shim_can_emit_future_verilator_command_without_execution(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "pulp_ita_mha",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--emit-verilator-command",
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ready_for_verilator_option_shim")
        self.assertTrue(payload["verilator_command_requested"])
        self.assertTrue(payload["verilator_command_emitted"])
        argv = payload["verilator_command_argv"]
        self.assertEqual(argv[0], "verilator")
        self.assertIn("--sim-accel", argv)
        self.assertIn("sidecar-gpu", argv)
        self.assertIn("--sim-accel-states", argv)
        self.assertIn("64", argv)
        self.assertIn("--sim-accel-steps", argv)
        self.assertIn("1", argv)
        self.assertIn("+define+ITA_M=16", argv)
        command = payload["verilator_command"]
        self.assertIn("verilator --cc", command)
        self.assertIn("--sim-accel sidecar-gpu", command)
        self.assertIn("--sim-accel-states 64", command)
        self.assertIn("--sim-accel-steps 1", command)
        self.assertIn("+define+ITA_M=16", command)
        self.assertIn("-Mdir artifacts/pulp_ita_mha_obj_dir", command)
        self.assertIn("--top-module pulp_ita_mha_gpu_cov_tb", command)
        self.assertIn("overlays/ITA/src/pulp_ita_mha_gpu_cov_tb.sv", command)
        operator_plan = payload["operator_plan"]
        self.assertEqual(operator_plan["status"], "planned")
        self.assertEqual(operator_plan["command_argv"], argv)
        self.assertEqual(operator_plan["command"], command)
        self.assertEqual(operator_plan["efficiency_estimate"]["speedup_class"], "high")
        self.assertEqual(operator_plan["correctness_policy"], "coverage_output_equivalence")
        self.assertIn("operator plan does not execute commands", operator_plan["non_claims"])
        self.assertIn("synthesized Verilator commands are printed but not executed", payload["non_claims"])

    def test_synthesized_verilator_command_preserves_verilator_defines(self) -> None:
        self.add_tools_to_path()
        from hybrid_benchmark_sidecar_plan import synthesized_verilator_command_argv

        argv = synthesized_verilator_command_argv(
            {
                "stages": [
                    {
                        "stage": "verilator_build",
                        "details": {
                            "mdir": "artifacts/example_obj_dir",
                            "top_module": "example_top",
                            "source_files": ["overlays/example_top.sv"],
                            "verilator_defines": ["EXAMPLE_DEFINE=1"],
                            "verilator_args": ["--flatten"],
                        },
                    },
                    {
                        "stage": "hybrid_sidecar_run",
                        "details": {
                            "nstates": 64,
                            "steps": 1,
                        },
                    },
                ],
            }
        )

        self.assertIn("-DEXAMPLE_DEFINE=1", argv)
        self.assertLess(argv.index("-DEXAMPLE_DEFINE=1"), argv.index("--flatten"))

    def test_verilator_sidecar_shim_can_print_future_verilator_command_only(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "pulp_ita_mha",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--print-verilator-command",
        )

        stdout = result.stdout.strip()
        self.assertTrue(stdout.startswith("verilator --cc"))
        self.assertIn("--sim-accel sidecar-gpu", stdout)
        self.assertIn("--sim-accel-states 64", stdout)
        self.assertIn("--sim-accel-steps 1", stdout)
        self.assertNotIn("schema_version", stdout)

    def test_verilator_sidecar_shim_can_print_efficiency_estimate_only(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "pulp_ita_mha",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--print-efficiency-estimate",
        )

        stdout = result.stdout
        self.assertIn("# efficiency_estimate", stdout)
        self.assertIn("target: pulp_ita_mha", stdout)
        self.assertIn("shape: 64x1", stdout)
        self.assertIn("speedup_class: high", stdout)
        self.assertIn("coverage-output equivalence remains separate from performance", stdout)
        self.assertNotIn("schema_version", stdout)

    def test_verilator_sidecar_shim_can_print_operator_plan_without_execution(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "pulp_ita_mha",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--print-operator-plan",
        )

        stdout = result.stdout
        self.assertIn("# verilator_sidecar_operator_plan", stdout)
        self.assertIn("command:\nverilator --cc", stdout)
        self.assertIn("--sim-accel sidecar-gpu", stdout)
        self.assertIn("correctness_policy: coverage_output_equivalence", stdout)
        self.assertIn("operator plan does not execute commands", stdout)
        self.assertIn("operator plan is not correctness or timing evidence", stdout)
        self.assertIn("# efficiency_estimate", stdout)
        self.assertIn("speedup_class: high", stdout)
        self.assertIn("coverage-output equivalence remains separate from performance", stdout)
        self.assertNotIn("schema_version", stdout)

    def test_verilator_sidecar_shim_rejects_two_print_only_modes(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "pulp_ita_mha",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--print-verilator-command",
            "--print-efficiency-estimate",
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["status"], "error")
        self.assertIn("mutually exclusive", payload["error"])

    def test_verilator_sidecar_shim_print_command_not_ready_keeps_json_status(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "mobile_vit",
            "--limit",
            "128",
            "--print-verilator-command",
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "not_ready_for_verilator_option_shim")
        self.assertTrue(payload["verilator_command_requested"])
        self.assertFalse(payload["verilator_command_emitted"])
        self.assertNotIn("verilator_command", payload)

    def test_verilator_sidecar_shim_rejects_unknown_stage_as_json_error(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "pulp_ita_mha",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--stage",
            "no_such_stage",
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["status"], "error")
        self.assertIn("unknown sidecar stage", payload["error"])
        self.assertIn("hybrid_sidecar_run", payload["error"])

    def test_verilator_sidecar_shim_rejects_emit_command_without_stage(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "pulp_ita_mha",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--emit-command",
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["status"], "error")
        self.assertIn("--emit-command requires --stage", payload["error"])

    def test_verilator_sidecar_shim_reports_json_error_exit_one(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "pulp_ita_mha",
            "--sim-accel-states",
            "64",
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["exit_code"], 1)
        self.assertIn("--sim-accel-states and --sim-accel-steps", payload["error"])

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
