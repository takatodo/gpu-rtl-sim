import json
import sys
import unittest
from typing import Any

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_bridge_spec as bridge_spec  # noqa: E402

# Fixed constants from the pre-FC-074 hand-maintained header at
# artifacts/scientific_circt/source_variant_verilator_entrypoint/scientific_circt_source_variant_bridge_gate.h,
# used to assert render_bridge_gate_header stays byte-compatible for that prefix.
_PRE_FC_074_INFERENCE2_HEADER_PREFIX = [
    "/* Generated from source-variant metadata by scientific_circt_source_variant_runtime_handoff.py. */",
    "#pragma once",
    '#define SCI_CIRCT_BRIDGE_EXPECTED_CANDIDATE "microgpt_inference_slice"',
    '#define SCI_CIRCT_BRIDGE_EXPECTED_SOURCE_VARIANT "inference2_hls_friendly"',
    '#define SCI_CIRCT_BRIDGE_EXPECTED_SHAPE "1024x1"',
    '#define SCI_CIRCT_BRIDGE_EXPECTED_RUN_GPU_OUTPUTS "inference2_hls_friendly_run_gpu_outputs"',
    '#define SCI_CIRCT_BRIDGE_EXPECTED_RUN_HYBRID_JSON "inference2_hls_friendly_run_hybrid_json"',
    '#define SCI_CIRCT_BRIDGE_EXPECTED_INPUT_ELEMENT_TYPE "uint8_t"',
    '#define SCI_CIRCT_BRIDGE_EXPECTED_INPUT_ELEMENT_COUNT "8"',
    '#define SCI_CIRCT_BRIDGE_EXPECTED_OUTPUT_ELEMENT_TYPE "uint64_t"',
    '#define SCI_CIRCT_BRIDGE_EXPECTED_OUTPUT_ELEMENT_COUNT "6"',
]


