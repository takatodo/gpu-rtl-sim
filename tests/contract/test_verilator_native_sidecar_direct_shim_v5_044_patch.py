import json
import re
import subprocess

from tests.contract.hybrid_cli_helpers import REPO_ROOT, HybridCliTestCase

DESCRIPTOR = REPO_ROOT / "overlays/verilator/patches/verilator_native_sidecar_direct_shim_v5_044.json"
PATCH = REPO_ROOT / "overlays/verilator/patches/verilator_native_sidecar_direct_shim_v5_044.patch"
CHECKOUT = REPO_ROOT / "artifacts/verilator-v5.044-apply-check-pristine"


class VerilatorNativeSidecarDirectShimV5044PatchTest(HybridCliTestCase):
    def setUp(self) -> None:
        self.descriptor = json.loads(DESCRIPTOR.read_text(encoding="utf-8"))
        self.patch_text = PATCH.read_text(encoding="utf-8")

    def test_descriptor_targets_v5_044_fc061(self) -> None:
        self.assertEqual(self.descriptor["upstream_ref"], "v5.044")
        self.assertEqual(
            self.descriptor["upstream_commit"],
            "8df584ca1ddde5c8afbd15dc5fdcb677a78f9af2",
        )
        self.assertEqual(self.descriptor["fc_issue"], "FC-061")
        self.assertEqual(
            self.descriptor["driver_contract_ref"]["entrypoint_cli"],
            "build-direct-shim-smoke",
        )

    def test_allowed_touched_files_match_patch_changed_files(self) -> None:
        changed = sorted(re.findall(r"^\+\+\+ b/(.+)$", self.patch_text, flags=re.MULTILINE))
        self.assertEqual(changed, sorted(self.descriptor["allowed_touched_files"]))
        self.assertEqual(
            sorted(self.descriptor["allowed_touched_files"]),
            ["src/V3EmitMk.cpp", "src/V3Options.cpp", "src/V3Options.h"],
        )

    def test_patch_contains_parser_and_make_hook_boundary(self) -> None:
        for needle in (
            "DECL_OPTION(\"-sim-accel\"",
            "DECL_OPTION(\"-sim-accel-states\"",
            "DECL_OPTION(\"-sim-accel-steps\"",
            "m_simAccelFilelist = parseFileArg",
            "$(if $(RTLMETER_REPO_ROOT),$(abspath $(RTLMETER_REPO_ROOT)),$(abspath $(firstword $(VM_USER_DIR))))",
            "--filelist $(abspath $(firstword $(VM_USER_DIR))/",
            "VL_SIDECAR_SHIM_OBJ = $(VM_PREFIX)__native_sidecar_shim.o",
            "GPU_RTL_SIM_REPO_ROOT_DEFAULT",
            "build-direct-shim-smoke",
            "known-unsupported artifact shapes before link",
            "sidecarExeDeps = \" $(VL_SIDECAR_SHIM_OBJ)\"",
            "sidecarExeLibs = \" -ldl\"",
        ):
            self.assertIn(needle, self.patch_text)
        self.assertIn("repo_root_resolution", self.descriptor["patch_behavior"])
        self.assertNotIn("$(GPU_RTL_SIM_REPO_ROOT)", self.patch_text)
        self.assertNotIn("src/tools/build_vl_gpu.py . --force", self.patch_text)

    def test_patch_applies_to_clean_v5_044_checkout_when_available(self) -> None:
        if not CHECKOUT.is_dir():
            self.skipTest("v5.044 Verilator checkout not available")
        status = subprocess.run(
            ["git", "-C", CHECKOUT.as_posix(), "status", "--short"],
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        if status:
            self.skipTest("v5.044 Verilator checkout is dirty")
        subprocess.run(
            ["git", "-C", CHECKOUT.as_posix(), "apply", "--check", PATCH.as_posix()],
            check=True,
            cwd=REPO_ROOT,
        )
