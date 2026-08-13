#!/usr/bin/env python3
"""Compare CPU and GPU semantic observables for the OpenTitan #10818 tracer.

The generated C++ root contains host pointers, so this tool deliberately does
not compare raw state images.  It builds a device-clean, clock-driven wrapper,
then compares only the declared oracle observables after the same action
schedule has run on CPU and GPU.
"""

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
from run_tlul10818_cpu_regression import REPO_ROOT, RTL_RELATIVE_PATHS
from tlul10818_gpu_schedule import (
    ACTION_DOMAIN,
    RESIDENT_SCALE_STATES,
    batch_patch_script,
    patch_script as _patch_script,
    uniform_scale_patch_script,
)


TOP = "tlul_adapter_sram_10818_gpu_tb"
GPU_TB = REPO_ROOT / "examples" / "tlul10818" / f"{TOP}.sv"
CPU_DRIVER = REPO_ROOT / "examples" / "tlul10818" / "tlul_adapter_sram_10818_gpu_driver.cpp"
HYBRID_RUNNER = REPO_ROOT / "src" / "tools" / "run_vl_hybrid.py"
OBSERVABLE_SUFFIXES = {
    "done": "done_o",
    "oracle_violation": "oracle_violation_o",
    "d_error": "observed_d_error_o",
    "intg_error": "observed_intg_error_o",
    "d_data": "observed_d_data_o",
    "action_coverage": "action_coverage_o",
}


def _run(command: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, env=env, cwd=REPO_ROOT)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rtl_inputs(opentitan: Path) -> list[str]:
    return [str(opentitan / path) for path in RTL_RELATIVE_PATHS]


def _base_verilator_command(verilator: Path, opentitan: Path, mdir: Path) -> list[str]:
    return [
        str(verilator), "--cc", "-Wno-fatal", "--public-flat-rw",
        "--top-module", TOP,
        f"-I{opentitan / 'hw/ip/prim/rtl'}", f"-I{opentitan / 'hw/ip/tlul/rtl'}",
        *_rtl_inputs(opentitan), str(GPU_TB), "--Mdir", str(mdir),
    ]


def _layout_offsets(mdir: Path) -> dict[str, int]:
    fields = probe_root_layout(mdir)
    offsets: dict[str, int] = {}
    for semantic, suffix in OBSERVABLE_SUFFIXES.items():
        matches = [entry for entry in fields if str(entry["name"]).endswith(f"__DOT__{suffix}")]
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one generated field for {semantic}, got {len(matches)}")
        offsets[semantic] = int(matches[0]["offset"])
    for name in ("clk_i", "rst_ni", "start_i", "malformed_i", "d_backpressure_i"):
        matches = [entry for entry in fields if entry["name"] == name]
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one top input field {name}")
        offsets[name] = int(matches[0]["offset"])
    return offsets


def _cpu_observables(binary: Path, *, malformed: bool, backpressure: bool, state_path: Path) -> dict[str, int]:
    command = [str(binary), "--dump-state", str(state_path)]
    if backpressure:
        command.append("--backpressure")
    if malformed:
        command.append("--malformed")
    completed = subprocess.run(command, text=True, capture_output=True)
    match = re.search(
        r"RESULT done=(\d+) oracle_violation=(\d+) d_data=([0-9a-fA-F]+) d_error=(\d+) intg_error=(\d+) coverage=([0-9a-fA-F]+)",
        completed.stdout,
    )
    if completed.returncode or not match:
        raise RuntimeError(f"CPU action failed: {completed.stderr}\n{completed.stdout}")
    return {
        "done": int(match.group(1)), "oracle_violation": int(match.group(2)),
        "d_data": int(match.group(3), 16), "d_error": int(match.group(4)),
        "intg_error": int(match.group(5)), "action_coverage": int(match.group(6), 16),
    }


def _gpu_observables(state_path: Path, offsets: dict[str, int]) -> dict[str, int]:
    image = state_path.read_bytes()
    values: dict[str, int] = {}
    for name in ("done", "oracle_violation", "d_error", "intg_error", "action_coverage"):
        values[name] = image[offsets[name]]
    values["d_data"] = int.from_bytes(image[offsets["d_data"] : offsets["d_data"] + 4], "little")
    return values


def _gpu_batch_observables(state_path: Path, offsets: dict[str, int], storage_size: int) -> list[dict[str, int]]:
    image = state_path.read_bytes()
    if len(image) != storage_size * len(ACTION_DOMAIN):
        raise RuntimeError(f"unexpected batch dump bytes={len(image)} storage={storage_size}")
    output: list[dict[str, int]] = []
    for state_index in range(len(ACTION_DOMAIN)):
        base = state_index * storage_size
        values = {name: image[base + offsets[name]] for name in ("done", "oracle_violation", "d_error", "intg_error", "action_coverage")}
        values["d_data"] = int.from_bytes(image[base + offsets["d_data"] : base + offsets["d_data"] + 4], "little")
        output.append(values)
    return output


def _all_states_match(state_path: Path, offsets: dict[str, int], storage_size: int, state_count: int, expected: dict[str, int]) -> bool:
    image = state_path.read_bytes()
    if len(image) != storage_size * state_count:
        return False
    for state_index in range(state_count):
        base = state_index * storage_size
        for name in ("done", "oracle_violation", "d_error", "intg_error", "action_coverage"):
            if image[base + offsets[name]] != expected[name]:
                return False
        if int.from_bytes(image[base + offsets["d_data"] : base + offsets["d_data"] + 4], "little") != expected["d_data"]:
            return False
    return True


