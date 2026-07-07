#!/usr/bin/env python3
"""Contract checks for clean-checkout sim prerequisite rebuilding."""

from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import build_vl_gpu_stage_env
import hybrid_template_commands
from hybrid_template_types import HybridTemplatePlan
from results_reproduction_io import sanitize_local_absolute_paths
import run_vl_hybrid
import run_vl_hybrid_launch
import run_vl_hybrid_launch_env


def _dummy_template_plan(root: Path) -> HybridTemplatePlan:
    mdir = root / "artifacts" / "demo_obj_dir"
    template_path = root / "config" / "slice_launch_templates" / "demo.json"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(
        '{"schema_version": 1, "build": {"host_probe_builder": "src/tools/build_host_probe.py"}}\n',
        encoding="utf-8",
    )
    return HybridTemplatePlan(
        template_path=template_path,
        target="DEMO.demo",
        target_name="demo",
        top_module="demo_tb",
        mdir=mdir,
        host_probe_target="demo_host_probe",
        source_gate=None,
        source_files=[root / "overlays" / "demo.sv"],
        source_closure={"status": "complete"},
        verilator_defines=[],
        verilator_args=[],
        cpu_init_state=mdir / "demo_cpu_repeat_1x1.bin",
        cpu_reference_state=mdir / "demo_cpu_repeat_2x3.bin",
        gpu_candidate_state=mdir / "demo_gpu_from_cpu_init_2x3.bin",
        cpu_init_report=root / "reports" / "demo_cpu_repeat_1x1.json",
        cpu_report=root / "reports" / "demo_cpu_repeat_2x3.json",
        hybrid_report=root / "reports" / "demo_hybrid_2x3.txt",
        compare_report=root / "reports" / "demo_cpu_vs_hybrid_2x3_coverage_output_compare.json",
        nstates=2,
        steps=3,
        cfg_batch_length=64,
        cfg_reset_cycles=2,
        cfg_drain_cycles=8,
        cfg_seed=1,
    )


