import contextlib
import io
import unittest
from pathlib import Path
from unittest import mock

from src.tools import check_staged_large_files


REPO_ROOT = Path(__file__).resolve().parents[2]


class LargeFileCommitGuardScriptGrowthTest(unittest.TestCase):
    def test_guarded_script_path_scope_is_limited_to_tooling_scripts(self) -> None:
        self.assertTrue(check_staged_large_files.is_guarded_script_path("src/tools/run_results_reproduction.py"))
        self.assertTrue(check_staged_large_files.is_guarded_script_path(".githooks/pre-commit"))
        self.assertTrue(check_staged_large_files.is_guarded_script_path(".githooks/pre-commit.sh"))
        self.assertFalse(check_staged_large_files.is_guarded_script_path("tests/contract/test_large_file_commit_guard.py"))
        self.assertFalse(check_staged_large_files.is_guarded_script_path("docs/status.md"))

    def test_guarded_contract_test_path_scope_is_limited_to_contract_tests(self) -> None:
        self.assertTrue(
            check_staged_large_files.is_guarded_contract_test_path(
                "tests/contract/test_full_ita_mha_larger_paged_kv_next.py"
            )
        )
        self.assertFalse(check_staged_large_files.is_guarded_contract_test_path("tests/contract/helper.py"))
        self.assertFalse(check_staged_large_files.is_guarded_contract_test_path("tests/unit/test_small.py"))
        self.assertFalse(check_staged_large_files.is_guarded_contract_test_path("src/tools/test_helper.py"))

    def test_script_growth_limit_rejects_large_single_script_delta(self) -> None:
        with mock.patch("src.tools.check_staged_large_files.staged_blobs") as blobs, mock.patch(
            "src.tools.check_staged_large_files.batch_object_size_map"
        ) as size_map, mock.patch(
            "src.tools.check_staged_large_files.staged_script_growth"
        ) as script_growth, mock.patch(
            "src.tools.check_staged_large_files.staged_new_script_count"
        ) as new_script_count, mock.patch(
            "src.tools.check_staged_large_files.staged_script_sizes"
        ) as script_sizes:
            blobs.return_value = [check_staged_large_files.StagedBlob(path="src/tools/new_flow.py", object_id="a" * 40)]
            size_map.return_value = {"a" * 40: 100}
            script_growth.return_value = [check_staged_large_files.ScriptGrowth("src/tools/new_flow.py", 251)]
            new_script_count.return_value = 0
            script_sizes.return_value = []

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main(["--max-script-added-lines", "250"])

        self.assertEqual(status, 1)
        self.assertIn("guarded scripts are growing too much", stderr.getvalue())
        self.assertIn("src/tools/new_flow.py: +251 lines", stderr.getvalue())
        self.assertIn("GPU_TOGGLE_MAX_SCRIPT_ADDED_LINES=<lines>", stderr.getvalue())

    def test_new_script_count_limit_rejects_many_new_tool_scripts(self) -> None:
        with mock.patch("src.tools.check_staged_large_files.staged_blobs") as blobs, mock.patch(
            "src.tools.check_staged_large_files.batch_object_size_map"
        ) as size_map, mock.patch(
            "src.tools.check_staged_large_files.staged_script_growth"
        ) as script_growth, mock.patch(
            "src.tools.check_staged_large_files.staged_new_script_count"
        ) as new_script_count, mock.patch(
            "src.tools.check_staged_large_files.staged_script_sizes"
        ) as script_sizes:
            blobs.return_value = [
                check_staged_large_files.StagedBlob(path="src/tools/a.py", object_id="a" * 40),
                check_staged_large_files.StagedBlob(path="src/tools/b.py", object_id="b" * 40),
            ]
            size_map.return_value = {"a" * 40: 100, "b" * 40: 100}
            script_growth.return_value = []
            new_script_count.return_value = 2
            script_sizes.return_value = []

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main(["--max-new-script-files", "1"])

        self.assertEqual(status, 1)
        self.assertIn("2 new guarded scripts exceeds the limit of 1", stderr.getvalue())
        self.assertIn("GPU_TOGGLE_MAX_NEW_SCRIPT_FILES=<count>", stderr.getvalue())

    def test_script_total_line_limit_rejects_large_staged_script(self) -> None:
        with mock.patch("src.tools.check_staged_large_files.staged_blobs") as blobs, mock.patch(
            "src.tools.check_staged_large_files.batch_object_size_map"
        ) as size_map, mock.patch(
            "src.tools.check_staged_large_files.staged_script_growth"
        ) as script_growth, mock.patch(
            "src.tools.check_staged_large_files.staged_new_script_count"
        ) as new_script_count, mock.patch(
            "src.tools.check_staged_large_files.staged_script_sizes"
        ) as script_sizes:
            blobs.return_value = [check_staged_large_files.StagedBlob(path="src/tools/large_flow.py", object_id="a" * 40)]
            size_map.return_value = {"a" * 40: 100}
            script_growth.return_value = []
            new_script_count.return_value = 0
            script_sizes.return_value = [check_staged_large_files.ScriptSize("src/tools/large_flow.py", 301)]

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main(["--max-script-total-lines", "300"])

        self.assertEqual(status, 1)
        self.assertIn("guarded scripts exceed the total line budget", stderr.getvalue())
        self.assertIn("src/tools/large_flow.py: 301 lines", stderr.getvalue())
        self.assertIn("GPU_TOGGLE_MAX_SCRIPT_TOTAL_LINES=<lines>", stderr.getvalue())

    def test_guarded_scripts_in_worktree_stay_below_total_line_budget(self) -> None:
        guarded_paths = [
            path
            for root in (REPO_ROOT / "src" / "tools", REPO_ROOT / ".githooks")
            for path in root.rglob("*")
            if path.is_file() and check_staged_large_files.is_guarded_script_path(path.relative_to(REPO_ROOT).as_posix())
        ]

        oversized = []
        for path in guarded_paths:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_count > check_staged_large_files.DEFAULT_MAX_SCRIPT_TOTAL_LINES:
                oversized.append(f"{path.relative_to(REPO_ROOT).as_posix()}: {line_count} lines")

        self.assertEqual(oversized, [])

    def test_invalid_script_growth_env_fails_closed_without_traceback(self) -> None:
        with mock.patch.dict("os.environ", {"GPU_TOGGLE_MAX_SCRIPT_ADDED_LINES": "lots"}):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main(["--paths"])

        self.assertEqual(status, 2)
        self.assertIn("invalid commit guard threshold", stderr.getvalue())
        self.assertIn("GPU_TOGGLE_MAX_SCRIPT_ADDED_LINES must be an integer", stderr.getvalue())

    def test_invalid_script_total_lines_env_fails_closed_without_traceback(self) -> None:
        with mock.patch.dict("os.environ", {"GPU_TOGGLE_MAX_SCRIPT_TOTAL_LINES": "huge"}):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main(["--paths"])

        self.assertEqual(status, 2)
        self.assertIn("invalid commit guard threshold", stderr.getvalue())
        self.assertIn("GPU_TOGGLE_MAX_SCRIPT_TOTAL_LINES must be an integer", stderr.getvalue())

    def test_readme_documents_hook_and_commit_cadence(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        status = (REPO_ROOT / "docs" / "status.md").read_text(encoding="utf-8")
        hook = (REPO_ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8")

        self.assertIn("git config core.hooksPath .githooks", readme)
        self.assertIn("check_staged_large_files.py", readme)
        self.assertIn("GPU_TOGGLE_MAX_COMMIT_FILE_COUNT", readme)
        self.assertIn("GPU_TOGGLE_MAX_SCRIPT_ADDED_LINES", readme)
        self.assertIn("GPU_TOGGLE_MAX_NEW_SCRIPT_FILES", readme)
        self.assertIn("GPU_TOGGLE_MAX_SCRIPT_TOTAL_LINES", readme)
        self.assertIn("GPU_TOGGLE_MAX_CONTRACT_TEST_ADDED_LINES", readme)
        self.assertIn("GPU_TOGGLE_MAX_CONTRACT_TEST_TOTAL_LINES", readme)
        self.assertIn("Commit cadence", readme)
        self.assertIn("Operator shortcuts", readme)
        self.assertIn("make check", readme)
        self.assertNotIn("src/tools/repo.py", readme)
        self.assertIn("Local disk hygiene", readme)
        self.assertIn("python3 -m venv artifacts/mobile_vit/venv", readme)
        self.assertIn("artifacts/mobile_vit/venv/bin/python -m pip install -r requirements/mobile_vit.txt", readme)
        self.assertIn("Commit guard state", status)
        self.assertIn("100` staged non-submodule file changes including deletions and type changes", status)
        self.assertIn("250` added lines per guarded script", status)
        self.assertIn("300` total lines per guarded script", status)
        self.assertIn("3` new guarded scripts", status)
        self.assertIn("contract tests above `1200` total lines", status)
        self.assertIn("skips submodule gitlinks", status)
        self.assertIn("artifacts/", status)
        self.assertIn("src/tools/check_staged_large_files.py", hook)


if __name__ == "__main__":
    unittest.main()
