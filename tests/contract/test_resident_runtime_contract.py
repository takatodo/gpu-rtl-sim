#!/usr/bin/env python3
"""Contract checks for the compact active hybrid-runtime surface."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SELECTION = REPO_ROOT / "config" / "selection.json"
TARGETS = REPO_ROOT / "config" / "targets.json"
CONFIG_README = REPO_ROOT / "config" / "README.md"
ARCHIVED_TARGETS = REPO_ROOT / "config" / "archived_targets.json"
SCALING_GATES_README = REPO_ROOT / "config" / "scaling_gates" / "README.md"
RECORDS_README = REPO_ROOT / "records" / "README.md"
CONFIG_MINIMAL_SURFACE_AUDIT = (
    REPO_ROOT / "records" / "scaling_gates" / "config_minimal_surface_completion_audit.json"
)
README = REPO_ROOT / "README.md"
STATUS = REPO_ROOT / "docs" / "status.md"
ROADMAP = REPO_ROOT / "docs" / "roadmap.md"
GITIGNORE = REPO_ROOT / ".gitignore"
GITMODULES = REPO_ROOT / ".gitmodules"
COMPARE_VL_HYBRID_MODES = REPO_ROOT / "src" / "tools" / "compare_vl_hybrid_modes.py"
TLUL_COVERAGE_OUTPUT_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "tlul_coverage_output_equivalence.json"
)
TLUL_FIFO_COVERAGE_MANIFEST = (
    REPO_ROOT
    / "overlays"
    / "rtlmeter"
    / "designs"
    / "OpenTitan"
    / "tests"
    / "tlul_fifo_sync_coverage_regions.json"
)
TLUL_SLICE_HOST_PROBE = REPO_ROOT / "src" / "hybrid" / "tlul_slice_host_probe.cpp"
TLUL_CPU_BASELINE_RUNNER = REPO_ROOT / "src" / "tools" / "run_tlul_fifo_sync_cpu_baseline.py"
RUN_VL_HYBRID_PY = REPO_ROOT / "src" / "tools" / "run_vl_hybrid.py"
RUN_VL_HYBRID_C = REPO_ROOT / "src" / "hybrid" / "run_vl_hybrid.c"


class ReducedActiveSurfaceContractTest(unittest.TestCase):
    def _load_tool_module(self, module_name: str):
        tools_dir = str(REPO_ROOT / "src" / "tools")
        added = False
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
            added = True
        try:
            return importlib.import_module(module_name)
        finally:
            if added:
                sys.path.remove(tools_dir)

    def test_selection_is_compact_current_state(self) -> None:
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))

        self.assertLess(SELECTION.stat().st_size, 32_000)
        self.assertEqual(selection["top_level_goal"], "modern_llm_serving_rtl_hybrid_conditions")
        self.assertEqual(
            selection["current_priority"],
            "define_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate",
        )
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["persistent_resident_state_abi_repeat_median_gate"],
            "config/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["persistent_resident_state_abi_repeat_median_summary"],
            "reports/persistent_resident_state_abi_repeat_median_summary.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["next_goal_selection_after_persistent_resident_repeat_median_gate"],
            "config/scaling_gates/next_goal_selection_after_persistent_resident_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["public_results_packaging_refresh_after_persistent_resident_repeat_median_gate"],
            "config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["public_benchmark_pack_externalization_completion_gate"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["next_measurement_selection_after_public_benchmark_pack_externalization_gate"],
            "config/scaling_gates/next_measurement_selection_after_public_benchmark_pack_externalization_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_scale_up_measurement_gate"],
            "config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_scale_up_measurement_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_timing_summary_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_timing_summary_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json",
        )
        self.assertEqual(selection["candidate_targets"], [])
        self.assertEqual(selection["active_scope"]["candidate_targets"], [])
        self.assertEqual(
            selection["repository_cleanup"]["selection_policy"],
            "current_state_only; historical gate details live in records/scaling_gates with config/scaling_gates as a compatibility link; generated outputs are reproducible under reports and artifacts but are not source of truth",
        )
        historical_prefixes = (
            "next_source_backed_gate_after_",
            "first_primitive_",
            "four_seed_",
            "ninety_",
        )
        self.assertFalse(
            any(key.startswith(historical_prefixes) for key in selection),
            "selection.json should not store historical gate-by-gate state",
        )

    def test_targets_registry_matches_selection_scope(self) -> None:
        targets = json.loads(TARGETS.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))

        active_names = [target["name"] for target in targets["active_targets"]]
        self.assertEqual(len(active_names), selection["active_scope"]["active_target_count"])
        self.assertEqual(set(active_names), set(selection["active_scope"]["targets"]))
        self.assertEqual(targets["candidate_targets"], [])
        self.assertIn("tlul_fifo_sync", active_names)
        self.assertIn("pulp_ita_mha_first_hybrid_benchmark_summary.json", json.dumps(selection))
        self.assertIn("pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json", json.dumps(selection))

    def test_retired_cpu_seed_templates_are_not_active_surface(self) -> None:
        targets = json.loads(TARGETS.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        archived = json.loads(ARCHIVED_TARGETS.read_text(encoding="utf-8"))
        retired_templates = {
            "config/slice_launch_templates/veer_el2.json",
            "config/slice_launch_templates/xuantie_e902.json",
        }
        retired_names = {"veer_el2", "xuantie_e902"}

        self.assertFalse((REPO_ROOT / "config" / "slice_launch_templates" / "veer_el2.json").exists())
        self.assertFalse((REPO_ROOT / "config" / "slice_launch_templates" / "xuantie_e902.json").exists())

        active_text = json.dumps(
            {
                "targets": targets,
                "selection_active_scope": selection["active_scope"],
                "selection_candidate_targets": selection["candidate_targets"],
            }
        )
        for retired_template in retired_templates:
            self.assertNotIn(retired_template, active_text)
        for retired_name in retired_names:
            self.assertNotIn(f'"name": "{retired_name}"', active_text)
            self.assertNotIn(f'"{retired_name}"', json.dumps(selection["active_scope"]["targets"]))

        archived_text = json.dumps(archived)
        for retired_template in retired_templates:
            self.assertIn(retired_template, archived_text)
        for retired_name in retired_names:
            self.assertIn(f'"name": "{retired_name}"', archived_text)

    def test_active_target_references_resolve_from_checkout(self) -> None:
        targets = json.loads(TARGETS.read_text(encoding="utf-8"))
        reference_keys = (
            "launch_template_path",
            "coverage_manifest_path",
            "coverage_output_gate_path",
            "source_gate_path",
            "upstream_module_path",
        )
        missing = []

        for target in targets["active_targets"]:
            for key in reference_keys:
                reference = target.get(key)
                if reference and not (REPO_ROOT / reference).exists():
                    missing.append(f"{target['name']}:{key}:{reference}")
            for reference in target.get("depth_candidate_gates", []):
                if not (REPO_ROOT / reference).exists():
                    missing.append(f"{target['name']}:depth_candidate_gates:{reference}")

        self.assertEqual(missing, [])

    def test_active_launch_templates_reference_only_present_source_paths(self) -> None:
        targets = json.loads(TARGETS.read_text(encoding="utf-8"))
        tracked_paths = set(
            subprocess.check_output(
                ["git", "ls-files"],
                cwd=REPO_ROOT,
                text=True,
            ).splitlines()
        )
        source_prefixes = (
            "config/scaling_gates/",
            "config/slice_launch_templates/",
            "overlays/rtlmeter/",
            "third_party/rtlmeter/",
        )
        missing = []
        untracked = []
        absolute_paths = []

        def collect_source_paths(value):
            if isinstance(value, dict):
                for child in value.values():
                    yield from collect_source_paths(child)
            elif isinstance(value, list):
                for child in value:
                    yield from collect_source_paths(child)
            elif isinstance(value, str):
                if value.startswith(source_prefixes):
                    yield value
                elif value.startswith("/"):
                    absolute_paths.append(value)

        template_paths = {
            target["launch_template_path"]
            for target in targets["active_targets"]
            if target.get("launch_template_path")
        }
        for template_path in sorted(template_paths):
            template = json.loads((REPO_ROOT / template_path).read_text(encoding="utf-8"))
            for reference in collect_source_paths(template):
                if not (REPO_ROOT / reference).exists():
                    missing.append(f"{template_path}:{reference}")
                if reference.startswith(("config/slice_launch_templates/", "overlays/rtlmeter/")):
                    if reference not in tracked_paths:
                        untracked.append(f"{template_path}:{reference}")

        self.assertEqual(missing, [])
        self.assertEqual(untracked, [])
        self.assertEqual(absolute_paths, [])

    def test_canonical_third_party_submodule_boundaries_are_explicit(self) -> None:
        gitmodules = GITMODULES.read_text(encoding="utf-8")

        self.assertIn('[submodule "third_party/rtlmeter"]', gitmodules)
        self.assertIn("path = third_party/rtlmeter", gitmodules)
        self.assertIn("url = https://github.com/verilator/rtlmeter.git", gitmodules)
        self.assertIn('[submodule "third_party/ITA"]', gitmodules)
        self.assertIn("path = third_party/ITA", gitmodules)
        self.assertIn("url = https://github.com/pulp-platform/ITA.git", gitmodules)
        self.assertIn('[submodule "third_party/common_cells"]', gitmodules)
        self.assertIn("path = third_party/common_cells", gitmodules)
        self.assertIn("url = https://github.com/pulp-platform/common_cells.git", gitmodules)
        self.assertNotIn("third_party/ibex", gitmodules)

    def test_generated_output_dirs_are_not_source_of_truth(self) -> None:
        ignore = GITIGNORE.read_text(encoding="utf-8")
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertIn("/artifacts/**", ignore)
        self.assertIn("/reports/**", ignore)
        self.assertIn("Generated outputs are not source of truth", combined)
        self.assertIn("Historical gate details live under `records/scaling_gates/`", combined)
        self.assertIn("Generated outputs are reproducible under `reports/` and `artifacts/`", combined)
        for generated_dir in (REPO_ROOT / "reports", REPO_ROOT / "artifacts"):
            self.assertTrue(generated_dir.exists())

    def test_config_directory_has_current_state_map_and_gate_policy(self) -> None:
        config_readme = CONFIG_README.read_text(encoding="utf-8")
        gates_readme = SCALING_GATES_README.read_text(encoding="utf-8")
        records_readme = RECORDS_README.read_text(encoding="utf-8")
        combined_docs = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertIn("`config/` is source-of-truth configuration, not generated output.", config_readme)
        self.assertIn("selection.json", config_readme)
        self.assertIn("targets.json", config_readme)
        self.assertIn("slice_launch_templates/", config_readme)
        self.assertIn("scaling_gates/", config_readme)
        self.assertIn("records/scaling_gates/", config_readme)
        self.assertIn("Do not put generated reports", config_readme)

        self.assertTrue((REPO_ROOT / "config" / "scaling_gates").is_symlink())
        self.assertIn("evidence ledger", gates_readme)
        self.assertIn("current_priority_source_artifact", gates_readme)
        self.assertIn("public_results_packaging_gate.json", gates_readme)
        self.assertIn("public_benchmark_pack_goal_completion_audit.json", gates_readme)
        self.assertIn("Keep generated measurements in `reports/`", gates_readme)
        self.assertIn("`config/scaling_gates` is a symlink", records_readme)

        self.assertIn("config/README.md", combined_docs)
        self.assertIn("records/scaling_gates", combined_docs)
        self.assertIn("config_minimal_surface_completion_audit.json", combined_docs)

        config_file_count = len([path for path in (REPO_ROOT / "config").glob("**/*") if path.is_file()])
        self.assertLess(config_file_count, 200)

    def test_config_minimal_surface_audit_records_counts_and_external_records(self) -> None:
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        audit = json.loads(CONFIG_MINIMAL_SURFACE_AUDIT.read_text(encoding="utf-8"))

        self.assertEqual(
            audit["status"],
            "complete_config_minimal_surface_with_external_records_and_generated_outputs_removed",
        )
        self.assertTrue(audit["completion_decision"]["achieved"])
        self.assertEqual(audit["measured_state"]["config_file_count_after_cleanup"], 146)
        self.assertEqual(audit["measured_state"]["records_scaling_gate_json_count"], 632)
        self.assertEqual(audit["measured_state"]["generated_output_non_gitignore_file_count_after_cleanup"], 0)
        self.assertEqual(audit["measured_state"]["reports_non_gitignore_file_count_after_cleanup"], 0)
        self.assertEqual(audit["measured_state"]["artifacts_non_gitignore_file_count_after_cleanup"], 0)
        self.assertTrue(audit["measured_state"]["config_scaling_gates_is_symlink"])
        self.assertEqual(audit["measured_state"]["config_scaling_gates_link_target"], "../records/scaling_gates")
        self.assertEqual(
            selection["repository_cleanup"]["config_minimal_surface_audit"],
            "records/scaling_gates/config_minimal_surface_completion_audit.json",
        )
        self.assertEqual(selection["repository_cleanup"]["config_file_count_after_cleanup"], 146)
        self.assertEqual(selection["repository_cleanup"]["records_scaling_gate_json_count"], 632)
        self.assertIn(
            "reports and artifacts may contain local generated evidence",
            selection["repository_cleanup"]["generated_output_policy"],
        )

        checklist = {entry["requirement"]: entry for entry in audit["prompt_to_artifact_checklist"]}
        for requirement in (
            "configディレクトリを必要最低限に絞る",
            "履歴 gate を active config surface から外す",
            "既存パス互換性を保つ",
            "生成物は別で管理する",
            "生成物は削除する",
            "境界を文書化する",
            "テストで固定する",
        ):
            self.assertEqual(checklist[requirement]["status"], "satisfied")

    def test_scaling_validation_parses_gpu_event_timing_metrics(self) -> None:
        runner = self._load_tool_module("run_tlul_fifo_sync_scaling_validation")
        metrics = runner._parse_timing_metrics(
            "\n".join(
                [
                    "gpu_kernel_time_ms: total=12.345678  per_launch=0.385802  (CUDA events, default stream)",
                    "gpu_kernel_time: per_state=0.753 us  (per_launch / nstates)",
                    "gpu_kernel_time_repeat_ms: count=3 min=11.000000 median=12.000000 max=13.000000 samples=13.000000,11.000000,12.000000",
                    "wall_time_ms: 14.321  (host; one GPU sync unless RUN_VL_HYBRID_SYNC_EACH_STEP=1)",
                ]
            )
        )

        self.assertEqual(metrics["gpu_kernel_time_ms_total"], 12.345678)
        self.assertEqual(metrics["gpu_kernel_time_ms_per_launch"], 0.385802)
        self.assertEqual(metrics["gpu_kernel_time_us_per_state"], 0.753)
        self.assertEqual(metrics["host_wall_time_ms"], 14.321)
        self.assertEqual(metrics["gpu_kernel_time_repeat_count"], 3)
        self.assertEqual(metrics["gpu_kernel_time_ms_total_samples"], [13.0, 11.0, 12.0])
        self.assertTrue(runner._format_gpu_event_timing(metrics)["available"])
        self.assertTrue(runner._format_gpu_event_timing_repeat(metrics)["available"])

    def test_run_vl_hybrid_rejects_unsafe_nonflat_syms_state_before_launch(self) -> None:
        runner = self._load_tool_module("run_vl_hybrid")
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp)
            (mdir / "vl_batch_gpu_opt.ll").write_text(
                "\n".join(
                    [
                        "%class.Vfoo__Syms = type { i8 }",
                        "  %p = getelementptr inbounds %class.Vfoo__Syms, ptr %symsp, i64 0, i32 5",
                    ]
                ),
                encoding="utf-8",
            )
            unsupported = runner._detect_unsupported_nonflat_syms_state(mdir)

        self.assertIsNotNone(unsupported)
        self.assertEqual(unsupported["reason"], "unsupported_nonflat_verilator_syms_state")

    def test_run_vl_hybrid_allows_declared_syms_state_image(self) -> None:
        runner = self._load_tool_module("run_vl_hybrid")
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp)
            (mdir / "vl_batch_gpu_opt.ll").write_text(
                "\n".join(
                    [
                        "%class.Vfoo__Syms = type { i8 }",
                        "  %p = getelementptr inbounds %class.Vfoo__Syms, ptr %symsp, i64 0, i32 5",
                    ]
                ),
                encoding="utf-8",
            )
            unsupported = runner._detect_unsupported_nonflat_syms_state(
                mdir,
                {
                    "hierarchy_state": {
                        "state_image_kind": "verilator_syms_image",
                        "unsafe_syms_gep_covered_by_state_image": True,
                        "prelaunch_rejection_required": False,
                    }
                },
            )

        self.assertIsNone(unsupported)

    def test_run_vl_hybrid_sanitizes_root_fields_at_syms_root_offset(self) -> None:
        runner = self._load_tool_module("run_vl_hybrid")
        sanitized, applied = runner._sanitize_host_only_internals_at_root_offset(
            b"AA" + b"\x01" + b"BBBB",
            [{"name": "__VstlFirstIteration", "offset": 0, "size": 1}],
            root_offset=2,
        )

        self.assertEqual(sanitized, b"AA" + b"\x00" + b"BBBB")
        self.assertEqual(applied[0]["offset"], 2)
        self.assertEqual(applied[0]["sanitized_start"], 2)

    def test_build_vl_gpu_records_hierarchy_state_metadata(self) -> None:
        builder = self._load_tool_module("build_vl_gpu")
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp)
            (mdir / "vl_batch_gpu_opt.ll").write_text(
                "\n".join(
                    [
                        "declare void @Vfoo__SymsC1(ptr noundef nonnull dereferenceable(2048))",
                        "  %p = getelementptr inbounds %class.Vfoo__Syms, ptr %symsp, i64 0, i32 5",
                        '!7 = !{!"_ZTS10Vfoo__Syms", !1, i64 0, !2, i64 64, !3, i64 576}',
                    ]
                ),
                encoding="utf-8",
            )
            metadata = builder.detect_hierarchy_state_metadata(mdir, 512)

        self.assertEqual(metadata["state_image_kind"], "root_image")
        self.assertEqual(metadata["syms_storage_size"], 2048)
        self.assertEqual(metadata["root_offset_in_syms"], 64)
        self.assertTrue(metadata["prelaunch_rejection_required"])

    def test_compare_tool_keeps_coverage_output_policy(self) -> None:
        text = COMPARE_VL_HYBRID_MODES.read_text(encoding="utf-8")
        self.assertIn("coverage_output_equivalence", text)
        self.assertIn("--coverage-output-gate", text)
        self.assertIn("--coverage-output-target", text)

        module = self._load_tool_module("compare_vl_hybrid_modes")
        gate = json.loads(TLUL_COVERAGE_OUTPUT_GATE.read_text(encoding="utf-8"))
        words = module.derive_strict_output_field_names(gate)
        self.assertEqual(len(words), 29)
        self.assertIn("real_toggle_subset_word17_o", words)
        self.assertIn("toggle_bitmap_word2_o", words)

        manifest = json.loads(TLUL_FIFO_COVERAGE_MANIFEST.read_text(encoding="utf-8"))
        validation = module.validate_coverage_output_manifest(manifest)
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["covered_word_count"], 18)

    def test_cpu_depth_dump_contract_is_wired(self) -> None:
        probe = TLUL_SLICE_HOST_PROBE.read_text(encoding="utf-8")
        runner = TLUL_CPU_BASELINE_RUNNER.read_text(encoding="utf-8")

        self.assertIn("--repeat-state-out", probe)
        self.assertIn("append_state", probe)
        self.assertIn("repeat_state_bytes", probe)
        self.assertIn("--repeat-state-out", runner)
        self.assertIn("cpu_final_state_dump_contract", runner)
        self.assertIn("concat_root_storage_by_state", runner)

    def test_persistent_resident_state_abi_runtime_surface_is_wired_as_probe_only(self) -> None:
        wrapper = RUN_VL_HYBRID_PY.read_text(encoding="utf-8")
        runner = RUN_VL_HYBRID_C.read_text(encoding="utf-8")

        self.assertIn("--persistent-resident-state-abi-handle", wrapper)
        self.assertIn("--persistent-resident-state-abi-phase", wrapper)
        self.assertIn("RUN_VL_HYBRID_PERSISTENT_RESIDENT_STATE_HANDLE", wrapper)
        self.assertIn("persistent resident state ABI phases after 1 must not use --init-state", wrapper)
        self.assertIn("requires --resident-steps", wrapper)

        self.assertIn("RUN_VL_HYBRID_PERSISTENT_RESIDENT_STATE_HANDLE", runner)
        self.assertIn("RUN_VL_HYBRID_PERSISTENT_RESIDENT_STATE_PHASE", runner)
        self.assertIn("probe_surface_phase1_only", runner)
        self.assertIn("refusing to fall back to a previous phase", runner)
        self.assertIn("persistent_resident_state_abi: handle=%s phase=%u", runner)

    def test_docs_record_current_nn_and_mobile_vit_evidence(self) -> None:
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        for token in [
            "modern_llm_serving_rtl_hybrid_conditions",
            "neural_network_rtl_paged_kv_cache_large_scaleup_gate.json",
            "neural_network_rtl_paged_kv_cache_large_review_gate.json",
            "neural_network_rtl_full_ita_mha_dependency_audit_gate.json",
            "neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json",
            "neural_network_rtl_full_ita_mha_larger_paged_kv_goal_review_gate.json",
            "neural_network_rtl_paged_attention_kv_score_harness_gate.json",
            "full_ita_mha_larger_paged_attention_kv_goal_completion_audit.json",
            "modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json",
            "public_results_packaging_gate.json",
            "one_command_reproduction_flow_gate.json",
            "repeat_median_results_reproduction_gate.json",
            "resident_execution_optimization_next_gate.json",
            "resident_batch_sweep_measurement_gate.json",
            "resident_batch_sweep_review_gate.json",
            "resident_state_reuse_experiment_gate.json",
            "resident_state_reuse_measurement_gate.json",
            "resident_state_reuse_review_gate.json",
            "persistent_resident_state_abi_probe_gate.json",
            "persistent_resident_state_abi_probe_implementation_gate.json",
            "persistent_resident_device_handle_storage_gate.json",
            "persistent_resident_device_handle_storage_review_gate.json",
            "docs/results.md",
            "src/tools/run_results_reproduction.py",
            "reports/results_reproduction_median_summary.json",
            "reports/resident_batch_sweep_summary.json",
            "reports/resident_state_reuse_experiment_summary.json",
            "reports/persistent_resident_state_abi_probe_summary.json",
            "reports/pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json",
            "reports/pulp_ita_mha_first_hybrid_benchmark_summary.json",
            "reports/pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json",
            "reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json",
            "reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json",
            "reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json",
            "pulp_paged_kv_cache_large_host_probe",
            "overlays/ITA/src/pulp_paged_kv_cache_large_gpu_cov_tb.sv",
            "tc_sram",
            "mobile_vit_cpu_kick_imagenet_accuracy",
            "mobile_vit_cpu_kick_rtl_hybrid_boundary",
            "apple/mobilevit-small",
            "complete_full_imagenet_validation_cpu_kick_accuracy_measured",
            "top-1 0.77022",
            "mobile_vit_cpu_kick_rtl_proxy_host_probe",
            "phase_12_mobile_vit_cpu_kick_rtl_hybrid_boundary",
            "phase_11_mobile_vit_cpu_kick_imagenet_accuracy",
            "select_mobile_vit_model_and_reference_eval_source: done",
            "define_mobile_vit_cpu_kick_control_contract: done",
            "define_mobile_vit_accuracy_metric_contract: done",
            "define_mobile_vit_reference_inference_contract: done",
            "define_mobile_vit_imagenet_manifest_builder_contract: done",
        ]:
            self.assertIn(token, combined)


if __name__ == "__main__":
    unittest.main()
