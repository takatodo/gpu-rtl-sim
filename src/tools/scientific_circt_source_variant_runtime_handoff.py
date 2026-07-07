#!/usr/bin/env python3
"""Measure the selected HLS source-variant runtime handoff boundary."""

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

from scientific_circt_bridge_spec import bridge_spec_from_metadata_row, render_bridge_gate_header
from scientific_circt_source_variant_metadata import src_hybrid_verilator_bridge_gate

REPORT = Path("reports/scientific_circt_source_variant_runtime_handoff.json")
SRC_HYBRID_REPORT = Path("reports/scientific_circt_source_variant_verilator_entrypoint.json")
SRC_HYBRID_BRIDGE = Path("src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp")
SRC_HYBRID_OUT_DIR = Path("artifacts/scientific_circt/source_variant_verilator_entrypoint")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _sanitize(text: str) -> str:
    text = text.replace(Path.cwd().as_posix(), "<repo>")
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root|usr)/[^\s\"']+", "<local-path>", text)


def _display_path(path: Path) -> str:
    return _sanitize(path.as_posix())


def _run(argv: list[str]) -> dict[str, Any]:
    start = time.perf_counter()
    proc = subprocess.run(argv, text=True, capture_output=True, check=False)
    return {
        "argv": [_sanitize(arg) for arg in argv],
        "returncode": proc.returncode,
        "stdout": _sanitize(proc.stdout.strip()),
        "stderr": _sanitize(proc.stderr.strip()),
        "process_wall_ms": (time.perf_counter() - start) * 1000.0,
    }


def _selected_boundary(matrix: dict[str, Any]) -> dict[str, Any]:
    selected = matrix.get("selected_next_source_variant_runtime_boundary")
    if isinstance(selected, dict):
        return selected
    queue = matrix.get("source_variant_runtime_integration_queue")
    if isinstance(queue, list):
        for row in queue:
            if isinstance(row, dict) and row.get("source_variant"):
                return row
    raise ValueError("dispatch matrix missing selected source-variant runtime boundary")


def _variant_report(summary: dict[str, Any], variant_name: str) -> dict[str, Any]:
    variants = summary.get("variants")
    if not isinstance(variants, list):
        raise ValueError("HLS variant report missing variants array")
    for variant in variants:
        if isinstance(variant, dict) and variant.get("variant") == variant_name:
            return variant
    raise ValueError(f"HLS variant report missing {variant_name}")


def _positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"variant report missing positive {key}")
    return value


def _shape_nstates(shape: object) -> int:
    nstates, steps = _shape_dimensions(shape)
    if steps != 1:
        raise ValueError("variant shape must be Nx1")
    return nstates


def _shape_dimensions(shape: object) -> tuple[int, int]:
    if not isinstance(shape, str):
        raise ValueError("variant shape must be Nx1")
    match = re.fullmatch(r"([1-9][0-9]*)x([1-9][0-9]*)", shape)
    if not match:
        raise ValueError("variant shape must be Nx1")
    return int(match.group(1)), int(match.group(2))


def _artifact(path: object) -> dict[str, Any]:
    if not isinstance(path, str):
        return {"path": None, "present": False, "executable": False}
    local = Path(path)
    return {
        "path": _display_path(local),
        "present": local.exists(),
        "executable": local.exists() and local.is_file() and bool(local.stat().st_mode & 0o111),
    }


def _metadata_rows_by_variant(metadata_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = metadata_report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("source variant metadata report missing rows array")
    by_variant: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("source_variant"), str):
            by_variant[str(row["source_variant"])] = row
    return by_variant


