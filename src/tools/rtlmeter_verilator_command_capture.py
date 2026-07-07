"""Capture RTLMeter's Verilator command shape without executing it."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any


SURFACE = "rtlmeter_verilator_command_capture"
SIDECAR_CONTRACT_ROLE = "frontend_owned_build_metadata"
JSON_FLOW_ROLE = "debug_inspection"
RTLMETER_PREFIX = "Vsim"
TRACE_TO_DEFINE = {
    "--trace": "+define+__RTLMETER_TRACE_VCD",
    "--trace-vcd": "+define+__RTLMETER_TRACE_VCD",
    "--trace-fst": "+define+__RTLMETER_TRACE_FST",
}


class RtlmeterCommandCaptureError(ValueError):
    pass

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_rtlmeter_root() -> Path:
    return _repo_root() / "third_party" / "rtlmeter"


def _rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _display_default_root_path(path: Path) -> str:
    try:
        return _rel(path, _repo_root())
    except ValueError:
        return "rtlmeter_root/src"


def _display_rtlmeter_path(path: Path, rtlmeter_root: Path) -> str:
    return f"third_party/rtlmeter/{_rel(path, rtlmeter_root)}"


def _apply_descriptor_defaults(desc: dict[str, Any]) -> dict[str, Any]:
    desc["compile"] = desc.get("compile") or {}
    desc["configurations"] = {
        key: {"compile": (value or {}).get("compile") or {}}
        for key, value in desc.get("configurations", {"default": {}}).items()
    }
    return desc


def _load_descriptor_yaml(descriptor_path: Path) -> tuple[dict[str, Any], str]:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise RtlmeterCommandCaptureError(
            "PyYAML is required for safe_yaml_descriptor_fallback when RTLMeter loader is unavailable"
        ) from exc
    with descriptor_path.open("r", encoding="utf-8") as stream:
        return _apply_descriptor_defaults(yaml.safe_load(stream) or {}), "safe_yaml_descriptor_fallback"


def _load_rtlmeter_descriptor(rtlmeter_root: Path, design: str) -> dict[str, Any]:
    src_dir = rtlmeter_root / "src"
    if not src_dir.is_dir():
        raise RtlmeterCommandCaptureError(
            f"RTLMeter source directory is missing: {_display_default_root_path(src_dir)}"
        )

    descriptor_path = rtlmeter_root / "designs" / design / "descriptor.yaml"
    if not descriptor_path.is_file():
        raise RtlmeterCommandCaptureError(f"RTLMeter design descriptor is missing: {design}")

    old_root = os.environ.get("RTLMETER_ROOT")
    old_path = list(sys.path)
    loader = "rtlmeter_yaml_descriptor"
    try:
        os.environ["RTLMETER_ROOT"] = str(rtlmeter_root.resolve())
        sys.path.insert(0, str(src_dir.resolve()))
        from rtlmeter import yaml_descriptor  # type: ignore

        descriptor = yaml_descriptor.load(str(descriptor_path))
    except ModuleNotFoundError:
        descriptor, loader = _load_descriptor_yaml(descriptor_path)
    finally:
        if old_root is None:
            os.environ.pop("RTLMETER_ROOT", None)
        else:
            os.environ["RTLMETER_ROOT"] = old_root
        sys.path[:] = old_path

    if not descriptor:
        raise RtlmeterCommandCaptureError(f"RTLMeter design descriptor is invalid: {design}")
    descriptor["__file__"] = descriptor_path
    descriptor["designDir"] = rtlmeter_root / "designs" / design
    descriptor["descriptor_loader"] = loader
    return descriptor


def _gather_scalar(key: str, *descs: dict[str, Any]) -> str | None:
    result: str | None = None
    for desc in descs:
        if (value := desc.get(key)) is not None:
            result = str(value)
    return result


def _gather_list(key: str, *descs: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for desc in descs:
        result.extend(str(item) for item in desc.get(key, []))
    return result


def _gather_dict(key: str, *descs: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for desc in descs:
        result.update((str(k), str(v)) for k, v in desc.get(key, {}).items())
    return result


def _split_case(case: str) -> tuple[str, str, str | None]:
    parts = case.split(":")
    if len(parts) == 2:
        return parts[0], parts[1], None
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    raise RtlmeterCommandCaptureError(
        "RTLMeter case must be formatted as <design>:<config> or <design>:<config>:<test>"
    )


def _relative_files(design_dir: Path, rtlmeter_root: Path, file_names: Sequence[str]) -> list[str]:
    return [_rel(design_dir / file_name, rtlmeter_root) for file_name in file_names]


def _rtlmeter_trace_define(command_argv: Sequence[str]) -> str | None:
    last_trace_option = None
    for arg in command_argv:
        if arg in TRACE_TO_DEFINE:
            last_trace_option = arg
    if last_trace_option is None:
        return None
    return TRACE_TO_DEFINE[last_trace_option]


def capture_rtlmeter_verilator_command(
    case: str,
    *,
    rtlmeter_root: str | Path | None = None,
    extra_args: Sequence[str] = (),
) -> dict[str, object]:
    """Return the non-executing Verilator command shape for an RTLMeter compile case."""

    root = Path(rtlmeter_root) if rtlmeter_root is not None else default_rtlmeter_root()
    root = root.resolve()
    design, config, test = _split_case(case)
    descriptor = _load_rtlmeter_descriptor(root, design)
    configs = descriptor.get("configurations", {})
    if config not in configs:
        raise RtlmeterCommandCaptureError(f"RTLMeter config is missing: {design}:{config}")

    root_compile = descriptor.get("compile") or {}
    config_compile = configs[config].get("compile") or {}
    design_dir = descriptor["designDir"]

    top_module = _gather_scalar("topModule", root_compile, config_compile)
    if top_module is None:
        raise RtlmeterCommandCaptureError(f"RTLMeter descriptor does not specify topModule: {design}")
    main_clock = _gather_scalar("mainClock", root_compile, config_compile)
    if main_clock is None:
        raise RtlmeterCommandCaptureError(f"RTLMeter descriptor does not specify mainClock: {design}")

    verilog_source_files = _relative_files(
        design_dir, root, _gather_list("verilogSourceFiles", root_compile, config_compile)
    ) + ["rtl/__rtlmeter_utils.sv"]
    verilog_include_files = _relative_files(
        design_dir, root, _gather_list("verilogIncludeFiles", root_compile, config_compile)
    ) + ["rtl/__rtlmeter_top_include.vh"]
    cpp_source_files = _relative_files(
        design_dir, root, _gather_list("cppSourceFiles", root_compile, config_compile)
    )
    cpp_include_files = _relative_files(
        design_dir, root, _gather_list("cppIncludeFiles", root_compile, config_compile)
    )
    verilog_defines = _gather_dict("verilogDefines", root_compile, config_compile)
    verilog_defines["__RTLMETER_MAIN_CLOCK"] = main_clock
    cpp_defines = _gather_dict("cppDefines", root_compile, config_compile)
    verilator_args = _gather_list("verilatorArgs", root_compile, config_compile)

    command_argv = [
        "verilator", "--cc", "--main", "--exe", "--timing", "--quiet-stats", "-Wno-fatal",
        "--prefix", RTLMETER_PREFIX, "--top-module", top_module,
    ]
    if verilog_include_files:
        command_argv.append("+incdir+verilogIncludeFiles")
    for key, value in sorted(verilog_defines.items()):
        command_argv.append(f"+define+{key}={value}")
    if cpp_include_files:
        command_argv.extend(["-CFLAGS", "-I../cppIncludeFiles"])
    for key, value in sorted(cpp_defines.items()):
        command_argv.extend(["-CFLAGS", f"-D{key}={value}"])
    command_argv.extend(["-f", "filelist"])
    command_argv.extend(verilator_args)
    command_argv.extend(str(arg) for arg in extra_args)
    trace_define = _rtlmeter_trace_define(command_argv)
    if trace_define is not None:
        command_argv.append(trace_define)

    filelist_entries = [
        f"verilogSourceFiles/{Path(file_name).name}" for file_name in verilog_source_files
    ] + [f"cppSourceFiles/{Path(file_name).name}" for file_name in cpp_source_files]

    return {
        "schema_version": 1,
        "surface": SURFACE,
        "case": case,
        "compile_case": f"{design}:{config}",
        "design": design,
        "config": config,
        "test": test,
        "rtlmeter_root": "third_party/rtlmeter",
        "descriptor": _display_rtlmeter_path(descriptor["__file__"], root),
        "descriptor_loader": descriptor["descriptor_loader"],
        "sidecar_contract_role": SIDECAR_CONTRACT_ROLE,
        "top_module": top_module,
        "main_clock": main_clock,
        "prefix": RTLMETER_PREFIX,
        "verilator_command_argv": command_argv,
        "filelist_entries": filelist_entries,
        "verilog_source_files": verilog_source_files,
        "verilog_include_files": verilog_include_files,
        "verilog_defines": verilog_defines,
        "cpp_source_files": cpp_source_files,
        "cpp_include_files": cpp_include_files,
        "cpp_defines": cpp_defines,
        "verilator_args": verilator_args,
        "extra_args": [str(arg) for arg in extra_args],
        "rtlmeter_trace_define": trace_define,
        "json_flow_role": JSON_FLOW_ROLE,
        "runtime_abi": False,
        "execution_authority": False,
        "non_claims": [
            "command capture does not compile RTLMeter or run Verilator",
            "command capture does not build GPU artifacts, run sidecar stages, compare outputs, or measure timing",
            "command capture does not prove RTLMeter acceleration",
        ],
    }
