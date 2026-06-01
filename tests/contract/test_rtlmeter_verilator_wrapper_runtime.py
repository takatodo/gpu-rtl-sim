import io
import json
import os
import subprocess
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVerilatorWrapperRuntimeTest(HybridCliTestCase):
    def _touch_executable(self, path: Path) -> None:
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)

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
            [
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
            ],
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
            [
                "--cc",
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
            [
                "--cc",
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
            [
                "--cc",
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
            [
                "--cc",
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
            [
                "--cc",
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
            [
                "--cc",
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
                [
                    "--cc",
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
                [
                    "--cc",
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
