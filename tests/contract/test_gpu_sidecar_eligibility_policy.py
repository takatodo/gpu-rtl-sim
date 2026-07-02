import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from gpu_sidecar_eligibility_policy import eligibility_from_suitability_report  # noqa: E402
from llvm_rtl_gpu_suitability import analyze_llvm_rtl_gpu_suitability  # noqa: E402
from tests.contract.test_llvm_rtl_gpu_suitability_cli import (  # noqa: E402
    ITA_MHA_STATE_PARALLEL_IR,
    VEER_MIXED_CPU_CORE_IR,
)


class GpuSidecarEligibilityPolicyTest(HybridCliTestCase):
    def _ita_report(self, *, shape: str) -> dict[str, object]:
        return analyze_llvm_rtl_gpu_suitability(
            ITA_MHA_STATE_PARALLEL_IR,
            target="filelist_known_template_pulp_ita_mha",
            workload="pulp_ita_mha",
            shape=shape,
            entry="pulp_ita_mha_state_parallel",
        )

    def test_64x1_state_parallel_suitability_is_correctness_smoke_not_speedup_policy(self) -> None:
        policy = eligibility_from_suitability_report(
            self._ita_report(shape="64x1"),
            source_closure_status="reviewed",
            state_bytes_estimate=6144,
            output_words_estimate=64,
        )

        self.assertEqual(policy["surface"], "gpu_sidecar_eligibility_policy")
        self.assertEqual(policy["independent_state_count"], 64)
        self.assertEqual(policy["steps_per_state"], 1)
        self.assertEqual(
            policy["recommended_action"],
            "gpu_correctness_smoke_only_require_larger_batch_evidence",
        )
        self.assertIn("no_speedup_claim_for_64x1", policy["reasons"])
        self.assertIn("debug_json_not_runtime_abi", policy["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(policy, sort_keys=True))

    def test_large_state_parallel_batch_can_be_policy_favorable_with_caveats(self) -> None:
        policy = eligibility_from_suitability_report(
            self._ita_report(shape="4096x1"),
            source_closure_status="reviewed",
            measurement_region="kernel_only_policy_input",
        )

        self.assertEqual(
            policy["recommended_action"],
            "prefer_gpu_state_parallel_large_batch_with_caveats",
        )
        self.assertEqual(policy["confidence"], "medium")
        self.assertIn("kernel_only_or_region_scoped_evidence_required", policy["reasons"])
        self.assertEqual(policy["suitability"]["recommended_path"], "gpu_state_parallel")

    def test_poor_design_cpu_suitability_maps_to_cpu_or_new_mapping(self) -> None:
        report = analyze_llvm_rtl_gpu_suitability(
            VEER_MIXED_CPU_CORE_IR,
            target="VeeR-EL2",
            workload="dhry+cmark+cmark_iccm",
            shape="3x100000",
            entry="veer_mixed_step",
        )
        policy = eligibility_from_suitability_report(report, source_closure_status="reviewed")

        self.assertEqual(policy["recommended_action"], "prefer_cpu_parallel_or_new_mapping")
        self.assertIn("suitability_recommends_cpu_or_new_mapping", policy["reasons"])
        self.assertGreater(policy["suitability"]["observable_pressure"], 0.08)

    def test_unreviewed_source_closure_fails_closed_even_for_good_suitability(self) -> None:
        policy = eligibility_from_suitability_report(
            self._ita_report(shape="4096x1"),
            source_closure_status="unknown",
        )

        self.assertEqual(policy["recommended_action"], "fail_closed_define_source_closure")
        self.assertIn("source_closure_not_reviewed", policy["reasons"])

    def test_single_state_repeated_step_prefers_mitigation(self) -> None:
        report = self._ita_report(shape="1x100000")
        policy = eligibility_from_suitability_report(report, source_closure_status="reviewed")

        self.assertEqual(policy["recommended_action"], "prefer_resident_or_cpu_parallel_mitigation")
        self.assertIn("single_state_repeated_step_shape", policy["reasons"])

    def test_cli_writes_policy_report_from_suitability_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            suitability_path = temp_path / "suitability.json"
            policy_path = temp_path / "policy.json"
            suitability_path.write_text(json.dumps(self._ita_report(shape="64x1")), encoding="utf-8")
            result = self.run_python_tool(
                "src/tools/gpu_sidecar_eligibility_policy_cli.py",
                "--suitability-report",
                suitability_path.as_posix(),
                "--source-closure-status",
                "reviewed",
                "--state-bytes-estimate",
                "6144",
                "--output-words-estimate",
                "64",
                "--write-report",
                "--report-out",
                policy_path.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(policy_path.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(
            report_payload["recommended_action"],
            "gpu_correctness_smoke_only_require_larger_batch_evidence",
        )
        self.assertEqual(report_payload["state_bytes_estimate"], 6144)
        self.assertEqual(report_payload["output_words_estimate"], 64)
        self.assert_no_local_absolute_paths(result.stdout)
        self.assert_no_local_absolute_paths(json.dumps(report_payload, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
