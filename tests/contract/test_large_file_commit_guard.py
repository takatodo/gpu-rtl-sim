import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.tools import check_staged_large_files
from tests.contract.large_file_commit_guard_helpers import subprocess_result


class LargeFileCommitGuardTest(unittest.TestCase):
    def test_oversized_files_reports_only_entries_above_limit(self) -> None:
        files = [
            check_staged_large_files.FileSize("small.txt", 100),
            check_staged_large_files.FileSize("large.bin", 101),
        ]

        failures = check_staged_large_files.oversized_files(files, max_bytes=100)

        self.assertEqual(failures, [check_staged_large_files.FileSize("large.bin", 101)])

    def test_paths_mode_rejects_large_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            large_path = Path(temp_dir) / "large.bin"
            large_path.write_bytes(b"x" * 17)

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main(["--max-bytes", "16", "--paths", str(large_path)])

        self.assertEqual(status, 1)
        self.assertIn("files larger than 16 B", stderr.getvalue())
        self.assertIn("large.bin: 17 B", stderr.getvalue())
        self.assertIn("GPU_TOGGLE_MAX_COMMIT_FILE_BYTES=<bytes>", stderr.getvalue())

    def test_paths_mode_accepts_small_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            small_path = Path(temp_dir) / "small.txt"
            small_path.write_text("small", encoding="utf-8")

            status = check_staged_large_files.main(["--max-bytes", "16", "--paths", str(small_path)])

        self.assertEqual(status, 0)

    def test_main_fails_closed_when_git_size_check_fails(self) -> None:
        with mock.patch("src.tools.check_staged_large_files.staged_blobs") as blobs, mock.patch(
            "src.tools.check_staged_large_files.subprocess.run"
        ) as run:
            blobs.return_value = [check_staged_large_files.StagedBlob(path="large.bin", object_id="a" * 40)]
            run.return_value = subprocess_result(stdout="", stderr="fatal: bad object", returncode=128)

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main([])

        self.assertEqual(status, 2)
        self.assertIn("unable to verify staged file sizes", stderr.getvalue())
        self.assertIn("fatal: bad object", stderr.getvalue())

    def test_invalid_env_threshold_fails_closed_without_traceback(self) -> None:
        with mock.patch.dict("os.environ", {"GPU_TOGGLE_MAX_COMMIT_FILE_BYTES": "not-an-int"}):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main(["--paths"])

        self.assertEqual(status, 2)
        self.assertIn("invalid commit guard threshold", stderr.getvalue())
        self.assertIn("must be an integer", stderr.getvalue())

    def test_cli_threshold_overrides_invalid_env_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.dict(
            "os.environ", {"GPU_TOGGLE_MAX_COMMIT_FILE_BYTES": "not-an-int"}
        ):
            small_path = Path(temp_dir) / "small.txt"
            small_path.write_text("small", encoding="utf-8")

            status = check_staged_large_files.main(["--max-bytes", "16", "--paths", str(small_path)])

        self.assertEqual(status, 0)

    def test_paths_mode_rejects_too_many_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = []
            for index in range(3):
                path = Path(temp_dir) / f"file_{index}.txt"
                path.write_text("small", encoding="utf-8")
                paths.append(str(path))

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main(["--max-bytes", "16", "--max-files", "2", "--paths", *paths])

        self.assertEqual(status, 1)
        self.assertIn("3 staged files exceeds", stderr.getvalue())
        self.assertIn("limit of 2", stderr.getvalue())
        self.assertIn("GPU_TOGGLE_MAX_COMMIT_FILE_COUNT=<count>", stderr.getvalue())

    def test_invalid_file_count_env_fails_closed_without_traceback(self) -> None:
        with mock.patch.dict("os.environ", {"GPU_TOGGLE_MAX_COMMIT_FILE_COUNT": "many"}):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main(["--paths"])

        self.assertEqual(status, 2)
        self.assertIn("invalid commit guard threshold", stderr.getvalue())
        self.assertIn("GPU_TOGGLE_MAX_COMMIT_FILE_COUNT must be an integer", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
