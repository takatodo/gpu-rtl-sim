#!/usr/bin/env python3
"""
Compare stock-Verilator hybrid outputs between:
  1) single-kernel vl_eval_batch_gpu
  2) phase-split launch_sequence (ico/nba)

This is a regression harness for Phase B fidelity work. It rebuilds the cubin in both modes,
runs src/tools/run_vl_hybrid.py twice with identical launch settings, dumps the final device
storage, and reports whether the bytewise state images match.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path

from build_vl_gpu import CLANG, CXX_STANDARD, build_vl_gpu, find_prefix, verilator_include_dir


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
RUN_VL_HYBRID = SCRIPT_DIR / "run_vl_hybrid.py"
FIELD_MACRO_RE = re.compile(r"^\s*VL_(?:IN|OUT)\d*\(\s*([A-Za-z_]\w*)\s*,")
FIELD_DECL_RE = re.compile(r"([A-Za-z_]\w*)\s*;\s*$")
FIELD_DECL_WITH_TYPE_RE = re.compile(
    r"^\s*(?P<decl_type>.+?)\s+(?P<name>[A-Za-z_]\w*)\s*(?:\[[^\]]+\])?\s*;\s*$"
)
SECTION_COMMENT_RE = re.compile(r"^\s*//\s+([A-Z][A-Z0-9_ ]+)\s*$")
VERILATOR_INTERNAL_FIELDS = {"vlSymsp", "vlNamep", "__VdlySched"}
ACCEPTANCE_POLICY_STRICT = "strict_final_state"
ACCEPTANCE_POLICY_IGNORE_INTERNAL = "ignore_verilator_internal_final_state"
ACCEPTANCE_POLICY_PHASE_B_ENDPOINT = "phase_b_endpoint"
ACCEPTANCE_POLICY_NORMALIZED_FINAL_STATE = "normalized_final_state_equivalence"
ACCEPTANCE_POLICY_COVERAGE_OUTPUT = "coverage_output_equivalence"
NORMALIZED_FINAL_STATE_POLICY_NAME = "primitive_design_state_fields_only"
COVERAGE_OUTPUT_POLICY_NAME = "tlul_coverage_output_strict_equality"
COVERAGE_OUTPUT_REQUIRED_DOMAIN = "toggle_real_subset_bitmap"
COVERAGE_OUTPUT_REQUIRED_PREFIX = "real_toggle_subset_word"
COVERAGE_OUTPUT_REQUIRED_COUNT = 18
NORMALIZED_FINAL_STATE_EXCLUSIONS = [
    "CELLS pointer fields",
    "std::string",
    "VlQueue",
    "VlClassRef",
    "scheduler objects",
    "internal variables section",
    "parameters",
]
PHASE_B_ALLOWED_INTERNAL_FIELDS = {
    "__VicoPhaseResult",
    "__VactIterCount",
    "__VinactIterCount",
    "__VicoTriggered",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_root_member_declarations(root_h: Path) -> list[dict[str, str]]:
    declarations: list[dict[str, str]] = []
    section = ""
    for raw_line in root_h.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        section_match = SECTION_COMMENT_RE.match(line)
        if section_match:
            section = section_match.group(1)
            continue
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        if line in {"public:", "private:", "protected:", "};"}:
            continue
        if line.startswith("class ") or line.startswith("struct {"):
            continue
        macro_match = FIELD_MACRO_RE.match(line)
        if macro_match:
            declarations.append(
                {
                    "name": macro_match.group(1),
                    "decl_type": line.split("(", 1)[0].strip(),
                    "section": section,
                    "declaration": line,
                }
            )
            continue
        if "(" in line or ")" in line:
            continue
        decl_with_type_match = FIELD_DECL_WITH_TYPE_RE.match(line)
        if decl_with_type_match:
            declarations.append(
                {
                    "name": decl_with_type_match.group("name"),
                    "decl_type": decl_with_type_match.group("decl_type").strip(),
                    "section": section,
                    "declaration": line,
                }
            )
            continue
        decl_match = FIELD_DECL_RE.search(line)
        if decl_match:
            declarations.append(
                {
                    "name": decl_match.group(1),
                    "decl_type": "",
                    "section": section,
                    "declaration": line,
                }
            )
    return declarations


def extract_root_member_names(root_h: Path) -> list[str]:
    names: list[str] = []
    for declaration in extract_root_member_declarations(root_h):
        names.append(declaration["name"])
    return names


def classify_field_role(field_name: str) -> str:
    if field_name.startswith("__V") or field_name in VERILATOR_INTERNAL_FIELDS:
        return "verilator_internal"
    if "__DOT__" in field_name:
        return "design_state"
    if field_name.endswith("_i") or field_name.endswith("_o"):
        return "top_level_io"
    return "other"


def probe_root_layout(mdir: Path) -> list[dict[str, int | str]]:
    prefix = find_prefix(mdir)
    root_type = f"{prefix}___024root"
    root_h = mdir / f"{root_type}.h"
    declarations = extract_root_member_declarations(root_h)
    member_names = [entry["name"] for entry in declarations]
    if not member_names:
        return []
    metadata_by_name = {entry["name"]: entry for entry in declarations}

    probe_lines = [
        "#include <cstddef>",
        "#include <cstdio>",
        f'#include "{root_h.resolve()}"',
        "int main() {",
    ]
    for name in member_names:
        probe_lines.append(
            f'  std::printf("{name}\\t%zu\\t%zu\\n", '
            f"offsetof({root_type}, {name}), sizeof((({root_type}*)nullptr)->{name}));"
        )
    probe_lines.append("  return 0;")
    probe_lines.append("}")
    probe_src = "\n".join(probe_lines) + "\n"

    with tempfile.TemporaryDirectory(prefix="vl_root_layout_") as tmpdir:
        tmp = Path(tmpdir)
        src = tmp / "probe_layout.cpp"
        exe = tmp / "probe_layout"
        src.write_text(probe_src, encoding="utf-8")
        cmd = [
            CLANG,
            f"-std={CXX_STANDARD}",
            "-Wno-invalid-offsetof",
            f"-I{mdir}",
            f"-I{verilator_include_dir()}",
            str(src),
            "-o",
            str(exe),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        result = subprocess.run([str(exe)], check=True, capture_output=True, text=True)

    layout: list[dict[str, int | str]] = []
    for line in result.stdout.splitlines():
        name, offset, size = line.split("\t")
        entry: dict[str, int | str] = {"name": name, "offset": int(offset), "size": int(size)}
        metadata = metadata_by_name.get(name)
        if metadata:
            entry["decl_type"] = metadata.get("decl_type", "")
            entry["section"] = metadata.get("section", "")
            entry["declaration"] = metadata.get("declaration", "")
        layout.append(entry)
    layout.sort(key=lambda entry: (int(entry["offset"]), int(entry["size"]), str(entry["name"])))
    return layout


def annotate_state_offset(
    layout: list[dict[str, int | str]], state_offset: int | None
) -> dict[str, int | str] | None:
    if state_offset is None:
        return None
    for entry in layout:
        start = int(entry["offset"])
        size = int(entry["size"])
        if start <= state_offset < start + size:
            return {
                "field_name": str(entry["name"]),
                "field_offset": start,
                "field_size": size,
                "field_byte_offset": state_offset - start,
            }
    return None


def summarize_mismatch_fields(
    single: bytes,
    split: bytes,
    *,
    storage_size: int,
    layout: list[dict[str, int | str]],
    limit: int = 16,
) -> tuple[int, list[dict[str, object]], list[dict[str, object]], dict[str, dict[str, int]]]:
    groups: dict[tuple[str, int], dict[str, object]] = {}
    max_len = max(len(single), len(split))
    for idx in range(max_len):
        single_byte = single[idx] if idx < len(single) else None
        split_byte = split[idx] if idx < len(split) else None
        if single_byte == split_byte:
            continue
        state_offset = idx % storage_size if storage_size > 0 else idx
        state_index = idx // storage_size if storage_size > 0 else 0
        annotation = annotate_state_offset(layout, state_offset)
        field_name = str(annotation["field_name"]) if annotation else "<unknown>"
        field_offset = int(annotation["field_offset"]) if annotation else state_offset
        key = (field_name, field_offset)
        group = groups.get(key)
        if group is None:
            group = {
                "field_name": field_name,
                "field_role": classify_field_role(field_name),
                "field_offset": field_offset,
                "field_size": int(annotation["field_size"]) if annotation else 1,
                "mismatch_bytes": 0,
                "first_global_offset": idx,
                "first_state_offset": state_offset,
                "first_state_index": state_index,
                "field_byte_offsets": [],
                "state_indices": [],
                "example_single_byte": single_byte,
                "example_split_byte": split_byte,
            }
            groups[key] = group
        group["mismatch_bytes"] = int(group["mismatch_bytes"]) + 1
        field_byte_offset = (
            int(annotation["field_byte_offset"]) if annotation else 0
        )
        if (
            field_byte_offset not in group["field_byte_offsets"]
            and len(group["field_byte_offsets"]) < 8
        ):
            group["field_byte_offsets"].append(field_byte_offset)
        if state_index not in group["state_indices"] and len(group["state_indices"]) < 8:
            group["state_indices"].append(state_index)

    ordered = sorted(groups.values(), key=lambda entry: int(entry["first_global_offset"]))
    role_summary: dict[str, dict[str, int]] = {}
    for entry in ordered:
        role = str(entry["field_role"])
        bucket = role_summary.setdefault(role, {"field_count": 0, "mismatch_bytes": 0})
        bucket["field_count"] += 1
        bucket["mismatch_bytes"] += int(entry["mismatch_bytes"])
    return len(ordered), ordered[:limit], ordered, role_summary


def first_field_with_role(
    mismatch_fields: list[dict[str, object]], *roles: str
) -> dict[str, object] | None:
    wanted = set(roles)
    for entry in mismatch_fields:
        if str(entry.get("field_role")) in wanted:
            return dict(entry)
    return None


def build_acceptance_candidates(
    *,
    match: bool,
    mismatch_count: int,
    role_summary: dict[str, dict[str, int]],
) -> dict[str, int | bool]:
    internal_bytes = int(role_summary.get("verilator_internal", {}).get("mismatch_bytes", 0))
    design_state_bytes = int(role_summary.get("design_state", {}).get("mismatch_bytes", 0))
    top_level_io_bytes = int(role_summary.get("top_level_io", {}).get("mismatch_bytes", 0))
    other_bytes = mismatch_count - internal_bytes - design_state_bytes - top_level_io_bytes
    return {
        "strict_match": match,
        "match_excluding_verilator_internal": mismatch_count == internal_bytes,
        "verilator_internal_mismatch_bytes": internal_bytes,
        "design_state_mismatch_bytes": design_state_bytes,
        "top_level_io_mismatch_bytes": top_level_io_bytes,
        "other_mismatch_bytes": other_bytes,
    }


def is_normalized_final_state_field(entry: dict[str, int | str]) -> bool:
    section = str(entry.get("section", ""))
    if section and section != "DESIGN SPECIFIC STATE":
        return False
    decl_type = str(entry.get("decl_type", ""))
    decl_type_without_comments = re.sub(r"/\*.*?\*/", "", decl_type)
    if "*" in decl_type_without_comments:
        return False
    excluded_type_markers = (
        "std::string",
        "VlQueue",
        "VlClassRef",
        "VlDelayScheduler",
        "VlTriggerVec",
    )
    if any(marker in decl_type for marker in excluded_type_markers):
        return False
    name = str(entry.get("name", ""))
    if name in VERILATOR_INTERNAL_FIELDS:
        return False
    return True


def normalized_final_state_fields(
    layout: list[dict[str, int | str]]
) -> list[dict[str, int | str]]:
    return [entry for entry in layout if is_normalized_final_state_field(entry)]


def _state_pair_plan(
    reference_len: int, candidate_len: int, storage_size: int
) -> dict[str, object]:
    if storage_size <= 0:
        return {
            "compatible": False,
            "reason": "storage_size_must_be_positive",
            "pairs": [],
            "comparison_mode": "invalid_storage_size",
            "reference_state_count": None,
            "candidate_state_count": None,
        }
    if reference_len % storage_size != 0 or candidate_len % storage_size != 0:
        return {
            "compatible": False,
            "reason": "state_dump_size_is_not_a_multiple_of_storage_size",
            "pairs": [],
            "comparison_mode": "incompatible_state_dump_sizes",
            "reference_state_count": None,
            "candidate_state_count": None,
        }
    reference_state_count = reference_len // storage_size
    candidate_state_count = candidate_len // storage_size
    if reference_state_count == candidate_state_count:
        pairs = [(idx, idx) for idx in range(reference_state_count)]
        comparison_mode = "corresponding_state_chunks"
    elif reference_state_count == 1:
        pairs = [(0, idx) for idx in range(candidate_state_count)]
        comparison_mode = "single_reference_state_against_candidate_chunks"
    elif candidate_state_count == 1:
        pairs = [(idx, 0) for idx in range(reference_state_count)]
        comparison_mode = "reference_chunks_against_single_candidate_state"
    else:
        return {
            "compatible": False,
            "reason": "reference_and_candidate_state_counts_are_incompatible",
            "pairs": [],
            "comparison_mode": "incompatible_state_counts",
            "reference_state_count": reference_state_count,
            "candidate_state_count": candidate_state_count,
        }
    return {
        "compatible": True,
        "reason": None,
        "pairs": pairs,
        "comparison_mode": comparison_mode,
        "reference_state_count": reference_state_count,
        "candidate_state_count": candidate_state_count,
    }


def build_normalized_final_state_policy_summary(
    reference: bytes,
    candidate: bytes,
    *,
    storage_size: int,
    layout: list[dict[str, int | str]],
    limit: int = 16,
) -> dict[str, object]:
    fields = normalized_final_state_fields(layout)
    included_byte_count = sum(int(entry["size"]) for entry in fields)
    summary: dict[str, object] = {
        "name": NORMALIZED_FINAL_STATE_POLICY_NAME,
        "acceptance_policy": ACCEPTANCE_POLICY_NORMALIZED_FINAL_STATE,
        "exclusions": list(NORMALIZED_FINAL_STATE_EXCLUSIONS),
        "included_member_count": len(fields),
        "included_byte_count": included_byte_count,
    }
    plan = _state_pair_plan(len(reference), len(candidate), storage_size)
    summary.update(
        {
            "comparison_mode": plan["comparison_mode"],
            "compatible": bool(plan["compatible"]),
            "reference_state_count": plan["reference_state_count"],
            "candidate_state_count": plan["candidate_state_count"],
        }
    )
    if not plan["compatible"]:
        summary.update(
            {
                "passed": False,
                "blocked_reason": plan["reason"],
                "mismatch_field_count": None,
                "mismatch_byte_count": None,
                "functional_non_internal_mismatch_field_count": None,
                "functional_non_internal_mismatch_byte_count": None,
                "max_functional_non_internal_mismatch_byte_count": None,
                "mismatch_role_summary": {},
                "mismatch_fields": [],
            }
        )
        return summary
    if not fields:
        summary.update(
            {
                "passed": False,
                "blocked_reason": "no_comparable_normalized_fields",
                "mismatch_field_count": 0,
                "mismatch_byte_count": 0,
                "functional_non_internal_mismatch_field_count": 0,
                "functional_non_internal_mismatch_byte_count": 0,
                "max_functional_non_internal_mismatch_byte_count": 0,
                "mismatch_role_summary": {},
                "mismatch_fields": [],
            }
        )
        return summary

    groups: dict[tuple[str, int], dict[str, object]] = {}
    role_summary: dict[str, dict[str, int]] = {}
    functional_fields: set[tuple[str, int]] = set()
    functional_bytes = 0
    per_candidate_functional_bytes: dict[int, int] = {}
    mismatching_candidate_states: set[int] = set()
    pairs = list(plan["pairs"])
    for reference_state_index, candidate_state_index in pairs:
        reference_base = int(reference_state_index) * storage_size
        candidate_base = int(candidate_state_index) * storage_size
        for field in fields:
            field_offset = int(field["offset"])
            field_size = int(field["size"])
            start_reference = reference_base + field_offset
            end_reference = start_reference + field_size
            start_candidate = candidate_base + field_offset
            end_candidate = start_candidate + field_size
            reference_slice = reference[start_reference:end_reference]
            candidate_slice = candidate[start_candidate:end_candidate]
            if reference_slice == candidate_slice:
                continue
            role = classify_field_role(str(field["name"]))
            mismatch_byte_offsets = [
                idx
                for idx, (reference_byte, candidate_byte) in enumerate(
                    zip(reference_slice, candidate_slice)
                )
                if reference_byte != candidate_byte
            ]
            mismatch_bytes = len(mismatch_byte_offsets) + abs(
                len(reference_slice) - len(candidate_slice)
            )
            if mismatch_bytes == 0:
                continue
            key = (str(field["name"]), field_offset)
            group = groups.get(key)
            if group is None:
                first_field_byte_offset = mismatch_byte_offsets[0] if mismatch_byte_offsets else 0
                group = {
                    "field_name": str(field["name"]),
                    "field_role": role,
                    "field_offset": field_offset,
                    "field_size": field_size,
                    "decl_type": str(field.get("decl_type", "")),
                    "mismatch_bytes": 0,
                    "first_reference_state_index": reference_state_index,
                    "first_candidate_state_index": candidate_state_index,
                    "first_field_byte_offset": first_field_byte_offset,
                    "reference_first_byte": (
                        reference_slice[first_field_byte_offset]
                        if first_field_byte_offset < len(reference_slice)
                        else None
                    ),
                    "candidate_first_byte": (
                        candidate_slice[first_field_byte_offset]
                        if first_field_byte_offset < len(candidate_slice)
                        else None
                    ),
                    "field_byte_offsets": [],
                    "reference_state_indices": [],
                    "candidate_state_indices": [],
                }
                groups[key] = group
            group["mismatch_bytes"] = int(group["mismatch_bytes"]) + mismatch_bytes
            for field_byte_offset in mismatch_byte_offsets[:8]:
                if field_byte_offset not in group["field_byte_offsets"]:
                    group["field_byte_offsets"].append(field_byte_offset)
            if reference_state_index not in group["reference_state_indices"]:
                group["reference_state_indices"].append(reference_state_index)
            if candidate_state_index not in group["candidate_state_indices"]:
                group["candidate_state_indices"].append(candidate_state_index)
            role_bucket = role_summary.setdefault(role, {"field_count": 0, "mismatch_bytes": 0})
            role_bucket["mismatch_bytes"] += mismatch_bytes
            mismatching_candidate_states.add(int(candidate_state_index))
            if role != "verilator_internal":
                functional_fields.add(key)
                functional_bytes += mismatch_bytes
                per_candidate_functional_bytes[int(candidate_state_index)] = (
                    per_candidate_functional_bytes.get(int(candidate_state_index), 0)
                    + mismatch_bytes
                )

    for group in groups.values():
        role = str(group["field_role"])
        role_summary.setdefault(role, {"field_count": 0, "mismatch_bytes": 0})
        role_summary[role]["field_count"] += 1

    ordered = sorted(
        groups.values(),
        key=lambda entry: (
            int(entry["first_candidate_state_index"]),
            int(entry["field_offset"]),
            str(entry["field_name"]),
        ),
    )
    max_functional_bytes = max(per_candidate_functional_bytes.values(), default=0)
    summary.update(
        {
            "passed": functional_bytes == 0,
            "blocked_reason": None,
            "mismatching_candidate_state_count": len(mismatching_candidate_states),
            "mismatch_field_count": len(ordered),
            "mismatch_byte_count": sum(int(entry["mismatch_bytes"]) for entry in ordered),
            "functional_non_internal_mismatch_field_count": len(functional_fields),
            "functional_non_internal_mismatch_byte_count": functional_bytes,
            "max_functional_non_internal_mismatch_byte_count": max_functional_bytes,
            "mismatch_role_summary": role_summary,
            "mismatch_fields": ordered[:limit],
        }
    )
    return summary


def derive_strict_output_field_names(gate: dict) -> list[str]:
    contract = gate.get("coverage_output_contract") or {}
    entries = contract.get("strict_output_words") or []
    words: list[str] = []
    for entry in entries:
        prefix = str(entry["prefix"])
        count = int(entry["count"])
        for idx in range(count):
            words.append(f"{prefix}{idx}_o")
    return words


def validate_coverage_output_manifest(
    manifest: dict,
    *,
    expected_prefix: str = COVERAGE_OUTPUT_REQUIRED_PREFIX,
    expected_count: int = COVERAGE_OUTPUT_REQUIRED_COUNT,
) -> dict:
    coverage_domain = manifest.get("coverage_domain")
    domain_ok = coverage_domain == COVERAGE_OUTPUT_REQUIRED_DOMAIN
    regions = manifest.get("regions") or []
    words: list[str] = []
    for region in regions:
        for word in region.get("words") or []:
            words.append(str(word))
    expected = {
        f"{expected_prefix}{idx}_o"
        for idx in range(expected_count)
    }
    actual = set(words)
    duplicates = sorted({word for word in words if words.count(word) > 1})
    missing_required = sorted(expected - actual)
    extra_unexpected = sorted(actual - expected)
    return {
        "coverage_domain": coverage_domain,
        "coverage_domain_ok": domain_ok,
        "region_count": len(regions),
        "covered_word_count": len(words),
        "covered_unique_word_count": len(actual),
        "missing_required_words": missing_required,
        "extra_unexpected_words": extra_unexpected,
        "duplicate_words": duplicates,
        "valid": (
            domain_ok
            and len(words) == expected_count
            and not missing_required
            and not extra_unexpected
            and not duplicates
        ),
    }


def select_coverage_output_target(gate: dict, target_name: str) -> dict:
    target_scope = gate.get("target_scope") or []
    matches = [entry for entry in target_scope if entry.get("target") == target_name]
    if not matches:
        names = [str(entry.get("target")) for entry in target_scope]
        raise ValueError(
            f"target {target_name!r} not in coverage gate target_scope; available: {names}"
        )
    return dict(matches[0])


def validate_coverage_output_gate(gate: dict) -> None:
    if gate.get("coverage_domain") != COVERAGE_OUTPUT_REQUIRED_DOMAIN:
        raise ValueError(
            f"coverage gate coverage_domain must be {COVERAGE_OUTPUT_REQUIRED_DOMAIN!r}, "
            f"got {gate.get('coverage_domain')!r}"
        )
    if not (gate.get("target_scope") or []):
        raise ValueError("coverage gate target_scope must be non-empty")
    contract = gate.get("coverage_output_contract") or {}
    entries = contract.get("strict_output_words") or []
    if not entries:
        raise ValueError(
            "coverage gate coverage_output_contract.strict_output_words must be non-empty"
        )


def build_coverage_output_policy_summary(
    reference: bytes,
    candidate: bytes,
    *,
    storage_size: int,
    layout: list[dict[str, int | str]],
    gate: dict,
    target_entry: dict,
    manifest: dict | None,
    manifest_path: str | None = None,
    limit: int = 16,
) -> dict[str, object]:
    contract = gate.get("coverage_output_contract") or {}
    strict_words = derive_strict_output_field_names(gate)
    summary: dict[str, object] = {
        "name": COVERAGE_OUTPUT_POLICY_NAME,
        "acceptance_policy": ACCEPTANCE_POLICY_COVERAGE_OUTPUT,
        "gate": gate.get("gate"),
        "coverage_domain": gate.get("coverage_domain"),
        "target": target_entry.get("target"),
        "manifest_path": manifest_path,
        "strict_output_word_prefixes": [
            {"prefix": str(entry["prefix"]), "count": int(entry["count"])}
            for entry in (contract.get("strict_output_words") or [])
        ],
        "expected_total_words_per_state": contract.get("total_words_per_state"),
        "expected_total_bytes_per_state": contract.get("total_bytes_per_state"),
        "strict_output_word_count": len(strict_words),
        "missing_fields": [],
        "compared_state_pair_count": 0,
        "compared_word_count": 0,
        "compared_byte_count": 0,
        "mismatches": [],
        "mismatch_count": 0,
    }

    if manifest is None:
        summary["manifest_validation"] = None
        summary["passed"] = False
        summary["blocked_reason"] = "coverage_manifest_not_loaded"
        return summary
    manifest_region_words = contract.get("manifest_region_words") or {}
    manifest_validation = validate_coverage_output_manifest(
        manifest,
        expected_prefix=str(
            manifest_region_words.get("prefix", COVERAGE_OUTPUT_REQUIRED_PREFIX)
        ),
        expected_count=int(
            manifest_region_words.get("count", COVERAGE_OUTPUT_REQUIRED_COUNT)
        ),
    )
    summary["manifest_validation"] = manifest_validation
    if not manifest_validation["valid"]:
        summary["passed"] = False
        summary["blocked_reason"] = "coverage_manifest_real_toggle_word_coverage_invalid"
        return summary

    layout_by_name = {str(entry["name"]): entry for entry in layout}
    missing_fields = [name for name in strict_words if name not in layout_by_name]
    if missing_fields:
        summary["missing_fields"] = missing_fields
        summary["passed"] = False
        summary["blocked_reason"] = "missing_coverage_output_fields"
        return summary

    plan = _state_pair_plan(len(reference), len(candidate), storage_size)
    summary["comparison_mode"] = plan["comparison_mode"]
    summary["compatible"] = bool(plan["compatible"])
    summary["reference_state_count"] = plan["reference_state_count"]
    summary["candidate_state_count"] = plan["candidate_state_count"]
    if not plan["compatible"]:
        summary["passed"] = False
        summary["blocked_reason"] = plan["reason"]
        return summary

    pairs = list(plan["pairs"])
    mismatches: list[dict[str, object]] = []
    compared_byte_count = 0
    compared_word_count = 0
    for reference_state_index, candidate_state_index in pairs:
        reference_base = int(reference_state_index) * storage_size
        candidate_base = int(candidate_state_index) * storage_size
        for word_name in strict_words:
            entry = layout_by_name[word_name]
            offset = int(entry["offset"])
            size = int(entry["size"])
            reference_slice = reference[reference_base + offset : reference_base + offset + size]
            candidate_slice = candidate[candidate_base + offset : candidate_base + offset + size]
            compared_byte_count += size
            compared_word_count += 1
            if reference_slice == candidate_slice:
                continue
            mismatch_byte_offsets = [
                idx
                for idx, (reference_byte, candidate_byte) in enumerate(
                    zip(reference_slice, candidate_slice)
                )
                if reference_byte != candidate_byte
            ]
            first_field_byte_offset = mismatch_byte_offsets[0] if mismatch_byte_offsets else 0
            mismatches.append(
                {
                    "field_name": word_name,
                    "field_offset": offset,
                    "field_size": size,
                    "reference_state_index": int(reference_state_index),
                    "candidate_state_index": int(candidate_state_index),
                    "mismatch_bytes": len(mismatch_byte_offsets)
                    + abs(len(reference_slice) - len(candidate_slice)),
                    "first_field_byte_offset": first_field_byte_offset,
                    "reference_first_byte": (
                        reference_slice[first_field_byte_offset]
                        if first_field_byte_offset < len(reference_slice)
                        else None
                    ),
                    "candidate_first_byte": (
                        candidate_slice[first_field_byte_offset]
                        if first_field_byte_offset < len(candidate_slice)
                        else None
                    ),
                }
            )
    summary["compared_state_pair_count"] = len(pairs)
    summary["compared_word_count"] = compared_word_count
    summary["compared_byte_count"] = compared_byte_count
    summary["mismatches"] = mismatches[:limit]
    summary["mismatch_count"] = len(mismatches)
    summary["passed"] = not mismatches
    summary["blocked_reason"] = None
    return summary


def has_only_phase_b_residual_fields(summary: dict[str, object]) -> bool:
    mismatch_fields = list(summary.get("mismatch_fields") or [])
    if not mismatch_fields:
        return True
    allowed = PHASE_B_ALLOWED_INTERNAL_FIELDS
    for entry in mismatch_fields:
        if str(entry.get("field_role")) != "verilator_internal":
            return False
        if str(entry.get("field_name")) not in allowed:
            return False
    return True


def build_acceptance_policies(summary: dict[str, object]) -> dict[str, dict[str, object]]:
    candidates = dict(summary.get("acceptance_candidates") or {})
    strict_passed = bool(candidates.get("strict_match", summary.get("match", False)))
    ignore_internal_passed = bool(candidates.get("match_excluding_verilator_internal", False))
    phase_b_endpoint_passed = ignore_internal_passed and has_only_phase_b_residual_fields(summary)
    normalized_summary = dict(summary.get("normalized_final_state_policy") or {})
    normalized_passed = bool(normalized_summary.get("passed", False))
    coverage_output_summary = dict(summary.get("coverage_output_policy") or {})
    coverage_output_passed = bool(coverage_output_summary.get("passed", False))
    return {
        ACCEPTANCE_POLICY_STRICT: {
            "passed": strict_passed,
            "description": "Final raw state bytes must match exactly.",
            "diagnostic_only_prefixes": True,
        },
        ACCEPTANCE_POLICY_IGNORE_INTERNAL: {
            "passed": ignore_internal_passed,
            "description": (
                "Final design_state/top_level_io/other bytes must match; "
                "verilator_internal bytes may differ."
            ),
            "diagnostic_only_prefixes": True,
        },
        ACCEPTANCE_POLICY_PHASE_B_ENDPOINT: {
            "passed": phase_b_endpoint_passed,
            "description": (
                "Final design_state/top_level_io/other bytes must match, and any residual "
                "verilator_internal mismatch must be limited to the known convergence "
                "bookkeeping fields (__VicoPhaseResult, __VactIterCount, "
                "__VinactIterCount, __VicoTriggered)."
            ),
            "diagnostic_only_prefixes": True,
        },
        ACCEPTANCE_POLICY_NORMALIZED_FINAL_STATE: {
            "passed": normalized_passed,
            "description": (
                "Final comparable primitive DESIGN SPECIFIC STATE fields must match for "
                "design_state/top_level_io/other roles. CELLS pointers, parameters, "
                "Verilator internal variables, and Verilator-internal primitive "
                "temporaries/trigger history are excluded from the claim."
            ),
            "diagnostic_only_prefixes": True,
            "comparison_policy": {
                "name": normalized_summary.get("name", NORMALIZED_FINAL_STATE_POLICY_NAME),
                "included_member_count": normalized_summary.get("included_member_count"),
                "included_byte_count": normalized_summary.get("included_byte_count"),
                "exclusions": normalized_summary.get(
                    "exclusions", list(NORMALIZED_FINAL_STATE_EXCLUSIONS)
                ),
            },
        },
        ACCEPTANCE_POLICY_COVERAGE_OUTPUT: {
            "passed": coverage_output_passed,
            "description": (
                "Coverage-output words derived from a coverage-output gate must match "
                "byte-for-byte for compatible CPU/GPU state pairs. This policy is separate "
                "from normalized_final_state_equivalence and only inspects the strict "
                "output fields named by the gate."
            ),
            "diagnostic_only_prefixes": True,
            "comparison_policy": {
                "name": coverage_output_summary.get("name", COVERAGE_OUTPUT_POLICY_NAME),
                "gate": coverage_output_summary.get("gate"),
                "target": coverage_output_summary.get("target"),
                "coverage_domain": coverage_output_summary.get("coverage_domain"),
                "strict_output_word_count": coverage_output_summary.get(
                    "strict_output_word_count"
                ),
                "compared_word_count": coverage_output_summary.get("compared_word_count"),
                "compared_byte_count": coverage_output_summary.get("compared_byte_count"),
                "missing_fields": coverage_output_summary.get("missing_fields") or [],
                "blocked_reason": coverage_output_summary.get("blocked_reason"),
            },
        },
    }


def select_acceptance_policy(
    summary: dict[str, object], policy_name: str
) -> dict[str, object]:
    policies = dict(summary.get("acceptance_policies") or {})
    selected = dict(policies[policy_name])
    selected["name"] = policy_name
    return selected


def build_phase_delta_summary(summary: dict[str, object]) -> dict[str, object]:
    payload: dict[str, object] = {
        "mismatch_count": int(summary.get("mismatch_count", 0)),
        "mismatch_field_count": int(summary.get("mismatch_field_count", 0)),
        "mismatch_role_summary": dict(summary.get("mismatch_role_summary") or {}),
        "acceptance_candidates": dict(summary.get("acceptance_candidates") or {}),
        "mismatch_fields": [dict(entry) for entry in summary.get("mismatch_fields", [])],
    }
    for key in ("first_mismatch", "first_non_internal_mismatch", "first_design_state_mismatch"):
        value = summary.get(key)
        if value is not None:
            payload[key] = dict(value)
    return payload


def compare_state_dumps(
    single_dump: Path,
    split_dump: Path,
    storage_size: int,
    *,
    layout: list[dict[str, int | str]] | None = None,
) -> dict:
    single = single_dump.read_bytes()
    split = split_dump.read_bytes()
    first_mismatch = None
    mismatch_count = 0
    compare_len = min(len(single), len(split))
    for idx in range(compare_len):
        if single[idx] != split[idx]:
            mismatch_count += 1
            if first_mismatch is None:
                first_mismatch = idx
    mismatch_count += abs(len(single) - len(split))

    payload = {
        "match": mismatch_count == 0 and len(single) == len(split),
        "single_bytes": len(single),
        "split_bytes": len(split),
        "mismatch_count": mismatch_count,
        "storage_size": storage_size,
        "single_sha256": sha256_file(single_dump),
        "split_sha256": sha256_file(split_dump),
    }
    if first_mismatch is not None:
        payload["first_mismatch"] = {
            "global_offset": first_mismatch,
            "state_index": first_mismatch // storage_size if storage_size > 0 else None,
            "state_offset": first_mismatch % storage_size if storage_size > 0 else None,
            "single_byte": single[first_mismatch],
            "split_byte": split[first_mismatch],
        }
        if layout:
            annotation = annotate_state_offset(layout, payload["first_mismatch"]["state_offset"])
            if annotation is not None:
                payload["first_mismatch"].update(annotation)
    if layout:
        field_count, mismatch_fields, all_mismatch_fields, role_summary = summarize_mismatch_fields(
            single,
            split,
            storage_size=storage_size,
            layout=layout,
        )
        payload["mismatch_field_count"] = field_count
        payload["mismatch_fields"] = mismatch_fields
        payload["mismatch_role_summary"] = role_summary
        payload["acceptance_candidates"] = build_acceptance_candidates(
            match=payload["match"],
            mismatch_count=mismatch_count,
            role_summary=role_summary,
        )
        payload["normalized_final_state_policy"] = build_normalized_final_state_policy_summary(
            single,
            split,
            storage_size=storage_size,
            layout=layout,
        )
        payload["acceptance_candidates"][
            "normalized_final_state_equivalence"
        ] = bool(payload["normalized_final_state_policy"]["passed"])
        first_non_internal = first_field_with_role(
            all_mismatch_fields, "design_state", "top_level_io", "other"
        )
        if first_non_internal is not None:
            payload["first_non_internal_mismatch"] = first_non_internal
        first_design_state = first_field_with_role(all_mismatch_fields, "design_state")
        if first_design_state is not None:
            payload["first_design_state_mismatch"] = first_design_state
    return payload


def read_storage_size_from_meta(mdir: Path) -> int:
    meta_path = mdir / "vl_batch_gpu.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    storage_size = int(meta["storage_size"])
    if storage_size <= 0:
        raise ValueError(f"invalid storage_size in {meta_path}: {storage_size}")
    return storage_size


def compare_dump_files(
    *,
    mdir: Path,
    display_mdir: Path,
    reference_dump: Path,
    candidate_dump: Path,
    storage_size: int | None,
    acceptance_policy: str,
    reference_label: str,
    candidate_label: str,
    coverage_output_gate_path: Path | None = None,
    coverage_output_target: str | None = None,
) -> dict[str, object]:
    effective_storage_size = (
        storage_size if storage_size is not None else read_storage_size_from_meta(mdir)
    )
    layout = probe_root_layout(mdir)
    summary = compare_state_dumps(
        reference_dump,
        candidate_dump,
        effective_storage_size,
        layout=layout,
    )
    if coverage_output_gate_path is not None:
        gate_path = coverage_output_gate_path.resolve()
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        validate_coverage_output_gate(gate)
        target_scope = gate.get("target_scope") or []
        if coverage_output_target is None:
            if len(target_scope) != 1:
                names = [str(entry.get("target")) for entry in target_scope]
                raise SystemExit(
                    "--coverage-output-target is required when the gate has multiple "
                    f"target_scope entries; available: {names}"
                )
            target_entry = dict(target_scope[0])
        else:
            target_entry = select_coverage_output_target(gate, coverage_output_target)
        manifest_relative = target_entry.get("coverage_manifest")
        manifest_path: Path | None = None
        manifest: dict | None = None
        if manifest_relative:
            manifest_candidate = Path(str(manifest_relative))
            candidate_paths = [
                manifest_candidate,
                REPO_ROOT / manifest_candidate,
                gate_path.parent / manifest_candidate,
            ]
            for candidate in candidate_paths:
                if candidate.exists():
                    manifest_path = candidate
                    break
            if manifest_path is not None:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        summary["coverage_output_policy"] = build_coverage_output_policy_summary(
            reference_dump.read_bytes(),
            candidate_dump.read_bytes(),
            storage_size=effective_storage_size,
            layout=layout,
            gate=gate,
            target_entry=target_entry,
            manifest=manifest,
            manifest_path=str(manifest_path) if manifest_path is not None else (
                str(manifest_relative) if manifest_relative else None
            ),
        )
    summary["acceptance_policies"] = build_acceptance_policies(summary)
    summary["selected_acceptance_policy"] = select_acceptance_policy(summary, acceptance_policy)
    summary.update(
        {
            "schema_version": 2,
            "mode": "compare_existing_state_dumps",
            "mdir": str(display_mdir),
            "reference_label": reference_label,
            "candidate_label": candidate_label,
            "reference_dump": str(reference_dump),
            "candidate_dump": str(candidate_dump),
            "root_layout_member_count": len(layout),
        }
    )
    return summary


def run_hybrid(
    *,
    mdir: Path | None,
    cubin: Path | None,
    storage_size: int,
    nstates: int,
    steps: int,
    block_size: int,
    dump_state: Path,
    patches: list[str],
    kernels: list[str] | None = None,
) -> None:
    cmd = [sys.executable, str(RUN_VL_HYBRID)]
    if mdir is not None:
        cmd.extend(["--mdir", str(mdir)])
    else:
        assert cubin is not None
        cmd.extend(["--cubin", str(cubin), "--storage-size", str(storage_size)])
    cmd.extend(
        [
            "--nstates",
            str(nstates),
            "--steps",
            str(steps),
            "--block-size",
            str(block_size),
            "--dump-state",
            str(dump_state),
        ]
    )
    if kernels is not None:
        cmd.extend(["--kernels", ",".join(kernels)])
    for patch in patches:
        cmd.extend(["--patch", patch])
    subprocess.run(cmd, check=True)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Compare single-kernel vs phase-split stock-Verilator hybrid outputs"
    )
    p.add_argument("mdir", type=Path, help="Verilator --cc output directory (contains *_classes.mk)")
    p.add_argument("--sm", default="sm_89", help="GPU arch (default: sm_89)")
    p.add_argument("--clang-O", dest="clang_opt", default="O1", help="clang optimization for .ll")
    p.add_argument("--force-build", action="store_true", help="Force both cubin rebuilds")
    p.add_argument("--nstates", type=int, default=64, help="Parallel states for each run")
    p.add_argument("--steps", type=int, default=1, help="Launch steps for each run")
    p.add_argument("--block-size", type=int, default=256, help="CUDA block size")
    p.add_argument(
        "--patch",
        action="append",
        default=[],
        metavar="GLOBAL_OFF:BYTE",
        help="Per-step HtoD patch forwarded to run_vl_hybrid.py",
    )
    p.add_argument("--json-out", type=Path, default=None, help="Optional JSON summary path")
    p.add_argument(
        "--compare-dumps",
        nargs=2,
        type=Path,
        metavar=("REFERENCE_DUMP", "CANDIDATE_DUMP"),
        help=(
            "Compare two existing state dumps using this mdir layout instead of rebuilding "
            "and running single/split GPU modes"
        ),
    )
    p.add_argument(
        "--storage-size",
        type=int,
        default=None,
        help="Storage bytes per state for --compare-dumps; defaults to mdir/vl_batch_gpu.meta.json",
    )
    p.add_argument(
        "--reference-label",
        default="reference",
        help="Label recorded for the first --compare-dumps input",
    )
    p.add_argument(
        "--candidate-label",
        default="candidate",
        help="Label recorded for the second --compare-dumps input",
    )
    p.add_argument(
        "--dump-dir",
        type=Path,
        default=None,
        help="Optional directory to keep single/split raw state dumps for mismatch debugging",
    )
    p.add_argument(
        "--acceptance-policy",
        default=ACCEPTANCE_POLICY_STRICT,
        choices=[
            ACCEPTANCE_POLICY_STRICT,
            ACCEPTANCE_POLICY_IGNORE_INTERNAL,
            ACCEPTANCE_POLICY_PHASE_B_ENDPOINT,
            ACCEPTANCE_POLICY_NORMALIZED_FINAL_STATE,
            ACCEPTANCE_POLICY_COVERAGE_OUTPUT,
        ],
        help="Pass/fail policy for the tool exit code (default: strict_final_state)",
    )
    p.add_argument(
        "--coverage-output-gate",
        type=Path,
        default=None,
        help=(
            "Path to a coverage-output equivalence gate JSON; required for "
            "--acceptance-policy coverage_output_equivalence. The gate is validated "
            "and its strict_output_words are compared field-by-field between the two "
            "--compare-dumps inputs using the probed root layout."
        ),
    )
    p.add_argument(
        "--coverage-output-target",
        default=None,
        help=(
            "Name of the target_scope entry in the coverage-output gate to use; "
            "required when the gate exposes more than one target."
        ),
    )
    args = p.parse_args()

    mdir = args.mdir.resolve()

    if args.compare_dumps is not None:
        reference_dump, candidate_dump = args.compare_dumps
        if (
            args.acceptance_policy == ACCEPTANCE_POLICY_COVERAGE_OUTPUT
            and args.coverage_output_gate is None
        ):
            raise SystemExit(
                "--acceptance-policy coverage_output_equivalence requires "
                "--coverage-output-gate PATH"
            )
        summary = compare_dump_files(
            mdir=mdir,
            display_mdir=args.mdir,
            reference_dump=reference_dump,
            candidate_dump=candidate_dump,
            storage_size=args.storage_size,
            acceptance_policy=args.acceptance_policy,
            reference_label=args.reference_label,
            candidate_label=args.candidate_label,
            coverage_output_gate_path=args.coverage_output_gate,
            coverage_output_target=args.coverage_output_target,
        )
        if args.json_out is not None:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            print(f"wrote: {args.json_out}")
        print(json.dumps(summary, indent=2))
        return 0 if summary["selected_acceptance_policy"]["passed"] else 2

    single_cubin = mdir / "vl_batch_gpu_single.cubin"
    split_cubin = mdir / "vl_batch_gpu_split.cubin"

    dump_ctx = (
        nullcontext(args.dump_dir.resolve())
        if args.dump_dir is not None
        else tempfile.TemporaryDirectory(prefix="vl_hybrid_compare_")
    )
    with dump_ctx as tmp:
        tmpdir = Path(tmp)
        tmpdir.mkdir(parents=True, exist_ok=True)
        single_dump = tmpdir / "single_state.bin"
        split_dump = tmpdir / "split_state.bin"
        layout = probe_root_layout(mdir)

        single_path, storage_size = build_vl_gpu(
            mdir,
            sm=args.sm,
            out_cubin=single_cubin,
            force=args.force_build,
            clang_opt=args.clang_opt,
            kernel_split_phases=False,
        )
        run_hybrid(
            mdir=None,
            cubin=single_path,
            storage_size=storage_size,
            nstates=args.nstates,
            steps=args.steps,
            block_size=args.block_size,
            dump_state=single_dump,
            patches=args.patch,
        )

        split_path, split_storage_size = build_vl_gpu(
            mdir,
            sm=args.sm,
            out_cubin=split_cubin,
            force=args.force_build,
            clang_opt=args.clang_opt,
            kernel_split_phases=True,
        )
        if split_storage_size != storage_size:
            raise RuntimeError(
                f"storage_size mismatch between single ({storage_size}) and split ({split_storage_size})"
            )
        run_hybrid(
            mdir=mdir,
            cubin=None,
            storage_size=storage_size,
            nstates=args.nstates,
            steps=args.steps,
            block_size=args.block_size,
            dump_state=split_dump,
            patches=args.patch,
        )

        summary = compare_state_dumps(single_dump, split_dump, storage_size, layout=layout)
        split_meta = json.loads((mdir / "vl_batch_gpu.meta.json").read_text(encoding="utf-8"))
        launch_sequence = list(split_meta.get("launch_sequence") or [])
        if launch_sequence:
            phase_debug = []
            prev_dump = None
            phase_localization = {
                "first_divergent_prefix_index": None,
                "first_divergent_kernels": None,
                "first_non_internal_prefix_index": None,
                "first_non_internal_kernels": None,
                "first_non_internal_mismatch": None,
                "first_design_state_prefix_index": None,
                "first_design_state_kernels": None,
                "first_design_state_mismatch": None,
                "first_delta_prefix_index": None,
                "first_delta_kernels": None,
                "first_delta_fields": None,
                "first_non_internal_delta_prefix_index": None,
                "first_non_internal_delta_kernels": None,
                "first_non_internal_delta_mismatch": None,
                "first_design_state_delta_prefix_index": None,
                "first_design_state_delta_kernels": None,
                "first_design_state_delta_mismatch": None,
                "per_prefix_mismatch_counts": [],
                "per_prefix_delta_counts": [],
            }
            for idx in range(len(launch_sequence)):
                kernels = launch_sequence[: idx + 1]
                prefix_dump = tmpdir / f"split_prefix_{idx + 1}.bin"
                run_hybrid(
                    mdir=None,
                    cubin=split_path,
                    storage_size=storage_size,
                    nstates=args.nstates,
                    steps=args.steps,
                    block_size=args.block_size,
                    dump_state=prefix_dump,
                    patches=args.patch,
                    kernels=kernels,
                )
                prefix_summary = compare_state_dumps(
                    single_dump,
                    prefix_dump,
                    storage_size,
                    layout=layout,
                )
                entry = {
                    "prefix_index": idx + 1,
                    "kernels": kernels,
                    "vs_single_final": prefix_summary,
                    "dump": str(prefix_dump),
                }
                phase_localization["per_prefix_mismatch_counts"].append(prefix_summary["mismatch_count"])
                if (
                    phase_localization["first_divergent_prefix_index"] is None
                    and prefix_summary["mismatch_count"] > 0
                ):
                    phase_localization["first_divergent_prefix_index"] = idx + 1
                    phase_localization["first_divergent_kernels"] = list(kernels)
                    phase_localization["first_divergent_fields"] = list(
                        prefix_summary.get("mismatch_fields", [])
                    )
                if (
                    phase_localization["first_non_internal_prefix_index"] is None
                    and prefix_summary.get("first_non_internal_mismatch") is not None
                ):
                    phase_localization["first_non_internal_prefix_index"] = idx + 1
                    phase_localization["first_non_internal_kernels"] = list(kernels)
                    phase_localization["first_non_internal_mismatch"] = dict(
                        prefix_summary["first_non_internal_mismatch"]
                    )
                if (
                    phase_localization["first_design_state_prefix_index"] is None
                    and prefix_summary.get("first_design_state_mismatch") is not None
                ):
                    phase_localization["first_design_state_prefix_index"] = idx + 1
                    phase_localization["first_design_state_kernels"] = list(kernels)
                    phase_localization["first_design_state_mismatch"] = dict(
                        prefix_summary["first_design_state_mismatch"]
                    )
                if prev_dump is not None:
                    prev_summary = compare_state_dumps(
                        prev_dump,
                        prefix_dump,
                        storage_size,
                        layout=layout,
                    )
                    entry["vs_previous_prefix"] = prev_summary
                    entry["delta_from_previous_prefix"] = build_phase_delta_summary(prev_summary)
                    phase_localization["per_prefix_delta_counts"].append(prev_summary["mismatch_count"])
                    if (
                        phase_localization["first_delta_prefix_index"] is None
                        and prev_summary["mismatch_count"] > 0
                    ):
                        phase_localization["first_delta_prefix_index"] = idx + 1
                        phase_localization["first_delta_kernels"] = list(kernels)
                        phase_localization["first_delta_fields"] = list(
                            prev_summary.get("mismatch_fields", [])
                        )
                    if (
                        phase_localization["first_non_internal_delta_prefix_index"] is None
                        and prev_summary.get("first_non_internal_mismatch") is not None
                    ):
                        phase_localization["first_non_internal_delta_prefix_index"] = idx + 1
                        phase_localization["first_non_internal_delta_kernels"] = list(kernels)
                        phase_localization["first_non_internal_delta_mismatch"] = dict(
                            prev_summary["first_non_internal_mismatch"]
                        )
                    if (
                        phase_localization["first_design_state_delta_prefix_index"] is None
                        and prev_summary.get("first_design_state_mismatch") is not None
                    ):
                        phase_localization["first_design_state_delta_prefix_index"] = idx + 1
                        phase_localization["first_design_state_delta_kernels"] = list(kernels)
                        phase_localization["first_design_state_delta_mismatch"] = dict(
                            prev_summary["first_design_state_mismatch"]
                        )
                else:
                    phase_localization["per_prefix_delta_counts"].append(None)
                phase_debug.append(entry)
                prev_dump = prefix_dump
            summary["phase_debug"] = phase_debug
            summary["phase_localization"] = phase_localization
        summary["phase_localization_note"] = (
            "Prefix comparisons are diagnostic against single final state, "
            "not phase-aligned acceptance gates; use delta_from_previous_prefix "
            "and first_*_delta_* keys to isolate what each added kernel changed."
        )
        summary["acceptance_policies"] = build_acceptance_policies(summary)
        summary["selected_acceptance_policy"] = select_acceptance_policy(
            summary, args.acceptance_policy
        )
        summary.update(
            {
                "schema_version": 2,
                "mdir": str(mdir),
                "single_cubin": str(single_path),
                "split_cubin": str(split_path),
                "launch_sequence": launch_sequence,
                "root_layout_member_count": len(layout),
                "nstates": args.nstates,
                "steps": args.steps,
                "block_size": args.block_size,
                "patches": list(args.patch),
                "single_dump": str(single_dump),
                "split_dump": str(split_dump),
            }
        )

        if args.json_out is not None:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            print(f"wrote: {args.json_out}")

        print(json.dumps(summary, indent=2))
        return 0 if summary["selected_acceptance_policy"]["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
