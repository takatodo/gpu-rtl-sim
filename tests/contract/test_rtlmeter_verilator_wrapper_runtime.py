import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVerilatorWrapperRuntimeTest(HybridCliTestCase):
    def _touch_executable(self, path: Path) -> None:
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)

    def _write_executable(self, path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)

    def _expanded_sidecar_argv(self) -> list[str]:
        return ["--cc", "--top-module", "top", "-f", "filelist", "--sim-accel", "sidecar-gpu", "--sim-accel-states", "64", "--sim-accel-steps", "1"]

    def _expanded_sidecar_argv_with_mdir(self) -> list[str]:
        return ["--cc", "-Mdir", "obj_dir", "--top-module", "top", "-f", "filelist", "--sim-accel", "sidecar-gpu", "--sim-accel-states", "64", "--sim-accel-steps", "1"]

    def _minimal_sidecar_context(self) -> dict[str, object]:
        return {
            "target": "rtlmeter_example_kind_hello",
            "mode": "rtlmeter_first_seed",
            "template_or_target_registry_entry": "rtlmeter-owned-context-not-template-yet",
            "source_gate_or_manifest_ref": "for_codex/issues/FC-034-rtlmeter-first-seed-execution-integration.md",
            "host_probe_metadata": {"clock_field": "top__DOT__clk", "reset_field": "none"},
            "coverage_output_target": "rtlmeter_stdout_and_cycles_equivalence",
            "coverage_manifest": {"outputs": ["normalized_stdout", "rtlmeter_cycles"]},
            "state_and_report_path_rules": {"root": "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare"},
            "compare_labels": {"cpu": "rtlmeter_cpu", "gpu": "rtlmeter_sidecar_candidate"},
            "source_closure": {"status": "complete"},
        }

    def test_no_gpu_intent_delegates_to_real_verilator_without_reselecting_wrapper(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import run_rtlmeter_verilator_wrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wrapper = root / "wrapper" / "verilator"
            real = root / "real" / "verilator"
            wrapper.parent.mkdir()
            real.parent.mkdir()
            self._touch_executable(wrapper)
            self._touch_executable(real)
            calls = []

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                return subprocess.CompletedProcess(command, 7)

            code = run_rtlmeter_verilator_wrapper(
                ["--cc", "--top-module", "top", "-f", "filelist"],
                executable=wrapper,
                environ={"PATH": f"{wrapper.parent}{os.pathsep}{real.parent}"},
                runner=fake_runner,
            )

        self.assertEqual(code, 7)
        self.assertEqual(calls[0][0], [str(real), "--cc", "--top-module", "top", "-f", "filelist"])
        self.assertNotEqual(calls[0][0][0], str(wrapper))

    def test_missing_real_verilator_fails_without_cpu_as_gpu_fallback(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import run_rtlmeter_verilator_wrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper = Path(temp_dir) / "verilator"
            self._touch_executable(wrapper)
            stderr = io.StringIO()
            code = run_rtlmeter_verilator_wrapper(
                ["--cc", "--top-module", "top", "-f", "filelist"],
                executable=wrapper,
                environ={"PATH": str(wrapper.parent)},
                stderr=stderr,
            )
            report = json.loads(stderr.getvalue())

        self.assertEqual(code, 127)
        self.assertEqual(report["status"], "real_verilator_missing")
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["delegated_to_real_verilator"])

    def test_use_gpu_fails_closed_until_schedule_is_explicit(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import run_rtlmeter_verilator_wrapper

        stderr = io.StringIO()
        code = run_rtlmeter_verilator_wrapper(
            ["--cc", "--top-module", "top", "-f", "filelist", "--use-gpu"],
            environ={"PATH": ""},
            runner=lambda *args, **kwargs: self.fail("GPU intent must not delegate to real Verilator"),
            stderr=stderr,
        )
        report = json.loads(stderr.getvalue())

        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "use_gpu_requires_explicit_sidecar_schedule")
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["sidecar_execution_invoked"])

    def test_expanded_sidecar_schedule_reaches_runtime_boundary_but_does_not_execute_yet(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import run_rtlmeter_verilator_wrapper

        stderr = io.StringIO()
        code = run_rtlmeter_verilator_wrapper(
            self._expanded_sidecar_argv(),
            environ={"PATH": ""},
            runner=lambda *args, **kwargs: self.fail("sidecar execution is not implemented in this wrapper"),
            stderr=stderr,
        )
        report = json.loads(stderr.getvalue())

        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "sidecar_schedule_captured_execution_not_implemented")
        self.assertEqual(report["inspection_status"], "ready_for_rtlmeter_sidecar_planning")
        self.assertFalse(report["cpu_as_gpu_fallback"])
        handoff = report["handoff_metadata"]
        self.assertEqual(handoff["surface"], "rtlmeter_sidecar_handoff")
        self.assertEqual(handoff["status"], "rtlmeter_sidecar_handoff_blocked_missing_context")
        self.assertEqual(handoff["schedule"]["shape"], "64x1")
        self.assertIn("template_or_target_registry_entry", handoff["missing_sidecar_context"])
        self.assertIn("host_probe_metadata", handoff["missing_sidecar_context"])
        self.assertFalse(handoff["sidecar_execution_invoked"])
        self.assertFalse(handoff["cpu_as_gpu_fallback"])

    def test_rtlmeter_sidecar_handoff_preserves_parser_inputs_without_execution(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_handoff

        handoff = build_rtlmeter_sidecar_handoff(
            [
                "--cc",
                "--main",
                "--top-module",
                "top",
                "+incdir+verilogIncludeFiles",
                "+define+__RTLMETER_MAIN_CLOCK=top.clk",
                "-f",
                "filelist",
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "64",
                "--sim-accel-steps",
                "1",
            ]
        )

        self.assertEqual(handoff["schedule"]["state_count"], 64)
        self.assertEqual(handoff["schedule"]["step_count"], 1)
        self.assertEqual(handoff["parser_payload"]["top_module"], "top")
        self.assertIn("filelist", handoff["parser_payload"]["filelists"])
        self.assertIn("+incdir+verilogIncludeFiles", handoff["parser_payload"]["include_dirs"])
        self.assertFalse(handoff["execution_authority"])
        self.assertFalse(handoff["sidecar_launcher_invoked"])
        self.assertFalse(handoff["coverage_output_compare_reached"])

    def test_rtlmeter_sidecar_handoff_marks_complete_context_metadata_ready_without_executing(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_handoff

        handoff = build_rtlmeter_sidecar_handoff(
            [
                "--cc",
                "--main",
                "-Mdir",
                "obj_dir",
                "--top-module",
                "top",
                "-f",
                "filelist",
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "64",
                "--sim-accel-steps",
                "1",
            ],
            sidecar_context=self._minimal_sidecar_context(),
        )

        self.assertEqual(handoff["status"], "rtlmeter_sidecar_handoff_metadata_ready")
        self.assertEqual(handoff["missing_sidecar_context"], [])
        self.assertTrue(handoff["sidecar_context_metadata_ready"])
        self.assertFalse(handoff["sidecar_context_ready"])
        self.assertEqual(handoff["parser_payload"]["mdir"], "obj_dir")
        self.assertEqual(handoff["sidecar_context"]["target"], "rtlmeter_example_kind_hello")
        self.assertFalse(handoff["sidecar_launcher_invoked"])
        self.assertFalse(handoff["sidecar_execution_invoked"])
        self.assertFalse(handoff["coverage_output_compare_reached"])

    def test_rtlmeter_sidecar_handoff_lists_partial_context_gaps(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_handoff

        context = self._minimal_sidecar_context()
        context.pop("host_probe_metadata")
        context["source_closure"] = {}

        handoff = build_rtlmeter_sidecar_handoff(
            self._expanded_sidecar_argv_with_mdir(),
            sidecar_context=context,
        )

        self.assertEqual(handoff["status"], "rtlmeter_sidecar_handoff_blocked_missing_context")
        self.assertIn("host_probe_metadata", handoff["missing_sidecar_context"])
        self.assertIn("source_closure", handoff["missing_sidecar_context"])
        self.assertFalse(handoff["sidecar_context_metadata_ready"])
        self.assertFalse(handoff["sidecar_context_ready"])

    def test_rtlmeter_context_candidate_preserves_known_fields_but_blocks_unresolved_context(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_contract_mapping import map_rtlmeter_case_to_sidecar_contract
        from rtlmeter_sidecar_handoff import (
            build_rtlmeter_sidecar_context_candidate,
            build_rtlmeter_sidecar_handoff,
        )

        contract = map_rtlmeter_case_to_sidecar_contract(
            "Example:kind:hello",
            compile_args=("--sim-accel", "sidecar-gpu", "--sim-accel-states", "64", "--sim-accel-steps", "1"),
        )
        context = build_rtlmeter_sidecar_context_candidate(
            contract,
            template_or_target_registry_entry="config/slice_launch_templates/rtlmeter_example_kind_hello.json",
        )
        handoff = build_rtlmeter_sidecar_handoff(
            self._expanded_sidecar_argv_with_mdir(),
            sidecar_context=context,
        )

        self.assertEqual(context["target"], "rtlmeter_example_kind_hello")
        self.assertEqual(
            context["template_or_target_registry_entry"],
            "config/slice_launch_templates/rtlmeter_example_kind_hello.json",
        )
        self.assertEqual(context["host_probe_metadata"]["main_clock"], "top.clk")
        self.assertEqual(context["compile_source_closure"]["status"], "complete")
        self.assertIn("third_party/rtlmeter/designs/Example/src/top.v", context["compile_source_closure"]["source_files"])
        self.assertIn("third_party/rtlmeter/rtl/__rtlmeter_utils.sv", context["compile_source_closure"]["source_files"])
        self.assertIn("third_party/rtlmeter/rtl/__rtlmeter_top_include.vh", context["compile_source_closure"]["include_files"])
        self.assertEqual(context["source_closure"]["status"], "frontend_metadata_only_not_source_closure")
        self.assertEqual(context["source_closure"]["execution_blocker"], "blocked_host_probe_contract_mismatch")
        self.assertEqual(handoff["status"], "rtlmeter_sidecar_handoff_blocked_missing_context")
        self.assertNotIn("template_or_target_registry_entry", handoff["missing_sidecar_context"])
        self.assertIn("source_closure", handoff["missing_sidecar_context"])
        self.assertNotIn("host_probe_metadata", handoff["missing_sidecar_context"])
        self.assertFalse(handoff["sidecar_context_metadata_ready"])

    def test_runtime_wrapper_reads_sidecar_context_json_but_still_does_not_execute(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import (
            SIDECAR_CONTEXT_JSON_ENV,
            run_rtlmeter_verilator_wrapper,
        )

        stderr = io.StringIO()
        code = run_rtlmeter_verilator_wrapper(
            self._expanded_sidecar_argv_with_mdir(),
            environ={SIDECAR_CONTEXT_JSON_ENV: json.dumps(self._minimal_sidecar_context()), "PATH": ""},
            runner=lambda *args, **kwargs: self.fail("sidecar execution is not implemented in this wrapper"),
            stderr=stderr,
        )
        report = json.loads(stderr.getvalue())

        self.assertEqual(code, 2)
        handoff = report["handoff_metadata"]
        self.assertIsNone(report["sidecar_context_parse_error"])
        self.assertEqual(handoff["status"], "rtlmeter_sidecar_handoff_metadata_ready")
        self.assertTrue(handoff["sidecar_context_metadata_ready"])
        self.assertFalse(handoff["sidecar_context_ready"])
        self.assertFalse(report["sidecar_execution_invoked"])

    def test_rtlmeter_sidecar_launcher_invocation_blocks_unresolved_context(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_contract_mapping import map_rtlmeter_case_to_sidecar_contract
        from rtlmeter_sidecar_handoff import (
            build_rtlmeter_sidecar_context_candidate,
            build_rtlmeter_sidecar_handoff,
            build_rtlmeter_sidecar_launcher_invocation,
        )

        contract = map_rtlmeter_case_to_sidecar_contract(
            "Example:kind:hello",
            compile_args=("--sim-accel", "sidecar-gpu", "--sim-accel-states", "64", "--sim-accel-steps", "1"),
        )
        handoff = build_rtlmeter_sidecar_handoff(
            self._expanded_sidecar_argv_with_mdir(),
            sidecar_context=build_rtlmeter_sidecar_context_candidate(
                contract,
                template_or_target_registry_entry="config/slice_launch_templates/rtlmeter_example_kind_hello.json",
            ),
        )
        invocation = build_rtlmeter_sidecar_launcher_invocation(handoff)

        self.assertEqual(invocation["status"], "rtlmeter_sidecar_launcher_invocation_blocked")
        self.assertIn("handoff_metadata_ready", invocation["missing_invocation_context"])
        self.assertIn("sidecar_context.source_closure", invocation["missing_invocation_context"])
        self.assertIn("template_file", invocation["missing_invocation_context"])
        self.assertIsNone(invocation["launcher_command_argv"])
        self.assertFalse(invocation["sidecar_launcher_invoked"])
        self.assertFalse(invocation["execution_performed"])

    def test_rtlmeter_launcher_invocation_does_not_trust_forged_metadata_ready_with_incomplete_closure(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_contract_mapping import map_rtlmeter_case_to_sidecar_contract
        from rtlmeter_sidecar_handoff import (
            build_rtlmeter_sidecar_context_candidate,
            build_rtlmeter_sidecar_handoff,
            build_rtlmeter_sidecar_launcher_invocation,
        )

        contract = map_rtlmeter_case_to_sidecar_contract("Example:kind:hello")
        context = build_rtlmeter_sidecar_context_candidate(
            contract,
            template_or_target_registry_entry="config/slice_launch_templates/rtlmeter_example_kind_hello.json",
        )
        handoff = build_rtlmeter_sidecar_handoff(
            self._expanded_sidecar_argv_with_mdir(),
            sidecar_context=context,
        )
        handoff["status"] = "rtlmeter_sidecar_handoff_metadata_ready"
        invocation = build_rtlmeter_sidecar_launcher_invocation(handoff)

        self.assertEqual(invocation["status"], "rtlmeter_sidecar_launcher_invocation_blocked")
        self.assertIn("sidecar_context.source_closure", invocation["missing_invocation_context"])
        self.assertIsNone(invocation["launcher_command_argv"])

    def test_rtlmeter_launcher_invocation_blocks_missing_template_file(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import (
            build_rtlmeter_sidecar_handoff,
            build_rtlmeter_sidecar_launcher_invocation,
        )

        context = self._minimal_sidecar_context()
        context["template_or_target_registry_entry"] = (
            "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
        )
        handoff = build_rtlmeter_sidecar_handoff(
            self._expanded_sidecar_argv_with_mdir(),
            sidecar_context=context,
        )
        invocation = build_rtlmeter_sidecar_launcher_invocation(handoff)

        self.assertEqual(invocation["status"], "rtlmeter_sidecar_launcher_invocation_blocked")
        self.assertIn("template_file", invocation["missing_invocation_context"])
        self.assertIsNone(invocation["launcher_command_argv"])

    def test_rtlmeter_launcher_invocation_blocks_template_target_mismatch(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import (
            build_rtlmeter_sidecar_handoff,
            build_rtlmeter_sidecar_launcher_invocation,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            template = root / "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            template.parent.mkdir(parents=True)
            template.write_text(json.dumps({"target": "wrong_target"}), encoding="utf-8")
            context = self._minimal_sidecar_context()
            context["template_or_target_registry_entry"] = (
                "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            )
            handoff = build_rtlmeter_sidecar_handoff(
                self._expanded_sidecar_argv_with_mdir(),
                sidecar_context=context,
            )
            invocation = build_rtlmeter_sidecar_launcher_invocation(handoff, repo_root=root)

        self.assertEqual(invocation["status"], "rtlmeter_sidecar_launcher_invocation_blocked")
        self.assertIn("template_target_match", invocation["missing_invocation_context"])
        self.assertIsNone(invocation["launcher_command_argv"])

    def test_rtlmeter_sidecar_launcher_invocation_materializes_argv_without_execution(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import (
            build_rtlmeter_sidecar_handoff,
            build_rtlmeter_sidecar_launcher_invocation,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            template = root / "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            template.parent.mkdir(parents=True)
            template.write_text(json.dumps({"target": "rtlmeter_example_kind_hello"}), encoding="utf-8")
            context = self._minimal_sidecar_context()
            context["template_or_target_registry_entry"] = (
                "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            )
            handoff = build_rtlmeter_sidecar_handoff(
                self._expanded_sidecar_argv_with_mdir(),
                sidecar_context=context,
            )
            invocation = build_rtlmeter_sidecar_launcher_invocation(handoff, repo_root=root)

        self.assertEqual(invocation["status"], "rtlmeter_sidecar_launcher_invocation_metadata_ready")
        self.assertEqual(
            invocation["launcher_command_argv"],
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/rtlmeter_example_kind_hello.json",
                "--shape",
                "64x1",
            ],
        )
        self.assertFalse(invocation["sidecar_launcher_invoked"])
        self.assertFalse(invocation["sidecar_execution_invoked"])
        self.assertFalse(invocation["coverage_output_compare_reached"])
        self.assertFalse(invocation["execution_performed"])

    def test_materialized_wrapper_is_named_verilator_and_executable(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import write_rtlmeter_verilator_wrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper = write_rtlmeter_verilator_wrapper(Path(temp_dir) / "verilator", python_executable="python3")

            self.assertEqual(wrapper.name, "verilator")
            self.assertTrue(os.access(wrapper, os.X_OK))
            self.assertIn("rtlmeter_verilator_wrapper_runtime.py", wrapper.read_text(encoding="utf-8"))

    def test_materialized_wrapper_delegates_no_gpu_argv_preserving_process_behavior(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import write_rtlmeter_verilator_wrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wrapper = write_rtlmeter_verilator_wrapper(
                root / "wrapper" / "verilator",
                python_executable=sys.executable,
            )
            real = root / "real" / "verilator"
            real.parent.mkdir()
            self._write_executable(
                real,
                "#!/bin/sh\n"
                "printf 'real stdout:%s\\n' \"$*\"\n"
                "printf 'real stderr:%s\\n' \"$*\" >&2\n"
                "exit 7\n",
            )

            completed = subprocess.run(
                [str(wrapper), "--cc", "--top-module", "top", "-f", "filelist"],
                env={**os.environ, "PATH": f"{wrapper.parent}{os.pathsep}{real.parent}"},
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 7)
        self.assertIn("real stdout:--cc --top-module top -f filelist", completed.stdout)
        self.assertIn("real stderr:--cc --top-module top -f filelist", completed.stderr)

    def test_materialized_wrapper_gpu_intent_fails_closed_without_delegating(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import write_rtlmeter_verilator_wrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wrapper = write_rtlmeter_verilator_wrapper(
                root / "wrapper" / "verilator",
                python_executable=sys.executable,
            )
            real = root / "real" / "verilator"
            real.parent.mkdir()
            self._write_executable(
                real,
                "#!/bin/sh\n"
                "echo should-not-delegate\n"
                "exit 99\n",
            )

            completed = subprocess.run(
                [str(wrapper), "--cc", "--top-module", "top", "-f", "filelist", "--use-gpu"],
                env={**os.environ, "PATH": f"{wrapper.parent}{os.pathsep}{real.parent}"},
                text=True,
                capture_output=True,
                check=False,
            )
            report = json.loads(completed.stderr)

        self.assertEqual(completed.returncode, 2)
        self.assertEqual(report["status"], "use_gpu_requires_explicit_sidecar_schedule")
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["delegated_to_real_verilator"])
        self.assertIsNone(report["launcher_invocation"])
        self.assertIsNone(report["stdout_cycles_execution_plan"])
        self.assertIsNone(report["stdout_cycles_runner_contract"])
        self.assertIsNone(report["stdout_cycles_runner_implementation"])
        self.assertIsNone(report["stdout_cycles_runner_adapter_implementation"])
        self.assertNotIn("should-not-delegate", completed.stdout)

    def test_materialized_wrapper_gpu_intent_with_missing_inputs_reports_inspection(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import write_rtlmeter_verilator_wrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wrapper = write_rtlmeter_verilator_wrapper(
                root / "wrapper" / "verilator",
                python_executable=sys.executable,
            )
            real = root / "real" / "verilator"
            real.parent.mkdir()
            self._write_executable(
                real,
                "#!/bin/sh\n"
                "echo should-not-delegate\n"
                "exit 99\n",
            )

            completed = subprocess.run(
                [str(wrapper), "--cc", "--use-gpu"],
                env={**os.environ, "PATH": f"{wrapper.parent}{os.pathsep}{real.parent}"},
                text=True,
                capture_output=True,
                check=False,
            )
            report = json.loads(completed.stderr)

        self.assertEqual(completed.returncode, 2)
        self.assertEqual(report["status"], "unsupported_gpu_request_fail_closed")
        self.assertEqual(report["inspection_status"], "unsupported_rtlmeter_sidecar_request")
        self.assertIn("--top-module <top>", report["missing_required_inputs"])
        self.assertIn("-f <filelist>", report["missing_required_inputs"])
        self.assertEqual(report["wrapper_inspection"]["status"], "unsupported_rtlmeter_sidecar_request")
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["delegated_to_real_verilator"])
        self.assertIsNone(report["launcher_invocation"])
        self.assertIsNone(report["stdout_cycles_execution_plan"])
        self.assertIsNone(report["stdout_cycles_runner_contract"])
        self.assertIsNone(report["stdout_cycles_runner_implementation"])
        self.assertIsNone(report["stdout_cycles_runner_adapter_implementation"])
        self.assertNotIn("should-not-delegate", completed.stdout)

    def _reviewed_source_closure_for_reentry_guard(self) -> dict[str, object]:
        return {
            "status": "complete",
            "authority": "reviewed_hybrid_execution_source_closure",
            "authority_scope": "rtlmeter_stdout_cycles_sidecar_runner",
            "target": "rtlmeter_example_kind_hello",
            "mode": "rtlmeter_first_seed",
            "rtlmeter_case": "Example:kind:hello",
            "source_gate_or_manifest_ref": "for_codex/issues/FC-034-rtlmeter-first-seed-execution-integration.md",
            "source_files": [
                "third_party/rtlmeter/designs/Example/src/top.v",
                "third_party/rtlmeter/rtl/__rtlmeter_utils.sv",
            ],
            "include_files": ["third_party/rtlmeter/rtl/__rtlmeter_top_include.vh"],
            "filelist_entries": [
                "verilogSourceFiles/top.v",
                "rtl/__rtlmeter_utils.sv",
                "rtl/__rtlmeter_top_include.vh",
            ],
            "observables": ["normalized_stdout", "rtlmeter_cycles"],
            "runner_strategy": "rtlmeter_stdout_cycles_direct_wrapper",
            "host_probe_contract_status": "reviewed_for_rtlmeter_sidecar",
            "cpu_as_gpu_fallback_allowed": False,
            "review_evidence": {
                "reviewed": True,
                "review_ref": "for_codex/issues/FC-034-rtlmeter-first-seed-execution-integration.md",
            },
        }

    def _reviewed_rtlmeter_context_for_reentry_guard(self) -> dict[str, object]:
        context = self._minimal_sidecar_context()
        context["template_or_target_registry_entry"] = (
            "config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json"
        )
        context["source_closure"] = self._reviewed_source_closure_for_reentry_guard()
        return context

    def test_runtime_wrapper_reentry_guard_blocks_recursive_rtlmeter_runner_argv(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import (
            SIDECAR_CONTEXT_JSON_ENV,
            run_rtlmeter_verilator_wrapper,
        )
        from rtlmeter_verilator_wrapper_phase import PHASE_ENV

        calls = []

        def fake_runner(*args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(args[0], 0)

        stderr = io.StringIO()
        code = run_rtlmeter_verilator_wrapper(
            self._expanded_sidecar_argv(),
            environ={
                SIDECAR_CONTEXT_JSON_ENV: json.dumps(self._reviewed_rtlmeter_context_for_reentry_guard()),
                "PATH": "",
            },
            runner=fake_runner,
            stderr=stderr,
        )
        report = json.loads(stderr.getvalue())
        adapter_implementation = report["stdout_cycles_runner_adapter_implementation"]
        reentry_guard = report["reentry_guard"]

        self.assertEqual(code, 2)
        self.assertEqual(calls, [])
        self.assertEqual(
            adapter_implementation["status"],
            "rtlmeter_stdout_cycles_runner_adapter_implementation_runner_argv_ready",
        )
        self.assertIsNotNone(adapter_implementation["runner_command_argv"])
        self.assertEqual(
            reentry_guard["status"],
            "rtlmeter_wrapper_reentry_guard_blocked_recursive_rtlmeter_run",
        )
        self.assertEqual(reentry_guard["phase_env"], PHASE_ENV)
        self.assertIsNone(reentry_guard["wrapper_phase"])
        self.assertTrue(reentry_guard["runner_command_present"])
        self.assertTrue(reentry_guard["runner_command_invokes_rtlmeter_run"])
        self.assertFalse(reentry_guard["runner_command_safe_to_execute_from_wrapper"])
        self.assertFalse(reentry_guard["direct_sidecar_verilate_phase_allowed"])
        self.assertFalse(reentry_guard["execution_authority"])
        self.assertFalse(reentry_guard["sidecar_execution_invoked"])
        self.assertFalse(reentry_guard["cpu_as_gpu_fallback"])

    def test_runtime_wrapper_rtlmeter_run_phase_keeps_runner_argv_metadata_only(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import (
            SIDECAR_CONTEXT_JSON_ENV,
            run_rtlmeter_verilator_wrapper,
        )
        from rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_RTL_METER_RUN, PHASE_SIDECAR_VERILATE

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wrapper = root / "wrapper" / "verilator"
            real = root / "real" / "verilator"
            wrapper.parent.mkdir()
            real.parent.mkdir()
            self._touch_executable(wrapper)
            self._touch_executable(real)
            calls = []

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                return subprocess.CompletedProcess(command, 19)

            argv = [
                "--cc",
                "--top-module",
                "top",
                "-f",
                "filelist",
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "64",
                "--sim-accel-steps",
                "1",
            ]
            stderr = io.StringIO()
            code = run_rtlmeter_verilator_wrapper(
                argv,
                executable=wrapper,
                environ={
                    SIDECAR_CONTEXT_JSON_ENV: json.dumps(self._reviewed_rtlmeter_context_for_reentry_guard()),
                    PHASE_ENV: PHASE_RTL_METER_RUN,
                    "PATH": f"{wrapper.parent}{os.pathsep}{real.parent}",
                },
                runner=fake_runner,
                stderr=stderr,
            )

        self.assertEqual(code, 19)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(calls[0][0], [str(real), *argv])
        self.assertEqual(calls[0][1]["env"][PHASE_ENV], PHASE_SIDECAR_VERILATE)
        flat_command = " ".join(calls[0][0])
        self.assertNotIn("rtlmeter run", flat_command)
        self.assertNotIn("rtlmeter_stdout_cycles_sidecar_runner.py", flat_command)
        self.assertNotIn("run_hybrid_template.py", flat_command)

    def test_runtime_wrapper_sidecar_verilate_phase_blocks_reentry(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import (
            SIDECAR_CONTEXT_JSON_ENV,
            run_rtlmeter_verilator_wrapper,
        )
        from rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_SIDECAR_VERILATE

        calls = []

        def fake_runner(*args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(args[0], 0)

        stderr = io.StringIO()
        code = run_rtlmeter_verilator_wrapper(
            self._expanded_sidecar_argv(),
            environ={
                SIDECAR_CONTEXT_JSON_ENV: json.dumps(self._reviewed_rtlmeter_context_for_reentry_guard()),
                PHASE_ENV: PHASE_SIDECAR_VERILATE,
                "PATH": "",
            },
            runner=fake_runner,
            stderr=stderr,
        )
        report = json.loads(stderr.getvalue())
        reentry_guard = report["reentry_guard"]

        self.assertEqual(code, 2)
        self.assertEqual(calls, [])
        self.assertEqual(
            reentry_guard["status"],
            "rtlmeter_wrapper_reentry_guard_blocked_sidecar_verilate_reentry",
        )
        self.assertEqual(reentry_guard["phase_env"], PHASE_ENV)
        self.assertEqual(reentry_guard["wrapper_phase"], PHASE_SIDECAR_VERILATE)
        self.assertFalse(reentry_guard["runner_command_safe_to_execute_from_wrapper"])
        self.assertFalse(reentry_guard["direct_sidecar_verilate_phase_allowed"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["sidecar_execution_invoked"])

    def test_rtlmeter_sidecar_handoff_uses_verilator_default_mdir_when_omitted(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_handoff

        handoff = build_rtlmeter_sidecar_handoff(
            [
                "--cc",
                "--main",
                "--top-module",
                "top",
                "-f",
                "filelist",
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "64",
                "--sim-accel-steps",
                "1",
            ],
            sidecar_context=self._reviewed_rtlmeter_context_for_reentry_guard(),
        )

        self.assertEqual(handoff["status"], "rtlmeter_sidecar_handoff_metadata_ready")
        self.assertEqual(handoff["missing_sidecar_context"], [])
        self.assertEqual(handoff["parser_payload"]["mdir"], "obj_dir")
        self.assertEqual(handoff["parser_payload_mdir_source"], "verilator_default_obj_dir")
        self.assertTrue(handoff["sidecar_context_metadata_ready"])
        self.assertFalse(handoff["sidecar_execution_invoked"])

    def test_rtlmeter_sidecar_handoff_rejects_complete_status_without_execution_authority(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_handoff

        context = self._reviewed_rtlmeter_context_for_reentry_guard()
        context["source_closure"] = {
            "status": "complete",
            "source_files": ["third_party/rtlmeter/designs/Example/src/top.v"],
            "include_files": ["third_party/rtlmeter/rtl/__rtlmeter_top_include.vh"],
        }
        handoff = build_rtlmeter_sidecar_handoff(
            self._expanded_sidecar_argv_with_mdir(),
            sidecar_context=context,
        )

        self.assertEqual(handoff["status"], "rtlmeter_sidecar_handoff_blocked_missing_context")
        self.assertIn("source_closure", handoff["missing_sidecar_context"])
        self.assertFalse(handoff["sidecar_context_metadata_ready"])
        self.assertFalse(handoff["sidecar_execution_invoked"])

    def test_rtlmeter_sidecar_handoff_rejects_thin_complete_source_closure(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_handoff

        context = self._reviewed_rtlmeter_context_for_reentry_guard()
        context["source_closure"] = {
            "status": "complete",
            "authority": "reviewed_hybrid_execution_source_closure",
        }
        handoff = build_rtlmeter_sidecar_handoff(
            self._expanded_sidecar_argv_with_mdir(),
            sidecar_context=context,
        )

        self.assertEqual(handoff["status"], "rtlmeter_sidecar_handoff_blocked_missing_context")
        self.assertIn("source_closure", handoff["missing_sidecar_context"])
        self.assertFalse(handoff["sidecar_context_metadata_ready"])
        self.assertFalse(handoff["sidecar_execution_invoked"])

    def _reviewed_template_payload_for_launcher_guard(
        self,
        target: str = "rtlmeter_example_kind_hello",
    ) -> dict[str, object]:
        return {
            "target": target,
            "template_execution_role": "runnable_hybrid_template",
            "source_closure": self._reviewed_source_closure_for_reentry_guard(),
        }

    def _launcher_invocation_for_guard(
        self,
        context: dict[str, object],
        *,
        repo_root: Path | None = None,
    ) -> dict[str, object]:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import (
            build_rtlmeter_sidecar_handoff,
            build_rtlmeter_sidecar_launcher_invocation,
        )

        handoff = build_rtlmeter_sidecar_handoff(
            self._expanded_sidecar_argv_with_mdir(),
            sidecar_context=context,
        )
        if repo_root is None:
            return build_rtlmeter_sidecar_launcher_invocation(handoff)
        return build_rtlmeter_sidecar_launcher_invocation(handoff, repo_root=repo_root)

    def test_rtlmeter_launcher_invocation_blocks_template_without_source_closure_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            template = root / "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            template.parent.mkdir(parents=True)
            template.write_text(
                json.dumps({"target": "rtlmeter_example_kind_hello", "source_closure": {"status": "complete"}}),
                encoding="utf-8",
            )
            context = self._reviewed_rtlmeter_context_for_reentry_guard()
            context["template_or_target_registry_entry"] = (
                "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            )
            invocation = self._launcher_invocation_for_guard(context, repo_root=root)

        self.assertEqual(invocation["status"], "rtlmeter_sidecar_launcher_invocation_blocked")
        self.assertIn("template_source_closure.authority", invocation["missing_invocation_context"])
        self.assertIsNone(invocation["launcher_command_argv"])
        self.assertFalse(invocation["execution_performed"])

    def test_rtlmeter_launcher_invocation_blocks_runtime_template_without_execution_role(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            template = root / "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            template.parent.mkdir(parents=True)
            payload = self._reviewed_template_payload_for_launcher_guard()
            payload.pop("template_execution_role")
            template.write_text(json.dumps(payload), encoding="utf-8")
            context = self._reviewed_rtlmeter_context_for_reentry_guard()
            context["template_or_target_registry_entry"] = (
                "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            )
            invocation = self._launcher_invocation_for_guard(context, repo_root=root)

        self.assertEqual(invocation["status"], "rtlmeter_sidecar_launcher_invocation_blocked")
        self.assertIn("template_execution_role", invocation["missing_invocation_context"])
        self.assertIsNone(invocation["launcher_command_argv"])
        self.assertFalse(invocation["execution_performed"])

    def test_rtlmeter_launcher_invocation_blocks_metadata_only_runtime_template_role(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            template = root / "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            template.parent.mkdir(parents=True)
            payload = self._reviewed_template_payload_for_launcher_guard()
            payload["template_execution_role"] = "metadata_only"
            template.write_text(json.dumps(payload), encoding="utf-8")
            context = self._reviewed_rtlmeter_context_for_reentry_guard()
            context["template_or_target_registry_entry"] = (
                "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            )
            invocation = self._launcher_invocation_for_guard(context, repo_root=root)

        self.assertEqual(invocation["status"], "rtlmeter_sidecar_launcher_invocation_blocked")
        self.assertIn("template_execution_role", invocation["missing_invocation_context"])
        self.assertIsNone(invocation["launcher_command_argv"])
        self.assertFalse(invocation["execution_performed"])

    def _reviewed_authority_registry_payload_for_registry_guard(self) -> dict[str, object]:
        return {
            "schema_role": "rtlmeter_sidecar_authority",
            "runtime_launchable": False,
            "target": "rtlmeter_example_kind_hello",
            "source_closure": self._reviewed_source_closure_for_reentry_guard(),
        }

    def test_rtlmeter_launcher_invocation_uses_authority_registry_without_materializing_argv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry = root / "config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json"
            registry.parent.mkdir(parents=True)
            registry.write_text(
                json.dumps(self._reviewed_authority_registry_payload_for_registry_guard()),
                encoding="utf-8",
            )
            context = self._reviewed_rtlmeter_context_for_reentry_guard()
            context["template_or_target_registry_entry"] = (
                "config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json"
            )
            invocation = self._launcher_invocation_for_guard(context, repo_root=root)

        self.assertEqual(invocation["status"], "rtlmeter_sidecar_launcher_invocation_blocked")
        self.assertEqual(
            invocation["authority_registry_entry"],
            "config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json",
        )
        self.assertIn("runtime_launch_template", invocation["missing_invocation_context"])
        self.assertIsNone(invocation["runtime_launch_template"])
        self.assertIsNone(invocation["launcher_command_argv"])
        self.assertFalse(invocation["execution_performed"])

    def test_rtlmeter_launcher_invocation_rejects_runtime_launchable_authority_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry = root / "config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json"
            template = root / "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            registry.parent.mkdir(parents=True)
            template.parent.mkdir(parents=True)
            registry_payload = self._reviewed_authority_registry_payload_for_registry_guard()
            registry_payload["runtime_launchable"] = True
            registry_payload["runtime_launch_template"] = (
                "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            )
            registry.write_text(json.dumps(registry_payload), encoding="utf-8")
            template.write_text(
                json.dumps(self._reviewed_template_payload_for_launcher_guard()),
                encoding="utf-8",
            )
            context = self._reviewed_rtlmeter_context_for_reentry_guard()
            context["template_or_target_registry_entry"] = (
                "config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json"
            )
            invocation = self._launcher_invocation_for_guard(context, repo_root=root)

        self.assertEqual(invocation["status"], "rtlmeter_sidecar_launcher_invocation_blocked")
        self.assertIn("authority_registry.runtime_launchable", invocation["missing_invocation_context"])
        self.assertIsNone(invocation["launcher_command_argv"])
        self.assertFalse(invocation["execution_performed"])

    def test_rtlmeter_sidecar_launcher_invocation_materializes_argv_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            template = root / "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            template.parent.mkdir(parents=True)
            template.write_text(
                json.dumps(self._reviewed_template_payload_for_launcher_guard()),
                encoding="utf-8",
            )
            context = self._reviewed_rtlmeter_context_for_reentry_guard()
            context["template_or_target_registry_entry"] = (
                "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            )
            invocation = self._launcher_invocation_for_guard(context, repo_root=root)

        self.assertEqual(invocation["status"], "rtlmeter_sidecar_launcher_invocation_metadata_ready")
        self.assertEqual(
            invocation["launcher_command_argv"],
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/rtlmeter_example_kind_hello.json",
                "--shape",
                "64x1",
            ],
        )
        self.assertEqual(invocation["launcher_command_role"], "materialized_for_later_run_not_invoked")
        self.assertFalse(invocation["sidecar_launcher_invoked"])
        self.assertFalse(invocation["sidecar_execution_invoked"])
        self.assertFalse(invocation["coverage_output_compare_reached"])
        self.assertFalse(invocation["execution_performed"])
        self.assertFalse(invocation["measurement_performed"])

    def test_runtime_wrapper_missing_real_verilator_fails_without_cpu_fallback(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import SIDECAR_CONTEXT_JSON_ENV, run_rtlmeter_verilator_wrapper
        from rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_RTL_METER_RUN

        argv = [
            "--cc", "--top-module", "top", "-f", "filelist",
            "--sim-accel", "sidecar-gpu", "--sim-accel-states", "64", "--sim-accel-steps", "1",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper = Path(temp_dir) / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            self._touch_executable(wrapper)
            stderr = io.StringIO()
            code = run_rtlmeter_verilator_wrapper(
                argv,
                executable=wrapper,
                environ={
                    SIDECAR_CONTEXT_JSON_ENV: json.dumps(self._reviewed_rtlmeter_context_for_reentry_guard()),
                    PHASE_ENV: PHASE_RTL_METER_RUN,
                    "PATH": str(wrapper.parent),
                },
                runner=lambda *args, **kwargs: self.fail("missing real Verilator must fail closed"),
                stderr=stderr,
            )
        report = json.loads(stderr.getvalue())

        self.assertEqual(code, 127)
        self.assertEqual(report["status"], "real_verilator_missing")
        self.assertEqual(report["wrapper_phase"], PHASE_RTL_METER_RUN)
        self.assertTrue(report["direct_sidecar_verilate_attempted"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["delegated_to_real_verilator"])
        self.assertFalse(report["sidecar_execution_invoked"])


    def test_runtime_wrapper_rejects_thin_env_source_closure_without_delegating(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import SIDECAR_CONTEXT_JSON_ENV, run_rtlmeter_verilator_wrapper

        context = self._reviewed_rtlmeter_context_for_reentry_guard()
        context["source_closure"] = {"status": "complete", "authority": "reviewed_hybrid_execution_source_closure"}
        stderr = io.StringIO()
        code = run_rtlmeter_verilator_wrapper(
            self._expanded_sidecar_argv(),
            environ={SIDECAR_CONTEXT_JSON_ENV: json.dumps(context), "PATH": ""},
            runner=lambda *args, **kwargs: self.fail("thin source closure must not delegate"),
            stderr=stderr,
        )
        report = json.loads(stderr.getvalue())
        contract = report["stdout_cycles_runner_contract"]

        self.assertEqual(code, 2)
        self.assertFalse(report["execution_authority"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["delegated_to_real_verilator"])
        self.assertFalse(report["sidecar_execution_invoked"])
        self.assertIn("handoff_metadata_ready", contract["missing_runner_context"])
        self.assertIn("sidecar_context.source_closure.authority_scope", contract["missing_runner_context"])
        self.assertIn("sidecar_context.source_closure.rtlmeter_case", contract["missing_runner_context"])
        self.assertIn("sidecar_context.source_closure.review_evidence", contract["missing_runner_context"])
        self.assertFalse(contract["sidecar_execution_invoked"])
