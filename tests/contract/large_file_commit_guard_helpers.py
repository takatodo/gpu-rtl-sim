import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def guard_tool_paths() -> list[Path]:
    return sorted((REPO_ROOT / "src" / "tools").glob("check_staged_large_files*.py"))


def subprocess_result(*, stdout: str | bytes, returncode: int, stderr: str | bytes = "") -> object:
    return type("Completed", (), {"stdout": stdout, "stderr": stderr, "returncode": returncode})()


def init_versioned_hook_repo(repo: Path) -> None:
    (repo / ".githooks").mkdir()
    (repo / "src" / "tools").mkdir(parents=True)
    shutil.copy(REPO_ROOT / ".githooks" / "pre-commit", repo / ".githooks" / "pre-commit")
    for source in guard_tool_paths():
        shutil.copy(source, repo / "src" / "tools" / source.name)

    run_git(repo, "init", "-q")
    run_git(repo, "config", "user.email", "test@example.com")
    run_git(repo, "config", "user.name", "Test")
    run_git(repo, "config", "core.hooksPath", ".githooks")


def commit_versioned_hook_baseline(repo: Path) -> None:
    run_git(
        repo,
        "add",
        ".githooks/pre-commit",
        *(f"src/tools/{path.name}" for path in guard_tool_paths()),
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"],
        cwd=repo,
        check=True,
        env={
            **os.environ,
            "GPU_TOGGLE_MAX_SCRIPT_ADDED_LINES": "1000",
            "GPU_TOGGLE_MAX_NEW_SCRIPT_FILES": "14",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def run_rejected_git_commit(repo: Path, message: str, **env_overrides: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        check=False,
        env={**os.environ, **env_overrides},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
