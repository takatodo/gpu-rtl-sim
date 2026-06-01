"""Static benchmark target registry for the hybrid benchmark CLI."""

from __future__ import annotations

from dataclasses import dataclass


KIND_SLICE_TEMPLATE = "slice_template"
KIND_MOBILE_VIT_IMAGENET = "mobile_vit_imagenet"

MODE_TEMPLATE = "template"
MODE_RESIDENT_STATE_REUSE = "resident-state-reuse"
MODE_PERSISTENT_RESIDENT_STATE_ABI = "persistent-resident-state-abi"

SIDECAR_ACCEL = "sidecar-gpu"
CORRECTNESS_POLICY_COVERAGE_OUTPUT = "coverage_output_equivalence"
STATUS_READY_FOR_VERILATOR_OPTION_SHIM = "ready_for_verilator_option_shim"
STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM = "not_ready_for_verilator_option_shim"
STATUS_READY_FOR_TEMPLATE_SHAPE = "ready_for_template_shape"
STATUS_MISSING_REQUIRED_INPUTS = "missing_required_inputs"
STATUS_UNSUPPORTED_FOR_STAGE_PLAN = "unsupported_for_stage_plan"
STATUS_PLANNED_NOT_READY_FOR_VERILATOR_OPTION_SHIM = "planned_not_ready_for_verilator_option_shim"
SCHEMA_ROLE_TARGET_FIRST_OPERATOR_PLAN = "target_first_operator_plan"
JSON_FLOW_ROLE_DEBUG_INSPECTION = "debug_inspection"


@dataclass(frozen=True)
class BenchmarkSpec:
    target: str
    kind: str
    template: str | None = None
    requires: tuple[str, ...] = ()
    modes: tuple[str, ...] = (MODE_TEMPLATE,)


BENCHMARKS: dict[str, BenchmarkSpec] = {
    "pulp_ita_mha": BenchmarkSpec(
        target="pulp_ita_mha",
        kind=KIND_SLICE_TEMPLATE,
        template="config/slice_launch_templates/pulp_ita_mha.json",
        requires=("--shape",),
        modes=(MODE_TEMPLATE, MODE_RESIDENT_STATE_REUSE, MODE_PERSISTENT_RESIDENT_STATE_ABI),
    ),
    "paged_attention_kv_score": BenchmarkSpec(
        target="paged_attention_kv_score",
        kind=KIND_SLICE_TEMPLATE,
        template="config/slice_launch_templates/pulp_paged_attention_kv_score.json",
        requires=("--shape",),
    ),
    "pulp_paged_attention_kv_score": BenchmarkSpec(
        target="paged_attention_kv_score",
        kind=KIND_SLICE_TEMPLATE,
        template="config/slice_launch_templates/pulp_paged_attention_kv_score.json",
        requires=("--shape",),
    ),
    "filelist_paged_attention_kv_score": BenchmarkSpec(
        target="filelist_paged_attention_kv_score",
        kind=KIND_SLICE_TEMPLATE,
        template="config/slice_launch_templates/filelist_paged_attention_kv_score.json",
        requires=("--shape",),
    ),
    "filelist_known_template_pulp_ita_mha": BenchmarkSpec(
        target="filelist_known_template_pulp_ita_mha",
        kind=KIND_SLICE_TEMPLATE,
        template="config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json",
        requires=("--shape",),
    ),
    "pulp_paged_kv_cache_large": BenchmarkSpec(
        target="pulp_paged_kv_cache_large",
        kind=KIND_SLICE_TEMPLATE,
        template="config/slice_launch_templates/pulp_paged_kv_cache_large.json",
        requires=("--shape",),
    ),
    "paged_kv_cache_large": BenchmarkSpec(
        target="pulp_paged_kv_cache_large",
        kind=KIND_SLICE_TEMPLATE,
        template="config/slice_launch_templates/pulp_paged_kv_cache_large.json",
        requires=("--shape",),
    ),
    "mobile_vit": BenchmarkSpec(
        target="mobile_vit",
        kind=KIND_MOBILE_VIT_IMAGENET,
        requires=("--limit 128",),
    ),
}
