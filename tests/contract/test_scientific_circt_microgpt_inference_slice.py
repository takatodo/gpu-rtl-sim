import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_microgpt_inference_slice as inference  # noqa: E402


class ScientificCirctMicrogptInferenceSliceTest(HybridCliTestCase):
    def test_shape_validation(self) -> None:
        self.assertEqual(inference._shape("1024x1"), (1024, 1))
        with self.assertRaises(ValueError):
            inference._shape("1024")

    def test_materialize_and_measure_summarizes_mocked_toolchain(self) -> None:
        sample = {
            "status": "measured",
            "nstates": 1024,
            "repeat": 5,
            "inner_repeat": 1000,
            "match": True,
            "cpu_ms": 3.0,
            "gpu_end_to_end_ms": 1.5,
            "gpu_kernel_ms": 0.3,
            "cpu_to_gpu_end_to_end_speedup": 2.0,
            "cpu_to_gpu_kernel_speedup": 10.0,
        }

        def fake_run(argv: list[str]) -> dict[str, object]:
            stdout = "TEST PASSED" if "Vsim" in argv[0] else ""
            if argv[0].endswith("microgpt_inference_slice_gpu_timing"):
                stdout = json.dumps(sample)
            return {"argv": [inference._sanitize(arg) for arg in argv], "returncode": 0, "stdout": stdout, "stderr": ""}

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(inference.shutil, "which", return_value="/usr/bin/tool"), \
             mock.patch.object(inference, "_run", side_effect=fake_run):
            report = inference.materialize_and_measure("1024x1", 5, 1000, Path(temp_dir))

        self.assertEqual(report["status"], "measured")
        self.assertEqual(report["candidate"], "microgpt_inference_slice")
        self.assertEqual(report["median"]["cpu_to_gpu_end_to_end_speedup"], 2.0)
        self.assertIn("not_full_block_size_sequence", report["non_claims"])
        self.assertIn("not_training_or_autograd", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
