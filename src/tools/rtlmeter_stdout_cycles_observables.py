"""Shared RTLMeter stdout/cycles observable helpers."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


TIMESTAMP_PREFIX_RE = re.compile(r"^\s*[0-9]+(?:\.[0-9]+)?\s+\|\s?")


def normalized_rtlmeter_stdout(text: str) -> str:
    lines = [TIMESTAMP_PREFIX_RE.sub("", line).rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def required_observable_files_missing(execute_dir: Path, prefix: str) -> list[str]:
    missing: list[str] = []
    if not (execute_dir / "_execute" / "stdout.log").is_file():
        missing.append(f"{prefix}._execute/stdout.log")
    if not (execute_dir / "_rtlmeter_cycles.txt").is_file():
        missing.append(f"{prefix}._rtlmeter_cycles.txt")
    return missing


def compare_rtlmeter_observables(cpu_execute_dir: Path, gpu_execute_dir: Path) -> dict[str, object]:
    cpu_stdout = normalized_rtlmeter_stdout((cpu_execute_dir / "_execute" / "stdout.log").read_text(encoding="utf-8"))
    gpu_stdout = normalized_rtlmeter_stdout((gpu_execute_dir / "_execute" / "stdout.log").read_text(encoding="utf-8"))
    cpu_cycles = int((cpu_execute_dir / "_rtlmeter_cycles.txt").read_text(encoding="utf-8").strip())
    gpu_cycles = int((gpu_execute_dir / "_rtlmeter_cycles.txt").read_text(encoding="utf-8").strip())
    stdout_match = cpu_stdout == gpu_stdout
    cycles_match = cpu_cycles == gpu_cycles
    return {
        "status": "passed" if stdout_match and cycles_match else "failed",
        "normalized_stdout_match": stdout_match,
        "cycle_count_match": cycles_match,
        "cpu_cycles": cpu_cycles,
        "gpu_cycles": gpu_cycles,
        "cpu_stdout_sha256": hashlib.sha256(cpu_stdout.encode("utf-8")).hexdigest(),
        "gpu_stdout_sha256": hashlib.sha256(gpu_stdout.encode("utf-8")).hexdigest(),
    }
