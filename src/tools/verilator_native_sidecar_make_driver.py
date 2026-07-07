"""Repo-side driver for the native ``verilator --sim-accel sidecar-gpu`` make hook."""

from __future__ import annotations

import hashlib
import contextlib
import io
import json
import os
import re
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path

try:
    from .rtlmeter_stdout_cycles_observables import (
        compare_rtlmeter_observables,
        required_observable_files_missing,
    )
except ImportError:  # pragma: no cover - exercised when invoked as a script.
    from rtlmeter_stdout_cycles_observables import (
        compare_rtlmeter_observables,
        required_observable_files_missing,
    )

from verilator_native_known_closure import (
    STATUS_RECOGNIZED,
    recognize_verilator_native_known_closure,
)

SURFACE = "verilator_native_sidecar_make_driver"
STATUS_BUILD_PLAN_READY = "verilator_native_sidecar_build_plan_ready"
STATUS_BLOCKED_UNRECOGNIZED = "verilator_native_sidecar_blocked_unrecognized_closure"
STATUS_BLOCKED_MISSING_MDIR = "verilator_native_sidecar_blocked_missing_verilated_mdir"
STATUS_BLOCKED_TEMPLATE = "verilator_native_sidecar_blocked_launch_template"
STATUS_BLOCKED_UNSUPPORTED_ARTIFACT = "verilator_native_sidecar_blocked_unsupported_gpu_artifact"
STATUS_BLOCKED_GPU_ARTIFACT_BUILD_FAILED = "verilator_native_sidecar_blocked_gpu_artifact_build_failed"
STATUS_BLOCKED_INIT_STATE_SANITIZE_FAILED = "verilator_native_sidecar_blocked_init_state_sanitize_failed"
STATUS_BLOCKED_VEER_EL2_STATE_LAYOUT = "verilator_native_sidecar_blocked_veer_el2_state_layout_unreviewed"
STATUS_BLOCKED_VEER_EL2_STATE_IMAGE_MATERIALIZER = (
    "verilator_native_sidecar_blocked_veer_el2_state_image_materializer"
)
STATUS_BLOCKED_VEER_EL2_SIDECAR_EXECUTABLE = (
    "verilator_native_sidecar_blocked_veer_el2_sidecar_executable"
)
STATUS_BLOCKED_VEER_EL2_GPU_STATE_IMAGE_LAUNCH = (
    "verilator_native_sidecar_blocked_veer_el2_gpu_state_image_launch"
)
STATUS_BLOCKED_VEER_EL2_SIDECAR_RUN_FAILED = (
    "verilator_native_sidecar_blocked_veer_el2_sidecar_run_failed"
)
STATUS_BLOCKED_VEER_EL2_SIDECAR_OBSERVABLES = (
    "verilator_native_sidecar_blocked_veer_el2_sidecar_observables"
)
STATUS_VEER_EL2_SIDECAR_COMPARE_PASSED = "verilator_native_sidecar_veer_el2_stdout_cycles_compare_passed"
STATUS_VEER_EL2_SIDECAR_COMPARE_FAILED = "verilator_native_sidecar_veer_el2_stdout_cycles_compare_failed"
UNSUPPORTED_TRIGGER_VECTOR_ARTIFACT = "unsupported_verilator_5_048_trigger_vector_artifact"
VEER_EL2_RTL_METER_TARGET = "rtlmeter_veer_el2_default_hello"
VEER_EL2_AUTHORITY = Path("config/rtlmeter_sidecar_authorities/rtlmeter_veer_el2_default_hello.json")
VEER_EL2_TESTBENCH = Path("third_party/rtlmeter/designs/VeeR-EL2/src/tb_top.sv")
VEER_EL2_PROGRAM_HEX = Path("third_party/rtlmeter/designs/VeeR-EL2/tests/hello/program.hex")
VEER_EL2_REVIEWED_PROGRAM_PRELOADS = {
    "hello": {
        "rtlmeter_case": "VeeR-EL2:default:hello",
        "path": VEER_EL2_PROGRAM_HEX,
        "sha256": "d0219135d529505962c1c5ed44360e91466ae046cb8ec40b5980761861c63d76",
    },
    "cmark": {
        "rtlmeter_case": "VeeR-EL2:default:cmark",
        "path": Path("third_party/rtlmeter/designs/VeeR-EL2/tests/cmark/program.hex"),
        "sha256": "a61239282baa0ee815b3613ff342690e2307182c9efda200958be117db2873c2",
    },
    "cmark_iccm": {
        "rtlmeter_case": "VeeR-EL2:default:cmark_iccm",
        "path": Path("third_party/rtlmeter/designs/VeeR-EL2/tests/cmark_iccm/program.hex"),
        "sha256": "ba4749e84329e93d68dcabc4161589c9b4a84cb7e75f0546cad831e8bb1dd652",
    },
    "dhry": {
        "rtlmeter_case": "VeeR-EL2:default:dhry",
        "path": Path("third_party/rtlmeter/designs/VeeR-EL2/tests/dhry/program.hex"),
        "sha256": "44e26685afe0a10b3a70bcc05d706b46e64fdabe612ee2983ce244ca54733bb0",
    },
}
VEER_EL2_PERMANENT_STATE_LAYOUT_BLOCKERS = (
    "gpu_state_image_materializer",
    "veer_el2_sidecar_execution_bridge",
)
RTLMETER_STDOUT_CYCLES_OBSERVABLE_FILES = (
    "_execute/stdout.log",
    "_rtlmeter_cycles.txt",
)
VEER_EL2_STATE_IMAGE_KIND = "veer_el2_extracted_preload_image"
VEER_EL2_SIDECAR_STATE_IMAGE_ENV = "VEER_EL2_SIDECAR_STATE_IMAGE"
VEER_EL2_SIDECAR_EXECUTE_DIR_ENV = "VEER_EL2_SIDECAR_EXECUTE_DIR"
VEER_EL2_SIDECAR_EXECUTABLE_REVIEW_ROLE = "veer_el2_sidecar_executable_review"
VEER_EL2_PYTHON_SIDECAR_EXECUTABLE = Path("src/tools/veer_el2_sidecar_executable.py")
DIRECT_SHIM_SANITIZED_INIT_STATE_NAME = (
    "filelist_known_template_pulp_ita_mha_cpu_repeat_1x1.sanitized.bin"
)
NATIVE_OBJ_DIR_EXECUTABLE_SIDECAR_SHIM_LINK_SMOKE_GATE_REF = (
    "records/scaling_gates/native_obj_dir_executable_sidecar_shim_link_smoke_gate.json"
)
NON_CLAIMS = (
    "recognition and plan construction are compile-side metadata, not GPU execution evidence",
    "the driver never falls back to CPU when the GPU pipeline is unavailable",
    "no speedup, timing, or arbitrary-RTL claim is made",
    "only a tracked known closure can reach sidecar make-time prep or the reviewed template GPU flow",
    "make-time prep is not CUDA module load, kernel launch, or coverage-output equivalence",
)


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>"


def _load_json(path: Path) -> Mapping[str, object] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, Mapping) else None


def _reviewed_veer_el2_program_preload(
    *,
    root: Path,
    program_path: Path | None,
    program_sha256: str | None,
) -> tuple[str | None, Mapping[str, object] | None]:
    if program_path is None or program_sha256 is None:
        return None, None
    try:
        relative_path = program_path.resolve(strict=False).relative_to(root.resolve()).as_posix()
    except ValueError:
        return None, None
    for key, preload in VEER_EL2_REVIEWED_PROGRAM_PRELOADS.items():
        expected_path = preload.get("path")
        expected_sha256 = preload.get("sha256")
        if not isinstance(expected_path, Path) or not isinstance(expected_sha256, str):
            continue
        if relative_path == expected_path.as_posix() and program_sha256 == expected_sha256:
            return key, preload
    return None, None


def _classes_mk_present(mdir: Path) -> bool:
    return mdir.is_dir() and bool(list(mdir.glob("*_classes.mk")))


def _artifact_text_contains(mdir: Path, names: tuple[str, ...], needle: str) -> bool:
    for name in names:
        for path in mdir.glob(name):
            if not path.is_file():
                continue
            try:
                if needle in path.read_text(encoding="utf-8", errors="ignore"):
                    return True
            except OSError:
                continue
    return False


def _first_glob_file(directory: Path, pattern: str) -> Path | None:
    for path in sorted(directory.glob(pattern)):
        if path.is_file():
            return path
    return None


