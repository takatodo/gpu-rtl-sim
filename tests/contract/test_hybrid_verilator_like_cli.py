import json
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import (
    PUBLIC_PACK_REPRESENTATIVE_PATHS,
    REPO_ROOT,
    HybridCliTestCase,
    hybrid_benchmark_command,
    results_reproduction_command,
)


class HybridVerilatorLikeCliTest(HybridCliTestCase):
    def test_state_pair_plan_covers_supported_dump_shapes(self) -> None:
        self.add_tools_to_path()
        from compare_vl_hybrid_state_pairs import state_pair_plan

        matching = state_pair_plan(reference_len=16, candidate_len=16, storage_size=8)
        self.assertTrue(matching["compatible"])
        self.assertEqual(matching["comparison_mode"], "corresponding_state_chunks")
        self.assertEqual(matching["pairs"], [(0, 0), (1, 1)])

        broadcast_reference = state_pair_plan(reference_len=8, candidate_len=24, storage_size=8)
        self.assertTrue(broadcast_reference["compatible"])
        self.assertEqual(
            broadcast_reference["comparison_mode"],
            "single_reference_state_against_candidate_chunks",
        )
        self.assertEqual(broadcast_reference["pairs"], [(0, 0), (0, 1), (0, 2)])

        incompatible = state_pair_plan(reference_len=16, candidate_len=24, storage_size=8)
        self.assertFalse(incompatible["compatible"])
        self.assertEqual(incompatible["comparison_mode"], "incompatible_state_counts")

    def test_hybrid_benchmark_list_targets_prints_supported_aliases(self) -> None:
        result = self.run_python_tool("src/tools/run_hybrid_benchmark.py", "--list-targets")

        payload = json.loads(result.stdout)
        self.assertEqual(payload["tool"], "src/tools/run_hybrid_benchmark.py")
        targets = {target["name"]: target for target in payload["targets"]}
        for name in (
            "pulp_ita_mha",
            "paged_attention_kv_score",
            "pulp_paged_attention_kv_score",
            "pulp_paged_kv_cache_large",
            "paged_kv_cache_large",
            "mobile_vit",
        ):
            self.assertIn(name, targets)
        self.assertEqual(targets["pulp_paged_kv_cache_large"]["requires"], ["--shape"])
        self.assertEqual(targets["paged_kv_cache_large"]["canonical_target"], "pulp_paged_kv_cache_large")
        self.assertEqual(targets["mobile_vit"]["requires"], ["--limit 128"])
        self.assertIn("persistent-resident-state-abi", targets["pulp_ita_mha"]["modes"])
        sidecar = targets["pulp_ita_mha"]["sidecar_gpu"]
        self.assertEqual(sidecar["sim_accel"], "sidecar-gpu")
        self.assertEqual(sidecar["option_shim_status"], "ready_for_template_shape")
        self.assertEqual(sidecar["requires"], ["--sim-accel-states", "--sim-accel-steps"])
        self.assertEqual(sidecar["ready_modes"], ["template"])
        self.assertIn("hybrid_sidecar_run", sidecar["ready_stage_names"])
        self.assertEqual(
            sidecar["not_ready_modes"]["resident-state-reuse"]["stage_names"],
            ["resident_state_reuse_workflow"],
        )
        self.assertEqual(
            sidecar["not_ready_modes"]["persistent-resident-state-abi"]["missing"],
            ["direct_verilator_resident_sidecar_handoff"],
        )
        self.assertEqual(sidecar["correctness_policy"], "coverage_output_equivalence")
        self.assertIn("readiness does not mean Verilator itself implements --sim-accel", sidecar["non_claims"])
        mobile_sidecar = targets["mobile_vit"]["sidecar_gpu"]
        self.assertEqual(mobile_sidecar["option_shim_status"], "not_ready_for_verilator_option_shim")
        self.assertIn("host preprocessing", mobile_sidecar["reason"])
        self.assertEqual(mobile_sidecar["stage_plan_status"], "planned_not_ready_for_verilator_option_shim")
        self.assertEqual(mobile_sidecar["stage_names"], ["host_preprocess", "rtl_sidecar_proxy_eval"])
        self.assertEqual(mobile_sidecar["missing"], ["direct_verilator_rtl_sidecar_handoff"])
        self.assertIn("--stage host_preprocess --emit-command", mobile_sidecar["inspect_stage_command"])
        self.assert_no_local_absolute_paths(result.stdout)

    def test_operator_tool_surface_documents_small_entrypoint_set(self) -> None:
        tool_surface = (REPO_ROOT / "docs/tool_surface.md").read_text(encoding="utf-8")
        option_doc = (REPO_ROOT / "docs/verilator_sidecar_option.md").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        results = (REPO_ROOT / "docs/results.md").read_text(encoding="utf-8")
        status = (REPO_ROOT / "docs/status.md").read_text(encoding="utf-8")
        self.add_tools_to_path()
        from results_reproduction_manifest_sources import PUBLIC_PACK_SOURCE_PATHS

        for entrypoint in (
            "src/tools/run_hybrid_benchmark.py",
            "src/tools/run_hybrid_template.py",
            "src/tools/run_results_reproduction.py",
            "src/tools/gen_hybrid_config.py",
        ):
            self.assertIn(entrypoint, tool_surface)

        for helper_prefix in (
            "build_vl_gpu_*",
            "compare_vl_hybrid_*",
            "results_reproduction_*",
            "check_staged_large_files_*",
        ):
            self.assertIn(helper_prefix, tool_surface)

        self.assertIn("docs/tool_surface.md", readme)
        self.assertIn("docs/tool_surface.md", results)
        self.assertIn("docs/tool_surface.md", PUBLIC_PACK_SOURCE_PATHS)
        self.assertIn("docs/verilator_sidecar_option.md", readme)
        self.assertIn("docs/verilator_sidecar_option.md", results)
        self.assertIn("docs/verilator_sidecar_option.md", tool_surface)
        self.assertIn("docs/verilator_sidecar_option.md", PUBLIC_PACK_SOURCE_PATHS)
        self.assertIn("src/tools/verilator_sidecar_shim.py", PUBLIC_PACK_SOURCE_PATHS)
        self.assertIn("src/tools/verilator_sidecar_options.py", PUBLIC_PACK_SOURCE_PATHS)
        self.assertIn("src/tools/hybrid_benchmark_sidecar_plan.py", PUBLIC_PACK_SOURCE_PATHS)
        self.assertIn("verilator --sim-accel sidecar-gpu", option_doc)
        self.assertIn("--sim-accel-states", option_doc)
        self.assertIn("--sim-accel-steps", option_doc)
        self.assertIn("compact compatibility spelling", option_doc)
        self.assertIn("coverage_output_equivalence", option_doc)
        self.assertIn("coverage_output_equivalence", tool_surface)
        self.assertIn("handoff_contract", status)
        self.assertIn("handoff_contract", tool_surface)
        self.assertIn("host_preprocess", status)
        self.assertIn("resident_state_reuse_workflow", status)
        self.assertIn("persistent_resident_state_abi_workflow", tool_surface)

    def test_verilator_sidecar_option_mapping_is_shared_and_strict(self) -> None:
        self.add_tools_to_path()
        from verilator_sidecar_options import resolve_sidecar_shape

        self.assertEqual(
            resolve_sidecar_shape(
                shape=None,
                sim_accel_shape=None,
                sim_accel_states="64",
                sim_accel_steps="1",
            ),
            "64x1",
        )
        self.assertEqual(
            resolve_sidecar_shape(
                shape=None,
                sim_accel_shape="1x64",
                sim_accel_states=None,
                sim_accel_steps=None,
            ),
            "1x64",
        )
        with self.assertRaisesRegex(ValueError, "provided together"):
            resolve_sidecar_shape(
                shape=None,
                sim_accel_shape=None,
                sim_accel_states="64",
                sim_accel_steps=None,
            )
        with self.assertRaisesRegex(ValueError, "only one shape spelling"):
            resolve_sidecar_shape(
                shape="64x1",
                sim_accel_shape=None,
                sim_accel_states="64",
                sim_accel_steps="1",
            )

    def test_hybrid_benchmark_requires_target_without_list_targets(self) -> None:
        result = self.run_python_tool("src/tools/run_hybrid_benchmark.py", "--dry-run", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("target is required unless --list-targets is used", result.stderr)

    def test_hybrid_benchmark_help_exposes_estimate_only_preview(self) -> None:
        result = self.run_python_tool("src/tools/run_hybrid_benchmark.py", "--help")

        self.assertIn("--print-efficiency-estimate", result.stdout)
        self.assertIn("without executing commands", result.stdout)

    def test_target_first_can_print_efficiency_estimate_without_execution(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
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
        self.assertIn("target: paged_attention_kv_score", stdout)
        self.assertIn("shape: 64x1", stdout)
        self.assertIn("speedup_class: high", stdout)
        self.assertIn("coverage-output equivalence remains separate from performance", stdout)
        self.assertNotIn("verilator --cc", stdout)

    def test_target_first_efficiency_estimate_not_ready_keeps_shim_exit_code(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "mobile_vit",
            "--limit",
            "128",
            "--print-efficiency-estimate",
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        stdout = result.stdout
        self.assertIn("# efficiency_estimate", stdout)
        self.assertIn("target: mobile_vit", stdout)
        self.assertIn("limit: 128", stdout)
        self.assertIn("speedup_class: unknown", stdout)
        self.assertNotIn("schema_version", stdout)

    def test_target_first_print_efficiency_rejects_other_estimate_output_flags(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "paged_attention_kv_score",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--print-efficiency-estimate",
            "--estimate-efficiency-json",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--print-efficiency-estimate cannot be combined", result.stderr)

    def test_explicit_sim_accel_dry_run_prints_verilator_option_preview(self) -> None:
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
        self.assertIn("# verilator_option_preview", stdout)
        self.assertIn("command_emitted: true", stdout)
        self.assertIn("command:\nverilator --cc", stdout)
        self.assertIn("--sim-accel sidecar-gpu", stdout)
        self.assertIn("correctness_policy: coverage_output_equivalence", stdout)
        self.assertIn("+ python3 src/tools/run_hybrid_template.py", stdout)
        self.assertIn("# efficiency_estimate", stdout)

    def test_explicit_sim_accel_dry_run_keeps_not_ready_preview_non_fatal(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "mobile_vit",
            "--sim-accel",
            "sidecar-gpu",
            "--limit",
            "128",
            "--dry-run",
        )

        stdout = result.stdout
        self.assertIn("# verilator_option_preview", stdout)
        self.assertIn("status: not_ready_for_verilator_option_shim", stdout)
        self.assertIn("command_emitted: false", stdout)
        self.assertIn("direct_verilator_rtl_sidecar_handoff", stdout)
        self.assertIn("mobile_vit_imagenet_manifest.py", stdout)
        self.assertIn("# efficiency_estimate", stdout)

    def test_preflight_includes_target_first_verilator_option_preview(self) -> None:
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
        preview = report["verilator_option_preview"]
        self.assertEqual(preview["status"], "planned")
        self.assertEqual(preview["exit_code"], 0)
        self.assertTrue(preview["command_emitted"])
        self.assertIn("--sim-accel sidecar-gpu", preview["command"])
        self.assertIn("--sim-accel-states 64", preview["command"])
        self.assertEqual(preview["correctness_policy"], "coverage_output_equivalence")
        self.assertEqual(preview["handoff_contract"]["compare"]["acceptance_policy"], "coverage_output_equivalence")
        self.assertIn("preview does not execute commands", preview["non_claims"])

    def test_summary_includes_not_ready_verilator_option_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "mobile_vit_summary.json"
            self.run_python_tool(
                "src/tools/run_hybrid_benchmark.py",
                "mobile_vit",
                "--limit",
                "128",
                "--dry-run",
                "--summary-out",
                str(summary_path),
            )

            report = json.loads(summary_path.read_text(encoding="utf-8"))

        preview = report["verilator_option_preview"]
        self.assertEqual(preview["status"], "not_ready_for_verilator_option_shim")
        self.assertEqual(preview["exit_code"], 2)
        self.assertFalse(preview["command_emitted"])
        self.assertEqual(preview["missing"], ["direct_verilator_rtl_sidecar_handoff"])
        self.assertNotIn("command", preview)

    def test_paged_attention_kv_cache_scale_up_measurement_dry_run_commands_pass(self) -> None:
        dry_run_commands = [
            hybrid_benchmark_command("pulp_paged_kv_cache_large", "--shape", "256x1", "--dry-run"),
            hybrid_benchmark_command("paged_kv_cache_large", "--shape", "1x64", "--dry-run"),
            hybrid_benchmark_command("paged_attention_kv_score", "--shape", "64x1", "--dry-run"),
            hybrid_benchmark_command("paged_attention_kv_score", "--shape", "1x64", "--dry-run"),
        ]

        for command in dry_run_commands:
            with self.subTest(command=" ".join(command)):
                self.assert_dry_run_command_passes(command)

    def test_public_pack_reproduction_smoke_dry_run_commands_pass(self) -> None:
        smoke_commands = [
            results_reproduction_command("--dry-run"),
            results_reproduction_command("--public-pack-archive", "--dry-run"),
            hybrid_benchmark_command("pulp_ita_mha", "--shape", "64x1", "--dry-run"),
            hybrid_benchmark_command("paged_attention_kv_score", "--shape", "64x1", "--dry-run"),
            hybrid_benchmark_command(
                "pulp_ita_mha",
                "--shape",
                "16x64",
                "--mode",
                "persistent-resident-state-abi",
                "--dry-run",
            ),
            results_reproduction_command(
                "--persistent-resident-state-abi-shape-phase-sweep",
                "--dry-run",
            ),
            hybrid_benchmark_command("pulp_paged_kv_cache_large", "--shape", "256x1", "--dry-run"),
            hybrid_benchmark_command("mobile_vit", "--limit", "128", "--dry-run"),
        ]

        for command in smoke_commands:
            with self.subTest(command=" ".join(command)):
                self.assert_dry_run_command_passes(command)

    def test_config_generation_validation_breadth_dry_run_commands_pass(self) -> None:
        dry_run_commands = [
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/nvdla_cmac_core_mac.json --shape 1x1 --dry-run",
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_dotp.json --shape 1x1 --dry-run",
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_softmax_top.json --shape 1x1 --dry-run",
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x1 --dry-run",
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_attention_kv_score.json --shape 1x1 --dry-run",
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_kv_cache_large.json --shape 1x1 --dry-run",
        ]

        for command in dry_run_commands:
            with self.subTest(command=command):
                result = self.run_python_tool(*command.split()[1:])
                self.assertIn("python3 src/tools/build_host_probe.py", result.stdout)
                self.assertIn("--acceptance-policy coverage_output_equivalence", result.stdout)
                self.assertNotIn("make -C src/hybrid", result.stdout)
                self.assert_no_local_absolute_paths(result.stdout)

    def test_config_generation_validation_additional_targets_dry_run_commands_pass(self) -> None:
        dry_run_commands = [
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/nvdla_cmac_a2cacc.json --shape 1x1 --dry-run",
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/prim_count.json --shape 1x1 --dry-run",
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/prim_secded_inv_39_32_enc.json --shape 1x1 --dry-run",
        ]

        for command in dry_run_commands:
            with self.subTest(command=command):
                result = self.run_python_tool(*command.split()[1:])
                self.assertIn("--acceptance-policy coverage_output_equivalence", result.stdout)
                self.assertIn("--shape 1x1", command)
                self.assert_no_local_absolute_paths(result.stdout)

    def test_public_pack_archive_dry_run_prints_include_exclude_plan(self) -> None:
        result = self.run_python_tool("src/tools/run_results_reproduction.py", "--public-pack-archive", "--dry-run")

        stdout = result.stdout
        self.assertIn("# public_pack_archive_ready", stdout)
        self.assertIn("# dry-run only: no archive is created", stdout)
        self.add_tools_to_path()
        from results_reproduction import PUBLIC_PACK_ARCHIVE_PATHS

        for path in PUBLIC_PACK_REPRESENTATIVE_PATHS:
            self.assertIn(path, PUBLIC_PACK_ARCHIVE_PATHS)

        for path in PUBLIC_PACK_ARCHIVE_PATHS:
            self.assertIn(f"include: {path}", stdout)
        self.assertIn("exclude: artifacts/", stdout)
        self.assertIn("exclude: reports/* except listed evidence snapshots", stdout)
        self.assertIn("tar -czf <generated-output>/public-benchmark-pack.tgz <listed paths>", stdout)
        include_lines = [line for line in stdout.splitlines() if line.startswith("include: ")]
        for excluded in ("include: .gitmodules", "include: third_party/", "include: overlays/"):
            self.assertNotIn(excluded, include_lines)
        self.assert_no_local_absolute_paths(stdout)
        self.assert_no_local_absolute_paths((REPO_ROOT / "src" / "tools" / "results_reproduction.py").read_text(encoding="utf-8"))

        result = self.run_python_tool("src/tools/run_results_reproduction.py", "--public-pack-archive", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dry-run only", result.stderr)

    def test_results_reproduction_format_command_sanitizes_local_absolute_paths(self) -> None:
        self.add_tools_to_path()
        from results_reproduction import ReproductionCommand, format_command

        command = ReproductionCommand(
            ["python3", "/home/example/private/run.py", "--out", "/tmp/private/out.json"],
            stdout=Path("/var/private/stdout.txt"),
        )

        rendered = format_command(command)
        self.assertNotIn("/home/example", rendered)
        self.assertNotIn("/tmp/private", rendered)
        self.assertNotIn("/var/private", rendered)
        self.assertIn("<local-absolute-path>", rendered)
if __name__ == "__main__":
    unittest.main()
