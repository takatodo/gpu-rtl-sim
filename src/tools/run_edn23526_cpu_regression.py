#!/usr/bin/env python3
"""Run the OpenTitan #23526 EDN valid/ready oracle on supplied revisions."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOP = "edn_csrng_23526_tb"
TESTBENCH = REPO_ROOT / "examples" / "edn23526" / f"{TOP}.sv"
PRIM_ALIAS = REPO_ROOT / "examples" / "edn23526" / "prim_generic_aliases.sv"
ACTION_DOMAIN = ("error_ack_backpressured",)
RTL_RELATIVE_PATHS = (
    "hw/top_earlgrey/rtl/top_pkg.sv",
    "hw/ip/prim/rtl/prim_mubi_pkg.sv",
    "hw/ip/prim/rtl/prim_util_pkg.sv",
    "hw/ip/prim/rtl/prim_secded_pkg.sv",
    "hw/ip/prim/rtl/prim_count_pkg.sv",
    "hw/ip/prim/rtl/prim_alert_pkg.sv",
    "hw/ip/entropy_src/rtl/entropy_src_pkg.sv",
    "hw/ip/csrng/rtl/csrng_pkg.sv",
    "hw/ip/edn/rtl/edn_reg_pkg.sv",
    "hw/ip/edn/rtl/edn_pkg.sv",
    "hw/ip/prim_generic/rtl/prim_generic_flop.sv",
    "hw/ip/prim_generic/rtl/prim_generic_flop_2sync.sv",
    "hw/ip/prim_generic/rtl/prim_generic_buf.sv",
    "hw/ip/prim_generic/rtl/prim_generic_xor2.sv",
    "hw/ip/prim/rtl/prim_sec_anchor_buf.sv",
    "hw/ip/prim/rtl/prim_intr_hw.sv",
    "hw/ip/prim/rtl/prim_edge_detector.sv",
    "hw/ip/prim/rtl/prim_mubi4_sync.sv",
    "hw/ip/prim/rtl/prim_fifo_sync_cnt.sv",
    "hw/ip/prim/rtl/prim_fifo_sync.sv",
    "hw/ip/prim/rtl/prim_count.sv",
    "hw/ip/prim/rtl/prim_arbiter_ppc.sv",
    "hw/ip/prim/rtl/prim_packer.sv",
    "hw/ip/prim/rtl/prim_packer_fifo.sv",
    "hw/ip/prim/rtl/prim_sparse_fsm_flop.sv",
    "hw/ip/edn/rtl/edn_main_sm.sv",
    "hw/ip/edn/rtl/edn_ack_sm.sv",
    "hw/ip/edn/rtl/edn_core.sv",
)


def _compile(verilator: Path, opentitan: Path, mdir: Path) -> subprocess.CompletedProcess[str]:
    mdir.mkdir(parents=True, exist_ok=True)
    command = [
        str(verilator),
        "--binary",
        "--timing",
        "-Wno-fatal",
        "--top-module",
        TOP,
        f"-I{opentitan / 'hw/ip/prim/rtl'}",
        f"-I{opentitan / 'hw/ip/edn/rtl'}",
        f"-I{opentitan / 'hw/ip/csrng/rtl'}",
        f"-I{opentitan / 'hw/ip/entropy_src/rtl'}",
        *(str(opentitan / relative) for relative in RTL_RELATIVE_PATHS),
        str(PRIM_ALIAS),
        str(TESTBENCH),
        "--Mdir",
        str(mdir),
    ]
    return subprocess.run(command, text=True, capture_output=True)


def _parse_result(stdout: str) -> dict[str, int] | None:
    match = re.search(r"RESULT protocol_violation=(\d+) valid_after_error=(\d+)", stdout)
    if not match:
        return None
    return {
        "protocol_violation": int(match.group(1)),
        "valid_after_error": int(match.group(2)),
    }


def _git_revision(path: Path) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def _revision_result(
    label: str,
    verilator: Path,
    opentitan: Path,
    out: Path,
    *,
    expected_violation: int,
    expected_valid_after_error: int,
) -> dict[str, object]:
    missing = [str(opentitan / relative) for relative in RTL_RELATIVE_PATHS if not (opentitan / relative).is_file()]
    if missing:
        return {"label": label, "status": "unavailable", "missing_files": missing}
    mdir = out / label / "obj_dir"
    compiled = _compile(verilator, opentitan, mdir)
    binary = mdir / f"V{TOP}"
    ran = subprocess.run([str(binary)], text=True, capture_output=True) if compiled.returncode == 0 and binary.is_file() else None
    observed = _parse_result(ran.stdout) if ran is not None else None
    expected = {
        "protocol_violation": expected_violation,
        "valid_after_error": expected_valid_after_error,
    }
    return {
        "label": label,
        "opentitan_revision": _git_revision(opentitan),
        "status": "pass" if observed == expected else "fail",
        "expected": expected,
        "observed": observed,
        "compile_returncode": compiled.returncode,
        "run_returncode": ran.returncode if ran is not None else None,
        "result_lines": [line for line in ran.stdout.splitlines() if line.startswith("RESULT ")] if ran is not None else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator", type=Path, required=True)
    parser.add_argument("--bad", type=Path, required=True, help="OpenTitan checkout before #23607")
    parser.add_argument("--fixed", type=Path, required=True, help="OpenTitan checkout including #23607")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.verilator.is_file():
        parser.error(f"Verilator executable does not exist: {args.verilator}")
    report = {
        "schema_version": 1,
        "issue": "https://github.com/lowRISC/opentitan/issues/23526",
        "fix_pull_request": "https://github.com/lowRISC/opentitan/pull/23607",
        "testbench": str(TESTBENCH.relative_to(REPO_ROOT)),
        "primitive_aliases": str(PRIM_ALIAS.relative_to(REPO_ROOT)),
        "actions": {
            ACTION_DOMAIN[0]: "CSRNG ACK error while csrng_req_valid is high and csrng_req_ready is low",
        },
        "revisions": [
            _revision_result(
                "bad", args.verilator.resolve(), args.bad.resolve(), args.out.resolve(),
                expected_violation=1, expected_valid_after_error=0,
            ),
            _revision_result(
                "fixed", args.verilator.resolve(), args.fixed.resolve(), args.out.resolve(),
                expected_violation=0, expected_valid_after_error=1,
            ),
        ],
    }
    report["status"] = "pass" if all(item["status"] == "pass" for item in report["revisions"]) else "fail"
    args.out.mkdir(parents=True, exist_ok=True)
    report_path = args.out / "edn23526_cpu_regression.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(report_path)}, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
