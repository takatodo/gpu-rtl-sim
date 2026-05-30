#!/usr/bin/env python3
"""Contract checks for the compact active hybrid-runtime surface."""

import json
import subprocess
import unittest
from tests.contract.resident_runtime_contract_helpers import ResidentRuntimeContractHelpers
from tests.contract.resident_runtime_contract_constants import *


class ReducedActiveSurfaceContractTest(ResidentRuntimeContractHelpers, unittest.TestCase):
    def test_makefile_operator_shortcuts_documents_and_runs_status(self) -> None:
        readme = README.read_text(encoding="utf-8")
        makefile = REPO_ROOT / "Makefile"

        self.assertTrue(makefile.is_file())
        self.assertFalse((REPO_ROOT / "src" / "tools" / "repo.py").exists())
        self.assertIn("Operator shortcuts", readme)
        self.assertIn("make simple", readme)
        self.assertIn("make surface", readme)
        self.assertIn("make check", readme)
        self.assertIn("run_results_reproduction.py --dry-run", readme)
        self.assertNotIn("src/tools/repo.py", readme)
        makefile_text = makefile.read_text(encoding="utf-8")
        self.assertIn("surface:", makefile_text)
        self.assertIn("test_tracked_tool_dependency_boundary", makefile_text)

        completed = subprocess.run(
            ["make", "simple"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn(
            "review_verilator_native_option_parser_sidecar_handoff_boundary_gate",
            completed.stdout,
        )

    def test_selection_is_compact_current_state(self) -> None:
        raw = json.loads(SELECTION.read_text(encoding="utf-8"))
        selection = self._load_selection()

        self.assertEqual(raw["schema_version"], 3)
        self.assertEqual(raw["selection_extensions"], "config/selection_extensions.json")
        self.assertNotIn("completed_goal_evidence", raw)
        self.assertNotIn("targets", raw.get("active_scope", {}))
        self.assertIn("commands_artifact", raw.get("verification", {}))
        self.assertNotIn("commands", raw.get("verification", {}))
        self.assertTrue((REPO_ROOT / "config" / "selection_extensions.json").is_file())
        self.assertTrue((REPO_ROOT / "config" / "selection_verification_commands.json").is_file())

        self.assertLess(SELECTION.stat().st_size, 34_000)
        self.assertEqual(selection["top_level_goal"], "modern_llm_serving_rtl_hybrid_conditions")
        self.assertEqual(
            selection["current_priority"],
            "review_verilator_native_option_parser_sidecar_handoff_boundary_gate",
        )
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/define_verilator_native_option_parser_sidecar_handoff_boundary_gate.json",
        )
        self._assert_selection_evidence_paths(selection)
        self.assertEqual(selection["candidate_targets"], [])
        self.assertEqual(selection["active_scope"]["candidate_targets"], [])
        self.assertEqual(
            selection["repository_cleanup"]["selection_policy"],
            "current_state_only; historical gate details live in records/scaling_gates with config/scaling_gates as a compatibility link; generated outputs are reproducible under reports and artifacts but are not source of truth",
        )
        historical_prefixes = (
            "next_source_backed_gate_after_",
            "first_primitive_",
            "four_seed_",
            "ninety_",
        )
        self.assertFalse(
            any(key.startswith(historical_prefixes) for key in selection),
            "selection.json should not store historical gate-by-gate state",
        )

    def test_selection_source_references_resolve_to_tracked_files(self) -> None:
        selection = self._load_selection()
        tracked = set(
            subprocess.check_output(
                ["git", "ls-files"],
                cwd=REPO_ROOT,
                text=True,
            ).splitlines()
        )
        missing = []
        untracked = []
        absolute_paths = []

        def collect(value):
            if isinstance(value, dict):
                for child in value.values():
                    yield from collect(child)
            elif isinstance(value, list):
                for child in value:
                    yield from collect(child)
            elif isinstance(value, str):
                if value.startswith(("config/", "docs/", "src/", "tests/", "records/")):
                    yield value
                elif value.startswith("/"):
                    absolute_paths.append(value)

        for reference in sorted(set(collect(selection))):
            path = REPO_ROOT / reference
            if not path.exists():
                missing.append(reference)
                continue
            candidates = [reference]
            if reference.startswith("config/scaling_gates/"):
                candidates.append(reference.replace("config/scaling_gates/", "records/scaling_gates/", 1))
            if not any(candidate in tracked for candidate in candidates):
                untracked.append(reference)

        self.assertEqual(missing, [])
        self.assertEqual(untracked, [])
        self.assertEqual(absolute_paths, [])

    def test_targets_registry_matches_selection_scope(self) -> None:
        targets = json.loads(TARGETS.read_text(encoding="utf-8"))
        selection = self._load_selection()

        active_names = [target["name"] for target in targets["active_targets"]]
        self.assertEqual(len(active_names), selection["active_scope"]["active_target_count"])
        self.assertEqual(set(active_names), set(selection["active_scope"]["targets"]))
        self.assertEqual(targets["candidate_targets"], [])
        self.assertIn("tlul_fifo_sync", active_names)
        self.assertIn("pulp_ita_mha_first_hybrid_benchmark_summary.json", json.dumps(selection))
        self.assertIn("pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json", json.dumps(selection))

    def test_retired_cpu_seed_templates_are_not_active_surface(self) -> None:
        targets = json.loads(TARGETS.read_text(encoding="utf-8"))
        selection = self._load_selection()
        archived = json.loads(ARCHIVED_TARGETS.read_text(encoding="utf-8"))
        retired_templates = {
            "config/slice_launch_templates/veer_el2.json",
            "config/slice_launch_templates/xuantie_e902.json",
        }
        retired_names = {"veer_el2", "xuantie_e902"}

        self.assertFalse((REPO_ROOT / "config" / "slice_launch_templates" / "veer_el2.json").exists())
        self.assertFalse((REPO_ROOT / "config" / "slice_launch_templates" / "xuantie_e902.json").exists())

        active_text = json.dumps(
            {
                "targets": targets,
                "selection_active_scope": selection["active_scope"],
                "selection_candidate_targets": selection["candidate_targets"],
            }
        )
        for retired_template in retired_templates:
            self.assertNotIn(retired_template, active_text)
        for retired_name in retired_names:
            self.assertNotIn(f'"name": "{retired_name}"', active_text)
            self.assertNotIn(f'"{retired_name}"', json.dumps(selection["active_scope"]["targets"]))

        archived_text = json.dumps(archived)
        for retired_template in retired_templates:
            self.assertIn(retired_template, archived_text)
        for retired_name in retired_names:
            self.assertIn(f'"name": "{retired_name}"', archived_text)

    def test_active_target_references_resolve_from_checkout(self) -> None:
        targets = json.loads(TARGETS.read_text(encoding="utf-8"))
        reference_keys = (
            "launch_template_path",
            "coverage_manifest_path",
            "coverage_output_gate_path",
            "source_gate_path",
            "upstream_module_path",
        )
        missing = []
        submodule_references = []

        for target in targets["active_targets"]:
            for key in reference_keys:
                reference = target.get(key)
                if not reference:
                    continue
                if reference.startswith("third_party/"):
                    submodule_references.append(f"{target['name']}:{key}:{reference}")
                    continue
                if not (REPO_ROOT / reference).exists():
                    missing.append(f"{target['name']}:{key}:{reference}")
            for reference in target.get("depth_candidate_gates", []):
                if not (REPO_ROOT / reference).exists():
                    missing.append(f"{target['name']}:depth_candidate_gates:{reference}")

        self.assertEqual(missing, [])
        self.assertTrue(submodule_references)

    def test_active_launch_templates_reference_only_present_source_paths(self) -> None:
        targets = json.loads(TARGETS.read_text(encoding="utf-8"))
        tracked_paths = set(
            subprocess.check_output(
                ["git", "ls-files"],
                cwd=REPO_ROOT,
                text=True,
            ).splitlines()
        )
        missing = []
        submodule_references = []
        untracked = []
        absolute_paths = []

        template_paths = {
            target["launch_template_path"]
            for target in targets["active_targets"]
            if target.get("launch_template_path")
        }
        for template_path in sorted(template_paths):
            template = json.loads((REPO_ROOT / template_path).read_text(encoding="utf-8"))
            for reference in self._collect_template_source_paths(template, absolute_paths=absolute_paths):
                if reference.startswith("third_party/"):
                    submodule_references.append(f"{template_path}:{reference}")
                    continue
                if not (REPO_ROOT / reference).exists():
                    missing.append(f"{template_path}:{reference}")
                if reference.startswith(("config/slice_launch_templates/", "overlays/rtlmeter/")):
                    if reference not in tracked_paths:
                        untracked.append(f"{template_path}:{reference}")

        self.assertEqual(missing, [])
        self.assertTrue(submodule_references)
        self.assertEqual(untracked, [])
        self.assertEqual(absolute_paths, [])

    def test_canonical_third_party_submodule_boundaries_are_explicit(self) -> None:
        gitmodules = GITMODULES.read_text(encoding="utf-8")

        self.assertIn('[submodule "third_party/rtlmeter"]', gitmodules)
        self.assertIn("path = third_party/rtlmeter", gitmodules)
        self.assertIn("url = https://github.com/verilator/rtlmeter.git", gitmodules)
        self.assertIn('[submodule "third_party/ITA"]', gitmodules)
        self.assertIn("path = third_party/ITA", gitmodules)
        self.assertIn("url = https://github.com/pulp-platform/ITA.git", gitmodules)
        self.assertIn('[submodule "third_party/common_cells"]', gitmodules)
        self.assertIn("path = third_party/common_cells", gitmodules)
        self.assertIn("url = https://github.com/pulp-platform/common_cells.git", gitmodules)
        self.assertNotIn("third_party/ibex", gitmodules)

if __name__ == "__main__":
    unittest.main()