class ScientificCirctBridgeSpecTest(HybridCliTestCase):
    def _attention_head4_row(self) -> dict[str, Any]:
        return {
            "source_variant": "attention_head4_hls_friendly",
            "candidate": "microgpt_attention_head",
            "shape": "1024x1",
            "entrypoint_kind": "direct-binary",
            "runtime_boundary_kind": "direct_callsite_hls_source_variant_boundary",
            "policy": "promote_to_hls_gpu",
            "gpu_symbols": {
                "run_gpu_outputs": "attention_head4_hls_run_gpu_outputs",
                "run_hybrid_json": "attention_head4_hls_run_hybrid_json",
            },
            "layout": {
                "input": {"element_type": "uint8_t", "element_count": 80, "bytes_per_state": 80},
                "output": {"element_type": "uint64_t", "element_count": 16, "bytes_per_state": 128},
            },
            "metadata_complete": True,
        }

    def _mlp4_row(self) -> dict[str, Any]:
        return {
            "source_variant": "mlp4_hls_friendly",
            "candidate": "microgpt_mlp_slice",
            "shape": "1024x1",
            "entrypoint_kind": "direct-binary",
            "runtime_boundary_kind": "direct_callsite_hls_source_variant_boundary",
            "policy": "promote_to_hls_gpu",
            "gpu_symbols": {
                "run_gpu_outputs": "mlp4_hls_friendly_run_gpu_outputs",
                "run_hybrid_json": "mlp4_hls_friendly_run_hybrid_json",
            },
            "layout": {
                "input": {"element_type": "uint8_t", "element_count": 16, "bytes_per_state": 16},
                "output": {"element_type": "uint64_t", "element_count": 8, "bytes_per_state": 64},
            },
            "metadata_complete": True,
        }

    def _inference2_row(self) -> dict[str, Any]:
        return {
            "source_variant": "inference2_hls_friendly",
            "candidate": "microgpt_inference_slice",
            "shape": "1024x1",
            "entrypoint_kind": "src-hybrid-verilator",
            "runtime_boundary_kind": "src_hybrid_verilator_callsite_bridge",
            "policy": "promote_to_hls_gpu",
            "gpu_symbols": {
                "run_gpu_outputs": "inference2_hls_friendly_run_gpu_outputs",
                "run_hybrid_json": "inference2_hls_friendly_run_hybrid_json",
            },
            "layout": {
                "input": {"element_type": "uint8_t", "element_count": 8, "bytes_per_state": 8},
                "output": {"element_type": "uint64_t", "element_count": 6, "bytes_per_state": 48},
            },
            "metadata_complete": True,
        }

    def _block2_row(self) -> dict[str, Any]:
        return {
            "source_variant": "block2_hls_friendly",
            "candidate": "microgpt_block_slice",
            "shape": "1024x1",
            "entrypoint_kind": "fallback-baseline",
            "runtime_boundary_kind": "cpu_or_baseline_fallback",
            "policy": "fallback_baseline_no_speedup_improvement",
            "gpu_symbols": {
                "run_gpu_outputs": "block2_hls_friendly_run_gpu_outputs",
                "run_hybrid_json": "block2_hls_friendly_run_hybrid_json",
            },
            "layout": {
                "input": {"element_type": "uint8_t", "element_count": 24, "bytes_per_state": 24},
                "output": {"element_type": "uint64_t", "element_count": 4, "bytes_per_state": 32},
            },
            "metadata_complete": True,
        }

    def test_extracts_spec_for_each_promoted_row(self) -> None:
        for row, expected_input_count, expected_output_count in (
            (self._attention_head4_row(), 80, 16),
            (self._mlp4_row(), 16, 8),
            (self._inference2_row(), 8, 6),
        ):
            spec = bridge_spec.bridge_spec_from_metadata_row(row)
            self.assertEqual(spec.source_variant, row["source_variant"])
            self.assertEqual(spec.candidate, row["candidate"])
            self.assertEqual(spec.shape, row["shape"])
            self.assertEqual(spec.input_element_count, expected_input_count)
            self.assertEqual(spec.output_element_count, expected_output_count)
            self.assertEqual(len(spec.input_ports), expected_input_count)
            self.assertEqual(len(spec.output_ports), expected_output_count)
            self.assertEqual(spec.run_gpu_outputs_symbol, row["gpu_symbols"]["run_gpu_outputs"])
            self.assertEqual(spec.run_hybrid_json_symbol, row["gpu_symbols"]["run_hybrid_json"])

    def test_inference2_port_names_match_bridge_field_order(self) -> None:
        spec = bridge_spec.bridge_spec_from_metadata_row(self._inference2_row())
        self.assertEqual(
            spec.input_ports,
            ("i0_tok0", "i0_pos0", "i0_tok1", "i0_pos1", "i1_tok0", "i1_pos0", "i1_tok1", "i1_pos1"),
        )
        self.assertEqual(spec.output_ports, ("i0_y0", "i0_y1", "i0_y2", "i1_y0", "i1_y1", "i1_y2"))

    def test_fails_closed_on_metadata_incomplete(self) -> None:
        row = self._inference2_row()
        row["metadata_complete"] = False
        with self.assertRaises(bridge_spec.BridgeSpecError):
            bridge_spec.bridge_spec_from_metadata_row(row)

    def test_fails_closed_on_unknown_source_variant(self) -> None:
        row = self._inference2_row()
        row["source_variant"] = "unknown_source_variant"
        with self.assertRaises(bridge_spec.BridgeSpecError):
            bridge_spec.bridge_spec_from_metadata_row(row)

    def test_fails_closed_on_wrong_element_count(self) -> None:
        row = self._attention_head4_row()
        row["layout"]["input"]["element_count"] = 79
        with self.assertRaises(bridge_spec.BridgeSpecError):
            bridge_spec.bridge_spec_from_metadata_row(row)

    def test_fails_closed_on_missing_symbol(self) -> None:
        row = self._mlp4_row()
        del row["gpu_symbols"]["run_gpu_outputs"]
        with self.assertRaises(bridge_spec.BridgeSpecError):
            bridge_spec.bridge_spec_from_metadata_row(row)

    def test_fails_closed_on_entrypoint_runtime_boundary_mismatch(self) -> None:
        row = self._mlp4_row()
        row["runtime_boundary_kind"] = "src_hybrid_verilator_callsite_bridge"
        with self.assertRaises(bridge_spec.BridgeSpecError):
            bridge_spec.bridge_spec_from_metadata_row(row)

    def test_fails_closed_on_unsupported_element_type(self) -> None:
        row = self._mlp4_row()
        row["layout"]["output"]["element_type"] = "float"
        with self.assertRaises(bridge_spec.BridgeSpecError):
            bridge_spec.bridge_spec_from_metadata_row(row)

    def test_selected_disagreement_raises(self) -> None:
        row = self._inference2_row()
        selected = {"candidate": "microgpt_mlp_slice", "source_variant": "inference2_hls_friendly", "shape": "1024x1"}
        with self.assertRaises(bridge_spec.BridgeSpecError):
            bridge_spec.bridge_spec_from_metadata_row(row, selected=selected)

    def test_block2_raises_and_header_is_unreachable(self) -> None:
        row = self._block2_row()
        with self.assertRaises(bridge_spec.BridgeSpecError):
            spec = bridge_spec.bridge_spec_from_metadata_row(row)
            bridge_spec.render_bridge_gate_header(spec)  # pragma: no cover - never reached

    def test_render_bridge_gate_header_inference2_byte_identical_prefix(self) -> None:
        spec = bridge_spec.bridge_spec_from_metadata_row(self._inference2_row())
        rendered = bridge_spec.render_bridge_gate_header(spec)
        rendered_lines = rendered.split("\n")
        self.assertEqual(rendered_lines[: len(_PRE_FC_074_INFERENCE2_HEADER_PREFIX)], _PRE_FC_074_INFERENCE2_HEADER_PREFIX)
        self.assertIn("SCI_CIRCT_BRIDGE_APPLY_INPUTS(top, in) top.i0_tok0 = in.x[0];", rendered)
        self.assertIn("SCI_CIRCT_BRIDGE_READ_OUTPUTS(top, base) base.y[0] = top.i0_y0;", rendered)

    def test_attention_head4_header_has_expected_assignment_and_read_counts_in_field_order(self) -> None:
        spec = bridge_spec.bridge_spec_from_metadata_row(self._attention_head4_row())
        rendered = bridge_spec.render_bridge_gate_header(spec)
        apply_line = next(line for line in rendered.splitlines() if line.startswith("#define SCI_CIRCT_BRIDGE_APPLY_INPUTS"))
        read_line = next(line for line in rendered.splitlines() if line.startswith("#define SCI_CIRCT_BRIDGE_READ_OUTPUTS"))
        self.assertEqual(apply_line.count("= in.x["), 80)
        self.assertEqual(read_line.count("= top.h"), 16)
        self.assertTrue(apply_line.endswith("top.h3_x19 = in.x[79];"))
        self.assertIn("top.h0_x0 = in.x[0];", apply_line)
        self.assertTrue(read_line.endswith("base.y[15] = top.h3_y3;"))
        self.assertIn("base.y[0] = top.h0_y0;", read_line)
        self.assert_no_local_absolute_paths(rendered)

    def test_json_roundtrip_of_extracted_dimensions(self) -> None:
        spec = bridge_spec.bridge_spec_from_metadata_row(self._mlp4_row())
        payload = json.dumps(
            {
                "source_variant": spec.source_variant,
                "input_element_count": spec.input_element_count,
                "output_element_count": spec.output_element_count,
            }
        )
        reloaded = json.loads(payload)
        self.assertEqual(reloaded["input_element_count"], 16)
        self.assertEqual(reloaded["output_element_count"], 8)


if __name__ == "__main__":
    unittest.main()
