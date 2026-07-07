"""CPU/GPU compare policy metadata for the first RTLMeter seed."""

from __future__ import annotations

import re

try:
    from .rtlmeter_seed_selection import SELECTED_SEED
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from rtlmeter_seed_selection import SELECTED_SEED


SURFACE = "rtlmeter_cpu_gpu_compare_policy"


def _report_path_for_seed(seed: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "_", seed).strip("_").lower()
    return f"reports/rtlmeter_{stem}_cpu_gpu_compare.json"


def _rtlmeter_command(seed: str, compile_args: str) -> str:
    return f'./rtlmeter run --cases {seed} --compileArgs "{compile_args}"'


def rtlmeter_cpu_gpu_compare_policy(
    seed: str | None = None,
    *,
    compile_args: str = "--use-gpu",
) -> dict[str, object]:
    """Define a non-executing compare policy for one RTLMeter seed."""

    selected_seed = seed or SELECTED_SEED
    if not selected_seed.strip():
        raise ValueError("seed must be non-empty")

    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": "policy_defined_not_executed",
        "seed": selected_seed,
        "compile_args": compile_args,
        "policy_scope": "policy_only_not_execution_integration",
        "canonical_project_state_changed": False,
        "policy_is_source_of_truth": False,
        "cpu_execution_owner": "rtlmeter",
        "gpu_execution_owner": "sidecar",
        "frontend_metadata_source": "rtlmeter_sidecar_contract_mapping",
        "rtlmeter_metrics_preserved": True,
        "rtlmeter_timing_conflated_with_sidecar_timing": False,
        "generated_report_path_rule": _report_path_for_seed(selected_seed),
        "report_schema_role": "rtlmeter_cpu_gpu_compare_report",
        "report_regeneration_command": _rtlmeter_command(selected_seed, compile_args),
        "report_generation_status": "planned_not_implemented",
        "generated_report_is_source_of_truth": False,
        "observable_outputs": [
            "RTLMeter simulator stdout transcript after timestamp stripping",
            "_rtlmeter_cycles.txt cycle count",
            "RTLMeter execute metrics kept as RTLMeter-owned evidence",
        ],
        "compare_policy": {
            "name": "rtlmeter_stdout_and_cycles_equivalence",
            "cpu_reference": "RTLMeter normal execute path",
            "gpu_candidate": "RTLMeter stdout/cycles candidate launched from Verilator argv that preserves sidecar intent",
            "required_matches": [
                "normalized stdout transcript",
                "reported RTLMeter cycle count",
            ],
            "diagnostic_only": [
                "RTLMeter elapsed/user/system/memory metrics",
                "sidecar build/run timing",
                "GPU kernel timing",
            ],
        },
        "non_claims": [
            "policy definition does not run RTLMeter",
            "policy definition does not run GPU sidecar execution",
            "policy definition does not create a compare report",
            "report regeneration command is planned documentation, not an executed workflow",
            "policy definition does not claim speedup or timing",
            "policy definition does not claim GPU runtime execution",
        ],
    }
