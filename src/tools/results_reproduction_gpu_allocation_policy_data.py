"""Static evidence values for filelist GPU allocation policy dry-runs."""

from __future__ import annotations


SOURCE_MEASUREMENT_GATE = "config/scaling_gates/filelist_shape_breadth_repeat_median_measurement_gate.json"
SOURCE_REVIEW_GATE = "config/scaling_gates/filelist_shape_breadth_repeat_median_review_gate.json"
SOURCE_SUMMARY_REPORT = "reports/filelist_shape_breadth_repeat_median_summary.json"
BROADER_SOURCE_POLICY_GATE = (
    "config/scaling_gates/"
    "define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json"
)
BROADER_SOURCE_MEASUREMENT_GATE = (
    "config/scaling_gates/"
    "filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_measurement_gate.json"
)
BROADER_SOURCE_REVIEW_GATE = (
    "config/scaling_gates/"
    "filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_review_gate.json"
)
BROADER_SOURCE_SUMMARY_REPORT = "reports/filelist_broader_shape_repeat_median_summary.json"

REVIEWED_TARGETS = (
    {
        "target": "filelist_paged_attention_kv_score",
        "template": "config/slice_launch_templates/filelist_paged_attention_kv_score.json",
        "state_parallel_wall_ratio_median": 68.83243486073675,
        "state_parallel_kernel_ratio_median": 69.53061468982342,
        "single_state_repeated_wall_ratio_median": 2.67586493987049,
        "single_state_repeated_kernel_ratio_median": 2.703171725478469,
    },
    {
        "target": "filelist_known_template_pulp_ita_mha",
        "template": "config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json",
        "state_parallel_wall_ratio_median": 76.07629547960308,
        "state_parallel_kernel_ratio_median": 78.9964646834701,
        "single_state_repeated_wall_ratio_median": 6.705723524656427,
        "single_state_repeated_kernel_ratio_median": 6.995307777417962,
    },
)

BROADER_REVIEWED_TARGETS = (
    {
        "target": "filelist_paged_attention_kv_score",
        "template": "config/slice_launch_templates/filelist_paged_attention_kv_score.json",
        "state_parallel_wall_ratio_median": 129.02924528301887,
        "state_parallel_kernel_ratio_median": 130.17003802281368,
        "single_state_repeated_wall_ratio_median": 2.204404109589041,
        "single_state_repeated_kernel_ratio_median": 2.2378048780487805,
    },
    {
        "target": "filelist_known_template_pulp_ita_mha",
        "template": "config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json",
        "state_parallel_wall_ratio_median": 121.47241379310344,
        "state_parallel_kernel_ratio_median": 123.52631578947368,
        "single_state_repeated_wall_ratio_median": 1.7360211463550361,
        "single_state_repeated_kernel_ratio_median": 1.7569444444444444,
    },
)

REFUSALS_OR_LOW_CONFIDENCE = (
    (
        "target_not_in_reviewed_filelist_set",
        "refused",
        "Run a scoped shape-breadth measurement gate before applying this policy.",
        "Define and measure a scoped target/shape gate before applying this broader policy.",
    ),
    (
        "source_closure_not_complete",
        "refused",
        "Provide explicit or copied complete source closure before execution planning.",
        "Provide explicit or copied complete source closure before execution planning.",
    ),
    (
        "missing_repeat_median_timing_evidence",
        "low",
        "Run repeat-count-3 timing first; single-run timing is not enough for this policy.",
        "Run repeat-count-3 timing first; single-run timing is not enough for this policy.",
    ),
    (
        "operator_requests_single_state_repeated_step_workload",
        "low",
        "Prefer state-parallel batching or a resident/persistent-resident mitigation gate.",
        "Prefer state-parallel batching or a resident/persistent-resident mitigation gate.",
    ),
    (
        "operator_expects_native_verilator_option_or_arbitrary_rtl_support",
        "refused",
        "Use the wrapper-sidecar flow; native Verilator and arbitrary RTL support are non-claims.",
        "Use the wrapper-sidecar flow; native Verilator and arbitrary RTL support are non-claims.",
    ),
)

NON_CLAIMS = [
    "not native Verilator option support",
    "not arbitrary RTL support",
    "not arbitrary RTL dependency inference",
    "not automatic optimal GPU allocation for any design",
    "not runtime or ABI change",
    "not new measurement evidence",
    "not production LLM-serving throughput",
]
