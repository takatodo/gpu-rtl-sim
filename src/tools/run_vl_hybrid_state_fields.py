from __future__ import annotations

import struct


_POINTER_SIZED_HOST_ONLY_FIELDS = {"__VdlySched"}
_FULLY_ZEROED_HOST_ONLY_FIELDS = {"vlNamep"}
_TRANSIENT_VERILATOR_RUNTIME_FIELDS = {
    "__VstlFirstIteration",
    "__VstlPhaseResult",
    "__VicoFirstIteration",
    "__VicoPhaseResult",
    "__VactPhaseResult",
    "__VinactPhaseResult",
    "__VnbaPhaseResult",
    "__VactIterCount",
    "__VinactIterCount",
    "__Vi",
}
_TRANSIENT_VERILATOR_RUNTIME_PREFIXES = (
    "__Vtrigprevexpr_",
    "__VstlTriggered",
    "__VicoTriggered",
    "__VactTriggered",
    "__VnbaTriggered",
    "__Vfunc_",
)


def _is_probable_host_string_field(name: str, size: int) -> bool:
    return name.endswith("_path") and size >= 24


def _is_probable_host_container_field(name: str, size: int) -> bool:
    return name.startswith("__VdlyCommitQueue") and size >= 24


def _is_transient_verilator_runtime_field(name: str) -> bool:
    if name in _TRANSIENT_VERILATOR_RUNTIME_FIELDS:
        return True
    return any(name.startswith(prefix) for prefix in _TRANSIENT_VERILATOR_RUNTIME_PREFIXES)


def sanitize_host_only_internals(
    blob: bytes, layout: list[dict[str, int | str]]
) -> tuple[bytes, list[dict[str, int]]]:
    patched = bytearray(blob)
    pointer_size = struct.calcsize("P")
    applied: list[dict[str, int]] = []
    for entry in layout:
        name = str(entry["name"])
        offset = int(entry["offset"])
        size = int(entry["size"])
        if offset < 0 or size <= 0 or offset + size > len(patched):
            continue
        if _is_transient_verilator_runtime_field(name):
            end = offset + size
            patched[offset:end] = b"\x00" * size
            applied.append(_sanitized_region(name, offset, size, offset, end, 0))
        elif name in _POINTER_SIZED_HOST_ONLY_FIELDS:
            preserve = min(pointer_size, size)
            start = offset + preserve
            end = offset + size
            if start < end:
                patched[start:end] = b"\x00" * (end - start)
                applied.append(_sanitized_region(name, offset, size, start, end, preserve))
        elif (
            name in _FULLY_ZEROED_HOST_ONLY_FIELDS
            or _is_probable_host_string_field(name, size)
            or _is_probable_host_container_field(name, size)
        ):
            end = offset + size
            patched[offset:end] = b"\x00" * size
            applied.append(_sanitized_region(name, offset, size, offset, end, 0))
    return bytes(patched), applied


def _sanitized_region(
    name: str,
    offset: int,
    size: int,
    sanitized_start: int,
    sanitized_end: int,
    preserved_prefix_bytes: int,
) -> dict[str, int]:
    return {
        "field_name": name,
        "offset": offset,
        "size": size,
        "sanitized_start": sanitized_start,
        "sanitized_end": sanitized_end,
        "preserved_prefix_bytes": preserved_prefix_bytes,
    }


def sanitize_host_only_internals_at_root_offset(
    blob: bytes,
    layout: list[dict[str, int | str]],
    *,
    root_offset: int,
) -> tuple[bytes, list[dict[str, int]]]:
    if root_offset <= 0:
        return sanitize_host_only_internals(blob, layout)
    if root_offset >= len(blob):
        return bytes(blob), []
    patched = bytearray(blob)
    root_blob, applied = sanitize_host_only_internals(bytes(patched[root_offset:]), layout)
    patched[root_offset:] = root_blob
    shifted = []
    for entry in applied:
        shifted.append(
            {
                "field_name": str(entry["field_name"]),
                "offset": int(entry["offset"]) + root_offset,
                "size": int(entry["size"]),
                "sanitized_start": int(entry["sanitized_start"]) + root_offset,
                "sanitized_end": int(entry["sanitized_end"]) + root_offset,
                "preserved_prefix_bytes": int(entry["preserved_prefix_bytes"]),
            }
        )
    return bytes(patched), shifted
