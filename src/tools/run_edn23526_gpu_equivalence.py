#!/usr/bin/env python3
"""Compare CPU and GPU semantic observables for the OpenTitan #23526 tracer."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from compare_vl_hybrid_root_layout import probe_root_layout
from edn23526_gpu_schedule import ACTION_DOMAIN, action_bits, patch_script
from run_edn23526_cpu_regression import PRIM_ALIAS, REPO_ROOT, RTL_RELATIVE_PATHS


TOP = "edn_csrng_23526_gpu_tb"
GPU_TB = REPO_ROOT / "examples" / "edn23526" / f"{TOP}.sv"
CPU_DRIVER = REPO_ROOT / "examples" / "edn23526" / "edn_csrng_23526_gpu_driver.cpp"
HYBRID_RUNNER = REPO_ROOT / "src" / "tools" / "run_vl_hybrid.py"
OBSERVABLES = (
    "done_o",
    "protocol_violation_o",
    "valid_after_error_o",
    "csrng_req_valid_seen_o",
    "action_coverage_o",
)
OBSERVABLE_KEYS = ("done", "protocol_violation", "valid_after_error", "valid_seen", "action_coverage")


def _run(command: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, env=env, cwd=REPO_ROOT)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rtl_inputs(opentitan: Path) -> list[str]:
    return [str(opentitan / path) for path in RTL_RELATIVE_PATHS]


def _base_verilator_command(verilator: Path, opentitan: Path, mdir: Path) -> list[str]:
    return [
        str(verilator), "--cc", "--timing", "-Wno-fatal", "--public-flat-rw",
        "--top-module", TOP,
        f"-I{opentitan / 'hw/ip/prim/rtl'}",
        f"-I{opentitan / 'hw/ip/edn/rtl'}",
        f"-I{opentitan / 'hw/ip/csrng/rtl'}",
        f"-I{opentitan / 'hw/ip/entropy_src/rtl'}",
        *_rtl_inputs(opentitan), str(PRIM_ALIAS), str(GPU_TB), "--Mdir", str(mdir),
    ]


def _layout_offsets(mdir: Path) -> dict[str, int]:
    fields = probe_root_layout(mdir)
    offsets: dict[str, int] = {}
    for name in ("clk_i", "rst_ni", "start_i", "inject_error_i", "csrng_ready_i", *OBSERVABLES):
        exact = [entry for entry in fields if entry["name"] == name]
        matches = exact or [entry for entry in fields if str(entry["name"]).endswith(f"__DOT__{name}")]
        if len(matches) != 1:
            raise RuntimeError(f"expected one generated field for {name}, got {len(matches)}")
        offsets[name] = int(matches[0]["offset"])
    return offsets


def _parse_cpu(stdout: str) -> dict[str, int]:
    match = re.search(
        r"RESULT done=(\d+) protocol_violation=(\d+) valid_after_error=(\d+) valid_seen=(\d+) coverage=([0-9a-fA-F]+) drive_cycles=(\d+) error=(\d+) backpressure=(\d+)",
        stdout,
    )
    if not match:
        raise RuntimeError(f"missing RESULT line:\n{stdout}")
    return {
        "done": int(match.group(1)),
        "protocol_violation": int(match.group(2)),
        "valid_after_error": int(match.group(3)),
        "valid_seen": int(match.group(4)),
        "action_coverage": int(match.group(5), 16),
        "drive_cycles": int(match.group(6)),
        "error": int(match.group(7)),
        "backpressure": int(match.group(8)),
    }


def _cpu_observables(binary: Path, state_path: Path, action: str) -> dict[str, int]:
    inject_error, backpressure = action_bits(action)
    command = [str(binary), "--dump-state", str(state_path)]
    if inject_error:
        command.append("--error-ack")
    if backpressure:
        command.append("--backpressure")
    completed = subprocess.run(command, text=True, capture_output=True)
    if completed.returncode:
        raise RuntimeError(f"CPU action failed: {completed.stderr}\n{completed.stdout}")
    return _parse_cpu(completed.stdout)


def _gpu_observables(state_path: Path, offsets: dict[str, int]) -> dict[str, int]:
    image = state_path.read_bytes()
    return {
        "done": image[offsets["done_o"]],
        "protocol_violation": image[offsets["protocol_violation_o"]],
        "valid_after_error": image[offsets["valid_after_error_o"]],
        "valid_seen": image[offsets["csrng_req_valid_seen_o"]],
        "action_coverage": image[offsets["action_coverage_o"]],
    }


def _git_revision(path: Path) -> str | None:
    completed = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], text=True, capture_output=True)
    return completed.stdout.strip() if completed.returncode == 0 else None


def _revision(
    *, label: str, opentitan: Path, fixed_revision: bool,
    verilator: Path, verilator_root: Path, out: Path,
) -> dict[str, object]:
    revision_out = out / label
    revision_out.mkdir(parents=True, exist_ok=True)
    gpu_mdir = revision_out / "gpu_obj"
    cpu_mdir = revision_out / "cpu_obj"
    env = os.environ.copy()
    env["VERILATOR_ROOT"] = str(verilator_root)
    env["PYTHONPATH"] = str(REPO_ROOT / "src" / "tools")
    gpu_compile = _run(_base_verilator_command(verilator, opentitan, gpu_mdir), env=env)
    cpu_compile = _run(_base_verilator_command(verilator, opentitan, cpu_mdir) + ["--exe", str(CPU_DRIVER), "--build"], env=env)
    if gpu_compile.returncode or cpu_compile.returncode:
        return {"label": label, "status": "fail", "gpu_compile": gpu_compile.stderr.splitlines()[-20:], "cpu_compile": cpu_compile.stderr.splitlines()[-20:]}
    build = _run([sys.executable, str(REPO_ROOT / "src/tools/build_vl_gpu.py"), str(gpu_mdir), "--force"], env=env)
    if build.returncode:
        return {"label": label, "status": "fail", "gpu_build": build.stderr.splitlines()[-20:]}
    try:
        offsets = _layout_offsets(gpu_mdir)
    except RuntimeError as exc:
        return {"label": label, "status": "fail", "error": str(exc)}
    actions: list[dict[str, object]] = []
    binary = cpu_mdir / f"V{TOP}"
    for action in ACTION_DOMAIN:
        try:
            cpu = _cpu_observables(binary, revision_out / f"{action}.cpu.bin", action)
        except RuntimeError as exc:
            actions.append({"action": action, "status": "fail", "cpu_error": str(exc)})
            continue
        script = revision_out / f"{action}.patch"
        script.write_text(patch_script(offsets, action=action, drive_cycles=cpu["drive_cycles"]), encoding="utf-8")
        gpu_state = revision_out / f"{action}.gpu.bin"
        gpu = _run([
            sys.executable, str(HYBRID_RUNNER), "--mdir", str(gpu_mdir), "--nstates", "1",
            "--resident-steps", "--patch-script", str(script), "--dump-state", str(gpu_state),
        ], env=env)
        observed = _gpu_observables(gpu_state, offsets) if gpu.returncode == 0 and gpu_state.is_file() else None
        cpu_semantic = {key: cpu[key] for key in OBSERVABLE_KEYS}
        expected_violation = int((not fixed_revision) and action == "error_ack_backpressured")
        expected_valid_after_error = int(fixed_revision and action == "error_ack_backpressured")
        matches = observed == cpu_semantic
        oracle_ok = cpu["protocol_violation"] == expected_violation
        if action == "error_ack_backpressured":
            oracle_ok = oracle_ok and cpu["valid_after_error"] == expected_valid_after_error
        actions.append({
            "action": action,
            "expected_oracle_violation": expected_violation,
            "expected_valid_after_error": expected_valid_after_error if action == "error_ack_backpressured" else None,
            "cpu": cpu_semantic,
            "gpu": observed,
            "drive_cycles": cpu["drive_cycles"],
            "gpu_returncode": gpu.returncode,
            "gpu_stderr_tail": gpu.stderr.splitlines()[-10:],
            "status": "pass" if matches and oracle_ok else "fail",
        })
    meta_path = gpu_mdir / "vl_batch_gpu.meta.json"
    return {
        "label": label,
        "opentitan_revision": _git_revision(opentitan),
        "oracle": "only error_ack_backpressured is the #23526 bug-candidate action",
        "actions": actions,
        "offsets": offsets,
        "gpu_manifest_sha256": _sha256(meta_path) if meta_path.is_file() else None,
        "status": "pass" if all(item["status"] == "pass" for item in actions) else "fail",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator", type=Path, required=True)
    parser.add_argument("--verilator-root", type=Path)
    parser.add_argument("--bad", type=Path, required=True)
    parser.add_argument("--fixed", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    verilator = args.verilator.resolve()
    if not verilator.is_file():
        parser.error(f"missing Verilator executable: {verilator}")
    root = args.verilator_root.resolve() if args.verilator_root else verilator.parent.parent
    if not (root / "include").is_dir():
        parser.error(f"missing Verilator include root: {root / 'include'}")
    args.out.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "issue": "https://github.com/lowRISC/opentitan/issues/23526",
        "fix_pull_request": "https://github.com/lowRISC/opentitan/pull/23607",
        "comparison": "semantic observables only; raw generated state is excluded",
        "action_domain": list(ACTION_DOMAIN),
        "revisions": [
            _revision(label="bad", opentitan=args.bad.resolve(), fixed_revision=False, verilator=verilator, verilator_root=root, out=args.out),
            _revision(label="fixed", opentitan=args.fixed.resolve(), fixed_revision=True, verilator=verilator, verilator_root=root, out=args.out),
        ],
    }
    report["status"] = "pass" if all(item["status"] == "pass" for item in report["revisions"]) else "fail"
    path = args.out / "edn23526_gpu_equivalence.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(path)}, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
