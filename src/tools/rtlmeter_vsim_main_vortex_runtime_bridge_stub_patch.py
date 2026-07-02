"""Patch generated Vortex Vsim main with a typed runtime bridge stub."""

from __future__ import annotations

from pathlib import Path


PATCH_BEGIN = "/* RTLMETER_VORTEX_RUNTIME_BRIDGE_STUB_PATCH_BEGIN */"
PATCH_END = "/* RTLMETER_VORTEX_RUNTIME_BRIDGE_STUB_PATCH_END */"
CALL_BEGIN = "/* RTLMETER_VORTEX_RUNTIME_BRIDGE_STUB_CALL_BEGIN */"
CALL_END = "/* RTLMETER_VORTEX_RUNTIME_BRIDGE_STUB_CALL_END */"
FUNCTION_ANCHOR = "//======================"
CALL_ANCHOR = "    /* RTLMETER_SIDECAR_PROXY_PATCH_BEGIN */"
DEFAULT_HEADER_RELATIVE_FROM_OBJ_DIR = "../../../../../../../src/hybrid/vortex_lowered_tb_runtime_sequence.h"
REQUIRED_SENTINELS = (
    "// DESCRIPTION: Verilator output: main() simulation loop, created with --main",
    '#include "verilated.h"',
    '#include "Vsim.h"',
    "int main(int argc, char** argv, char**) {",
    "contextp->commandArgs(argc, argv);",
    "while (VL_LIKELY(!contextp->gotFinish())) {",
    "topp->eval();",
    "topp->final();",
)
STATUS_PATCHED = "rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch_applied"
STATUS_ALREADY_PATCHED = "rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch_already_present"
STATUS_MISSING = "rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch_missing_source"
STATUS_UNSUPPORTED = "rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch_unsupported_source"


def _relative_path(path: Path, repo_root: Path | None) -> str:
    if repo_root is not None:
        try:
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    if path.is_absolute():
        return "<local-absolute-path>"
    return path.as_posix()


def _include_line(header: str) -> str:
    return f'#include "{header}"\n\n'


def _stub_block() -> str:
    return (
        f"{PATCH_BEGIN}\n"
        "static int rtlmeter_vortex_runtime_bridge_typed_stub() {\n"
        "    /* schema_version=1 */\n"
        "    /* producer=rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch */\n"
        "    /* runtime_authority=false timing_measured=false speedup_claimed=false */\n"
        "    /* typed_header_bridge_stub=true */\n"
        "    VortexRuntimeSequenceSummary sequence_summary;\n"
        "    VortexLoweredTbRuntimeSummary tb_summary;\n"
        "    vortex_runtime_sequence_summary_clear(&sequence_summary);\n"
        "    vortex_lowered_tb_runtime_summary_clear(&tb_summary);\n"
        "    return sequence_summary.kernel_launch_invoked + tb_summary.runtime_sequence_called;\n"
        "}\n"
        f"{PATCH_END}\n\n"
    )


def _call_block() -> str:
    return (
        f"    {CALL_BEGIN}\n"
        "    (void)rtlmeter_vortex_runtime_bridge_typed_stub();\n"
        f"    {CALL_END}\n"
    )


def _unsupported(main_cpp: Path, repo_root: Path | None, missing: list[str]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch",
        "status": STATUS_UNSUPPORTED,
        "main_cpp": _relative_path(main_cpp, repo_root),
        "bridge_stub_applied": False,
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "missing_patch_context": missing,
    }


def patch_vortex_runtime_bridge_stub(
    *,
    main_cpp: Path,
    repo_root: Path | None = None,
    header_relative_from_obj_dir: str = DEFAULT_HEADER_RELATIVE_FROM_OBJ_DIR,
) -> dict[str, object]:
    if main_cpp.name != "Vsim__main.cpp" or main_cpp.parent.name != "obj_dir":
        return _unsupported(main_cpp, repo_root, ["rtlmeter_vsim_main_path"])
    if not main_cpp.is_file():
        return {
            "schema_version": 1,
            "surface": "rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch",
            "status": STATUS_MISSING,
            "main_cpp": _relative_path(main_cpp, repo_root),
            "bridge_stub_applied": False,
            "runtime_authority": False,
            "timing_measured": False,
            "speedup_claimed": False,
            "missing_patch_context": ["main_cpp"],
        }

    header_path = main_cpp.parent / header_relative_from_obj_dir
    if not header_path.is_file():
        return _unsupported(main_cpp, repo_root, ["vortex_lowered_tb_runtime_sequence_header"])

    text = main_cpp.read_text(encoding="utf-8")
    begin_count = text.count(PATCH_BEGIN)
    end_count = text.count(PATCH_END)
    call_count = text.count(CALL_BEGIN)
    if begin_count == 1 and end_count == 1 and call_count == 1:
        return {
            "schema_version": 1,
            "surface": "rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch",
            "status": STATUS_ALREADY_PATCHED,
            "main_cpp": _relative_path(main_cpp, repo_root),
            "bridge_stub_applied": True,
            "runtime_authority": False,
            "timing_measured": False,
            "speedup_claimed": False,
            "header": header_relative_from_obj_dir,
            "missing_patch_context": [],
        }
    if begin_count or end_count or call_count:
        return _unsupported(main_cpp, repo_root, ["vortex_runtime_bridge_stub_patch_markers"])
    missing = [sentinel for sentinel in REQUIRED_SENTINELS if text.count(sentinel) != 1]
    if FUNCTION_ANCHOR not in text:
        missing.append("function_anchor")
    if CALL_ANCHOR not in text:
        missing.append("call_anchor")
    if missing:
        return _unsupported(main_cpp, repo_root, missing)

    patched = text.replace(FUNCTION_ANCHOR, _include_line(header_relative_from_obj_dir) + _stub_block() + FUNCTION_ANCHOR, 1)
    patched = patched.replace(CALL_ANCHOR, _call_block() + CALL_ANCHOR, 1)
    main_cpp.write_text(patched, encoding="utf-8")
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch",
        "status": STATUS_PATCHED,
        "main_cpp": _relative_path(main_cpp, repo_root),
        "bridge_stub_applied": True,
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "header": header_relative_from_obj_dir,
        "missing_patch_context": [],
    }
