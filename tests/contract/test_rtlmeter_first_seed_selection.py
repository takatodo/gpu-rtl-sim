from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterFirstSeedSelectionTest(HybridCliTestCase):
    def test_selects_one_seed_without_mutating_project_selection(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_seed_selection import rtlmeter_first_seed_selection

        selection = rtlmeter_first_seed_selection()

        self.assertEqual(selection["surface"], "rtlmeter_first_seed_selection")
        self.assertEqual(selection["status"], "candidate_selected_not_configured")
        self.assertEqual(selection["selected_seed"], "Example:kind:hello")
        self.assertEqual(selection["selection_scope"], "rtlmeter_user_path_plumbing_candidate")
        self.assertFalse(selection["config_selection_json_updated"])
        self.assertFalse(selection["config_targets_json_updated"])
        self.assertFalse(selection["active_project_priority_changed"])
        self.assertFalse(selection["canonical_project_state_changed"])
        self.assertIn("non-canonical planning metadata", selection["source_of_truth_note"])
        self.assertIn("no broad RTLMeter acceleration claim", selection["non_goals"])
        self.assertIn("no performance or speedup claim from the seed decision", selection["non_goals"])
        self.assertIn("no source-of-truth change from this helper", selection["non_goals"])

    def test_candidate_summary_defers_overlay_heavy_targets(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_seed_selection import rtlmeter_first_seed_selection

        selection = rtlmeter_first_seed_selection()
        candidates = selection["candidate_summary"]

        self.assertEqual(candidates["Example:kind:hello"]["decision"], "selected")
        self.assertEqual(candidates["OpenTitan primitive overlay"]["decision"], "defer")
        self.assertEqual(candidates["TL-UL target"]["decision"], "defer")
        self.assertEqual(candidates["NVDLA CMAC"]["decision"], "defer")
        self.assertIn("CPU/GPU compare integration", selection["next_gate_before_config_update"])
