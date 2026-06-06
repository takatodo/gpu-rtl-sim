"""Prototype logic for a PATH-selected RTLMeter Verilator wrapper."""

from __future__ import annotations

import json
import shlex
import sys
from collections.abc import Sequence

try:
    from .rtlmeter_verilator_command_capture import (
        RtlmeterCommandCaptureError,
        capture_rtlmeter_verilator_command,
    )
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from rtlmeter_verilator_command_capture import (
        RtlmeterCommandCaptureError,
        capture_rtlmeter_verilator_command,
    )


SURFACE = "rtlmeter_verilator_path_wrapper"
COMPILEARGS_SURFACE = "rtlmeter_compileargs_pass_through_smoke"
JSON_FLOW_ROLE = "debug_inspection"
STATUS_DELEGATE_TO_REAL_VERILATOR = "delegate_to_real_verilator"
STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING = "ready_for_rtlmeter_sidecar_planning"
STATUS_GPU_INTENT_CAPTURED_NOT_READY = "gpu_intent_captured_not_ready"
STATUS_UNSUPPORTED_RTL_METER_SIDECAR_REQUEST = "unsupported_rtlmeter_sidecar_request"
STATUS_RTL_METER_SOURCE_UNAVAILABLE = "rtlmeter_source_unavailable"


GPU_INTENT_FLAGS = (
    "--use-gpu",
    "--sim-accel",
    "--sim-accel-states",
    "--sim-accel-steps",
    "--sim-accel-shape",
)
MINIMAL_SUPPORTED_ARGV_SURFACE = (
    "verilator",
    "--cc",
    "-f <filelist>",
    "--top-module <top>",
    "--use-gpu or --sim-accel sidecar-gpu",
)


def _option_values(argv: Sequence[str], option: str) -> list[str]:
    values: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == option and index + 1 < len(argv):
            values.append(argv[index + 1])
            index += 2
            continue
        if arg.startswith(f"{option}="):
            values.append(arg.split("=", 1)[1])
        index += 1
    return values


def _has_flag_or_value(argv: Sequence[str], option: str) -> bool:
    return option in argv or any(arg.startswith(f"{option}=") for arg in argv)


def _gpu_intent_flags(argv: Sequence[str]) -> list[str]:
    return [flag for flag in GPU_INTENT_FLAGS if _has_flag_or_value(argv, flag)]


def _has_sidecar_accel(argv: Sequence[str]) -> bool:
    return "sidecar-gpu" in _option_values(argv, "--sim-accel")


def inspect_rtlmeter_verilator_wrapper_argv(argv: Sequence[str]) -> dict[str, object]:
    """Classify a Verilator argv as a non-executing RTLMeter sidecar wrapper would."""

    args = [str(arg) for arg in argv]
    full_command = ["verilator", *args]
    gpu_flags = _gpu_intent_flags(args)
    top_modules = _option_values(args, "--top-module")
    filelists = _option_values(args, "-f")
    state_values = _option_values(args, "--sim-accel-states")
    step_values = _option_values(args, "--sim-accel-steps")

    missing: list[str] = []
    if "--cc" not in args:
        missing.append("--cc")
    if not top_modules:
        missing.append("--top-module <top>")
    if not filelists:
        missing.append("-f <filelist>")

    gpu_intent_detected = bool(gpu_flags)
    has_use_gpu = _has_flag_or_value(args, "--use-gpu")
    has_expanded_sidecar = _has_sidecar_accel(args) and bool(state_values) and bool(step_values)

    if not gpu_intent_detected:
        status = STATUS_DELEGATE_TO_REAL_VERILATOR
        diagnostic = "no GPU intent flag was found; a real PATH wrapper should delegate to Verilator"
    elif missing:
        status = STATUS_UNSUPPORTED_RTL_METER_SIDECAR_REQUEST
        diagnostic = "GPU intent was found, but required RTLMeter Verilator build inputs are missing"
    elif has_expanded_sidecar:
        status = STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING
        diagnostic = "expanded sidecar schedule and RTLMeter Verilator build inputs were captured"
    elif has_use_gpu:
        status = STATUS_GPU_INTENT_CAPTURED_NOT_READY
        diagnostic = (
            "--use-gpu reached the wrapper, but the first RTLMeter seed and sidecar schedule "
            "are not selected yet"
        )
    else:
        status = STATUS_UNSUPPORTED_RTL_METER_SIDECAR_REQUEST
        diagnostic = "GPU-related flags were found, but they do not form a supported sidecar request"

    return {
        "schema_version": 1,
        "surface": SURFACE,
        "json_flow_role": JSON_FLOW_ROLE,
        "runtime_abi": False,
        "execution_authority": False,
        "wrapper_strategy": "a future installable wrapper would be named verilator and placed before the real Verilator in PATH",
        "prototype_behavior": "inspect_only_no_delegate_or_exec",
        "real_wrapper_required_behavior": (
            "delegate no-GPU-intent argv to the real Verilator, and intercept GPU-intent argv only "
            "after sidecar schedule selection is explicit"
        ),
        "prototype_exits_without_delegation": True,
        "delegate_to_real_verilator_required": status == STATUS_DELEGATE_TO_REAL_VERILATOR,
        "requires_rtlmeter_source_patch": False,
        "command_argv": full_command,
        "gpu_intent_detected": gpu_intent_detected,
        "gpu_intent_flags": gpu_flags,
        "status": status,
        "diagnostic": diagnostic,
        "missing_required_inputs": missing,
        "top_module": top_modules[-1] if top_modules else None,
        "filelists": filelists,
        "sidecar_accel": "sidecar-gpu" if _has_sidecar_accel(args) else None,
        "sidecar_states": state_values[-1] if state_values else None,
        "sidecar_steps": step_values[-1] if step_values else None,
        "minimal_supported_argv_surface_for_first_run": list(MINIMAL_SUPPORTED_ARGV_SURFACE),
        "non_claims": [
            "PATH wrapper inspection does not compile RTLMeter or run Verilator",
            "PATH wrapper inspection is not the delegating runtime; use rtlmeter_verilator_wrapper_runtime.py or a materialized verilator wrapper for execution",
            "PATH wrapper inspection does not build GPU artifacts, run sidecar stages, compare outputs, or measure timing",
            "capturing --use-gpu pass-through does not prove RTLMeter acceleration",
            "no CPU-only fallback is reported as GPU acceleration",
        ],
    }


