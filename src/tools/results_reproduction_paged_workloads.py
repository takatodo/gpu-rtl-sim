"""Paged-attention/KV-cache workload sets for results reproduction."""

from __future__ import annotations

from results_reproduction_types import MedianWorkload
from results_reproduction_workload_factory import median_workload


def paged_attention_kv_cache_repeat_median_workloads() -> list[MedianWorkload]:
    return [
        median_workload(
            name="pulp_paged_kv_cache_large_256x1",
            target_name="pulp_paged_kv_cache_large",
            nstates=256,
            steps=1,
            report_tag="paged_kv_repeat_pulp_paged_kv_cache_large_256x1",
        ),
        median_workload(
            name="pulp_paged_kv_cache_large_1x64",
            target_name="pulp_paged_kv_cache_large",
            nstates=1,
            steps=64,
            report_tag="paged_kv_repeat_pulp_paged_kv_cache_large_1x64",
        ),
        median_workload(
            name="pulp_paged_attention_kv_score_64x1",
            target_name="pulp_paged_attention_kv_score",
            nstates=64,
            steps=1,
            report_tag="paged_kv_repeat_pulp_paged_attention_kv_score_64x1",
        ),
        median_workload(
            name="pulp_paged_attention_kv_score_1x64",
            target_name="pulp_paged_attention_kv_score",
            nstates=1,
            steps=64,
            report_tag="paged_kv_repeat_pulp_paged_attention_kv_score_1x64",
        ),
    ]


def paged_attention_kv_cache_continuation_repeat_median_workloads() -> list[MedianWorkload]:
    return [
        median_workload(
            name="pulp_paged_kv_cache_large_512x1",
            target_name="pulp_paged_kv_cache_large",
            nstates=512,
            steps=1,
            report_tag="paged_kv_continuation_repeat_pulp_paged_kv_cache_large_512x1",
        ),
        median_workload(
            name="pulp_paged_kv_cache_large_1x128",
            target_name="pulp_paged_kv_cache_large",
            nstates=1,
            steps=128,
            report_tag="paged_kv_continuation_repeat_pulp_paged_kv_cache_large_1x128",
        ),
        median_workload(
            name="pulp_paged_attention_kv_score_128x1",
            target_name="pulp_paged_attention_kv_score",
            nstates=128,
            steps=1,
            report_tag="paged_kv_continuation_repeat_pulp_paged_attention_kv_score_128x1",
        ),
        median_workload(
            name="pulp_paged_attention_kv_score_1x128",
            target_name="pulp_paged_attention_kv_score",
            nstates=1,
            steps=128,
            report_tag="paged_kv_continuation_repeat_pulp_paged_attention_kv_score_1x128",
        ),
    ]


def paged_attention_kv_cache_next_shapes_repeat_median_workloads() -> list[MedianWorkload]:
    return [
        median_workload(
            name="pulp_paged_kv_cache_large_1024x1",
            target_name="pulp_paged_kv_cache_large",
            nstates=1024,
            steps=1,
            report_tag="paged_kv_next_shapes_repeat_pulp_paged_kv_cache_large_1024x1",
        ),
        median_workload(
            name="pulp_paged_kv_cache_large_1x256",
            target_name="pulp_paged_kv_cache_large",
            nstates=1,
            steps=256,
            report_tag="paged_kv_next_shapes_repeat_pulp_paged_kv_cache_large_1x256",
        ),
        median_workload(
            name="pulp_paged_attention_kv_score_256x1",
            target_name="pulp_paged_attention_kv_score",
            nstates=256,
            steps=1,
            report_tag="paged_kv_next_shapes_repeat_pulp_paged_attention_kv_score_256x1",
        ),
        median_workload(
            name="pulp_paged_attention_kv_score_1x256",
            target_name="pulp_paged_attention_kv_score",
            nstates=1,
            steps=256,
            report_tag="paged_kv_next_shapes_repeat_pulp_paged_attention_kv_score_1x256",
        ),
    ]
