#!/usr/bin/env python3
"""Contract checks for tracked src/tools import closure."""

from __future__ import annotations

import ast
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "tools"
CONTRACT_TEST_DIR = REPO_ROOT / "tests" / "contract"


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


if __name__ == "__main__":
    unittest.main()