def _src_hybrid_metadata_gate(
    selected: dict[str, Any],
    metadata_row: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    return src_hybrid_verilator_bridge_gate(selected, metadata_row)


def _bind_hls_summary_to_gate(
    gate: dict[str, Any],
    selected: dict[str, Any],
    hls_variant: dict[str, Any],
    *,
    nstates: int,
    shape_steps: int,
) -> tuple[dict[str, Any], str | None]:
    checks = gate.setdefault("checks", {})
    checks["hls_candidate"] = hls_variant.get("candidate") == selected.get("candidate") == gate.get("candidate")
    checks["hls_source_variant"] = hls_variant.get("variant") == selected.get("source_variant") == gate.get("source_variant")
    checks["hls_shape"] = hls_variant.get("shape") == selected.get("shape") == gate.get("shape")
    checks["hls_steps"] = shape_steps == 1 and selected.get("steps") in (None, 1)
    gate["expected_nstates"] = _shape_nstates(gate.get("shape"))
    checks["argv_nstates"] = gate["expected_nstates"] == nstates
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        gate["failed_checks"] = failed
        return gate, "src_hybrid_verilator_metadata_gate_rejected"
    return gate, None


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
    start = time.perf_counter()
    proc = subprocess.run(["verilator", "--getenv", "VERILATOR_ROOT"], text=True, capture_output=True, check=False)
    raw_stdout = proc.stdout.strip()
    result = {
        "argv": ["verilator", "--getenv", "VERILATOR_ROOT"],
        "returncode": proc.returncode,
        "stdout": _sanitize(raw_stdout),
        "stderr": _sanitize(proc.stderr.strip()),
        "process_wall_ms": (time.perf_counter() - start) * 1000.0,
    }
    if proc.returncode != 0 or not raw_stdout:
        return None, result
    return Path(raw_stdout), result


def _write_src_hybrid_bridge_gate_header(
    metadata_row: dict[str, Any],
    out_dir: Path,
    *,
    selected: dict[str, Any] | None = None,
) -> Path:
    """Render the bridge gate header from a metadata row via BridgeSpec.

    The metadata row has already passed `src_hybrid_verilator_bridge_gate`
    scoped checks by the time this is called, so this only re-derives the
    same port-map-aware BridgeSpec for header rendering.
    """
    spec = bridge_spec_from_metadata_row(metadata_row, selected=selected)
    header = out_dir / "scientific_circt_source_variant_bridge_gate.h"
    header.parent.mkdir(parents=True, exist_ok=True)
    header.write_text(render_bridge_gate_header(spec), encoding="utf-8")
    return header


def _compile_src_hybrid_bridge(
    source: Path,
    binary: Path,
    mdir: Path,
    verilator_root: Path,
    gate_header: Path | None = None,
) -> dict[str, Any]:
    cxx = shutil.which(os.environ.get("CXX", "g++"))
    if cxx is None:
        return {
            "argv": ["g++", "-O3", "-std=c++17", _display_path(source), "-o", _display_path(binary)],
            "returncode": 127,
            "stdout": "",
            "stderr": "missing g++",
            "process_wall_ms": 0.0,
        }
    binary.parent.mkdir(parents=True, exist_ok=True)
    include = verilator_root / "include"
    vltstd = include / "vltstd"
    command = [
        cxx,
        "-O3",
        "-std=c++17",
        "-I",
        mdir.as_posix(),
        "-I",
        include.as_posix(),
        "-I",
        vltstd.as_posix(),
    ]
    if gate_header is not None:
        command.extend(["-include", gate_header.as_posix()])
    command.extend(
        [
            source.as_posix(),
            (mdir / "Vsim__ALL.a").as_posix(),
            (mdir / "verilated.o").as_posix(),
            (mdir / "verilated_threads.o").as_posix(),
            "-ldl",
            "-pthread",
            "-o",
            binary.as_posix(),
        ]
    )
    return _run(command)


def build_runtime_handoff_report(
    matrix: dict[str, Any],
    hls_summary: dict[str, Any],
    *,
    execute: bool = True,
    entrypoint: str = "direct-binary",
    src_hybrid_bridge: Path = SRC_HYBRID_BRIDGE,
    src_hybrid_out_dir: Path = SRC_HYBRID_OUT_DIR,
    selected_boundary: dict[str, Any] | None = None,
    metadata_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected = selected_boundary or _selected_boundary(matrix)
    variant_name = selected.get("source_variant")
    if not isinstance(variant_name, str):
        raise ValueError("selected boundary missing source_variant")
    variant = _variant_report(hls_summary, variant_name)
    artifacts = variant.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("variant report missing artifacts object")

    shape = str(variant.get("shape"))
    nstates, shape_steps = _shape_dimensions(shape)
    repeat = _positive_int(variant, "repeat")
    inner_repeat = _positive_int(variant, "inner_repeat")
    integration_batches = _positive_int(variant, "integration_batches")
    binary = artifacts.get("direct_callsite_binary")
    gpu_library = artifacts.get("gpu_library")
    mdir = artifacts.get("verilator_mdir")
    binary_artifact = _artifact(binary)
    library_artifact = _artifact(gpu_library)
    mdir_path = Path(mdir) if isinstance(mdir, str) else None

    report: dict[str, Any] = {
        "schema_version": 1,
        "surface": "scientific_circt_source_variant_runtime_handoff",
        "candidate": selected.get("candidate"),
        "source_variant": variant_name,
        "shape": shape,
        "nstates": nstates,
        "steps": selected.get("steps"),
        "source_matrix_surface": matrix.get("surface"),
        "source_hls_summary_surface": hls_summary.get("surface"),
        "selection_reason": selected.get("selection_reason"),
        "selected_queue_rank": selected.get("rank"),
        "expected": {
            "baseline_speedup": selected.get("baseline_speedup"),
            "variant_speedup": selected.get("variant_speedup"),
            "speedup_delta": selected.get("speedup_delta"),
        },
        "dimensions": {
            "repeat": repeat,
            "inner_repeat": inner_repeat,
            "integration_batches": integration_batches,
        },
        "artifacts": {
            "direct_callsite_binary": binary_artifact,
            "gpu_library": library_artifact,
            "systemverilog": _artifact(artifacts.get("systemverilog")),
            "verilator_mdir": _artifact(mdir),
            "src_hybrid_bridge_source": _artifact(src_hybrid_bridge.as_posix()),
        },
        "entrypoint_kind": entrypoint,
        "runtime_boundary": {
            "cpu_owner": selected.get("cpu_owner"),
            "gpu_subsystem": selected.get("gpu_subsystem"),
            "cpu_resident_authority": [
                "token_loop_order",
                "sampler_or_output_authority",
                "kv_cache_state_authority",
            ],
            "gpu_handoff_scope": "hls_friendly_batched_arithmetic_source_variant",
            "correctness_policy": "verilator_cpu_outputs_equal_gpu_outputs_for_same_input_batch",
        },
        "commands": [],
        "non_claims": [
            "not_full_microgpt_execution",
            "not_training_or_autograd",
            "not_pcie_framing_evidence",
            "not_rtlmeter_evidence",
            "not_automatic_hls_rewrite",
            "not_production_runtime_boundary",
        ],
    }

    run_binary = Path(str(binary))
    expected_observed_status = "hls_variant_measured"
    bridge_gate: dict[str, Any] | None = None
    bridge_gate, gate_rejection = _src_hybrid_metadata_gate(selected, metadata_row)
    report["metadata_gate"] = bridge_gate
    if gate_rejection is None and bridge_gate is not None:
        bridge_gate, gate_rejection = _bind_hls_summary_to_gate(
            bridge_gate,
            selected,
            variant,
            nstates=nstates,
            shape_steps=shape_steps,
        )
        report["metadata_gate"] = bridge_gate
    if gate_rejection is not None:
        report["status"] = gate_rejection
        return report
    if entrypoint == "src-hybrid-verilator" and mdir_path is None:
        report["status"] = "src_hybrid_verilator_mdir_missing"
        return report
    if not binary_artifact["present"] or not library_artifact["present"]:
        report["status"] = "runtime_handoff_artifacts_missing"
        return report
    if not execute:
        report["status"] = "runtime_handoff_artifacts_ready"
        return report

    if entrypoint == "src-hybrid-verilator":
        verilator_root, root_command = _verilator_root()
        if root_command is not None:
            report["commands"].append({"stage": "resolve_verilator_root", **root_command})
        required = [
            src_hybrid_bridge,
            mdir_path / "Vsim.h",
            mdir_path / "Vsim__ALL.a",
            mdir_path / "verilated.o",
            mdir_path / "verilated_threads.o",
        ]
        missing = [_display_path(path) for path in required if not path.exists()]
        if verilator_root is None:
            report["status"] = "src_hybrid_verilator_root_missing"
            return report
        if missing:
            report["status"] = "src_hybrid_verilator_inputs_missing"
            report["missing_inputs"] = missing
            return report
        run_binary = src_hybrid_out_dir / "scientific_circt_source_variant_verilator_bridge"
        gate_header = _write_src_hybrid_bridge_gate_header(metadata_row, src_hybrid_out_dir, selected=selected)
        report["metadata_gate"]["generated_header"] = _artifact(gate_header.as_posix())
        report["metadata_gate"]["generated_header_source"] = "source_variant_metadata_row"
        compile_result = _compile_src_hybrid_bridge(
            src_hybrid_bridge,
            run_binary,
            mdir_path,
            verilator_root,
            gate_header,
        )
        report["commands"].append({"stage": "build_src_hybrid_verilator_bridge", **compile_result})
        if compile_result["returncode"] != 0:
            report["status"] = "src_hybrid_verilator_bridge_build_failed"
            return report
        report["artifacts"]["src_hybrid_bridge_binary"] = _artifact(run_binary.as_posix())
        expected_observed_status = "src_hybrid_verilator_callsite_passed"
    elif entrypoint != "direct-binary":
        raise ValueError("entrypoint must be direct-binary or src-hybrid-verilator")

    command = [
        run_binary.as_posix(),
        str(gpu_library),
    ]
    if entrypoint == "src-hybrid-verilator" and bridge_gate is not None:
        command.extend(
            [
                str(bridge_gate["candidate"]),
                str(bridge_gate["source_variant"]),
                str(bridge_gate["shape"]),
                str(bridge_gate["run_gpu_outputs_symbol"]),
                str(bridge_gate["run_hybrid_json_symbol"]),
                str(bridge_gate["input_element_type"]),
                str(bridge_gate["input_element_count"]),
                str(bridge_gate["output_element_type"]),
                str(bridge_gate["output_element_count"]),
            ]
        )
    command.extend([str(nstates), str(repeat), str(inner_repeat), str(integration_batches)])
    result = _run(command)
    report["commands"].append({"stage": "source_variant_runtime_handoff_run", **result})
    if result["returncode"] != 0:
        report["status"] = "runtime_handoff_run_failed"
        return report
    observed = json.loads(result["stdout"])
    report["observed"] = observed
    report["input_bytes"] = observed.get("input_bytes")
    report["output_bytes"] = observed.get("output_bytes")
    report["cpu_vs_gpu_output_equal"] = observed.get("cpu_vs_gpu_output_equal") is True
    report["cpu_vs_gpu_control_checksum_equal"] = observed.get("cpu_vs_gpu_control_checksum_equal") is True
    report["average"] = {
        "cpu_ms": observed.get("cpu_ms"),
        "gpu_end_to_end_ms": observed.get("gpu_end_to_end_ms"),
        "gpu_kernel_ms": observed.get("gpu_kernel_ms"),
        "bridge_hybrid_wall_ms_per_integration_batch": observed.get("bridge_hybrid_wall_ms_per_integration_batch"),
        "cpu_to_gpu_end_to_end_speedup": observed.get("cpu_to_gpu_end_to_end_speedup"),
        "cpu_to_gpu_kernel_speedup": observed.get("cpu_to_gpu_kernel_speedup"),
        "cpu_to_bridge_hybrid_wall_speedup": observed.get("cpu_to_bridge_hybrid_wall_speedup"),
    }
    speedup = observed.get("cpu_to_bridge_hybrid_wall_speedup")
    expected_speedup = selected.get("variant_speedup")
    report["selected_speedup_matches_observed"] = (
        isinstance(speedup, int | float)
        and isinstance(expected_speedup, int | float)
        and abs(float(speedup) - float(expected_speedup)) <= max(0.05, abs(float(expected_speedup)) * 0.2)
    )
    report["status"] = (
        "runtime_handoff_boundary_measured"
        if observed.get("status") == expected_observed_status
        and report["cpu_vs_gpu_output_equal"]
        and report["cpu_vs_gpu_control_checksum_equal"]
        else "runtime_handoff_boundary_failed"
    )
    if report["status"] == "runtime_handoff_boundary_measured" and entrypoint == "src-hybrid-verilator":
        report["status"] = "src_hybrid_verilator_runtime_handoff_measured"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=Path("reports/scientific_circt_hybrid_dispatch_matrix.json"))
    parser.add_argument(
        "--hls-variant-report",
        type=Path,
        default=Path("reports/scientific_circt_hls_mlp_block_variants.json"),
    )
    parser.add_argument("--no-execute", action="store_true")
    parser.add_argument("--entrypoint", choices=("direct-binary", "src-hybrid-verilator"), default="direct-binary")
    parser.add_argument("--src-hybrid-bridge", type=Path, default=SRC_HYBRID_BRIDGE)
    parser.add_argument("--src-hybrid-out-dir", type=Path, default=SRC_HYBRID_OUT_DIR)
    parser.add_argument("--metadata-report", type=Path, default=None)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        matrix = _load(args.matrix)
        selected = _selected_boundary(matrix)
        metadata_row = None
        if args.metadata_report is not None:
            source_variant = selected.get("source_variant")
            if not isinstance(source_variant, str):
                raise ValueError("selected boundary missing source_variant")
            metadata_row = _metadata_rows_by_variant(_load(args.metadata_report)).get(source_variant)
        report = build_runtime_handoff_report(
            matrix,
            _load(args.hls_variant_report),
            execute=not args.no_execute,
            entrypoint=args.entrypoint,
            src_hybrid_bridge=args.src_hybrid_bridge,
            src_hybrid_out_dir=args.src_hybrid_out_dir,
            metadata_row=metadata_row,
        )
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        report_out = args.report_out or (SRC_HYBRID_REPORT if args.entrypoint == "src-hybrid-verilator" else REPORT)
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") in {
        "runtime_handoff_boundary_measured",
        "src_hybrid_verilator_runtime_handoff_measured",
        "runtime_handoff_artifacts_ready",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
