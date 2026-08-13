#!/usr/bin/env python3
"""Run the OpenTitan #10818 TL-UL oracle against supplied source revisions.

OpenTitan and Verilator are intentionally external dependencies.  This tool
does not fetch, vendor, or modify either project; it only compiles the checked
out RTL and writes a machine-readable report under ``--out``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TESTBENCH = REPO_ROOT / "examples" / "tlul10818" / "tlul_adapter_sram_10818_tb.sv"
RTL_RELATIVE_PATHS = (
    "hw/top_earlgrey/rtl/top_pkg.sv",
    "hw/ip/prim/rtl/prim_mubi_pkg.sv",
    "hw/ip/prim/rtl/prim_util_pkg.sv",
    "hw/ip/prim/rtl/prim_secded_pkg.sv",
    "hw/ip/tlul/rtl/tlul_pkg.sv",
    "hw/ip/prim/rtl/prim_fifo_sync.sv",
    "hw/ip/tlul/rtl/tlul_cmd_intg_chk.sv",
    "hw/ip/tlul/rtl/tlul_rsp_intg_gen.sv",
    "hw/ip/tlul/rtl/tlul_data_integ_enc.sv",
    "hw/ip/tlul/rtl/tlul_sram_byte.sv",
    "hw/ip/tlul/rtl/tlul_adapter_sram.sv",
)
ACTIONS = (0, 1)


def _compile(verilator: Path, opentitan: Path, mdir: Path) -> subprocess.CompletedProcess[str]:
    command = [
        str(verilator), "--binary", "--timing", "-Wno-fatal",
        "--top-module", "tlul_adapter_sram_10818_tb",
        f"-I{opentitan / 'hw/ip/prim/rtl'}",
        f"-I{opentitan / 'hw/ip/tlul/rtl'}",
        *(str(opentitan / relative) for relative in RTL_RELATIVE_PATHS),
        str(TESTBENCH), "--Mdir", str(mdir),
    ]
    return subprocess.run(command, text=True, capture_output=True)


def _run_actions(binary: Path) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for action in ACTIONS:
        completed = subprocess.run([str(binary), f"+action={action}"], text=True, capture_output=True)
        results.append({
            "action": action,
            "returncode": completed.returncode,
            "result_lines": [line for line in completed.stdout.splitlines() if line.startswith("RESULT ")],
            "stderr_tail": completed.stderr.splitlines()[-10:],
        })
    return results


def _revision_result(label: str, verilator: Path, opentitan: Path, out: Path, expected_pass: bool) -> dict[str, object]:
    missing = [str(opentitan / relative) for relative in RTL_RELATIVE_PATHS if not (opentitan / relative).is_file()]
    if missing:
        return {"label": label, "status": "unavailable", "missing_files": missing}
    mdir = out / label / "obj_dir"
    mdir.parent.mkdir(parents=True, exist_ok=True)
    compiled = _compile(verilator, opentitan, mdir)
    compile_ok = compiled.returncode == 0
    binary = mdir / "Vtlul_adapter_sram_10818_tb"
    actions = _run_actions(binary) if compile_ok and binary.is_file() else []
    observed_pass = bool(actions) and all(item["returncode"] == 0 for item in actions)
    return {
        "label": label,
        "opentitan": str(opentitan),
        "status": "pass" if compile_ok and observed_pass == expected_pass else "fail",
        "expected_oracle_pass": expected_pass,
        "observed_oracle_pass": observed_pass,
        "compile_returncode": compiled.returncode,
        "compile_stderr_tail": compiled.stderr.splitlines()[-10:],
        "actions": actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator", type=Path, required=True)
    parser.add_argument("--bad", type=Path, required=True, help="OpenTitan checkout before #10820")
    parser.add_argument("--fixed", type=Path, required=True, help="OpenTitan checkout including #10820")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.verilator.is_file():
        parser.error(f"Verilator executable does not exist: {args.verilator}")
    report = {
        "schema_version": 1,
        "issue": "https://github.com/lowRISC/opentitan/issues/10818",
        "fix_pull_request": "https://github.com/lowRISC/opentitan/pull/10820",
        "testbench": str(TESTBENCH.relative_to(REPO_ROOT)),
        "actions": {
            "0": "malformed TL-UL Get; D accepted immediately",
            "1": "malformed TL-UL Get; D backpressured until observed",
        },
        "revisions": [
            _revision_result("bad", args.verilator.resolve(), args.bad.resolve(), args.out.resolve(), False),
            _revision_result("fixed", args.verilator.resolve(), args.fixed.resolve(), args.out.resolve(), True),
        ],
    }
    report["status"] = "pass" if all(item["status"] == "pass" for item in report["revisions"]) else "fail"
    args.out.mkdir(parents=True, exist_ok=True)
    report_path = args.out / "tlul10818_cpu_regression.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(report_path)}, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
