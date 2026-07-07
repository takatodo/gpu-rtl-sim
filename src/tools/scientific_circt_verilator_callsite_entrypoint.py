#!/usr/bin/env python3
"""Measure the adapter GPU path against a Verilator-generated CPU callsite."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from scientific_circt_hybrid_protocol import _load

REPORT = Path("reports/scientific_circt_verilator_callsite_entrypoint.json")
ADAPTER_REPORT = Path("reports/scientific_circt_runtime_handoff_adapter.json")
OUT_DIR = Path("artifacts/scientific_circt/verilator_callsite_entrypoint")
BRIDGE_SOURCE = Path("src/hybrid/scientific_circt_verilator_callsite_bridge.cpp")
DEFAULT_MDIR = Path("artifacts/scientific_circt/microgpt_attention_head/obj_dir")


def _sanitize(text: str) -> str:
    repo = Path.cwd().as_posix()
    text = text.replace(repo, "<repo>")
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root)/[^\s\"']+", "<local-path>", text)


def _display_path(path: Path) -> str:
    return _sanitize(path.as_posix())


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    return float(value) if isinstance(value, int | float) else None


def _run(argv: list[str]) -> dict[str, Any]:
    start = time.perf_counter()
    proc = subprocess.run(argv, text=True, capture_output=True, check=False)
    wall_ms = (time.perf_counter() - start) * 1000.0
    return {
        "argv": [_sanitize(arg) for arg in argv],
        "returncode": proc.returncode,
        "stdout": _sanitize(proc.stdout.strip()),
        "stderr": _sanitize(proc.stderr.strip()),
        "process_wall_ms": wall_ms,
    }


def _verilator_root() -> tuple[Path | None, dict[str, Any] | None]:
    env_root = os.environ.get("VERILATOR_ROOT")
    if env_root:
        return Path(env_root), None
    if shutil.which("verilator") is None:
        return None, {
            "argv": ["verilator", "--getenv", "VERILATOR_ROOT"],
            "returncode": 127,
            "stdout": "",
            "stderr": "missing verilator",
            "process_wall_ms": 0.0,
        }
    result = _run(["verilator", "--getenv", "VERILATOR_ROOT"])
    if result["returncode"] != 0 or not result["stdout"]:
        return None, result
    return Path(str(result["stdout"]).strip()), result


def _require_adapter_library(adapter: dict[str, Any]) -> Path:
    if adapter.get("status") != "adapter_correctness_passed":
        raise ValueError("runtime handoff adapter is not ready")
    if adapter.get("candidate") != "microgpt_attention_head" or adapter.get("shape") != "1024x1":
        raise ValueError("Verilator callsite entrypoint currently supports microgpt_attention_head 1024x1")
    library = adapter.get("adapter_library")
    if not isinstance(library, str) or not library:
        raise ValueError("adapter report missing adapter_library")
    return Path(library)


def _adapter_dimensions(adapter: dict[str, Any]) -> tuple[int, int, int, int]:
    nstates = int(adapter.get("nstates", 0))
    repeat = int(adapter.get("repeat", 0))
    inner_repeat = int(adapter.get("inner_repeat", 0))
    integration_batches = int(adapter.get("integration_batches", 0))
    if nstates <= 0 or repeat <= 0 or inner_repeat <= 0 or integration_batches <= 0:
        raise ValueError("adapter report missing positive nstates/repeat/inner_repeat/integration_batches")
    return nstates, repeat, inner_repeat, integration_batches


def _bridge_binary(out_dir: Path) -> Path:
    return out_dir / "scientific_circt_verilator_callsite_bridge"


def _compile_bridge(source: Path, binary: Path, mdir: Path, verilator_root: Path) -> dict[str, Any]:
    cxx = shutil.which("g++")
    if cxx is None:
        return {
            "argv": ["g++", "-O2", "-std=c++17", _display_path(source), "-o", _display_path(binary)],
            "returncode": 127,
            "stdout": "",
            "stderr": "missing g++",
            "process_wall_ms": 0.0,
        }
    binary.parent.mkdir(parents=True, exist_ok=True)
    include = verilator_root / "include"
    vltstd = include / "vltstd"
    return _run(
        [
            cxx,
            "-O2",
            "-std=c++17",
            source.as_posix(),
            "-I",
            mdir.as_posix(),
            "-I",
            include.as_posix(),
            "-I",
            vltstd.as_posix(),
            (mdir / "Vsim__ALL.a").as_posix(),
            (mdir / "verilated.o").as_posix(),
            (mdir / "verilated_threads.o").as_posix(),
            "-ldl",
            "-pthread",
            "-o",
            binary.as_posix(),
        ]
    )


def measure_verilator_callsite_entrypoint(
    adapter: dict[str, Any],
    *,
    out_dir: Path = OUT_DIR,
    bridge_source: Path = BRIDGE_SOURCE,
    mdir: Path = DEFAULT_MDIR,
) -> dict[str, Any]:
    library = _require_adapter_library(adapter)
    nstates, repeat, inner_repeat, integration_batches = _adapter_dimensions(adapter)
    binary = _bridge_binary(out_dir)
    verilator_root, verilator_root_command = _verilator_root()
    report: dict[str, Any] = {
        "schema_version": 1,
        "surface": "scientific_circt_verilator_callsite_entrypoint",
        "status": "entrypoint_ready",
        "candidate": adapter.get("candidate"),
        "shape": adapter.get("shape"),
        "source_adapter_report": _display_path(ADAPTER_REPORT),
        "source_adapter_library": _display_path(library),
        "verilator_mdir": _display_path(mdir),
        "bridge_source": _display_path(bridge_source),
        "bridge_binary": _display_path(binary),
        "entrypoint_kind": "src_hybrid_cxx_bridge_verilator_generated_callsite",
        "cpu_callsite_kind": "verilator_generated_Vsim_eval",
        "gpu_callsite_kind": "adapter_shared_library_dlopen",
        "subprocess_used_for_adapter": False,
        "python_process_spawn_used_for_bridge": True,
        "warmup_run_excluded_from_timing": True,
        "nstates": nstates,
        "repeat": repeat,
        "inner_repeat": inner_repeat,
        "integration_batches": integration_batches,
        "commands": [],
        "non_claims": [
            "not_full_microgpt_execution",
            "not_pcie_framing_evidence",
            "not_rtlmeter_evidence",
            "not_automatic_partitioning",
            "not_production_runtime_entrypoint",
        ],
    }
    if verilator_root_command is not None:
        report["commands"].append({"stage": "resolve_verilator_root", **verilator_root_command})
    required_paths = [
        library,
        bridge_source,
        mdir / "Vsim.h",
        mdir / "Vsim__ALL.a",
        mdir / "verilated.o",
        mdir / "verilated_threads.o",
    ]
    missing = [_display_path(path) for path in required_paths if not path.exists()]
    if verilator_root is None:
        report["status"] = "failed_missing_verilator_root"
        return report
    if missing:
        report["status"] = "failed_missing_verilator_callsite_inputs"
        report["missing_inputs"] = missing
        return report

    build = _compile_bridge(bridge_source, binary, mdir, verilator_root)
    report["commands"].append({"stage": "build_verilator_callsite_bridge", **build})
    if build["returncode"] != 0:
        report["status"] = "failed_verilator_callsite_bridge_build"
        return report

    run = _run(
        [
            binary.as_posix(),
            library.as_posix(),
            str(nstates),
            str(repeat),
            str(inner_repeat),
            str(integration_batches),
        ]
    )
    report["commands"].append({"stage": "run_verilator_callsite_bridge", **run})
    if run["returncode"] != 0:
        report["status"] = "failed_verilator_callsite_bridge_run"
        return report

    observed = json.loads(run["stdout"])
    cpu_ms = _number(observed.get("cpu_ms"))
    bridge_wall_ms = _number(observed.get("bridge_hybrid_wall_ms"))
    bridge_wall_per_batch = _number(observed.get("bridge_hybrid_wall_ms_per_integration_batch"))
    gpu_end_to_end_ms = _number(observed.get("gpu_end_to_end_ms"))
    gpu_kernel_ms = _number(observed.get("gpu_kernel_ms"))
    report.update(
        {
            "observed": observed,
            "verilator_callsite_used": observed.get("verilator_callsite_used") is True,
            "cpu_vs_gpu_output_equal": observed.get("cpu_vs_gpu_output_equal") is True,
            "cpu_vs_gpu_control_checksum_equal": observed.get("cpu_vs_gpu_control_checksum_equal") is True,
            "bridge_hybrid_wall_ms": bridge_wall_ms,
            "bridge_hybrid_wall_ms_per_integration_batch": bridge_wall_per_batch,
            "adapter_average": {
                "cpu_ms": cpu_ms,
                "gpu_end_to_end_ms": gpu_end_to_end_ms,
                "gpu_kernel_ms": gpu_kernel_ms,
                "cpu_to_gpu_end_to_end_speedup": _number(observed.get("cpu_to_gpu_end_to_end_speedup")),
                "cpu_to_gpu_kernel_speedup": _number(observed.get("cpu_to_gpu_kernel_speedup")),
            },
            "cpu_to_bridge_hybrid_wall_speedup": _number(
                observed.get("cpu_to_bridge_hybrid_wall_speedup")
            ),
            "next_required_evidence": (
                "replace_remaining_handwritten_gpu_adapter_kernel_with_lowered_or_generated_gpu_kernel"
            ),
        }
    )
    report["status"] = (
        "direct_verilator_callsite_entrypoint_timing_measured"
        if observed.get("status") == "direct_verilator_callsite_entrypoint_passed"
        and report["verilator_callsite_used"]
        and report["cpu_vs_gpu_output_equal"]
        and report["cpu_vs_gpu_control_checksum_equal"]
        and cpu_ms is not None
        and bridge_wall_per_batch is not None
        and cpu_ms > bridge_wall_per_batch
        else "direct_verilator_callsite_entrypoint_not_cpu_favorable_or_correctness_failed"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-report", type=Path, default=ADAPTER_REPORT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--mdir", type=Path, default=DEFAULT_MDIR)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        adapter = _load(args.adapter_report)
        report = measure_verilator_callsite_entrypoint(adapter, out_dir=args.out_dir, mdir=args.mdir)
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "direct_verilator_callsite_entrypoint_timing_measured" else 1


if __name__ == "__main__":
    raise SystemExit(main())
