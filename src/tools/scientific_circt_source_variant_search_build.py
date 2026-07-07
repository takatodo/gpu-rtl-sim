#!/usr/bin/env python3
"""Build and measure emitted FC-075 source-variant search sources."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
from typing import Any

import scientific_circt_hls_mlp_block_variants as hls
import scientific_circt_source_variant_search as search
import scientific_circt_source_variant_search_codegen as codegen


PROBE = r'''#include "Vsim.h"
#include "verilated.h"
int main(int argc, char **argv) {
  Verilated::commandArgs(argc, argv);
  VerilatedContext context;
  Vsim top(&context);
  top.eval();
  top.final();
  return 0;
}
'''


@dataclass(frozen=True)
class SourceTriple:
    firrtl: Path
    cuda: Path
    bridge: Path


@dataclass(frozen=True)
class BuildPaths:
    work_dir: Path
    firrtl: Path
    systemverilog: Path
    probe: Path
    cuda: Path
    bridge: Path
    obj_dir: Path
    gpu_library: Path
    binary: Path


def plan_slug(plan: search.VariantPlan) -> str:
    shape = search.plan_shape(plan)
    return f"replicate-{shape.units}-unroll-{shape.inner_repeat}-pack-{shape.packing}"


def paths_for(root: Path, descriptor: search.BlockDescriptor, plan: search.VariantPlan) -> BuildPaths:
    name = codegen.variant_name(descriptor, plan)
    work_dir = root / descriptor.candidate / plan_slug(plan)
    return BuildPaths(
        work_dir=work_dir,
        firrtl=work_dir / f"{name}.fir",
        systemverilog=work_dir / f"{name}.sv",
        probe=work_dir / f"tb_{name}.cpp",
        cuda=work_dir / f"{name}_gpu.cu",
        bridge=work_dir / f"{name}_bridge.cpp",
        obj_dir=work_dir / "obj_dir",
        gpu_library=work_dir / f"lib{name}_gpu.so",
        binary=work_dir / f"{name}_direct",
    )


def command_plan(
    paths: BuildPaths,
    *,
    module_name: str,
    verilator_root: Path,
    nstates: int,
    repeat: int,
    inner_repeat: int,
    integration_batches: int,
) -> list[tuple[str, list[str]]]:
    include = verilator_root / "include"
    return [
        ("firtool", [hls._tool("firtool") or "firtool", paths.firrtl.as_posix(), "-o", paths.systemverilog.as_posix()]),
        (
            "verilator_build",
            [
                hls._tool("verilator") or "verilator",
                "--cc",
                "--exe",
                "--timing",
                "-Wno-fatal",
                "--prefix",
                "Vsim",
                "--top-module",
                module_name,
                "-Mdir",
                paths.obj_dir.as_posix(),
                paths.systemverilog.as_posix(),
                paths.probe.as_posix(),
                "-MAKEFLAGS",
                "OBJCACHE=",
                "--build",
            ],
        ),
        (
            "nvcc_gpu_library_build",
            [
                hls._tool("nvcc") or "nvcc",
                "-O3",
                "--std=c++17",
                "-shared",
                "-Xcompiler",
                "-fPIC",
                paths.cuda.as_posix(),
                "-o",
                paths.gpu_library.as_posix(),
            ],
        ),
        (
            "cxx_direct_callsite_build",
            [
                os.environ.get("CXX", "g++"),
                "-O3",
                "-std=c++17",
                paths.bridge.as_posix(),
                "-I",
                paths.obj_dir.as_posix(),
                "-I",
                include.as_posix(),
                "-I",
                (include / "vltstd").as_posix(),
                (paths.obj_dir / "Vsim__ALL.a").as_posix(),
                (paths.obj_dir / "verilated.o").as_posix(),
                (paths.obj_dir / "verilated_threads.o").as_posix(),
                "-ldl",
                "-pthread",
                "-o",
                paths.binary.as_posix(),
            ],
        ),
        (
            "direct_callsite_run",
            [
                paths.binary.as_posix(),
                paths.gpu_library.as_posix(),
                str(nstates),
                str(repeat),
                str(inner_repeat),
                str(integration_batches),
            ],
        ),
    ]


def parse_bridge_stdout(stdout: str) -> dict[str, Any] | None:
    observed = parse_json_object(stdout)
    if observed is None:
        return None
    required = (
        "status",
        "mismatch_count",
        "cpu_vs_gpu_output_equal",
        "cpu_vs_gpu_control_checksum_equal",
        "cpu_to_bridge_hybrid_wall_speedup",
    )
    if not all(key in observed for key in required):
        return None
    speedup = observed.get("cpu_to_bridge_hybrid_wall_speedup")
    if not isinstance(speedup, int | float) or isinstance(speedup, bool) or not math.isfinite(float(speedup)):
        return None
    return observed


def parse_json_object(stdout: str) -> dict[str, Any] | None:
    try:
        observed = json.loads(stdout.strip())
    except json.JSONDecodeError:
        return None
    return observed if isinstance(observed, dict) else None


def write_sources(paths: BuildPaths, sources: codegen.GeneratedSources) -> SourceTriple:
    paths.work_dir.mkdir(parents=True, exist_ok=True)
    paths.firrtl.write_text(sources.firrtl, encoding="utf-8")
    paths.cuda.write_text(sources.cuda, encoding="utf-8")
    paths.bridge.write_text(sources.bridge, encoding="utf-8")
    paths.probe.write_text(PROBE, encoding="utf-8")
    return SourceTriple(paths.firrtl, paths.cuda, paths.bridge)


def build_and_measure(
    descriptor: search.BlockDescriptor,
    plan: search.VariantPlan,
    *,
    out_root: Path,
    nstates: int = 1024,
    repeat: int = 1,
    integration_batches: int = 15,
) -> dict[str, Any]:
    shape = search.plan_shape(plan)
    paths = paths_for(out_root, descriptor, plan)
    sources = codegen.render_sources(descriptor, plan)
    write_sources(paths, sources)
    report: dict[str, Any] = {
        "schema_version": 1,
        "surface": "scientific_circt_source_variant_search_build",
        "candidate": descriptor.candidate,
        "variant": codegen.variant_name(descriptor, plan),
        "plan": str(plan),
        "plan_slug": plan_slug(plan),
        "shape": f"{nstates}x1",
        "repeat": repeat,
        "inner_repeat": shape.inner_repeat,
        "integration_batches": integration_batches,
        "artifacts": {
            "firrtl": hls._display_path(paths.firrtl),
            "systemverilog": hls._display_path(paths.systemverilog),
            "verilator_mdir": hls._display_path(paths.obj_dir),
            "gpu_library_source": hls._display_path(paths.cuda),
            "gpu_library": hls._display_path(paths.gpu_library),
            "direct_callsite_bridge_source": hls._display_path(paths.bridge),
            "direct_callsite_binary": hls._display_path(paths.binary),
        },
        "commands": [],
        "toolchain": {
            "firtool": hls._tool("firtool") is not None,
            "verilator": hls._tool("verilator") is not None,
            "nvcc": hls._tool("nvcc") is not None,
        },
        "non_claims": [
            "not_full_microgpt_execution",
            "not_automatic_hls_rewrite",
            "not_pcie_framing_evidence",
            "not_rtlmeter_evidence",
            "not_production_runtime_entrypoint",
        ],
    }
    if shape.packing != "uint8":
        report["status"] = "unsupported_emit_only_pack_inputs"
        report["reason"] = "PackInputs codegen remains emit-only until packed ABI sources are implemented"
        return report
    verilator_root, root_command = hls._verilator_root_command()
    if root_command is not None:
        report["commands"].append({"stage": "resolve_verilator_root", **root_command})
    if verilator_root is None:
        report["status"] = "failed_missing_verilator_root"
        return report
    for stage, command in command_plan(
        paths,
        module_name=codegen.module_name(descriptor, plan),
        verilator_root=verilator_root,
        nstates=nstates,
        repeat=repeat,
        inner_repeat=shape.inner_repeat,
        integration_batches=integration_batches,
    ):
        result = hls._run(command)
        report["commands"].append({"stage": stage, **result})
        if stage == "direct_callsite_run":
            observed_any = parse_json_object(str(result.get("stdout", "")))
            if observed_any is not None:
                report["observed"] = observed_any
            observed = parse_bridge_stdout(str(result.get("stdout", "")))
            if observed is not None:
                report["observed"] = observed
                report["cpu_vs_gpu_output_equal"] = observed.get("cpu_vs_gpu_output_equal") is True
                report["cpu_vs_gpu_control_checksum_equal"] = observed.get("cpu_vs_gpu_control_checksum_equal") is True
                report["average"] = {
                    "cpu_ms": observed.get("cpu_ms"),
                    "gpu_end_to_end_ms": observed.get("gpu_end_to_end_ms"),
                    "gpu_kernel_ms": observed.get("gpu_kernel_ms"),
                    "bridge_hybrid_wall_ms_per_integration_batch": observed.get(
                        "bridge_hybrid_wall_ms_per_integration_batch"
                    ),
                    "cpu_to_bridge_hybrid_wall_speedup": observed.get("cpu_to_bridge_hybrid_wall_speedup"),
                }
        if result["returncode"] != 0:
            report["status"] = "generated_source_variant_mismatch" if report.get("observed") else f"failed_{stage}"
            return report
    report["status"] = (
        "generated_source_variant_measured"
        if (report.get("observed") or {}).get("status") == "hls_variant_measured"
        else "generated_source_variant_failed"
    )
    report["lowering_evidence"] = {
        "firrtl_to_systemverilog": True,
        "verilator_build": True,
        "gpu_library_build": True,
        "direct_callsite_bridge_build": True,
        "direct_callsite_run": report["status"] == "generated_source_variant_measured",
    }
    return report
