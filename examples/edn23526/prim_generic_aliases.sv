// Minimal primitive aliases for direct Verilator builds outside OpenTitan's
// FuseSoC/primgen flow.
module prim_flop #(
  parameter int               Width      = 1,
  parameter logic [Width-1:0] ResetValue = 0
) (
  input                    clk_i,
  input                    rst_ni,
  input        [Width-1:0] d_i,
  output logic [Width-1:0] q_o
);
  prim_generic_flop #(
    .Width(Width),
    .ResetValue(ResetValue)
  ) u_impl (
    .clk_i,
    .rst_ni,
    .d_i,
    .q_o
  );
endmodule

module prim_flop_2sync #(
  parameter int               Width              = 16,
  parameter logic [Width-1:0] ResetValue         = '0,
  parameter bit               EnablePrimCdcRand  = 1
) (
  input                    clk_i,
  input                    rst_ni,
  input        [Width-1:0] d_i,
  output logic [Width-1:0] q_o
);
  prim_generic_flop_2sync #(
    .Width(Width),
    .ResetValue(ResetValue),
    .EnablePrimCdcRand(EnablePrimCdcRand)
  ) u_impl (
    .clk_i,
    .rst_ni,
    .d_i,
    .q_o
  );
endmodule

module prim_buf #(
  parameter int Width = 1
) (
  input        [Width-1:0] in_i,
  output logic [Width-1:0] out_o
);
  prim_generic_buf #(
    .Width(Width)
  ) u_impl (
    .in_i,
    .out_o
  );
endmodule

module prim_xor2 #(
  parameter int Width = 1
) (
  input        [Width-1:0] in0_i,
  input        [Width-1:0] in1_i,
  output logic [Width-1:0] out_o
);
  prim_generic_xor2 #(
    .Width(Width)
  ) u_impl (
    .in0_i,
    .in1_i,
    .out_o
  );
endmodule
