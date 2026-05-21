from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class HybridSidecarOptionMappingCliTest(HybridCliTestCase):
    def test_benchmark_operator_entrypoint_metadata_lives_in_shared_option_mapping(self) -> None:
        self.add_tools_to_path()
        from verilator_sidecar_options import operator_entrypoint_metadata

        metadata = operator_entrypoint_metadata(
            shape="64x1",
            sim_accel=None,
            sim_accel_shape="64x1",
            sim_accel_states=None,
            sim_accel_steps=None,
            sidecar_gpu=True,
        )

        self.assertEqual(metadata["surface"], "sim_accel_compat")
        self.assertTrue(metadata["sidecar_gpu_requested"])
        self.assertEqual(metadata["effective_sim_accel"], "sidecar-gpu")
        self.assertEqual(metadata["sim_accel_source"], "sim_accel_shape_spelling")
        self.assertEqual(metadata["shape_source"], "sim_accel_shape")
        self.assertIn("not execution, correctness, or timing evidence", metadata["non_claims"][1])

    def test_shim_sidecar_option_normalization_keeps_shim_entrypoint_thin(self) -> None:
        self.add_tools_to_path()
        from verilator_sidecar_options import normalize_shim_sidecar_options

        options = normalize_shim_sidecar_options(
            shape=None,
            sim_accel="sidecar-gpu",
            sim_accel_shape="64x1",
            sim_accel_states=None,
            sim_accel_steps=None,
            emit_verilator_command=False,
            print_verilator_command=False,
            print_verilator_estimate_command=True,
            print_efficiency_estimate=False,
            sim_accel_estimate_efficiency=False,
            print_operator_plan=False,
        )

        self.assertEqual(options.shape, "64x1")
        self.assertFalse(options.print_efficiency_estimate)
        self.assertTrue(options.emit_verilator_command)

        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            normalize_shim_sidecar_options(
                shape=None,
                sim_accel="sidecar-gpu",
                sim_accel_shape="64x1",
                sim_accel_states=None,
                sim_accel_steps=None,
                emit_verilator_command=False,
                print_verilator_command=True,
                print_verilator_estimate_command=False,
                print_efficiency_estimate=False,
                sim_accel_estimate_efficiency=True,
                print_operator_plan=False,
            )

    def test_compatibility_entrypoint_uses_shared_shape_parser(self) -> None:
        self.add_tools_to_path()
        from hybrid_benchmark_catalog import compatibility_entrypoint_for_shape

        self.assertEqual(
            compatibility_entrypoint_for_shape("64X1"),
            "--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1",
        )
        self.assertIsNone(compatibility_entrypoint_for_shape(None))
        with self.assertRaisesRegex(ValueError, "shape values must be positive"):
            compatibility_entrypoint_for_shape("0x1")
        with self.assertRaisesRegex(ValueError, "shape must be formatted as NxS"):
            compatibility_entrypoint_for_shape("64")
