import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR

sys.path.insert(0, TOOLS_DIR.as_posix())

from build_vl_gpu_compile import plan_verilator_ll_files  # noqa: E402


class BuildVlGpuCompileTests(unittest.TestCase):
    def test_plan_verilator_ll_files_skips_verilator_host_main(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mdir = Path(td)
            (mdir / "Vsim.cpp").write_text("// model\n")
            (mdir / "Vsim___024root.cpp").write_text("// root\n")
            (mdir / "Vsim__main.cpp").write_text("// verilator host main\n")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                ll_files, any_ll_rebuilt = plan_verilator_ll_files(
                    mdir=mdir,
                    all_classes=["Vsim", "Vsim___024root", "Vsim__main"],
                    force=True,
                    clang_changed=False,
                    clang_opt="O0",
                )

            self.assertTrue(any_ll_rebuilt)
            self.assertEqual(
                [path.name for path in ll_files],
                ["Vsim.ll", "Vsim___024root.ll"],
            )
            self.assertIn("skip (host main): Vsim__main.cpp", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
