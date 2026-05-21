import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.tools import check_staged_large_files


REPO_ROOT = Path(__file__).resolve().parents[2]


class LargeFileCommitGuardGeneratedOutputTest(unittest.TestCase):
    def test_artifacts_paths_are_rejected_as_generated_output(self) -> None:
        files = [
            check_staged_large_files.FileSize("src/tool.py", 10),
            check_staged_large_files.FileSize("artifacts/generated.bin", 10),
        ]

        self.assertEqual(
            check_staged_large_files.forbidden_source_paths(entry.path for entry in files),
            ["artifacts/generated.bin"],
        )

    def test_reports_paths_are_not_forbidden_by_generated_output_guard(self) -> None:
        files = [
            check_staged_large_files.FileSize("reports/summary.json", 10),
            check_staged_large_files.FileSize("src/tool.py", 10),
        ]

        self.assertEqual(check_staged_large_files.forbidden_source_paths(entry.path for entry in files), [])

    def test_absolute_artifacts_path_under_repo_is_rejected_as_generated_output(self) -> None:
        artifact_path = REPO_ROOT / "artifacts" / "generated.bin"

        self.assertEqual(
            check_staged_large_files.forbidden_source_paths([str(artifact_path)]),
            [str(artifact_path)],
        )

    def test_paths_mode_rejects_artifacts_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_dir = Path(temp_dir) / "artifacts"
            artifact_dir.mkdir()
            artifact_path = artifact_dir / "generated.bin"
            artifact_path.write_bytes(b"x")

            relative_artifact_path = "artifacts/generated.bin"
            with mock.patch("src.tools.check_staged_large_files.filesystem_file_sizes") as sizes:
                sizes.return_value = [check_staged_large_files.FileSize(relative_artifact_path, 1)]
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    status = check_staged_large_files.main(["--paths", str(artifact_path)])

        self.assertEqual(status, 1)
        self.assertIn("artifacts/ is generated output", stderr.getvalue())
        self.assertIn(relative_artifact_path, stderr.getvalue())

    def test_staged_artifacts_skip_blob_size_lookup(self) -> None:
        with mock.patch("src.tools.check_staged_large_files.staged_blobs") as blobs, mock.patch(
            "src.tools.check_staged_large_files.batch_object_size_map"
        ) as size_map, mock.patch(
            "src.tools.check_staged_large_files.staged_script_growth"
        ) as script_growth, mock.patch(
            "src.tools.check_staged_large_files.staged_new_script_count"
        ) as new_script_count:
            blobs.return_value = [
                check_staged_large_files.StagedBlob(path="artifacts/generated.bin", object_id="a" * 40),
            ]
            script_growth.return_value = []
            new_script_count.return_value = 0

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main([])

        self.assertEqual(status, 1)
        self.assertIn("artifacts/ is generated output", stderr.getvalue())
        size_map.assert_not_called()

    def test_staged_count_limit_skips_blob_size_lookup(self) -> None:
        with mock.patch("src.tools.check_staged_large_files.staged_blobs") as blobs, mock.patch(
            "src.tools.check_staged_large_files.batch_object_size_map"
        ) as size_map, mock.patch(
            "src.tools.check_staged_large_files.staged_script_growth"
        ) as script_growth, mock.patch(
            "src.tools.check_staged_large_files.staged_new_script_count"
        ) as new_script_count:
            blobs.return_value = [
                check_staged_large_files.StagedBlob(path="a.txt", object_id="a" * 40),
                check_staged_large_files.StagedBlob(path="b.txt", object_id="b" * 40),
                check_staged_large_files.StagedBlob(path="c.txt", object_id="c" * 40),
            ]
            script_growth.return_value = []
            new_script_count.return_value = 0

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main(["--max-files", "2"])

        self.assertEqual(status, 1)
        self.assertIn("3 staged files exceeds", stderr.getvalue())
        size_map.assert_not_called()

    def test_deleted_staged_files_count_toward_commit_limit(self) -> None:
        with mock.patch("src.tools.check_staged_large_files.staged_blobs") as blobs, mock.patch(
            "src.tools.check_staged_large_files.batch_object_size_map"
        ) as size_map, mock.patch(
            "src.tools.check_staged_large_files.staged_script_growth"
        ) as script_growth, mock.patch(
            "src.tools.check_staged_large_files.staged_new_script_count"
        ) as new_script_count:
            blobs.return_value = [
                check_staged_large_files.StagedBlob(path="old_a.txt", object_id=None),
                check_staged_large_files.StagedBlob(path="old_b.txt", object_id=None),
                check_staged_large_files.StagedBlob(path="old_c.txt", object_id=None),
            ]
            script_growth.return_value = []
            new_script_count.return_value = 0

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main(["--max-files", "2"])

        self.assertEqual(status, 1)
        self.assertIn("3 staged files exceeds", stderr.getvalue())
        size_map.assert_not_called()

    def test_staged_count_limit_still_reports_artifacts_paths(self) -> None:
        with mock.patch("src.tools.check_staged_large_files.staged_blobs") as blobs, mock.patch(
            "src.tools.check_staged_large_files.batch_object_size_map"
        ) as size_map, mock.patch(
            "src.tools.check_staged_large_files.staged_script_growth"
        ) as script_growth, mock.patch(
            "src.tools.check_staged_large_files.staged_new_script_count"
        ) as new_script_count:
            blobs.return_value = [
                check_staged_large_files.StagedBlob(path="artifacts/generated.bin", object_id="a" * 40),
                check_staged_large_files.StagedBlob(path="src/a.txt", object_id="b" * 40),
                check_staged_large_files.StagedBlob(path="src/b.txt", object_id="c" * 40),
            ]
            script_growth.return_value = []
            new_script_count.return_value = 0

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_staged_large_files.main(["--max-files", "2"])

        error_text = stderr.getvalue()
        self.assertEqual(status, 1)
        self.assertIn("artifacts/ is generated output", error_text)
        self.assertIn("3 staged files exceeds", error_text)
        size_map.assert_not_called()


if __name__ == "__main__":
    unittest.main()
