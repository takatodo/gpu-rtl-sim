import json

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class HybridBenchmarkDiscoveryCliTest(HybridCliTestCase):
    def test_run_hybrid_benchmark_help_shows_discovery_entrypoints(self) -> None:
        result = self.run_python_tool("src/tools/run_hybrid_benchmark.py", "--help")

        stdout = result.stdout
        self.assertIn("examples:", stdout)
        self.assertIn("python3 src/tools/run_hybrid_benchmark.py --list-targets", stdout)
        self.assertIn("python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu", stdout)
        self.assertIn("--shape 64x1 --sidecar-gpu --dry-run", stdout)
        self.assertIn("--shape 64x1 --sidecar-gpu --preflight", stdout)
        self.assertIn("--sim-accel-shape 64x1 --sim-accel-estimate-efficiency --dry-run", stdout)
        self.assertIn("--sim-accel-shape 64x1 --print-verilator-command", stdout)
        self.assertIn("--sim-accel-shape 64x1 --print-verilator-estimate-command", stdout)
        self.assertIn("--sim-accel-shape 64x1 --print-efficiency-estimate", stdout)
        self.assertIn("--sim-accel-shape 64x1 --print-operator-plan", stdout)
        self.assertIn("--sim-accel-shape 64x1 --operator-plan-json", stdout)
        self.assertIn("do not execute commands", stdout)
        self.assertIn("--sim-accel-estimate-efficiency follows the normal execution or --dry-run path", stdout)
        self.assertIn("coverage_output_equivalence remains the correctness policy", stdout)

    def test_list_targets_sidecar_gpu_view_matches_discovery_hint_source(self) -> None:
        result = self.run_python_tool("src/tools/run_hybrid_benchmark.py", "--list-targets", "sidecar_gpu")

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["tool"], "src/tools/run_hybrid_benchmark.py")
        self.assertEqual(payload["view"], "sidecar_gpu")
        self.assertEqual(
            payload["shortest_operator_path"],
            [
                "python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu",
                (
                    "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score "
                    "--sim-accel-shape 64x1 --print-operator-plan"
                ),
                (
                    "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score "
                    "--sim-accel-shape 64x1 --operator-plan-json"
                ),
            ],
        )
        self.assertIn("sidecar discovery is not execution evidence", payload["non_claims"])
        self.assertGreater(len(payload["targets"]), 0)

        ready_targets = [
            target
            for target in payload["targets"]
            if target["sidecar_gpu"]["option_shim_status"] == "ready_for_template_shape"
        ]
        ready_names = {target["name"] for target in ready_targets}
        self.assertIn("filelist_paged_attention_kv_score", ready_names)
        self.assertIn("filelist_known_template_pulp_ita_mha", ready_names)
        self.assertGreater(len(ready_targets), 0)
        for target in ready_targets:
            sidecar = target["sidecar_gpu"]
            self.assertEqual(sidecar["recommended_entrypoint"], "--sim-accel-shape <NxS>")
            self.assertEqual(
                sidecar["compatibility_entrypoint"],
                "--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>",
            )
            self.assertIn("operator_plan_example_command", sidecar)
            self.assertIn("verilator_estimate_example_command", sidecar)
            self.assertIn("operator_plan_json_example_command", sidecar)
            self.assertIn(sidecar["recommended_entrypoint"], sidecar["operator_plan_command_template"])
            self.assertIn(sidecar["recommended_entrypoint"], sidecar["verilator_estimate_command_template"])
            self.assertNotIn(sidecar["compatibility_entrypoint"], sidecar["operator_plan_command_template"])
            self.assertNotIn(sidecar["compatibility_entrypoint"], sidecar["verilator_estimate_command_template"])
            self.assertNotIn("requires", target)
            self.assertNotIn("template", target)

    def test_list_targets_rejects_unknown_view(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_hybrid_benchmark.py",
            "--list-targets",
            "unknown_view",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported --list-targets view: unknown_view", result.stderr)
