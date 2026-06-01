#!/usr/bin/env python3
"""Contract checks for clean-checkout sim prerequisite rebuilding."""

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import build_vl_gpu_stage_env
import run_vl_hybrid_launch


class CleanSimPrerequisiteTest(unittest.TestCase):
    def test_build_vl_gpu_rebuilds_missing_pass_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            passes_dir = Path(temp_dir) / "passes"
            passes_dir.mkdir()
            existing_so = passes_dir / "VlGpuPasses.so"
            missing_vlgpugen = passes_dir / "vlgpugen"
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
            passes_dir.mkdir()
            pass_tools = (passes_dir / "VlGpuPasses.so", passes_dir / "vlgpugen")
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

    def test_run_vl_hybrid_rebuilds_missing_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            hybrid_dir = repo_root / "src" / "hybrid"
            hybrid_dir.mkdir(parents=True)
            hybrid_bin = hybrid_dir / "run_vl_hybrid"

            with mock.patch.object(run_vl_hybrid_launch, "REPO_ROOT", repo_root), mock.patch.object(
                run_vl_hybrid_launch,
                "HYBRID_BIN",
                hybrid_bin,
            ), mock.patch.object(run_vl_hybrid_launch.subprocess, "run") as run:
                with redirect_stderr(io.StringIO()):
                    run_vl_hybrid_launch.ensure_hybrid_runtime_built()

            run.assert_called_once_with(
                ["make", "-C", str(hybrid_dir), "--no-print-directory"],
                cwd=repo_root,
                check=True,
            )

    def test_run_vl_hybrid_reports_runtime_build_failure_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            hybrid_dir = repo_root / "src" / "hybrid"
            hybrid_dir.mkdir(parents=True)
            hybrid_bin = hybrid_dir / "run_vl_hybrid"

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


if __name__ == "__main__":
    unittest.main()
