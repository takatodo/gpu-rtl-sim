import json

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterOverlaysAuditTest(HybridCliTestCase):
    def test_first_seed_requires_no_rtlmeter_overlay(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_seed_selection import SELECTED_SEED
        from rtlmeter_overlay_audit import rtlmeter_overlays_audit

        audit = rtlmeter_overlays_audit(tracked_paths=["README.md"])

        self.assertEqual(audit["surface"], "rtlmeter_overlays_audit")
        self.assertEqual(audit["status"], "audit_recorded_no_cleanup_performed")
        self.assertEqual(audit["first_seed"], SELECTED_SEED)
        self.assertEqual(audit["minimal_overlay_set_for_first_seed"], [])
        self.assertFalse(audit["first_seed_requires_repo_specific_launch_template"])
        self.assertFalse(audit["canonical_project_state_changed"])
        self.assertFalse(audit["audit_is_source_of_truth"])
        self.assertEqual(audit["audit_source"], "provided_tracked_paths")
        self.assertEqual(audit["classifications"]["first_seed_required"], [])
        self.assertEqual(audit["tracked_counts"]["rtlmeter_overlays"], 0)
        self.assert_no_local_absolute_paths(json.dumps(audit, sort_keys=True))

    def test_audit_classifies_tracked_overlay_inventory_without_deleting(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_overlay_audit import rtlmeter_overlays_audit

        audit = rtlmeter_overlays_audit(
            tracked_paths=[
                "README.md",
                "config/slice_launch_templates/prim_and2.json",
                "config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json",
                "overlays/generated/tests/filelist_paged_attention_kv_score_coverage_regions.json",
                "overlays/rtlmeter/designs/OpenTitan/src/prim_and2_gpu_cov_tb.sv",
            ]
        )
        classifications = audit["classifications"]

        self.assertEqual(audit["audit_source"], "provided_tracked_paths")
        self.assertEqual(audit["tracked_counts"]["rtlmeter_overlays"], 1)
        self.assertEqual(audit["tracked_counts"]["generated_overlays"], 1)
        self.assertEqual(audit["tracked_counts"]["legacy_launch_templates"], 1)
        self.assertIn(
            "overlays/rtlmeter/designs/OpenTitan/src/prim_and2_gpu_cov_tb.sv",
            classifications["potentially_useful_later_examples"],
        )
        self.assertIn(
            "overlays/rtlmeter/designs/OpenTitan/src/prim_and2_gpu_cov_tb.sv",
            classifications["rtlmeter_overlay_inventory_examples"],
        )
        self.assertIn(
            "overlays/generated/tests/filelist_paged_attention_kv_score_coverage_regions.json",
            classifications["tracked_generated_output_warning_examples"],
        )
        self.assertEqual(classifications["legacy_launch_template_examples"], ["config/slice_launch_templates/prim_and2.json"])
        self.assertIn(
            "overlays/rtlmeter/designs/OpenTitan/**",
            classifications["de_emphasize_from_public_rtlmeter_path"],
        )
        self.assertEqual(classifications["delete_or_archive_candidate"], [])
        self.assertIn("performs no file deletion", " ".join(audit["non_claims"]))
