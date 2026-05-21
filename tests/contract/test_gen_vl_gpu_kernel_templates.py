import unittest

from src.tools import gen_vl_gpu_kernel_templates as templates


class GenVlGpuKernelTemplatesTest(unittest.TestCase):
    def test_kernel_template_lines_keep_public_entrypoints_and_annotations(self) -> None:
        lines = []
        lines.extend(templates.header_lines(storage_size=256, eval_fn="Vtop___024root___eval", vlsyms_offset=16))
        lines.extend(templates.nvvm_decl_lines())
        lines.extend(templates.init_replication_kernel_lines())
        lines.extend(
            templates.batch_kernel_lines(
                storage_size=256,
                eval_fn="Vtop___024root___eval",
                vlsyms_offset=16,
            )
        )
        lines.extend(templates.patch_schedule_kernel_lines())
        lines.extend(templates.metadata_lines("!7 = !{i32 1}"))
        text = "\n".join(lines)

        self.assertIn('target triple = "nvptx64-nvidia-cuda"', text)
        self.assertIn("@vl_replicate_init_state_gpu", text)
        self.assertIn("@vl_eval_batch_gpu", text)
        self.assertIn("@vl_apply_patch_schedule_gpu", text)
        self.assertIn("call void @Vtop___024root___eval(ptr %state_ptr)", text)
        self.assertIn("store ptr @fake_syms_buf", text)
        self.assertIn('!nvvm.annotations = !{!8, !9, !10}', text)

    def test_batch_kernel_omits_syms_store_when_offset_is_unknown(self) -> None:
        text = "\n".join(
            templates.batch_kernel_lines(
                storage_size=128,
                eval_fn="Vtop___024root___eval",
                vlsyms_offset=None,
            )
        )

        self.assertIn("call void @Vtop___024root___eval(ptr %state_ptr)", text)
        self.assertNotIn("fake_syms_buf", text)


if __name__ == "__main__":
    unittest.main()
