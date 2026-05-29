#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from hybrid_config_benchmark import benchmark_gate
from hybrid_config_spec import HybridConfigSpec, default_gate_name, default_paths


REPO_ROOT = Path(__file__).resolve().parents[2]

ITA_FULL_TOP_REQUIRED_SOURCES = (
    "third_party/common_cells/src/cf_math_pkg.sv",
    "third_party/common_cells/src/lzc.sv",
    "third_party/common_cells/src/fifo_v3.sv",
    "third_party/ITA/src/ita_package.sv",
)


def _repo_relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError as exc:
        raise ValueError(f"path is outside repository: {path}") from exc


def _require_tracked_template(raw_path: str) -> Path:
    path = (REPO_ROOT / raw_path).resolve()
    relative = _repo_relative_path(path)
    if not relative.startswith("config/slice_launch_templates/") or not relative.endswith(".json"):
        raise ValueError(
            "copy source-closure template must be a tracked config/slice_launch_templates/*.json file"
        )
    if not path.exists():
        raise ValueError(f"copy source-closure template does not exist: {relative}")
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"copy source-closure template is not tracked: {relative}")
    return path


def _load_known_template(raw_path: str) -> tuple[str, dict]:
    path = _require_tracked_template(raw_path)
    relative = _repo_relative_path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return relative, payload


def _load_known_template_source_closure(raw_path: str) -> tuple[list[str], dict]:
    relative, payload = _load_known_template(raw_path)
    source_files = [str(item) for item in payload.get("source_files") or []]
    source_closure = dict(payload.get("source_closure") or {})
    status = source_closure.get("status")
    if status != "complete":
        raise ValueError(
            f"copy source-closure template must declare source_closure.status=complete: {relative}"
        )
    if not source_files:
        raise ValueError(f"copy source-closure template has no source_files: {relative}")
    source_closure["provenance"] = "copied_from_known_tracked_template"
    source_closure["reference_template"] = relative
    source_closure["copied_from_template"] = relative
    source_closure["source_file_count"] = len(source_files)
    source_closure["source_files_sha256"] = hashlib.sha256(
        "\n".join(source_files).encode("utf-8")
    ).hexdigest()
    return source_files, source_closure


def _merge_verilator_args_from_known_template(raw_path: str, local_args: list[str]) -> list[str]:
    _relative, payload = _load_known_template(raw_path)
    merged: list[str] = []
    for arg in [*(payload.get("verilator_args") or []), *local_args]:
        value = str(arg)
        if value not in merged:
            merged.append(value)
    return merged


def _validate_requested_sources_in_copied_closure(
    requested_sources: list[str],
    copied_sources: list[str],
    *,
    reference_template: str,
) -> None:
    copied = set(copied_sources)
    missing = [source for source in requested_sources if source not in copied]
    if missing:
        raise ValueError(
            "requested --source entries are not present in copied source closure "
            f"from {reference_template}: {', '.join(missing)}"
        )


def source_closure_metadata(spec: HybridConfigSpec, source_files: list[str]) -> dict:
    if spec.copy_source_closure_from_template:
        _source_files, source_closure = _load_known_template_source_closure(
            spec.copy_source_closure_from_template
        )
        return source_closure

    source_set = set(source_files)
    provenance = "operator_supplied_complete_source_list" if spec.source_files else "refused_or_unknown"
    status = "complete" if spec.source_files else "unknown"
    risk = None
    missing_required_sources: list[str] = []

    if "third_party/ITA/src/ita.sv" in source_set:
        missing_required_sources = [
            item for item in ITA_FULL_TOP_REQUIRED_SOURCES if item not in source_set
        ]
        if missing_required_sources:
            status = "incomplete"
            provenance = "refused_or_unknown"
            risk = "third_party/ITA/src/ita.sv imports ita_package/common_cells dependencies that are not in source_files"

    return {
        "status": status,
        "provenance": provenance,
        "source_file_count": len(source_files),
        "missing_required_sources": missing_required_sources,
        "risk": risk,
        "policy": {
            "explicit_source_closure_required_for_execution": True,
            "known_template_source_closure_copy_allowed": True,
            "automatic_dependency_inference_for_arbitrary_rtl_implemented": False,
        },
        "non_claims": [
            "not automatic dependency inference for arbitrary RTL",
            "not native Verilator option support",
            "not automatic optimal GPU allocation",
        ],
    }


