#!/usr/bin/env python3
"""Define a first runtime handoff ABI candidate from the scientific dispatch queue."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from scientific_circt_hybrid_protocol import _load

REPORT = Path("reports/scientific_circt_runtime_handoff_abi.json")


def _display_path(path: Path) -> str:
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root)/[^\s\"']+", "<local-path>", path.as_posix())


def _top_queue_row(matrix: dict[str, Any]) -> dict[str, Any]:
    row = matrix.get("top_runtime_integration_candidate")
    if isinstance(row, dict):
        return row
    queue = matrix.get("runtime_integration_queue")
    if isinstance(queue, list) and queue and isinstance(queue[0], dict):
        return queue[0]
    raise ValueError("dispatch matrix missing top runtime integration candidate")


def _candidate_protocol(protocol: dict[str, Any], candidate: str) -> dict[str, Any]:
    candidates = protocol.get("candidates")
    if not isinstance(candidates, dict):
        raise ValueError("protocol missing candidates object")
    payload = candidates.get(candidate)
    if not isinstance(payload, dict):
        raise ValueError(f"protocol missing candidate {candidate}")
    return payload


def _artifact_ready(path: str | None) -> dict[str, Any]:
    if not path:
        return {"path": None, "present": False}
    local = Path(path)
    return {"path": _display_path(local), "present": local.exists()}


def build_handoff_abi(
    matrix: dict[str, Any],
    protocol: dict[str, Any],
    timing_report: dict[str, Any],
    systemverilog: Path,
    cpu_reference_binary: Path,
    gpu_timing_binary: Path,
) -> dict[str, Any]:
    top = _top_queue_row(matrix)
    candidate = str(top.get("candidate"))
    shape = str(top.get("shape"))
    if candidate != "microgpt_attention_head" or shape != "1024x1":
        raise ValueError("first runtime handoff ABI expects top candidate microgpt_attention_head 1024x1")
    payload = _candidate_protocol(protocol, candidate)
    if payload.get("status") != "protocol_ready":
        raise ValueError(f"{candidate}: protocol is not ready")
    timing = top
    nstates = int(top.get("nstates", 0))
    input_bytes_per_state = 20
    output_bytes_per_state = 32
    expected_input_bytes = input_bytes_per_state * nstates
    expected_output_bytes = output_bytes_per_state * nstates
    artifacts = {
        "systemverilog": _artifact_ready(systemverilog.as_posix()),
        "verilator_cpu_reference_binary": _artifact_ready(cpu_reference_binary.as_posix()),
        "gpu_timing_binary": _artifact_ready(gpu_timing_binary.as_posix()),
    }
    timing_ok = (
        timing_report.get("status") == "measured"
        and timing_report.get("candidate") == candidate
        and timing_report.get("shape") == shape
        and isinstance(timing_report.get("median"), dict)
    )
    artifacts_ready = all(record["present"] for record in artifacts.values())
    status = "handoff_abi_ready" if timing_ok and artifacts_ready else "handoff_abi_incomplete"
    return {
        "schema_version": 1,
        "surface": "scientific_circt_runtime_handoff_abi",
        "status": status,
        "candidate": candidate,
        "shape": shape,
        "nstates": nstates,
        "steps": top.get("steps"),
        "source_matrix_surface": matrix.get("surface"),
        "source_protocol_surface": protocol.get("surface"),
        "source_timing_surface": timing_report.get("surface"),
        "runtime_queue_rank": top.get("rank", 1),
        "measured_speedup": {
            "cpu_to_gpu_end_to_end_speedup": timing.get("cpu_to_gpu_end_to_end_speedup"),
            "cpu_to_gpu_kernel_speedup": timing.get("cpu_to_gpu_kernel_speedup"),
            "cpu_ms": timing.get("cpu_ms"),
            "gpu_end_to_end_ms": timing.get("gpu_end_to_end_ms"),
            "gpu_kernel_ms": timing.get("gpu_kernel_ms"),
        },
        "handoff_abi": {
            "layout": "array_of_structs",
            "state_count": nstates,
            "input_struct": {
                "name": "MicrogptAttentionHeadIn",
                "bytes_per_state": input_bytes_per_state,
                "fields": [
                    {"name": "q", "count": 4, "type": "uint8"},
                    {"name": "k0", "count": 4, "type": "uint8"},
                    {"name": "k1", "count": 4, "type": "uint8"},
                    {"name": "v0", "count": 4, "type": "uint8"},
                    {"name": "v1", "count": 4, "type": "uint8"},
                ],
            },
            "output_struct": {
                "name": "MicrogptAttentionHeadOut",
                "bytes_per_state": output_bytes_per_state,
                "fields": [{"name": "y", "count": 4, "type": "uint64"}],
            },
            "logical_input_bytes": expected_input_bytes,
            "logical_output_bytes": expected_output_bytes,
            "logical_roundtrip_bytes": expected_input_bytes + expected_output_bytes,
            "cpu_owner": payload.get("cpu_owner"),
            "gpu_subsystem": payload.get("gpu_subsystem"),
            "correctness_policy": "cpu_reference_outputs_equal_gpu_outputs_for_same_input_batch",
            "runtime_adapter_entrypoint": "future_microgpt_attention_head_handoff_adapter",
        },
        "artifacts": artifacts,
        "timing_report_matches": timing_ok,
        "artifacts_ready": artifacts_ready,
        "next_required_evidence": [
            "materialize_runtime_adapter_source_for_this_abi",
            "run_cpu_reference_and_gpu_adapter_on_identical_input_batch",
            "record_cpu_vs_hybrid_output_equality_before_runtime_speedup_claim",
        ],
        "non_claims": [
            "not_runtime_execution_evidence",
            "not_runtime_speedup_claim",
            "not_pcie_framing_evidence",
            "not_full_microgpt_execution",
            "not_rtlmeter_evidence",
            "not_automatic_partitioning",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=Path("reports/scientific_circt_hybrid_dispatch_matrix.json"))
    parser.add_argument("--protocol", type=Path, default=Path("reports/scientific_circt_hybrid_protocol.json"))
    parser.add_argument(
        "--timing-report",
        type=Path,
        default=Path("reports/scientific_circt_microgpt_attention_head_1024x1.json"),
    )
    parser.add_argument(
        "--systemverilog",
        type=Path,
        default=Path("artifacts/scientific_circt/microgpt_attention_head/microgpt_attention_head.sv"),
    )
    parser.add_argument(
        "--cpu-reference-binary",
        type=Path,
        default=Path("artifacts/scientific_circt/microgpt_attention_head/obj_dir/Vsim"),
    )
    parser.add_argument(
        "--gpu-timing-binary",
        type=Path,
        default=Path("artifacts/scientific_circt/microgpt_attention_head/microgpt_attention_head_gpu_timing"),
    )
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = build_handoff_abi(
            _load(args.matrix),
            _load(args.protocol),
            _load(args.timing_report),
            args.systemverilog,
            args.cpu_reference_binary,
            args.gpu_timing_binary,
        )
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "handoff_abi_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
