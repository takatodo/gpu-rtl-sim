import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from scientific_circt_hybrid_protocol import build_protocol, decide  # noqa: E402


class ScientificCirctHybridProtocolTest(HybridCliTestCase):
    def _policy(self) -> dict[str, object]:
        return {
            "surface": "scientific_circt_gpu_selection_policy",
            "candidates": {
                "microgpt_inference_slice": {
                    "recommended_action": "select_gpu_state_parallel",
                    "required_steps": 1,
                    "min_gpu_nstates": 256,
                    "first_gpu_end_to_end_favorable_shape": "256x1",
                },
                "unknown_candidate": {
                    "recommended_action": "select_gpu_state_parallel",
                    "required_steps": 1,
                    "min_gpu_nstates": 256,
                    "first_gpu_end_to_end_favorable_shape": "256x1",
                },
            },
            "source_variants": [
                {
                    "candidate": "microgpt_inference_slice",
                    "source_variant": "inference2_hls_friendly",
                    "shape": "1024x1",
                    "recommended_action": "promote_to_hls_gpu",
                    "baseline_speedup": 3.5,
                    "variant_speedup": 9.8,
                    "speedup_delta": 6.3,
                    "speedup_improved": True,
                    "cpu_vs_gpu_output_equal": True,
                    "cpu_vs_gpu_control_checksum_equal": True,
                },
                {
                    "candidate": "microgpt_block_slice",
                    "source_variant": "block2_hls_friendly",
                    "shape": "1024x1",
                    "recommended_action": "keep_baseline_gpu_or_cpu",
                    "baseline_speedup": 5.8,
                    "variant_speedup": 5.6,
                    "speedup_delta": -0.2,
                    "speedup_improved": False,
                    "cpu_vs_gpu_output_equal": True,
                    "cpu_vs_gpu_control_checksum_equal": True,
                },
            ],
        }

    def _summary(self) -> dict[str, object]:
        return {
            "surface": "scientific_circt_hybrid_advantage",
            "by_candidate": {
                "microgpt_inference_slice": {
                    "best_gpu_end_to_end": {
                        "cpu_to_gpu_end_to_end_speedup": 3.5,
                    },
                },
            },
        }

    def test_build_protocol_records_cpu_gpu_boundary_and_transfer_estimate(self) -> None:
        report = build_protocol(self._policy(), self._summary())

        self.assertEqual(report["status"], "protocol_ready")
        self.assertEqual(report["ready_candidate_count"], 1)
        self.assertEqual(report["source_variant_ready_count"], 1)
        inference = report["candidates"]["microgpt_inference_slice"]
        self.assertEqual(inference["status"], "protocol_ready")
        self.assertEqual(inference["cpu_owner"], "microgpt_token_loop_sampler_and_full_kv_cache_authority")
        self.assertEqual(inference["gpu_subsystem"], "microgpt_two_token_inference_arithmetic")
        self.assertEqual(inference["transfer_estimate_at_threshold"]["logical_roundtrip_bytes"], 7168)
        self.assertIn("cpu_fallback_below_threshold", inference["protocol_invariants"])
        self.assertEqual(report["candidates"]["unknown_candidate"]["status"], "measure_or_define_protocol_before_gpu")
        source_variant = report["source_variants"]["inference2_hls_friendly"]
        self.assertEqual(source_variant["status"], "source_variant_protocol_ready")
        self.assertEqual(source_variant["transfer_estimate_at_threshold"]["logical_roundtrip_bytes"], 57344)
        self.assertEqual(report["source_variants"]["block2_hls_friendly"]["status"], "keep_baseline_protocol")
        self.assertIn("source_variant", report["handoff_protocol"]["dispatch_key"])
        self.assertIn("not_runtime_abi_authority", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_decide_fails_closed_below_threshold_or_unknown_candidate(self) -> None:
        report = build_protocol(self._policy(), self._summary())

        gpu = decide(report, "microgpt_inference_slice", 256, 1)
        self.assertEqual(gpu["decision"], "select_gpu_state_parallel")
        self.assertEqual(gpu["reason"], "measured_candidate_at_or_above_threshold")
        self.assertEqual(gpu["gpu_subsystem"], "microgpt_two_token_inference_arithmetic")
        self.assertEqual(gpu["logical_roundtrip_bytes"], 7168)

        below = decide(report, "microgpt_inference_slice", 64, 1)
        self.assertEqual(below["decision"], "select_cpu")
        self.assertEqual(below["reason"], "below_min_gpu_nstates")
        self.assertTrue(below["fallback_used"])

        unknown = decide(report, "missing", 1024, 1)
        self.assertEqual(unknown["decision"], "select_cpu")
        self.assertEqual(unknown["reason"], "candidate_not_in_protocol")

    def test_decide_source_variant_promotes_or_keeps_baseline(self) -> None:
        report = build_protocol(self._policy(), self._summary())

        promoted = decide(report, "microgpt_inference_slice", 1024, 1, "inference2_hls_friendly")
        self.assertEqual(promoted["decision"], "promote_to_hls_gpu")
        self.assertEqual(promoted["reason"], "measured_source_variant_at_or_above_threshold")
        self.assertEqual(promoted["gpu_subsystem"], "microgpt_inference_hls_friendly_arithmetic")
        self.assertEqual(promoted["logical_roundtrip_bytes"], 57344)

        below = decide(report, "microgpt_inference_slice", 256, 1, "inference2_hls_friendly")
        self.assertEqual(below["decision"], "select_cpu")
        self.assertEqual(below["reason"], "below_min_gpu_nstates")

        keep = decide(report, "microgpt_block_slice", 1024, 1, "block2_hls_friendly")
        self.assertEqual(keep["decision"], "keep_baseline_gpu_or_cpu")
        self.assertEqual(keep["reason"], "source_variant_measured_but_not_faster_than_baseline")
        self.assertTrue(keep["fallback_used"])

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy = root / "policy.json"
            summary = root / "summary.json"
            out = root / "protocol.json"
            policy.write_text(json.dumps(self._policy()), encoding="utf-8")
            summary.write_text(json.dumps(self._summary()), encoding="utf-8")
            result = self.run_python_tool(
                "src/tools/scientific_circt_hybrid_protocol.py",
                "--policy",
                policy.as_posix(),
                "--summary",
                summary.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(json.loads(result.stdout), report_payload)
        self.assert_no_local_absolute_paths(result.stdout)

    def test_cli_emits_dispatch_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy = root / "policy.json"
            summary = root / "summary.json"
            policy.write_text(json.dumps(self._policy()), encoding="utf-8")
            summary.write_text(json.dumps(self._summary()), encoding="utf-8")
            result = self.run_python_tool(
                "src/tools/scientific_circt_hybrid_protocol.py",
                "--policy",
                policy.as_posix(),
                "--summary",
                summary.as_posix(),
                "--candidate",
                "microgpt_inference_slice",
                "--source-variant",
                "inference2_hls_friendly",
                "--nstates",
                "1024",
                "--steps",
                "1",
            )
            payload = json.loads(result.stdout)

        self.assertEqual(payload["surface"], "scientific_circt_hybrid_dispatch_decision")
        self.assertEqual(payload["decision"], "promote_to_hls_gpu")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
