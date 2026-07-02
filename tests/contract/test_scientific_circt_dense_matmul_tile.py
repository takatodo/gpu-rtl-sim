import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from scientific_circt_dense_matmul_tile import materialize  # noqa: E402


class ScientificCirctDenseMatmulTileTest(HybridCliTestCase):
    def test_materialize_writes_reproducible_firrtl_and_harness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "dense_matmul_tile"
            report = materialize(out_dir=out_dir)

            firrtl = out_dir / "dense_matmul_tile.fir"
            harness = out_dir / "tb_dense_matmul_tile.cpp"
            self.assertTrue(firrtl.exists())
            self.assertTrue(harness.exists())
            self.assertEqual(report["status"], "materialized_firrtl_and_harness")
            self.assertIn("FIRRTL version 4.0.0", firrtl.read_text(encoding="utf-8"))
            self.assertIn("public module DenseMatmulTile", firrtl.read_text(encoding="utf-8"))
            self.assertIn("TEST PASSED", harness.read_text(encoding="utf-8"))
            self.assertIn("no_gpu_execution", report["non_claims"])
            self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report_without_running_toolchain(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "dense_matmul_tile"
            report_out = Path(temp_dir) / "report.json"
            result = self.run_python_tool(
                "src/tools/scientific_circt_dense_matmul_tile.py",
                "--out-dir",
                out_dir.as_posix(),
                "--write-report",
                "--report-out",
                report_out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(report_out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["candidate"], "dense_matmul_tile")
        self.assertEqual(report_payload["status"], "materialized_firrtl_and_harness")
        self.assert_no_local_absolute_paths(result.stdout)

    @unittest.skipUnless(
        shutil.which("firtool") and shutil.which("verilator"),
        "firtool and verilator are required for the integration gate",
    )
    def test_optional_circt_verilator_cpu_reference_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "dense_matmul_tile"
            report = materialize(out_dir=out_dir, run_circt=True, run_verilator_cpu=True)

        self.assertEqual(report["status"], "cpu_reference_pass")
        self.assertEqual(report["commands"][-1]["stage"], "cpu_reference_run")
        self.assertIn("TEST PASSED", report["commands"][-1]["stdout"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
