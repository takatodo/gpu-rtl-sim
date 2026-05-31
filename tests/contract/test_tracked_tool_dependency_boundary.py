#!/usr/bin/env python3
"""Contract checks for tracked src/tools import closure."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "tools"
CONTRACT_TEST_DIR = REPO_ROOT / "tests" / "contract"
MANIFEST_SOURCE_PATH = REPO_ROOT / "src" / "tools" / "results_reproduction_manifest_sources.py"
SELECTION_PATH = REPO_ROOT / "config" / "selection.json"
CONFIG_MINIMAL_SURFACE_AUDIT_PATH = (
    REPO_ROOT / "records" / "scaling_gates" / "config_minimal_surface_completion_audit.json"
)
PUBLIC_PACK_TOOL_ROOTS = (
    "run_results_reproduction",
    "compare_vl_hybrid_cli",
    "run_vl_hybrid",
    "run_hybrid_benchmark",
    "run_hybrid_template",
    "gen_hybrid_config",
    "build_host_probe",
    "build_vl_gpu",
    "mobile_vit_hybrid_imagenet_cli",
    "mobile_vit_hybrid_imagenet_eval",
    "mobile_vit_imagenet_manifest_cli",
    "verilator_sidecar_shim",
)
TRACKED_TOOL_ROOTS = (
    *PUBLIC_PACK_TOOL_ROOTS,
    "check_staged_large_files",
    "gen_vl_gpu_kernel",
    "llvm_stub_gen",
    "named_patch_lowering",
    "run_tlul_fifo_sync_cpu_baseline",
    "run_tlul_fifo_sync_scaling_validation",
    "selection_state",
    "verilator_native_option_parser_sidecar_handoff",
    "verilator_native_option_parser_sidecar_plan_resolution",
    "verilator_native_option_parser_direct_command_path_fixture",
    "verilator_native_option_parser_direct_native_invocation_fixture",
    "verilator_native_option_parser_direct_stage_plan_materialization",
    "verilator_native_option_parser_stub_fixture",
)
TRACKED_REFERENCE_PREFIXES = (
    "AGENTS.md",
    "README.md",
    "config/",
    "docs/",
    "records/README.md",
    "src/tools/",
    "tests/contract/",
)
REPO_PATH_REFERENCE_PATTERN = re.compile(
    r"(?:(?:config/scaling_gates)|(?:records/scaling_gates)|(?:overlays)|(?:src/tools)|(?:tests/contract))"
    r"/[A-Za-z0-9_./-]+"
)
GATE_RECORD_NAME_PATTERN = re.compile(r"[A-Za-z0-9_.-]+\.json")


def tracked_paths() -> set[str]:
    return set(
        subprocess.check_output(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            text=True,
        ).splitlines()
    )


def local_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "import_module"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            imports.add(node.args[0].value.split(".")[0])
    return {
        module
        for module in imports
        if (TOOLS_DIR / f"{module}.py").exists()
    }


def reachable_local_modules(root: str) -> set[str]:
    seen: set[str] = set()
    stack = [root]
    while stack:
        module = stack.pop()
        if module in seen:
            continue
        seen.add(module)
        module_path = TOOLS_DIR / f"{module}.py"
        if module_path.exists():
            stack.extend(sorted(local_imports(module_path) - seen))
    return seen


class TrackedToolDependencyBoundaryTest(unittest.TestCase):
    def test_tracked_tools_do_not_depend_on_untracked_local_helpers(self) -> None:
        tracked = tracked_paths()
        tracked_tool_roots = sorted(
            Path(path).stem
            for path in tracked
            if path.startswith("src/tools/") and path.endswith(".py")
        )
        violations = []

        for root in tracked_tool_roots:
            for module in sorted(reachable_local_modules(root)):
                module_path = f"src/tools/{module}.py"
                if (TOOLS_DIR / f"{module}.py").exists() and module_path not in tracked:
                    violations.append(f"{root}->{module_path}")

        self.assertEqual(violations, [])

    def test_tracked_contract_tests_do_not_depend_on_untracked_local_helpers(self) -> None:
        tracked = tracked_paths()
        tracked_contract_tests = sorted(
            path
            for path in tracked
            if path.startswith("tests/contract/") and path.endswith(".py")
        )
        violations = []

        for test_path in tracked_contract_tests:
            for module in sorted(contract_test_imports(REPO_ROOT / test_path)):
                module_path = f"tests/contract/{module}.py"
                if (CONTRACT_TEST_DIR / f"{module}.py").exists() and module_path not in tracked:
                    violations.append(f"{test_path}->{module_path}")

        self.assertEqual(violations, [])

    def test_tracked_tools_are_reachable_from_declared_roots(self) -> None:
        tracked = tracked_paths()
        expected = set()
        for root in TRACKED_TOOL_ROOTS:
            expected.update(reachable_local_modules(root))

        self.assertEqual(sorted(tracked_tool_modules(tracked) - expected), [])


def contract_test_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    prefix = "tests.contract."
    for node in ast.walk(tree):
        modules = []
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        for module in modules:
            if module.startswith(prefix):
                imports.add(module.removeprefix(prefix).split(".")[0])
    return imports


def public_pack_source_paths() -> tuple[str, ...]:
    namespace: dict[str, object] = {}
    exec(MANIFEST_SOURCE_PATH.read_text(encoding="utf-8"), namespace)
    paths = namespace["PUBLIC_PACK_SOURCE_PATHS"]
    if not isinstance(paths, tuple):
        raise AssertionError("PUBLIC_PACK_SOURCE_PATHS must be a tuple")
    return paths


def public_pack_tool_modules() -> set[str]:
    return {
        Path(path).stem
        for path in public_pack_source_paths()
        if path.startswith("src/tools/") and path.endswith(".py")
    }


def tracked_tool_modules(paths: set[str]) -> set[str]:
    return {
        Path(path).stem
        for path in paths
        if path.startswith("src/tools/") and path.endswith(".py")
    }


def tracked_gate_record_count(paths: set[str]) -> int:
    return len(
        [
            path
            for path in paths
            if path.startswith("records/scaling_gates/") and path.endswith(".json")
        ]
    )


def public_pack_record_paths() -> tuple[str, ...]:
    sys.path.insert(0, str(TOOLS_DIR))
    try:
        from results_reproduction_manifest import PUBLIC_PACK_RECORD_PATHS
    finally:
        sys.path.pop(0)
    return PUBLIC_PACK_RECORD_PATHS


def _looks_like_tool_path(token: str) -> str | None:
    path = token.strip("`'\".,:;)(")
    if path.startswith("src/tools/") and path.endswith(".py"):
        return path
    return None


def tracked_active_surface_files(paths: set[str]) -> list[str]:
    return sorted(
        path
        for path in paths
        if path.endswith((".py", ".md", ".json", ".txt"))
        and any(path == prefix or path.startswith(prefix) for prefix in TRACKED_REFERENCE_PREFIXES)
    )


def untracked_tool_path_references(paths: set[str]) -> list[str]:
    violations: list[str] = []
    for path in tracked_active_surface_files(paths):
        source = REPO_ROOT / path
        if not source.exists():
            continue
        for lineno, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            for token in line.replace("\\", " ").split():
                tool_path = _looks_like_tool_path(token)
                if tool_path and (REPO_ROOT / tool_path).exists() and tool_path not in paths:
                    violations.append(f"{path}:{lineno}->{tool_path}")
    return violations


def _canonical_reference_path(reference: str) -> str:
    path = reference.strip("`'\".,:;)]}")
    if path.startswith("config/scaling_gates/"):
        return f"records/scaling_gates/{Path(path).name}"
    return path


def untracked_repo_path_references(paths: set[str]) -> list[str]:
    violations: list[str] = []
    for path in tracked_active_surface_files(paths):
        source = REPO_ROOT / path
        if not source.exists():
            continue
        for lineno, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            for match in REPO_PATH_REFERENCE_PATTERN.finditer(line):
                reference = match.group(0)
                canonical = _canonical_reference_path(reference)
                if (REPO_ROOT / canonical).is_file() and canonical not in paths:
                    violations.append(f"{path}:{lineno}->{reference}")
    return violations


def public_pack_local_import_edges(paths: tuple[str, ...]) -> list[str]:
    manifest_paths = set(paths)
    edges: list[str] = []
    for path in sorted(paths):
        source = REPO_ROOT / path
        if not path.startswith("src/tools/") or not source.exists():
            continue
        for module in sorted(local_imports(source)):
            dependency = f"src/tools/{module}.py"
            if dependency not in manifest_paths:
                edges.append(f"{path}->{dependency}")
    return edges


def public_pack_record_untracked_references(paths: tuple[str, ...], tracked: set[str]) -> list[str]:
    violations: list[str] = []
    for path in sorted(paths):
        source = REPO_ROOT / path
        if not source.exists():
            continue
        for lineno, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            for match in REPO_PATH_REFERENCE_PATTERN.finditer(line):
                reference = match.group(0)
                canonical = _canonical_reference_path(reference)
                if (REPO_ROOT / canonical).is_file() and canonical not in tracked:
                    violations.append(f"{path}:{lineno}->{reference}")
    return violations


def active_gate_record_references(paths: set[str]) -> set[str]:
    references = set(public_pack_record_paths())
    tracked_records_by_name = {
        Path(path).name: path
        for path in paths
        if path.startswith("records/scaling_gates/") and path.endswith(".json")
    }
    for path in tracked_active_surface_files(paths):
        source = REPO_ROOT / path
        if not source.exists():
            continue
        text = source.read_text(encoding="utf-8")
        for match in REPO_PATH_REFERENCE_PATTERN.finditer(text):
            reference = _canonical_reference_path(match.group(0))
            if reference.startswith("records/scaling_gates/") and reference.endswith(".json"):
                references.add(reference)
        for match in GATE_RECORD_NAME_PATTERN.finditer(text):
            reference = tracked_records_by_name.get(match.group(0))
            if reference:
                references.add(reference)
    return references


class PublicPackSourceBoundaryTest(unittest.TestCase):
    def test_public_pack_records_are_explicit_not_candidate_filtered(self) -> None:
        manifest_source = MANIFEST_SOURCE_PATH.with_name("results_reproduction_manifest.py").read_text(encoding="utf-8")

        self.assertNotIn("_PUBLIC_PACK_RECORD_CANDIDATE_PATHS", manifest_source)
        self.assertNotIn("_tracked_or_packaged_record_paths", manifest_source)

    def test_public_pack_source_paths_are_tracked(self) -> None:
        tracked = tracked_paths()
        violations = [path for path in public_pack_source_paths() if path not in tracked]

        self.assertEqual(violations, [])

    def test_public_pack_source_paths_include_tracked_local_imports(self) -> None:
        violations = public_pack_local_import_edges(public_pack_source_paths())

        self.assertEqual(violations, [])

    def test_public_pack_tool_sources_are_reachable_from_public_entrypoints(self) -> None:
        expected = set()
        for root in PUBLIC_PACK_TOOL_ROOTS:
            expected.update(reachable_local_modules(root))

        self.assertEqual(sorted(public_pack_tool_modules() - expected), [])

    def test_public_pack_record_paths_are_tracked(self) -> None:
        tracked = tracked_paths()
        violations = [path for path in public_pack_record_paths() if path not in tracked]

        self.assertEqual(violations, [])

    def test_public_pack_records_do_not_reference_existing_untracked_repo_files(self) -> None:
        tracked = tracked_paths()
        violations = public_pack_record_untracked_references(public_pack_record_paths(), tracked)

        self.assertEqual(violations, [])


class TrackedReferenceBoundaryTest(unittest.TestCase):
    def test_active_surface_does_not_reference_untracked_tool_paths(self) -> None:
        violations = untracked_tool_path_references(tracked_paths())

        self.assertEqual(violations, [])

    def test_active_surface_does_not_reference_existing_untracked_repo_paths(self) -> None:
        violations = untracked_repo_path_references(tracked_paths())

        self.assertEqual(violations, [])

    def test_tracked_templates_do_not_reference_untracked_repo_overlays(self) -> None:
        tracked = tracked_paths()
        violations = []
        for path in sorted(
            item
            for item in tracked
            if item.startswith("config/slice_launch_templates/") and item.endswith(".json")
        ):
            data = json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))
            refs = []
            source_files = data.get("source_files")
            if isinstance(source_files, list):
                refs.extend(item for item in source_files if isinstance(item, str))
            planned_overlay = data.get("planned_overlay")
            if isinstance(planned_overlay, dict):
                refs.extend(
                    planned_overlay[key]
                    for key in ("coverage_tb_path", "coverage_manifest_path")
                    if isinstance(planned_overlay.get(key), str)
                )
            for ref in refs:
                if ref.startswith("overlays/") and (REPO_ROOT / ref).exists() and ref not in tracked:
                    violations.append(f"{path}->{ref}")

        self.assertEqual(violations, [])

    def test_tracked_gate_records_are_referenced_by_active_surface(self) -> None:
        tracked = tracked_paths()
        references = active_gate_record_references(tracked)
        unreferenced = sorted(
            path
            for path in tracked
            if path.startswith("records/scaling_gates/")
            and path.endswith(".json")
            and path not in references
        )

        self.assertEqual(unreferenced, [])

    def test_canonical_gate_record_counts_match_tracked_surface(self) -> None:
        tracked_count = tracked_gate_record_count(tracked_paths())
        selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
        audit = json.loads(CONFIG_MINIMAL_SURFACE_AUDIT_PATH.read_text(encoding="utf-8"))

        self.assertEqual(selection["repository_cleanup"]["records_scaling_gate_json_count"], tracked_count)
        self.assertEqual(audit["measured_state"]["records_scaling_gate_json_count"], tracked_count)


if __name__ == "__main__":
    unittest.main()