def _revision(
    *, label: str, opentitan: Path, expected_violation: bool, verilator: Path,
    verilator_root: Path, out: Path,
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
        return {"label": label, "status": "fail", "layout_error": str(exc)}
    binary = cpu_mdir / f"V{TOP}"
    action_results: list[dict[str, object]] = []
    for malformed in (False, True):
      for backpressure in (False, True):
        action = f"{'malformed' if malformed else 'valid'}_{'d_backpressured' if backpressure else 'd_immediate'}"
        script = revision_out / f"{action}.patch"
        script.write_text(_patch_script(offsets, malformed=malformed, backpressure=backpressure), encoding="utf-8")
        cpu_state = revision_out / f"{action}.cpu.bin"
        gpu_state = revision_out / f"{action}.gpu.bin"
        try:
            cpu = _cpu_observables(binary, malformed=malformed, backpressure=backpressure, state_path=cpu_state)
        except RuntimeError as exc:
            action_results.append({"action": action, "status": "fail", "cpu_error": str(exc)})
            continue
        gpu = _run([
            sys.executable, str(HYBRID_RUNNER), "--mdir", str(gpu_mdir), "--nstates", "1",
            "--resident-steps", "--patch-script", str(script), "--dump-state", str(gpu_state),
        ], env=env)
        observed = _gpu_observables(gpu_state, offsets) if gpu.returncode == 0 and gpu_state.is_file() else None
        matches = observed == cpu
        expected_action_violation = expected_violation and malformed
        action_results.append({
            "action": action, "status": "pass" if matches else "fail", "cpu": cpu,
            "expected_oracle_violation": expected_action_violation,
            "gpu": observed, "gpu_returncode": gpu.returncode,
            "gpu_stderr_tail": gpu.stderr.splitlines()[-10:],
        })
    valid = all(item["status"] == "pass" and bool(item["cpu"]["oracle_violation"]) == item["expected_oracle_violation"] for item in action_results)
    batch_script = revision_out / "all_actions_batch.patch"
    batch_script.write_text(batch_patch_script(offsets), encoding="utf-8")
    batch_state = revision_out / "all_actions_batch.gpu.bin"
    batch = _run([
        sys.executable, str(HYBRID_RUNNER), "--mdir", str(gpu_mdir), "--nstates", str(len(ACTION_DOMAIN)),
        "--resident-steps", "--patch-script", str(batch_script), "--dump-state", str(batch_state),
    ], env=env)
    meta_path = gpu_mdir / "vl_batch_gpu.meta.json"
    storage_size = int(json.loads(meta_path.read_text(encoding="utf-8"))["storage_size"])
    batch_observed = _gpu_batch_observables(batch_state, offsets, storage_size) if batch.returncode == 0 and batch_state.is_file() else []
    expected_by_action = {str(item["action"]): item.get("cpu") for item in action_results}
    batch_matches = len(batch_observed) == len(ACTION_DOMAIN) and all(
        batch_observed[index] == expected_by_action[action]
        for index, action in enumerate(ACTION_DOMAIN)
    )
    scale_script = revision_out / f"malformed_d_backpressured_{RESIDENT_SCALE_STATES}.patch"
    scale_script.write_text(uniform_scale_patch_script(offsets, RESIDENT_SCALE_STATES), encoding="utf-8")
    scale_state = revision_out / f"malformed_d_backpressured_{RESIDENT_SCALE_STATES}.gpu.bin"
    scale = _run([
        sys.executable, str(HYBRID_RUNNER), "--mdir", str(gpu_mdir), "--nstates", str(RESIDENT_SCALE_STATES),
        "--resident-steps", "--patch-script", str(scale_script), "--dump-state", str(scale_state),
    ], env=env)
    expected_scale = expected_by_action["malformed_d_backpressured"]
    scale_matches = scale.returncode == 0 and scale_state.is_file() and _all_states_match(scale_state, offsets, storage_size, RESIDENT_SCALE_STATES, expected_scale)
    valid = valid and batch_matches and scale_matches
    return {
        "label": label, "opentitan": str(opentitan), "expected_oracle_violation": expected_violation,
        "offsets": offsets, "actions": action_results,
        "gpu_manifest_sha256": _sha256(meta_path),
        "gpu_resident_batch": {"state_count": len(ACTION_DOMAIN), "status": "pass" if batch_matches else "fail", "observables": batch_observed, "returncode": batch.returncode, "storage_size": storage_size},
        "gpu_resident_scale": {"state_count": RESIDENT_SCALE_STATES, "action": "malformed_d_backpressured", "status": "pass" if scale_matches else "fail", "returncode": scale.returncode, "storage_size": storage_size},
        "status": "pass" if valid else "fail",
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
    if not verilator.is_file(): parser.error(f"missing Verilator executable: {verilator}")
    root = args.verilator_root.resolve() if args.verilator_root else verilator.parent.parent
    if not (root / "include").is_dir(): parser.error(f"missing Verilator include root: {root / 'include'}")
    args.out.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "issue": "https://github.com/lowRISC/opentitan/issues/10818",
        "oracle": "malformed TL-UL Get must return DataWhenError",
        "comparison": "semantic observables only; raw generated state is excluded",
        "revisions": [
            _revision(label="bad", opentitan=args.bad.resolve(), expected_violation=True, verilator=verilator, verilator_root=root, out=args.out),
            _revision(label="fixed", opentitan=args.fixed.resolve(), expected_violation=False, verilator=verilator, verilator_root=root, out=args.out),
        ],
    }
    report["status"] = "pass" if all(item["status"] == "pass" for item in report["revisions"]) else "fail"
    path = args.out / "tlul10818_gpu_equivalence.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(path)}, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