def coverage_manifest(spec: HybridConfigSpec) -> dict:
    return {
        "schema_version": 1,
        "target": spec.target,
        "coverage_domain": "toggle_real_subset_bitmap",
        "top_module": spec.top_module,
        "regions": [
            {
                "name": f"{spec.target_name}_counts",
                "words": [f"real_toggle_subset_word{idx}_o" for idx in range(8)],
            },
            {
                "name": f"{spec.target_name}_signatures",
                "words": [f"real_toggle_subset_word{idx}_o" for idx in range(8, 14)],
            },
            {
                "name": f"{spec.target_name}_samples",
                "words": [f"real_toggle_subset_word{idx}_o" for idx in range(14, 18)],
            },
        ],
        "non_claims": [
            "not correctness equivalence beyond scoped output words",
            "not raw full-state equality",
        ],
    }


def launch_template(spec: HybridConfigSpec, *, gate_path: str, manifest_path: str) -> dict:
    copied_source_closure: dict | None = None
    if spec.copy_source_closure_from_template:
        source_files, copied_source_closure = _load_known_template_source_closure(
            spec.copy_source_closure_from_template
        )
        _validate_requested_sources_in_copied_closure(
            spec.source_files,
            source_files,
            reference_template=str(copied_source_closure["reference_template"]),
        )
    else:
        source_files = list(spec.source_files)
    planned_overlay_status = "not_applicable"
    if spec.overlay:
        planned_overlay_status = "implemented"
        if spec.overlay not in source_files:
            source_files.append(spec.overlay)
    source_closure = copied_source_closure or source_closure_metadata(spec, source_files)
    verilator_args = list(spec.verilator_args)
    if spec.copy_source_closure_from_template:
        verilator_args = _merge_verilator_args_from_known_template(
            spec.copy_source_closure_from_template,
            verilator_args,
        )
    return {
        "schema_version": 1,
        "status": spec.status,
        "target": spec.target,
        "source_gate": gate_path,
        "top_module": spec.top_module,
        "build": {
            "mdir": spec.resolved_mdir,
            "work_dir": spec.resolved_work_dir,
            "host_probe_target": spec.resolved_host_probe_target,
            "host_probe_builder": "src/tools/build_host_probe.py",
            "host_probe": {
                "output": "tlul_slice_host_probe",
                "clock_field": spec.clock_field or f"{spec.top_module}__DOT__clk_i",
                "clock_report_name": spec.clock_report_name,
                "reset_field": spec.reset_field or f"{spec.top_module}__DOT__reset_like_w",
                "reset_report_name": spec.reset_report_name,
                "reset_asserted_value": spec.reset_asserted_value,
                "reset_deasserted_value": spec.reset_deasserted_value,
                "host_clock_control": spec.host_clock_control,
                "host_reset_control": spec.host_reset_control,
                "probe_syms_state": spec.probe_syms_state,
            },
            "verilator_mode": "flattened" if "--flatten" in verilator_args else "default",
        },
        "source_files": source_files,
        "source_closure": source_closure,
        "verilator_args": verilator_args,
        "planned_overlay": {
            "coverage_tb_path": spec.overlay,
            "coverage_manifest_path": manifest_path,
            "launch_template_path": f"config/slice_launch_templates/{spec.target_name}.json",
            "host_probe_target": spec.resolved_host_probe_target,
            "host_probe_builder": "src/tools/build_host_probe.py",
            "makefile": "not_required_for_generated_template",
            "status": planned_overlay_status,
        },
        "acceptance": {
            "candidate_only_until_first_cpu_vs_hybrid_benchmark": True,
            "next_gate_must_build_cpu_reference": True,
            "next_gate_must_build_gpu_cubin": True,
            "next_gate_must_compare_cpu_vs_hybrid": True,
            "speedup_claim_allowed_by_template_alone": False,
        },
        "non_claims": [
            "not raw full-state equality",
            "not broad speedup",
        ],
    }


def generated_payloads(spec: HybridConfigSpec) -> dict[str, dict]:
    paths = default_paths(spec)
    return {
        paths["manifest"]: coverage_manifest(spec),
        paths["template"]: launch_template(spec, gate_path=paths["gate"], manifest_path=paths["manifest"]),
        paths["gate"]: benchmark_gate(spec, manifest_path=paths["manifest"], template_path=paths["template"]),
    }


def write_payloads(payloads: dict[str, dict], *, dry_run: bool = False, allow_overwrite: bool = False) -> None:
    for raw_path, payload in payloads.items():
        path = REPO_ROOT / raw_path
        print(f"write: {raw_path}")
        if dry_run:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            continue
        if path.exists() and not allow_overwrite:
            raise FileExistsError(
                f"refusing to overwrite existing source-of-truth file: {raw_path}; "
                "choose a new target/gate name or pass allow_overwrite from a reviewed gate"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
