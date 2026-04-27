#!/usr/bin/env python3
"""Contract checks for the explicit resident GPU runtime boundary."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_VL_HYBRID = REPO_ROOT / "src" / "tools" / "run_vl_hybrid.py"
GPU_SCALING_RUNNER = REPO_ROOT / "src" / "tools" / "run_tlul_fifo_sync_scaling_validation.py"
CPU_BASELINE_RUNNER = REPO_ROOT / "src" / "tools" / "run_tlul_fifo_sync_cpu_baseline.py"
NAMED_PATCH_LOWERING = REPO_ROOT / "src" / "tools" / "named_patch_lowering.py"
RESIDENT_GATE = REPO_ROOT / "config" / "scaling_gates" / "xuantie_e902_memory_resident_workload.json"
VEER_EL2_RESIDENT_GATE = REPO_ROOT / "config" / "scaling_gates" / "veer_el2_resident_workload.json"
VEER_EL2_CPU_GATE = REPO_ROOT / "config" / "scaling_gates" / "veer_el2_cpu_exact_loop_resident_workload.json"
VEER_EL2_LARGER_RESIDENT_GATE = REPO_ROOT / "config" / "scaling_gates" / "veer_el2_larger_resident_workload.json"
VEER_EL2_LARGER_CPU_GATE = REPO_ROOT / "config" / "scaling_gates" / "veer_el2_cpu_exact_loop_larger_resident_workload.json"
VEER_EL2_PATCH_GATE = REPO_ROOT / "config" / "scaling_gates" / "veer_el2_resident_patch_schedule.json"
VEER_EL2_PATCH_CPU_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "veer_el2_cpu_exact_loop_resident_patch_schedule.json"
)
VEER_EL2_TEMPLATE = REPO_ROOT / "config" / "slice_launch_templates" / "veer_el2.json"
VEER_EL2_ASSETS = REPO_ROOT / "third_party" / "rtlmeter" / "designs" / "VeeR-EL2"
RESIDENT_PATCH_SEMANTICS = REPO_ROOT / "config" / "resident_patch_script_semantics.json"
RESIDENT_PATCH_GATE = REPO_ROOT / "config" / "scaling_gates" / "tlul_fifo_sync_resident_patch_schedule.json"
RESIDENT_PATCH_CPU_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "tlul_fifo_sync_cpu_exact_loop_resident_patch_schedule.json"
)
TLUL_SINK_RESIDENT_PATCH_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "tlul_sink_resident_patch_schedule.json"
)
TLUL_SINK_RESIDENT_PATCH_CPU_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "tlul_sink_cpu_exact_loop_resident_patch_schedule.json"
)
XUANTIE_E902_PATCH_GATE = REPO_ROOT / "config" / "scaling_gates" / "xuantie_e902_resident_patch_schedule.json"
XUANTIE_E902_PATCH_CPU_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "xuantie_e902_cpu_exact_loop_resident_patch_schedule.json"
)
XUANTIE_E902_ROM_DELTA_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "xuantie_e902_rom_memory_delta_patch_schedule.json"
)
XUANTIE_E902_ROM_DELTA_CPU_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "xuantie_e902_cpu_exact_loop_rom_memory_delta_patch_schedule.json"
)
XUANTIE_E902_NAMED_ROM_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "xuantie_e902_named_rom_memory_mapping.json"
)
XUANTIE_E902_NAMED_ROM_CPU_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "xuantie_e902_cpu_exact_loop_named_rom_memory_mapping.json"
)
XUANTIE_E902_PROGRAM_IMAGE_DELTA_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "xuantie_e902_program_image_delta.json"
)
XUANTIE_E902_PROGRAM_IMAGE_DELTA_CPU_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "xuantie_e902_cpu_exact_loop_program_image_delta.json"
)
TARGETS = REPO_ROOT / "config" / "targets.json"
README = REPO_ROOT / "README.md"
RUNTIME = REPO_ROOT / "src" / "hybrid" / "run_vl_hybrid.c"


class ResidentRuntimeContractTest(unittest.TestCase):
    def test_resident_steps_rejects_host_patches_before_runtime_launch(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(RUN_VL_HYBRID),
                "--resident-steps",
                "--patch",
                "0:1",
                "--storage-size",
                "1",
                "--cubin",
                "/no/such/file",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("--resident-steps rejects --patch", completed.stderr)

    def test_resident_steps_allows_patch_script_past_argparse(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(RUN_VL_HYBRID),
                "--resident-steps",
                "--patch-script",
                "/no/such/script",
                "--storage-size",
                "1",
                "--cubin",
                "/no/such/file",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(completed.returncode, 2)
        self.assertIn("error: cubin not found", completed.stderr)

    def test_resident_gate_requires_resident_steps_for_every_run(self) -> None:
        gate = json.loads(RESIDENT_GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["gate"], "xuantie_e902_memory_resident_workload_scaling")
        self.assertGreater(len(gate["runs"]), 0)
        self.assertTrue(all(run.get("resident_steps") is True for run in gate["runs"]))

    def test_veer_el2_resident_gate_is_defined_before_asset_copy(self) -> None:
        gate = json.loads(VEER_EL2_RESIDENT_GATE.read_text(encoding="utf-8"))
        cpu_gate = json.loads(VEER_EL2_CPU_GATE.read_text(encoding="utf-8"))
        larger_gate = json.loads(VEER_EL2_LARGER_RESIDENT_GATE.read_text(encoding="utf-8"))
        larger_cpu_gate = json.loads(VEER_EL2_LARGER_CPU_GATE.read_text(encoding="utf-8"))
        targets = json.loads(TARGETS.read_text(encoding="utf-8"))
        self.assertEqual(gate["gate"], "veer_el2_resident_workload_scaling")
        self.assertEqual(gate["target"], "veer_el2")
        self.assertGreater(len(gate["runs"]), 0)
        self.assertTrue(all(run.get("resident_steps") is True for run in gate["runs"]))
        self.assertEqual(cpu_gate["source_gpu_gate"], "config/scaling_gates/veer_el2_resident_workload.json")
        self.assertEqual(larger_gate["gate"], "veer_el2_larger_resident_workload_scaling")
        self.assertTrue(all(run.get("resident_steps") is True for run in larger_gate["runs"]))
        self.assertEqual(
            larger_cpu_gate["source_gpu_gate"],
            "config/scaling_gates/veer_el2_larger_resident_workload.json",
        )
        veer_targets = [target for target in targets["active_targets"] if target["name"] == "veer_el2"]
        self.assertEqual(len(veer_targets), 1)
        self.assertIn(
            veer_targets[0]["status"],
            {
                "resident_gate_defined_before_asset_copy",
                "asset_boundary_materialized",
                "asset_boundary_validated",
                "verilator_obj_dir_generated",
                "gpu_cubin_built",
                "gpu_smoke_pass",
                "cpu_reference_contract_pass",
                "resident_workload_cpu_favorable",
                "larger_resident_workload_gpu_win",
                "packaged_larger_resident_boundary",
            },
        )

    def test_veer_el2_asset_boundary_is_materialized_without_work_history(self) -> None:
        template = json.loads(VEER_EL2_TEMPLATE.read_text(encoding="utf-8"))
        required_paths = [
            VEER_EL2_ASSETS / "descriptor.yaml",
            VEER_EL2_ASSETS / "LICENSE-VeeR-EL2",
            REPO_ROOT / template["runner_args_template"]["coverage_tb_path"],
            REPO_ROOT / template["enrollment"]["runtime_input_path"],
            VEER_EL2_ASSETS / "tests" / "veer_el2_coverage_regions.json",
            VEER_EL2_ASSETS / "tests" / "veer_el2_program_hex_target_config.json",
        ]
        for path in required_paths:
            self.assertTrue(path.exists(), str(path.relative_to(REPO_ROOT)))
        copied_files = [path.relative_to(VEER_EL2_ASSETS).parts[0] for path in VEER_EL2_ASSETS.rglob("*") if path.is_file()]
        self.assertNotIn("work", copied_files)
        self.assertNotIn("output", copied_files)

    def test_veer_el2_descriptor_referenced_assets_exist(self) -> None:
        descriptor = (VEER_EL2_ASSETS / "descriptor.yaml").read_text(encoding="utf-8")
        relative_paths = re.findall(r"- (src/[^\n ]+|tests/[^\n ]+)", descriptor)
        missing = [path for path in relative_paths if not (VEER_EL2_ASSETS / path).exists()]
        self.assertEqual(missing, [])

    def test_runtime_reports_resident_mode(self) -> None:
        runtime = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("RUN_VL_HYBRID_RESIDENT_STEPS", runtime)
        self.assertIn('printf("resident_mode: %s\\n"', runtime)

    def test_resident_patch_script_semantics_are_implemented_before_validation(self) -> None:
        semantics = json.loads(RESIDENT_PATCH_SEMANTICS.read_text(encoding="utf-8"))
        self.assertEqual(semantics["name"], "resident_patch_script_semantics")
        self.assertEqual(semantics["status"], "packaged_bounded_multi_seed_gpu_wins")
        self.assertEqual(
            semantics["accepted_semantics"]["per_step_host_copy"],
            "No cuMemcpyHtoD patch copy may occur inside the resident step loop.",
        )
        self.assertEqual(
            semantics["implementation_policy"]["phase_1"],
            "Keep rejecting direct --patch with --resident-steps because it is still a host argv per-step patch interface.",
        )
        self.assertEqual(semantics["next_action"], "define_xuantie_e902_program_image_delta_gate")

    def test_resident_patch_schedule_kernel_contract_is_present(self) -> None:
        runtime = RUNTIME.read_text(encoding="utf-8")
        generator = (REPO_ROOT / "src" / "tools" / "gen_vl_gpu_kernel.py").read_text(
            encoding="utf-8"
        )
        cpp_generator = (REPO_ROOT / "src" / "passes" / "vlgpugen.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("vl_apply_patch_schedule_gpu", generator)
        self.assertIn("vl_apply_patch_schedule_gpu", cpp_generator)
        self.assertIn("resident_patch_schedule", runtime)
        self.assertIn("cuMemcpyHtoD(resident_patch_schedule.d_offsets", runtime)
        self.assertIn("launch_resident_patch_step", runtime)

    def test_resident_patch_schedule_gate_is_defined(self) -> None:
        gate = json.loads(RESIDENT_PATCH_GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["gate"], "tlul_fifo_sync_resident_patch_schedule_validation")
        self.assertEqual(gate["target"], "tlul_fifo_sync")
        self.assertGreaterEqual(len(gate["runs"]), 2)
        self.assertTrue(all(run.get("resident_steps") is True for run in gate["runs"]))
        self.assertTrue(all("patch_script_lines" in run for run in gate["runs"]))

    def test_scaling_runner_supports_inline_patch_script_gate_lines(self) -> None:
        runner = (REPO_ROOT / "src" / "tools" / "run_tlul_fifo_sync_scaling_validation.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("patch_script_lines", runner)
        self.assertIn("_patch_script_logical_steps", runner)
        self.assertIn("--patch-script", runner)

    def test_cpu_patch_schedule_baseline_gate_is_defined(self) -> None:
        gate = json.loads(RESIDENT_PATCH_CPU_GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["gate"], "tlul_fifo_sync_cpu_exact_loop_resident_patch_schedule")
        self.assertEqual(
            gate["source_gpu_gate"], "config/scaling_gates/tlul_fifo_sync_resident_patch_schedule.json"
        )
        self.assertTrue(all("patch_script_lines" in run for run in gate["runs"]))
        runner = (REPO_ROOT / "src" / "tools" / "run_tlul_fifo_sync_cpu_baseline.py").read_text(
            encoding="utf-8"
        )
        probe = (REPO_ROOT / "src" / "hybrid" / "tlul_slice_host_probe.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("--patch-script", runner)
        self.assertIn("--patch-script", probe)

    def test_second_seed_patch_schedule_gates_are_defined(self) -> None:
        gpu_gate = json.loads(TLUL_SINK_RESIDENT_PATCH_GATE.read_text(encoding="utf-8"))
        cpu_gate = json.loads(TLUL_SINK_RESIDENT_PATCH_CPU_GATE.read_text(encoding="utf-8"))
        self.assertEqual(gpu_gate["gate"], "tlul_sink_resident_patch_schedule_validation")
        self.assertEqual(cpu_gate["gate"], "tlul_sink_cpu_exact_loop_resident_patch_schedule")
        self.assertEqual(cpu_gate["source_gpu_gate"], "config/scaling_gates/tlul_sink_resident_patch_schedule.json")
        self.assertTrue(all(run.get("resident_steps") is True for run in gpu_gate["runs"]))
        self.assertTrue(all("patch_script_lines" in run for run in gpu_gate["runs"]))
        self.assertTrue(all("patch_script_lines" in run for run in cpu_gate["runs"]))

    def test_veer_el2_resident_patch_schedule_gate_is_defined(self) -> None:
        gpu_gate = json.loads(VEER_EL2_PATCH_GATE.read_text(encoding="utf-8"))
        cpu_gate = json.loads(VEER_EL2_PATCH_CPU_GATE.read_text(encoding="utf-8"))
        self.assertEqual(gpu_gate["gate"], "veer_el2_resident_patch_schedule_validation")
        self.assertEqual(gpu_gate["target"], "veer_el2")
        self.assertEqual(cpu_gate["source_gpu_gate"], "config/scaling_gates/veer_el2_resident_patch_schedule.json")
        self.assertEqual(gpu_gate["artifacts"]["report"], "reports/veer_el2_resident_patch_schedule.json")
        self.assertEqual(
            cpu_gate["artifacts"]["report"],
            "reports/veer_el2_cpu_exact_loop_resident_patch_schedule.json",
        )
        self.assertTrue(all(run.get("resident_steps") is True for run in gpu_gate["runs"]))
        self.assertTrue(all("patch_script_lines" in run for run in gpu_gate["runs"]))
        self.assertTrue(all("patch_script_lines" in run for run in cpu_gate["runs"]))

    def test_xuantie_e902_resident_patch_schedule_gate_is_defined(self) -> None:
        gpu_gate = json.loads(XUANTIE_E902_PATCH_GATE.read_text(encoding="utf-8"))
        cpu_gate = json.loads(XUANTIE_E902_PATCH_CPU_GATE.read_text(encoding="utf-8"))
        self.assertEqual(gpu_gate["gate"], "xuantie_e902_resident_patch_schedule_validation")
        self.assertEqual(gpu_gate["target"], "xuantie_e902")
        self.assertEqual(
            cpu_gate["source_gpu_gate"],
            "config/scaling_gates/xuantie_e902_resident_patch_schedule.json",
        )
        self.assertEqual(gpu_gate["artifacts"]["report"], "reports/xuantie_e902_resident_patch_schedule.json")
        self.assertEqual(
            cpu_gate["artifacts"]["report"],
            "reports/xuantie_e902_cpu_exact_loop_resident_patch_schedule.json",
        )
        self.assertTrue(all(run.get("resident_steps") is True for run in gpu_gate["runs"]))
        self.assertTrue(all("patch_script_lines" in run for run in gpu_gate["runs"]))
        self.assertTrue(all("patch_script_lines" in run for run in cpu_gate["runs"]))

    def test_xuantie_e902_rom_memory_delta_patch_schedule_gate_is_defined(self) -> None:
        gpu_gate = json.loads(XUANTIE_E902_ROM_DELTA_GATE.read_text(encoding="utf-8"))
        cpu_gate = json.loads(XUANTIE_E902_ROM_DELTA_CPU_GATE.read_text(encoding="utf-8"))
        self.assertEqual(gpu_gate["gate"], "xuantie_e902_rom_memory_delta_patch_schedule_validation")
        self.assertEqual(gpu_gate["semantic"], "rom_or_memory_init_delta")
        self.assertEqual(cpu_gate["source_gpu_gate"], "config/scaling_gates/xuantie_e902_rom_memory_delta_patch_schedule.json")
        self.assertEqual(gpu_gate["artifacts"]["report"], "reports/xuantie_e902_rom_memory_delta_patch_schedule.json")
        self.assertEqual(
            cpu_gate["artifacts"]["report"],
            "reports/xuantie_e902_cpu_exact_loop_rom_memory_delta_patch_schedule.json",
        )
        self.assertIn("storage_mapping", gpu_gate["semantic_mapping"])
        self.assertTrue(all(run.get("resident_steps") is True for run in gpu_gate["runs"]))
        self.assertTrue(all("patch_script_lines" in run for run in gpu_gate["runs"]))
        self.assertTrue(all("patch_script_lines" in run for run in cpu_gate["runs"]))

    def test_xuantie_e902_named_rom_memory_mapping_gates_are_defined(self) -> None:
        gpu_gate = json.loads(XUANTIE_E902_NAMED_ROM_GATE.read_text(encoding="utf-8"))
        cpu_gate = json.loads(XUANTIE_E902_NAMED_ROM_CPU_GATE.read_text(encoding="utf-8"))
        self.assertEqual(gpu_gate["gate"], "xuantie_e902_named_rom_memory_mapping_validation")
        self.assertEqual(cpu_gate["source_gpu_gate"], "config/scaling_gates/xuantie_e902_named_rom_memory_mapping.json")
        self.assertEqual(gpu_gate["named_mapping"]["selected_family"], "iahb_instruction_memory")
        self.assertEqual(
            gpu_gate["named_mapping"]["testbench_initialization_lane_mapping"]["ram0"],
            "word[31:24]",
        )
        self.assertEqual(gpu_gate["runtime_support"]["status"], "named_mapping_lowering_required")
        self.assertTrue(gpu_gate["runtime_support"]["current_patch_script_lines_are_not_source_of_truth"])
        self.assertTrue(all("named_patch_delta_sequence" in run for run in gpu_gate["runs"]))
        self.assertTrue(all("named_patch_delta_sequence" in run for run in cpu_gate["runs"]))

    def test_named_rom_memory_mapping_lowering_is_wired_into_runners(self) -> None:
        lowering = NAMED_PATCH_LOWERING.read_text(encoding="utf-8")
        gpu_runner = GPU_SCALING_RUNNER.read_text(encoding="utf-8")
        cpu_runner = CPU_BASELINE_RUNNER.read_text(encoding="utf-8")
        self.assertIn("probe_root_layout", lowering)
        self.assertIn("named_patch_delta_sequence", lowering)
        self.assertIn("x_iahb_mem_ctrl__DOT__{lane}__DOT__mem", lowering)
        self.assertIn("_repeated_to_(?P<steps>\\d+)_logical_steps", lowering)
        self.assertIn("resolve_patch_script_lines", gpu_runner)
        self.assertIn("patch_script_lowering", gpu_runner)
        self.assertIn("resolve_patch_script_lines", cpu_runner)
        self.assertIn("patch_script_lowering", cpu_runner)

    def test_xuantie_e902_program_image_delta_gates_are_defined(self) -> None:
        gpu_gate = json.loads(XUANTIE_E902_PROGRAM_IMAGE_DELTA_GATE.read_text(encoding="utf-8"))
        cpu_gate = json.loads(XUANTIE_E902_PROGRAM_IMAGE_DELTA_CPU_GATE.read_text(encoding="utf-8"))
        self.assertEqual(gpu_gate["semantic"], "program_image_delta")
        self.assertEqual(gpu_gate["mapping_semantic"], "named_rom_memory_symbol_mapping")
        self.assertEqual(
            gpu_gate["program_image_delta_contract"]["program_image_source"],
            "case.pat loaded through mem_inst_temp",
        )
        self.assertEqual(
            cpu_gate["source_gpu_gate"],
            "config/scaling_gates/xuantie_e902_program_image_delta.json",
        )
        self.assertTrue(gpu_gate["runtime_support"]["current_patch_script_lines_are_not_source_of_truth"])
        self.assertTrue(all("named_patch_delta_sequence" in run for run in gpu_gate["runs"]))
        self.assertTrue(all("named_patch_delta_sequence" in run for run in cpu_gate["runs"]))
        self.assertIn("not ISA/program correctness", gpu_gate["correctness_policy"]["non_claims"])

    def test_selection_advances_after_two_seed_boundary_commit(self) -> None:
        selection = json.loads((REPO_ROOT / "config" / "selection.json").read_text(encoding="utf-8"))
        self.assertEqual(
            selection["current_priority"],
            "define_xuantie_e902_input_stream_delta_contract",
        )
        self.assertEqual(
            selection["resident_patch_schedule_boundary_status"],
            "committed_veer_el2_resident_patch_schedule_gpu_win",
        )
        self.assertEqual(
            selection["xuantie_e902_resident_patch_schedule_boundary_status"],
            "committed_xuantie_e902_resident_patch_schedule_gpu_win",
        )
        self.assertEqual(
            selection["next_patch_schedule_semantics_axis"],
            "application_like_patch_schedule_semantics",
        )
        self.assertEqual(
            selection["selected_application_like_patch_schedule_semantic"],
            "rom_or_memory_init_delta",
        )
        self.assertEqual(
            selection["rom_or_memory_init_delta_boundary_status"],
            "committed_xuantie_e902_rom_memory_delta_patch_schedule_gpu_win",
        )
        self.assertEqual(selection["next_rom_memory_precision_axis"], "named_rom_memory_symbol_mapping")
        self.assertEqual(selection["named_rom_memory_symbol_mapping_status"], "gpu_cpu_named_mapping_gates_passed")
        self.assertEqual(
            selection["named_rom_memory_symbol_mapping_boundary_status"],
            "packaged_xuantie_e902_named_mapping_gpu_win",
        )
        self.assertEqual(selection["next_application_like_semantics_axis"], "program_image_delta")
        self.assertEqual(selection["program_image_delta_status"], "packaged_gpu_win")
        self.assertEqual(
            selection["program_image_delta_gpu_report"],
            "reports/xuantie_e902_program_image_delta.json",
        )
        self.assertEqual(
            selection["program_image_delta_cpu_report"],
            "reports/xuantie_e902_cpu_exact_loop_program_image_delta.json",
        )
        self.assertEqual(selection["next_responsibility_expansion_axis"], "broader_memory_family_coverage")
        self.assertEqual(selection["broader_memory_family_coverage_status"], "source_contract_gap_found")
        self.assertIn("zero-fills", selection["broader_memory_family_coverage_gap"]["x_dmem_ctrl"])
        self.assertIn("does not load", selection["broader_memory_family_coverage_gap"]["x_smem_ctrl"])
        self.assertEqual(
            selection["post_xuantie_memory_gap_next_axis_options"],
            ["input_stream_delta", "target_breadth"],
        )
        self.assertEqual(selection["post_xuantie_memory_gap_selected_axis"], "input_stream_delta")
        self.assertEqual(selection["post_xuantie_memory_gap_deferred_axis"], "target_breadth")
        self.assertIn("case.pat", selection["post_xuantie_memory_gap_selection_reason"])
        self.assertEqual(
            selection["active_non_tlul_candidate_program_image_delta_gate"],
            "config/scaling_gates/xuantie_e902_program_image_delta.json",
        )
        self.assertEqual(
            selection["active_non_tlul_candidate_cpu_exact_loop_program_image_delta_gate"],
            "config/scaling_gates/xuantie_e902_cpu_exact_loop_program_image_delta.json",
        )
        self.assertEqual(
            selection["named_rom_memory_symbol_mapping_gpu_report"],
            "reports/xuantie_e902_named_rom_memory_mapping.json",
        )
        self.assertEqual(
            selection["named_rom_memory_symbol_mapping_cpu_report"],
            "reports/xuantie_e902_cpu_exact_loop_named_rom_memory_mapping.json",
        )
        self.assertEqual(
            selection["named_rom_memory_symbol_mapping_contract"]["selected_family"],
            "iahb_instruction_memory",
        )
        self.assertIn(
            "ram0=word[31:24]",
            selection["named_rom_memory_symbol_mapping_contract"]["testbench_initialization_lane_mapping"],
        )
        self.assertIn(
            "xuantie_e902_gpu_cov_tb.dut.x_soc.x_cpu_sub_system_ahb.x_iahb_mem_ctrl.ram0..3.mem",
            selection["named_rom_memory_symbol_mapping_candidate_fields"],
        )

    def test_resident_patch_semantics_names_application_like_next_axis(self) -> None:
        semantics = json.loads(RESIDENT_PATCH_SEMANTICS.read_text(encoding="utf-8"))
        self.assertEqual(semantics["next_action"], "define_xuantie_e902_program_image_delta_gate")
        self.assertEqual(semantics["next_semantics_axis"]["name"], "application_like_patch_schedule_semantics")
        self.assertEqual(semantics["next_semantics_axis"]["selected_first_semantic"], "rom_or_memory_init_delta")
        self.assertIn("rom_or_memory_init_delta", semantics["next_semantics_axis"]["candidate_semantics"])
        self.assertEqual(
            semantics["next_semantics_axis"]["selected_semantic_contract"]["cpu_baseline"],
            "matching single-process CPU exact-loop applies the same memory-image deltas before each corresponding eval step",
        )
        self.assertEqual(
            semantics["next_semantics_axis"]["selected_semantic_contract"]["next_precision_step"],
            "define_xuantie_e902_program_image_delta_gate",
        )
        self.assertIn(
            "x_iahb_mem_ctrl.ram0..3.mem",
            semantics["next_semantics_axis"]["selected_semantic_contract"]["named_mapping_contract"],
        )

    def test_readme_keeps_xuantie_boundary_limited(self) -> None:
        readme = README.read_text(encoding="utf-8")
        self.assertIn("XuanTie-E902 Resident Runtime Boundary", readme)
        self.assertIn("GPU resident mode beats", readme)
        self.assertIn("Not broad XuanTie family support", readme)
        self.assertIn("resident --patch / --patch-script semantics", readme)
        self.assertIn("define_resident_patch_script_semantics", readme)
        self.assertIn("config/resident_patch_script_semantics.json", readme)
        self.assertIn("config/scaling_gates/veer_el2_resident_workload.json", readme)
        self.assertIn("config/scaling_gates/veer_el2_larger_resident_workload.json", readme)
        self.assertIn("make -C src/hybrid veer_el2_host_probe", readme)


if __name__ == "__main__":
    unittest.main()
