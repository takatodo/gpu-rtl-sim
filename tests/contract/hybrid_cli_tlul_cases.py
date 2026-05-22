TLUL_CLOCK_RESET_DEFINE_CASES = {
    "tlul_sink": (
        "-DROOT_CLK_FIELD=tlul_sink_gpu_cov_tb__DOT__clk_i",
        "-DROOT_RST_FIELD=tlul_sink_gpu_cov_tb__DOT__rst_ni",
    ),
    "tlul_request_loopback": (
        "-DROOT_CLK_FIELD=tlul_request_loopback_gpu_cov_tb__DOT__clk_i",
        "-DROOT_RST_FIELD=tlul_request_loopback_gpu_cov_tb__DOT__rst_ni",
    ),
    "tlul_adapter_host": ("-DROOT_CLK_FIELD=clk_i", "-DROOT_RST_FIELD=rst_ni"),
    "tlul_socket_m1": ("-DROOT_CLK_FIELD=clk_i", "-DROOT_RST_FIELD=rst_ni"),
    "tlul_socket_1n": ("-DROOT_CLK_FIELD=clk_i", "-DROOT_RST_FIELD=rst_ni"),
    "tlul_adapter_reg": (
        "-DROOT_CLK_FIELD=tlul_adapter_reg_gpu_cov_tb__DOT__clk_i",
        "-DROOT_RST_FIELD=tlul_adapter_reg_gpu_cov_tb__DOT__rst_ni",
    ),
    "tlul_adapter_sram": (
        "-DROOT_CLK_FIELD=tlul_adapter_sram_gpu_cov_tb__DOT__clk_i",
        "-DROOT_RST_FIELD=tlul_adapter_sram_gpu_cov_tb__DOT__rst_ni",
    ),
    "tlul_lc_gate": (
        "-DROOT_CLK_FIELD=tlul_lc_gate_gpu_cov_tb__DOT__clk_i",
        "-DROOT_RST_FIELD=tlul_lc_gate_gpu_cov_tb__DOT__rst_ni",
    ),
    "tlul_err_resp": (
        "-DROOT_CLK_FIELD=tlul_err_resp_gpu_cov_tb__DOT__clk_i",
        "-DROOT_RST_FIELD=tlul_err_resp_gpu_cov_tb__DOT__rst_ni",
    ),
    "tlul_err": (
        "-DROOT_CLK_FIELD=tlul_err_gpu_cov_tb__DOT__clk_i",
        "-DROOT_RST_FIELD=tlul_err_gpu_cov_tb__DOT__rst_ni",
    ),
    "tlul_cmd_intg_chk": (
        "-DROOT_CLK_FIELD=tlul_cmd_intg_chk_gpu_cov_tb__DOT__clk_i",
        "-DROOT_RST_FIELD=tlul_cmd_intg_chk_gpu_cov_tb__DOT__rst_ni",
    ),
}
