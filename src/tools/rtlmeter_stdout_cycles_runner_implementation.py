"""Metadata-only boundary for the missing RTLMeter stdout/cycles runner implementation."""

from __future__ import annotations

from collections.abc import Mapping

try:
    from .rtlmeter_stdout_cycles_plan import EXPECTED_OBSERVABLES
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from rtlmeter_stdout_cycles_plan import EXPECTED_OBSERVABLES


SURFACE = "rtlmeter_stdout_cycles_runner_implementation"
STATUS_BLOCKED_CONTRACT = "rtlmeter_stdout_cycles_runner_implementation_blocked_contract"
STATUS_BLOCKED_MISSING_ADAPTER = "rtlmeter_stdout_cycles_runner_implementation_blocked_missing_adapter"
STATUS_ADAPTER_METADATA_READY = "rtlmeter_stdout_cycles_runner_implementation_adapter_entrypoint_metadata_ready"
ADAPTER_ENTRYPOINT_METADATA_SURFACE = "rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata"
ADAPTER_ENTRYPOINT_METADATA_READY = "rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata_ready"


def _copy_mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    return {str(key): item for key, item in value.items()}


def _contract_gap_is_only_missing_implementation(contract: Mapping[str, object]) -> bool:
    missing = contract.get("missing_runner_context")
    return missing == ["rtlmeter_stdout_cycles_runner_implementation"]


def build_rtlmeter_stdout_cycles_runner_implementation_boundary(
    *,
    runner_contract: Mapping[str, object] | None,
    runner_adapter_entrypoint_metadata: Mapping[str, object] | None = None,
    runner_adapter_entrypoint: str | None = None,
) -> dict[str, object]:
    """Return metadata for the still-missing RTLMeter-specific runner implementation."""

    missing: list[str] = []
    if runner_contract is None:
        missing.append("runner_contract")
    else:
        if runner_contract.get("surface") != "rtlmeter_stdout_cycles_runner_contract":
            missing.append("runner_contract.surface")
        if not _contract_gap_is_only_missing_implementation(runner_contract):
            missing.append("runner_contract_missing_context")
            contract_missing = runner_contract.get("missing_runner_context")
            if isinstance(contract_missing, list):
                missing.extend(f"runner_contract.{item}" for item in contract_missing if isinstance(item, str))

    adapter_entrypoint = runner_adapter_entrypoint
    if adapter_entrypoint is None and isinstance(runner_adapter_entrypoint_metadata, Mapping):
        entrypoint = runner_adapter_entrypoint_metadata.get("runner_adapter_entrypoint")
        if isinstance(entrypoint, str) and entrypoint:
            adapter_entrypoint = entrypoint
    if runner_adapter_entrypoint_metadata is not None:
        if not isinstance(runner_adapter_entrypoint_metadata, Mapping):
            missing.append("runner_adapter_entrypoint_metadata")
        else:
            if runner_adapter_entrypoint_metadata.get("surface") != ADAPTER_ENTRYPOINT_METADATA_SURFACE:
                missing.append("runner_adapter_entrypoint_metadata.surface")
            if runner_adapter_entrypoint_metadata.get("status") != ADAPTER_ENTRYPOINT_METADATA_READY:
                missing.append("runner_adapter_entrypoint_metadata.status")
    if adapter_entrypoint is None:
        missing.append("runner_adapter_entrypoint")

    acceptance_policy = _copy_mapping(runner_contract.get("acceptance_policy") if runner_contract else None)
    if any(item.startswith("runner_contract") for item in missing):
        status = STATUS_BLOCKED_CONTRACT
    elif missing:
        status = STATUS_BLOCKED_MISSING_ADAPTER
    else:
        status = STATUS_ADAPTER_METADATA_READY
    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": status,
        "implementation_kind": "rtlmeter_stdout_cycles_direct_wrapper",
        "runner_adapter_entrypoint": adapter_entrypoint,
        "runner_adapter_entrypoint_metadata": _copy_mapping(runner_adapter_entrypoint_metadata),
        "missing_implementation_context": missing,
        "source_contract_surface": runner_contract.get("surface") if runner_contract else None,
        "source_contract_status": runner_contract.get("status") if runner_contract else None,
        "observables": list(EXPECTED_OBSERVABLES),
        "acceptance_policy": acceptance_policy,
        "uses_run_hybrid_template": False,
        "requires_runtime_launch_template": False,
        "run_hybrid_template_compatible": False,
        "launcher_command_argv": None,
        "runner_command_argv": None,
        "runner_command_role": "not_materialized",
        "execution_authority": False,
        "runtime_abi": False,
        "sidecar_runner_invoked": False,
        "sidecar_execution_invoked": False,
        "coverage_output_compare_reached": False,
        "execution_performed": False,
        "measurement_performed": False,
        "cpu_as_gpu_fallback": False,
        "next_required_boundary": "provide a reviewed RTLMeter stdout/cycles sidecar runner adapter",
        "non_claims": [
            "implementation boundary does not execute RTLMeter",
            "implementation boundary does not materialize a runner command",
            "implementation boundary does not invoke run_hybrid_template.py",
            "implementation boundary does not prove GPU correctness, timing, or speedup",
        ],
    }
