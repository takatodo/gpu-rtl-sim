"""Non-executing RTLMeter stdout/cycles sidecar runner plan."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

try:
    from .rtlmeter_seed_selection import SELECTED_SEED
except ImportError:  # pragma: no cover - exercised when invoked as a script.
    from rtlmeter_seed_selection import SELECTED_SEED


DEFAULT_COMPILE_ARGS = "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1"
DEFAULT_ARTIFACT_ROOT = Path("artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare")
DEFAULT_AUTHORITY_REGISTRY = "config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json"
WRAPPER_ENV = "RTLMETER_SIDECAR_VERILATOR_WRAPPER"
EXPECTED_OBSERVABLES = ["normalized_stdout", "rtlmeter_cycles"]


def split_rtlmeter_seed(seed: str) -> tuple[str, str, str]:
    parts = seed.split(":")
    if len(parts) != 3:
        raise ValueError("RTLMeter execution seed must be formatted as <design>:<config>:<test>")
    return parts[0], parts[1], parts[2]


def rtlmeter_execute_dir(work_root: Path, seed: str) -> Path:
    design, config, test = split_rtlmeter_seed(seed)
    return work_root / design / config / "execute-0" / test


def rtlmeter_compile_dir(work_root: Path, seed: str) -> Path:
    design, config, _test = split_rtlmeter_seed(seed)
    return work_root / design / config / "compile-0"


def rtlmeter_command(seed: str, work_root: Path, compile_args: str = "") -> list[str]:
    command = [
        "third_party/rtlmeter/rtlmeter",
        "run",
        "--cases",
        seed,
        "--workRoot",
        work_root.as_posix(),
    ]
    if compile_args:
        command.append(f"--compileArgs={compile_args}")
    return command


def sidecar_compile_args_from_wrapper_inspection(inspection: Mapping[str, object]) -> str:
    states = inspection.get("sidecar_states")
    steps = inspection.get("sidecar_steps")
    if inspection.get("sidecar_accel") != "sidecar-gpu" or not isinstance(states, str) or not isinstance(steps, str):
        return DEFAULT_COMPILE_ARGS
    return f"--sim-accel sidecar-gpu --sim-accel-states {states} --sim-accel-steps {steps}"


def build_rtlmeter_stdout_cycles_execution_plan(
    *,
    seed: str = SELECTED_SEED,
    compile_args: str = DEFAULT_COMPILE_ARGS,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    authority_registry: str = DEFAULT_AUTHORITY_REGISTRY,
) -> dict[str, object]:
    """Return the non-executing RTLMeter stdout/cycles runner plan."""

    cpu_work_root = artifact_root / "cpu"
    gpu_work_root = artifact_root / "gpu"
    return {
        "schema_version": 1,
        "surface": "rtlmeter_stdout_cycles_execution_plan",
        "status": "plan_only_sidecar_wrapper_not_implemented",
        "seed": seed,
        "runner_strategy": "rtlmeter_stdout_cycles_direct_wrapper",
        "uses_run_hybrid_template": False,
        "requires_runtime_launch_template": False,
        "authority_registry": authority_registry,
        "observables": list(EXPECTED_OBSERVABLES),
        "acceptance_policy": {
            "normalized_stdout_match": True,
            "cycle_count_match": True,
            "raw_state_equality_required": False,
        },
        "cpu_reference": {
            "role": "rtlmeter_cpu_reference",
            "owner": "rtlmeter",
            "execution_kind": "cpu_reference_required",
            "command": rtlmeter_command(seed, cpu_work_root),
            "work_root": cpu_work_root.as_posix(),
            "observable_execute_dir": rtlmeter_execute_dir(cpu_work_root, seed).as_posix(),
            "compile_args": "",
        },
        "gpu_candidate": {
            "role": "rtlmeter_sidecar_candidate",
            "owner": "sidecar",
            "execution_kind": "sidecar_required",
            "command": rtlmeter_command(seed, gpu_work_root, compile_args),
            "work_root": gpu_work_root.as_posix(),
            "observable_execute_dir": rtlmeter_execute_dir(gpu_work_root, seed).as_posix(),
            "compile_args": compile_args,
            "requires_path_selected_verilator_wrapper": True,
            "sidecar_wrapper_env": WRAPPER_ENV,
            "cpu_as_gpu_fallback_allowed": False,
            "fallback_policy": "forbidden",
        },
        "execution_performed": False,
        "measurement_performed": False,
        "next_required_boundary": "sidecar-capable RTLMeter Verilator wrapper for stdout/cycles evidence",
        "non_claims": [
            "plan does not execute RTLMeter",
            "plan does not invoke run_hybrid_template.py",
            "plan does not prove sidecar correctness, timing, or speedup",
            "CPU execution must not be reported as GPU execution",
        ],
    }
