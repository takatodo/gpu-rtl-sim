#!/usr/bin/env python3
"""Materialize the first scientific CIRCT candidate: a 2x2 dense matmul tile."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_OUT_DIR = Path("artifacts/scientific_circt/dense_matmul_tile")
DEFAULT_REPORT = Path("reports/scientific_circt_dense_matmul_tile_materialize.json")

FIRRTL_TEXT = """FIRRTL version 4.0.0
circuit DenseMatmulTile :
  public module DenseMatmulTile :
    input a00 : UInt<16>
    input a01 : UInt<16>
    input a10 : UInt<16>
    input a11 : UInt<16>
    input b00 : UInt<16>
    input b01 : UInt<16>
    input b10 : UInt<16>
    input b11 : UInt<16>
    output c00 : UInt<33>
    output c01 : UInt<33>
    output c10 : UInt<33>
    output c11 : UInt<33>

    node p00_0 = mul(a00, b00)
    node p00_1 = mul(a01, b10)
    connect c00, add(p00_0, p00_1)
    node p01_0 = mul(a00, b01)
    node p01_1 = mul(a01, b11)
    connect c01, add(p01_0, p01_1)
    node p10_0 = mul(a10, b00)
    node p10_1 = mul(a11, b10)
    connect c10, add(p10_0, p10_1)
    node p11_0 = mul(a10, b01)
    node p11_1 = mul(a11, b11)
    connect c11, add(p11_0, p11_1)
"""

HARNESS_TEXT = r'''#include "Vsim.h"
#include "verilated.h"

#include <array>
#include <cstdint>
#include <iostream>

struct Case {
  uint16_t a00, a01, a10, a11;
  uint16_t b00, b01, b10, b11;
};

static uint64_t dot(uint16_t left0, uint16_t left1, uint16_t right0, uint16_t right1) {
  return static_cast<uint64_t>(left0) * right0 + static_cast<uint64_t>(left1) * right1;
}

int main(int argc, char **argv) {
  Verilated::commandArgs(argc, argv);
  Vsim top;
  const std::array<Case, 4> cases = {{
      {1, 2, 3, 4, 5, 6, 7, 8},
      {0, 9, 10, 0, 11, 12, 13, 14},
      {255, 17, 19, 23, 29, 31, 37, 41},
      {65535, 65534, 3, 4, 5, 6, 7, 8},
  }};

  for (const auto &c : cases) {
    top.a00 = c.a00; top.a01 = c.a01; top.a10 = c.a10; top.a11 = c.a11;
    top.b00 = c.b00; top.b01 = c.b01; top.b10 = c.b10; top.b11 = c.b11;
    top.eval();
    const uint64_t exp00 = dot(c.a00, c.a01, c.b00, c.b10);
    const uint64_t exp01 = dot(c.a00, c.a01, c.b01, c.b11);
    const uint64_t exp10 = dot(c.a10, c.a11, c.b00, c.b10);
    const uint64_t exp11 = dot(c.a10, c.a11, c.b01, c.b11);
    if (top.c00 != exp00 || top.c01 != exp01 || top.c10 != exp10 || top.c11 != exp11) {
      std::cerr << "dense_matmul_tile mismatch"
                << " got=(" << top.c00 << "," << top.c01 << "," << top.c10 << "," << top.c11 << ")"
                << " exp=(" << exp00 << "," << exp01 << "," << exp10 << "," << exp11 << ")\n";
      return 1;
    }
  }
  top.final();
  std::cout << "TEST PASSED dense_matmul_tile_cpu_reference cases=" << cases.size() << "\n";
  return 0;
}
'''


def _rel(path: Path) -> str:
    return path.as_posix()


def _sanitize(text: str) -> str:
    text = text.replace(Path.cwd().as_posix(), "<repo>")
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root)/[^\s\"']+", "<local-path>", text)


def _display_path(path: Path, out_dir: Path) -> str:
    if out_dir.is_absolute():
        try:
            return f"<out_dir>/{path.relative_to(out_dir).as_posix()}"
        except ValueError:
            return _sanitize(path.as_posix())
    return path.as_posix()


def _run(argv: list[str]) -> dict[str, Any]:
    result = subprocess.run(argv, text=True, capture_output=True, check=False)
    return {
        "argv": [_sanitize(arg) for arg in argv],
        "returncode": result.returncode,
        "stdout": _sanitize(result.stdout.strip()),
        "stderr": _sanitize(result.stderr.strip()),
    }


def materialize(
    *,
    out_dir: Path = DEFAULT_OUT_DIR,
    run_circt: bool = False,
    run_verilator_cpu: bool = False,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    firrtl = out_dir / "dense_matmul_tile.fir"
    sv = out_dir / "dense_matmul_tile.sv"
    harness = out_dir / "tb_dense_matmul_tile.cpp"
    obj_dir = out_dir / "obj_dir"
    firrtl.write_text(FIRRTL_TEXT, encoding="utf-8")
    harness.write_text(HARNESS_TEXT, encoding="utf-8")

    report: dict[str, Any] = {
        "schema_version": 1,
        "surface": "scientific_circt_dense_matmul_tile",
        "candidate": "dense_matmul_tile",
        "status": "materialized_firrtl_and_harness",
        "artifacts": {
            "firrtl": _display_path(firrtl, out_dir),
            "systemverilog": _display_path(sv, out_dir),
            "harness": _display_path(harness, out_dir),
            "obj_dir": _display_path(obj_dir, out_dir),
            "binary": _display_path(obj_dir / "Vsim", out_dir),
        },
        "toolchain": {
            "firtool": shutil.which("firtool") is not None,
            "verilator": shutil.which("verilator") is not None,
        },
        "non_claims": ["no_gpu_execution", "no_speedup_claim", "no_hybrid_partition_claim"],
        "commands": [],
    }

    if run_circt:
        if not report["toolchain"]["firtool"]:
            report["status"] = "blocked_firtool_missing"
            return report
        firtool = _run(["firtool", _rel(firrtl), "-o", _rel(sv)])
        report["commands"].append({"stage": "firtool", **firtool})
        if firtool["returncode"] != 0:
            report["status"] = "failed_firtool"
            return report
        report["status"] = "generated_systemverilog"

    if run_verilator_cpu:
        if not sv.exists():
            report["status"] = "blocked_systemverilog_missing"
            return report
        if not report["toolchain"]["verilator"]:
            report["status"] = "blocked_verilator_missing"
            return report
        build = _run([
            "verilator", "--cc", "--exe", "--timing", "-Wno-fatal",
            "--prefix", "Vsim", "--top-module", "DenseMatmulTile",
            "-Mdir", _rel(obj_dir), _rel(sv), _rel(harness), "--build",
        ])
        report["commands"].append({"stage": "verilator_build", **build})
        if build["returncode"] != 0:
            report["status"] = "failed_verilator_build"
            return report
        run = _run([_rel(obj_dir / "Vsim")])
        report["commands"].append({"stage": "cpu_reference_run", **run})
        passed = run["returncode"] == 0 and "TEST PASSED" in run["stdout"]
        report["status"] = "cpu_reference_pass" if passed else "failed_cpu_reference"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-circt", action="store_true")
    parser.add_argument("--run-verilator-cpu", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    report = materialize(
        out_dir=args.out_dir,
        run_circt=args.run_circt,
        run_verilator_cpu=args.run_verilator_cpu,
    )
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not report["status"].startswith("failed_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
