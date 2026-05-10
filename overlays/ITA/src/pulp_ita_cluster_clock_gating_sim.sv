// Simulation-only clock-gating shim for PULP ITA register files.
module cluster_clock_gating (
  input  logic clk_i,
  input  logic en_i,
  input  logic test_en_i,
  output logic clk_o
);

  assign clk_o = clk_i & (en_i | test_en_i);

endmodule
