#!/usr/bin/env python3
"""Contract checks for clean-checkout sim prerequisite rebuilding."""

from __future__ import annotations

import argparse
import io
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
from results_reproduction_io import sanitize_local_absolute_paths
import run_vl_hybrid
import run_vl_hybrid_launch
import run_vl_hybrid_launch_env


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

    def test_log_sanitizer_handles_option_value_absolute_paths(self) -> None:
        text = "-I/home/user/repo/artifacts/obj --load-pass-plugin=/home/user/repo/artifacts/tool_bins/passes/VlGpuPasses.so"
        self.assertEqual(
            sanitize_local_absolute_paths(text),
            "-I<local-absolute-path> --load-pass-plugin=<local-absolute-path>",
        )

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
