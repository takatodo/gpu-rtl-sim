import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "reports"
SLICE_LAUNCH_TEMPLATES = REPO_ROOT / "config" / "slice_launch_templates"
ITA_OVERLAY_SRC = REPO_ROOT / "overlays" / "ITA" / "src"
ITA_OVERLAY_TESTS = REPO_ROOT / "overlays" / "ITA" / "tests"


def report_path(filename: str) -> Path:
    return REPORTS / filename


def template_path(filename: str) -> Path:
    return SLICE_LAUNCH_TEMPLATES / filename


def ita_src_path(filename: str) -> Path:
    return ITA_OVERLAY_SRC / filename


def ita_test_path(filename: str) -> Path:
    return ITA_OVERLAY_TESTS / filename


REPEAT_MEDIAN_RESULTS_SUMMARY = report_path("results_reproduction_median_summary.json")
RESIDENT_BATCH_SWEEP_SUMMARY = report_path("resident_batch_sweep_summary.json")
RESIDENT_STATE_REUSE_SUMMARY = report_path("resident_state_reuse_experiment_summary.json")
PERSISTENT_RESIDENT_STATE_ABI_SUMMARY = report_path("persistent_resident_state_abi_probe_summary.json")
SELECTION = REPO_ROOT / "config" / "selection.json"
STATUS = REPO_ROOT / "docs" / "status.md"
ROADMAP = REPO_ROOT / "docs" / "roadmap.md"
README = REPO_ROOT / "README.md"
RESULTS = REPO_ROOT / "docs" / "results.md"
MAKEFILE = REPO_ROOT / "src" / "hybrid" / "Makefile"
NVDLA_CMAC_A2CACC_OVERLAY = (
    REPO_ROOT
    / "overlays"
    / "rtlmeter"
    / "designs"
    / "NVDLA"
    / "src"
    / "nvdla_cmac_a2cacc_gpu_cov_tb.sv"
)
NVDLA_CMAC_A2CACC_MANIFEST = (
    REPO_ROOT
    / "overlays"
    / "rtlmeter"
    / "designs"
    / "NVDLA"
    / "tests"
    / "nvdla_cmac_a2cacc_coverage_regions.json"
)
NVDLA_CMAC_A2CACC_TEMPLATE = template_path("nvdla_cmac_a2cacc.json")
NVDLA_CMAC_CORE_MAC_OVERLAY = (
    REPO_ROOT
    / "overlays"
    / "rtlmeter"
    / "designs"
    / "NVDLA"
    / "src"
    / "nvdla_cmac_core_mac_gpu_cov_tb.sv"
)
NVDLA_CMAC_CORE_MAC_MANIFEST = (
    REPO_ROOT
    / "overlays"
    / "rtlmeter"
    / "designs"
    / "NVDLA"
    / "tests"
    / "nvdla_cmac_core_mac_coverage_regions.json"
)
NVDLA_CMAC_CORE_MAC_TEMPLATE = template_path("nvdla_cmac_core_mac.json")
LARGE_KV_OVERLAY = ita_src_path("pulp_paged_kv_cache_large_gpu_cov_tb.sv")
LARGE_KV_MANIFEST = ita_test_path("pulp_paged_kv_cache_large_coverage_regions.json")
LARGE_KV_TEMPLATE = template_path("pulp_paged_kv_cache_large.json")
LARGE_KV_SUMMARY = report_path("pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json")
FULL_ITA_TC_SRAM_OVERLAY = ita_src_path("pulp_ita_tc_sram_sim.sv")
FULL_ITA_MHA_OVERLAY = ita_src_path("pulp_ita_mha_gpu_cov_tb.sv")
FULL_ITA_MHA_MANIFEST = ita_test_path("pulp_ita_mha_coverage_regions.json")
FULL_ITA_MHA_TEMPLATE = template_path("pulp_ita_mha.json")
FULL_ITA_MHA_SUMMARY = report_path("pulp_ita_mha_first_hybrid_benchmark_summary.json")
FULL_ITA_MHA_COMPARE = report_path("pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json")
FULL_ITA_MHA_COMPARE_32X1 = report_path("pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json")
FULL_ITA_MHA_COMPARE_1X32 = report_path("pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json")
FULL_ITA_MHA_SCALEUP_GATE = REPO_ROOT / "config" / "scaling_gates" / "full_mha_scaleup_64x1_1x64_gate.json"
FULL_ITA_MHA_SCALEUP_SUMMARY = report_path("pulp_ita_mha_64x1_1x64_scaling_summary.json")
FULL_ITA_MHA_COMPARE_64X1 = report_path("pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json")
FULL_ITA_MHA_COMPARE_1X64 = report_path("pulp_ita_mha_cpu_vs_hybrid_1x64_coverage_output_compare.json")
PULP_ITA_DOTP_OVERLAY = ita_src_path("pulp_ita_dotp_gpu_cov_tb.sv")
PULP_ITA_DOTP_MANIFEST = ita_test_path("pulp_ita_dotp_coverage_regions.json")
PULP_ITA_DOTP_TEMPLATE = template_path("pulp_ita_dotp.json")
PULP_ITA_CLUSTER_CLOCK_GATING_SHIM = ita_src_path("pulp_ita_cluster_clock_gating_sim.sv")
PULP_ITA_SOFTMAX_TOP_OVERLAY = ita_src_path("pulp_ita_softmax_top_gpu_cov_tb.sv")
PULP_ITA_SOFTMAX_TOP_MANIFEST = ita_test_path("pulp_ita_softmax_top_coverage_regions.json")
PULP_ITA_SOFTMAX_TOP_TEMPLATE = template_path("pulp_ita_softmax_top.json")
FULL_ITA_MHA_PREFILL_DECODE_GATE = REPO_ROOT / "config" / "scaling_gates" / "prefill_decode_split_mha_benchmark_gate.json"
FULL_ITA_MHA_PREFILL_DECODE_SUMMARY = report_path("pulp_ita_mha_prefill_decode_split_summary.json")
FULL_ITA_MHA_RESIDENT_DECODE_GATE = REPO_ROOT / "config" / "scaling_gates" / "resident_decode_optimization_probe_gate.json"
FULL_ITA_MHA_RESIDENT_DECODE_SUMMARY = report_path("pulp_ita_mha_resident_decode_1x64_summary.json")
FULL_ITA_MHA_RESIDENT_BATCH_GATE = REPO_ROOT / "config" / "scaling_gates" / "resident_decode_batch_parallel_probe_gate.json"
FULL_ITA_MHA_RESIDENT_BATCH_SUMMARY = report_path("pulp_ita_mha_resident_decode_batch_parallel_summary.json")
PAGED_ATTENTION_OVERLAY = ita_src_path("pulp_paged_attention_kv_score_gpu_cov_tb.sv")
PAGED_ATTENTION_MANIFEST = ita_test_path("pulp_paged_attention_kv_score_coverage_regions.json")
PAGED_ATTENTION_TEMPLATE = template_path("pulp_paged_attention_kv_score.json")
PAGED_ATTENTION_SUMMARY = report_path("pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json")
PAGED_ATTENTION_COMPARE_1X1 = report_path("pulp_paged_attention_kv_score_cpu_vs_hybrid_1x1_coverage_output_compare.json")
PAGED_ATTENTION_COMPARE_64X1 = report_path("pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json")
PAGED_ATTENTION_COMPARE_1X64 = report_path("pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json")
HYBRID_BENCHMARK_WRAPPER_SUMMARIES = [
    report_path("hybrid_benchmark_pulp_ita_mha_template_1x1.json"),
    report_path("hybrid_benchmark_paged_attention_kv_score_template_1x1.json"),
    report_path("hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json"),
    report_path("hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json"),
    report_path("hybrid_benchmark_mobile_vit_template_limit128.json"),
]
HYBRID_BENCHMARK_REQUIRED_SCHEMA_FIELDS = {
    "schema_version",
    "tool",
    "target",
    "shape",
    "limit",
    "mode",
    "phases",
    "execution_mode",
    "command_count",
    "commands",
    "expected_reports",
    "evidence",
    "non_claims",
}
LOCAL_ABSOLUTE_PATH_MARKERS = (
    "/home/",
    "/tmp/",
    "/Users/",
    "/var/",
    "/mnt/",
    "/workspace/",
    "/root/",
)


def git_ls_files(path: Path) -> str:
    return subprocess.check_output(
        ["git", "ls-files", "--", str(path.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        text=True,
    ).strip()


__all__ = [
    name
    for name in globals()
    if not name.startswith("_")
]
