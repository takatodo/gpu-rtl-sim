"""Root-layout probing and mismatch annotation helpers."""

from __future__ import annotations

from compare_vl_hybrid_root_layout import (
    VERILATOR_INTERNAL_FIELDS,
    classify_field_role,
    extract_root_member_declarations,
    extract_root_member_names,
    probe_root_layout,
    sha256_file,
)


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
        field_byte_offset = int(annotation["field_byte_offset"]) if annotation else 0
        if field_byte_offset not in group["field_byte_offsets"] and len(group["field_byte_offsets"]) < 8:
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
