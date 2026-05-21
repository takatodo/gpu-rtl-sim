"""Static benchmark target registry for the hybrid benchmark CLI."""

from __future__ import annotations

from dataclasses import dataclass


KIND_SLICE_TEMPLATE = "slice_template"
KIND_MOBILE_VIT_IMAGENET = "mobile_vit_imagenet"

MODE_TEMPLATE = "template"
MODE_RESIDENT_STATE_REUSE = "resident-state-reuse"
MODE_PERSISTENT_RESIDENT_STATE_ABI = "persistent-resident-state-abi"


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
