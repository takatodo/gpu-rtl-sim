import json

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class HybridVerilatorSidecarShimExamplesCliTest(HybridCliTestCase):
    def test_verilator_sidecar_shim_help_examples_execute(self) -> None:
        result = self.run_python_tool("src/tools/verilator_sidecar_shim.py", "--help")

        example_commands = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip().startswith("python3 src/tools/verilator_sidecar_shim.py ")
        ]
        self.assertEqual(
            example_commands,
            [
                (
                    "python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score "
                    "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 "
                    "--print-verilator-command"
                ),
                (
                    "python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score "
                    "--sim-accel-shape 64x1 --print-verilator-estimate-command"
                ),
                (
                    "python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score "
                    "--sim-accel-shape 64x1 --emit-verilator-command"
                ),
                (
                    "python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score "
                    "--sim-accel-shape 64x1 --sim-accel-estimate-efficiency"
                ),
                (
                    "python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score "
                    "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 "
                    "--print-operator-plan"
                ),
                "python3 src/tools/verilator_sidecar_shim.py --target mobile_vit --limit 128 --stage host_preprocess --emit-command",
                (
                    "python3 src/tools/verilator_sidecar_shim.py --target pulp_ita_mha "
                    "--sim-accel-states 1 --sim-accel-steps 64 --mode resident-state-reuse "
                    "--stage resident_state_reuse_workflow --emit-command"
                ),
            ],
        )
        self.assertIn("Not-ready stage examples still emit JSON stage commands and return exit code 2", result.stdout)

        for command in example_commands:
            with self.subTest(command=command):
                command_result = self.run_python_tool(*command.split()[1:], check=False)
                self.assert_no_local_absolute_paths(command_result.stdout)
                self._assert_shim_example(command, command_result)

    def test_compact_shape_matches_expanded_compatibility_entrypoint(self) -> None:
        compact = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "paged_attention_kv_score",
            "--sim-accel-shape",
            "64x1",
            "--emit-verilator-command",
        )
        expanded = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "paged_attention_kv_score",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "--emit-verilator-command",
        )

        compact_payload = json.loads(compact.stdout)
        expanded_payload = json.loads(expanded.stdout)
        self.assertEqual(compact_payload["shape"], "64x1")
        self.assertEqual(compact_payload["verilator_command"], expanded_payload["verilator_command"])
        self.assertEqual(compact_payload["discovery_hint"], expanded_payload["discovery_hint"])
        self.assertEqual(
            compact_payload["operator_plan"]["requested_compatibility_entrypoint"],
            "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1",
        )
        self.assertEqual(
            compact_payload["operator_plan"]["discovery_hint"]["requested_compatibility_entrypoint"],
            compact_payload["operator_plan"]["requested_compatibility_entrypoint"],
        )

    def test_accepts_verilator_style_efficiency_alias(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "pulp_ita_mha",
            "--sim-accel-shape",
            "1x64",
            "--sim-accel-estimate-efficiency",
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        stdout = result.stdout
        self.assertIn("# efficiency_estimate", stdout)
        self.assertIn("target: pulp_ita_mha", stdout)
        self.assertIn("shape: 1x64", stdout)
        self.assertIn("speedup_class: low", stdout)
        self.assertIn("prefer resident execution or batch multiple states", stdout)
        self.assertNotIn("verilator --cc", stdout)
        self.assertNotIn("schema_version", stdout)

    def test_rejects_efficiency_alias_with_command_only_mode(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "pulp_ita_mha",
            "--sim-accel-shape",
            "64x1",
            "--print-verilator-command",
            "--sim-accel-estimate-efficiency",
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["status"], "error")
        self.assertIn("mutually exclusive", payload["error"])

    def test_print_estimate_command_not_ready_keeps_json_status(self) -> None:
        result = self.run_python_tool(
            "src/tools/verilator_sidecar_shim.py",
            "--target",
            "mobile_vit",
            "--limit",
            "128",
            "--print-verilator-estimate-command",
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "not_ready_for_verilator_option_shim")
        self.assertTrue(payload["verilator_command_requested"])
        self.assertFalse(payload["verilator_command_emitted"])
        self.assertNotIn("verilator_estimate_command", payload)

    def _assert_shim_example(self, command: str, command_result) -> None:
        if "--print-verilator-command" in command:
            self.assertEqual(command_result.returncode, 0)
            self.assertIn("verilator --cc", command_result.stdout)
            self.assertIn("--sim-accel sidecar-gpu", command_result.stdout)
            self.assertNotIn("--sim-accel-estimate-efficiency", command_result.stdout)
            self.assertNotIn("requested_compatibility_entrypoint", command_result.stdout)
        elif "--print-verilator-estimate-command" in command:
            self.assertEqual(command_result.returncode, 0)
            self.assertIn("verilator --cc", command_result.stdout)
            self.assertIn("--sim-accel sidecar-gpu", command_result.stdout)
            self.assertIn("--sim-accel-estimate-efficiency", command_result.stdout)
            self.assertNotIn("requested_compatibility_entrypoint", command_result.stdout)
        elif "--emit-verilator-command" in command:
            self.assertEqual(command_result.returncode, 0)
            payload = json.loads(command_result.stdout)
            self.assertEqual(payload["verilator_command_emitted"], True)
            self.assertEqual(
                payload["operator_plan"]["requested_compatibility_entrypoint"],
                "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1",
            )
            self.assertEqual(payload["discovery_hint"], payload["operator_plan"]["discovery_hint"])
        elif "--sim-accel-estimate-efficiency" in command:
            self.assertEqual(command_result.returncode, 0)
            self.assertIn("# efficiency_estimate", command_result.stdout)
            self.assertIn("target: paged_attention_kv_score", command_result.stdout)
            self.assertIn("shape: 64x1", command_result.stdout)
            self.assertIn("speedup_class: high", command_result.stdout)
        elif "--print-operator-plan" in command:
            self.assertEqual(command_result.returncode, 0)
            self.assertIn("# verilator_sidecar_operator_plan", command_result.stdout)
            self.assertIn("requested_compatibility_entrypoint:", command_result.stdout)
        else:
            self.assertEqual(command_result.returncode, 2)
            payload = json.loads(command_result.stdout)
            self.assertTrue(payload["command_emitted"])
            self.assertEqual(payload["status"], "not_ready_for_verilator_option_shim")
