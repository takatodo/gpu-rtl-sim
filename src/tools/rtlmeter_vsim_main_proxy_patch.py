"""Patch generated RTLMeter Vsim main sources with a fail-closed proxy handoff."""

from __future__ import annotations

from pathlib import Path


PATCH_BEGIN = "/* RTLMETER_SIDECAR_PROXY_PATCH_BEGIN */"
PATCH_END = "/* RTLMETER_SIDECAR_PROXY_PATCH_END */"
INSERT_ANCHOR = "    // Simulate until $finish"
INCLUDE_ANCHOR = '#include "Vsim.h"'
PROXY_ENV = "RTLMETER_VSIM_SIDECAR_PROXY"
REQUIRED_SENTINELS = (
    "// DESCRIPTION: Verilator output: main() simulation loop, created with --main",
    '#include "verilated.h"',
    '#include "Vsim.h"',
    "int main(int argc, char** argv, char**) {",
    "const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};",
    "contextp->commandArgs(argc, argv);",
    'const std::unique_ptr<Vsim> topp{new Vsim{contextp.get(), ""}};',
    "while (VL_LIKELY(!contextp->gotFinish())) {",
    "topp->eval();",
    "topp->final();",
    "contextp->statsPrintSummary();",
)
STATUS_PATCHED = "rtlmeter_vsim_main_proxy_patch_applied"
STATUS_ALREADY_PATCHED = "rtlmeter_vsim_main_proxy_patch_already_present"
STATUS_MISSING = "rtlmeter_vsim_main_proxy_patch_missing_source"
STATUS_UNSUPPORTED = "rtlmeter_vsim_main_proxy_patch_unsupported_source"


def _relative_path(path: Path, repo_root: Path | None) -> str:
    if repo_root is not None:
        try:
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    if path.is_absolute():
        return "<local-absolute-path>"
    return path.as_posix()


def _patch_block() -> str:
    return (
        f"    {PATCH_BEGIN}\n"
        "    /* schema_version=1 phase=sidecar_verilate execution_authority=true */\n"
        "    /* producer=rtlmeter_vsim_main_proxy_patch cpu_as_gpu_fallback=false ordinary_vsim_output=false */\n"
        f"    const char* rtlmeter_sidecar_proxy = std::getenv(\"{PROXY_ENV}\");\n"
        "    if (rtlmeter_sidecar_proxy == nullptr || rtlmeter_sidecar_proxy[0] == '\\0') {\n"
        f"        std::fprintf(stderr, \"missing {PROXY_ENV} for RTLMeter sidecar proxy\\n\");\n"
        "        return 125;\n"
        "    }\n"
        "    argv[0] = const_cast<char*>(rtlmeter_sidecar_proxy);\n"
        "    execv(rtlmeter_sidecar_proxy, argv);\n"
        "    std::perror(\"execv RTLMeter sidecar proxy\");\n"
        "    return 126;\n"
        f"    {PATCH_END}\n"
    )


def _include_block() -> str:
    return "\n".join((INCLUDE_ANCHOR, "#include <cstdio>", "#include <cstdlib>", "#include <unistd.h>"))


def _unsupported(main_cpp: Path, repo_root: Path | None, missing: list[str]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vsim_main_proxy_patch",
        "status": STATUS_UNSUPPORTED,
        "main_cpp": _relative_path(main_cpp, repo_root),
        "patched_by_wrapper_branch": False,
        "reviewed_proxy_metadata_observed": False,
        "sidecar_execution_invoked": False,
        "cpu_as_gpu_fallback": False,
        "ordinary_vsim_output": False,
        "missing_patch_context": missing,
    }


def patch_rtlmeter_vsim_main_proxy_marker(*, main_cpp: Path, repo_root: Path | None = None) -> dict[str, object]:
    if main_cpp.name != "Vsim__main.cpp" or main_cpp.parent.name != "obj_dir":
        return _unsupported(main_cpp, repo_root, ["rtlmeter_vsim_main_path"])
    if not main_cpp.is_file():
        return {
            "schema_version": 1,
            "surface": "rtlmeter_vsim_main_proxy_patch",
            "status": STATUS_MISSING,
            "main_cpp": _relative_path(main_cpp, repo_root),
            "patched_by_wrapper_branch": False,
            "reviewed_proxy_metadata_observed": False,
            "sidecar_execution_invoked": False,
            "cpu_as_gpu_fallback": False,
            "ordinary_vsim_output": False,
            "missing_patch_context": ["main_cpp"],
        }

    text = main_cpp.read_text(encoding="utf-8")
    begin_count = text.count(PATCH_BEGIN)
    end_count = text.count(PATCH_END)
    if begin_count == 1 and end_count == 1:
        return {
            "schema_version": 1,
            "surface": "rtlmeter_vsim_main_proxy_patch",
            "status": STATUS_ALREADY_PATCHED,
            "main_cpp": _relative_path(main_cpp, repo_root),
            "patched_by_wrapper_branch": True,
            "reviewed_proxy_metadata_observed": True,
            "sidecar_execution_invoked": False,
            "cpu_as_gpu_fallback": False,
            "ordinary_vsim_output": False,
            "missing_patch_context": [],
        }
    if begin_count or end_count:
        return _unsupported(main_cpp, repo_root, ["proxy_patch_markers"])
    missing = [sentinel for sentinel in REQUIRED_SENTINELS if text.count(sentinel) != 1]
    if INSERT_ANCHOR not in text:
        missing.append("simulate_until_finish_anchor")
    if missing:
        return _unsupported(main_cpp, repo_root, missing)

    patched = text.replace(INCLUDE_ANCHOR, _include_block(), 1)
    patched = patched.replace(INSERT_ANCHOR, _patch_block() + INSERT_ANCHOR, 1)
    main_cpp.write_text(patched, encoding="utf-8")
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vsim_main_proxy_patch",
        "status": STATUS_PATCHED,
        "main_cpp": _relative_path(main_cpp, repo_root),
        "patched_by_wrapper_branch": True,
        "reviewed_proxy_metadata_observed": True,
        "sidecar_execution_invoked": False,
        "cpu_as_gpu_fallback": False,
        "ordinary_vsim_output": False,
        "missing_patch_context": [],
    }
