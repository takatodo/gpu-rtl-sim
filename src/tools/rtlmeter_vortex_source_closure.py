"""Validate the descriptor-owned source closure for Vortex mini hello gating."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import yaml


DESCRIPTOR = Path("third_party/rtlmeter/designs/Vortex/descriptor.yaml")


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected YAML object")
    return payload


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _path_records(design_root: Path, rel_paths: list[str], *, repo_root: Path) -> list[dict[str, Any]]:
    records = []
    for rel_path in rel_paths:
        path = design_root / rel_path
        records.append(
            {
                "path": _display_path(path, repo_root=repo_root),
                "descriptor_path": rel_path,
                "exists": path.is_file(),
                "size_bytes": path.stat().st_size if path.is_file() else None,
            }
        )
    return records


def _path_list_sha256(records: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(str(record["path"]).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def build_source_closure(repo_root: Path) -> dict[str, Any]:
    descriptor_path = repo_root / DESCRIPTOR
    descriptor = _load_yaml(descriptor_path)
    design_root = descriptor_path.parent
    compile_section = descriptor.get("compile")
    if not isinstance(compile_section, dict):
        raise ValueError(f"{descriptor_path}: compile section must be an object")

    verilog_sources = _string_list(compile_section.get("verilogSourceFiles"))
    include_files = _string_list(compile_section.get("verilogIncludeFiles"))
    cpp_sources = _string_list(compile_section.get("cppSourceFiles"))
    verilog_records = _path_records(design_root, verilog_sources, repo_root=repo_root)
    include_records = _path_records(design_root, include_files, repo_root=repo_root)
    cpp_records = _path_records(design_root, cpp_sources, repo_root=repo_root)
    all_records = [*verilog_records, *include_records, *cpp_records]
    missing = [record["path"] for record in all_records if not record["exists"]]
    all_sources_exist = not missing and bool(verilog_records)

    defines = compile_section.get("verilogDefines")
    if not isinstance(defines, dict):
        defines = {}
    verilator_args = _string_list(compile_section.get("verilatorArgs"))

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_source_closure",
        "status": "descriptor_source_closure_complete" if all_sources_exist else "descriptor_source_closure_incomplete",
        "descriptor": _display_path(descriptor_path, repo_root=repo_root),
        "top_module": compile_section.get("topModule"),
        "main_clock": compile_section.get("mainClock"),
        "all_sources_exist": all_sources_exist,
        "missing_paths": missing,
        "source_counts": {
            "verilog": len(verilog_records),
            "include": len(include_records),
            "cpp": len(cpp_records),
            "total": len(all_records),
        },
        "source_path_list_sha256": _path_list_sha256(all_records),
        "verilog_defines": {str(key): str(value) for key, value in sorted(defines.items())},
        "verilator_args": verilator_args,
        "source_files": verilog_records,
        "include_files": include_records,
        "cpp_source_files": cpp_records,
        "execution_authority": {
            "runtime_launchable": False,
            "why": "descriptor sources exist, but DPI memory bridge and observable runtime integration are separate execution blockers",
            "non_claims": [
                "not Vortex GPU execution",
                "not CPU-vs-hybrid timing evidence",
                "not complete sidecar runtime source closure",
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", help="Output JSON path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        summary = build_source_closure(Path(args.repo_root))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        Path(args.report_out).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
