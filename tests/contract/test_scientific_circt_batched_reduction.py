import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_batched_reduction as reduction  # noqa: E402


class ScientificCirctBatchedReductionTest(HybridCliTestCase):
    def test_shape_validation(self) -> None:
        self.assertEqual(reduction._shape("256x1"), (256, 1))
        with self.assertRaises(ValueError):
            reduction._shape("256")

    def test_materialize_and_measure_summarizes_mocked_toolchain(self) -> None:
        sample = {
            "status": "measured", "nstates": 256, "repeat": 5, "inner_repeat": 1000,
            "match": True, "cpu_ms": 1.0, "gpu_end_to_end_ms": 0.5, "gpu_kernel_ms": 0.25,
            "cpu_to_gpu_end_to_end_speedup": 2.0, "cpu_to_gpu_kernel_speedup": 4.0,
        }

        def fake_run(argv: list[str]) -> dict[str, object]:
            stdout = "TEST PASSED" if "Vsim" in argv[0] else ""
            if argv[0].endswith("batched_reduction_gpu_timing"):
                stdout = json.dumps(sample)
            return {"argv": [reduction._sanitize(arg) for arg in argv], "returncode": 0, "stdout": stdout, "stderr": ""}

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(reduction.shutil, "which", return_value="/usr/bin/tool"), \
             mock.patch.object(reduction, "_run", side_effect=fake_run):
            report = reduction.materialize_and_measure("256x1", 5, 1000, Path(temp_dir))

        self.assertEqual(report["status"], "measured")
        self.assertEqual(report["candidate"], "batched_reduction")
        self.assertEqual(report["median"]["cpu_to_gpu_end_to_end_speedup"], 2.0)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
