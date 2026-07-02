import json
import os
import subprocess
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


def _write_minimal_rtlmeter_tree(root: Path) -> None:
    rtlmeter_root = root / "third_party/rtlmeter"
    (rtlmeter_root / "venv/bin").mkdir(parents=True)
    (rtlmeter_root / "src").mkdir(parents=True)
    (rtlmeter_root / "designs/Example/src").mkdir(parents=True)
    (rtlmeter_root / "rtl").mkdir(parents=True)
    (rtlmeter_root / "rtlmeter").write_text("#!/bin/sh\n", encoding="utf-8")
    (rtlmeter_root / "venv/bin/python3").write_text("#!/bin/sh\n", encoding="utf-8")
    (rtlmeter_root / "designs/Example/descriptor.yaml").write_text(
        "\n".join(
            [
                "compile:",
                "  verilogSourceFiles:",
                "    - src/top.v",
                "  topModule: top",
                "  mainClock: top.clk",
                "configurations:",
                "  kind:",
                "    compile: {}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (rtlmeter_root / "designs/Example/src/top.v").write_text("module top; endmodule\n", encoding="utf-8")
    (rtlmeter_root / "rtl/__rtlmeter_utils.sv").write_text("", encoding="utf-8")
    (rtlmeter_root / "rtl/__rtlmeter_top_include.vh").write_text("", encoding="utf-8")


def _write_executable_vsim_sidecar_proxy(root: Path) -> str:
    proxy = root / "bin" / "rtlmeter-vsim-sidecar-proxy"
    proxy.parent.mkdir(exist_ok=True)
    proxy.write_text("#!/bin/sh\nexit 126\n", encoding="utf-8")
    proxy.chmod(0o755)
    (proxy.parent / f"{proxy.name}.review.json").write_text(
        json.dumps(
            {
                "schema_role": "rtlmeter_vsim_sidecar_proxy_target_review",
                "target_path": proxy.relative_to(root).as_posix(),
                "reviewed_proxy_target": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return proxy.as_posix()


class RtlmeterCpuGpuCompareIntegrationTest(HybridCliTestCase):
    def test_default_run_is_non_executing_and_report_safe(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import run_rtlmeter_cpu_gpu_compare_integration

        report = run_rtlmeter_cpu_gpu_compare_integration(environ={})

        self.assertEqual(report["surface"], "rtlmeter_cpu_gpu_compare_integration")
        self.assertEqual(report["status"], "opt_in_required")
        self.assertEqual(report["seed"], "Example:kind:hello")
        self.assertFalse(report["canonical_project_state_changed"])
        self.assertFalse(report["generated_report_is_source_of_truth"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["ran_commands"])
        self.assertIsNone(report["stdout_cycles_sidecar_runner"])
        self.assertEqual(report["commands"]["cpu"][0], "third_party/rtlmeter/rtlmeter")
        self.assertIn(
            "--compileArgs=--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1",
            report["commands"]["gpu"],
        )
        plan = report["stdout_cycles_execution_plan"]
        self.assertEqual(plan["surface"], "rtlmeter_stdout_cycles_execution_plan")
        self.assertEqual(plan["observables"], ["normalized_stdout", "rtlmeter_cycles"])
        self.assertFalse(plan["execution_performed"])
        self.assertFalse(plan["measurement_performed"])
        self.assertFalse(plan["uses_run_hybrid_template"])
        self.assertEqual(plan["cpu_reference"]["owner"], "rtlmeter")
        self.assertEqual(plan["gpu_candidate"]["owner"], "sidecar")
        self.assertEqual(plan["gpu_candidate"]["execution_kind"], "sidecar_required")
        self.assertEqual(plan["gpu_candidate"]["fallback_policy"], "forbidden")
        self.assertFalse(plan["gpu_candidate"]["cpu_as_gpu_fallback_allowed"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_fails_closed_when_prerequisites_are_missing(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import OPT_IN_ENV, run_rtlmeter_cpu_gpu_compare_integration

        with tempfile.TemporaryDirectory() as temp_dir:
            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=Path(temp_dir),
                environ={OPT_IN_ENV: "1", "PATH": ""},
            )

        self.assertEqual(report["status"], "cannot_execute")
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["ran_commands"])
        self.assertGreater(len(report["missing_prerequisites"]), 0)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_preflight_requires_named_executable_wrapper(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import _preflight

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            real_verilator_dir = root / "bin"
            real_verilator_dir.mkdir()
            real_verilator = real_verilator_dir / "verilator"
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")

            missing = _preflight(
                repo_root=root,
                sidecar_wrapper=wrapper.as_posix(),
                path_env=real_verilator_dir.as_posix(),
            )

        self.assertIn("RTLMETER_SIDECAR_VERILATOR_WRAPPER executable bit", missing)

    def test_preflight_accepts_explicit_real_verilator_without_path_real(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            REAL_VERILATOR_ENV,
            REAL_VERILATOR_PREFLIGHT_SELECTED,
            _sanitize,
            build_real_verilator_preflight,
        )

        self.assertEqual(_sanitize("/usr/local/bin/verilator"), "<local-absolute-path>")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            real_verilator = root / "real" / "verilator"
            real_verilator.parent.mkdir()
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)

            report = build_real_verilator_preflight(
                repo_root=root,
                sidecar_wrapper=wrapper.as_posix(),
                environ={REAL_VERILATOR_ENV: real_verilator.as_posix(), "PATH": ""},
            )

        self.assertEqual(report["status"], REAL_VERILATOR_PREFLIGHT_SELECTED)
        self.assertEqual(report["selected_real_verilator_source"], REAL_VERILATOR_ENV)
        self.assertEqual(report["missing_prerequisites"], [])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execution_env_absolutizes_repo_relative_real_verilator(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            OPT_IN_ENV,
            REAL_VERILATOR_ENV,
            REAL_VERILATOR_PREFLIGHT_SELECTED,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            real_verilator = bin_dir / "verilator"
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)
            calls = []

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                return subprocess.CompletedProcess(command, 1, stdout="", stderr="stop after CPU")

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={
                    OPT_IN_ENV: "1",
                    WRAPPER_ENV: wrapper.as_posix(),
                    REAL_VERILATOR_ENV: "bin/verilator",
                    "PATH": "",
                },
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "cpu_execution_failed")
        self.assertEqual(report["real_verilator_preflight"]["status"], REAL_VERILATOR_PREFLIGHT_SELECTED)
        self.assertEqual(report["real_verilator_preflight"]["selected_real_verilator_source"], REAL_VERILATOR_ENV)
        self.assertEqual(calls[0][1]["env"][REAL_VERILATOR_ENV], real_verilator.as_posix())

    def test_preflight_rejects_wrapper_only_path_as_real_verilator_missing(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            REAL_VERILATOR_PREFLIGHT_MISSING,
            build_real_verilator_preflight,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)

            report = build_real_verilator_preflight(
                repo_root=root,
                sidecar_wrapper=wrapper.as_posix(),
                environ={"PATH": wrapper.parent.as_posix()},
            )

        self.assertEqual(report["status"], REAL_VERILATOR_PREFLIGHT_MISSING)
        self.assertEqual(report["real_verilator_resolution"], "missing_after_excluding_wrapper")
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["sidecar_execution_invoked"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execution_env_prepends_rtlmeter_root_for_repo_root_launch(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            OPT_IN_ENV,
            REAL_VERILATOR_PREFLIGHT_SELECTED,
            SIDECAR_CONTEXT_JSON_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            real_verilator = bin_dir / "verilator"
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)
            calls = []

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                return subprocess.CompletedProcess(command, 1, stdout="", stderr="stop after CPU")

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={
                    OPT_IN_ENV: "1",
                    WRAPPER_ENV: wrapper.as_posix(),
                    "PATH": bin_dir.as_posix(),
                    "PYTHONPATH": "existing",
                },
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "cpu_execution_failed")
        self.assertEqual(report["real_verilator_preflight"]["status"], REAL_VERILATOR_PREFLIGHT_SELECTED)
        self.assertEqual(report["real_verilator_preflight"]["selected_real_verilator_source"], "wrapper_filtered_PATH")
        pythonpath = calls[0][1]["env"]["PYTHONPATH"].split(os.pathsep)
        self.assertEqual(pythonpath[:2], [(root / "third_party/rtlmeter").as_posix(), "existing"])
        metadata = report["sidecar_contract"]["frontend_owned_build_metadata"]
        self.assertEqual(
            metadata["extra_args"],
            ["--sim-accel", "sidecar-gpu", "--sim-accel-states", "64", "--sim-accel-steps", "1"],
        )
        self.assertIn("--sim-accel", metadata["verilator_command_argv"])
        self.assertEqual(report["sidecar_context_candidate"]["target"], "rtlmeter_example_kind_hello")
        self.assertEqual(
            report["sidecar_context_candidate"]["template_or_target_registry_entry"],
            "config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json",
        )
        self.assertNotIn(SIDECAR_CONTEXT_JSON_ENV, calls[0][1]["env"])

    def test_gpu_failure_includes_sanitized_verilate_diagnostic_log(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            BLOCKER_GPU_RUNNER_EXECUTION_FAILED,
            OPT_IN_ENV,
            SIDECAR_CONTEXT_JSON_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            real_verilator = bin_dir / "verilator"
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)
            log_path = (
                root
                / "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu/Example/kind/compile-0/_verilate/stdout.log"
            )
            calls = []

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                if len(calls) == 2:
                    log_path.parent.mkdir(parents=True)
                    log_path.write_text(
                        '/home/user/work -- diagnostic\n{"path": "/home/user/work/file.py"}\n',
                        encoding="utf-8",
                    )
                return subprocess.CompletedProcess(command, 0 if len(calls) == 1 else 2, stdout="", stderr="")

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={OPT_IN_ENV: "1", WRAPPER_ENV: wrapper.as_posix(), "PATH": bin_dir.as_posix()},
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "gpu_execution_failed")
        self.assertEqual(report["first_seed_handoff_evidence_status"], "blocked_before_compare")
        self.assertEqual(report["gpu_failure_blocker"], BLOCKER_GPU_RUNNER_EXECUTION_FAILED)
        self.assertEqual(
            report["cleaned_generated_work_roots"],
            [],
        )
        gpu_context = json.loads(calls[1][1]["env"][SIDECAR_CONTEXT_JSON_ENV])
        self.assertEqual(gpu_context["target"], "rtlmeter_example_kind_hello")
        self.assertEqual(gpu_context["source_closure"]["status"], "frontend_metadata_only_not_source_closure")
        self.assertIsNotNone(report["sidecar_context_candidate"])
        self.assertEqual(calls[1][0][0], "python3")
        self.assertEqual(calls[1][0][1], "src/tools/rtlmeter_stdout_cycles_sidecar_runner.py")
        self.assertIn("--", calls[1][0])
        self.assertIn("third_party/rtlmeter/rtlmeter", calls[1][0])
        self.assertEqual(
            report["stdout_cycles_sidecar_runner"]["status"],
            "rtlmeter_stdout_cycles_sidecar_runner_execution_failed",
        )
        self.assertTrue(report["stdout_cycles_sidecar_runner"]["subprocess_invoked"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["execution_performed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["reviewed_proxy_metadata_observed"])
        self.assertIn("<local-absolute-path>", report["gpu_failure_diagnostic_log"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_gpu_failure_classifies_missing_vsim_sidecar_proxy_env(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            BLOCKER_RTL_METER_VSIM_SIDECAR_PROXY_ENV_MISSING,
            OPT_IN_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            real_verilator = bin_dir / "verilator"
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)
            calls = []

            runner_report = {
                "status": "rtlmeter_stdout_cycles_sidecar_runner_vsim_sidecar_proxy_env_missing",
                "vsim_sidecar_proxy_env_present": False,
                "command_result": {
                    "returncode": 125,
                    "stderr": "missing RTLMETER_VSIM_SIDECAR_PROXY for RTLMeter sidecar proxy\n",
                },
            }

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                if len(calls) == 1:
                    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
                return subprocess.CompletedProcess(command, 125, stdout=json.dumps(runner_report), stderr="")

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={OPT_IN_ENV: "1", WRAPPER_ENV: wrapper.as_posix(), "PATH": bin_dir.as_posix()},
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "gpu_execution_failed")
        self.assertEqual(report["first_seed_handoff_evidence_status"], "blocked_before_compare")
        self.assertEqual(report["gpu_failure_blocker"], BLOCKER_RTL_METER_VSIM_SIDECAR_PROXY_ENV_MISSING)
        self.assertEqual(
            report["stdout_cycles_sidecar_runner"]["status"],
            "rtlmeter_stdout_cycles_sidecar_runner_vsim_sidecar_proxy_env_missing",
        )
        self.assertEqual(report["stdout_cycles_sidecar_runner"]["runner_stdout_report"]["command_result"]["returncode"], 125)
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["execution_performed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["reviewed_proxy_metadata_observed"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_gpu_failure_classifies_real_verilator_without_sim_accel_support(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            BLOCKER_REAL_VERILATOR_NOT_SIDECAR_CAPABLE,
            OPT_IN_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            real_verilator = bin_dir / "verilator"
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)
            log_path = (
                root
                / "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu/Example/kind/compile-0/_verilate/stdout.log"
            )
            calls = []

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                if len(calls) == 2:
                    log_path.parent.mkdir(parents=True)
                    log_path.write_text(
                        "%Error: Invalid option: --sim-accel\n",
                        encoding="utf-8",
                    )
                return subprocess.CompletedProcess(command, 0 if len(calls) == 1 else 1, stdout="", stderr="")

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={OPT_IN_ENV: "1", WRAPPER_ENV: wrapper.as_posix(), "PATH": bin_dir.as_posix()},
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "gpu_execution_failed")
        self.assertEqual(report["gpu_failure_blocker"], BLOCKER_REAL_VERILATOR_NOT_SIDECAR_CAPABLE)
        self.assertIn("Invalid option: --sim-accel", report["gpu_failure_diagnostic_log"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["gpu_execution_claimed"])

    def test_runner_backed_observables_only_success_has_no_reviewed_proxy_metadata_observed(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            OPT_IN_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )
        from rtlmeter_stdout_cycles_sidecar_runner_cli import (
            VSIM_SIDECAR_PROXY_ENV,
            run_rtlmeter_stdout_cycles_sidecar_runner,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            real_verilator = bin_dir / "verilator"
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)
            proxy_path = _write_executable_vsim_sidecar_proxy(root)
            base = root / "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare"
            cpu_execute = base / "cpu/Example/kind/execute-0/hello"
            gpu_execute = base / "gpu/Example/kind/execute-0/hello"
            calls = []

            def write_observables(path: Path) -> None:
                (path / "_execute").mkdir(parents=True)
                (path / "_execute/stdout.log").write_text("    0.01 | Hello World!\n", encoding="utf-8")
                (path / "_rtlmeter_cycles.txt").write_text("1000000\n", encoding="utf-8")

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                if len(calls) == 1:
                    write_observables(cpu_execute)
                    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
                observable_index = command.index("--observable-execute-dir")
                separator_index = command.index("--")
                runner_report = run_rtlmeter_stdout_cycles_sidecar_runner(
                    observable_execute_dir=command[observable_index + 1],
                    command_argv=command[separator_index:],
                    repo_root=root,
                    environ=kwargs["env"],
                    runner=lambda inner_command, **inner_kwargs: (
                        write_observables(gpu_execute)
                        or subprocess.CompletedProcess(inner_command, 0, stdout="", stderr="")
                    ),
                )
                return subprocess.CompletedProcess(command, 0, stdout=json.dumps(runner_report), stderr="")

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={
                    OPT_IN_ENV: "1",
                    WRAPPER_ENV: wrapper.as_posix(),
                    VSIM_SIDECAR_PROXY_ENV: proxy_path,
                    "PATH": bin_dir.as_posix(),
                },
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["comparison"]["status"], "passed")
        self.assertEqual(report["first_seed_handoff_evidence_status"], "compare_passed_without_handoff_authority")
        self.assertTrue(report["comparison"]["normalized_stdout_match"])
        self.assertTrue(report["comparison"]["cycle_count_match"])
        self.assertEqual(
            report["stdout_cycles_sidecar_runner"]["status"],
            "rtlmeter_stdout_cycles_sidecar_runner_observables_ready",
        )
        self.assertTrue(report["stdout_cycles_sidecar_runner"]["subprocess_invoked"])
        self.assertTrue(report["stdout_cycles_sidecar_runner"]["execution_performed"])
        self.assertTrue(report["stdout_cycles_sidecar_runner"]["observables_ready"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["cpu_as_gpu_fallback"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1][0][0], "python3")
        self.assertEqual(calls[1][0][1], "src/tools/rtlmeter_stdout_cycles_sidecar_runner.py")
        self.assertIn("third_party/rtlmeter/rtlmeter", calls[1][0])
        self.assertTrue(report["stdout_cycles_sidecar_runner"]["adapter_invoked"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["reviewed_proxy_metadata_observed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["sidecar_execute_proxy_installed_by_wrapper_branch"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["gpu_execution_claimed"])
        evidence = report["sidecar_proxy_evidence"]
        self.assertFalse(evidence["reviewed_proxy_metadata_observed"])
        self.assertEqual(evidence["rtlmeter_vsim_proxy_handoff_status"], "blocked")
        self.assertFalse(evidence["rtlmeter_vsim_proxy_handoff_reached"])
        self.assertTrue(evidence["reviewed_proxy_metadata_requires_valid_proxy_marker"])
        self.assertTrue(evidence["reviewed_proxy_metadata_requires_execute_proxy_install"])
        self.assertTrue(evidence["reviewed_proxy_metadata_requires_source_patch_marker"])
        self.assertFalse(evidence["sidecar_execute_proxy_installed_by_wrapper_branch"])
        self.assertFalse(evidence["sidecar_execute_proxy_authorized_by_wrapper_branch"])
        self.assertEqual((evidence["vsim_binary_proxy_installed_by_wrapper_branch"], evidence["vsim_main_source_patch_applied_by_wrapper_branch"], evidence["wrapper_executed_obj_dir_vsim"]), (False, False, False))
        self.assertFalse(evidence["gpu_execution_claimed"])
        self.assertEqual((evidence["runtime_execution_authority"], evidence["obj_dir_vsim_execution_observed"], evidence["vsim_runtime_execution_claimed"]), (False, False, False))
        self.assertFalse(evidence["cpu_as_gpu_fallback"])
        self.assertFalse(evidence["timing_measured"])
        self.assertFalse(evidence["speedup_claimed"])
        self.assertIn("sidecar_execute_proxy_installed_by_wrapper_branch", evidence["blocking_context"])
        execution_evidence = report["sidecar_proxy_execution_evidence"]
        self.assertEqual(execution_evidence["status"], "blocked")
        self.assertTrue(execution_evidence["observables_ready"])
        self.assertTrue(execution_evidence["runner_command_observed"])
        self.assertFalse(execution_evidence["reviewed_proxy_metadata_observed"])
        self.assertIn("sidecar_execute_proxy_installed_by_wrapper_branch", execution_evidence["blocking_context"])
        self.assertIn("RTLMETER_SIDECAR_VERILATOR_WRAPPER", calls[1][1]["env"])
        self.assertEqual(calls[1][1]["env"][VSIM_SIDECAR_PROXY_ENV], proxy_path)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_runner_backed_gpu_success_with_installed_proxy_marker_grants_authority(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            OPT_IN_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )
        from rtlmeter_sidecar_proxy_marker import write_rtlmeter_sidecar_proxy_marker
        from rtlmeter_stdout_cycles_sidecar_runner_cli import (
            VSIM_SIDECAR_PROXY_ENV,
            run_rtlmeter_stdout_cycles_sidecar_runner,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            real_verilator = bin_dir / "verilator"
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)
            proxy_path = _write_executable_vsim_sidecar_proxy(root)
            base = root / "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare"
            cpu_execute = base / "cpu/Example/kind/execute-0/hello"
            gpu_execute = base / "gpu/Example/kind/execute-0/hello"
            calls = []

            def write_observables(path: Path) -> None:
                (path / "_execute").mkdir(parents=True)
                (path / "_execute/stdout.log").write_text("    0.01 | Hello World!\n", encoding="utf-8")
                (path / "_rtlmeter_cycles.txt").write_text("1000000\n", encoding="utf-8")

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                if len(calls) == 1:
                    write_observables(cpu_execute)
                    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
                else:
                    observable_index = command.index("--observable-execute-dir")
                    separator_index = command.index("--")

                    def inner_runner(inner_command, **inner_kwargs):
                        write_observables(gpu_execute)
                        write_rtlmeter_sidecar_proxy_marker(
                            observable_execute_dir=gpu_execute.relative_to(root).as_posix(),
                            repo_root=root,
                            proxy_readiness={
                                "status": "rtlmeter_direct_sidecar_proxy_installed",
                                "proxy_installed_by_wrapper_branch": True,
                                "proxy_authorized_by_wrapper_branch": True,
                                "reviewed_proxy_metadata_observed": True,
                                "vsim_execute_proxy": {"status": "rtlmeter_vsim_execute_proxy_installed", "reviewed_proxy_metadata_observed": True},
                                "vsim_sidecar_proxy_target": {"reviewed_proxy_target": True},
                                "vsim_main_proxy_patch": {
                                    "patched_by_wrapper_branch": True,
                                    "reviewed_proxy_metadata_observed": True,
                                },
                            },
                        )
                        return subprocess.CompletedProcess(inner_command, 0, stdout="", stderr="")

                    runner_report = run_rtlmeter_stdout_cycles_sidecar_runner(
                        observable_execute_dir=command[observable_index + 1],
                        command_argv=command[separator_index:],
                        repo_root=root,
                        environ={**kwargs["env"], VSIM_SIDECAR_PROXY_ENV: proxy_path},
                        runner=inner_runner,
                    )
                    return subprocess.CompletedProcess(command, 0, stdout=json.dumps(runner_report), stderr="")

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={
                    OPT_IN_ENV: "1",
                    WRAPPER_ENV: wrapper.as_posix(),
                    VSIM_SIDECAR_PROXY_ENV: proxy_path,
                    "PATH": bin_dir.as_posix(),
                },
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["comparison"]["status"], "passed")
        self.assertEqual(report["first_seed_handoff_evidence_status"], "ready")
        self.assertTrue(report["stdout_cycles_sidecar_runner"]["execution_performed"])
        self.assertTrue(report["stdout_cycles_sidecar_runner"]["sidecar_proxy_marker_valid"])
        self.assertTrue(report["stdout_cycles_sidecar_runner"]["sidecar_execute_proxy_installed_by_wrapper_branch"])
        self.assertTrue(report["stdout_cycles_sidecar_runner"]["reviewed_proxy_metadata_requires_source_patch_marker"])
        self.assertTrue(report["stdout_cycles_sidecar_runner"]["reviewed_proxy_metadata_observed"])
        self.assertTrue(report["stdout_cycles_sidecar_runner"]["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["gpu_execution_claimed"])
        evidence = report["sidecar_proxy_evidence"]
        self.assertTrue(evidence["reviewed_proxy_metadata_observed"])
        self.assertEqual(evidence["rtlmeter_vsim_proxy_handoff_status"], "ready")
        self.assertTrue(evidence["rtlmeter_vsim_proxy_handoff_reached"])
        self.assertTrue(evidence["reviewed_proxy_metadata_requires_valid_proxy_marker"])
        self.assertTrue(evidence["reviewed_proxy_metadata_requires_execute_proxy_install"])
        self.assertTrue(evidence["reviewed_proxy_metadata_requires_source_patch_marker"])
        self.assertEqual(evidence["sidecar_proxy_marker_status"], "rtlmeter_sidecar_proxy_marker_valid")
        self.assertTrue(evidence["sidecar_proxy_marker_valid"])
        self.assertTrue(evidence["sidecar_execute_proxy_installed_by_wrapper_branch"])
        self.assertTrue(evidence["sidecar_execute_proxy_source_patch_by_wrapper_branch"])
        self.assertTrue(evidence["sidecar_execute_proxy_authorized_by_wrapper_branch"])
        self.assertEqual((evidence["vsim_binary_proxy_installed_by_wrapper_branch"], evidence["vsim_main_source_patch_applied_by_wrapper_branch"], evidence["wrapper_executed_obj_dir_vsim"]), (True, True, False))
        self.assertFalse(evidence["gpu_execution_claimed"])
        self.assertEqual((evidence["runtime_execution_authority"], evidence["obj_dir_vsim_execution_observed"], evidence["vsim_runtime_execution_claimed"]), (False, False, False))
        self.assertFalse(evidence["cpu_as_gpu_fallback"])
        self.assertFalse(evidence["timing_measured"])
        self.assertFalse(evidence["speedup_claimed"])
        self.assertEqual(evidence["blocking_context"], [])
        execution_evidence = report["sidecar_proxy_execution_evidence"]
        self.assertEqual(execution_evidence["status"], "ready")
        self.assertTrue(execution_evidence["reviewed_proxy_metadata_observed"])
        self.assertTrue(execution_evidence["rtlmeter_proxy_handoff_observed"])
        self.assertEqual(execution_evidence["blocking_context"], [])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_ready_proxy_marker_with_compare_mismatch_reports_compare_failed(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            OPT_IN_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )
        from rtlmeter_sidecar_proxy_marker import write_rtlmeter_sidecar_proxy_marker
        from rtlmeter_stdout_cycles_sidecar_runner_cli import (
            VSIM_SIDECAR_PROXY_ENV,
            run_rtlmeter_stdout_cycles_sidecar_runner,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            (bin_dir / "verilator").write_text("#!/bin/sh\n", encoding="utf-8")
            (bin_dir / "verilator").chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)
            proxy_path = _write_executable_vsim_sidecar_proxy(root)
            base = root / "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare"
            cpu_execute = base / "cpu/Example/kind/execute-0/hello"
            gpu_execute = base / "gpu/Example/kind/execute-0/hello"
            calls = []

            def write_observables(path: Path, cycles: int) -> None:
                (path / "_execute").mkdir(parents=True)
                (path / "_execute/stdout.log").write_text("    0.01 | Hello World!\n", encoding="utf-8")
                (path / "_rtlmeter_cycles.txt").write_text(f"{cycles}\n", encoding="utf-8")

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                if len(calls) == 1:
                    write_observables(cpu_execute, 1000000)
                    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
                observable_index = command.index("--observable-execute-dir")
                separator_index = command.index("--")

                def inner_runner(inner_command, **inner_kwargs):
                    write_observables(gpu_execute, 1000001)
                    write_rtlmeter_sidecar_proxy_marker(
                        observable_execute_dir=gpu_execute.relative_to(root).as_posix(),
                        repo_root=root,
                        proxy_readiness={
                            "status": "rtlmeter_direct_sidecar_proxy_installed",
                            "proxy_installed_by_wrapper_branch": True,
                            "proxy_authorized_by_wrapper_branch": True,
                            "reviewed_proxy_metadata_observed": True,
                            "vsim_execute_proxy": {"status": "rtlmeter_vsim_execute_proxy_installed", "reviewed_proxy_metadata_observed": True},
                            "vsim_sidecar_proxy_target": {"reviewed_proxy_target": True},
                            "vsim_main_proxy_patch": {
                                "patched_by_wrapper_branch": True,
                                "reviewed_proxy_metadata_observed": True,
                            },
                        },
                    )
                    return subprocess.CompletedProcess(inner_command, 0, stdout="", stderr="")

                runner_report = run_rtlmeter_stdout_cycles_sidecar_runner(
                    observable_execute_dir=command[observable_index + 1],
                    command_argv=command[separator_index:],
                    repo_root=root,
                    environ={**kwargs["env"], VSIM_SIDECAR_PROXY_ENV: proxy_path},
                    runner=inner_runner,
                )
                return subprocess.CompletedProcess(command, 0, stdout=json.dumps(runner_report), stderr="")

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={
                    OPT_IN_ENV: "1",
                    WRAPPER_ENV: wrapper.as_posix(),
                    VSIM_SIDECAR_PROXY_ENV: proxy_path,
                    "PATH": bin_dir.as_posix(),
                },
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["comparison"]["status"], "failed")
        self.assertEqual(report["first_seed_handoff_evidence_status"], "compare_failed")
        self.assertTrue(report["stdout_cycles_sidecar_runner"]["reviewed_proxy_metadata_observed"])
        self.assertEqual(report["sidecar_proxy_execution_evidence"]["status"], "ready")
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["gpu_execution_claimed"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_gpu_success_without_observables_fails_closed(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            OPT_IN_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            for path in (bin_dir / "verilator", root / "wrapper" / "verilator"):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("#!/bin/sh\n", encoding="utf-8")
                path.chmod(0o755)

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={
                    OPT_IN_ENV: "1",
                    WRAPPER_ENV: (root / "wrapper" / "verilator").as_posix(),
                    "RTLMETER_VSIM_SIDECAR_PROXY": (root / "bin" / "rtlmeter-vsim-sidecar-proxy").as_posix(),
                    "PATH": bin_dir.as_posix(),
                },
                runner=lambda command, **kwargs: subprocess.CompletedProcess(command, 0, stdout="", stderr=""),
            )

        self.assertEqual(report["status"], "gpu_observables_not_ready")
        self.assertEqual(report["first_seed_handoff_evidence_status"], "blocked_before_compare")
        self.assertEqual(report["missing_runner_report"], "rtlmeter_stdout_cycles_sidecar_runner_json_stdout")
        self.assertEqual(
            report["stdout_cycles_sidecar_runner"]["status"],
            "rtlmeter_stdout_cycles_sidecar_runner_outputs_missing",
        )
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["execution_performed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["measurement_performed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["cpu_as_gpu_fallback"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["reviewed_proxy_metadata_observed"])

    def test_gpu_runner_does_not_reuse_stale_matching_observables(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            OPT_IN_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )
        from rtlmeter_stdout_cycles_sidecar_runner_cli import run_rtlmeter_stdout_cycles_sidecar_runner

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            for path in (bin_dir / "verilator", root / "wrapper" / "verilator"):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("#!/bin/sh\n", encoding="utf-8")
                path.chmod(0o755)
            base = root / "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare"
            cpu_execute = base / "cpu/Example/kind/execute-0/hello"
            gpu_execute = base / "gpu/Example/kind/execute-0/hello"
            calls = []

            def write_observables(path: Path) -> None:
                (path / "_execute").mkdir(parents=True)
                (path / "_execute/stdout.log").write_text("    0.01 | Hello World!\n", encoding="utf-8")
                (path / "_rtlmeter_cycles.txt").write_text("1000000\n", encoding="utf-8")

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                if len(calls) == 1:
                    write_observables(cpu_execute)
                    write_observables(gpu_execute)
                    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

                observable_index = command.index("--observable-execute-dir")
                separator_index = command.index("--")
                runner_report = run_rtlmeter_stdout_cycles_sidecar_runner(
                    observable_execute_dir=command[observable_index + 1],
                    command_argv=command[separator_index:],
                    repo_root=root,
                    environ=kwargs["env"],
                    runner=lambda inner_command, **inner_kwargs: subprocess.CompletedProcess(
                        inner_command, 0, stdout="", stderr=""
                    ),
                )
                return subprocess.CompletedProcess(command, 0, stdout=json.dumps(runner_report), stderr="")

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={
                    OPT_IN_ENV: "1",
                    WRAPPER_ENV: (root / "wrapper" / "verilator").as_posix(),
                    "PATH": bin_dir.as_posix(),
                },
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "observables_missing")
        self.assertEqual(report["first_seed_handoff_evidence_status"], "blocked_before_compare")
        self.assertEqual(
            report["stdout_cycles_sidecar_runner"]["status"],
            "rtlmeter_stdout_cycles_sidecar_runner_outputs_missing",
        )
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["execution_performed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["reviewed_proxy_metadata_observed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["gpu_execution_claimed"])
        self.assertIsNone(report["comparison"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_cleans_generated_work_roots_before_fresh_run(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            OPT_IN_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            real_verilator = bin_dir / "verilator"
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)
            cpu_stale = root / "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/cpu/stale"
            gpu_stale = root / "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu/stale"
            cpu_stale.parent.mkdir(parents=True)
            gpu_stale.parent.mkdir(parents=True)
            cpu_stale.write_text("old\n", encoding="utf-8")
            gpu_stale.write_text("old\n", encoding="utf-8")

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={OPT_IN_ENV: "1", WRAPPER_ENV: wrapper.as_posix(), "PATH": bin_dir.as_posix()},
                runner=lambda command, **kwargs: subprocess.CompletedProcess(command, 1, stdout="", stderr="stop"),
            )

        self.assertEqual(report["status"], "cpu_execution_failed")
        self.assertEqual(
            set(report["cleaned_generated_work_roots"]),
            {
                "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/cpu",
                "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu",
            },
        )

    def test_compare_observables_uses_normalized_stdout_and_cycles(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import compare_rtlmeter_observables

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpu = root / "cpu"
            gpu = root / "gpu"
            for path in (cpu / "_execute", gpu / "_execute"):
                path.mkdir(parents=True)
            (cpu / "_execute" / "stdout.log").write_text("    0.01 | hello\n", encoding="utf-8")
            (gpu / "_execute" / "stdout.log").write_text("    9.99 | hello\n", encoding="utf-8")
            (cpu / "_rtlmeter_cycles.txt").write_text("12\n", encoding="utf-8")
            (gpu / "_rtlmeter_cycles.txt").write_text("12\n", encoding="utf-8")

            comparison = compare_rtlmeter_observables(cpu, gpu)

        self.assertEqual(comparison["status"], "passed")
        self.assertTrue(comparison["normalized_stdout_match"])
        self.assertTrue(comparison["cycle_count_match"])
        self.assertEqual(comparison["cpu_cycles"], 12)
        self.assertEqual(comparison["gpu_cycles"], 12)

    def test_write_report_keeps_report_generated_and_relative(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import run_rtlmeter_cpu_gpu_compare_integration

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            report = run_rtlmeter_cpu_gpu_compare_integration(
                write_report=True,
                report_path="reports/sample.json",
                repo_root=repo_root,
                environ={},
            )
            written = json.loads((repo_root / "reports/sample.json").read_text(encoding="utf-8"))

        self.assertEqual(report["report_path"], "reports/sample.json")
        self.assertEqual(written["status"], "opt_in_required")
        self.assertFalse(written["generated_report_is_source_of_truth"])
        self.assert_no_local_absolute_paths(json.dumps(written, sort_keys=True))

    def test_write_report_rejects_absolute_report_path(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import run_rtlmeter_cpu_gpu_compare_integration

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            outside = repo_root.parent / "rtlmeter-outside-report.json"
            if outside.exists():
                outside.unlink()
            report = run_rtlmeter_cpu_gpu_compare_integration(
                write_report=True,
                report_path=outside,
                repo_root=repo_root,
                environ={},
            )

        self.assertEqual(report["status"], "invalid_report_path")
        self.assertEqual(report["missing_prerequisites"], ["report_path.absolute", "report_path.outside_reports"])
        self.assertFalse(outside.exists())
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_emits_non_executing_json_by_default(self) -> None:
        result = self.run_python_tool("src/tools/rtlmeter_cpu_gpu_compare_integration.py")
        report = json.loads(result.stdout)

        self.assertEqual(report["status"], "opt_in_required")
        self.assertFalse(report["ran_commands"])
        self.assert_no_local_absolute_paths(result.stdout)
