from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def expand_cpp_globs(command: list[str]) -> list[str]:
    expanded: list[str] = []
    for arg in command:
        if arg.endswith("/*.cpp"):
            glob_dir = Path(arg[:-6])
            if not glob_dir.is_absolute():
                glob_dir = REPO_ROOT / glob_dir
            matches = sorted(glob_dir.glob("*.cpp"))
            if not matches:
                raise FileNotFoundError(f"no Verilator C++ files matched {arg}")
            expanded.extend(display_path(path) for path in matches)
        else:
            expanded.append(arg)
    return expanded


def run_compile_command(command: list[str]) -> None:
    subprocess.run(expand_cpp_globs(command), cwd=REPO_ROOT, check=True)
