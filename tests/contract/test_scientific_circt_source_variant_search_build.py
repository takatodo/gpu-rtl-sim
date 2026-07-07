import json
import sys
import unittest
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import TOOLS_DIR

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_source_variant_search as search  # noqa: E402
import scientific_circt_source_variant_search_build as build  # noqa: E402


class ScientificCirctSourceVariantSearchBuildTest(unittest.TestCase):
    def test_plan_slug_covers_replicate_unroll_and_pack(self) -> None:
        plan = search.VariantPlan(
            (
                search.Replicate(4),
                search.UnrollDensity(250),
                search.PackInputs("uint32"),
            )
        )

        self.assertEqual(build.plan_slug(plan), "replicate-4-unroll-250-pack-uint32")

    def test_command_plan_uses_hls_toolchain_flags_and_generated_artifacts(self) -> None:
        paths = build.BuildPaths(
            work_dir=Path("artifacts/scientific_circt/search/microgpt_attention_head/replicate-2-unroll-1000-pack-uint8"),
            firrtl=Path("w/attention_head2_hls_friendly.fir"),
            systemverilog=Path("w/attention_head2_hls_friendly.sv"),
            probe=Path("w/tb_attention_head2_hls_friendly.cpp"),
            cuda=Path("w/attention_head2_hls_friendly_gpu.cu"),
            bridge=Path("w/attention_head2_hls_friendly_bridge.cpp"),
            obj_dir=Path("w/obj_dir"),
            gpu_library=Path("w/libattention_head2_hls_friendly_gpu.so"),
            binary=Path("w/attention_head2_hls_friendly_direct"),
        )

        with mock.patch.object(build.hls, "_tool", side_effect=lambda name: f"/tools/{name}"):
            commands = build.command_plan(
                paths,
                module_name="MicrogptAttentionHeadHls2",
                verilator_root=Path("/verilator"),
                nstates=1024,
                repeat=1,
                inner_repeat=1000,
                integration_batches=15,
            )

        by_stage = dict(commands)
        self.assertEqual(by_stage["firtool"][:3], ["/tools/firtool", "w/attention_head2_hls_friendly.fir", "-o"])
        self.assertEqual(by_stage["verilator_build"][:8], ["/tools/verilator", "--cc", "--exe", "--timing", "-Wno-fatal", "--prefix", "Vsim", "--top-module"])
        self.assertIn("MicrogptAttentionHeadHls2", by_stage["verilator_build"])
        self.assertIn("OBJCACHE=", by_stage["verilator_build"])
        self.assertEqual(by_stage["nvcc_gpu_library_build"][:6], ["/tools/nvcc", "-O3", "--std=c++17", "-shared", "-Xcompiler", "-fPIC"])
        self.assertIn("/verilator/include", by_stage["cxx_direct_callsite_build"])
        self.assertEqual(
            by_stage["direct_callsite_run"],
            [
                "w/attention_head2_hls_friendly_direct",
                "w/libattention_head2_hls_friendly_gpu.so",
                "1024",
                "1",
                "1000",
                "15",
            ],
        )

    def test_parse_bridge_stdout_accepts_direct_binary_contract(self) -> None:
        observed = {
            "status": "hls_variant_measured",
            "variant": "attention_head2_hls_friendly",
            "mismatch_count": 0,
            "cpu_vs_gpu_output_equal": True,
            "cpu_vs_gpu_control_checksum_equal": True,
            "cpu_to_bridge_hybrid_wall_speedup": 7.5,
        }

        self.assertEqual(build.parse_bridge_stdout(json.dumps(observed)), observed)
        self.assertEqual(build.parse_json_object('{"status":"failed_gpu_outputs"}'), {"status": "failed_gpu_outputs"})
        self.assertIsNone(build.parse_bridge_stdout('{"status":"failed_usage"}'))
        self.assertIsNone(build.parse_bridge_stdout("not json"))

    def tearDown(self) -> None:
        tools_dir = str(TOOLS_DIR)
        while tools_dir in sys.path:
            sys.path.remove(tools_dir)


if __name__ == "__main__":
    unittest.main()
