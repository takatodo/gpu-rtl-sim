#!/usr/bin/env python3
"""Build a compile-time CPU/GPU protocol from scientific CIRCT measurements."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REPORT = Path("reports/scientific_circt_hybrid_protocol.json")

PROTOCOL_SHAPES: dict[str, dict[str, Any]] = {
    "dense_matmul_tile": {
        "gpu_subsystem": "dense_matmul_tile_arithmetic",
        "cpu_owner": "scenario_scheduler",
        "input_bytes_per_state": 32,
        "output_bytes_per_state": 16,
        "boundary_fields": ["a00", "a01", "a10", "a11", "b00", "b01", "b10", "b11", "y00", "y01"],
    },
    "batched_reduction": {
        "gpu_subsystem": "fixed_width_reduction_arithmetic",
        "cpu_owner": "scenario_scheduler",
        "input_bytes_per_state": 32,
        "output_bytes_per_state": 8,
        "boundary_fields": ["values[8]", "sum"],
    },
    "stencil_2d_tile": {
        "gpu_subsystem": "neighbor_stencil_arithmetic",
        "cpu_owner": "halo_and_boundary_scheduler",
        "input_bytes_per_state": 20,
        "output_bytes_per_state": 4,
        "boundary_fields": ["center", "north", "south", "east", "west", "next_center"],
    },
    "softmax_exp_pipeline": {
        "gpu_subsystem": "exp_softmax_like_arithmetic",
        "cpu_owner": "token_or_scenario_scheduler",
        "input_bytes_per_state": 16,
        "output_bytes_per_state": 16,
        "boundary_fields": ["logits[4]", "weights[4]"],
    },
    "microgpt_math_block": {
        "gpu_subsystem": "microgpt_regular_math_block",
        "cpu_owner": "microgpt_token_loop_and_state_authority",
        "input_bytes_per_state": 32,
        "output_bytes_per_state": 16,
        "boundary_fields": ["math_inputs", "math_outputs"],
    },
    "microgpt_attention_head": {
        "gpu_subsystem": "microgpt_attention_head_arithmetic",
        "cpu_owner": "microgpt_sequence_order_and_kv_cache_authority",
        "input_bytes_per_state": 20,
        "output_bytes_per_state": 32,
        "boundary_fields": ["q[4]", "k0[4]", "k1[4]", "v0[4]", "v1[4]", "head_out[4]"],
    },
    "microgpt_mlp_slice": {
        "gpu_subsystem": "microgpt_mlp_slice_arithmetic",
        "cpu_owner": "microgpt_token_loop_and_residual_authority",
        "input_bytes_per_state": 16,
        "output_bytes_per_state": 16,
        "boundary_fields": ["x[4]", "mlp_out[4]"],
    },
    "microgpt_block_slice": {
        "gpu_subsystem": "microgpt_block_level_arithmetic",
        "cpu_owner": "microgpt_token_loop_and_full_kv_cache_authority",
        "input_bytes_per_state": 12,
        "output_bytes_per_state": 16,
        "boundary_fields": ["x[4]", "k[2][2]", "v[2][2]", "block_out[2]"],
    },
    "microgpt_inference_slice": {
        "gpu_subsystem": "microgpt_two_token_inference_arithmetic",
        "cpu_owner": "microgpt_token_loop_sampler_and_full_kv_cache_authority",
        "input_bytes_per_state": 4,
        "output_bytes_per_state": 24,
        "boundary_fields": ["tok0", "pos0", "tok1", "pos1", "logit0", "logit1", "cache_digest"],
    },
}

SOURCE_VARIANT_SHAPES: dict[str, dict[str, Any]] = {
    "attention_head4_hls_friendly": {
        "gpu_subsystem": "microgpt_attention_head_hls_friendly_arithmetic",
        "cpu_owner": "microgpt_sequence_order_and_kv_cache_authority",
        "input_bytes_per_state": 80,
        "output_bytes_per_state": 128,
        "boundary_fields": ["q[4][4]", "k[4][2][4]", "v[4][2][4]", "head_out[4][4]"],
        "runtime_boundary_scope": "four_independent_attention_heads_per_state",
    },
    "mlp4_hls_friendly": {
        "gpu_subsystem": "microgpt_mlp_hls_friendly_arithmetic",
        "cpu_owner": "microgpt_token_loop_and_residual_authority",
        "input_bytes_per_state": 16,
        "output_bytes_per_state": 64,
        "boundary_fields": ["x[4]", "mlp_out[4][4]"],
        "runtime_boundary_scope": "four_independent_mlp_slices_per_state",
    },
    "block2_hls_friendly": {
        "gpu_subsystem": "microgpt_block_hls_friendly_arithmetic",
        "cpu_owner": "microgpt_token_loop_and_full_kv_cache_authority",
        "input_bytes_per_state": 24,
        "output_bytes_per_state": 32,
        "boundary_fields": ["x[2][4]", "k[2][2][2]", "v[2][2][2]", "block_out[2][2]"],
        "runtime_boundary_scope": "two_independent_block_slices_per_state",
    },
    "inference2_hls_friendly": {
        "gpu_subsystem": "microgpt_inference_hls_friendly_arithmetic",
        "cpu_owner": "microgpt_token_loop_sampler_and_full_kv_cache_authority",
        "input_bytes_per_state": 8,
        "output_bytes_per_state": 48,
        "boundary_fields": ["tok[2]", "pos[2]", "logit[2]", "cache_digest[2]"],
        "runtime_boundary_scope": "two_independent_two_token_inference_slices_per_state",
    },
}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _display_path(path: Path) -> str:
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root)/[^\s\"']+", "<local-path>", path.as_posix())


def _estimate(shape: dict[str, Any], nstates: int | None) -> dict[str, Any]:
    if not nstates:
        return {"available": False}
    input_bytes = int(shape["input_bytes_per_state"]) * nstates
    output_bytes = int(shape["output_bytes_per_state"]) * nstates
    return {
        "available": True,
        "logical_input_bytes": input_bytes,
        "logical_output_bytes": output_bytes,
        "logical_roundtrip_bytes": input_bytes + output_bytes,
        "nstates": nstates,
    }


def _candidate_protocol(candidate: str, policy: dict[str, Any], summary_entry: dict[str, Any] | None) -> dict[str, Any]:
    shape = PROTOCOL_SHAPES.get(candidate)
    min_nstates = policy.get("min_gpu_nstates")
    ready = policy.get("recommended_action") == "select_gpu_state_parallel" and bool(shape)
    return {
        "candidate": candidate,
        "status": "protocol_ready" if ready else "measure_or_define_protocol_before_gpu",
        "recommended_action": policy.get("recommended_action"),
        "required_steps": policy.get("required_steps"),
        "min_gpu_nstates": min_nstates,
        "first_gpu_end_to_end_favorable_shape": policy.get("first_gpu_end_to_end_favorable_shape"),
        "gpu_subsystem": shape.get("gpu_subsystem") if shape else None,
        "cpu_owner": shape.get("cpu_owner") if shape else None,
        "boundary_fields": shape.get("boundary_fields") if shape else [],
        "transfer_estimate_at_threshold": _estimate(shape, min_nstates) if shape else {"available": False},
        "transfer_estimate_at_1024x1": _estimate(shape, 1024) if shape else {"available": False},
        "best_measured_end_to_end_speedup": (
            summary_entry.get("best_gpu_end_to_end", {}).get("cpu_to_gpu_end_to_end_speedup")
            if isinstance(summary_entry, dict) and isinstance(summary_entry.get("best_gpu_end_to_end"), dict)
            else None
        ),
        "protocol_invariants": [
            "batch_entries_are_independent_scenarios",
            "cpu_preserves_global_sequence_order",
            "gpu_kernel_is_single_step_arithmetic_region",
            "cpu_fallback_below_threshold",
        ],
    }


def _shape_min_nstates(shape_name: object) -> int | None:
    if not isinstance(shape_name, str):
        return None
    match = re.fullmatch(r"([1-9][0-9]*)x([1-9][0-9]*)", shape_name)
    if not match:
        return None
    return int(match.group(1))


def _source_variant_protocol(policy: dict[str, Any]) -> dict[str, Any]:
    source_variant = policy.get("source_variant")
    shape = SOURCE_VARIANT_SHAPES.get(source_variant) if isinstance(source_variant, str) else None
    min_nstates = _shape_min_nstates(policy.get("shape"))
    action = policy.get("recommended_action")
    equality_ok = bool(policy.get("cpu_vs_gpu_output_equal")) and bool(policy.get("cpu_vs_gpu_control_checksum_equal"))
    ready = action == "promote_to_hls_gpu" and equality_ok and bool(shape) and isinstance(min_nstates, int)
    keep_baseline = action == "keep_baseline_gpu_or_cpu" and equality_ok
    if ready:
        status = "source_variant_protocol_ready"
    elif keep_baseline:
        status = "keep_baseline_protocol"
    else:
        status = "reject_or_measure_before_protocol"
    return {
        "candidate": policy.get("candidate"),
        "source_variant": source_variant,
        "shape": policy.get("shape"),
        "status": status,
        "recommended_action": action,
        "required_steps": 1,
        "min_gpu_nstates": min_nstates,
        "cpu_vs_gpu_output_equal": policy.get("cpu_vs_gpu_output_equal"),
        "cpu_vs_gpu_control_checksum_equal": policy.get("cpu_vs_gpu_control_checksum_equal"),
        "speedup_improved": policy.get("speedup_improved"),
        "baseline_speedup": policy.get("baseline_speedup"),
        "variant_speedup": policy.get("variant_speedup"),
        "speedup_delta": policy.get("speedup_delta"),
        "gpu_subsystem": shape.get("gpu_subsystem") if shape else None,
        "cpu_owner": shape.get("cpu_owner") if shape else None,
        "boundary_fields": shape.get("boundary_fields") if shape else [],
        "runtime_boundary_scope": shape.get("runtime_boundary_scope") if shape else None,
        "transfer_estimate_at_threshold": _estimate(shape, min_nstates) if shape else {"available": False},
        "protocol_invariants": [
            "source_variant_shape_matches_measured_policy_shape",
            "cpu_preserves_token_order_and_state_authority",
            "gpu_kernel_executes_hls_friendly_arithmetic_region",
            "cpu_fallback_when_variant_unpromoted_or_below_threshold",
        ],
    }


def build_protocol(policy: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    candidates = policy.get("candidates")
    if not isinstance(candidates, dict):
        raise ValueError("policy missing candidates object")
    by_candidate = summary.get("by_candidate")
    if not isinstance(by_candidate, dict):
        raise ValueError("summary missing by_candidate object")
    protocols = {
        str(candidate): _candidate_protocol(str(candidate), payload, by_candidate.get(candidate))
        for candidate, payload in sorted(candidates.items())
        if isinstance(payload, dict)
    }
    source_variants_payload = policy.get("source_variants", [])
    source_variants = {
        str(payload["source_variant"]): _source_variant_protocol(payload)
        for payload in source_variants_payload
        if isinstance(payload, dict) and isinstance(payload.get("source_variant"), str)
    }
    ready = [name for name, payload in protocols.items() if payload["status"] == "protocol_ready"]
    source_variant_ready = [
        name for name, payload in source_variants.items() if payload["status"] == "source_variant_protocol_ready"
    ]
    return {
        "schema_version": 1,
        "surface": "scientific_circt_hybrid_protocol",
        "status": "protocol_ready" if ready else "protocol_incomplete",
        "source_policy": policy.get("surface"),
        "source_summary": summary.get("surface"),
        "ready_candidate_count": len(ready),
        "source_variant_ready_count": len(source_variant_ready),
        "candidates": protocols,
        "source_variants": source_variants,
        "cpu_resident_subsystems": [
            "token_loop_control",
            "sampler_or_observable_authority",
            "full_kv_cache_state_authority",
            "unsupported_or_below_threshold_candidates",
        ],
        "handoff_protocol": {
            "dispatch_key": ["candidate", "source_variant", "nstates", "steps"],
            "required_steps": 1,
            "gpu_call_shape": "one_kernel_launch_per_candidate_batch",
            "fallback": "select_cpu_when_candidate_unmeasured_or_below_min_gpu_nstates",
            "transfer_accounting": "logical_payload_bytes_only; allocator, alignment, and PCIe framing are not included",
        },
        "non_claims": [
            "not_runtime_abi_authority",
            "not_a_general_rtl_speedup_claim",
            "not_rtlmeter_evidence",
            "not_full_microgpt_execution",
            "not_automatic_partitioning",
            "not_automatic_hls_rewrite",
        ],
    }


def decide(
    protocol: dict[str, Any],
    candidate: str,
    nstates: int,
    steps: int,
    source_variant: str | None = None,
) -> dict[str, Any]:
    if source_variant is not None:
        source_variants = protocol.get("source_variants")
        if not isinstance(source_variants, dict):
            raise ValueError("protocol missing source_variants object")
        payload = source_variants.get(source_variant)
        if not isinstance(payload, dict):
            return {
                "schema_version": 1,
                "surface": "scientific_circt_hybrid_dispatch_decision",
                "candidate": candidate,
                "source_variant": source_variant,
                "nstates": nstates,
                "steps": steps,
                "decision": "select_cpu",
                "reason": "source_variant_not_in_protocol",
                "fallback_used": True,
                "non_claims": protocol.get("non_claims", []),
            }
        if payload.get("candidate") != candidate:
            return {
                "schema_version": 1,
                "surface": "scientific_circt_hybrid_dispatch_decision",
                "candidate": candidate,
                "source_variant": source_variant,
                "nstates": nstates,
                "steps": steps,
                "decision": "select_cpu",
                "reason": "source_variant_candidate_mismatch",
                "fallback_used": True,
                "non_claims": protocol.get("non_claims", []),
            }
        required_steps = payload.get("required_steps")
        min_nstates = payload.get("min_gpu_nstates")
        action = payload.get("recommended_action")
        ready = payload.get("status") == "source_variant_protocol_ready"
        keep_baseline = payload.get("status") == "keep_baseline_protocol"
        use_variant = ready and steps == required_steps and isinstance(min_nstates, int) and nstates >= min_nstates
        if use_variant:
            decision = "promote_to_hls_gpu"
            reason = "measured_source_variant_at_or_above_threshold"
        elif steps != required_steps:
            decision = "select_cpu"
            reason = "steps_mismatch"
        elif keep_baseline:
            decision = "keep_baseline_gpu_or_cpu"
            reason = "source_variant_measured_but_not_faster_than_baseline"
        elif not ready:
            decision = "select_cpu"
            reason = "source_variant_protocol_not_ready"
        else:
            decision = "select_cpu"
            reason = "below_min_gpu_nstates"
        return {
            "schema_version": 1,
            "surface": "scientific_circt_hybrid_dispatch_decision",
            "candidate": candidate,
            "source_variant": source_variant,
            "shape": payload.get("shape"),
            "nstates": nstates,
            "steps": steps,
            "decision": decision,
            "reason": reason,
            "fallback_used": decision != "promote_to_hls_gpu",
            "recommended_action": action,
            "gpu_subsystem": payload.get("gpu_subsystem") if decision == "promote_to_hls_gpu" else None,
            "cpu_owner": payload.get("cpu_owner"),
            "min_gpu_nstates": min_nstates,
            "required_steps": required_steps,
            "baseline_speedup": payload.get("baseline_speedup"),
            "variant_speedup": payload.get("variant_speedup"),
            "speedup_delta": payload.get("speedup_delta"),
            "logical_roundtrip_bytes": (
                int(payload.get("transfer_estimate_at_threshold", {}).get("logical_roundtrip_bytes"))
                if decision == "promote_to_hls_gpu"
                and isinstance(payload.get("transfer_estimate_at_threshold"), dict)
                and isinstance(payload["transfer_estimate_at_threshold"].get("logical_roundtrip_bytes"), int)
                and nstates == min_nstates
                else None
            ),
            "non_claims": protocol.get("non_claims", []),
        }

    candidates = protocol.get("candidates")
    if not isinstance(candidates, dict):
        raise ValueError("protocol missing candidates object")
    payload = candidates.get(candidate)
    if not isinstance(payload, dict):
        return {
            "schema_version": 1,
            "surface": "scientific_circt_hybrid_dispatch_decision",
            "candidate": candidate,
            "nstates": nstates,
            "steps": steps,
            "decision": "select_cpu",
            "reason": "candidate_not_in_protocol",
            "fallback_used": True,
            "non_claims": protocol.get("non_claims", []),
        }
    required_steps = payload.get("required_steps")
    min_nstates = payload.get("min_gpu_nstates")
    ready = payload.get("status") == "protocol_ready"
    use_gpu = ready and steps == required_steps and isinstance(min_nstates, int) and nstates >= min_nstates
    if use_gpu:
        reason = "measured_candidate_at_or_above_threshold"
    elif not ready:
        reason = "candidate_protocol_not_ready"
    elif steps != required_steps:
        reason = "steps_mismatch"
    else:
        reason = "below_min_gpu_nstates"
    return {
        "schema_version": 1,
        "surface": "scientific_circt_hybrid_dispatch_decision",
        "candidate": candidate,
        "nstates": nstates,
        "steps": steps,
        "decision": "select_gpu_state_parallel" if use_gpu else "select_cpu",
        "reason": reason,
        "fallback_used": not use_gpu,
        "gpu_subsystem": payload.get("gpu_subsystem") if use_gpu else None,
        "cpu_owner": payload.get("cpu_owner"),
        "min_gpu_nstates": min_nstates,
        "required_steps": required_steps,
        "logical_roundtrip_bytes": (
            int(payload.get("transfer_estimate_at_threshold", {}).get("logical_roundtrip_bytes"))
            if use_gpu and isinstance(payload.get("transfer_estimate_at_threshold"), dict)
            and isinstance(payload["transfer_estimate_at_threshold"].get("logical_roundtrip_bytes"), int)
            and nstates == min_nstates
            else None
        ),
        "non_claims": protocol.get("non_claims", []),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=Path("reports/scientific_circt_gpu_selection_policy.json"))
    parser.add_argument("--summary", type=Path, default=Path("reports/scientific_circt_testbench_hybrid_advantage.json"))
    parser.add_argument("--protocol", type=Path, default=None)
    parser.add_argument("--candidate")
    parser.add_argument("--source-variant")
    parser.add_argument("--nstates", type=int)
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = _load(args.protocol) if args.protocol else build_protocol(_load(args.policy), _load(args.summary))
        if args.candidate is not None:
            if args.nstates is None:
                print("--candidate requires --nstates")
                return 2
            report = decide(report, args.candidate, args.nstates, args.steps, args.source_variant)
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if report.get("surface") == "scientific_circt_hybrid_dispatch_decision":
        return 0
    return 0 if report.get("status") == "protocol_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