def inspect_rtlmeter_compileargs_pass_through(
    case: str,
    compile_args: str,
    *,
    rtlmeter_root: str | None = None,
) -> dict[str, object]:
    """Smoke-check that RTLMeter compileArgs reaches the wrapper-visible argv."""

    extra_args = shlex.split(compile_args)
    try:
        capture = capture_rtlmeter_verilator_command(
            case,
            rtlmeter_root=rtlmeter_root,
            extra_args=extra_args,
        )
    except RtlmeterCommandCaptureError as exc:
        diagnostic = str(exc)
        if "source directory is missing" not in diagnostic:
            raise
        return {
            "schema_version": 1,
            "surface": COMPILEARGS_SURFACE,
            "json_flow_role": JSON_FLOW_ROLE,
            "runtime_abi": False,
            "execution_authority": False,
            "status": STATUS_RTL_METER_SOURCE_UNAVAILABLE,
            "case": case,
            "compile_args": compile_args,
            "extra_args": extra_args,
            "gpu_intent_reaches_wrapper": False,
            "command_capture": None,
            "wrapper_inspection": None,
            "diagnostic": diagnostic,
            "non_claims": [
                "compileArgs smoke could not inspect RTLMeter because the RTLMeter source tree is unavailable",
                "compileArgs smoke does not run RTLMeter",
                "compileArgs smoke does not run Verilator",
                "compileArgs smoke proves pass-through only, not GPU execution or speedup",
            ],
        }
    command_argv = capture["verilator_command_argv"]
    assert isinstance(command_argv, list)
    wrapper = inspect_rtlmeter_verilator_wrapper_argv(command_argv[1:])
    gpu_intent_reaches_wrapper = bool(wrapper["gpu_intent_detected"])
    return {
        "schema_version": 1,
        "surface": COMPILEARGS_SURFACE,
        "json_flow_role": JSON_FLOW_ROLE,
        "runtime_abi": False,
        "execution_authority": False,
        "status": "compileargs_pass_through_inspected",
        "case": case,
        "compile_args": compile_args,
        "extra_args": extra_args,
        "gpu_intent_reaches_wrapper": gpu_intent_reaches_wrapper,
        "command_capture": capture,
        "wrapper_inspection": wrapper,
        "non_claims": [
            "compileArgs smoke does not run RTLMeter",
            "compileArgs smoke does not run Verilator",
            "compileArgs smoke proves pass-through only, not GPU execution or speedup",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    report = inspect_rtlmeter_verilator_wrapper_argv(sys.argv[1:] if argv is None else argv)
    print(json.dumps(report, indent=2))
    return 2 if report["gpu_intent_detected"] else 127


if __name__ == "__main__":
    raise SystemExit(main())
