"""Workload definitions for results reproduction workflows."""

from __future__ import annotations

from results_reproduction_paged_workloads import (
    paged_attention_kv_cache_continuation_repeat_median_workloads,
    paged_attention_kv_cache_next_shapes_repeat_median_workloads,
    paged_attention_kv_cache_repeat_median_workloads,
)
from results_reproduction_types import MedianWorkload
from results_reproduction_workload_factory import median_workload as _median_workload


def median_workloads() -> list[MedianWorkload]:
    return [
        _median_workload(
            name="pulp_ita_mha_64x1",
            target_name="pulp_ita_mha",
            nstates=64,
            steps=1,
        ),
        _median_workload(
            name="pulp_ita_mha_1x64",
            target_name="pulp_ita_mha",
            nstates=1,
            steps=64,
        ),
        _median_workload(
            name="pulp_ita_mha_1x64_resident",
            target_name="pulp_ita_mha",
            nstates=1,
            steps=64,
            resident=True,
        ),
        _median_workload(
            name="pulp_ita_mha_32x64_resident",
            target_name="pulp_ita_mha",
            nstates=32,
            steps=64,
            resident=True,
        ),
        _median_workload(
            name="pulp_paged_attention_kv_score_64x1",
            target_name="pulp_paged_attention_kv_score",
            nstates=64,
            steps=1,
        ),
    ]


def filelist_shape_breadth_repeat_median_workloads() -> list[MedianWorkload]:
    return [
        _median_workload(
            name="filelist_paged_attention_kv_score_32x1",
            target_name="filelist_paged_attention_kv_score",
            nstates=32,
            steps=1,
            report_tag="filelist_shape_breadth_repeat_filelist_paged_attention_kv_score_32x1",
        ),
        _median_workload(
            name="filelist_paged_attention_kv_score_1x32",
            target_name="filelist_paged_attention_kv_score",
            nstates=1,
            steps=32,
            report_tag="filelist_shape_breadth_repeat_filelist_paged_attention_kv_score_1x32",
        ),
        _median_workload(
            name="filelist_known_template_pulp_ita_mha_32x1",
            target_name="filelist_known_template_pulp_ita_mha",
            nstates=32,
            steps=1,
            report_tag="filelist_shape_breadth_repeat_filelist_known_template_pulp_ita_mha_32x1",
        ),
        _median_workload(
            name="filelist_known_template_pulp_ita_mha_1x32",
            target_name="filelist_known_template_pulp_ita_mha",
            nstates=1,
            steps=32,
            report_tag="filelist_shape_breadth_repeat_filelist_known_template_pulp_ita_mha_1x32",
        ),
    ]


def filelist_broader_shape_repeat_median_workloads() -> list[MedianWorkload]:
    return [
        _median_workload(
            name="filelist_paged_attention_kv_score_64x1",
            target_name="filelist_paged_attention_kv_score",
            nstates=64,
            steps=1,
            report_tag="filelist_broader_shape_repeat_filelist_paged_attention_kv_score_64x1",
        ),
        _median_workload(
            name="filelist_paged_attention_kv_score_1x64",
            target_name="filelist_paged_attention_kv_score",
            nstates=1,
            steps=64,
            report_tag="filelist_broader_shape_repeat_filelist_paged_attention_kv_score_1x64",
        ),
        _median_workload(
            name="filelist_known_template_pulp_ita_mha_64x1",
            target_name="filelist_known_template_pulp_ita_mha",
            nstates=64,
            steps=1,
            report_tag="filelist_broader_shape_repeat_filelist_known_template_pulp_ita_mha_64x1",
        ),
        _median_workload(
            name="filelist_known_template_pulp_ita_mha_1x64",
            target_name="filelist_known_template_pulp_ita_mha",
            nstates=1,
            steps=64,
            report_tag="filelist_broader_shape_repeat_filelist_known_template_pulp_ita_mha_1x64",
        ),
    ]


def filelist_broader_policy_repeat_median_workloads() -> list[MedianWorkload]:
    return [
        _median_workload(
            name="filelist_paged_attention_kv_score_policy_64x1",
            target_name="filelist_paged_attention_kv_score",
            nstates=64,
            steps=1,
            report_tag="filelist_broader_policy_repeat_filelist_paged_attention_kv_score_64x1",
        ),
        _median_workload(
            name="filelist_known_template_pulp_ita_mha_policy_64x1",
            target_name="filelist_known_template_pulp_ita_mha",
            nstates=64,
            steps=1,
            report_tag="filelist_broader_policy_repeat_filelist_known_template_pulp_ita_mha_64x1",
        ),
    ]


def resident_batch_sweep_workloads(batch_states: list[int]) -> list[MedianWorkload]:
    return [
        _median_workload(
            name=f"pulp_ita_mha_{nstates}x64_resident_batch_sweep",
            target_name="pulp_ita_mha",
            nstates=nstates,
            steps=64,
            resident=True,
        )
        for nstates in batch_states
    ]


def mha_reuse_workload(*, nstates: int, steps: int) -> MedianWorkload:
    return _median_workload(
        name=f"pulp_ita_mha_{nstates}x{steps}_resident_state_reuse",
        target_name="pulp_ita_mha",
        nstates=nstates,
        steps=steps,
        resident=True,
    )
