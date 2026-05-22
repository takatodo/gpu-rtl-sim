#!/usr/bin/env python3
"""Contract checks for tracked src/tools import closure."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "tools"
CONTRACT_TEST_DIR = REPO_ROOT / "tests" / "contract"
MANIFEST_SOURCE_PATH = REPO_ROOT / "src" / "tools" / "results_reproduction_manifest_sources.py"
TRACKED_REFERENCE_PREFIXES = (
    "README.md",
    "config/",
    "docs/",
    "src/tools/",
    "tests/contract/",
)


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


class PublicPackSourceBoundaryTest(unittest.TestCase):
    def test_public_pack_source_paths_are_tracked(self) -> None:
        tracked = tracked_paths()
        violations = [path for path in public_pack_source_paths() if path not in tracked]

        self.assertEqual(violations, [])

    def test_public_pack_source_paths_include_tracked_local_imports(self) -> None:
        violations = public_pack_local_import_edges(public_pack_source_paths())

        self.assertEqual(violations, [])

    def test_public_pack_record_paths_are_tracked(self) -> None:
        tracked = tracked_paths()
        violations = [path for path in public_pack_record_paths() if path not in tracked]

        self.assertEqual(violations, [])


class TrackedReferenceBoundaryTest(unittest.TestCase):
    def test_active_surface_does_not_reference_untracked_tool_paths(self) -> None:
        violations = untracked_tool_path_references(tracked_paths())

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


if __name__ == "__main__":
    unittest.main()
