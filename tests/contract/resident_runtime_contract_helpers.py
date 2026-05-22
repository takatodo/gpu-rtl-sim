import importlib
import sys

from tests.contract.resident_runtime_contract_constants import (
    DEFAULT_SELECTION_EVIDENCE_KEYS,
    REPO_ROOT,
    SPECIAL_SELECTION_EVIDENCE_PATHS,
)


class ResidentRuntimeContractHelpers:
    def _load_tool_module(self, module_name: str):
        tools_dir = str(REPO_ROOT / "src" / "tools")
        added = False
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
            added = True
        try:
            return importlib.import_module(module_name)
        finally:
            if added:
                sys.path.remove(tools_dir)

    def _load_selection(self) -> dict:
        module = self._load_tool_module("selection_state")
        return module.load_selection(REPO_ROOT)

    def _assert_selection_evidence_paths(self, selection: dict) -> None:
        evidence = selection["completed_goal_evidence"]
        for key in DEFAULT_SELECTION_EVIDENCE_KEYS:
            self.assertEqual(evidence[key], f"config/scaling_gates/{key}.json")
        for key, expected in SPECIAL_SELECTION_EVIDENCE_PATHS.items():
            self.assertEqual(evidence[key], expected)

    def _collect_template_source_paths(self, value, *, absolute_paths: list[str]):
        source_prefixes = (
            "config/scaling_gates/",
            "config/slice_launch_templates/",
            "overlays/rtlmeter/",
            "third_party/rtlmeter/",
        )
        if isinstance(value, dict):
            for child in value.values():
                yield from self._collect_template_source_paths(child, absolute_paths=absolute_paths)
        elif isinstance(value, list):
            for child in value:
                yield from self._collect_template_source_paths(child, absolute_paths=absolute_paths)
        elif isinstance(value, str):
            if value.startswith(source_prefixes):
                yield value
            elif value.startswith("/"):
                absolute_paths.append(value)
