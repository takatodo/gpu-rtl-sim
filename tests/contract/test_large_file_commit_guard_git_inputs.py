import subprocess
import unittest
from unittest import mock

from src.tools import check_staged_large_files
from tests.contract.large_file_commit_guard_helpers import subprocess_result


class LargeFileCommitGuardGitInputTest(unittest.TestCase):
    def test_batch_object_size_map_deduplicates_object_ids(self) -> None:
        with mock.patch("src.tools.check_staged_large_files.batch_object_sizes") as batch_sizes:
            batch_sizes.return_value = [10, 20]

            size_map = check_staged_large_files.batch_object_size_map(["a", "b", "a"])

        self.assertEqual(size_map, {"a": 10, "b": 20})
        batch_sizes.assert_called_once_with(["a", "b"])

    def test_staged_blobs_parses_rename_records(self) -> None:
        raw = b":100644 100644 " + b"a" * 40 + b" " + b"b" * 40 + b" R100\0old name.txt\0new name.txt\0"
        with mock.patch("src.tools.check_staged_large_files.subprocess.run") as run:
            run.return_value = subprocess_result(stdout=raw, returncode=0)

            blobs = check_staged_large_files.staged_blobs()

        self.assertEqual(blobs, [check_staged_large_files.StagedBlob(path="new name.txt", object_id="b" * 40)])
        self.assertEqual(run.call_args.args[0], ["git", "diff", "--cached", "--raw", "-z", "--diff-filter=ACMRDT"])

    def test_staged_blobs_skips_submodule_gitlinks(self) -> None:
        raw = b":160000 160000 " + b"a" * 40 + b" " + b"b" * 40 + b" M\0third_party/ITA\0"
        with mock.patch("src.tools.check_staged_large_files.subprocess.run") as run:
            run.return_value = subprocess_result(stdout=raw, returncode=0)

            blobs = check_staged_large_files.staged_blobs()

        self.assertEqual(blobs, [])

    def test_staged_blobs_skips_file_to_gitlink_typechange(self) -> None:
        raw = b":100644 160000 " + b"a" * 40 + b" " + b"b" * 40 + b" T\0third_party/ITA\0"
        with mock.patch("src.tools.check_staged_large_files.subprocess.run") as run:
            run.return_value = subprocess_result(stdout=raw, returncode=0)

            blobs = check_staged_large_files.staged_blobs()

        self.assertEqual(blobs, [])

    def test_staged_blobs_skips_gitlink_to_file_typechange(self) -> None:
        raw = b":160000 100644 " + b"a" * 40 + b" " + b"b" * 40 + b" T\0third_party/ITA\0"
        with mock.patch("src.tools.check_staged_large_files.subprocess.run") as run:
            run.return_value = subprocess_result(stdout=raw, returncode=0)

            blobs = check_staged_large_files.staged_blobs()

        self.assertEqual(blobs, [])

    def test_staged_blobs_counts_deleted_paths_without_size_lookup_id(self) -> None:
        raw = b":100644 000000 " + b"a" * 40 + b" " + b"0" * 40 + b" D\0old.txt\0"
        with mock.patch("src.tools.check_staged_large_files.subprocess.run") as run:
            run.return_value = subprocess_result(stdout=raw, returncode=0)

            blobs = check_staged_large_files.staged_blobs()

        self.assertEqual(blobs, [check_staged_large_files.StagedBlob(path="old.txt", object_id=None)])

    def test_staged_blobs_counts_typechanges(self) -> None:
        raw = b":120000 100644 " + b"a" * 40 + b" " + b"b" * 40 + b" T\0script.sh\0"
        with mock.patch("src.tools.check_staged_large_files.subprocess.run") as run:
            run.return_value = subprocess_result(stdout=raw, returncode=0)

            blobs = check_staged_large_files.staged_blobs()

        self.assertEqual(blobs, [check_staged_large_files.StagedBlob(path="script.sh", object_id="b" * 40)])

    def test_staged_script_growth_uses_new_path_for_rename_records(self) -> None:
        stdout = b"12\t3\t\0src/tools/old_flow.py\0src/tools/new_flow.py\0"
        with mock.patch("src.tools.check_staged_large_files.subprocess.run") as run:
            run.return_value = subprocess_result(stdout=stdout, returncode=0)

            growth = check_staged_large_files.staged_script_growth()

        self.assertEqual(growth, [check_staged_large_files.ScriptGrowth("src/tools/new_flow.py", 12)])
        self.assertEqual(run.call_args.args[0], ["git", "diff", "--cached", "--numstat", "-z", "--diff-filter=ACMRT"])

    def test_staged_script_growth_counts_typechange_records(self) -> None:
        stdout = b"300\t0\tsrc/tools/from_symlink.py\0"
        with mock.patch("src.tools.check_staged_large_files.subprocess.run") as run:
            run.return_value = subprocess_result(stdout=stdout, returncode=0)

            growth = check_staged_large_files.staged_script_growth()

        self.assertEqual(growth, [check_staged_large_files.ScriptGrowth("src/tools/from_symlink.py", 300)])
        self.assertEqual(run.call_args.args[0], ["git", "diff", "--cached", "--numstat", "-z", "--diff-filter=ACMRT"])

    def test_staged_new_script_count_counts_rename_into_guarded_scope(self) -> None:
        raw = b":100644 100644 " + b"a" * 40 + b" " + b"b" * 40 + b" R100\0docs/helper.py\0src/tools/helper.py\0"
        with mock.patch("src.tools.check_staged_large_files.subprocess.run") as run:
            run.return_value = subprocess_result(stdout=raw, returncode=0)

            count = check_staged_large_files.staged_new_script_count()

        self.assertEqual(count, 1)
        self.assertEqual(run.call_args.args[0], ["git", "diff", "--cached", "--raw", "-z", "--diff-filter=ACMR"])

    def test_staged_new_script_count_does_not_count_guarded_rename_within_scope(self) -> None:
        raw = b":100644 100644 " + b"a" * 40 + b" " + b"b" * 40 + b" R100\0src/tools/old.py\0src/tools/new.py\0"
        with mock.patch("src.tools.check_staged_large_files.subprocess.run") as run:
            run.return_value = subprocess_result(stdout=raw, returncode=0)

            count = check_staged_large_files.staged_new_script_count()

        self.assertEqual(count, 0)

    def test_staged_new_script_count_counts_copied_guarded_script(self) -> None:
        raw = b":100644 100644 " + b"a" * 40 + b" " + b"b" * 40 + b" C100\0docs/template.py\0src/tools/copied.py\0"
        with mock.patch("src.tools.check_staged_large_files.subprocess.run") as run:
            run.return_value = subprocess_result(stdout=raw, returncode=0)

            count = check_staged_large_files.staged_new_script_count()

        self.assertEqual(count, 1)

    def test_staged_script_sizes_reads_staged_blob_line_count(self) -> None:
        blobs = [
            check_staged_large_files.StagedBlob(path="src/tools/tool.py", object_id="a" * 40),
            check_staged_large_files.StagedBlob(path="docs/status.md", object_id="b" * 40),
            check_staged_large_files.StagedBlob(path="src/tools/deleted.py", object_id=None),
        ]
        with mock.patch("src.tools.check_staged_large_files.subprocess.run") as run:
            run.return_value = subprocess_result(stdout=b"one\ntwo\nthree", returncode=0)

            sizes = check_staged_large_files.staged_script_sizes(blobs)

        self.assertEqual(sizes, [check_staged_large_files.ScriptSize("src/tools/tool.py", 3)])
        run.assert_called_once_with(
            ["git", "cat-file", "-p", "a" * 40],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


if __name__ == "__main__":
    unittest.main()
