"""Patch generated Vortex Vsim main with a materialized runtime-args probe."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PATCH_BEGIN = "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN */"
PATCH_END = "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_END */"
CALL_BEGIN = "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_BEGIN */"
CALL_END = "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_END */"
FUNCTION_ANCHOR = "//======================"
CALL_ANCHOR = "    /* RTLMETER_SIDECAR_PROXY_PATCH_BEGIN */"
DEFAULT_REPO_ROOT_RELATIVE_FROM_OBJ_DIR = "../../../../../../.."
STATUS_PATCHED = "rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch_applied"
STATUS_ALREADY_PATCHED = "rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch_already_present"
STATUS_MISSING = "rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch_missing_source"
STATUS_UNSUPPORTED = "rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch_unsupported_source"


@dataclass(frozen=True)
class BufferSpec:
    name: str
    bytes_: int
    rel_path: str
    direction: str


BUFFER_SPECS = (
    BufferSpec(
        "vortex_init_segment_table",
        216,
        "artifacts/rtlmeter_vortex_mini_hello_device_buffers/vortex_init_segment_table.bin",
        "VORTEX_BUFFER_HOST_TO_DEVICE",
    ),
    BufferSpec(
        "vortex_init_payload",
        36864,
        "artifacts/rtlmeter_vortex_mini_hello_device_buffers/vortex_init_payload.bin",
        "VORTEX_BUFFER_HOST_TO_DEVICE",
    ),
    BufferSpec(
        "vortex_post_segment_table",
        24,
        "artifacts/rtlmeter_vortex_mini_hello_device_buffers/vortex_post_segment_table.bin",
        "VORTEX_BUFFER_HOST_TO_DEVICE",
    ),
    BufferSpec(
        "vortex_post_expected_payload",
        48,
        "artifacts/rtlmeter_vortex_mini_hello_device_buffers/vortex_post_expected_payload.bin",
        "VORTEX_BUFFER_HOST_TO_DEVICE",
    ),
    BufferSpec(
        "vortex_dcr_write_table",
        72,
        "artifacts/rtlmeter_vortex_mini_hello_device_buffers/vortex_dcr_write_table.bin",
        "VORTEX_BUFFER_HOST_TO_DEVICE",
    ),
    BufferSpec(
        "vortex_stdout_ring_initial",
        64,
        "artifacts/rtlmeter_vortex_mini_hello_device_buffers/vortex_stdout_ring_initial.bin",
        "VORTEX_BUFFER_DEVICE_TO_HOST",
    ),
    BufferSpec(
        "vortex_post_compare_result_initial",
        24,
        "artifacts/rtlmeter_vortex_mini_hello_device_buffers/vortex_post_compare_result_initial.bin",
        "VORTEX_BUFFER_DEVICE_TO_HOST",
    ),
)

REQUIRED_SENTINELS = (
    "// DESCRIPTION: Verilator output: main() simulation loop, created with --main",
    '#include "verilated.h"',
    '#include "Vsim.h"',
    "int main(int argc, char** argv, char**) {",
    "contextp->commandArgs(argc, argv);",
    '#include "../../../../../../../src/hybrid/vortex_lowered_tb_runtime_sequence.h"',
    "vortex_lowered_tb_invoke_runtime_sequence",
)


def _relative_path(path: Path, repo_root: Path | None) -> str:
    if repo_root is not None:
        try:
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    if path.is_absolute():
        return "<local-absolute-path>"
    return path.as_posix()


def _artifact_path_literal(root_rel: str, rel_path: str) -> str:
    return f"{root_rel}/{rel_path}"


def _buffer_init_lines(root_rel: str) -> str:
    lines: list[str] = []
    for index, spec in enumerate(BUFFER_SPECS):
        host_data = (
            f'rtlmeter_vortex_runtime_args_probe_load_file("{_artifact_path_literal(root_rel, spec.rel_path)}", '
            f"{spec.bytes_}u)"
            if spec.direction == "VORTEX_BUFFER_HOST_TO_DEVICE"
            else "0"
        )
        lines.extend(
            [
                f'    buffers[{index}].name = "{spec.name}";',
                f"    buffers[{index}].host_data = {host_data};",
                f"    buffers[{index}].bytes = {spec.bytes_}u;",
                f"    buffers[{index}].direction = {spec.direction};",
                f"    buffers[{index}].initial_value = 0;",
                f"    buffers[{index}].device_ptr = 0;",
            ]
        )
    return "\n".join(lines)


def _probe_block(root_rel: str) -> str:
    return (
        f"{PATCH_BEGIN}\n"
        "typedef struct {\n"
        "    unsigned alloc_count;\n"
        "    unsigned h2d_count;\n"
        "    unsigned memset_count;\n"
        "    unsigned free_count;\n"
        "    unsigned dcr_count;\n"
        "    unsigned kernel_count;\n"
        "    unsigned dtoh_count;\n"
        "    VortexCuDeviceptr next_ptr;\n"
        "} RtlmeterVortexMaterializedRuntimeArgsProbe;\n\n"
        "static RtlmeterVortexMaterializedRuntimeArgsProbe rtlmeter_vortex_runtime_args_probe;\n"
        "static VortexPostCompareResult rtlmeter_vortex_runtime_args_probe_post;\n"
        "static unsigned char rtlmeter_vortex_runtime_args_probe_stdout[64];\n\n"
        "static void* rtlmeter_vortex_runtime_args_probe_load_file(const char* path, size_t expected_bytes) {\n"
        "    FILE* fp = fopen(path, \"rb\");\n"
        "    if (fp == 0) return 0;\n"
        "    unsigned char* data = (unsigned char*)malloc(expected_bytes == 0 ? 1 : expected_bytes);\n"
        "    if (data == 0) { fclose(fp); return 0; }\n"
        "    size_t read_bytes = fread(data, 1, expected_bytes, fp);\n"
        "    int extra = fgetc(fp);\n"
        "    fclose(fp);\n"
        "    if (read_bytes != expected_bytes || extra != EOF) { free(data); return 0; }\n"
        "    return data;\n"
        "}\n\n"
        "static VortexCuResult rtlmeter_vortex_runtime_args_probe_alloc(VortexCuDeviceptr* out, size_t bytes) {\n"
        "    if (out == 0 || bytes == 0) return 11;\n"
        "    *out = rtlmeter_vortex_runtime_args_probe.next_ptr++;\n"
        "    ++rtlmeter_vortex_runtime_args_probe.alloc_count;\n"
        "    return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult rtlmeter_vortex_runtime_args_probe_h2d(VortexCuDeviceptr dst, const void* src, size_t bytes) {\n"
        "    if (dst == 0 || src == 0 || bytes == 0) return 12;\n"
        "    ++rtlmeter_vortex_runtime_args_probe.h2d_count;\n"
        "    return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult rtlmeter_vortex_runtime_args_probe_memset(VortexCuDeviceptr dst, unsigned char value, size_t bytes) {\n"
        "    if (dst == 0 || value != 0 || bytes == 0) return 13;\n"
        "    ++rtlmeter_vortex_runtime_args_probe.memset_count;\n"
        "    return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult rtlmeter_vortex_runtime_args_probe_free(VortexCuDeviceptr ptr) {\n"
        "    if (ptr == 0) return 14;\n"
        "    ++rtlmeter_vortex_runtime_args_probe.free_count;\n"
        "    return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult rtlmeter_vortex_runtime_args_probe_dcr(void* user, uint32_t addr, uint32_t value, int reset_asserted) {\n"
        "    (void)user; (void)addr; (void)value;\n"
        "    if (reset_asserted != 1) return 15;\n"
        "    ++rtlmeter_vortex_runtime_args_probe.dcr_count;\n"
        "    return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult rtlmeter_vortex_runtime_args_probe_kernel(void* user, VortexRuntimeBuffer* buffers, unsigned buffer_count) {\n"
        "    (void)user;\n"
        "    if (buffers == 0 || buffer_count != 7) return 16;\n"
        "    if (buffers[0].device_ptr != 1000 || buffers[6].device_ptr != 1006) return 17;\n"
        "    ++rtlmeter_vortex_runtime_args_probe.kernel_count;\n"
        "    return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult rtlmeter_vortex_runtime_args_probe_dtoh(void* dst, VortexCuDeviceptr src, size_t bytes) {\n"
        "    ++rtlmeter_vortex_runtime_args_probe.dtoh_count;\n"
        "    if (src == 1006) {\n"
        "        if (bytes != sizeof(VortexPostCompareResult)) return 18;\n"
        "        memcpy(dst, &rtlmeter_vortex_runtime_args_probe_post, bytes);\n"
        "        return VORTEX_CUDA_SUCCESS;\n"
        "    }\n"
        "    if (src == 1005) {\n"
        "        if (bytes != 64) return 19;\n"
        "        memcpy(dst, rtlmeter_vortex_runtime_args_probe_stdout, bytes);\n"
        "        return VORTEX_CUDA_SUCCESS;\n"
        "    }\n"
        "    return 20;\n"
        "}\n\n"
        "static int rtlmeter_vortex_materialized_runtime_args_probe() {\n"
        "    memset(&rtlmeter_vortex_runtime_args_probe, 0, sizeof(rtlmeter_vortex_runtime_args_probe));\n"
        "    memset(&rtlmeter_vortex_runtime_args_probe_post, 0, sizeof(rtlmeter_vortex_runtime_args_probe_post));\n"
        "    memset(rtlmeter_vortex_runtime_args_probe_stdout, 0, sizeof(rtlmeter_vortex_runtime_args_probe_stdout));\n"
        "    memcpy(rtlmeter_vortex_runtime_args_probe_stdout, \"TEST PASSED\\n\", 12);\n"
        "    rtlmeter_vortex_runtime_args_probe.next_ptr = 1000;\n"
        "    VortexRuntimeBuffer buffers[7];\n"
        f"{_buffer_init_lines(root_rel)}\n"
        "    for (unsigned i = 0; i < 5; ++i) { if (buffers[i].host_data == 0) return 21; }\n"
        "    VortexDcrWrite* dcr_writes = (VortexDcrWrite*)buffers[4].host_data;\n"
        "    VortexCudaUploadDriver upload = {\n"
        "        rtlmeter_vortex_runtime_args_probe_alloc,\n"
        "        rtlmeter_vortex_runtime_args_probe_h2d,\n"
        "        rtlmeter_vortex_runtime_args_probe_memset,\n"
        "        rtlmeter_vortex_runtime_args_probe_free\n"
        "    };\n"
        "    VortexObservableExportDriver export_driver = {rtlmeter_vortex_runtime_args_probe_dtoh};\n"
        "    VortexRuntimeSequenceArgs args = {\n"
        "        &upload, buffers, 7, dcr_writes, 9,\n"
        "        rtlmeter_vortex_runtime_args_probe_dcr, 0,\n"
        "        rtlmeter_vortex_runtime_args_probe_kernel, 0,\n"
        "        &export_driver\n"
        "    };\n"
        "    VortexRuntimeSequenceSummary sequence_summary;\n"
        "    VortexLoweredTbRuntimeSummary tb_summary;\n"
        "    VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);\n"
        "    for (unsigned i = 0; i < 5; ++i) { free((void*)buffers[i].host_data); buffers[i].host_data = 0; }\n"
        "    if (result != VORTEX_CUDA_SUCCESS) return 30;\n"
        "    if (tb_summary.runtime_sequence_called != 1 || tb_summary.runtime_sequence_passed != 1) return 31;\n"
        "    if (tb_summary.authority_report_ready != 1 || tb_summary.authority_passed != 1) return 32;\n"
        "    if (sequence_summary.dcr_applied_count != 9 || sequence_summary.kernel_launch_invoked != 1) return 33;\n"
        "    if (sequence_summary.observable_export_invoked != 1 || sequence_summary.buffers_released != 1) return 34;\n"
        "    return 0;\n"
        "}\n"
        f"{PATCH_END}\n\n"
    )


def _call_block() -> str:
    return (
        f"    {CALL_BEGIN}\n"
        "    if (rtlmeter_vortex_materialized_runtime_args_probe() != 0) return 123;\n"
        f"    {CALL_END}\n"
    )


def _unsupported(main_cpp: Path, repo_root: Path | None, missing: list[str]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch",
        "status": STATUS_UNSUPPORTED,
        "main_cpp": _relative_path(main_cpp, repo_root),
        "materialized_runtime_args_probe_applied": False,
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "missing_patch_context": missing,
    }


def patch_vortex_materialized_runtime_args_probe(
    *,
    main_cpp: Path,
    repo_root: Path | None = None,
    repo_root_relative_from_obj_dir: str = DEFAULT_REPO_ROOT_RELATIVE_FROM_OBJ_DIR,
) -> dict[str, object]:
    if main_cpp.name != "Vsim__main.cpp" or main_cpp.parent.name != "obj_dir":
        return _unsupported(main_cpp, repo_root, ["rtlmeter_vsim_main_path"])
    if not main_cpp.is_file():
        return {
            "schema_version": 1,
            "surface": "rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch",
            "status": STATUS_MISSING,
            "main_cpp": _relative_path(main_cpp, repo_root),
            "materialized_runtime_args_probe_applied": False,
            "runtime_authority": False,
            "timing_measured": False,
            "speedup_claimed": False,
            "missing_patch_context": ["main_cpp"],
        }

    missing_artifacts = []
    for spec in BUFFER_SPECS:
        artifact = main_cpp.parent / repo_root_relative_from_obj_dir / spec.rel_path
        if not artifact.is_file():
            missing_artifacts.append(f"artifact.{spec.name}")
        elif artifact.stat().st_size != spec.bytes_:
            missing_artifacts.append(f"artifact_size.{spec.name}")
    if missing_artifacts:
        return _unsupported(main_cpp, repo_root, missing_artifacts)

    text = main_cpp.read_text(encoding="utf-8")
    begin_count = text.count(PATCH_BEGIN)
    end_count = text.count(PATCH_END)
    call_count = text.count(CALL_BEGIN)
    if begin_count == 1 and end_count == 1 and call_count == 1:
        return {
            "schema_version": 1,
            "surface": "rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch",
            "status": STATUS_ALREADY_PATCHED,
            "main_cpp": _relative_path(main_cpp, repo_root),
            "materialized_runtime_args_probe_applied": True,
            "runtime_authority": False,
            "timing_measured": False,
            "speedup_claimed": False,
            "buffer_count": len(BUFFER_SPECS),
            "host_to_device_bytes": sum(
                spec.bytes_ for spec in BUFFER_SPECS if spec.direction == "VORTEX_BUFFER_HOST_TO_DEVICE"
            ),
            "device_to_host_initial_bytes": sum(
                spec.bytes_ for spec in BUFFER_SPECS if spec.direction == "VORTEX_BUFFER_DEVICE_TO_HOST"
            ),
            "dcr_write_count": 9,
            "missing_patch_context": [],
        }
    if begin_count or end_count or call_count:
        return _unsupported(main_cpp, repo_root, ["vortex_materialized_runtime_args_probe_patch_markers"])
    missing = [sentinel for sentinel in REQUIRED_SENTINELS if text.count(sentinel) < 1]
    if FUNCTION_ANCHOR not in text:
        missing.append("function_anchor")
    if CALL_ANCHOR not in text:
        missing.append("call_anchor")
    if missing:
        return _unsupported(main_cpp, repo_root, missing)

    patched = text.replace(FUNCTION_ANCHOR, _probe_block(repo_root_relative_from_obj_dir) + FUNCTION_ANCHOR, 1)
    patched = patched.replace(CALL_ANCHOR, _call_block() + CALL_ANCHOR, 1)
    main_cpp.write_text(patched, encoding="utf-8")
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch",
        "status": STATUS_PATCHED,
        "main_cpp": _relative_path(main_cpp, repo_root),
        "materialized_runtime_args_probe_applied": True,
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "buffer_count": len(BUFFER_SPECS),
        "host_to_device_bytes": sum(spec.bytes_ for spec in BUFFER_SPECS if spec.direction == "VORTEX_BUFFER_HOST_TO_DEVICE"),
        "device_to_host_initial_bytes": sum(spec.bytes_ for spec in BUFFER_SPECS if spec.direction == "VORTEX_BUFFER_DEVICE_TO_HOST"),
        "dcr_write_count": 9,
        "missing_patch_context": [],
    }
