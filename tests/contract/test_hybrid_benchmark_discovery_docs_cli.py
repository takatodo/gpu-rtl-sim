import json
import shlex
import sys

from tests.contract.hybrid_cli_helpers import HybridCliTestCase, REPO_ROOT


class HybridBenchmarkDiscoveryDocsCliTest(HybridCliTestCase):
    def test_readme_shortest_sidecar_operator_path_executes(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        commands = self._commands_after_heading(readme, "Verilator-like benchmark runner:", limit=3)
        discovery = json.loads(
            self.run_python_tool("src/tools/run_hybrid_benchmark.py", "--list-targets", "sidecar_gpu").stdout
        )

        self.assertEqual(commands, discovery["shortest_operator_path"])
        for command in commands:
            result = self.run_command(self._argv_for_command(command))
            self.assertIn("coverage_output_equivalence", result.stdout)

    def test_docs_full_references_keep_compact_terminal_preview_commands(self) -> None:
        expected_commands = [
            "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-verilator-command",
            (
                "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score "
                "--sim-accel-shape 64x1 --print-verilator-estimate-command"
            ),
            "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-efficiency-estimate",
            "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-operator-plan",
            "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --operator-plan-json",
        ]
        doc_blocks = {
            "README.md": self._commands_after_heading(
                (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
                "Full command reference:",
                limit=30,
            ),
            "docs/results.md": self._commands_after_heading(
                (REPO_ROOT / "docs/results.md").read_text(encoding="utf-8"),
                "The fuller reference remains:",
                limit=30,
            ),
        }

        for path, commands in doc_blocks.items():
            with self.subTest(path=path):
                positions = [commands.index(command) for command in expected_commands]
                self.assertEqual(positions, sorted(positions))

    def test_docs_repeat_shortest_sidecar_operator_path(self) -> None:
        command = "python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu"
        for path in (
            REPO_ROOT / "docs/results.md",
            REPO_ROOT / "docs/tool_surface.md",
            REPO_ROOT / "docs/status.md",
        ):
            self.assertIn(command, path.read_text(encoding="utf-8"))

    def test_operator_docs_distinguish_coverage_output_policy_from_raw_state_match(self) -> None:
        for path in (
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs/results.md",
            REPO_ROOT / "docs/tool_surface.md",
        ):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("coverage_output_equivalence", text)
                self.assertIn("raw", text)
                self.assertIn("match", text)
                self.assertIn("false", text)

    def test_verilator_sidecar_option_direct_preview_example_executes(self) -> None:
        option_doc = (REPO_ROOT / "docs/verilator_sidecar_option.md").read_text(encoding="utf-8")
        command = self._single_bash_command_after_heading(
            option_doc,
            "The recommended direct-option preview is",
        )

        self.assertEqual(
            command,
            (
                "python3 src/tools/verilator_sidecar_shim.py "
                "--target paged_attention_kv_score "
                "--sim-accel-shape 64x1 "
                "--emit-verilator-command"
            ),
        )
        result = self.run_command(self._argv_for_command(command))
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ready_for_verilator_option_shim")
        self.assertNotIn("--sim-accel-estimate-efficiency", payload["verilator_command"])
        self.assertIn("--sim-accel-estimate-efficiency", payload["verilator_estimate_command"])
        self.assertEqual(
            payload["operator_plan"]["requested_compatibility_entrypoint"],
            "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1",
        )
        self.assertEqual(payload["operator_plan"]["estimate_command"], payload["verilator_estimate_command"])
        self.assertEqual(payload["discovery_hint"], payload["operator_plan"]["discovery_hint"])

    @staticmethod
    def _argv_for_command(command: str) -> list[str]:
        argv = shlex.split(command)
        if argv[0] == "python3":
            argv[0] = sys.executable
        return argv

    @staticmethod
    def _commands_after_heading(text: str, heading: str, *, limit: int) -> list[str]:
        after_heading = text.split(heading, 1)[1]
        block = after_heading.split("```bash", 1)[1].split("```", 1)[0]
        return [
            line.strip()
            for line in block.splitlines()
            if line.strip().startswith("python3 ")
        ][:limit]

    @staticmethod
    def _single_bash_command_after_heading(text: str, heading: str) -> str:
        after_heading = text.split(heading, 1)[1]
        block = after_heading.split("```bash", 1)[1].split("```", 1)[0]
        parts = []
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parts.append(stripped.removesuffix("\\").strip())
        return " ".join(parts)
