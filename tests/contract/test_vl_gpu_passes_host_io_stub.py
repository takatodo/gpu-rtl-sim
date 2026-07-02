from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


class VlGpuPassesHostIoStubTest(unittest.TestCase):
    def test_host_io_stub_covers_finish_flush_and_invoke_call_sites(self) -> None:
        source = (REPO_ROOT / "src" / "passes" / "VlGpuPasses.cpp").read_text(encoding="utf-8")

        self.assertIn('Name.starts_with("_Z12VL_FINISH_MT")', source)
        self.assertIn('Name.starts_with("_ZN9Verilated17runFlushCallbacksEv")', source)
        self.assertIn('Name.contains("VlDelayScheduler")', source)
        self.assertIn('Name.contains("VlCoroutineHandle")', source)
        self.assertIn('Name.contains("_Rb_tree")', source)
        self.assertIn('Name.contains("St8multimapIm")', source)
        self.assertIn("SmallVector<std::pair<CallBase *, Function *>", source)
        self.assertIn("dyn_cast<CallBase>", source)
        self.assertIn("dyn_cast<InvokeInst>", source)
        self.assertIn("BranchInst::Create(II->getNormalDest(), II)", source)
        self.assertIn("HasRemainingEhPad", source)
        self.assertIn("isa<LandingPadInst>", source)
        self.assertIn("isa<ResumeInst>", source)
        self.assertIn("F.hasPersonalityFn() && !HasRemainingEhPad", source)
        self.assertIn("shouldPreserveGpuDiagnosticOptNone", source)
        self.assertIn('"vlgpu.eval_hot_path_compact_cluster_outline_callee"', source)
        self.assertIn('"__vlgpu_compact_cluster_outline_frame_stub"', source)
        self.assertIn("Attribute::OptimizeNone", source)
        self.assertIn("if (PreserveNoInline || PreserveOptNone)", source)
        self.assertGreaterEqual(source.count("static bool isRequired() { return true; }"), 5)


if __name__ == "__main__":
    unittest.main()
