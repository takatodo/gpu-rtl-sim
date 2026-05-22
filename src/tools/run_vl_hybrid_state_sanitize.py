from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

import compare_vl_hybrid_modes as cmp
from run_vl_hybrid_state_fields import (
    sanitize_host_only_internals as _sanitize_host_only_internals,
    sanitize_host_only_internals_at_root_offset as _sanitize_host_only_internals_at_root_offset,
)

_UNSAFE_SYMS_GEP_RE = re.compile(
    r"getelementptr\s+inbounds\s+%class\.[^,\n]*__Syms[^,\n]*,"
)


def _syms_state_is_covered_by_meta(meta: dict[str, object] | None) -> bool:
    if not isinstance(meta, dict):
        return False
    hierarchy_state = meta.get("hierarchy_state")
    if not isinstance(hierarchy_state, dict):
        return False
    if (
        hierarchy_state.get("unsafe_syms_gep_count") == 0
        and hierarchy_state.get("prelaunch_rejection_required") is False
    ):
        return True
    return (
        hierarchy_state.get("state_image_kind") == "verilator_syms_image"
        and hierarchy_state.get("unsafe_syms_gep_covered_by_state_image") is True
        and hierarchy_state.get("prelaunch_rejection_required") is False
    )


def _root_offset_in_state_from_meta(meta: dict[str, object] | None) -> int:
    if not _syms_state_is_covered_by_meta(meta):
        return 0
    hierarchy_state = meta.get("hierarchy_state") if isinstance(meta, dict) else None
    if not isinstance(hierarchy_state, dict):
        return 0
    if hierarchy_state.get("state_image_kind") != "verilator_syms_image":
        return 0
    raw_offset = hierarchy_state.get("root_offset_in_state")
    if raw_offset is None:
        raw_offset = hierarchy_state.get("root_offset_in_syms")
    try:
        offset = int(raw_offset)
    except (TypeError, ValueError):
        return 0
    return offset if offset > 0 else 0


def _prepare_sanitized_init_state(
    *, mdir: Path, init_state: Path
) -> tuple[Path, list[dict[str, int]]] | None:
    layout = cmp.probe_root_layout(mdir)
    if not layout:
        return None
    meta_path = mdir / "vl_batch_gpu.meta.json"
    meta = None
    storage_size = None
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            storage_size = int(meta["storage_size"])
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            meta = None
            storage_size = None
    root_offset = _root_offset_in_state_from_meta(meta)
    blob = init_state.read_bytes()
    if storage_size is None or storage_size <= 0 or len(blob) <= storage_size:
        sanitized_blob, applied = _sanitize_host_only_internals_at_root_offset(
            blob, layout, root_offset=root_offset
        )
    elif len(blob) % storage_size == 0:
        chunk_count = len(blob) // storage_size
        sanitized_parts: list[bytes] = []
        applied = []
        for state_idx in range(chunk_count):
            base = state_idx * storage_size
            part, part_applied = _sanitize_host_only_internals_at_root_offset(
                blob[base : base + storage_size], layout, root_offset=root_offset
            )
            sanitized_parts.append(part)
            for entry in part_applied:
                applied.append(
                    {
                        "field_name": str(entry["field_name"]),
                        "offset": int(entry["offset"]) + base,
                        "size": int(entry["size"]),
                        "sanitized_start": int(entry["sanitized_start"]) + base,
                        "sanitized_end": int(entry["sanitized_end"]) + base,
                        "preserved_prefix_bytes": int(entry["preserved_prefix_bytes"]),
                        "state_index": state_idx,
                    }
                )
        sanitized_blob = b"".join(sanitized_parts)
    else:
        sanitized_blob, applied = _sanitize_host_only_internals(blob, layout)
    if not applied:
        return None
    fd, tmp_path = tempfile.mkstemp(prefix="run_vl_hybrid_init_", suffix=".bin")
    os.close(fd)
    tmp = Path(tmp_path)
    tmp.write_bytes(sanitized_blob)
    return tmp, applied


def _detect_unsupported_nonflat_syms_state(
    mdir: Path,
    meta: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Detect non-flattened Verilator Syms state dereferences before CUDA launch."""
    if _syms_state_is_covered_by_meta(meta):
        return None
    for ir_name in ("vl_batch_gpu_opt.ll", "vl_batch_gpu.ll"):
        ir_path = mdir / ir_name
        if not ir_path.is_file():
            continue
        for line_no, line in enumerate(ir_path.read_text(encoding="utf-8").splitlines(), 1):
            if _UNSAFE_SYMS_GEP_RE.search(line):
                return {
                    "reason": "unsupported_nonflat_verilator_syms_state",
                    "ir": str(ir_path),
                    "line": line_no,
                    "detail": (
                        "GPU IR dereferences Verilator __Syms/submodule state, but "
                        "the current metadata does not prove a covering Syms state "
                        "image ABI. Rebuild this target with --flatten or with "
                        "--syms-state-image metadata before launching."
                    ),
                }
    return None
