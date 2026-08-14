#!/usr/bin/env python3
"""Run the OpenTitan #10983 entropy_src FW override timing oracle."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOP = "entropy_src_main_sm_10983_tb"
TESTBENCH = REPO_ROOT / "examples" / "entropy10983" / f"{TOP}.sv"
PRIM_ALIAS = REPO_ROOT / "examples" / "edn23526" / "prim_generic_aliases.sv"
ACTION_DOMAIN = ("health_tests_before_fw_sha3_start",)
RTL_RELATIVE_PATHS = (
    "hw/ip/prim_generic/rtl/prim_generic_flop.sv",
    "hw/ip/prim/rtl/prim_sparse_fsm_flop.sv",
    "hw/ip/entropy_src/rtl/entropy_src_main_sm.sv",
)


def _compile(verilator: Path, opentitan: Path, mdir: Path, *, fixed: bool) -> subprocess.CompletedProcess[str]:
    mdir.mkdir(parents=True, exist_ok=True)
    command = [
        str(verilator),
        "--binary",
        "--timing",
        "-Wno-fatal",
        "--top-module",
        TOP,
        f"-I{opentitan / 'hw/ip/prim/rtl'}",
        *(["-DENTROPY_SRC_10983_FIXED"] if fixed else []),
        *(str(opentitan / relative) for relative in RTL_RELATIVE_PATHS),
        str(PRIM_ALIAS),
        str(TESTBENCH),
        "--Mdir",
        str(mdir),
    ]
    return subprocess.run(command, text=True, capture_output=True)


def _parse_result(stdout: str) -> dict[str, int] | None:
    match = re.search(r"RESULT early_sha3_process=(\d+) sha3_process=(\d+) fw_start=(\d+) main_sm_err=(\d+) state=([0-9a-fA-F]+)", stdout)
    if not match:
        return None
    return {
        "early_sha3_process": int(match.group(1)),
        "sha3_process": int(match.group(2)),
        "fw_start": int(match.group(3)),
        "main_sm_err": int(match.group(4)),
        "state": int(match.group(5), 16),
    }


def _git_revision(path: Path) -> str | None:
    completed = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], text=True, capture_output=True)
    return completed.stdout.strip() if completed.returncode == 0 else None


def _revision_result(
    label: str,
    verilator: Path,
    opentitan: Path,
    out: Path,
    *,
    fixed: bool,
    expected_violation: int,
) -> dict[str, object]:
    missing = [str(opentitan / relative) for relative in RTL_RELATIVE_PATHS if not (opentitan / relative).is_file()]
    if missing:
        return {"label": label, "status": "unavailable", "missing_files": missing}
    mdir = out / label / "obj_dir"
    compiled = _compile(verilator, opentitan, mdir, fixed=fixed)
    binary = mdir / f"V{TOP}"
    ran = subprocess.run([str(binary)], text=True, capture_output=True) if compiled.returncode == 0 and binary.is_file() else None
    observed = _parse_result(ran.stdout) if ran is not None else None
    expected = {"early_sha3_process": expected_violation, "fw_start": 0, "main_sm_err": 0}
    status = "pass" if observed is not None and all(observed[key] == value for key, value in expected.items()) else "fail"
    return {
        "label": label,
        "opentitan_revision": _git_revision(opentitan),
        "status": status,
        "expected": expected,
        "observed": observed,
        "compile_returncode": compiled.returncode,
        "run_returncode": ran.returncode if ran is not None else None,
        "compile_stderr_tail": compiled.stderr.splitlines()[-20:],
        "result_lines": [line for line in ran.stdout.splitlines() if line.startswith("RESULT ")] if ran is not None else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator", type=Path, required=True)
    parser.add_argument("--bad", type=Path, required=True, help="OpenTitan checkout before #11003")
    parser.add_argument("--fixed", type=Path, required=True, help="OpenTitan checkout including #11003")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.verilator.is_file():
        parser.error(f"Verilator executable does not exist: {args.verilator}")
    args.out.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "issue": "https://github.com/lowRISC/opentitan/issues/10983",
        "fix_pull_request": "https://github.com/lowRISC/opentitan/pull/11003",
        "testbench": str(TESTBENCH.relative_to(REPO_ROOT)),
        "action_domain": list(ACTION_DOMAIN),
        "checkpoint_identity": "reset_entropy_src_main_sm_fw_override_insert_before_fw_sha3_start_v1",
        "oracle": "sha3_process_o must not assert before firmware starts the FW override insert window",
        "revisions": [
            _revision_result("bad", args.verilator.resolve(), args.bad.resolve(), args.out.resolve(), fixed=False, expected_violation=1),
            _revision_result("fixed", args.verilator.resolve(), args.fixed.resolve(), args.out.resolve(), fixed=True, expected_violation=0),
        ],
    }
    report["status"] = "pass" if all(item["status"] == "pass" for item in report["revisions"]) else "fail"
    report_path = args.out / "entropy10983_cpu_regression.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(report_path)}, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
