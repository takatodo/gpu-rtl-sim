import json
import shlex
import sys

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class HybridBenchmarkDiscoveryExamplesCliTest(HybridCliTestCase):
    def test_run_hybrid_benchmark_help_examples_execute(self) -> None:
        result = self.run_python_tool("src/tools/run_hybrid_benchmark.py", "--help")

        example_commands = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip().startswith("python3 src/tools/run_hybrid_benchmark.py ")
        ]
        self.assertEqual(
            example_commands,
            [
                "python3 src/tools/run_hybrid_benchmark.py --list-targets",
                "python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu",
                "python3 src/tools/run_hybrid_benchmark.py --minimal-bench-suite",
                "python3 src/tools/run_hybrid_benchmark.py --run-minimal-bench-suite",
                "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --sidecar-gpu --dry-run",
                "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --sidecar-gpu --preflight",
                (
                    "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score "
                    "--sim-accel-shape 64x1 --sim-accel-estimate-efficiency --dry-run"
                ),
                "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-verilator-command",
                (
                    "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score "
                    "--sim-accel-shape 64x1 --print-verilator-estimate-command"
                ),
                "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-efficiency-estimate",
                "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-operator-plan",
                "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --operator-plan-json",
            ],
        )

        for command in example_commands:
            with self.subTest(command=command):
                command_result = self.run_python_tool(*command.split()[1:])
                self.assert_no_local_absolute_paths(command_result.stdout)

                if "--list-targets" in command:
                    self._assert_list_targets_example(command, command_result.stdout)
                elif "--minimal-bench-suite" in command:
                    self.assertEqual(
                        json.loads(command_result.stdout)["schema_role"],
                        "verilator_compatible_gpu_hybrid_minimal_bench_suite",
                    )
                elif "--run-minimal-bench-suite" in command:
                    self.assertEqual(
                        json.loads(command_result.stdout)["schema_role"],
                        "verilator_compatible_gpu_hybrid_minimal_bench_suite_run",
                    )
                elif "--preflight" in command:
                    self._assert_preflight_example(command_result.stdout)
                elif "--dry-run" in command:
                    self._assert_dry_run_example(command, command_result.stdout)
                elif "--operator-plan-json" in command:
                    self._assert_operator_plan_json_example(command_result.stdout)
                elif "--print-verilator-command" in command:
                    self._assert_plain_verilator_command_example(command_result.stdout)
                elif "--print-verilator-estimate-command" in command:
                    self._assert_estimate_command_example(command_result.stdout)
                elif "--print-efficiency-estimate" in command:
                    self._assert_efficiency_only_example(command_result.stdout)
                else:
                    self._assert_operator_plan_text_example(command_result.stdout)

    def test_list_targets_sidecar_gpu_json_example_executes(self) -> None:
        sidecar = self._sidecar_discovery_for("paged_attention_kv_score")
        argv = self._argv_for_command(sidecar["operator_plan_json_example_command"])

        plan = self.run_command(argv)
        report = json.loads(plan.stdout)
        self.assertEqual(report["schema_role"], "target_first_operator_plan")
        self.assertEqual(report["discovery_hint"]["source"], "src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu")
        self.assertEqual(report["discovery_hint"]["recommended_entrypoint"], sidecar["recommended_entrypoint"])
        self.assertEqual(report["discovery_hint"]["compatibility_entrypoint"], sidecar["compatibility_entrypoint"])
        self.assertEqual(
            report["discovery_hint"]["requested_compatibility_entrypoint"],
            "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1",
        )
        self.assertIn(report["discovery_hint"]["requested_compatibility_entrypoint"], report["command"])
        self.assertNotIn("--sim-accel-estimate-efficiency", report["command"])
        self.assertEqual(report["estimate_flag"], "--sim-accel-estimate-efficiency")
        self.assertEqual(report["estimate_command_argv"], [*report["command_argv"], "--sim-accel-estimate-efficiency"])
        self.assertIn(report["command"], report["estimate_command"])
        self.assertIn("--sim-accel-estimate-efficiency", report["estimate_command"])
        self.assertEqual(
            report["discovery_hint"]["verilator_estimate_command_example_command"],
            sidecar["verilator_estimate_example_command"],
        )
        self.assertEqual(
            report["discovery_hint"]["operator_plan_json_example_command"],
            sidecar["operator_plan_json_example_command"],
        )

    def test_list_targets_sidecar_gpu_estimate_example_executes(self) -> None:
        sidecar = self._sidecar_discovery_for("paged_attention_kv_score")

        estimate_command = self.run_command(self._argv_for_command(sidecar["verilator_estimate_example_command"]))
        stdout = estimate_command.stdout
        self.assertIn("verilator --cc", stdout)
        self.assertIn("--sim-accel sidecar-gpu", stdout)
        self.assertIn("--sim-accel-estimate-efficiency", stdout)
        self.assertNotIn("# efficiency_estimate", stdout)
        self.assertNotIn("schema_version", stdout)

    def _sidecar_discovery_for(self, target_name: str) -> dict:
        result = self.run_python_tool("src/tools/run_hybrid_benchmark.py", "--list-targets", "sidecar_gpu")
        payload = json.loads(result.stdout)
        return next(target["sidecar_gpu"] for target in payload["targets"] if target["name"] == target_name)

    @staticmethod
    def _argv_for_command(command: str) -> list[str]:
        argv = shlex.split(command)
        if argv[0] == "python3":
            argv[0] = sys.executable
        return argv

    def _assert_list_targets_example(self, command: str, stdout: str) -> None:
        report = json.loads(stdout)
        self.assertEqual(report["tool"], "src/tools/run_hybrid_benchmark.py")
        if command.endswith("sidecar_gpu"):
            self.assertEqual(report["view"], "sidecar_gpu")
            self.assertIn("sidecar discovery is not execution evidence", report["non_claims"])
        else:
            target_names = {target["name"] for target in report["targets"]}
            self.assertIn("paged_attention_kv_score", target_names)

    def _assert_preflight_example(self, stdout: str) -> None:
        report = json.loads(stdout)
        self.assertEqual(report["operator_entrypoint"]["surface"], "sidecar_gpu_alias")
        self.assertEqual(report["verilator_option_preview"]["status"], "planned")
        self.assertEqual(
            report["verilator_option_preview"]["requested_compatibility_entrypoint"],
            "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1",
        )

    def _assert_dry_run_example(self, command: str, stdout: str) -> None:
        self.assertIn("# verilator_option_preview", stdout)
        self.assertIn("requested_compatibility_entrypoint:", stdout)
        self.assertIn("estimate_command:", stdout)
        self.assertIn("--sim-accel-estimate-efficiency", stdout)
        self.assertIn("+ python3 src/tools/run_hybrid_template.py", stdout)
        self.assertIn("# efficiency_estimate", stdout)
        if "--sim-accel-estimate-efficiency" in command:
            self.assertIn("--shape 64x1", stdout)
            self.assertNotIn("schema_version", stdout)

    def _assert_operator_plan_json_example(self, stdout: str) -> None:
        report = json.loads(stdout)
        self.assertEqual(report["schema_role"], "target_first_operator_plan")
        self.assertEqual(report["status"], "planned")
        self.assertEqual(report["correctness_policy"], "coverage_output_equivalence")
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["operator_entrypoint"]["sim_accel_source"], "sim_accel_shape_spelling")

    def _assert_plain_verilator_command_example(self, stdout: str) -> None:
        self.assertIn("verilator --cc", stdout)
        self.assertIn("--sim-accel sidecar-gpu", stdout)
        self.assertNotIn("--sim-accel-estimate-efficiency", stdout)
        self.assertNotIn("requested_compatibility_entrypoint", stdout)
        self.assertNotIn("# efficiency_estimate", stdout)

    def _assert_estimate_command_example(self, stdout: str) -> None:
        self.assertIn("verilator --cc", stdout)
        self.assertIn("--sim-accel sidecar-gpu", stdout)
        self.assertIn("--sim-accel-estimate-efficiency", stdout)
        self.assertNotIn("requested_compatibility_entrypoint", stdout)
        self.assertNotIn("# efficiency_estimate", stdout)

    def _assert_efficiency_only_example(self, stdout: str) -> None:
        self.assertIn("# efficiency_estimate", stdout)
        self.assertNotIn("verilator --cc", stdout)
        self.assertNotIn("requested_compatibility_entrypoint", stdout)

    def _assert_operator_plan_text_example(self, stdout: str) -> None:
        self.assertIn("# verilator_sidecar_operator_plan", stdout)
        self.assertIn(
            "requested_compatibility_entrypoint: "
            "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1",
            stdout,
        )
        self.assertIn("correctness_policy: coverage_output_equivalence", stdout)
        self.assertIn("# efficiency_estimate", stdout)
