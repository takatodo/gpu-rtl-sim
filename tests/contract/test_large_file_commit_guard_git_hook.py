import os
import stat
import tempfile
import unittest
from pathlib import Path

from tests.contract.large_file_commit_guard_helpers import (
    REPO_ROOT,
    commit_versioned_hook_baseline,
    init_versioned_hook_repo,
    run_git,
    run_rejected_git_commit,
)


class LargeFileCommitGuardGitHookTest(unittest.TestCase):
    def test_versioned_hook_is_executable(self) -> None:
        hook = REPO_ROOT / ".githooks" / "pre-commit"

        self.assertTrue(os.access(hook, os.X_OK))

    def test_versioned_hook_runs_active_surface_boundary_when_available(self) -> None:
        hook = (REPO_ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8")

        self.assertIn("test_tracked_tool_dependency_boundary", hook)
        self.assertIn("[ -f tests/contract/test_tracked_tool_dependency_boundary.py ]", hook)

    def test_versioned_hook_blocks_oversized_git_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_versioned_hook_repo(repo)
            (repo / "small.txt").write_text("small", encoding="utf-8")
            run_git(repo, "add", "small.txt")
            run_git(repo, "commit", "-q", "-m", "init")

            (repo / "large.bin").write_bytes(b"x" * 17)
            run_git(repo, "add", "large.bin")
            commit = run_rejected_git_commit(repo, "large", GPU_TOGGLE_MAX_COMMIT_FILE_BYTES="16")

        self.assertNotEqual(commit.returncode, 0)
        self.assertIn("files larger than 16 B", commit.stderr)
        self.assertIn("large.bin: 17 B", commit.stderr)

    def test_versioned_hook_blocks_guarded_script_growth_git_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_versioned_hook_repo(repo)
            commit_versioned_hook_baseline(repo)

            tool = repo / "src" / "tools" / "check_staged_large_files.py"
            with tool.open("a", encoding="utf-8") as stream:
                stream.write("\n# extra line one\n# extra line two\n")
            run_git(repo, "add", "src/tools/check_staged_large_files.py")
            commit = run_rejected_git_commit(repo, "script growth", GPU_TOGGLE_MAX_SCRIPT_ADDED_LINES="1")

        self.assertNotEqual(commit.returncode, 0)
        self.assertIn("guarded scripts are growing too much", commit.stderr)
        self.assertIn("src/tools/check_staged_large_files.py: +", commit.stderr)

    def test_versioned_hook_blocks_guarded_script_typechange_growth_git_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_versioned_hook_repo(repo)
            commit_versioned_hook_baseline(repo)

            symlink_path = repo / "src" / "tools" / "from_symlink.py"
            symlink_path.symlink_to("target")
            run_git(repo, "add", "src/tools/from_symlink.py")
            run_git(repo, "commit", "-q", "-m", "add symlink script")
            symlink_path.unlink()
            symlink_path.write_text("line one\nline two\n", encoding="utf-8")
            run_git(repo, "add", "src/tools/from_symlink.py")
            commit = run_rejected_git_commit(repo, "typechange growth", GPU_TOGGLE_MAX_SCRIPT_ADDED_LINES="1")

        self.assertNotEqual(commit.returncode, 0)
        self.assertIn("guarded scripts are growing too much", commit.stderr)
        self.assertIn("src/tools/from_symlink.py: +2 lines", commit.stderr)

    def test_versioned_hook_blocks_rename_into_guarded_scope_git_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_versioned_hook_repo(repo)
            (repo / "docs").mkdir()
            commit_versioned_hook_baseline(repo)

            for name in ("a.py", "b.py"):
                (repo / "docs" / name).write_text("print('small')\n", encoding="utf-8")
            run_git(repo, "add", "docs/a.py", "docs/b.py")
            run_git(repo, "commit", "-q", "-m", "add docs scripts")
            run_git(repo, "mv", "docs/a.py", "src/tools/a.py")
            run_git(repo, "mv", "docs/b.py", "src/tools/b.py")
            commit = run_rejected_git_commit(
                repo,
                "move scripts into guarded scope",
                GPU_TOGGLE_MAX_NEW_SCRIPT_FILES="1",
            )

        self.assertNotEqual(commit.returncode, 0)
        self.assertIn("2 new guarded scripts exceeds the limit of 1", commit.stderr)

    def test_versioned_hook_blocks_new_large_contract_test_git_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_versioned_hook_repo(repo)
            (repo / "tests" / "contract").mkdir(parents=True)
            (repo / "small.txt").write_text("small", encoding="utf-8")
            run_git(repo, "add", "small.txt")
            run_git(repo, "commit", "-q", "-m", "init")

            contract_test = repo / "tests" / "contract" / "test_generated_large_gate.py"
            contract_test.write_text("line one\nline two\nline three\n", encoding="utf-8")
            run_git(repo, "add", "tests/contract/test_generated_large_gate.py")
            commit = run_rejected_git_commit(
                repo,
                "large contract test",
                GPU_TOGGLE_MAX_CONTRACT_TEST_TOTAL_LINES="2",
            )

        self.assertNotEqual(commit.returncode, 0)
        self.assertIn("guarded contract tests are too large or growing too much", commit.stderr)
        self.assertIn("tests/contract/test_generated_large_gate.py: 3 lines", commit.stderr)


if __name__ == "__main__":
    unittest.main()
