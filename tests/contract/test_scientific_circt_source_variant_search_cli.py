import json
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase, REPO_ROOT


GOLDEN_CU = REPO_ROOT / "artifacts/scientific_circt/hls_attention_head4/attention_head4_hls_friendly_gpu.cu"


class ScientificCirctSourceVariantSearchCliTest(HybridCliTestCase):
    def test_help_is_clean(self) -> None:
        result = self.run_python_tool("src/tools/scientific_circt_source_variant_search_cli.py", "--help")
        self.assertIn("--candidate", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_emit_only_writes_attention_replicate4_sources_equal_to_golden(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_python_tool(
                "src/tools/scientific_circt_source_variant_search_cli.py",
                "--emit-only",
                "--candidate",
                "microgpt_attention_head",
                "--plan",
                "replicate=4",
                "--out-dir",
                temp_dir,
            )
            report = json.loads(result.stdout)
            emitted_cu = Path(report["emitted"][0]["cuda"])
            self.assertEqual(emitted_cu.read_text(encoding="utf-8"), GOLDEN_CU.read_text(encoding="utf-8"))

    def test_repeat_zero_fails_closed_with_structured_error(self) -> None:
        result = self.run_python_tool(
            "src/tools/scientific_circt_source_variant_search_cli.py",
            "--candidate",
            "microgpt_attention_head",
            "--repeat",
            "0",
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "failed_invalid_args")


if __name__ == "__main__":
    unittest.main()
