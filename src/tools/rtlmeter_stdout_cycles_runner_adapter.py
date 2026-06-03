"""Metadata-only entrypoint declaration for a future RTLMeter stdout/cycles adapter."""

from __future__ import annotations

from collections.abc import Mapping

try:
    from .rtlmeter_stdout_cycles_plan import EXPECTED_OBSERVABLES
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from rtlmeter_stdout_cycles_plan import EXPECTED_OBSERVABLES


SURFACE = "rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata"
STATUS_READY = "rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata_ready"
DEFAULT_RUNNER_ADAPTER_ENTRYPOINT = "rtlmeter_stdout_cycles_sidecar_runner_entrypoint"


def build_rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata(
    *,
    entrypoint: str = DEFAULT_RUNNER_ADAPTER_ENTRYPOINT,
    acceptance_policy: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return non-executing metadata for the future adapter entrypoint."""

    policy = {
        "normalized_stdout_match": True,
        "cycle_count_match": True,
        "raw_state_equality_required": False,
    }
    if acceptance_policy is not None:
        policy.update({str(key): value for key, value in acceptance_policy.items()})
    policy.update(
        {
            "normalized_stdout_match": True,
            "cycle_count_match": True,
            "raw_state_equality_required": False,
        }
    )

    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": STATUS_READY,
        "runner_adapter_entrypoint": entrypoint,
        "runner_adapter_entrypoint_role": "declared_future_entrypoint_not_materialized",
        "adapter_kind": "rtlmeter_stdout_cycles_direct_wrapper",
        "source_contract_surface": "rtlmeter_stdout_cycles_runner_contract",
        "source_contract_required_missing_runner_context": ["rtlmeter_stdout_cycles_runner_implementation"],
        "required_command_source": "gpu_candidate.command",
        "required_wrapper_env": "RTLMETER_SIDECAR_VERILATOR_WRAPPER",
        "outputs": {
            "observable_execute_dir": "gpu_candidate.observable_execute_dir",
            "stdout_log": "_execute/stdout.log",
            "cycle_count_file": "_rtlmeter_cycles.txt",
            "observables": list(EXPECTED_OBSERVABLES),
        },
        "acceptance_policy": policy,
        "uses_run_hybrid_template": False,
        "requires_runtime_launch_template": False,
        "run_hybrid_template_compatible": False,
        "launcher_command_argv": None,
        "runner_command_argv": None,
        "runner_command_role": "not_materialized",
        "execution_authority": False,
        "runtime_abi": False,
        "adapter_invoked": False,
        "sidecar_runner_invoked": False,
        "sidecar_execution_invoked": False,
        "coverage_output_compare_reached": False,
        "execution_performed": False,
        "measurement_performed": False,
        "cpu_as_gpu_fallback": False,
        "non_claims": [
            "adapter metadata does not execute RTLMeter",
            "adapter metadata does not materialize a runner command",
            "adapter metadata does not name a tracked sidecar runner source file",
            "adapter metadata does not invoke run_hybrid_template.py",
            "adapter metadata does not prove GPU correctness, timing, or speedup",
        ],
    }
