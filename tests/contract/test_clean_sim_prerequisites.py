#!/usr/bin/env python3
"""Contract checks for clean-checkout sim prerequisite rebuilding."""

from __future__ import annotations

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
import run_vl_hybrid_launch


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


if __name__ == "__main__":
    unittest.main()
