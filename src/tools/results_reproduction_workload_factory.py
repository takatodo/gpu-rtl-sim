"""Shared workload factory for results reproduction."""

from __future__ import annotations

from pathlib import Path

from results_reproduction_types import MedianWorkload


REPO_ROOT = Path(__file__).resolve().parents[2]

PULP_ITA_MHA_GATE = "config/scaling_gates/neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json"
PAGED_KV_CACHE_GATE = "config/scaling_gates/neural_network_rtl_paged_kv_cache_large_scaleup_gate.json"
PAGED_ATTENTION_GATE = "config/scaling_gates/neural_network_rtl_paged_attention_kv_score_harness_gate.json"

TARGET_OBJ_DIRS = {
    "pulp_ita_mha": REPO_ROOT / "artifacts" / "pulp_ita_mha_obj_dir",
    "pulp_paged_kv_cache_large": REPO_ROOT / "artifacts" / "pulp_paged_kv_cache_large_obj_dir",
    "pulp_paged_attention_kv_score": REPO_ROOT / "artifacts" / "pulp_paged_attention_kv_score_obj_dir",
}
TARGET_GATES = {
    "pulp_ita_mha": PULP_ITA_MHA_GATE,
    "pulp_paged_kv_cache_large": PAGED_KV_CACHE_GATE,
    "pulp_paged_attention_kv_score": PAGED_ATTENTION_GATE,
}


def median_workload(
    *,
    name: str,
    target_name: str,
    nstates: int,
    steps: int,
    resident: bool = False,
    report_tag: str | None = None,
) -> MedianWorkload:
    return MedianWorkload(
        name=name,
        target_name=target_name,
        obj_dir=TARGET_OBJ_DIRS[target_name],
        nstates=nstates,
        steps=steps,
        source_gate=TARGET_GATES[target_name],
        coverage_target=target_name,
        resident=resident,
        report_tag=report_tag,
    )