class CleanSimPrerequisiteTest(unittest.TestCase):
    def test_build_vl_gpu_rebuilds_missing_pass_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            passes_dir = Path(temp_dir) / "passes"
            pass_tool_dir = Path(temp_dir) / "artifacts" / "tool_bins" / "passes"
            passes_dir.mkdir()
            pass_tool_dir.mkdir(parents=True)
            existing_so = pass_tool_dir / "VlGpuPasses.so"
            missing_vlgpugen = pass_tool_dir / "vlgpugen"
            existing_so.write_text("", encoding="utf-8")
            calls = []

            with mock.patch.object(build_vl_gpu_stage_env, "PASSES_DIR", passes_dir), mock.patch.object(
                build_vl_gpu_stage_env,
                "PASS_TOOL_OUTPUTS",
                (existing_so, missing_vlgpugen),
            ):
                with redirect_stdout(io.StringIO()):
                    build_vl_gpu_stage_env.ensure_pass_tools_built(run_command=calls.append)

            self.assertEqual(calls, [["make", "-C", str(passes_dir), "--no-print-directory"]])

    def test_build_vl_gpu_skips_make_when_pass_tools_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            passes_dir = Path(temp_dir) / "passes"
            pass_tool_dir = Path(temp_dir) / "artifacts" / "tool_bins" / "passes"
            passes_dir.mkdir()
            pass_tool_dir.mkdir(parents=True)
            pass_tools = (pass_tool_dir / "VlGpuPasses.so", pass_tool_dir / "vlgpugen")
            for path in pass_tools:
                path.write_text("", encoding="utf-8")
            calls = []

            with mock.patch.object(build_vl_gpu_stage_env, "PASSES_DIR", passes_dir), mock.patch.object(
                build_vl_gpu_stage_env,
                "PASS_TOOL_OUTPUTS",
                pass_tools,
            ):
                with redirect_stdout(io.StringIO()):
                    build_vl_gpu_stage_env.ensure_pass_tools_built(run_command=calls.append)

            self.assertEqual(calls, [])

    def test_build_vl_gpu_rebuilds_stale_pass_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            passes_dir = Path(temp_dir) / "passes"
            pass_tool_dir = Path(temp_dir) / "artifacts" / "tool_bins" / "passes"
            passes_dir.mkdir()
            pass_tool_dir.mkdir(parents=True)
            source = passes_dir / "vlgpugen.cpp"
            source.write_text("// newer source\n", encoding="utf-8")
            pass_tools = (pass_tool_dir / "VlGpuPasses.so", pass_tool_dir / "vlgpugen")
            for path in pass_tools:
                path.write_text("", encoding="utf-8")
            old_mtime = source.stat().st_mtime - 10
            for path in pass_tools:
                os.utime(path, (old_mtime, old_mtime))
            calls = []

            with mock.patch.object(build_vl_gpu_stage_env, "PASSES_DIR", passes_dir), mock.patch.object(
                build_vl_gpu_stage_env,
                "PASS_TOOL_OUTPUTS",
                pass_tools,
            ):
                with redirect_stdout(io.StringIO()):
                    build_vl_gpu_stage_env.ensure_pass_tools_built(run_command=calls.append)

            self.assertEqual(calls, [["make", "-C", str(passes_dir), "--no-print-directory"]])

    def test_generated_helper_binary_paths_are_outside_src(self) -> None:
        repo_root = Path(build_vl_gpu_stage_env.REPO_ROOT)
        self.assertEqual(
            build_vl_gpu_stage_env.PASS_TOOL_OUTPUTS,
            (
                repo_root / "artifacts" / "tool_bins" / "passes" / "VlGpuPasses.so",
                repo_root / "artifacts" / "tool_bins" / "passes" / "vlgpugen",
            ),
        )
        self.assertEqual(
            run_vl_hybrid_launch.HYBRID_BIN,
            REPO_ROOT / "artifacts" / "tool_bins" / "hybrid" / "run_vl_hybrid",
        )
        for path in (*build_vl_gpu_stage_env.PASS_TOOL_OUTPUTS, run_vl_hybrid_launch.HYBRID_BIN):
            self.assertIn("artifacts/tool_bins", path.as_posix())
            self.assertNotIn("/src/passes/", path.as_posix())
            self.assertNotIn("/src/hybrid/", path.as_posix())

    def test_runner_command_uses_artifact_runtime_binary(self) -> None:
        args = SimpleNamespace(nstates=2, block_size=64, steps=3, patch=[])
        resolution = SimpleNamespace(cubin=Path("demo.cubin"), storage=128)
        command = run_vl_hybrid_launch.build_runner_command(args, resolution)

        self.assertEqual(Path(command[0]), run_vl_hybrid_launch.HYBRID_BIN)
        self.assertIn("artifacts/tool_bins/hybrid/run_vl_hybrid", command[0])

    def test_run_vl_hybrid_launch_env_forwards_feedback_edges(self) -> None:
        env: dict[str, str] = {}
        args = SimpleNamespace(
            resident_steps=True,
            gpu_replicate_init_state=False,
            timing_repeats=1,
            feedback_edges="7:3,236:232",
            feedback_increments="4:1",
            feedback_phase_sets="1:6:1,2:6:1",
            feedback_edge_mode="phase",
        )

        run_vl_hybrid_launch_env.configure_runtime_mode_env(env, args)

        self.assertEqual(env["RUN_VL_HYBRID_RESIDENT_STEPS"], "1")
        self.assertEqual(env["RUN_VL_HYBRID_FEEDBACK_EDGES"], "7:3,236:232")
        self.assertEqual(env["RUN_VL_HYBRID_FEEDBACK_INCREMENTS"], "4:1")
        self.assertEqual(env["RUN_VL_HYBRID_FEEDBACK_PHASE_SETS"], "1:6:1,2:6:1")
        self.assertEqual(env["RUN_VL_HYBRID_FEEDBACK_EDGE_MODE"], "phase")

    def test_run_vl_hybrid_launch_env_forwards_module_load_symbol_check(self) -> None:
        env: dict[str, str] = {}
        args = SimpleNamespace(module_load_symbol_check="vl_demo_kernel")

        run_vl_hybrid_launch_env.configure_module_load_symbol_check_env(env, args)

        self.assertEqual(
            env["RUN_VL_HYBRID_MODULE_LOAD_SYMBOL_CHECK"],
            "vl_demo_kernel",
        )

    def test_run_vl_hybrid_parser_accepts_module_load_symbol_check(self) -> None:
        parser = run_vl_hybrid.build_parser()

        args = parser.parse_args(
            [
                "--cubin",
                "demo.ptx",
                "--storage-size",
                "64",
                "--module-load-symbol-check",
                "vl_demo_kernel",
            ]
        )

        self.assertEqual(args.module_load_symbol_check, "vl_demo_kernel")

    def test_hybrid_runtime_has_module_load_symbol_check_mode(self) -> None:
        source = (REPO_ROOT / "src" / "hybrid" / "run_vl_hybrid.c").read_text(
            encoding="utf-8"
        )

        self.assertIn("RUN_VL_HYBRID_MODULE_LOAD_SYMBOL_CHECK", source)
        self.assertIn("module_load_symbol_check: passed", source)
        self.assertIn("before_module_load_symbol_check", source)

    def test_run_vl_hybrid_launch_env_consumes_schedule_lowering_plan(self) -> None:
        from gategpt_schedule_planner import (
            build_padded_start_pair_cycle_loop_lowering_plan,
            write_lowering_plan_artifact,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "lowering_plan.json"
            write_lowering_plan_artifact(
                plan_path,
                build_padded_start_pair_cycle_loop_lowering_plan(
                    nstates=2,
                    phase_count=3,
                    loop_chunk=1701,
                ),
            )
            env: dict[str, str] = {}
            args = SimpleNamespace(schedule_lowering_plan=plan_path)

            validation = run_vl_hybrid_launch_env.configure_schedule_lowering_plan_env(env, args)

        self.assertIsNotNone(validation)
        self.assertEqual(validation["status"], "valid")
        self.assertEqual(env["RUN_VL_HYBRID_SCHEDULE_LOWERING_SHAPE"], "padded_start_pair_cycle_loop")
        self.assertEqual(env["RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE"], "1")
        self.assertEqual(env["RUN_VL_HYBRID_FUSED_PAIR_CYCLE"], "1")
        self.assertEqual(env["RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP"], "1")
        self.assertEqual(env["RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK"], "1701")

    def test_run_vl_hybrid_launch_env_consumes_ordering_aware_plan_by_default(self) -> None:
        from gategpt_schedule_planner import (
            build_ordering_aware_phase_resident_token_loop_lowering_plan,
            write_lowering_plan_artifact,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "ordering_aware_plan.json"
            write_lowering_plan_artifact(
                plan_path,
                build_ordering_aware_phase_resident_token_loop_lowering_plan(
                    nstates=16,
                    phase_count=9,
                    loop_chunk=1701,
                ),
            )
            env: dict[str, str] = {}
            args = SimpleNamespace(schedule_lowering_plan=plan_path)

            validation = run_vl_hybrid_launch_env.configure_schedule_lowering_plan_env(env, args)

        self.assertEqual(validation["status"], "ready_for_schedule_integrated_cpu_comparison")
        self.assertTrue(validation["runtime_supported"])
        self.assertEqual(
            env["RUN_VL_HYBRID_SCHEDULE_LOWERING_SHAPE"],
            "ordering_aware_phase_resident_token_loop",
        )
        self.assertEqual(env["RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE"], "1")
        self.assertEqual(env["RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE_START"], "0")
        self.assertEqual(env["RUN_VL_HYBRID_FUSED_PAIR_CYCLE"], "1")
        self.assertEqual(env["RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP"], "1")
        self.assertEqual(env["RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK"], "1701")
        self.assertNotIn("RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_PROBE_PLAN_ONLY", env)

    def test_run_vl_hybrid_launch_env_can_consume_ordering_aware_probe_plan_explicitly(self) -> None:
        from gategpt_schedule_planner import (
            build_ordering_aware_phase_resident_token_loop_lowering_plan,
            write_lowering_plan_artifact,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "ordering_aware_plan.json"
            write_lowering_plan_artifact(
                plan_path,
                build_ordering_aware_phase_resident_token_loop_lowering_plan(
                    nstates=16,
                    phase_count=9,
                    loop_chunk=1701,
                    terminal_mask_specs="0:6,1:8",
                ),
            )
            env: dict[str, str] = {}
            args = SimpleNamespace(
                schedule_lowering_plan=plan_path,
                allow_ordering_aware_token_loop_probe_plan=True,
            )

            validation = run_vl_hybrid_launch_env.configure_schedule_lowering_plan_env(env, args)

        self.assertEqual(validation["status"], "ready_for_schedule_integrated_cpu_comparison")
        self.assertTrue(validation["runtime_supported"])
        self.assertEqual(
            env["RUN_VL_HYBRID_SCHEDULE_LOWERING_SHAPE"],
            "ordering_aware_phase_resident_token_loop",
        )
        self.assertEqual(env["RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_PROBE_PLAN_ONLY"], "1")
        self.assertEqual(env["RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_ABI_PROBE"], "1")
        self.assertEqual(env["RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE"], "1")
        self.assertEqual(env["RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE_START"], "0")
        self.assertEqual(env["RUN_VL_HYBRID_FUSED_PAIR_CYCLE"], "1")
        self.assertEqual(env["RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP"], "1")
        self.assertEqual(env["RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK"], "1701")
        self.assertEqual(
            env["RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK"],
            "0:6,1:8",
        )

    def test_run_vl_hybrid_launch_env_rejects_chunked_ordering_aware_plan_without_continuation_abi(
        self,
    ) -> None:
        from gategpt_schedule_planner import (
            build_ordering_aware_phase_resident_token_loop_lowering_plan,
            write_lowering_plan_artifact,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "ordering_aware_chunked_plan.json"
            write_lowering_plan_artifact(
                plan_path,
                build_ordering_aware_phase_resident_token_loop_lowering_plan(
                    nstates=16,
                    phase_count=8,
                    loop_chunk=256,
                ),
            )
            env: dict[str, str] = {}
            args = SimpleNamespace(schedule_lowering_plan=plan_path)

            with self.assertRaises(SystemExit) as raised:
                run_vl_hybrid_launch_env.configure_schedule_lowering_plan_env(env, args)

        self.assertEqual(raised.exception.code, 1)
        self.assertNotIn("RUN_VL_HYBRID_SCHEDULE_LOWERING_SHAPE", env)
        self.assertNotIn("RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK", env)

    def test_make_compat_targets_do_not_write_helper_binaries_under_src(self) -> None:
        if shutil.which("make") is None:
            self.skipTest("make is not installed")

        cases = (
            ("src/passes", "vlgpugen", "../../artifacts/tool_bins/passes/vlgpugen", r"-o\s+vlgpugen(\s|$)"),
            ("src/passes", "VlGpuPasses.so", "../../artifacts/tool_bins/passes/VlGpuPasses.so", r"-o\s+VlGpuPasses\.so(\s|$)"),
            ("src/hybrid", "run_vl_hybrid", "../../artifacts/tool_bins/hybrid/run_vl_hybrid", r"-o\s+run_vl_hybrid(\s|$)"),
        )
        for make_dir, target, artifact_output, forbidden_output in cases:
            with self.subTest(target=target):
                result = subprocess.run(
                    ["make", "-B", "-n", "-C", make_dir, "--no-print-directory", target],
                    cwd=REPO_ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                output = result.stdout + result.stderr
                self.assertIn(artifact_output, output)
                self.assertNotRegex(output, forbidden_output)

    def test_run_vl_hybrid_rebuilds_missing_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            hybrid_src_dir = repo_root / "src" / "hybrid"
            hybrid_src_dir.mkdir(parents=True)
            hybrid_bin = repo_root / "artifacts" / "tool_bins" / "hybrid" / "run_vl_hybrid"

            with mock.patch.object(run_vl_hybrid_launch, "REPO_ROOT", repo_root), mock.patch.object(
                run_vl_hybrid_launch,
                "HYBRID_BIN",
                hybrid_bin,
            ), mock.patch.object(run_vl_hybrid_launch.subprocess, "run") as run:
                with redirect_stderr(io.StringIO()):
                    run_vl_hybrid_launch.ensure_hybrid_runtime_built()

            run.assert_called_once_with(
                ["make", "-C", str(hybrid_src_dir), "--no-print-directory"],
                cwd=repo_root,
                check=True,
            )

    def test_run_vl_hybrid_rebuilds_stale_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            hybrid_src_dir = repo_root / "src" / "hybrid"
            hybrid_src_dir.mkdir(parents=True)
            source = hybrid_src_dir / "run_vl_hybrid.c"
            source.write_text("int main(void) { return 0; }\n", encoding="utf-8")
            hybrid_bin = repo_root / "artifacts" / "tool_bins" / "hybrid" / "run_vl_hybrid"
            hybrid_bin.parent.mkdir(parents=True)
            hybrid_bin.write_text("old runtime\n", encoding="utf-8")
            old_time = 1_700_000_000
            new_time = old_time + 10
            hybrid_bin.touch()
            source.touch()
            os.utime(hybrid_bin, (old_time, old_time))
            os.utime(source, (new_time, new_time))

            with mock.patch.object(run_vl_hybrid_launch, "REPO_ROOT", repo_root), mock.patch.object(
                run_vl_hybrid_launch,
                "HYBRID_BIN",
                hybrid_bin,
            ), mock.patch.object(run_vl_hybrid_launch.subprocess, "run") as run:
                with redirect_stderr(io.StringIO()):
                    run_vl_hybrid_launch.ensure_hybrid_runtime_built()

            run.assert_called_once_with(
                ["make", "-C", str(hybrid_src_dir), "--no-print-directory"],
                cwd=repo_root,
                check=True,
            )

    def test_run_vl_hybrid_keeps_fresh_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            hybrid_src_dir = repo_root / "src" / "hybrid"
            hybrid_src_dir.mkdir(parents=True)
            source = hybrid_src_dir / "run_vl_hybrid.c"
            source.write_text("int main(void) { return 0; }\n", encoding="utf-8")
            hybrid_bin = repo_root / "artifacts" / "tool_bins" / "hybrid" / "run_vl_hybrid"
            hybrid_bin.parent.mkdir(parents=True)
            hybrid_bin.write_text("fresh runtime\n", encoding="utf-8")
            old_time = 1_700_000_000
            new_time = old_time + 10
            os.utime(source, (old_time, old_time))
            os.utime(hybrid_bin, (new_time, new_time))

            with mock.patch.object(run_vl_hybrid_launch, "REPO_ROOT", repo_root), mock.patch.object(
                run_vl_hybrid_launch,
                "HYBRID_BIN",
                hybrid_bin,
            ), mock.patch.object(run_vl_hybrid_launch.subprocess, "run") as run:
                with redirect_stderr(io.StringIO()):
                    run_vl_hybrid_launch.ensure_hybrid_runtime_built()

            run.assert_not_called()

    def test_run_vl_hybrid_reports_runtime_build_failure_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            hybrid_src_dir = repo_root / "src" / "hybrid"
            hybrid_src_dir.mkdir(parents=True)
            hybrid_bin = repo_root / "artifacts" / "tool_bins" / "hybrid" / "run_vl_hybrid"

            with mock.patch.object(run_vl_hybrid_launch, "REPO_ROOT", repo_root), mock.patch.object(
                run_vl_hybrid_launch,
                "HYBRID_BIN",
                hybrid_bin,
            ), mock.patch.object(
                run_vl_hybrid_launch.subprocess,
                "run",
                side_effect=subprocess.CalledProcessError(2, ["make"]),
            ), self.assertRaises(SystemExit) as raised, redirect_stderr(io.StringIO()) as stderr:
                run_vl_hybrid_launch.ensure_hybrid_runtime_built()

            self.assertEqual(raised.exception.code, 1)
            self.assertIn("failed to build hybrid runtime", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_run_vl_hybrid_reports_runner_failure_without_traceback(self) -> None:
        resolution = SimpleNamespace()
        with mock.patch.object(
            sys,
            "argv",
            ["run_vl_hybrid.py", "--cubin", "demo.cubin", "--storage-size", "1"],
        ), mock.patch.object(run_vl_hybrid, "resolve_launch_inputs", return_value=resolution), mock.patch.object(
            run_vl_hybrid,
            "require_launch_files",
        ), mock.patch.object(
            run_vl_hybrid,
            "build_runner_command",
            return_value=["/home/example/src/hybrid/run_vl_hybrid", "/tmp/demo.cubin"],
        ), mock.patch.object(
            run_vl_hybrid,
            "configure_launch_env",
            return_value={},
        ), mock.patch.object(
            run_vl_hybrid,
            "prepare_init_state_env",
            return_value=None,
        ), mock.patch.object(
            run_vl_hybrid.subprocess,
            "run",
            side_effect=subprocess.CalledProcessError(100, ["runner"]),
        ), self.assertRaises(SystemExit) as raised, redirect_stdout(io.StringIO()) as stdout, redirect_stderr(
            io.StringIO()
        ) as stderr:
            run_vl_hybrid.main()

        self.assertEqual(raised.exception.code, 100)
        self.assertIn("<local-absolute-path>", stdout.getvalue())
        self.assertNotIn("/home/example", stdout.getvalue())
        self.assertIn("hybrid runtime failed with exit code 100", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_run_vl_hybrid_classifies_direct_cuda_init_failure(self) -> None:
        resolution = SimpleNamespace()
        with mock.patch.object(
            sys,
            "argv",
            ["run_vl_hybrid.py", "--cubin", "demo.cubin", "--storage-size", "1"],
        ), mock.patch.object(run_vl_hybrid, "resolve_launch_inputs", return_value=resolution), mock.patch.object(
            run_vl_hybrid,
            "require_launch_files",
        ), mock.patch.object(
            run_vl_hybrid,
            "build_runner_command",
            return_value=["/home/example/artifacts/tool_bins/hybrid/run_vl_hybrid", "/tmp/demo.cubin"],
        ), mock.patch.object(
            run_vl_hybrid,
            "configure_launch_env",
            return_value={},
        ), mock.patch.object(
            run_vl_hybrid,
            "prepare_init_state_env",
            return_value=None,
        ), mock.patch.object(
            run_vl_hybrid.subprocess,
            "run",
            return_value=SimpleNamespace(
                returncode=304,
                stdout="",
                stderr="/home/example/src/hybrid/run_vl_hybrid.c:1189 CUDA error 304: operating system call failed (cuInit)\n",
            ),
        ), self.assertRaises(SystemExit) as raised, redirect_stdout(io.StringIO()) as stdout, redirect_stderr(
            io.StringIO()
        ) as stderr:
            run_vl_hybrid.main()

        self.assertEqual(raised.exception.code, 304)
        self.assertIn("<local-absolute-path>", stdout.getvalue())
        self.assertIn("CUDA error 304", stderr.getvalue())
        self.assertIn("classified_failure: gpu_runtime_unavailable", stderr.getvalue())
        self.assertIn("cuInit", stderr.getvalue())
        self.assertNotIn("/home/example", stderr.getvalue())
        self.assertNotIn("/tmp/demo.cubin", stdout.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_template_run_plan_default_prints_concise_stage_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            plan = _dummy_template_plan(repo_root)
            commands = [[f"cmd{index}"] for index in range(1, 8)]

            with mock.patch.object(hybrid_template_commands, "REPO_ROOT", repo_root), mock.patch.object(
                hybrid_template_commands,
                "command_plan",
                return_value=commands,
            ), mock.patch.object(hybrid_template_commands.subprocess, "run") as run:
                run.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
                with redirect_stdout(io.StringIO()) as stdout:
                    hybrid_template_commands.run_plan(plan)

            self.assertEqual(run.call_count, 7)
            output = stdout.getvalue()
            self.assertIn("[1/7] Verilator build: start", output)
            self.assertIn("[7/7] Coverage-output compare: ok", output)
            self.assertIn("log: reports/demo_2x3_verilator_build.log", output)
            self.assertIn("report: reports/demo_hybrid_2x3.txt", output)
            self.assertNotIn("+ cmd1", output)

    def test_template_run_plan_dry_run_keeps_copyable_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            plan = _dummy_template_plan(repo_root)
            command = [str(repo_root / "tool"), "--arg"]

            with mock.patch.object(hybrid_template_commands, "REPO_ROOT", repo_root), mock.patch.object(
                hybrid_template_commands,
                "command_plan",
                return_value=[command] * 7,
            ):
                with redirect_stdout(io.StringIO()) as stdout:
                    hybrid_template_commands.run_plan(plan, dry_run=True)

            output = stdout.getvalue()
            self.assertIn(str(repo_root / "tool"), output)
            self.assertNotIn("<local-absolute-path>", output)

    def test_template_resident_command_plan_uses_patch_script_and_distinct_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            plan = _dummy_template_plan(repo_root)
            patch_script = repo_root / "artifacts" / "packet_pattern.patch"

            with mock.patch.object(hybrid_template_commands, "REPO_ROOT", repo_root):
                commands = hybrid_template_commands.command_plan(plan, resident_patch_script=patch_script)

            hybrid = commands[5]
            compare = commands[6]
            self.assertIn("--resident-steps", hybrid)
            self.assertEqual(hybrid[hybrid.index("--patch-script") + 1], "artifacts/packet_pattern.patch")
            self.assertEqual(
                hybrid[hybrid.index("--dump-state") + 1],
                "artifacts/demo_obj_dir/demo_gpu_resident_multistep_2x3.bin",
            )
            self.assertEqual(compare[compare.index("--candidate-label") + 1], "resident_multistep_from_cpu_init_2x3")
            self.assertEqual(
                compare[compare.index("--json-out") + 1],
                "reports/demo_cpu_vs_resident_multistep_2x3_coverage_output_compare.json",
            )

    def test_template_resident_run_plan_dry_run_prints_resident_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            plan = _dummy_template_plan(repo_root)
            patch_script = repo_root / "artifacts" / "packet_pattern.patch"

            with mock.patch.object(hybrid_template_commands, "REPO_ROOT", repo_root):
                with redirect_stdout(io.StringIO()) as stdout:
                    hybrid_template_commands.run_plan(
                        plan,
                        dry_run=True,
                        resident_patch_script=patch_script,
                    )

            output = stdout.getvalue()
            self.assertIn("--resident-steps --patch-script artifacts/packet_pattern.patch", output)
            self.assertIn("demo_gpu_resident_multistep_2x3.bin", output)
            self.assertIn("demo_cpu_vs_resident_multistep_2x3_coverage_output_compare.json", output)

    def test_template_run_plan_verbose_keeps_command_stream(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            plan = _dummy_template_plan(repo_root)
            commands = [[f"cmd{index}"] for index in range(1, 8)]

            with mock.patch.object(hybrid_template_commands, "REPO_ROOT", repo_root), mock.patch.object(
                hybrid_template_commands,
                "command_plan",
                return_value=commands,
            ), mock.patch.object(hybrid_template_commands.subprocess, "run") as run:
                with redirect_stdout(io.StringIO()) as stdout:
                    hybrid_template_commands.run_plan(plan, verbose=True)

            self.assertEqual(run.call_count, 7)
            output = stdout.getvalue()
            self.assertIn("+ cmd1", output)
            self.assertIn("+ cmd7", output)
            self.assertNotIn("[1/7] Verilator build: start", output)

    def test_template_run_plan_failure_reports_stage_and_log_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            plan = _dummy_template_plan(repo_root)
            commands = [[f"cmd{index}"] for index in range(1, 8)]

            with mock.patch.object(hybrid_template_commands, "REPO_ROOT", repo_root), mock.patch.object(
                hybrid_template_commands,
                "command_plan",
                return_value=commands,
            ), mock.patch.object(
                hybrid_template_commands.subprocess,
                "run",
                side_effect=subprocess.CalledProcessError(7, ["cmd1", "--noisy-arg"]),
            ):
                with self.assertRaises(hybrid_template_commands.HybridTemplateStageError) as raised:
                    with redirect_stdout(io.StringIO()):
                        hybrid_template_commands.run_plan(plan)

            message = str(raised.exception)
            self.assertIn("Verilator build failed with exit code 7", message)
            self.assertIn("log: reports/demo_2x3_verilator_build.log", message)
            self.assertNotIn("--noisy-arg", message)

    def test_template_run_plan_runtime_failure_reports_short_classification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            plan = _dummy_template_plan(repo_root)
            commands = [[f"cmd{index}"] for index in range(1, 8)]
            calls = []

            def fake_run(*args, **_kwargs):
                calls.append(args[0])
                if len(calls) == 6:
                    return SimpleNamespace(
                        returncode=100,
                        stdout="",
                        stderr="/home/user/src/hybrid/run_vl_hybrid.c:1189 CUDA error 100: no CUDA-capable device is detected (cuInit)\n",
                    )
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            with mock.patch.object(hybrid_template_commands, "REPO_ROOT", repo_root), mock.patch.object(
                hybrid_template_commands,
                "command_plan",
                return_value=commands,
            ), mock.patch.object(hybrid_template_commands.subprocess, "run", side_effect=fake_run):
                with self.assertRaises(hybrid_template_commands.HybridTemplateStageError) as raised:
                    with redirect_stdout(io.StringIO()):
                        hybrid_template_commands.run_plan(plan)

            message = str(raised.exception)
            self.assertIn("Hybrid sidecar run failed with exit code 100", message)
            self.assertIn("classified_failure: gpu_runtime_unavailable", message)
            self.assertIn("CUDA error 100", message)
            self.assertIn("cuInit", message)
            self.assertIn("log: reports/demo_2x3_hybrid_sidecar_run.log", message)
            self.assertIn("report: reports/demo_hybrid_2x3.txt", message)
            self.assertNotIn("/home/user", message)

    def test_template_stage_log_starts_with_command_before_child_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            plan = _dummy_template_plan(repo_root)

            with mock.patch.object(hybrid_template_commands, "REPO_ROOT", repo_root):
                log_path = hybrid_template_commands._run_stage(
                    plan=plan,
                    index=1,
                    stage="verilator_build",
                    command=[sys.executable, "-c", "print('/' + 'tmp/child-output')"],
                    verbose=False,
                )

            assert log_path is not None
            lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertTrue(lines[0].startswith("$ "))
            self.assertEqual(lines[2], "<local-absolute-path>")
            self.assertNotIn("/tmp/child-output", log_path.read_text(encoding="utf-8"))

    def test_log_sanitizer_handles_option_value_absolute_paths(self) -> None:
        text = "-I/home/user/repo/artifacts/obj --load-pass-plugin=/home/user/repo/artifacts/tool_bins/passes/VlGpuPasses.so"
        self.assertEqual(
            sanitize_local_absolute_paths(text),
            "-I<local-absolute-path> --load-pass-plugin=<local-absolute-path>",
        )

    def test_sanitize_summary_is_compact_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_state = root / "init.bin"
            sanitized_state = root / "sanitized.bin"
            init_state.write_bytes(b"init")
            sanitized_state.write_bytes(b"safe")
            applied = [
                {"field_name": "very_long_host_only_field_a", "sanitized_start": 1, "sanitized_end": 2},
                {"field_name": "very_long_host_only_field_b", "sanitized_start": 3, "sanitized_end": 4},
            ]
            parser = argparse.ArgumentParser()
            args = SimpleNamespace(init_state=init_state, sanitize_host_only_internals=True)
            resolution = SimpleNamespace(mdir=root / "obj_dir")
            env: dict[str, str] = {}

            with mock.patch.object(
                run_vl_hybrid_launch_env,
                "_prepare_sanitized_init_state",
                return_value=(sanitized_state, applied),
            ), redirect_stderr(io.StringIO()) as stderr:
                run_vl_hybrid_launch_env.prepare_init_state_env(parser, args, resolution, env)

            output = stderr.getvalue()
            self.assertIn("count=2", output)
            self.assertIn("RUN_VL_HYBRID_VERBOSE_SANITIZE=1", output)
            self.assertIn("output=<local-absolute-path>", output)
            self.assertNotIn(str(sanitized_state), output)
            self.assertNotIn("very_long_host_only_field_a[1:2]", output)
            self.assertEqual(env["RUN_VL_HYBRID_INIT_STATE"], str(sanitized_state))

    def test_sanitize_summary_can_emit_verbose_region_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_state = root / "init.bin"
            sanitized_state = root / "sanitized.bin"
            init_state.write_bytes(b"init")
            sanitized_state.write_bytes(b"safe")
            applied = [
                {"field_name": "host_only_field", "sanitized_start": 5, "sanitized_end": 8},
            ]
            parser = argparse.ArgumentParser()
            args = SimpleNamespace(init_state=init_state, sanitize_host_only_internals=True)
            resolution = SimpleNamespace(mdir=root / "obj_dir")
            env = {"RUN_VL_HYBRID_VERBOSE_SANITIZE": "1"}

            with mock.patch.object(
                run_vl_hybrid_launch_env,
                "_prepare_sanitized_init_state",
                return_value=(sanitized_state, applied),
            ), redirect_stderr(io.StringIO()) as stderr:
                run_vl_hybrid_launch_env.prepare_init_state_env(parser, args, resolution, env)

            self.assertIn("host_only_field[5:8]", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
