#!/usr/bin/env python3
"""Contract checks for tracked src/tools import closure."""

from __future__ import annotations

import ast
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "tools"


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


if __name__ == "__main__":
    unittest.main()
