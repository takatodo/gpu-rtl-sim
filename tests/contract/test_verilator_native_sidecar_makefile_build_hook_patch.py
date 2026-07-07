import json
import re

from tests.contract.hybrid_cli_helpers import REPO_ROOT, HybridCliTestCase

DESCRIPTOR = REPO_ROOT / "overlays/verilator/patches/verilator_native_sidecar_makefile_build_hook_v5_048.json"
PATCH = REPO_ROOT / "overlays/verilator/patches/verilator_native_sidecar_makefile_build_hook_v5_048.patch"


class VerilatorNativeSidecarMakefileBuildHookPatchTest(HybridCliTestCase):
    def setUp(self) -> None:
        self.descriptor = json.loads(DESCRIPTOR.read_text(encoding="utf-8"))
        self.patch_text = PATCH.read_text(encoding="utf-8")

    def test_descriptor_layers_after_the_parse_only_patch(self) -> None:
        self.assertEqual(self.descriptor["depends_on_patch"], "verilator_native_option_parser_sidecar_gpu_v5_048")
        self.assertEqual(self.descriptor["fc_issue"], "FC-061")

    def test_allowed_touched_files_match_patch_changed_files(self) -> None:
        changed = sorted(re.findall(r"^\+\+\+ b/(.+)$", self.patch_text, flags=re.MULTILINE))
        self.assertEqual(changed, sorted(self.descriptor["allowed_touched_files"]))
        self.assertEqual(
            sorted(self.descriptor["allowed_touched_files"]),
            ["src/V3EmitMk.cpp", "src/V3Options.cpp", "src/V3Options.h"],
        )

    def test_scope_is_direct_kernel_launch_smoke_and_does_not_launch_in_verilator(self) -> None:
        behavior = self.descriptor["patch_behavior"]
        self.assertEqual(behavior["scope"], "emit_makefile_direct_cuda_kernel_launch_smoke_hook_only")
        self.assertEqual(
            self.descriptor["driver_contract_ref"]["entrypoint_cli"],
            "build-direct-shim-smoke",
        )
        self.assertTrue(behavior["does_not_launch_sidecar_runtime_in_verilator_process"])
        self.assertTrue(behavior["does_emit_makefile_rule_that_invokes_repo_sidecar_build_driver"])
        self.assertTrue(behavior["does_not_claim_gpu_execution_from_verilate_success"])
        self.assertTrue(behavior["fails_closed_for_unsupported_or_unrecognized_closures"])
        self.assertTrue(behavior["shim_object_enters_final_link_inputs"])
        self.assertTrue(behavior["stamp_is_not_a_link_input"])

    def test_patch_emits_shim_object_as_normal_link_prereq(self) -> None:
        self.assertIn("VL_SIDECAR_STAMP = $(VM_PREFIX)__sidecar_build.stamp", self.patch_text)
        self.assertIn("VL_SIDECAR_SHIM_SRC =", self.patch_text)
        self.assertIn("src/hybrid/native_sidecar_shim.c", self.patch_text)
        self.assertIn("VL_SIDECAR_SHIM_OBJ = $(VM_PREFIX)__native_sidecar_shim.o", self.patch_text)
        self.assertIn("verilator_native_sidecar_make_driver.py", self.patch_text)
        self.assertIn("build-direct-shim-smoke", self.patch_text)
        self.assertNotIn("src/tools/build_vl_gpu.py . --force", self.patch_text)
        self.assertIn("known-unsupported artifact shapes before link", self.patch_text)
        self.assertIn("$(if $(RTLMETER_REPO_ROOT),$(abspath $(RTLMETER_REPO_ROOT)),$(abspath $(firstword $(VM_USER_DIR))))", self.patch_text)
        self.assertIn("$(VL_SIDECAR_REPO_ROOT)/src/tools", self.patch_text)
        self.assertIn("GPU_RTL_SIM_REPO_ROOT_DEFAULT", self.patch_text)
        self.assertIn("--filelist $(abspath $(firstword $(VM_USER_DIR))/", self.patch_text)
        self.assertNotIn("$(GPU_RTL_SIM_REPO_ROOT)", self.patch_text)
        self.assertIn("$(VM_PREFIX)__ALL.a\" + sidecarExeDeps", self.patch_text)
        self.assertIn("sidecarExeDeps = \" $(VL_SIDECAR_SHIM_OBJ)\"", self.patch_text)
        self.assertIn("sidecarExeLibs = \" -ldl\"", self.patch_text)
        self.assertIn("+ sidecarExeLibs + \" -o $@\\n\"", self.patch_text)
        self.assertNotIn("| $(VL_SIDECAR_STAMP)", self.patch_text)
        # Repo root resolution must not be tied to VERILATOR_ROOT.
        self.assertNotIn("$(VERILATOR_ROOT)/src/tools", self.patch_text)
        self.assertEqual(
            self.descriptor["patch_behavior"]["repo_root_resolution"],
            "VL_SIDECAR_REPO_ROOT make variable defaults to RTLMETER_REPO_ROOT when present, otherwise $(abspath $(firstword $(VM_USER_DIR))), and is passed into the shim as GPU_RTL_SIM_REPO_ROOT_DEFAULT; it is not VERILATOR_ROOT and does not require operator-provided GPU_RTL_SIM_REPO_ROOT for normal runs",
        )

    def test_patch_emits_fail_closed_fatals(self) -> None:
        for needle in (
            "--sim-accel sidecar-gpu requires --exe",
            "--sim-accel sidecar-gpu requires --top-module",
            "--sim-accel sidecar-gpu requires a -f filelist",
            "positive --sim-accel-states",
        ):
            self.assertIn(needle, self.patch_text)

    def test_filelist_capture_is_metadata_only(self) -> None:
        self.assertIn("m_simAccelFilelist", self.patch_text)
        self.assertIn(
            "preserving the original -f filelist argument",
            self.descriptor["patch_behavior"]["v3options_change_note"],
        )