def _read_text_or_empty(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _sha256_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _required_markers_found(text: str, markers: Mapping[str, tuple[str, ...]]) -> dict[str, bool]:
    return {name: all(marker in text for marker in required) for name, required in markers.items()}


def _combined_glob_text(directory: Path, pattern: str) -> str:
    chunks: list[str] = []
    for path in sorted(directory.glob(pattern)):
        if path.is_file():
            chunks.append(_read_text_or_empty(path))
    return "\n".join(chunks)


def _veer_el2_gpr_indices(root_header_text: str) -> list[int]:
    indices = {
        int(match.group(1))
        for match in re.finditer(r"arf__DOT____Vcellout__gpr__BRA__(\d+)__KET____DOT__gprff__dout", root_header_text)
    }
    return sorted(indices)


def _schema_int(mapping: Mapping[str, object], key: str, default: int) -> int:
    value = mapping.get(key)
    return value if isinstance(value, int) else default


def _schema_str(mapping: Mapping[str, object], key: str, default: str) -> str:
    value = mapping.get(key)
    return value if isinstance(value, str) else default


def _schema_bool(mapping: Mapping[str, object], key: str, default: bool) -> bool:
    value = mapping.get(key)
    return value if isinstance(value, bool) else default


def _schema_str_list(mapping: Mapping[str, object], key: str) -> list[str]:
    value = mapping.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _schema_mapping(mapping: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else {}


def _rtlmeter_stdout_cycles_binding_verified(
    *,
    binding: Mapping[str, object],
    root_cpp_text: str,
    testbench_markers: Mapping[str, bool],
) -> bool:
    cpu_reference = _schema_mapping(binding, "cpu_reference")
    sidecar_candidate = _schema_mapping(binding, "sidecar_candidate")
    stdout_binding = _schema_mapping(binding, "normalized_stdout")
    cycles_binding = _schema_mapping(binding, "rtlmeter_cycles")
    pass_fail_binding = _schema_mapping(binding, "pass_fail_markers")
    required_cpu_files = _schema_str_list(cpu_reference, "required_files")
    required_sidecar_files = _schema_str_list(sidecar_candidate, "required_files")
    cycle_fields = _schema_str_list(cycles_binding, "counter_fields")
    required_markers = _schema_str_list(pass_fail_binding, "required_markers")
    return (
        _schema_str(binding, "status", "") == "reviewed_binding_not_observed"
        and _schema_str(binding, "comparison_policy", "")
        == "rtlmeter_stdout_cycles_observables.compare_rtlmeter_observables"
        and _schema_str(stdout_binding, "normalizer", "") == "normalized_rtlmeter_stdout"
        and _schema_str(stdout_binding, "source", "") == "veer_el2_mailbox_write_stream"
        and required_cpu_files == list(RTLMETER_STDOUT_CYCLES_OBSERVABLE_FILES)
        and required_sidecar_files == list(RTLMETER_STDOUT_CYCLES_OBSERVABLE_FILES)
        and cycle_fields == ["mcyclel", "minstretl"]
        and required_markers == ["TEST_PASSED", "TEST_FAILED"]
        and _schema_bool(binding, "cpu_as_gpu_fallback_allowed", True) is False
        and _schema_bool(binding, "gpu_execution_claimed_by_binding", True) is False
        and _schema_bool(binding, "speedup_claimed_by_binding", True) is False
        and testbench_markers.get("observable_policy_found") is True
        and all(marker in root_cpp_text for marker in ("VL_WRITEF_NX", "mcyclel", "minstretl"))
    )


def _bank_ram_fields_found(
    *,
    root_header_text: str,
    schema: Mapping[str, object],
) -> list[int]:
    prefix = _schema_str(schema, "bank_field_prefix", "")
    suffix = _schema_str(schema, "bank_field_suffix", "")
    rows = _schema_int(schema, "rows_per_bank", 0)
    width = _schema_int(schema, "stored_width_bits", 0)
    banks = _schema_int(schema, "num_banks", 0)
    found: list[int] = []
    for bank in range(banks):
        marker = f"VlUnpacked<QData/*{width - 1}:0*/, {rows}> {prefix}{bank}{suffix}"
        if marker in root_header_text:
            found.append(bank)
    return found


def _parse_readmemh_bytes(path: Path) -> dict[int, int]:
    memory: dict[int, int] = {}
    addr = 0
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        for token in line.split():
            if token.startswith("@"):
                addr = int(token[1:], 16)
                continue
            value = int(token, 16)
            if value < 0 or value > 0xFF:
                raise ValueError(f"readmemh byte token out of range: {token}")
            memory[addr] = value
            addr += 1
    return memory


def _read_word_le(memory: Mapping[int, int], addr: int) -> int:
    return (
        int(memory.get(addr, 0))
        | (int(memory.get(addr + 1, 0)) << 8)
        | (int(memory.get(addr + 2, 0)) << 16)
        | (int(memory.get(addr + 3, 0)) << 24)
    )


def _riscv_ecc32(data: int) -> int:
    masks = (
        0x56AA_AD5B,
        0x9B33_366D,
        0xE3C3_C78E,
        0x03FC_07F0,
        0x03FF_F800,
        0xFC00_0000,
    )
    synd = 0
    for bit, mask in enumerate(masks):
        if ((data & mask).bit_count() & 1) != 0:
            synd |= 1 << bit
    if (((data.bit_count() + (synd & 0x3F).bit_count()) & 1) != 0):
        synd |= 1 << 6
    return synd


def _packed_ecc_word(data: int) -> int:
    return 0 if data == 0 else (_riscv_ecc32(data) << 32) | data


def _veer_el2_bank_and_index(addr: int) -> tuple[int, int]:
    # Default VeeR-EL2 has 64 KiB memories, 4 banks, and RV_*_BITS=16.
    return (addr >> 2) & 0x3, (addr & 0xFFFF) >> 4


def _hex_int(value: object) -> int | None:
    if isinstance(value, str) and value.startswith("0x"):
        return int(value, 16)
    return value if isinstance(value, int) else None


def _derive_preload_bank_entries(
    *,
    memory: Mapping[int, int],
    saddr_marker: int,
    schema: Mapping[str, object],
) -> tuple[bool, int, int, dict[str, list[dict[str, str | int]]]]:
    start = _read_word_le(memory, saddr_marker)
    end = _read_word_le(memory, saddr_marker + 4)
    schema_start = _hex_int(schema.get("start_address_hex"))
    schema_end = _hex_int(schema.get("end_address_hex"))
    banks = _schema_int(schema, "num_banks", 4)
    entries: dict[str, list[dict[str, str | int]]] = {str(bank): [] for bank in range(banks)}
    if schema_start is None or schema_end is None or start < schema_start or start > schema_end:
        return False, start, end, entries
    if end < start or end > schema_end:
        return False, start, end, entries
    for addr in range(start, end + 1, 4):
        data = _read_word_le(memory, addr)
        packed = _packed_ecc_word(data)
        if packed == 0:
            continue
        bank, index = _veer_el2_bank_and_index(addr)
        entries[str(bank)].append({
            "addr": f"0x{addr:08x}",
            "index": index,
            "word_hex": f"0x{packed:010x}",
            "data_hex": f"0x{data:08x}",
        })
    return True, start, end, entries


def _sparse_readmemh_entries(memory: Mapping[int, int]) -> list[dict[str, str | int]]:
    return [
        {"addr": f"0x{addr:08x}", "byte_hex": f"0x{value:02x}"}
        for addr, value in sorted(memory.items())
    ]


def _materialize_veer_el2_state_image(
    *,
    root: Path,
    inspection: Mapping[str, object],
    state_image_out: Path,
) -> dict[str, object]:
    if inspection.get("rtlmeter_program_hex") is not None:
        detected_for_identity = inspection.get("detected_layout")
        identity_verified = (
            isinstance(detected_for_identity, Mapping)
            and detected_for_identity.get("rtlmeter_program_identity_verified") is True
        )
        if not identity_verified:
            report = dict(inspection)
            missing = list(report.get("missing_build_context", []))
            missing.extend(
                [
                    "rtlmeter_program_identity_verified",
                    "rtlmeter_program_preload_identity_binding",
                ]
            )
            report["status"] = STATUS_BLOCKED_VEER_EL2_STATE_IMAGE_MATERIALIZER
            report["state_image_materialized"] = False
            report["missing_build_context"] = list(dict.fromkeys(missing))
            report["diagnostic"] = (
                "VeeR-EL2 state-image materializer is blocked: requested "
                "RTLMeter program does not match the reviewed accepted preload"
            )
            return report

    detected = inspection.get("detected_layout")
    if not isinstance(detected, Mapping) or detected.get("gpu_state_image_initialization_schema_verified") is not True:
        report = dict(inspection)
        report["status"] = STATUS_BLOCKED_VEER_EL2_STATE_IMAGE_MATERIALIZER
        report["state_image_materialized"] = False
        report["missing_build_context"] = ["gpu_state_image_initialization_schema"]
        report["diagnostic"] = "VeeR-EL2 state-image materializer is blocked: initialization schema is not verified"
        return report
    accepted_program = inspection.get("accepted_program_preload")
    if not isinstance(accepted_program, str):
        report = dict(inspection)
        report["status"] = STATUS_BLOCKED_VEER_EL2_STATE_IMAGE_MATERIALIZER
        report["state_image_materialized"] = False
        report["missing_build_context"] = ["accepted_program_preload"]
        report["diagnostic"] = "VeeR-EL2 state-image materializer is blocked: no accepted program preload"
        return report

    program_path = root / accepted_program
    program_memory = _parse_readmemh_bytes(program_path)
    authority = _load_json(root / VEER_EL2_AUTHORITY) or {}
    state_layout = authority.get("state_layout") if isinstance(authority, Mapping) else {}
    memory_preload_schema = (
        state_layout.get("memory_preload_schema") if isinstance(state_layout, Mapping) else {}
    )
    if not isinstance(memory_preload_schema, Mapping):
        memory_preload_schema = {}
    dccm_schema = memory_preload_schema.get("dccm")
    iccm_schema = memory_preload_schema.get("iccm")
    if not isinstance(dccm_schema, Mapping):
        dccm_schema = {}
    if not isinstance(iccm_schema, Mapping):
        iccm_schema = {}
    dccm_active, dccm_start, dccm_end, dccm_entries = _derive_preload_bank_entries(
        memory=program_memory,
        saddr_marker=0xFFFF_FFF8,
        schema=dccm_schema,
    )
    iccm_active, iccm_start, iccm_end, iccm_entries = _derive_preload_bank_entries(
        memory=program_memory,
        saddr_marker=0xFFFF_FFF0,
        schema=iccm_schema,
    )
    image = {
        "schema_version": 1,
        "schema_role": "veer_el2_extracted_preload_state_image",
        "target": VEER_EL2_RTL_METER_TARGET,
        "program_preload": accepted_program,
        "program_sha256": inspection.get("accepted_program_preload_sha256"),
        "state_image_kind": "veer_el2_extracted_preload_image",
        "sections": {
            "program_staging_lmem": _sparse_readmemh_entries(program_memory),
            "program_staging_imem": _sparse_readmemh_entries(program_memory),
            "dccm_banks": {
                "preload_active": dccm_active,
                "start_address_hex": f"0x{dccm_start:08x}",
                "end_address_hex": f"0x{dccm_end:08x}",
                "nonzero_entries_by_bank": dccm_entries,
            },
            "iccm_banks": {
                "preload_active": iccm_active,
                "start_address_hex": f"0x{iccm_start:08x}",
                "end_address_hex": f"0x{iccm_end:08x}",
                "nonzero_entries_by_bank": iccm_entries,
            },
            "control_scalars": {
                "tb_top__DOT__core_clk": 0,
                "tb_top__DOT__rst_l": 0,
                "tb_top__DOT__porst_l": 0,
            },
        },
        "non_claims": [
            "state image materialization is not GPU execution",
            "state image materialization is not RTLMeter stdout/cycles comparison",
            "state image materialization is not speedup evidence",
        ],
    }
    image_blob = json.dumps(image, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    state_image_out.parent.mkdir(parents=True, exist_ok=True)
    state_image_out.write_bytes(image_blob)

    report = dict(inspection)
    remaining = [
        item
        for item in report.get("missing_build_context", [])
        if item != "gpu_state_image_materializer"
    ]
    report["status"] = STATUS_BLOCKED_VEER_EL2_STATE_LAYOUT
    report["state_image_materialized"] = True
    report["state_image_path"] = _display_path(state_image_out, root)
    report["state_image_sha256"] = _sha256_bytes(image_blob)
    report["state_image_program_byte_count"] = len(program_memory)
    report["state_image_dccm_preload_active"] = dccm_active
    report["state_image_iccm_preload_active"] = iccm_active
    report["state_image_dccm_nonzero_entry_count"] = sum(len(entries) for entries in dccm_entries.values())
    report["state_image_iccm_nonzero_entry_count"] = sum(len(entries) for entries in iccm_entries.values())
    report["missing_build_context"] = remaining
    report["diagnostic"] = (
        "VeeR-EL2 state image was materialized, but GPU usefulness is still blocked "
        "until the direct sidecar execution bridge and GPU run are reviewed"
    )
    return report


def _veer_el2_state_layout_inspection(
    *,
    root: Path,
    plan: dict[str, object],
    rtlmeter_program_hex: str | Path | None = None,
) -> dict[str, object]:
    raw_mdir = plan.get("mdir")
    mdir = root / str(raw_mdir) if isinstance(raw_mdir, str) else None
    if mdir is not None and Path(str(raw_mdir)).is_absolute():
        mdir = Path(str(raw_mdir))
    root_header = _first_glob_file(mdir, "*___024root.h") if mdir is not None else None
    if root_header is None:
        plan["status"] = STATUS_BLOCKED_VEER_EL2_STATE_LAYOUT
        plan["build_plan_ready"] = False
        plan["state_layout_ready"] = False
        plan["state_layout_inspection_performed"] = False
        plan["root_header"] = None
        plan["testbench_source"] = _display_path(root / VEER_EL2_TESTBENCH, root)
        plan["program_hex"] = _display_path(root / VEER_EL2_PROGRAM_HEX, root)
        plan["missing_build_context"] = [
            "verilated_root_header",
            *VEER_EL2_PERMANENT_STATE_LAYOUT_BLOCKERS,
        ]
        plan["diagnostic"] = "VeeR-EL2 state layout inspection is blocked: no Verilated root header was found"
        return plan

    root_header_text = _read_text_or_empty(root_header)
    root_cpp_text = _combined_glob_text(root_header.parent, "*___024root*.cpp")
    testbench_source = root / VEER_EL2_TESTBENCH
    testbench_text = _read_text_or_empty(testbench_source)
    authority = _load_json(root / VEER_EL2_AUTHORITY) or {}
    state_layout = authority.get("state_layout") if isinstance(authority, Mapping) else None
    expected_program = None
    expected_program_sha256 = None
    expected_pc_candidates: list[str] = []
    expected_gpr_indices = list(range(1, 32))
    expected_gpr_width_bits = 32
    expected_gpr_x0_implicit_zero = True
    memory_preload_schema: Mapping[str, object] = {}
    gpu_state_image_schema: Mapping[str, object] = {}
    stdout_cycles_binding: Mapping[str, object] = {}
    if isinstance(state_layout, Mapping):
        expected_program_value = state_layout.get("accepted_program_preload")
        if isinstance(expected_program_value, str) and expected_program_value:
            expected_program = root / expected_program_value
        expected_program_sha256_value = state_layout.get("accepted_program_preload_sha256")
        if isinstance(expected_program_sha256_value, str) and expected_program_sha256_value:
            expected_program_sha256 = expected_program_sha256_value
        pc_schema = state_layout.get("pc_schema")
        if isinstance(pc_schema, Mapping):
            candidate_values = pc_schema.get("accepted_field_candidates")
            if isinstance(candidate_values, list):
                expected_pc_candidates = [str(item) for item in candidate_values if str(item)]
        gpr_schema = state_layout.get("integer_register_file_schema")
        if isinstance(gpr_schema, Mapping):
            index_values = gpr_schema.get("explicit_register_indices")
            if isinstance(index_values, list):
                expected_gpr_indices = sorted(
                    int(item)
                    for item in index_values
                    if isinstance(item, int) or (isinstance(item, str) and item.isdigit())
                )
            width_value = gpr_schema.get("width_bits")
            if isinstance(width_value, int):
                expected_gpr_width_bits = width_value
            x0_value = gpr_schema.get("x0_implicit_zero")
            if isinstance(x0_value, bool):
                expected_gpr_x0_implicit_zero = x0_value
        memory_schema_value = state_layout.get("memory_preload_schema")
        if isinstance(memory_schema_value, Mapping):
            memory_preload_schema = memory_schema_value
        state_image_schema_value = state_layout.get("gpu_state_image_initialization_schema")
        if isinstance(state_image_schema_value, Mapping):
            gpu_state_image_schema = state_image_schema_value
        stdout_cycles_binding_value = state_layout.get("rtlmeter_stdout_cycles_gpu_compare_binding")
        if isinstance(stdout_cycles_binding_value, Mapping):
            stdout_cycles_binding = stdout_cycles_binding_value
    observed_program_path = None
    if rtlmeter_program_hex is not None:
        observed_program_path = Path(rtlmeter_program_hex)
        if not observed_program_path.is_absolute():
            observed_program_path = root / observed_program_path
    observed_program_sha256 = _sha256_file(observed_program_path) if observed_program_path is not None else None
    reviewed_program_key, reviewed_program_preload = _reviewed_veer_el2_program_preload(
        root=root,
        program_path=observed_program_path,
        program_sha256=observed_program_sha256,
    )
    if reviewed_program_preload is not None:
        reviewed_program_path = reviewed_program_preload.get("path")
        reviewed_program_sha256 = reviewed_program_preload.get("sha256")
        if isinstance(reviewed_program_path, Path) and isinstance(reviewed_program_sha256, str):
            expected_program = root / reviewed_program_path
            expected_program_sha256 = reviewed_program_sha256
    expected_program_observed_sha256 = _sha256_file(expected_program) if expected_program is not None else None
    program_identity_verified = (
        observed_program_sha256 is not None
        and expected_program_sha256 is not None
        and expected_program_observed_sha256 == expected_program_sha256
        and observed_program_sha256 == expected_program_sha256
    )

    root_markers = _required_markers_found(
        root_header_text,
        {
            "reset_clock_fields_found": (
                "tb_top__DOT__core_clk",
                "tb_top__DOT__rst_l",
                "tb_top__DOT__porst_l",
            ),
            "preload_memories_found": (
                "VlAssocArray<IData/*31:0*/, CData/*7:0*/> tb_top__DOT__imem__DOT__mem",
                "VlAssocArray<IData/*31:0*/, CData/*7:0*/> tb_top__DOT__lmem__DOT__mem",
            ),
            "observable_root_fields_found": (
                "tb_top__DOT__mailbox_write",
                "tb_top__DOT__mailbox_data",
            ),
            "cycle_counter_fields_found": (
                "mcyclel",
                "minstretl",
            ),
        },
    )
    observable_expression_markers = _required_markers_found(
        root_cpp_text,
        {
            "observable_expression_binding_found": (
                "tb_top__DOT__mailbox_write",
                "bus_buffer__DOT__obuf_data",
                'VL_WRITEF_NX("%c"',
                'VL_WRITEF_NX("TEST_PASSED',
                'VL_WRITEF_NX("TEST_FAILED',
                "minstretl",
                "mcyclel",
            ),
            "mailbox_address_expression_found": (
                "tb_top__DOT__mailbox_write",
                "tb_top__DOT__lmem_axi_awvalid",
                "tb_top__DOT__lsu_axi_awaddr",
                "0xd0580000U",
            ),
        },
    )
    pc_candidates = [
        marker for marker in (
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_i0_pc_d",
            "i0_pc_r_ff",
        )
        if marker in root_header_text
    ]
    gpr_indices = _veer_el2_gpr_indices(root_header_text)
    pc_schema_verified = bool(expected_pc_candidates) and any(
        candidate in root_header_text for candidate in expected_pc_candidates
    )
    gpr_schema_verified = (
        expected_gpr_width_bits == 32
        and expected_gpr_x0_implicit_zero is True
        and gpr_indices == expected_gpr_indices
    )
    testbench_markers = _required_markers_found(
        testbench_text,
        {
            "program_readmemh_found": (
                '$readmemh("program.hex",  lmem.mem);',
                '$readmemh("program.hex",  imem.mem);',
            ),
            "iteration_plusarg_preload_found": (
                '$value$plusargs("iterations=%d", iterations)',
                "lmem.mem[32'h10000000]",
            ),
            "preload_tasks_found": (
                "preload_dccm();",
                "preload_iccm();",
            ),
            "ecc_bank_preload_found": (
                "riscv_ecc32",
                "slam_dccm_ram",
                "slam_iccm_ram",
            ),
            "observable_policy_found": (
                "TEST_PASSED",
                "TEST_FAILED",
                "mailbox_write",
            ),
        },
    )
    program_staging_schema = memory_preload_schema.get("program_staging")
    if not isinstance(program_staging_schema, Mapping):
        program_staging_schema = {}
    dccm_schema = memory_preload_schema.get("dccm")
    if not isinstance(dccm_schema, Mapping):
        dccm_schema = {}
    iccm_schema = memory_preload_schema.get("iccm")
    if not isinstance(iccm_schema, Mapping):
        iccm_schema = {}
    dccm_bank_fields = _bank_ram_fields_found(root_header_text=root_header_text, schema=dccm_schema)
    iccm_bank_fields = _bank_ram_fields_found(root_header_text=root_header_text, schema=iccm_schema)
    expected_dccm_banks = list(range(_schema_int(dccm_schema, "num_banks", 0)))
    expected_iccm_banks = list(range(_schema_int(iccm_schema, "num_banks", 0)))
    staging_memory_schema_verified = (
        _schema_str(program_staging_schema, "lmem_field", "") in root_header_text
        and _schema_str(program_staging_schema, "imem_field", "") in root_header_text
        and _schema_int(program_staging_schema, "entry_key_width_bits", 0) == 32
        and _schema_int(program_staging_schema, "entry_value_width_bits", 0) == 8
        and testbench_markers["program_readmemh_found"]
        and testbench_markers["iteration_plusarg_preload_found"]
    )
    dccm_schema_verified = (
        bool(dccm_schema)
        and dccm_bank_fields == expected_dccm_banks
        and _schema_int(dccm_schema, "rows_per_bank", 0) == 4096
        and _schema_int(dccm_schema, "stored_width_bits", 0) == 39
        and _schema_str(dccm_schema, "slam_task", "") in testbench_text
        and _schema_str(dccm_schema, "bank_function", "") in root_cpp_text
    )
    iccm_schema_verified = (
        bool(iccm_schema)
        and iccm_bank_fields == expected_iccm_banks
        and _schema_int(iccm_schema, "rows_per_bank", 0) == 4096
        and _schema_int(iccm_schema, "stored_width_bits", 0) == 39
        and _schema_str(iccm_schema, "slam_task", "") in testbench_text
        and _schema_str(iccm_schema, "bank_function", "") in root_cpp_text
    )
    ecc_schema = memory_preload_schema.get("packed_word")
    if not isinstance(ecc_schema, Mapping):
        ecc_schema = {}
    ecc_schema_verified = (
        _schema_int(ecc_schema, "data_width_bits", 0) == 32
        and _schema_int(ecc_schema, "ecc_width_bits", 0) == 7
        and _schema_int(ecc_schema, "stored_width_bits", 0) == 39
        and _schema_str(memory_preload_schema, "ecc_function", "") in testbench_text
        and testbench_markers["ecc_bank_preload_found"]
    )
    memory_preload_schema_verified = (
        staging_memory_schema_verified
        and dccm_schema_verified
        and iccm_schema_verified
        and ecc_schema_verified
    )
    stdout_cycles_binding_verified = _rtlmeter_stdout_cycles_binding_verified(
        binding=stdout_cycles_binding,
        root_cpp_text=root_cpp_text,
        testbench_markers=testbench_markers,
    )
    state_image_sections = gpu_state_image_schema.get("state_image_sections")
    if not isinstance(state_image_sections, list):
        state_image_sections = []
    state_image_section_names = sorted(
        str(section.get("name"))
        for section in state_image_sections
        if isinstance(section, Mapping) and isinstance(section.get("name"), str)
    )
    expected_state_image_section_names = sorted([
        "control_scalars",
        "dccm_banks",
        "iccm_banks",
        "program_staging_imem",
        "program_staging_lmem",
    ])
    state_image_required_root_fields = _schema_str_list(gpu_state_image_schema, "required_root_fields")
    state_image_required_cpp_markers = _schema_str_list(
        gpu_state_image_schema, "required_generated_cpp_markers"
    )
    state_image_order = _schema_str_list(gpu_state_image_schema, "initialization_order")
    expected_state_image_order = [
        "zero_root_state",
        "load_program_hex_into_lmem_imem",
        "apply_iterations_plusarg_lmem_patch",
        "derive_dccm_banks_from_lmem_with_ecc",
        "derive_iccm_banks_from_imem_with_ecc",
        "initialize_reset_clock_inputs",
        "bind_pc_gpr_and_observable_fields",
    ]
    state_image_schema_verified = (
        bool(gpu_state_image_schema)
        and _schema_str(gpu_state_image_schema, "state_image_kind", "")
        == "veer_el2_extracted_preload_image"
        and _schema_bool(gpu_state_image_schema, "requires_materializer", False) is True
        and state_image_order == expected_state_image_order
        and state_image_section_names == expected_state_image_section_names
        and all(field in root_header_text for field in state_image_required_root_fields)
        and all(marker in root_cpp_text for marker in state_image_required_cpp_markers)
        and memory_preload_schema_verified
        and pc_schema_verified
        and gpr_schema_verified
        and (
            root_markers["observable_root_fields_found"]
            or (
                observable_expression_markers["observable_expression_binding_found"]
                and observable_expression_markers["mailbox_address_expression_found"]
            )
        )
    )
    detected_layout: dict[str, object] = {
        **root_markers,
        **observable_expression_markers,
        "observable_fields_found": (
            root_markers["observable_root_fields_found"]
            or (
                observable_expression_markers["observable_expression_binding_found"]
                and observable_expression_markers["mailbox_address_expression_found"]
            )
        ),
        "pc_field_candidates": pc_candidates,
        "pc_schema_verified": pc_schema_verified,
        "gpr_field_indices_detected": gpr_indices,
        "gpr_field_indices_1_to_31_detected": gpr_indices == list(range(1, 32)),
        "gpr_schema_verified": gpr_schema_verified,
        "gpr_schema_expected_indices": expected_gpr_indices,
        "gpr_schema_x0_implicit_zero": expected_gpr_x0_implicit_zero,
        "gpr_schema_width_bits": expected_gpr_width_bits,
        "staging_memory_schema_verified": staging_memory_schema_verified,
        "dccm_schema_verified": dccm_schema_verified,
        "dccm_bank_fields_detected": dccm_bank_fields,
        "iccm_schema_verified": iccm_schema_verified,
        "iccm_bank_fields_detected": iccm_bank_fields,
        "ecc_schema_verified": ecc_schema_verified,
        "memory_preload_schema_verified": memory_preload_schema_verified,
        "gpu_state_image_initialization_schema_verified": state_image_schema_verified,
        "rtlmeter_stdout_cycles_gpu_compare_binding_verified": stdout_cycles_binding_verified,
        "gpu_state_image_sections": state_image_section_names,
        "gpu_state_image_requires_materializer": _schema_bool(
            gpu_state_image_schema, "requires_materializer", False
        ),
        "testbench_program_preload_found": testbench_markers["program_readmemh_found"],
        "testbench_iteration_plusarg_preload_found": testbench_markers["iteration_plusarg_preload_found"],
        "testbench_preload_tasks_found": testbench_markers["preload_tasks_found"],
        "testbench_ecc_bank_preload_found": testbench_markers["ecc_bank_preload_found"],
        "testbench_observable_policy_found": testbench_markers["observable_policy_found"],
        "rtlmeter_program_identity_verified": program_identity_verified,
        "reviewed_rtlmeter_program_preload_supported": reviewed_program_preload is not None,
    }
    alternative_observable_keys = {
        "observable_root_fields_found",
        "observable_expression_binding_found",
        "mailbox_address_expression_found",
    }
    missing = [
        name
        for name, found in detected_layout.items()
        if (
            isinstance(found, bool)
            and not found
            and name not in alternative_observable_keys
        )
    ]
    if not pc_candidates:
        missing.append("pc_field_candidates")
    if not pc_schema_verified:
        missing.append("pc_schema")
    if not gpr_indices:
        missing.append("gpr_field_indices_detected")
    if not gpr_schema_verified:
        missing.append("complete_gpr_field_layout_schema")
    if not memory_preload_schema_verified:
        missing.append("explicit_iccm_dccm_bank_ecc_layout_schema")
    if not state_image_schema_verified:
        missing.append("gpu_state_image_initialization_schema")
    if not program_identity_verified:
        missing.append("rtlmeter_program_preload_identity_binding")
    if not stdout_cycles_binding_verified:
        missing.append("rtlmeter_stdout_cycles_gpu_compare_binding")
    missing.append("gpu_state_image_materializer")
    missing.extend(VEER_EL2_PERMANENT_STATE_LAYOUT_BLOCKERS)
    missing = list(dict.fromkeys(missing))

    plan["status"] = STATUS_BLOCKED_VEER_EL2_STATE_LAYOUT
    plan["build_plan_ready"] = False
    plan["state_layout_ready"] = False
    plan["state_layout_inspection_performed"] = True
    plan["state_layout_target"] = VEER_EL2_RTL_METER_TARGET
    plan["root_header"] = _display_path(root_header, root)
    plan["testbench_source"] = _display_path(testbench_source, root)
    plan["program_hex"] = _display_path(root / VEER_EL2_PROGRAM_HEX, root)
    plan["rtlmeter_program_hex"] = (
        _display_path(observed_program_path, root) if observed_program_path is not None else None
    )
    plan["rtlmeter_program_sha256"] = observed_program_sha256
    plan["accepted_program_preload"] = (
        _display_path(expected_program, root) if expected_program is not None else None
    )
    plan["accepted_program_preload_sha256"] = expected_program_sha256
    plan["accepted_program_observed_sha256"] = expected_program_observed_sha256
    plan["reviewed_rtlmeter_program_preload_key"] = reviewed_program_key
    plan["reviewed_rtlmeter_program_preload_supported"] = reviewed_program_preload is not None
    plan["reviewed_rtlmeter_case"] = (
        reviewed_program_preload.get("rtlmeter_case")
        if isinstance(reviewed_program_preload, Mapping)
        else None
    )
    plan["detected_layout"] = detected_layout
    plan["missing_build_context"] = missing
    plan["diagnostic"] = (
        "VeeR-EL2 state/preload/observable markers were inspected, but GPU usefulness "
        "is still blocked until the GPU state-image materializer and sidecar execution bridge are reviewed"
    )
    return plan


def _unsupported_gpu_artifact_compatibility(mdir: Path) -> dict[str, object] | None:
    meta = _load_json(mdir / "vl_batch_gpu.meta.json")
    if isinstance(meta, Mapping):
        compatibility = meta.get("fc061_direct_shim_compatibility")
        if isinstance(compatibility, Mapping) and compatibility.get("supported") is False:
            return dict(compatibility)

    has_triggered_acc = _artifact_text_contains(
        mdir,
        ("*___024root.h",),
        "__VactTriggeredAcc",
    )
    has_trigger_vec = _artifact_text_contains(
        mdir,
        ("vl_batch_gpu*.ll",),
        "eval_triggers_vec__act",
    )
    if has_triggered_acc or has_trigger_vec:
        markers = []
        if has_triggered_acc:
            markers.append("root_header___VactTriggeredAcc")
        if has_trigger_vec:
            markers.append("gpu_ir_eval_triggers_vec__act")
        return {
            "status": UNSUPPORTED_TRIGGER_VECTOR_ARTIFACT,
            "supported": False,
            "trigger_vector_artifact_detected": True,
            "trigger_vector_markers": markers,
        }
    return None


def _layout_entry_summary(entry: Mapping[str, object]) -> dict[str, object]:
    return {
        "name": entry.get("name"),
        "offset": entry.get("offset"),
        "size": entry.get("size"),
        "decl_type": entry.get("decl_type"),
    }


def _resolve_layout_marker(
    layout_by_name: Mapping[str, Mapping[str, object]],
    marker: str,
) -> Mapping[str, object] | None:
    exact = layout_by_name.get(marker)
    if exact is not None:
        return exact
    candidates = [entry for name, entry in layout_by_name.items() if marker in name]
    if not candidates:
        return None
    for entry in candidates:
        name = str(entry.get("name", ""))
        if name.endswith(f"__DOT__{marker}") or name.endswith(f"____Vcellout__{marker}__dout"):
            return entry
    for entry in candidates:
        name = str(entry.get("name", ""))
        decl_type = str(entry.get("decl_type", ""))
        if name.endswith(marker) and "IData" in decl_type:
            return entry
    return sorted(candidates, key=lambda entry: len(str(entry.get("name", ""))))[0]


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _veer_el2_root_state_offset_review_from_layout(
    *,
    layout: list[Mapping[str, object]],
    authority: Mapping[str, object],
) -> dict[str, object]:
    layout_by_name = {str(entry.get("name")): entry for entry in layout if isinstance(entry.get("name"), str)}
    state_layout = _as_mapping(authority.get("state_layout"))
    pc_schema = _as_mapping(state_layout.get("pc_schema"))
    gpr_schema = _as_mapping(state_layout.get("integer_register_file_schema"))
    memory_schema = _as_mapping(state_layout.get("memory_preload_schema"))
    state_image_schema = _as_mapping(state_layout.get("gpu_state_image_initialization_schema"))
    stdout_cycles_binding = _as_mapping(state_layout.get("rtlmeter_stdout_cycles_gpu_compare_binding"))

    required_markers: dict[str, str] = {}
    for field in _schema_str_list(state_image_schema, "required_root_fields"):
        required_markers[field] = field
    for section in state_image_schema.get("state_image_sections", []):
        if not isinstance(section, Mapping):
            continue
        source_field = section.get("source_field")
        if isinstance(source_field, str) and source_field:
            required_markers[source_field] = source_field
        fields = section.get("fields")
        if isinstance(fields, list):
            for field in fields:
                if isinstance(field, str) and field:
                    required_markers[field] = field

    for candidate in _schema_str_list(pc_schema, "accepted_field_candidates"):
        required_markers[f"pc:{candidate}"] = candidate

    gpr_regex = str(gpr_schema.get("field_regex", ""))
    if "\\\\d" in gpr_regex:
        gpr_regex = gpr_regex.replace("\\\\d", "\\d")
    gpr_pattern = re.compile(gpr_regex) if gpr_regex else None
    expected_gprs = set()
    raw_indices = gpr_schema.get("explicit_register_indices")
    if isinstance(raw_indices, list):
        expected_gprs = {
            int(item)
            for item in raw_indices
            if isinstance(item, int) or (isinstance(item, str) and item.isdigit())
        }
    gpr_entries: dict[int, Mapping[str, object]] = {}
    if gpr_pattern is not None:
        for name, entry in layout_by_name.items():
            match = gpr_pattern.search(name)
            if match:
                gpr_entries[int(match.group(1))] = entry

    program_staging = _as_mapping(memory_schema.get("program_staging"))
    for field in (
        _schema_str(program_staging, "lmem_field", ""),
        _schema_str(program_staging, "imem_field", ""),
    ):
        if field:
            required_markers[field] = field
    for schema_name in ("dccm", "iccm"):
        bank_schema = _as_mapping(memory_schema.get(schema_name))
        prefix = _schema_str(bank_schema, "bank_field_prefix", "")
        suffix = _schema_str(bank_schema, "bank_field_suffix", "")
        for bank in range(_schema_int(bank_schema, "num_banks", 0)):
            field = f"{prefix}{bank}{suffix}"
            required_markers[field] = field

    cycle_fields = _as_mapping(stdout_cycles_binding.get("rtlmeter_cycles")).get("counter_fields")
    if isinstance(cycle_fields, list):
        for field in cycle_fields:
            if isinstance(field, str) and field:
                required_markers[f"cycle:{field}"] = field
    for field in ("mailbox_write", "obuf_data"):
        required_markers[f"observable:{field}"] = field
    for field in ("tb_top__DOT__reset_vector", "tb_top__DOT__nmi_vector"):
        required_markers[field] = field
    for logical_name, field in (
        ("debug:dec_i0_branch_d", "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_i0_branch_d"),
        ("debug:dec_i0_decode_d", "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_i0_decode_d"),
        (
            "debug:dec_decode_valid_gate",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT____VdfgRegularize_hdab710bf_0_43",
        ),
        (
            "debug:dec_ib0_valid_d",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__dec_ib0_valid_d",
        ),
        (
            "debug:dec_misc2ff_dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT____Vcellout__misc2ff__dout",
        ),
        (
            "debug:dec_i0_exublock_d",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_exublock_d",
        ),
        (
            "debug:dec_misc1ff_dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT____Vcellout__misc1ff__dout",
        ),
        (
            "debug:dec_halt_ff_dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT____Vcellout__halt_ff__dout",
        ),
        (
            "debug:dec_presync_stall",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__presync_stall",
        ),
        (
            "debug:dec_lsu_idle",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__lsu_idle",
        ),
        (
            "debug:exu_div_valid_in",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT____Vcellinp__genblock5__DOT__i_new_4bit_div_fullshortq__valid_in",
        ),
        (
            "debug:exu_div_running_state",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__running_state",
        ),
        (
            "debug:exu_div_i_misc_ff_dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT____Vcellout__i_misc_ff__dout",
        ),
        (
            "debug:exu_div_i_misc_ff_din",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__i_misc_ff__DOT__genblock__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din",
        ),
        (
            "debug:exu_div_shortq",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__shortq",
        ),
        (
            "debug:exu_div_shortq_enable",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__shortq_enable",
        ),
        (
            "debug:exu_div_quotient_raw",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__quotient_raw",
        ),
        (
            "debug:exu_div_quotient_new",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__quotient_new",
        ),
        (
            "debug:exu_div_dw_shortq_raw",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__dw_shortq_raw",
        ),
        (
            "debug:exu_div_i_b_ff_dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT____Vcellout__i_b_ff__dout",
        ),
        (
            "debug:exu_div_i_b_ff_din",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__i_b_ff__DOT__genblock__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din",
        ),
        (
            "debug:exu_div_a_ff",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__a_ff",
        ),
        (
            "debug:exu_div_q_ff",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__q_ff",
        ),
        (
            "debug:exu_div_r_ff",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__r_ff",
        ),
        (
            "debug:i0_pc_r_ff_din",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_pc_r_ff__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din",
        ),
        (
            "debug:dec_i0_instr_d",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__dec_i0_instr_d",
        ),
        (
            "debug:i0_brp_valid",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_brp_valid",
        ),
        (
            "debug:i0_predict_nt",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_predict_nt",
        ),
        (
            "debug:i0_predict_br",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_predict_br",
        ),
        (
            "debug:dec_tlu_i0_valid_r",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__dec_tlu_i0_valid_r",
        ),
        (
            "debug:i0_valid_no_ebreak_ecall_r",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT__i0_valid_no_ebreak_ecall_r",
        ),
        ("debug:dma_dccm_stall_any", "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dma_dccm_stall_any"),
        ("debug:lsu_store_stall_any", "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__lsu_store_stall_any"),
        ("debug:dec_lsu_valid_raw_d", "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_lsu_valid_raw_d"),
        ("debug:ifu_pmu_fetch_stall", "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_pmu_fetch_stall"),
        (
            "debug:ifu_pmu_instr_aligned",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_pmu_instr_aligned",
        ),
        (
            "debug:ifu_ifc_fbwrite_dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT____Vcellout__fbwrite_ff__dout",
        ),
        (
            "debug:ifu_ifc_fetch_consume_gate",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT____VdfgRegularize_h02fb64cc_0_10",
        ),
        ("debug:dec_tlu_flush_err_r", "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_flush_err_r"),
        ("debug:dma_iccm_stall_any", "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dma_iccm_stall_any"),
        (
            "debug:ifu_mem_perr_state",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__perr_state",
        ),
        (
            "debug:ifu_mem_err_stop_state",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__err_stop_state",
        ),
        ("debug:exu_flush_final", "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu_flush_final"),
        (
            "debug:dec_tlu_flush_lower_r",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_flush_lower_r",
        ),
        (
            "debug:dec_tlu_flush_path_r",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_flush_path_r",
        ),
        ("debug:tb_ifu_axi_rvalid", "tb_top__DOT__ifu_axi_rvalid"),
        ("debug:tb_ifu_axi_rid", "tb_top__DOT__ifu_axi_rid"),
        ("debug:tb_ifu_axi_rresp", "tb_top__DOT__ifu_axi_rresp"),
        ("debug:tb_ifu_axi_rdata", "tb_top__DOT__ifu_axi_rdata"),
        ("debug:tb_mux_axi_rvalid", "tb_top__DOT__mux_axi_rvalid"),
        ("debug:tb_sb_axi_rdata", "tb_top__DOT__sb_axi_rdata"),
        ("debug:tb_lmem_axi_rvalid", "tb_top__DOT__lmem_axi_rvalid"),
        ("debug:tb_lmem_axi_rdata", "tb_top__DOT__lmem_axi_rdata"),
        ("debug:tb_ifu_axi_arready", "tb_top__DOT__ifu_axi_arready"),
        (
            "debug:ifu_bus_cmd_valid",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__ifu_bus_cmd_valid",
        ),
        (
            "debug:ifu_bus_rd_addr_count",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__bus_rd_addr_count",
        ),
        (
            "debug:ifu_fetch_addr_f",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT____Vcellout__ifu_fetch_addr_f_ff__dout",
        ),
        (
            "debug:ifu_pmp_addr",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_pmp_addr",
        ),
        (
            "debug:ifu_ifc_fetch_req_bf",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT__ifc_fetch_req_bf",
        ),
        (
            "debug:ifu_ifc_fb_write_ns",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT__fb_write_ns",
        ),
        (
            "debug:ifu_ifc_miss_f",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT__miss_f",
        ),
        (
            "debug:ifu_mem_miss_f",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT____Vcellout__miss_f_ff__dout",
        ),
        (
            "debug:ifu_mem_miss_state",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__miss_state",
        ),
        (
            "debug:ifu_mem_miss_state_en",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__miss_state_en",
        ),
        (
            "debug:ifu_mem_write_ic_16_bytes",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__write_ic_16_bytes",
        ),
        (
            "debug:ifu_mem_ic_act_miss_f",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__ic_act_miss_f",
        ),
        (
            "debug:ifu_ifc_fetch_ready",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT____VdfgRegularize_h02fb64cc_0_8",
        ),
        (
            "debug:ifu_ifc_ic_hit_f",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT__ic_hit_f",
        ),
        (
            "debug:ifu_aln_aligndata",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__aligndata",
        ),
        (
            "debug:ifu_aln_alignfromf1",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__alignfromf1",
        ),
        (
            "debug:ifu_aln_brdata0_en",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__genblock1__DOT__brdata0ff__DOT__genblock__DOT__genblock__DOT__dff__DOT__en",
        ),
        (
            "debug:ifu_aln_brdata1_en",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__genblock1__DOT__brdata1ff__DOT__genblock__DOT__genblock__DOT__dff__DOT__en",
        ),
        (
            "debug:ifu_aln_brdata2_en",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__genblock1__DOT__brdata2ff__DOT__genblock__DOT__genblock__DOT__dff__DOT__en",
        ),
        (
            "debug:ifu_aln_shift_f1_f0",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__shift_f1_f0",
        ),
        (
            "debug:ifu_aln_shift_f2_f0",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__shift_f2_f0",
        ),
        (
            "debug:ifu_aln_shift_f2_f1",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__shift_f2_f1",
        ),
        (
            "debug:ifu_aln_sf0val",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__sf0val",
        ),
        (
            "debug:ifu_aln_sf1val",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__sf1val",
        ),
        (
            "debug:ifu_aln_bundle1",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT____Vcellout__bundle1ff__dout",
        ),
        (
            "debug:ifu_aln_bundle2",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT____Vcellout__bundle2ff__dout",
        ),
        (
            "debug:dec_tlu_flush_noredir_r",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_flush_noredir_r",
        ),
        (
            "debug:ifu_ic_fetch_val_f",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ic_fetch_val_f",
        ),
        (
            "debug:ifu_iccm_rd_ecc_single_err",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_iccm_rd_ecc_single_err",
        ),
        (
            "debug:ifu_ic_error_start",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_ic_error_start",
        ),
        (
            "debug:dec_tlu_i0_commit_cmt",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_i0_commit_cmt",
        ),
        (
            "debug:dec_tlu_freeff_dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT____Vcellout__freeff__dout",
        ),
        (
            "debug:dec_tlu_freeff_din",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT__freeff__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din",
        ),
        (
            "debug:ifu_aln_fetch_to_f0",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__fetch_to_f0",
        ),
        (
            "debug:ifu_aln_fetch_to_f1",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__fetch_to_f1",
        ),
        (
            "debug:ifu_aln_fetch_to_f2",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__fetch_to_f2",
        ),
        (
            "debug:ifu_aln_bundle1_din",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT____Vcellinp__bundle1ff__din",
        ),
        (
            "debug:ifu_aln_bundle2_din",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__bundle2ff__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din",
        ),
        ("debug:root_act_triggered", "__VactTriggered"),
        ("debug:root_nba_triggered", "__VnbaTriggered"),
    ):
        required_markers[logical_name] = field

    resolved: dict[str, dict[str, object]] = {}
    missing: list[str] = []
    for logical_name, marker in sorted(required_markers.items()):
        entry = _resolve_layout_marker(layout_by_name, marker)
        if entry is None:
            missing.append(logical_name)
        else:
            resolved[logical_name] = _layout_entry_summary(entry)

    missing_gprs = sorted(expected_gprs.difference(gpr_entries))
    for index, entry in sorted(gpr_entries.items()):
        if not expected_gprs or index in expected_gprs:
            resolved[f"gpr:{index}"] = _layout_entry_summary(entry)
    if missing_gprs:
        missing.append("integer_register_file")

    ready = not missing
    return {
        "schema_version": 1,
        "reviewed": ready,
        "root_layout_member_count": len(layout),
        "mapped_field_count": len(resolved),
        "mapped_fields": resolved,
        "missing_field_markers": list(dict.fromkeys(missing)),
    }


def _veer_el2_root_state_offset_review(mdir: Path | None, repo_root: Path) -> dict[str, object]:
    if mdir is None:
        return {
            "schema_version": 1,
            "reviewed": False,
            "missing_field_markers": ["verilated_mdir"],
        }
    try:
        from compare_vl_hybrid_layout import probe_root_layout  # noqa: PLC0415

        layout = probe_root_layout(mdir)
    except Exception as exc:  # pragma: no cover - compiler/toolchain failures vary.
        return {
            "schema_version": 1,
            "reviewed": False,
            "probe_error": type(exc).__name__,
            "missing_field_markers": ["root_layout_probe"],
        }
    authority = _load_json(repo_root / VEER_EL2_AUTHORITY) or {}
    review = _veer_el2_root_state_offset_review_from_layout(layout=layout, authority=authority)
    review["root_header"] = _display_path(_first_glob_file(mdir, "*___024root.h") or mdir, repo_root)
    return review


def _mapped_root_field_by_name(
    mapped_fields: Mapping[str, object],
    marker: str,
) -> Mapping[str, object] | None:
    for logical_name, raw_entry in mapped_fields.items():
        entry = _as_mapping(raw_entry)
        name = str(entry.get("name", ""))
        if logical_name == marker or name == marker or marker in name:
            return entry
    return None


def _state_image_section_item_count(value: object) -> int:
    if isinstance(value, list):
        return len(value)
    if not isinstance(value, Mapping):
        return 0
    entries_by_bank = value.get("nonzero_entries_by_bank")
    if not isinstance(entries_by_bank, Mapping):
        return 0
    total = 0
    for entries in entries_by_bank.values():
        if isinstance(entries, list):
            total += len(entries)
    return total


def _parse_hex_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    try:
        return int(value, 0)
    except ValueError:
        return None


def _program_staging_entries_review(entries: object) -> dict[str, object]:
    if not isinstance(entries, list):
        return {
            "valid": False,
            "entry_count": 0,
            "missing_context": ["program_staging_entries"],
        }
    missing: list[str] = []
    addresses: list[int] = []
    for index, raw_entry in enumerate(entries):
        entry = _as_mapping(raw_entry)
        addr = _parse_hex_int(entry.get("addr"))
        byte = _parse_hex_int(entry.get("byte_hex"))
        if addr is None:
            missing.append(f"program_staging_entry_{index}.addr")
        else:
            addresses.append(addr)
        if byte is None or byte < 0 or byte > 0xFF:
            missing.append(f"program_staging_entry_{index}.byte_hex")
    return {
        "valid": not missing,
        "entry_count": len(entries),
        "address_min_hex": f"0x{min(addresses):08x}" if addresses else None,
        "address_max_hex": f"0x{max(addresses):08x}" if addresses else None,
        "missing_context": list(dict.fromkeys(missing)),
    }


def _program_staging_flat_byte_window_review(
    entries: object,
    *,
    max_dense_span_bytes: int = 64 * 1024,
) -> dict[str, object]:
    entries_review = _program_staging_entries_review(entries)
    missing = list(_schema_str_list(entries_review, "missing_context"))
    if not isinstance(entries, list):
        return {
            "schema_version": 1,
            "representation": "flat_byte_window",
            "ready": False,
            "entry_count": 0,
            "missing_context": list(dict.fromkeys(missing)),
        }

    byte_values: dict[int, int] = {}
    duplicates: list[str] = []
    for raw_entry in entries:
        entry = _as_mapping(raw_entry)
        addr = _parse_hex_int(entry.get("addr"))
        byte = _parse_hex_int(entry.get("byte_hex"))
        if addr is None or byte is None or byte < 0 or byte > 0xFF:
            continue
        if addr in byte_values:
            duplicates.append(f"0x{addr:08x}")
        byte_values[addr] = byte

    if duplicates:
        missing.append("program_staging_duplicate_byte_address")
    if not byte_values:
        span = 0
        base = None
    else:
        base = min(byte_values)
        span = max(byte_values) - base + 1
    if span > max_dense_span_bytes:
        missing.append("program_staging_flat_window_span_too_large")

    ready = entries_review["valid"] is True and not missing
    return {
        "schema_version": 1,
        "representation": "flat_byte_window",
        "ready": ready,
        "entry_count": len(entries),
        "unique_address_count": len(byte_values),
        "base_addr_hex": f"0x{base:08x}" if base is not None else None,
        "byte_count": span,
        "max_dense_span_bytes": max_dense_span_bytes,
        "density": (len(byte_values) / span) if span else 1.0,
        "missing_context": list(dict.fromkeys(missing)),
    }


def _gpu_ir_contains_assoc_array_map(mdir: Path | None) -> bool | None:
    if mdir is None:
        return None
    for name in ("vl_batch_gpu_opt.ll", "vl_batch_gpu.ptx"):
        path = mdir / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "VlAssocArray" in text or "class.std::map" in text:
            return True
    return False


def _veer_el2_root_image_materializer_review(
    *,
    state_image: Mapping[str, object] | None,
    offset_review: Mapping[str, object],
    repo_root: Path,
    mdir: Path | None = None,
) -> dict[str, object]:
    del repo_root
    mapped_fields = _as_mapping(offset_review.get("mapped_fields"))
    sections = _as_mapping(state_image.get("sections") if state_image is not None else None)
    gpu_ir_assoc_array_map = _gpu_ir_contains_assoc_array_map(mdir)
    materializable_sections: list[str] = []
    blocked_sections: list[str] = []
    missing: list[str] = []
    section_details: dict[str, object] = {}

    if state_image is None:
        missing.append("veer_el2_state_image_json")
    if offset_review.get("reviewed") is not True:
        missing.append("veer_el2_gpu_root_state_image_field_offset_map")

    control_scalars = _as_mapping(sections.get("control_scalars"))
    control_missing = [
        field for field in control_scalars if _mapped_root_field_by_name(mapped_fields, str(field)) is None
    ]
    if control_scalars and not control_missing:
        materializable_sections.append("control_scalars")
    elif control_scalars:
        blocked_sections.append("control_scalars")
        missing.append("veer_el2_control_scalar_root_offsets")
    section_details["control_scalars"] = {
        "entry_count": len(control_scalars),
        "materializable_as_root_bytes": bool(control_scalars) and not control_missing,
        "missing_fields": control_missing,
    }

    for section_name in ("dccm_banks", "iccm_banks"):
        section = _as_mapping(sections.get(section_name))
        prefix = "dccm_bank__DOT__ram_core" if section_name == "dccm_banks" else "iccm_bank__DOT__ram_core"
        bank_fields = [
            entry
            for entry in mapped_fields.values()
            if prefix in str(_as_mapping(entry).get("name", ""))
        ]
        has_shape = bool(bank_fields) and all(
            str(_as_mapping(entry).get("decl_type", "")).startswith("VlUnpacked<QData")
            for entry in bank_fields
        )
        if has_shape:
            materializable_sections.append(section_name)
        else:
            blocked_sections.append(section_name)
            missing.append(f"veer_el2_{section_name}_root_offsets")
        section_details[section_name] = {
            "entry_count": _state_image_section_item_count(section),
            "preload_active": section.get("preload_active"),
            "bank_field_count": len(bank_fields),
            "materializable_as_root_bytes": has_shape,
        }

    for section_name, marker in (
        ("program_staging_lmem", "lmem__DOT__mem"),
        ("program_staging_imem", "imem__DOT__mem"),
    ):
        entries = sections.get(section_name)
        root_field = _mapped_root_field_by_name(mapped_fields, marker)
        decl_type = str(root_field.get("decl_type", "")) if root_field is not None else ""
        entry_count = len(entries) if isinstance(entries, list) else 0
        entries_review = _program_staging_entries_review(entries)
        flat_window_review = _program_staging_flat_byte_window_review(entries)
        is_assoc_array = decl_type.startswith("VlAssocArray")
        is_flat_program_mem = decl_type.startswith("VlGpuFlatByteMem")
        host_initializer_ready = bool(
            entries_review["valid"]
            and root_field is not None
            and is_assoc_array
            and "IData" in decl_type
            and "CData" in decl_type
        )
        flat_program_mem_ready = bool(
            entries_review["valid"]
            and root_field is not None
            and is_flat_program_mem
            and flat_window_review["ready"] is True
        )
        if entry_count == 0:
            materializable_sections.append(section_name)
        elif flat_program_mem_ready:
            materializable_sections.append(section_name)
        elif host_initializer_ready and flat_window_review["ready"] is True and gpu_ir_assoc_array_map is False:
            materializable_sections.append(section_name)
        elif host_initializer_ready:
            blocked_sections.append(section_name)
            missing.append("veer_el2_program_staging_assoc_array_gpu_lowering")
        elif is_assoc_array:
            blocked_sections.append(section_name)
            missing.extend(_schema_str_list(entries_review, "missing_context"))
        else:
            blocked_sections.append(section_name)
            missing.append("veer_el2_program_staging_to_byte_addressable_memory_map")
        section_details[section_name] = {
            "entry_count": entry_count,
            "entry_schema_valid": entries_review["valid"],
            "address_min_hex": entries_review["address_min_hex"],
            "address_max_hex": entries_review["address_max_hex"],
            "root_field": dict(root_field) if root_field is not None else None,
            "host_assoc_array_initializer_ready": host_initializer_ready,
            "root_flat_program_mem_ready": flat_program_mem_ready,
            "gpu_ir_assoc_array_map_detected": gpu_ir_assoc_array_map,
            "gpu_flat_byte_window_review": flat_window_review,
            "materializable_as_root_bytes": entry_count == 0 and root_field is not None,
            "materializable_as_gpu_flat_bytes": (
                entry_count > 0
                and (host_initializer_ready or flat_program_mem_ready)
                and flat_window_review["ready"] is True
                and (gpu_ir_assoc_array_map is False or flat_program_mem_ready)
            ),
            "blocked_by_assoc_array_container": entry_count > 0 and is_assoc_array,
            "blocked_by_gpu_assoc_array_lowering": entry_count > 0 and is_assoc_array and gpu_ir_assoc_array_map is True,
        }

    ready = (
        state_image is not None
        and offset_review.get("reviewed") is True
        and not blocked_sections
        and not missing
    )
    return {
        "schema_version": 1,
        "reviewed": ready,
        "root_image_materialized": False,
        "gpu_ir_assoc_array_map_detected": gpu_ir_assoc_array_map,
        "materializable_sections": list(dict.fromkeys(materializable_sections)),
        "blocked_sections": list(dict.fromkeys(blocked_sections)),
        "missing_build_context": list(dict.fromkeys(missing)),
        "section_details": section_details,
    }


def _veer_el2_gpu_state_image_launch_blocker(
    mdir: Path | None,
    repo_root: Path,
    state_image: Mapping[str, object] | None = None,
) -> dict[str, object] | None:
    if mdir is None:
        return None
    meta_path = mdir / "vl_batch_gpu.meta.json"
    meta = _load_json(meta_path)
    if not isinstance(meta, Mapping):
        return None
    hierarchy_state = meta.get("hierarchy_state")
    if not isinstance(hierarchy_state, Mapping):
        return None
    prelaunch_rejection_required = hierarchy_state.get("prelaunch_rejection_required") is True
    unsafe_covered = hierarchy_state.get("unsafe_syms_gep_covered_by_state_image") is True
    nonflat_assoc_array_detected = hierarchy_state.get("nonflat_assoc_array_detected") is True
    if (
        not prelaunch_rejection_required
        and unsafe_covered
        and not nonflat_assoc_array_detected
    ):
        return None
    offset_review = _veer_el2_root_state_offset_review(mdir, repo_root)
    offset_map_ready = offset_review.get("reviewed") is True
    missing = []
    if prelaunch_rejection_required:
        missing.append("veer_el2_gpu_root_state_image_prelaunch_rejection")
    if not unsafe_covered:
        missing.append("veer_el2_gpu_unsafe_syms_gep_coverage")
    if nonflat_assoc_array_detected:
        missing.append("veer_el2_program_staging_assoc_array_gpu_lowering")
    if not offset_map_ready:
        missing.append("veer_el2_gpu_root_state_image_field_offset_map")
    materializer_review = None
    if state_image is not None:
        materializer_review = _veer_el2_root_image_materializer_review(
            state_image=state_image,
            offset_review=offset_review,
            repo_root=repo_root,
            mdir=mdir,
        )
        if materializer_review.get("reviewed") is not True:
            missing.extend(_schema_str_list(materializer_review, "missing_build_context"))
            missing.append("veer_el2_gpu_root_state_image_materializer")
    else:
        missing.append("veer_el2_gpu_root_state_image_materializer")
    review = {
        "schema_version": 1,
        "meta_path": _display_path(meta_path, repo_root),
        "state_image_kind": hierarchy_state.get("state_image_kind"),
        "root_storage_size": hierarchy_state.get("root_storage_size"),
        "syms_storage_size": hierarchy_state.get("syms_storage_size"),
        "root_offset_in_syms": hierarchy_state.get("root_offset_in_syms"),
        "unsafe_syms_gep_count": hierarchy_state.get("unsafe_syms_gep_count"),
        "unsafe_syms_gep_covered_by_state_image": hierarchy_state.get("unsafe_syms_gep_covered_by_state_image"),
        "prelaunch_rejection_required": hierarchy_state.get("prelaunch_rejection_required"),
        "nonflat_assoc_array_detected": hierarchy_state.get("nonflat_assoc_array_detected"),
        "nonflat_assoc_array_markers": hierarchy_state.get("nonflat_assoc_array_markers"),
        "assoc_array_gpu_lowering_supported": hierarchy_state.get("assoc_array_gpu_lowering_supported"),
        "metadata_source": hierarchy_state.get("metadata_source"),
        "root_state_image_field_offset_review": offset_review,
        "missing_build_context": list(dict.fromkeys(missing)),
    }
    if materializer_review is not None:
        review["root_state_image_materializer_review"] = materializer_review
    return review


def _build_vl_gpu_with_veer_el2_auto_syms_state_image(
    mdir: Path,
    *,
    build_vl_gpu_fn=None,
) -> dict[str, object]:
    """Build VeeR once as root-image, then auto-promote to __Syms image if needed."""
    if build_vl_gpu_fn is None:
        from build_vl_gpu import build_vl_gpu as build_vl_gpu_fn  # noqa: PLC0415

    review: dict[str, object] = {
        "schema_version": 1,
        "mode": "veer_el2_auto_syms_state_image_build",
        "initial_build_invoked": True,
        "syms_rebuild_invoked": False,
    }
    build_vl_gpu_fn(mdir, force=True)
    meta = _load_json(mdir / "vl_batch_gpu.meta.json")
    hierarchy_state = _as_mapping(_as_mapping(meta).get("hierarchy_state"))
    review["initial_state_image_kind"] = hierarchy_state.get("state_image_kind")
    review["initial_prelaunch_rejection_required"] = hierarchy_state.get("prelaunch_rejection_required")
    review["initial_unsafe_syms_gep_covered_by_state_image"] = hierarchy_state.get(
        "unsafe_syms_gep_covered_by_state_image"
    )
    review["initial_unsafe_syms_gep_count"] = hierarchy_state.get("unsafe_syms_gep_count")
    needs_syms_rebuild = (
        hierarchy_state.get("prelaunch_rejection_required") is True
        and hierarchy_state.get("unsafe_syms_gep_covered_by_state_image") is not True
    )
    syms_size = hierarchy_state.get("syms_storage_size")
    root_offset = hierarchy_state.get("root_offset_in_syms")
    if not needs_syms_rebuild or not isinstance(syms_size, int) or not isinstance(root_offset, int):
        review["syms_rebuild_reason"] = (
            "not_required" if not needs_syms_rebuild else "missing_syms_size_or_root_offset"
        )
        return review

    review["syms_rebuild_invoked"] = True
    review["syms_storage_size"] = syms_size
    review["state_root_offset"] = root_offset
    build_vl_gpu_fn(
        mdir,
        force=True,
        syms_state_image=True,
        syms_storage_size=syms_size,
        state_root_offset=root_offset,
    )
    final_meta = _load_json(mdir / "vl_batch_gpu.meta.json")
    final_hierarchy = _as_mapping(_as_mapping(final_meta).get("hierarchy_state"))
    review["final_state_image_kind"] = final_hierarchy.get("state_image_kind")
    review["final_prelaunch_rejection_required"] = final_hierarchy.get("prelaunch_rejection_required")
    review["final_unsafe_syms_gep_covered_by_state_image"] = final_hierarchy.get(
        "unsafe_syms_gep_covered_by_state_image"
    )
    review["final_unsafe_syms_gep_count"] = final_hierarchy.get("unsafe_syms_gep_count")
    return review


def _prepare_direct_shim_sanitized_init_state(
    *,
    root: Path,
    launch_template: str,
    mdir: Path,
) -> tuple[bool, str | None, int, str | None]:
    from hybrid_template_runner import load_template_plan  # noqa: PLC0415
    from run_vl_hybrid_state_sanitize import _prepare_sanitized_init_state  # noqa: PLC0415

    template_plan = load_template_plan(root / launch_template, shape="1x1")
    init_state = template_plan.cpu_init_state
    if not init_state.is_file():
        return False, "missing_direct_shim_source_init_state", 0, None

    prepared = _prepare_sanitized_init_state(mdir=mdir, init_state=init_state)
    if prepared is None:
        return False, "direct_shim_init_state_sanitize_no_layout_or_regions", 0, None

    sanitized_tmp, applied = prepared
    sanitized_out = mdir / DIRECT_SHIM_SANITIZED_INIT_STATE_NAME
    try:
        sanitized_out.write_bytes(sanitized_tmp.read_bytes())
    finally:
        sanitized_tmp.unlink(missing_ok=True)
    return True, None, len(applied), _display_path(sanitized_out, root)


def _report(
    *,
    status: str,
    recognition: Mapping[str, object],
    mdir_display: str | None,
    mdir_verilated: bool,
    missing_context: list[str],
    diagnostic: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": status,
        "build_plan_ready": status == STATUS_BUILD_PLAN_READY,
        "recognition": dict(recognition),
        "target": recognition.get("target"),
        "top_module": recognition.get("top_module"),
        "launch_template": recognition.get("launch_template"),
        "mdir": mdir_display,
        "mdir_verilated": mdir_verilated,
        "fail_closed": True,
        "cpu_as_gpu_fallback": False,
        "gpu_execution_claimed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "missing_build_context": missing_context,
        "diagnostic": diagnostic,
        "non_claims": list(NON_CLAIMS),
    }


def plan_native_sidecar_build(
    *,
    filelist_path: str | Path,
    top_module: str,
    repo_root: Path | None = None,
    registry_path: str | Path | None = None,
    mdir_override: str | Path | None = None,
) -> dict[str, object]:
    """Recognize the closure and resolve the make mdir without running anything."""
    root = (repo_root or Path.cwd()).resolve()
    recognition = recognize_verilator_native_known_closure(
        filelist_path=filelist_path,
        top_module=top_module,
        repo_root=root,
        registry_path=registry_path,
    )
    if recognition["status"] != STATUS_RECOGNIZED:
        return _report(
            status=STATUS_BLOCKED_UNRECOGNIZED,
            recognition=recognition,
            mdir_display=None,
            mdir_verilated=False,
            missing_context=["recognized_known_closure"],
            diagnostic="native sidecar build is blocked: the filelist/top pair is not a tracked known closure",
        )

    if mdir_override is not None:
        mdir = Path(mdir_override)
        if not mdir.is_absolute():
            mdir = Path.cwd() / mdir
        mdir_value = mdir.as_posix()
    else:
        template = _load_json(root / str(recognition["launch_template"]))
        build = template.get("build") if isinstance(template, Mapping) else None
        mdir_value = build.get("mdir") if isinstance(build, Mapping) else None
        if not isinstance(mdir_value, str) or not mdir_value:
            return _report(
                status=STATUS_BLOCKED_TEMPLATE,
                recognition=recognition,
                mdir_display=None,
                mdir_verilated=False,
                missing_context=["launch_template.build.mdir"],
                diagnostic="native sidecar build is blocked: the recognized closure template has no build mdir",
            )

    mdir = Path(mdir_value)
    if not mdir.is_absolute():
        mdir = root / mdir
    mdir_display = _display_path(mdir, root)
    mdir_verilated = _classes_mk_present(mdir)
    if not mdir_verilated:
        return _report(
            status=STATUS_BLOCKED_MISSING_MDIR,
            recognition=recognition,
            mdir_display=mdir_display,
            mdir_verilated=False,
            missing_context=["verilated_mdir_classes_mk"],
            diagnostic="native sidecar build is blocked: the verilated mdir has no *_classes.mk yet",
        )

    return _report(
        status=STATUS_BUILD_PLAN_READY,
        recognition=recognition,
        mdir_display=mdir_display,
        mdir_verilated=True,
        missing_context=[],
        diagnostic="recognized closure resolved to a verilated mdir ready for sidecar make-time prep",
    )


def run_native_sidecar_build(
    *,
    filelist_path: str | Path,
    top_module: str,
    repo_root: Path | None = None,
    registry_path: str | Path | None = None,
    mdir_override: str | Path | None = None,
    shape: str = "64x1",
    template_runner=None,
) -> dict[str, object]:
    """Plan, then delegate a recognized closure to the reviewed template flow (FC-055)."""
    root = (repo_root or Path.cwd()).resolve()
    plan = plan_native_sidecar_build(
        filelist_path=filelist_path,
        top_module=top_module,
        repo_root=root,
        registry_path=registry_path,
        mdir_override=mdir_override,
    )
    plan["template_flow_shape"] = shape
    plan["template_flow_invoked"] = False
    plan["template_flow_passed"] = False
    plan["diagnostic_native_exe_is_cpu_only"] = (
        "the make-emitted --main executable is a CPU binary; GPU execution and "
        "coverage-output equivalence are produced by the delegated template flow"
    )
    if plan["status"] != STATUS_BUILD_PLAN_READY:
        return plan

    launch_template_value = plan.get("launch_template")
    if not isinstance(launch_template_value, str) or not launch_template_value:
        plan["status"] = STATUS_BLOCKED_TEMPLATE
        plan["build_plan_ready"] = False
        plan["missing_build_context"] = ["launch_template"]
        plan["diagnostic"] = (
            "native sidecar run is blocked: the recognized closure has no "
            "reviewed runtime launch template"
        )
        return plan

    launch_template = launch_template_value
    if template_runner is None:
        from run_hybrid_template import main as template_runner  # noqa: PLC0415

    returncode = template_runner([str(root / launch_template), "--shape", shape])
    plan["template_flow_invoked"] = True
    plan["template_flow_returncode"] = int(returncode)
    plan["template_flow_passed"] = returncode == 0
    return plan


def inspect_veer_el2_state_layout(
    *,
    filelist_path: str | Path,
    top_module: str,
    repo_root: Path | None = None,
    registry_path: str | Path | None = None,
    mdir_override: str | Path | None = None,
    rtlmeter_program_hex: str | Path | None = None,
) -> dict[str, object]:
    """Inspect the tracked RTLMeter VeeR-EL2 state surface without claiming GPU readiness."""
    root = (repo_root or Path.cwd()).resolve()
    plan = plan_native_sidecar_build(
        filelist_path=filelist_path,
        top_module=top_module,
        repo_root=root,
        registry_path=registry_path,
        mdir_override=mdir_override,
    )
    plan["mode"] = "inspect_veer_el2_state_layout"
    plan["state_layout_inspection_performed"] = False
    plan["state_layout_ready"] = False
    if plan["status"] != STATUS_BUILD_PLAN_READY:
        return plan
    if plan.get("target") != VEER_EL2_RTL_METER_TARGET:
        plan["status"] = STATUS_BLOCKED_UNRECOGNIZED
        plan["build_plan_ready"] = False
        plan["missing_build_context"] = ["rtlmeter_veer_el2_default_hello_target"]
        plan["diagnostic"] = "VeeR-EL2 state layout inspection is scoped to the tracked default/hello closure"
        return plan
    return _veer_el2_state_layout_inspection(
        root=root,
        plan=plan,
        rtlmeter_program_hex=rtlmeter_program_hex,
    )


def materialize_veer_el2_state_image(
    *,
    filelist_path: str | Path,
    top_module: str,
    state_image_out: str | Path,
    repo_root: Path | None = None,
    registry_path: str | Path | None = None,
    mdir_override: str | Path | None = None,
    rtlmeter_program_hex: str | Path | None = None,
) -> dict[str, object]:
    """Materialize the reviewed VeeR-EL2 extracted preload state image."""
    root = (repo_root or Path.cwd()).resolve()
    inspection = inspect_veer_el2_state_layout(
        filelist_path=filelist_path,
        top_module=top_module,
        repo_root=root,
        registry_path=registry_path,
        mdir_override=mdir_override,
        rtlmeter_program_hex=rtlmeter_program_hex,
    )
    raw_out = Path(state_image_out)
    out = raw_out if raw_out.is_absolute() else root / raw_out
    return _materialize_veer_el2_state_image(
        root=root,
        inspection=inspection,
        state_image_out=out,
    )


def _load_veer_el2_state_image(path: Path) -> tuple[Mapping[str, object] | None, list[str]]:
    image = _load_json(path)
    missing: list[str] = []
    if image is None:
        return None, ["veer_el2_state_image_json"]
    checks = (
        ("schema_role", "veer_el2_extracted_preload_state_image"),
        ("target", VEER_EL2_RTL_METER_TARGET),
        ("state_image_kind", VEER_EL2_STATE_IMAGE_KIND),
    )
    for key, expected in checks:
        if image.get(key) != expected:
            missing.append(f"state_image.{key}")
    sections = image.get("sections")
    if not isinstance(sections, Mapping):
        missing.append("state_image.sections")
    else:
        for name in (
            "program_staging_lmem",
            "program_staging_imem",
            "dccm_banks",
            "iccm_banks",
            "control_scalars",
        ):
            if name not in sections:
                missing.append(f"state_image.sections.{name}")
    return image, missing


def _executable_ready(path: Path | None) -> bool:
    return path is not None and path.is_file() and path.stat().st_mode & 0o111 != 0


def _reviewed_veer_el2_sidecar_executable(
    *,
    executable: Path | None,
    repo_root: Path,
) -> tuple[bool, dict[str, object]]:
    executable_ready = _executable_ready(executable)
    review_path = executable.with_name(f"{executable.name}.review.json") if executable is not None else None
    review = _load_json(review_path) if review_path is not None and review_path.is_file() else None
    missing: list[str] = []
    if executable is None:
        missing.append("sidecar_executable")
    elif not executable_ready:
        missing.append("sidecar_executable.executable")
    if review_path is None or not review_path.is_file():
        missing.append("sidecar_executable.review_manifest")
    if not isinstance(review, Mapping):
        if review_path is not None and review_path.is_file():
            missing.append("sidecar_executable.review_manifest_json")
    else:
        expected = {
            "schema_role": VEER_EL2_SIDECAR_EXECUTABLE_REVIEW_ROLE,
            "target": VEER_EL2_RTL_METER_TARGET,
            "executable_path": _display_path(executable, repo_root) if executable is not None else None,
            "state_image_env": VEER_EL2_SIDECAR_STATE_IMAGE_ENV,
            "execute_dir_env": VEER_EL2_SIDECAR_EXECUTE_DIR_ENV,
        }
        for key, value in expected.items():
            if review.get(key) != value:
                missing.append(f"sidecar_executable.review_manifest.{key}")
        if review.get("emits_rtlmeter_observables") is not True:
            missing.append("sidecar_executable.review_manifest.emits_rtlmeter_observables")
        if review.get("cpu_as_gpu_fallback_allowed") is not False:
            missing.append("sidecar_executable.review_manifest.cpu_as_gpu_fallback_allowed")
        if review.get("copies_cpu_observables") is not False:
            missing.append("sidecar_executable.review_manifest.copies_cpu_observables")
    reviewed = executable_ready and not missing
    return reviewed, {
        "schema_version": 1,
        "schema_role": VEER_EL2_SIDECAR_EXECUTABLE_REVIEW_ROLE,
        "review_manifest_path": _display_path(review_path, repo_root) if review_path is not None else None,
        "reviewed": reviewed,
        "executable_ready": executable_ready,
        "missing_review_context": list(dict.fromkeys(missing)),
    }


def _use_in_process_veer_el2_sidecar(executable: Path | None, repo_root: Path) -> bool:
    if executable is None:
        return False
    return executable.resolve(strict=False) == (repo_root / VEER_EL2_PYTHON_SIDECAR_EXECUTABLE).resolve(strict=False)


def _run_in_process_veer_el2_sidecar(root: Path, env: Mapping[str, str]) -> subprocess.CompletedProcess[str]:
    from veer_el2_sidecar_executable import run_sidecar

    old_env = os.environ.copy()
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        os.environ.clear()
        os.environ.update(env)
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            returncode = int(run_sidecar(root))
    except BaseException as exc:
        print(f"{type(exc).__name__}: {exc}", file=stderr)
        returncode = 1
    finally:
        os.environ.clear()
        os.environ.update(old_env)
    return subprocess.CompletedProcess(
        [str(VEER_EL2_PYTHON_SIDECAR_EXECUTABLE)],
        returncode,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )


def run_veer_el2_sidecar_execution_bridge(
    *,
    state_image_path: str | Path,
    cpu_execute_dir: str | Path,
    sidecar_execute_dir: str | Path,
    sidecar_executable: str | Path | None = None,
    mdir: str | Path | None = None,
    sidecar_env: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
    runner=subprocess.run,
) -> dict[str, object]:
    """Run the reviewed VeeR-EL2 sidecar observable bridge when an executable exists."""
    total_started = time.perf_counter()
    phase_started = total_started
    phase_timing_s: dict[str, float] = {}

    def mark_phase(name: str) -> None:
        nonlocal phase_started
        now = time.perf_counter()
        phase_timing_s[name] = round(now - phase_started, 6)
        phase_started = now

    root = (repo_root or Path.cwd()).resolve()
    raw_state_image = Path(state_image_path)
    state_image = raw_state_image if raw_state_image.is_absolute() else root / raw_state_image
    raw_cpu_execute_dir = Path(cpu_execute_dir)
    cpu_dir = raw_cpu_execute_dir if raw_cpu_execute_dir.is_absolute() else root / raw_cpu_execute_dir
    raw_sidecar_execute_dir = Path(sidecar_execute_dir)
    sidecar_dir = raw_sidecar_execute_dir if raw_sidecar_execute_dir.is_absolute() else root / raw_sidecar_execute_dir
    raw_executable = Path(sidecar_executable) if sidecar_executable else None
    executable = (
        raw_executable
        if raw_executable is not None and raw_executable.is_absolute()
        else (root / raw_executable if raw_executable is not None else None)
    )
    raw_mdir = Path(mdir) if mdir is not None else None
    gpu_mdir = (
        raw_mdir
        if raw_mdir is not None and raw_mdir.is_absolute()
        else (root / raw_mdir if raw_mdir is not None else None)
    )
    image, image_missing = _load_veer_el2_state_image(state_image)
    cpu_missing = required_observable_files_missing(cpu_dir, "cpu")
    gpu_state_image_blocker = _veer_el2_gpu_state_image_launch_blocker(gpu_mdir, root, image)
    executable_ready = _executable_ready(executable)
    executable_reviewed, executable_review = _reviewed_veer_el2_sidecar_executable(
        executable=executable,
        repo_root=root,
    )
    mark_phase("preflight_s")
    missing_context = [
        *image_missing,
        *cpu_missing,
        *(gpu_state_image_blocker["missing_build_context"] if gpu_state_image_blocker is not None else []),
        *(["reviewed_veer_el2_sidecar_executable"] if not executable_reviewed else []),
    ]
    blocked_by_gpu_state = gpu_state_image_blocker is not None
    report: dict[str, object] = {
        "schema_version": 1,
        "surface": SURFACE,
        "mode": "run_veer_el2_sidecar_execution_bridge",
        "status": (
            STATUS_BLOCKED_VEER_EL2_GPU_STATE_IMAGE_LAUNCH
            if blocked_by_gpu_state
            else (
                STATUS_BLOCKED_VEER_EL2_SIDECAR_EXECUTABLE
                if not executable_reviewed
                else STATUS_BLOCKED_VEER_EL2_SIDECAR_OBSERVABLES
            )
        ),
        "target": VEER_EL2_RTL_METER_TARGET,
        "state_image_path": _display_path(state_image, root),
        "state_image_loaded": image is not None and not image_missing,
        "state_image_kind": image.get("state_image_kind") if isinstance(image, Mapping) else None,
        "gpu_mdir": _display_path(gpu_mdir, root) if gpu_mdir is not None else None,
        "gpu_state_image_launch_review": gpu_state_image_blocker,
        "cpu_execute_dir": _display_path(cpu_dir, root),
        "sidecar_execute_dir": _display_path(sidecar_dir, root),
        "sidecar_executable": _display_path(executable, root) if executable is not None else None,
        "sidecar_executable_ready": executable_ready,
        "sidecar_executable_review": executable_review,
        "sidecar_bridge_invoked": False,
        "sidecar_executable_invocation_mode": None,
        "sidecar_observables_ready": False,
        "comparison": None,
        "fail_closed": True,
        "cpu_as_gpu_fallback": False,
        "gpu_execution_claimed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "missing_build_context": list(dict.fromkeys(missing_context)),
        "non_claims": [
            "the bridge does not copy CPU observables into the sidecar output",
            "stdout/cycles comparison is correctness evidence only after a reviewed sidecar executable produces the outputs",
            "no timing, speedup, or usefulness claim is made",
        ],
    }
    if missing_context:
        phase_timing_s["total_bridge_s"] = round(time.perf_counter() - total_started, 6)
        report["phase_timing_s"] = phase_timing_s
        report["diagnostic"] = (
            "VeeR-EL2 GPU artifact requires root state-image coverage before a sidecar executable can launch it"
            if blocked_by_gpu_state
            else "VeeR-EL2 sidecar bridge is blocked before execution"
        )
        return report

    sidecar_dir.mkdir(parents=True, exist_ok=True)
    for stale in (sidecar_dir / "_execute" / "stdout.log", sidecar_dir / "_rtlmeter_cycles.txt"):
        if stale.is_file():
            stale.unlink()
    env = os.environ.copy()
    env.update(
        {
            VEER_EL2_SIDECAR_STATE_IMAGE_ENV: state_image.as_posix(),
            VEER_EL2_SIDECAR_EXECUTE_DIR_ENV: sidecar_dir.as_posix(),
        }
    )
    if sidecar_env:
        env.update({str(key): str(value) for key, value in sidecar_env.items()})
    invocation_mode = "subprocess_executable"
    if _use_in_process_veer_el2_sidecar(executable, root):
        invocation_mode = "in_process_veer_el2_sidecar"
        completed = _run_in_process_veer_el2_sidecar(root, env)
    else:
        completed = runner([executable.as_posix()], cwd=root, env=env, text=True, capture_output=True)
    mark_phase("sidecar_executable_wall_s")
    report["sidecar_bridge_invoked"] = True
    report["sidecar_executable_invocation_mode"] = invocation_mode
    report["sidecar_bridge_returncode"] = int(completed.returncode)
    report["sidecar_bridge_stdout_sha256"] = _sha256_bytes(str(completed.stdout).encode("utf-8"))
    report["sidecar_bridge_stderr_sha256"] = _sha256_bytes(str(completed.stderr).encode("utf-8"))
    if int(completed.returncode) != 0:
        phase_timing_s["total_bridge_s"] = round(time.perf_counter() - total_started, 6)
        report["phase_timing_s"] = phase_timing_s
        report["status"] = STATUS_BLOCKED_VEER_EL2_SIDECAR_RUN_FAILED
        report["missing_build_context"] = ["veer_el2_sidecar_execution_bridge_passed"]
        report["diagnostic"] = "VeeR-EL2 sidecar bridge executable returned nonzero"
        return report

    sidecar_missing = required_observable_files_missing(sidecar_dir, "sidecar")
    mark_phase("check_sidecar_observables_s")
    if sidecar_missing:
        phase_timing_s["total_bridge_s"] = round(time.perf_counter() - total_started, 6)
        report["phase_timing_s"] = phase_timing_s
        report["status"] = STATUS_BLOCKED_VEER_EL2_SIDECAR_OBSERVABLES
        report["missing_build_context"] = sidecar_missing
        report["diagnostic"] = "VeeR-EL2 sidecar bridge did not emit the required RTLMeter observables"
        return report

    report["sidecar_observables_ready"] = True
    comparison = compare_rtlmeter_observables(cpu_dir, sidecar_dir)
    mark_phase("compare_observables_s")
    report["comparison"] = comparison
    report["status"] = (
        STATUS_VEER_EL2_SIDECAR_COMPARE_PASSED
        if comparison.get("status") == "passed"
        else STATUS_VEER_EL2_SIDECAR_COMPARE_FAILED
    )
    report["missing_build_context"] = [] if comparison.get("status") == "passed" else ["rtlmeter_stdout_cycles_equivalence"]
    report["sidecar_execution_claimed"] = comparison.get("status") == "passed"
    report["gpu_execution_claimed"] = False
    report["diagnostic"] = (
        "VeeR-EL2 sidecar stdout/cycles comparison passed; timing/usefulness is still unmeasured"
        if comparison.get("status") == "passed"
        else "VeeR-EL2 sidecar stdout/cycles comparison failed"
    )
    phase_timing_s["total_bridge_s"] = round(time.perf_counter() - total_started, 6)
    report["phase_timing_s"] = phase_timing_s
    return report


def prepare_direct_shim_smoke(
    *,
    filelist_path: str | Path,
    top_module: str,
    repo_root: Path | None = None,
    registry_path: str | Path | None = None,
    mdir_override: str | Path | None = None,
) -> dict[str, object]:
    """FC-059 make-time prep for the direct executable sidecar shim."""
    plan = plan_native_sidecar_build(
        filelist_path=filelist_path,
        top_module=top_module,
        repo_root=repo_root,
        registry_path=registry_path,
        mdir_override=mdir_override,
    )
    plan["mode"] = "prepare_direct_shim_smoke"
    plan["template_flow_invoked"] = False
    plan["run_hybrid_template_invoked"] = False
    plan["direct_shim_link_prepared"] = plan["status"] == STATUS_BUILD_PLAN_READY
    plan["runtime_evidence_written_by"] = "native_sidecar_shim executable at run time, not this build-time step"
    if plan["status"] == STATUS_BUILD_PLAN_READY:
        plan["diagnostic"] = "recognized closure is ready to link the direct executable shim smoke object"
    return plan


def build_direct_shim_smoke(
    *,
    filelist_path: str | Path,
    top_module: str,
    repo_root: Path | None = None,
    registry_path: str | Path | None = None,
    mdir_override: str | Path | None = None,
    gpu_builder=None,
    init_state_preparer=None,
) -> dict[str, object]:
    """FC-061 make-time build plus guard for direct executable kernel-launch smoke."""
    root = (repo_root or Path.cwd()).resolve()
    plan = prepare_direct_shim_smoke(
        filelist_path=filelist_path,
        top_module=top_module,
        repo_root=root,
        registry_path=registry_path,
        mdir_override=mdir_override,
    )
    plan["mode"] = "build_direct_shim_smoke"
    plan["gpu_artifact_build_invoked"] = False
    plan["gpu_artifact_build_passed"] = False
    plan["gpu_artifact_supported_for_direct_shim"] = False
    plan["direct_shim_init_state_prepared"] = False
    if plan["status"] != STATUS_BUILD_PLAN_READY:
        return plan

    raw_mdir = Path(str(plan["mdir"]))
    mdir = raw_mdir if raw_mdir.is_absolute() else root / raw_mdir
    if gpu_builder is None:
        if plan.get("target") == VEER_EL2_RTL_METER_TARGET:
            gpu_builder = _build_vl_gpu_with_veer_el2_auto_syms_state_image
        else:
            from build_vl_gpu import build_vl_gpu  # noqa: PLC0415

            def gpu_builder(path: Path) -> None:
                build_vl_gpu(path, force=True)

    plan["gpu_artifact_build_invoked"] = True
    try:
        gpu_build_review = gpu_builder(mdir)
    except Exception as exc:  # pragma: no cover - concrete exception types vary by toolchain.
        plan["status"] = STATUS_BLOCKED_GPU_ARTIFACT_BUILD_FAILED
        plan["build_plan_ready"] = False
        plan["gpu_artifact_build_error"] = type(exc).__name__
        plan["diagnostic"] = "native sidecar GPU artifact build failed before direct shim link"
        plan["missing_build_context"] = ["gpu_artifact_build"]
        return plan

    plan["gpu_artifact_build_passed"] = True
    if isinstance(gpu_build_review, Mapping):
        plan["gpu_artifact_build_review"] = dict(gpu_build_review)
    unsupported_compatibility = _unsupported_gpu_artifact_compatibility(mdir)
    if unsupported_compatibility is not None:
        plan["status"] = STATUS_BLOCKED_UNSUPPORTED_ARTIFACT
        plan["build_plan_ready"] = False
        plan["direct_shim_link_prepared"] = False
        plan["gpu_artifact_supported_for_direct_shim"] = False
        plan["gpu_artifact_compatibility_status"] = unsupported_compatibility.get("status")
        plan["unsupported_gpu_artifact_reason"] = unsupported_compatibility.get("status")
        plan["trigger_vector_artifact_detected"] = unsupported_compatibility.get(
            "trigger_vector_artifact_detected",
            False,
        )
        markers = unsupported_compatibility.get("trigger_vector_markers", [])
        plan["trigger_vector_markers"] = list(markers) if isinstance(markers, list) else []
        for key in (
            "observed_storage_size",
            "known_good_storage_size_for_fc061",
            "observed_verilator_artifact_family",
        ):
            if key in unsupported_compatibility:
                plan[key] = unsupported_compatibility[key]
        plan["missing_build_context"] = ["direct_shim_supported_gpu_artifact"]
        plan["diagnostic"] = (
            "native sidecar build is blocked: this Verilator/GPU artifact shape "
            "uses trigger-vector state that the FC-061 direct shim path has not "
            "proved safe to launch"
        )
        return plan

    plan["gpu_artifact_supported_for_direct_shim"] = True
    plan["gpu_artifact_compatibility_status"] = "supported_for_fc061_direct_kernel_launch_smoke"
    if plan.get("target") == VEER_EL2_RTL_METER_TARGET:
        gpu_state_image_blocker = _veer_el2_gpu_state_image_launch_blocker(mdir, root)
        plan["gpu_state_image_launch_review"] = gpu_state_image_blocker
        plan["status"] = (
            STATUS_BLOCKED_VEER_EL2_GPU_STATE_IMAGE_LAUNCH
            if gpu_state_image_blocker is not None
            else STATUS_BLOCKED_VEER_EL2_SIDECAR_EXECUTABLE
        )
        plan["build_plan_ready"] = False
        plan["direct_shim_link_prepared"] = False
        plan["missing_build_context"] = list(
            dict.fromkeys([
                *(gpu_state_image_blocker["missing_build_context"] if gpu_state_image_blocker is not None else []),
                "reviewed_veer_el2_sidecar_executable",
            ])
        )
        if gpu_state_image_blocker is not None:
            plan["diagnostic"] = (
                "native VeeR-EL2 sidecar build produced a GPU artifact, but its hierarchy-state metadata "
                "requires root state-image offset/coverage work before the executable may launch it"
            )
        else:
            plan["diagnostic"] = (
                "native VeeR-EL2 sidecar build produced a GPU artifact, but the "
                "reviewed executable that consumes the extracted state image and "
                "emits RTLMeter stdout/cycles observables is not implemented yet"
            )
        return plan
    if init_state_preparer is None:
        init_state_preparer = _prepare_direct_shim_sanitized_init_state
    try:
        init_prepared, init_error, sanitized_regions, init_path = init_state_preparer(
            root=root,
            launch_template=str(plan["launch_template"]),
            mdir=mdir,
        )
    except Exception as exc:  # pragma: no cover - sanitizer failures are environment-specific.
        init_prepared = False
        init_error = type(exc).__name__
        sanitized_regions = 0
        init_path = None
    if not init_prepared:
        plan["status"] = STATUS_BLOCKED_INIT_STATE_SANITIZE_FAILED
        plan["build_plan_ready"] = False
        plan["direct_shim_link_prepared"] = False
        plan["direct_shim_init_state_error"] = init_error or "direct_shim_init_state_unprepared"
        plan["missing_build_context"] = ["direct_shim_sanitized_init_state"]
        plan["diagnostic"] = (
            "native sidecar build is blocked: the direct shim requires a sanitized "
            "1x1 init-state image before launching the GPU kernel"
        )
        return plan

    plan["direct_shim_init_state_prepared"] = True
    plan["direct_shim_init_state_path"] = init_path
    plan["direct_shim_init_state_sanitized_regions"] = sanitized_regions
    plan["diagnostic"] = "recognized closure built a GPU artifact supported by the direct shim smoke"
    return plan


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "plan",
            "run",
            "prepare-direct-shim-smoke",
            "build-direct-shim-smoke",
            "inspect-veer-el2-state-layout",
            "materialize-veer-el2-state-image",
            "run-veer-el2-sidecar-bridge",
        ),
    )
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--filelist", required=True)
    parser.add_argument("--top-module", required=True)
    parser.add_argument("--mdir", default=None)
    parser.add_argument("--registry", default=None)
    parser.add_argument("--summary-out", default=None)
    parser.add_argument("--state-image-out", default=None)
    parser.add_argument("--state-image", default=None)
    parser.add_argument("--cpu-execute-dir", default=None)
    parser.add_argument("--sidecar-execute-dir", default=None)
    parser.add_argument("--sidecar-executable", default=None)
    parser.add_argument("--rtlmeter-program-hex", default=None)
    parser.add_argument("--sim-accel", default=None)
    parser.add_argument("--sim-accel-states", default=None)
    parser.add_argument("--sim-accel-steps", default=None)
    return parser


def _shape_from_args(states: str | None, steps: str | None) -> str:
    n = int(states) if states else 64
    s = int(steps) if steps else 1
    return f"{n}x{s}"


def main(argv: list[str] | None = None) -> int:
    import json as _json

    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()
    if args.command == "plan":
        report = plan_native_sidecar_build(
            filelist_path=args.filelist,
            top_module=args.top_module,
            repo_root=repo_root,
            registry_path=args.registry,
            mdir_override=args.mdir,
        )
    elif args.command == "prepare-direct-shim-smoke":
        report = prepare_direct_shim_smoke(
            filelist_path=args.filelist,
            top_module=args.top_module,
            repo_root=repo_root,
            registry_path=args.registry,
            mdir_override=args.mdir,
        )
    elif args.command == "build-direct-shim-smoke":
        report = build_direct_shim_smoke(
            filelist_path=args.filelist,
            top_module=args.top_module,
            repo_root=repo_root,
            registry_path=args.registry,
            mdir_override=args.mdir,
        )
    elif args.command == "inspect-veer-el2-state-layout":
        report = inspect_veer_el2_state_layout(
            filelist_path=args.filelist,
            top_module=args.top_module,
            repo_root=repo_root,
            registry_path=args.registry,
            mdir_override=args.mdir,
            rtlmeter_program_hex=args.rtlmeter_program_hex,
        )
    elif args.command == "materialize-veer-el2-state-image":
        if not args.state_image_out:
            raise SystemExit("--state-image-out is required for materialize-veer-el2-state-image")
        report = materialize_veer_el2_state_image(
            filelist_path=args.filelist,
            top_module=args.top_module,
            repo_root=repo_root,
            registry_path=args.registry,
            mdir_override=args.mdir,
            rtlmeter_program_hex=args.rtlmeter_program_hex,
            state_image_out=args.state_image_out,
        )
    elif args.command == "run-veer-el2-sidecar-bridge":
        missing_args = [
            name
            for name, value in (
                ("--state-image", args.state_image),
                ("--cpu-execute-dir", args.cpu_execute_dir),
                ("--sidecar-execute-dir", args.sidecar_execute_dir),
            )
            if not value
        ]
        if missing_args:
            raise SystemExit(f"{', '.join(missing_args)} required for run-veer-el2-sidecar-bridge")
        report = run_veer_el2_sidecar_execution_bridge(
            repo_root=repo_root,
            state_image_path=args.state_image,
            cpu_execute_dir=args.cpu_execute_dir,
            sidecar_execute_dir=args.sidecar_execute_dir,
            sidecar_executable=args.sidecar_executable,
            mdir=args.mdir,
        )
    else:
        report = run_native_sidecar_build(
            filelist_path=args.filelist,
            top_module=args.top_module,
            repo_root=repo_root,
            registry_path=args.registry,
            mdir_override=args.mdir,
            shape=_shape_from_args(args.sim_accel_states, args.sim_accel_steps),
        )
    serialized = _json.dumps(report, indent=2)
    print(serialized)
    if args.summary_out:
        summary_path = Path(args.summary_out)
        if not summary_path.is_absolute():
            summary_path = Path.cwd() / summary_path
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(serialized + "\n", encoding="utf-8")
    if args.command == "plan":
        return 0 if report["status"] == STATUS_BUILD_PLAN_READY else 1
    if args.command == "prepare-direct-shim-smoke":
        return 0 if report["status"] == STATUS_BUILD_PLAN_READY else 1
    if args.command == "build-direct-shim-smoke":
        return 0 if report["status"] == STATUS_BUILD_PLAN_READY else 1
    if args.command == "inspect-veer-el2-state-layout":
        return 0 if report.get("state_layout_ready") is True else 1
    if args.command == "materialize-veer-el2-state-image":
        return 0 if report.get("state_image_materialized") is True else 1
    if args.command == "run-veer-el2-sidecar-bridge":
        return 0 if report.get("status") == STATUS_VEER_EL2_SIDECAR_COMPARE_PASSED else 1
    return 0 if report.get("template_flow_passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
