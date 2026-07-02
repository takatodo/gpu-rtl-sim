import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from scientific_circt_hybrid_dispatch_matrix import build_matrix  # noqa: E402


class ScientificCirctHybridDispatchMatrixTest(HybridCliTestCase):
    def _protocol(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "surface": "scientific_circt_hybrid_protocol",
            "status": "protocol_ready",
            "non_claims": [
                "not_runtime_abi_authority",
                "not_a_general_rtl_speedup_claim",
                "not_rtlmeter_evidence",
                "not_full_microgpt_execution",
                "not_automatic_partitioning",
            ],
            "candidates": {
                "microgpt_inference_slice": {
                    "status": "protocol_ready",
                    "required_steps": 1,
                    "min_gpu_nstates": 256,
                    "gpu_subsystem": "microgpt_two_token_inference_arithmetic",
                    "cpu_owner": "microgpt_token_loop_sampler_and_full_kv_cache_authority",
                },
                "microgpt_mlp_slice": {
                    "status": "protocol_ready",
                    "required_steps": 1,
                    "min_gpu_nstates": 1024,
                    "gpu_subsystem": "microgpt_mlp_slice_arithmetic",
                    "cpu_owner": "microgpt_token_loop_and_residual_authority",
                },
            },
            "source_variants": {
                "attention_head4_hls_friendly": {
                    "candidate": "microgpt_attention_head",
                    "source_variant": "attention_head4_hls_friendly",
                    "shape": "1024x1",
                    "status": "source_variant_protocol_ready",
                    "recommended_action": "promote_to_hls_gpu",
                    "required_steps": 1,
                    "min_gpu_nstates": 1024,
                    "gpu_subsystem": "microgpt_attention_head_hls_friendly_arithmetic",
                    "cpu_owner": "microgpt_sequence_order_and_kv_cache_authority",
                    "baseline_speedup": 6.1,
                    "variant_speedup": 13.3,
                    "speedup_delta": 7.2,
                },
                "mlp4_hls_friendly": {
                    "candidate": "microgpt_mlp_slice",
                    "source_variant": "mlp4_hls_friendly",
                    "shape": "1024x1",
                    "status": "source_variant_protocol_ready",
                    "recommended_action": "promote_to_hls_gpu",
                    "required_steps": 1,
                    "min_gpu_nstates": 1024,
                    "gpu_subsystem": "microgpt_mlp_hls_friendly_arithmetic",
                    "cpu_owner": "microgpt_token_loop_and_residual_authority",
                    "baseline_speedup": 2.3,
                    "variant_speedup": 9.9,
                    "speedup_delta": 7.6,
                },
                "block2_hls_friendly": {
                    "candidate": "microgpt_block_slice",
                    "source_variant": "block2_hls_friendly",
                    "shape": "1024x1",
                    "status": "keep_baseline_protocol",
                    "recommended_action": "keep_baseline_gpu_or_cpu",
                    "required_steps": 1,
                    "min_gpu_nstates": 1024,
                    "gpu_subsystem": "microgpt_block_hls_friendly_arithmetic",
                    "cpu_owner": "microgpt_token_loop_and_full_kv_cache_authority",
                    "baseline_speedup": 5.8,
                    "variant_speedup": 5.6,
                    "speedup_delta": -0.2,
                },
                "inference2_hls_friendly": {
                    "candidate": "microgpt_inference_slice",
                    "source_variant": "inference2_hls_friendly",
                    "shape": "1024x1",
                    "status": "source_variant_protocol_ready",
                    "recommended_action": "promote_to_hls_gpu",
                    "required_steps": 1,
                    "min_gpu_nstates": 1024,
                    "gpu_subsystem": "microgpt_inference_hls_friendly_arithmetic",
                    "cpu_owner": "microgpt_token_loop_sampler_and_full_kv_cache_authority",
                    "baseline_speedup": 3.6,
                    "variant_speedup": 9.8,
                    "speedup_delta": 6.2,
                },
            },
        }

    def _summary(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "surface": "scientific_circt_hybrid_advantage",
            "records": [
                {
                    "candidate": "microgpt_inference_slice",
                    "shape": "64x1",
                    "status": "measured",
                    "classifications": ["cpu_end_to_end_favorable", "gpu_kernel_favorable"],
                    "cpu_ms": 1.0,
                    "gpu_end_to_end_ms": 4.0,
                    "gpu_kernel_ms": 0.4,
                    "cpu_to_gpu_end_to_end_speedup": 0.25,
                    "cpu_to_gpu_kernel_speedup": 2.5,
                    "inner_repeat": 1000,
                    "source": "reports/scientific_circt_microgpt_inference_slice_64x1.json",
                },
                {
                    "candidate": "microgpt_inference_slice",
                    "shape": "256x1",
                    "status": "measured",
                    "classifications": ["gpu_end_to_end_favorable", "gpu_kernel_favorable"],
                    "cpu_ms": 4.0,
                    "gpu_end_to_end_ms": 2.0,
                    "gpu_kernel_ms": 0.5,
                    "cpu_to_gpu_end_to_end_speedup": 2.0,
                    "cpu_to_gpu_kernel_speedup": 8.0,
                    "inner_repeat": 1000,
                    "source": "reports/scientific_circt_microgpt_inference_slice_256x1.json",
                },
                {
                    "candidate": "microgpt_mlp_slice",
                    "shape": "1024x1",
                    "status": "measured",
                    "classifications": ["gpu_end_to_end_favorable", "gpu_kernel_favorable"],
                    "cpu_ms": 8.0,
                    "gpu_end_to_end_ms": 4.0,
                    "gpu_kernel_ms": 1.0,
                    "cpu_to_gpu_end_to_end_speedup": 3.0,
                    "cpu_to_gpu_kernel_speedup": 8.0,
                    "inner_repeat": 1000,
                    "source": "reports/scientific_circt_microgpt_mlp_slice_1024x1.json",
                },
            ],
        }

    def test_build_matrix_counts_shape_dispatches(self) -> None:
        report = build_matrix(self._protocol(), [64, 256, 1024], 1, self._summary())

        self.assertEqual(report["status"], "matrix_ready")
        self.assertEqual(report["candidate_count"], 2)
        self.assertEqual(report["shape_points"], ["64x1", "256x1", "1024x1"])
        self.assertEqual(report["gpu_decision_count"], 3)
        self.assertEqual(report["cpu_decision_count"], 3)
        self.assertEqual(report["source_variant_count"], 4)
        self.assertEqual(report["source_variant_decision_count"], 12)
        self.assertEqual(report["source_variant_promote_count"], 3)
        self.assertEqual(report["source_variant_keep_baseline_count"], 3)
        self.assertEqual(report["source_variant_select_cpu_count"], 6)
        self.assertEqual(report["measured_speedup_records_attached"], 3)
        self.assertEqual(report["by_shape"]["64x1"]["select_cpu"], 2)
        self.assertEqual(report["by_shape"]["256x1"]["select_gpu_state_parallel"], 1)
        self.assertEqual(report["by_shape"]["1024x1"]["select_gpu_state_parallel"], 2)
        self.assertEqual(report["runtime_integration_queue"][0]["candidate"], "microgpt_mlp_slice")
        self.assertEqual(report["runtime_integration_queue"][0]["shape"], "1024x1")
        self.assertEqual(report["top_runtime_integration_candidate"]["cpu_to_gpu_end_to_end_speedup"], 3.0)
        self.assertEqual(
            report["top_runtime_integration_candidate"]["next_required_evidence"],
            "broader_hybrid_runtime_entrypoint_with_amortized_integration_timing",
        )
        self.assertEqual(
            report["by_candidate"]["microgpt_inference_slice"][1]["timing_evidence"][
                "cpu_to_gpu_end_to_end_speedup"
            ],
            2.0,
        )
        self.assertEqual(
            report["by_candidate"]["microgpt_mlp_slice"][1]["reason"],
            "below_min_gpu_nstates",
        )
        self.assertEqual(
            report["source_variant_runtime_integration_queue"][0]["source_variant"],
            "attention_head4_hls_friendly",
        )
        self.assertEqual(
            report["selected_next_source_variant_runtime_boundary"]["source_variant"],
            "inference2_hls_friendly",
        )
        self.assertEqual(
            report["by_source_variant"]["mlp4_hls_friendly"][2]["decision"],
            "promote_to_hls_gpu",
        )
        self.assertEqual(
            report["by_source_variant"]["block2_hls_friendly"][0]["decision"],
            "keep_baseline_gpu_or_cpu",
        )
        self.assertIn("not_runtime_abi_authority", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_step_mismatch_fails_closed_across_matrix(self) -> None:
        report = build_matrix(self._protocol(), [1024], 2)

        self.assertEqual(report["gpu_decision_count"], 0)
        self.assertEqual(report["cpu_decision_count"], 2)
        self.assertEqual(report["source_variant_promote_count"], 0)
        self.assertEqual(report["source_variant_keep_baseline_count"], 0)
        self.assertEqual(report["records"][0]["reason"], "steps_mismatch")
        self.assertEqual(report["records"][1]["reason"], "steps_mismatch")

    def test_cli_writes_matrix_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protocol = root / "protocol.json"
            summary = root / "summary.json"
            out = root / "matrix.json"
            protocol.write_text(json.dumps(self._protocol()), encoding="utf-8")
            summary.write_text(json.dumps(self._summary()), encoding="utf-8")
            result = self.run_python_tool(
                "src/tools/scientific_circt_hybrid_dispatch_matrix.py",
                "--protocol",
                protocol.as_posix(),
                "--summary",
                summary.as_posix(),
                "--nstates",
                "64",
                "--nstates",
                "256",
                "--nstates",
                "1024",
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(json.loads(result.stdout), report_payload)
        self.assertEqual(report_payload["gpu_decision_count"], 3)
        self.assertEqual(report_payload["source_variant_promote_count"], 3)
        self.assertEqual(report_payload["measured_speedup_records_attached"], 3)
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
