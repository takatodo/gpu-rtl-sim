import sys
import unittest

from tests.contract.hybrid_cli_helpers import REPO_ROOT


EXPECTED_PUBLIC_PACK_RECORDS = (
    "records/scaling_gates/filelist_shape_breadth_repeat_median_workflow_gate.json",
    "records/scaling_gates/filelist_shape_breadth_repeat_median_measurement_gate.json",
    "records/scaling_gates/filelist_shape_breadth_repeat_median_review_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_repeat_median_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_repeat_median_result_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_repeat_median_review_gate.json",
    "records/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_repeat_median_gate.json",
    "records/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_repeat_median_public_pack_refresh_gate.json",
    "records/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_gate.json",
    "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_dry_run_result_gate.json",
    "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_dry_run_review_gate.json",
    "records/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_execution_gate.json",
    "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_execution_dry_run_result_gate.json",
    "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_execution_dry_run_review_gate.json",
    "records/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json",
    "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_result_gate.json",
    "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_review_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_result_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_review_gate.json",
    "records/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json",
    "records/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_public_pack_refresh_gate.json",
    "records/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_gate.json",
    "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_dry_run_result_gate.json",
    "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_dry_run_review_gate.json",
    "records/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate.json",
    "records/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_timing_gate.json",
    "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_workflow_gate.json",
    "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_measurement_gate.json",
    "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_review_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_result_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_review_gate.json",
    "records/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate.json",
    "records/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_public_pack_refresh_gate.json",
    "records/scaling_gates/define_verilator_native_option_prototype_boundary_gate.json",
    "records/scaling_gates/verilator_native_option_prototype_boundary_dry_run_result_gate.json",
    "records/scaling_gates/verilator_native_option_prototype_boundary_dry_run_review_gate.json",
    "records/scaling_gates/define_verilator_native_option_prototype_filelist_target_resolution_gate.json",
    "records/scaling_gates/verilator_native_option_prototype_filelist_registry_result_gate.json",
    "records/scaling_gates/verilator_native_option_prototype_filelist_registry_review_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_result_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_review_gate.json",
    "records/scaling_gates/public_benchmark_pack_externalization_completion_after_verilator_native_option_prototype_filelist_registry_gate.json",
    "records/scaling_gates/next_measurement_selection_after_verilator_native_option_prototype_filelist_registry_public_pack_refresh_gate.json",
    "records/scaling_gates/define_verilator_native_option_parser_boundary_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_boundary_gate.json",
    "records/scaling_gates/verilator_native_option_parser_boundary_dry_run_result_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_boundary_dry_run_gate.json",
    "records/scaling_gates/define_verilator_native_option_parser_stub_boundary_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_stub_boundary_gate.json",
    "records/scaling_gates/define_verilator_native_option_parser_stub_fixture_gate.json",
)

EXPECTED_PUBLIC_PACK_REPORTS = (
    "reports/filelist_shape_breadth_repeat_median_summary.json",
    "reports/filelist_shape_breadth_repeat_filelist_paged_attention_kv_score_32x1_median.json",
    "reports/filelist_shape_breadth_repeat_filelist_paged_attention_kv_score_1x32_median.json",
    "reports/filelist_shape_breadth_repeat_filelist_known_template_pulp_ita_mha_32x1_median.json",
    "reports/filelist_shape_breadth_repeat_filelist_known_template_pulp_ita_mha_1x32_median.json",
    "reports/filelist_broader_shape_repeat_median_summary.json",
    "reports/filelist_broader_shape_repeat_filelist_paged_attention_kv_score_64x1_median.json",
    "reports/filelist_broader_shape_repeat_filelist_paged_attention_kv_score_1x64_median.json",
    "reports/filelist_broader_shape_repeat_filelist_known_template_pulp_ita_mha_64x1_median.json",
    "reports/filelist_broader_shape_repeat_filelist_known_template_pulp_ita_mha_1x64_median.json",
    "reports/filelist_broader_policy_repeat_median_summary.json",
    "reports/filelist_broader_policy_repeat_filelist_paged_attention_kv_score_64x1_median.json",
    "reports/filelist_broader_policy_repeat_filelist_known_template_pulp_ita_mha_64x1_median.json",
)


class FilelistPublicPackManifestPathsTest(unittest.TestCase):
    def test_public_pack_manifest_includes_filelist_policy_records_and_reports(self) -> None:
        sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
        try:
            from results_reproduction_manifest import PUBLIC_PACK_ARCHIVE_PATHS
        finally:
            sys.path.pop(0)

        for path in (*EXPECTED_PUBLIC_PACK_RECORDS, *EXPECTED_PUBLIC_PACK_REPORTS):
            self.assertIn(path, PUBLIC_PACK_ARCHIVE_PATHS)


if __name__ == "__main__":
    unittest.main()
