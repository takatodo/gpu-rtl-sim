import json
import re
import subprocess

from tests.contract.hybrid_cli_helpers import REPO_ROOT, HybridCliTestCase


DESCRIPTOR = REPO_ROOT / "overlays/rtlmeter/patches/rtlmeter_veer_eh_mailbox_observable_public_flat.json"
PATCH = REPO_ROOT / "overlays/rtlmeter/patches/rtlmeter_veer_eh_mailbox_observable_public_flat.patch"


class RtlmeterVeerMailboxObservablePatchTest(HybridCliTestCase):
    def setUp(self) -> None:
        self.descriptor = json.loads(DESCRIPTOR.read_text(encoding="utf-8"))
        self.patch_text = PATCH.read_text(encoding="utf-8")

    def test_descriptor_scopes_patch_to_eh_mailbox_observables(self) -> None:
        self.assertEqual(self.descriptor["descriptor_name"], "rtlmeter_veer_eh_mailbox_observable_public_flat")
        self.assertEqual(self.descriptor["apply_scope"], "repo_root_rtlmeter_submodule_worktree")
        self.assertTrue(self.descriptor["patch_behavior"]["adds_public_flat_to_mailbox_write"])
        self.assertTrue(self.descriptor["patch_behavior"]["adds_public_flat_to_write_data"])
        self.assertFalse(self.descriptor["patch_behavior"]["changes_testbench_behavior"])
        self.assertTrue(self.descriptor["patch_behavior"]["does_not_claim_sidecar_execution"])
        self.assertIn("tb_top__DOT__mailbox_write", self.descriptor["expected_new_root_markers"])

    def test_allowed_touched_files_match_patch(self) -> None:
        changed = sorted(re.findall(r"^\+\+\+ b/(.+)$", self.patch_text, flags=re.MULTILINE))
        self.assertEqual(changed, sorted(self.descriptor["allowed_touched_files"]))
        self.assertEqual(
            changed,
            [
                "third_party/rtlmeter/designs/VeeR-EH1/src/tb_top.sv",
                "third_party/rtlmeter/designs/VeeR-EH2/src/tb_top.sv",
            ],
        )

    def test_patch_adds_public_flat_only_to_mailbox_valid_and_data(self) -> None:
        self.assertIn("mailbox_write /* verilator public_flat */", self.patch_text)
        self.assertEqual(self.patch_text.count("mailbox_write /* verilator public_flat */"), 2)
        self.assertIn("WriteData /* verilator public_flat */", self.patch_text)
        self.assertEqual(self.patch_text.count("WriteData /* verilator public_flat */"), 2)
        self.assertNotIn("gpu_execution_claimed=true", self.patch_text)

    def test_patch_applies_to_current_rtlmeter_worktree(self) -> None:
        apply_check = subprocess.run(
            ["git", "apply", "--check", PATCH.as_posix()],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if apply_check.returncode == 0:
            return
        reverse_check = subprocess.run(
            ["git", "apply", "--reverse", "--check", PATCH.as_posix()],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            reverse_check.returncode,
            0,
            msg=apply_check.stderr + reverse_check.stderr,
        )
        for rel_path in self.descriptor["allowed_touched_files"]:
            source_text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            self.assertIn("mailbox_write /* verilator public_flat */", source_text)
            self.assertIn("WriteData /* verilator public_flat */", source_text)


if __name__ == "__main__":
    import unittest

    unittest.main()
