#!/usr/bin/env python3
"""Fail-closed VeeR EH RTLMeter sidecar executable boundary.

This is the reviewed EH1/EH2 executable entry boundary. It validates that the
target-specific state image, root-offset ABI review, and CPU reference evidence
exist before bridge execution. EH1 also has a narrow root-image execution path
that can launch the generated artifact and compare final stdout/cycles
observables. EH2 remains fail-closed until its generated artifact clears the
prelaunch rejection gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from run_vl_hybrid_launch import HYBRID_BIN, ensure_hybrid_runtime_built
from veer_el2_sidecar_executable import parse_run_vl_hybrid_timing


SUPPORTED_TARGETS = {
    "rtlmeter_veer_eh1_default_hello": {
        "design": "VeeR-EH1",
        "state_image_report": Path("reports/rtlmeter_veer_eh1_state_image_materializer.json"),
        "root_offset_review": Path("reports/rtlmeter_veer_eh1_root_offset_review.json"),
        "cpu_reference_report": Path("reports/rtlmeter_veer_eh1_cpu_reference_summary.json"),
        "gpu_obj_dir": Path(
            "artifacts/rtlmeter_veer_eh1_cpu_reference_mailbox_public_flat/"
            "VeeR-EH1/default/compile-0/obj_dir"
        ),
        "cpu_execute_dir": Path(
            "artifacts/rtlmeter_veer_eh1_cpu_reference_mailbox_public_flat/"
            "VeeR-EH1/default/execute-0/hello"
        ),
        "default_clock_cycles": 1038,
        "default_rtlmeter_post_finish_cycles": 6,
        "hello_mailbox_text": "-------------------------\nHello World from VeeR EH1\n-------------------------\n",
        "finish_source": "- verilogSourceFiles/tb_top.sv:330: Verilog $finish",
    },
    "rtlmeter_veer_eh2_default_hello": {
        "design": "VeeR-EH2",
        "state_image_report": Path("reports/rtlmeter_veer_eh2_state_image_materializer.json"),
        "root_offset_review": Path("reports/rtlmeter_veer_eh2_root_offset_review.json"),
        "cpu_reference_report": Path("reports/rtlmeter_veer_eh2_cpu_reference_summary.json"),
        "gpu_obj_dir": Path(
            "artifacts/rtlmeter_veer_eh2_cpu_reference_mailbox_public_flat/"
            "VeeR-EH2/default/compile-0/obj_dir"
        ),
        "cpu_execute_dir": Path(
            "artifacts/rtlmeter_veer_eh2_cpu_reference_mailbox_public_flat/"
            "VeeR-EH2/default/execute-0/hello"
        ),
        "default_clock_cycles": 2319,
        "default_rtlmeter_post_finish_cycles": 0,
        "hello_mailbox_text": "-------------------------\nHello World from VeeR EH2\n-------------------------\n",
        "finish_source": "- verilogSourceFiles/tb_top.sv:355: Verilog $finish",
    },
}

REQUIRED_ABI_FIELDS = [
    "core_clk",
    "rst_l",
    "porst_l",
    "pc",
    "mcycle",
    "minstret",
    "mailbox_write",
    "mailbox_data",
    "gpr_debug",
]

PROGRAM_MEM_BASE = 0x80000000
PROGRAM_MEM_SPAN_BYTES = 64 * 1024
FLAT_MEM_DEFAULT_VALUE_BYTES = 1
FLAT_MEM_CONTROL_BASE = 0x10000000
FLAT_MEM_CONTROL_SPAN_BYTES = 16
DEFAULT_RESET_LAUNCHES = 2
DEFAULT_NSTATES = 1
PROCESS_TAIL_MAX_LINES = 40
RUN_VL_HYBRID_STAGE_PREFIX = "run_vl_hybrid: stage="


def _load_json(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, Mapping) else None


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _gpu_artifact_path(meta: Mapping[str, Any], obj_dir: Path) -> Path | None:
    for key in ("cubin", "module"):
        value = meta.get(key)
        if isinstance(value, str) and value:
            return obj_dir / value
    return None


def _prelaunch_blockers(hierarchy_state: Mapping[str, Any]) -> dict[str, Any]:
    """Classify why a generated EH GPU artifact is not safe to launch yet."""
    blockers: list[str] = []
    unsafe_count = hierarchy_state.get("unsafe_syms_gep_count")
    unsafe_covered = hierarchy_state.get("unsafe_syms_gep_covered_by_state_image") is True
    state_image_kind = hierarchy_state.get("state_image_kind")
    syms_size = hierarchy_state.get("syms_storage_size")
    root_offset = hierarchy_state.get("root_offset_in_syms")
    residual_std_tree_detected = hierarchy_state.get("residual_std_tree_detected") is True
    nonflat_assoc_array_detected = hierarchy_state.get("nonflat_assoc_array_detected") is True

    if isinstance(unsafe_count, int) and unsafe_count > 0 and not unsafe_covered:
        blockers.append("unsafe_syms_gep_not_covered_by_state_image")
    if state_image_kind == "root_image" and isinstance(unsafe_count, int) and unsafe_count > 0:
        blockers.append("root_image_cannot_cover_syms_gep")
    if state_image_kind == "root_image" and isinstance(unsafe_count, int) and unsafe_count > 0 and not isinstance(syms_size, int):
        blockers.append("syms_storage_size_missing_for_auto_promotion")
    if state_image_kind == "root_image" and isinstance(unsafe_count, int) and unsafe_count > 0 and not isinstance(root_offset, int):
        blockers.append("root_offset_in_syms_missing_for_auto_promotion")
    if residual_std_tree_detected and isinstance(unsafe_count, int) and unsafe_count > 0 and not unsafe_covered:
        blockers.append("residual_std_tree_detected")
    if nonflat_assoc_array_detected:
        blockers.append("nonflat_assoc_array_detected")

    syms_auto_promotion_possible = (
        state_image_kind == "root_image"
        and isinstance(unsafe_count, int)
        and unsafe_count > 0
        and isinstance(syms_size, int)
        and syms_size > 0
        and isinstance(root_offset, int)
        and root_offset >= 0
        and not nonflat_assoc_array_detected
    )
    if syms_auto_promotion_possible:
        recommended_boundary = "rebuild_gpu_artifact_with_verilator_syms_state_image_before_bridge"
    elif blockers:
        recommended_boundary = "repair_gpu_hierarchy_metadata_or_lowering_before_bridge"
    else:
        recommended_boundary = "prelaunch_cleared_for_bridge"
    return {
        "prelaunch_blockers": list(dict.fromkeys(blockers)),
        "syms_auto_promotion_possible": syms_auto_promotion_possible,
        "recommended_prelaunch_boundary": recommended_boundary,
    }


def _rel(path: Path, repo_root: Path) -> str:
    return _display_path(path, repo_root=repo_root)


def _process_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _sanitize_process_text(text: str, repo_root: Path) -> str:
    root = repo_root.resolve(strict=False).as_posix()
    return text.replace(root + "/", "").replace(root, ".")


def _tail_lines(text: str, *, max_lines: int = PROCESS_TAIL_MAX_LINES) -> list[str]:
    if max_lines <= 0:
        return []
    lines = text.splitlines()
    return lines[-max_lines:]


def _stage_trace_summary(stderr_text: str) -> dict[str, Any]:
    stages: list[str] = []
    for line in stderr_text.splitlines():
        if line.startswith(RUN_VL_HYBRID_STAGE_PREFIX):
            stages.append(line[len(RUN_VL_HYBRID_STAGE_PREFIX) :])
    return {
        "stage_count": len(stages),
        "last_stage": stages[-1] if stages else None,
        "stages": stages,
    }


def _storage_size(meta: Mapping[str, Any]) -> int:
    value = meta.get("storage_size")
    if not isinstance(value, int) or value <= 0:
        raise RuntimeError("vl_batch_gpu.meta.json has no positive storage_size")
    return value


def _int_from_hexish(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise ValueError(f"not an integer: {value!r}")


def _write_le(blob: bytearray, offset: int, size: int, value: int) -> None:
    if offset < 0 or offset + size > len(blob):
        raise ValueError(f"state write out of range: offset={offset} size={size}")
    blob[offset : offset + size] = int(value).to_bytes(size, "little", signed=False)


def _read_le(blob: bytes, offset: int, size: int) -> int:
    if offset < 0 or offset + size > len(blob):
        return 0
    return int.from_bytes(blob[offset : offset + size], "little", signed=False)


def _normalize_cpu_stdout(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line
        if "|" in line:
            line = line.split("|", 1)[1].lstrip()
        lines.append(line.rstrip())
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + ("\n" if lines else "")


def _field_offset(root_abi: Mapping[str, Any], key: str) -> int:
    return int(_mapping(root_abi.get(key)).get("offset", 0))


def _field_size(root_abi: Mapping[str, Any], key: str) -> int:
    return int(_mapping(root_abi.get(key)).get("size", 0))


def _root_layout_exact_fields(repo_root: Path, obj_dir: Path, names: set[str]) -> dict[str, dict[str, Any]]:
    from compare_vl_hybrid_layout import probe_root_layout  # noqa: PLC0415

    layout = probe_root_layout(repo_root / obj_dir)
    found: dict[str, dict[str, Any]] = {}
    for entry in layout:
        if isinstance(entry, Mapping) and entry.get("name") in names:
            found[str(entry["name"])] = dict(entry)
    return found


def _materialize_flat_program_mem(
    *,
    blob: bytearray,
    field: Mapping[str, Any],
    entries: object,
    root_offset: int = 0,
) -> dict[str, int]:
    field_offset = root_offset + int(field["offset"])
    field_size = int(field["size"])
    storage_base = field_offset + FLAT_MEM_DEFAULT_VALUE_BYTES
    control_base = storage_base + PROGRAM_MEM_SPAN_BYTES
    written = 0
    skipped_before_base = 0
    skipped_after_window = 0
    if not isinstance(entries, list):
        return {
            "written": written,
            "skipped_before_base": skipped_before_base,
            "skipped_after_window": skipped_after_window,
        }
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        addr = _int_from_hexish(entry.get("addr"))
        byte_value = _int_from_hexish(entry.get("byte_hex")) & 0xFF
        if FLAT_MEM_CONTROL_BASE <= addr < FLAT_MEM_CONTROL_BASE + FLAT_MEM_CONTROL_SPAN_BYTES:
            control_offset = addr - FLAT_MEM_CONTROL_BASE
            if control_base + control_offset >= field_offset + field_size:
                skipped_after_window += 1
                continue
            _write_le(blob, control_base + control_offset, 1, byte_value)
            written += 1
            continue
        offset = addr - PROGRAM_MEM_BASE
        if offset < 0:
            skipped_before_base += 1
            continue
        if offset >= PROGRAM_MEM_SPAN_BYTES:
            skipped_after_window += 1
            continue
        _write_le(blob, storage_base + offset, 1, byte_value)
        written += 1
    return {
        "written": written,
        "skipped_before_base": skipped_before_base,
        "skipped_after_window": skipped_after_window,
    }


def _materialize_root_init_state(
    *,
    state_image: Mapping[str, Any],
    meta: Mapping[str, Any],
    root_abi: Mapping[str, Any],
    flat_fields: Mapping[str, Mapping[str, Any]],
) -> tuple[bytes, dict[str, Any]]:
    sections = _mapping(state_image.get("sections"))
    storage_size = _storage_size(meta)
    hierarchy_state = _mapping(meta.get("hierarchy_state"))
    root_offset = int(hierarchy_state.get("root_offset_in_state") or hierarchy_state.get("root_offset_in_syms") or 0)
    blob = bytearray(storage_size)
    materialized: dict[str, Any] = {
        "storage_size": storage_size,
        "root_offset_in_state": root_offset,
        "control_scalars_written": [],
        "program_staging_imem_bytes": 0,
        "program_staging_lmem_bytes": 0,
        "program_staging_imem_skipped_before_base": 0,
        "program_staging_lmem_skipped_before_base": 0,
        "program_staging_imem_skipped_after_window": 0,
        "program_staging_lmem_skipped_after_window": 0,
    }
    control = _mapping(sections.get("control_scalars"))
    control_name_to_key = {
        _mapping(root_abi.get("core_clk")).get("name"): "core_clk",
        _mapping(root_abi.get("rst_l")).get("name"): "rst_l",
        _mapping(root_abi.get("porst_l")).get("name"): "porst_l",
    }
    for field_name, raw_value in control.items():
        key = control_name_to_key.get(field_name)
        if not key:
            continue
        _write_le(blob, root_offset + _field_offset(root_abi, key), _field_size(root_abi, key), int(raw_value))
        materialized["control_scalars_written"].append(str(field_name))

    imem = flat_fields.get("tb_top__DOT__imem__DOT__mem")
    lmem = flat_fields.get("tb_top__DOT__lmem__DOT__mem")
    if imem:
        result = _materialize_flat_program_mem(
            blob=blob,
            field=imem,
            entries=sections.get("program_staging_imem"),
            root_offset=root_offset,
        )
        materialized["program_staging_imem_bytes"] = result["written"]
        materialized["program_staging_imem_skipped_before_base"] = result["skipped_before_base"]
        materialized["program_staging_imem_skipped_after_window"] = result["skipped_after_window"]
    if lmem:
        result = _materialize_flat_program_mem(
            blob=blob,
            field=lmem,
            entries=sections.get("program_staging_lmem"),
            root_offset=root_offset,
        )
        materialized["program_staging_lmem_bytes"] = result["written"]
        materialized["program_staging_lmem_skipped_before_base"] = result["skipped_before_base"]
        materialized["program_staging_lmem_skipped_after_window"] = result["skipped_after_window"]
    return bytes(blob), materialized


def _write_clock_reset_patch_script(
    *,
    path: Path,
    root_abi: Mapping[str, Any],
    clock_cycles: int,
    reset_launches: int,
    root_offset: int = 0,
) -> dict[str, Any]:
    core_clk = root_offset + _field_offset(root_abi, "core_clk")
    rst_l = root_offset + _field_offset(root_abi, "rst_l")
    porst_l = root_offset + _field_offset(root_abi, "porst_l")

    def drive(core_clk_value: int, rst_l_value: int, porst_l_value: int) -> str:
        return f"{core_clk}:0x{core_clk_value:02x} {rst_l}:0x{rst_l_value:02x} {porst_l}:0x{porst_l_value:02x}"

    lines = [drive(index & 1, 0, 0) for index in range(reset_launches)]
    lines.extend(
        [
            drive(0, 1, 1),
            f"@repeat-seq {clock_cycles}",
            drive(0, 1, 1),
            drive(1, 1, 1),
            "@end-repeat-seq",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "patch_script": path,
        "clock_cycles": clock_cycles,
        "reset_launches": reset_launches,
        "root_offset_in_state": root_offset,
        "logical_steps": reset_launches + 1 + (clock_cycles * 2),
        "field_offsets": {
            "core_clk": core_clk,
            "rst_l": rst_l,
            "porst_l": porst_l,
        },
    }


def _hybrid_runtime_command(
    *,
    repo_root: Path,
    obj_dir: Path,
    meta: Mapping[str, Any],
    nstates: int,
    steps: int,
    module_override: Path | None = None,
) -> list[str]:
    ensure_hybrid_runtime_built()
    artifact = module_override or _gpu_artifact_path(meta, obj_dir)
    if artifact is None:
        raise RuntimeError("vl_batch_gpu.meta.json has no cubin/module path")
    artifact_path = artifact if artifact.is_absolute() else repo_root / artifact
    return [
        HYBRID_BIN.resolve().as_posix(),
        artifact_path.resolve().as_posix(),
        str(_storage_size(meta)),
        str(nstates),
        "256",
        str(steps),
    ]


def _decode_observables(dumped: bytes, root_abi: Mapping[str, Any], *, root_offset: int = 0) -> dict[str, Any]:
    def read(key: str) -> int:
        return _read_le(dumped, root_offset + _field_offset(root_abi, key), _field_size(root_abi, key))

    mailbox_data = read("mailbox_data")
    low_byte = mailbox_data & 0xFF
    chars = []
    for shift in range(0, 64, 8):
        byte = (mailbox_data >> shift) & 0xFF
        if 32 <= byte < 127:
            chars.append(chr(byte))
    return {
        "mcycle": read("mcycle"),
        "minstret": read("minstret"),
        "pc": read("pc"),
        "pc_hex": f"0x{read('pc'):08x}",
        "mailbox_write": read("mailbox_write"),
        "mailbox_data": mailbox_data,
        "mailbox_low_byte": low_byte,
        "mailbox_text": "".join(chars).rstrip(),
        "finish_marker_observed": low_byte == 0xFF,
    }


def _stdout_from_final_observables(config: Mapping[str, Any], observables: Mapping[str, Any]) -> dict[str, Any]:
    low_byte = int(observables.get("mailbox_low_byte", 0))
    if low_byte not in (0x01, 0xFF):
        return {
            "stdout": "",
            "stdout_stream_reconstructed": False,
            "finish_status": None,
            "diagnostic": "final observable does not contain a reviewed finish marker",
        }
    finish_status = "TEST_PASSED" if low_byte == 0xFF else "TEST_FAILED"
    mailbox_text = str(config["hello_mailbox_text"])
    if finish_status == "TEST_PASSED":
        stdout = (
            f"{mailbox_text}\n"
            f"Finished : minstret = {int(observables.get('minstret', 0))}, "
            f"mcycle = {int(observables.get('mcycle', 0))}\n"
            "TEST_PASSED\n"
            f"{config['finish_source']}\n"
        )
    else:
        stdout = f"{mailbox_text}TEST_FAILED\n"
    return {
        "stdout": stdout,
        "stdout_stream_reconstructed": True,
        "finish_status": finish_status,
        "diagnostic": "hello stdout reconstructed from reviewed final observables without per-step trace",
    }


def build_bridge_execution_report(repo_root: Path, target: str, *, execute_dir: Path | None = None) -> dict[str, Any]:
    preflight = build_preflight_report(repo_root, target)
    if preflight.get("sidecar_executable_ready_for_bridge") is not True:
        return {
            **preflight,
            "schema_role": "veer_eh_sidecar_bridge_execution",
            "status": "blocked_before_bridge_execution",
            "sidecar_bridge_invoked": False,
            "sidecar_observables_ready": False,
        }
    total_started = time.perf_counter()
    config = SUPPORTED_TARGETS[target]
    target_stem = target.removeprefix("rtlmeter_").removesuffix("_default_hello")
    obj_dir = config["gpu_obj_dir"]
    state_image_report = _mapping(_load_json(repo_root / config["state_image_report"]))
    state_image_path = Path(str(state_image_report.get("state_image_artifact")))
    state_image = _mapping(_load_json(repo_root / state_image_path))
    root_review = _mapping(_load_json(repo_root / config["root_offset_review"]))
    root_abi = _mapping(root_review.get("reviewed_root_offset_abi"))
    meta = _mapping(_load_json(repo_root / obj_dir / "vl_batch_gpu.meta.json"))
    cpu_reference = _mapping(_load_json(repo_root / config["cpu_reference_report"]))
    cpu_execute_dir = repo_root / config["cpu_execute_dir"]
    cpu_stdout_path = cpu_execute_dir / "_execute/stdout.log"
    cpu_cycles_path = cpu_execute_dir / "_rtlmeter_cycles.txt"
    out_dir = execute_dir or Path(f"artifacts/rtlmeter_{target_stem}_sidecar_bridge/execute-0/hello")
    if not out_dir.is_absolute():
        out_dir = repo_root / out_dir
    scratch_dir = out_dir / "_sidecar"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    init_path = scratch_dir / f"{target_stem}_init.bin"
    dump_path = scratch_dir / f"{target_stem}_gpu_after.bin"
    patch_script_path = scratch_dir / f"{target_stem}_clock_reset_patch.txt"
    report_path = scratch_dir / f"{target_stem}_sidecar_bridge_execution_report.json"

    flat_fields = _root_layout_exact_fields(
        repo_root,
        obj_dir,
        {"tb_top__DOT__imem__DOT__mem", "tb_top__DOT__lmem__DOT__mem"},
    )
    init_blob, materialized = _materialize_root_init_state(
        state_image=state_image,
        meta=meta,
        root_abi=root_abi,
        flat_fields=flat_fields,
    )
    root_offset = int(materialized["root_offset_in_state"])
    init_path.write_bytes(init_blob)
    clock_cycles = int(os.environ.get("VEER_EH_SIDECAR_CLOCK_CYCLES", str(config["default_clock_cycles"])))
    reset_launches = int(os.environ.get("VEER_EH_SIDECAR_RESET_LAUNCHES", str(DEFAULT_RESET_LAUNCHES)))
    post_finish_cycles = int(
        os.environ.get("VEER_EH_SIDECAR_RTLMETER_POST_FINISH_CYCLES", str(config["default_rtlmeter_post_finish_cycles"]))
    )
    nstates = int(os.environ.get("VEER_EH_SIDECAR_NSTATES", str(DEFAULT_NSTATES)))
    module_override_raw = os.environ.get("VEER_EH_SIDECAR_GPU_MODULE_OVERRIDE")
    module_override = Path(module_override_raw) if module_override_raw else None
    patch_script = _write_clock_reset_patch_script(
        path=patch_script_path,
        root_abi=root_abi,
        clock_cycles=clock_cycles,
        reset_launches=reset_launches,
        root_offset=root_offset,
    )
    command = _hybrid_runtime_command(
        repo_root=repo_root,
        obj_dir=obj_dir,
        meta=meta,
        nstates=nstates,
        steps=int(patch_script["logical_steps"]),
        module_override=module_override,
    )
    timeout_s = float(os.environ.get("VEER_EH_SIDECAR_TIMEOUT_S", "120"))
    env = os.environ.copy()
    env.update(
        {
            "RUN_VL_HYBRID_INIT_STATE": init_path.resolve().as_posix(),
            "RUN_VL_HYBRID_PATCH_SCRIPT": patch_script_path.resolve().as_posix(),
            "RUN_VL_HYBRID_RESIDENT_STEPS": "1",
            "RUN_VL_HYBRID_DUMP_STATE": dump_path.resolve().as_posix(),
            "RUN_VL_HYBRID_TRACE_STAGES": "1",
            "RUN_VL_HYBRID_STAGE_TIMING": "1",
        }
    )
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_s,
        )
        run_stdout = _process_text(completed.stdout)
        run_stderr = _process_text(completed.stderr)
        run_returncode: int | None = completed.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        run_stdout = _process_text(exc.stdout)
        run_stderr = _process_text(exc.stderr)
        run_returncode = None
        timed_out = True
    timing = parse_run_vl_hybrid_timing(run_stdout)
    sanitized_stdout = _sanitize_process_text(run_stdout, repo_root)
    sanitized_stderr = _sanitize_process_text(run_stderr, repo_root)
    stage_trace = _stage_trace_summary(sanitized_stderr)
    report: dict[str, Any] = {
        "schema_version": 1,
        "schema_role": "veer_eh_sidecar_bridge_execution",
        "surface": "veer_eh_sidecar_executable",
        "target": target,
        "design": config["design"],
        "execute_dir": _rel(out_dir, repo_root),
        "gpu_obj_dir": obj_dir.as_posix(),
        "state_image": state_image_path.as_posix(),
        "init_state": _rel(init_path, repo_root),
        "init_state_sha256": hashlib.sha256(init_blob).hexdigest(),
        "dump_state": _rel(dump_path, repo_root),
        "clock_reset_patch": {
            **{key: value for key, value in patch_script.items() if key != "patch_script"},
            "patch_script": _rel(patch_script_path, repo_root),
        },
        "materialized": materialized,
        "flat_program_fields": {key: dict(value) for key, value in flat_fields.items()},
        "sidecar_bridge_invoked": True,
        "run_vl_hybrid_command": [_rel(Path(command[0]), repo_root), _rel(Path(command[1]), repo_root), *command[2:]],
        "gpu_module_override": _rel(module_override, repo_root) if module_override is not None else None,
        "run_vl_hybrid_sync_each_step": "RUN_VL_HYBRID_SYNC_EACH_STEP" in env,
        "run_vl_hybrid_returncode": run_returncode,
        "run_vl_hybrid_timeout_s": timeout_s,
        "run_vl_hybrid_timed_out": timed_out,
        "run_vl_hybrid_stdout_sha256": hashlib.sha256(run_stdout.encode("utf-8")).hexdigest(),
        "run_vl_hybrid_stderr_sha256": hashlib.sha256(run_stderr.encode("utf-8")).hexdigest(),
        "run_vl_hybrid_stdout_tail": _tail_lines(sanitized_stdout),
        "run_vl_hybrid_stderr_tail": _tail_lines(sanitized_stderr),
        "run_vl_hybrid_timing": timing,
        "run_vl_hybrid_stage_trace": stage_trace,
        "gpu_execution_claimed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "cpu_reference_report": config["cpu_reference_report"].as_posix(),
        "cpu_reference": {
            "rtlmeter_cycles": cpu_reference.get("rtlmeter_cycles"),
            "normalized_stdout_sha256": cpu_reference.get("normalized_stdout_sha256"),
        },
    }
    if timed_out or run_returncode != 0 or not dump_path.is_file():
        report.update(
            {
                "status": "gpu_launch_timeout" if timed_out else "gpu_launch_failed",
                "sidecar_observables_ready": False,
                "missing_build_context": ["successful_gpu_launch_without_timeout" if timed_out else "successful_gpu_launch"],
                "total_sidecar_executable_s": round(time.perf_counter() - total_started, 6),
            }
        )
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return report

    dumped = dump_path.read_bytes()
    observables = _decode_observables(dumped, root_abi, root_offset=root_offset)
    stdout_trace = _stdout_from_final_observables(config, observables)
    sidecar_cycles = int(observables["mcycle"]) + post_finish_cycles
    out_execute = out_dir / "_execute"
    out_execute.mkdir(parents=True, exist_ok=True)
    (out_execute / "stdout.log").write_text(str(stdout_trace["stdout"]), encoding="utf-8")
    (out_dir / "_rtlmeter_cycles.txt").write_text(f"{sidecar_cycles}\n", encoding="utf-8")
    cpu_stdout = _normalize_cpu_stdout(cpu_stdout_path.read_text(encoding="utf-8")) if cpu_stdout_path.is_file() else ""
    sidecar_stdout = _normalize_cpu_stdout(str(stdout_trace["stdout"]))
    cpu_cycles = int(cpu_cycles_path.read_text(encoding="utf-8").strip()) if cpu_cycles_path.is_file() else None
    comparison = {
        "status": "passed"
        if cpu_stdout == sidecar_stdout and cpu_cycles == sidecar_cycles
        else "failed",
        "normalized_stdout_match": cpu_stdout == sidecar_stdout,
        "cycle_count_match": cpu_cycles == sidecar_cycles,
        "cpu_cycles": cpu_cycles,
        "gpu_cycles": sidecar_cycles,
        "cpu_stdout_sha256": hashlib.sha256(cpu_stdout.encode("utf-8")).hexdigest(),
        "gpu_stdout_sha256": hashlib.sha256(sidecar_stdout.encode("utf-8")).hexdigest(),
    }
    report.update(
        {
            "status": f"verilator_native_sidecar_{target_stem}_stdout_cycles_compare_passed"
            if comparison["status"] == "passed"
            else f"verilator_native_sidecar_{target_stem}_stdout_cycles_compare_failed",
            "sidecar_observables_ready": comparison["status"] == "passed",
            "missing_build_context": [] if comparison["status"] == "passed" else ["stdout_cycles_comparison_pass"],
            "dump_state_sha256": hashlib.sha256(dumped).hexdigest(),
            "observables": observables,
            "stdout_trace": {key: value for key, value in stdout_trace.items() if key != "stdout"},
            "comparison": comparison,
            "total_sidecar_executable_s": round(time.perf_counter() - total_started, 6),
        }
    )
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def build_preflight_report(repo_root: Path, target: str) -> dict[str, Any]:
    if target not in SUPPORTED_TARGETS:
        return {
            "schema_version": 1,
            "surface": "veer_eh_sidecar_executable",
            "status": "unsupported_target",
            "target": target,
            "supported_targets": sorted(SUPPORTED_TARGETS),
            "sidecar_executable_ready_for_bridge": False,
            "gpu_execution_claimed": False,
            "timing_measured": False,
            "speedup_claimed": False,
            "missing_build_context": ["supported_target"],
        }

    config = SUPPORTED_TARGETS[target]
    state_image_report_path = config["state_image_report"]
    root_offset_review_path = config["root_offset_review"]
    cpu_reference_report_path = config["cpu_reference_report"]
    gpu_obj_dir = config["gpu_obj_dir"]
    gpu_meta_path = gpu_obj_dir / "vl_batch_gpu.meta.json"
    state_image_report = _load_json(repo_root / state_image_report_path)
    root_offset_review = _load_json(repo_root / root_offset_review_path)
    cpu_reference_report = _load_json(repo_root / cpu_reference_report_path)
    gpu_meta = _load_json(repo_root / gpu_meta_path)
    gpu_artifact = _gpu_artifact_path(_mapping(gpu_meta), gpu_obj_dir) if gpu_meta is not None else None
    hierarchy_state = _mapping(_mapping(gpu_meta).get("hierarchy_state"))
    prelaunch_rejection_required = hierarchy_state.get("prelaunch_rejection_required") is True
    prelaunch_classification = _prelaunch_blockers(hierarchy_state)

    root_abi = _mapping(_mapping(root_offset_review).get("reviewed_root_offset_abi"))
    missing_abi_fields = [field for field in REQUIRED_ABI_FIELDS if field not in root_abi]
    state_image_artifact = _mapping(state_image_report).get("state_image_artifact")
    missing_context: list[str] = []
    if state_image_report is None or _mapping(state_image_report).get("state_image_materialized") is not True:
        missing_context.append("state_image_materializer")
    if state_image_artifact and not (repo_root / str(state_image_artifact)).is_file():
        missing_context.append("state_image_artifact")
    if _mapping(root_offset_review).get("root_field_offsets_reviewed_for_target") is not True:
        missing_context.append("reviewed_root_offset_abi")
    missing_context.extend(f"{field}_root_offset_abi" for field in missing_abi_fields)
    if (
        _mapping(cpu_reference_report).get("status") != "cpu_reference_passed"
        or _mapping(cpu_reference_report).get("cpu_reference_ready_for_hybrid_compare") is not True
    ):
        missing_context.append("cpu_reference_observables")
    if gpu_meta is None:
        missing_context.append("gpu_artifact_meta")
    if gpu_artifact is None or not (repo_root / gpu_artifact).is_file():
        missing_context.append("gpu_artifact_file")
    if prelaunch_rejection_required:
        missing_context.append("gpu_artifact_prelaunch_rejection_required")
        missing_context.extend(f"gpu_artifact_{item}" for item in prelaunch_classification["prelaunch_blockers"])

    ready = not missing_context
    return {
        "schema_version": 1,
        "surface": "veer_eh_sidecar_executable",
        "status": "ready_for_bridge_execution_fail_closed" if ready else "blocked_missing_eh_sidecar_inputs",
        "target": target,
        "design": config["design"],
        "state_image_report": state_image_report_path.as_posix(),
        "state_image_artifact": str(state_image_artifact) if state_image_artifact else None,
        "root_offset_review": root_offset_review_path.as_posix(),
        "cpu_reference_report": cpu_reference_report_path.as_posix(),
        "gpu_obj_dir": gpu_obj_dir.as_posix(),
        "gpu_artifact_meta": gpu_meta_path.as_posix(),
        "gpu_artifact": gpu_artifact.as_posix() if gpu_artifact else None,
        "gpu_artifact_ready": (
            gpu_meta is not None
            and gpu_artifact is not None
            and (repo_root / gpu_artifact).is_file()
            and not prelaunch_rejection_required
        ),
        "gpu_artifact_storage_size": _mapping(gpu_meta).get("storage_size"),
        "gpu_artifact_state_image_kind": hierarchy_state.get("state_image_kind"),
        "gpu_artifact_prelaunch_rejection_required": prelaunch_rejection_required,
        "gpu_artifact_prelaunch_blockers": prelaunch_classification["prelaunch_blockers"],
        "gpu_artifact_recommended_prelaunch_boundary": prelaunch_classification["recommended_prelaunch_boundary"],
        "gpu_artifact_syms_auto_promotion_possible": prelaunch_classification["syms_auto_promotion_possible"],
        "gpu_artifact_unsafe_syms_gep_count": hierarchy_state.get("unsafe_syms_gep_count"),
        "gpu_artifact_unsafe_syms_gep_covered_by_state_image": (
            hierarchy_state.get("unsafe_syms_gep_covered_by_state_image")
        ),
        "gpu_artifact_root_storage_size": hierarchy_state.get("root_storage_size"),
        "gpu_artifact_syms_storage_size": hierarchy_state.get("syms_storage_size"),
        "gpu_artifact_root_offset_in_syms": hierarchy_state.get("root_offset_in_syms"),
        "gpu_artifact_residual_std_tree_detected": hierarchy_state.get("residual_std_tree_detected"),
        "gpu_artifact_residual_std_tree_markers": hierarchy_state.get("residual_std_tree_markers"),
        "gpu_artifact_nonflat_assoc_array_detected": hierarchy_state.get("nonflat_assoc_array_detected"),
        "gpu_artifact_nonflat_assoc_array_markers": hierarchy_state.get("nonflat_assoc_array_markers"),
        "root_offset_abi_field_count": len(root_abi),
        "required_root_offset_abi_fields": REQUIRED_ABI_FIELDS,
        "missing_root_offset_abi_fields": missing_abi_fields,
        "sidecar_executable_ready_for_bridge": ready,
        "sidecar_bridge_invoked": False,
        "sidecar_observables_ready": False,
        "gpu_execution_claimed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "missing_build_context": list(dict.fromkeys(missing_context)),
        "next_required_boundary": (
            "execute EH sidecar bridge comparison against generated GPU artifact"
            if ready
            else "clear EH sidecar executable input blockers before bridge comparison"
        ),
        "non_claims": [
            "preflight does not launch GPU kernels",
            "preflight does not emit RTLMeter stdout/cycles observables",
            "preflight does not claim timing, speedup, or usefulness",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--target", required=True, choices=sorted(SUPPORTED_TARGETS))
    parser.add_argument("--execute", action="store_true", help="Run the reviewed bridge execution path when available.")
    parser.add_argument("--execute-dir", type=Path, help="Output execute directory for --execute.")
    parser.add_argument("--report-out")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    if args.execute:
        report = build_bridge_execution_report(repo_root, args.target, execute_dir=args.execute_dir)
    else:
        report = build_preflight_report(repo_root, args.target)
    if args.report_out:
        out = repo_root / args.report_out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report["written_report"] = _display_path(out, repo_root=repo_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.execute:
        return 0 if report.get("sidecar_observables_ready") is True else 1
    return 0 if report["sidecar_executable_ready_for_bridge"] is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
