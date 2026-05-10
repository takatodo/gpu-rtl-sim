module tc_sram #(
  parameter int unsigned NumWords  = 32'd1024,
  parameter int unsigned DataWidth = 32'd128,
  parameter int unsigned ByteWidth = 32'd8,
  parameter int unsigned NumPorts  = 32'd2,
  parameter int unsigned Latency   = 32'd1,
  parameter              SimInit   = "zeros",
  parameter bit          PrintSimCfg = 1'b0,
  parameter int unsigned AddrWidth = (NumWords > 32'd1) ? $clog2(NumWords) : 32'd1,
  parameter int unsigned BeWidth   = (DataWidth + ByteWidth - 32'd1) / ByteWidth,
  parameter type         addr_t    = logic [AddrWidth-1:0],
  parameter type         data_t    = logic [DataWidth-1:0],
  parameter type         be_t      = logic [BeWidth-1:0]
) (
  input  logic                 clk_i,
  input  logic                 rst_ni,
  input  logic  [NumPorts-1:0] req_i,
  input  logic  [NumPorts-1:0] we_i,
  input  addr_t [NumPorts-1:0] addr_i,
  input  data_t [NumPorts-1:0] wdata_i,
  input  be_t   [NumPorts-1:0] be_i,
  output data_t [NumPorts-1:0] rdata_o
);
  data_t mem_q [NumWords];
  data_t rdata_q [NumPorts];

  initial begin
    for (int unsigned word = 0; word < NumWords; word = word + 1) begin
      mem_q[word] = '0;
    end
    for (int unsigned port = 0; port < NumPorts; port = port + 1) begin
      rdata_q[port] = '0;
    end
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      for (int unsigned port = 0; port < NumPorts; port = port + 1) begin
        rdata_q[port] <= '0;
      end
    end else begin
      for (int unsigned port = 0; port < NumPorts; port = port + 1) begin
        if (req_i[port]) begin
          if (we_i[port]) begin
            for (int unsigned byte_idx = 0; byte_idx < BeWidth; byte_idx = byte_idx + 1) begin
              if (be_i[port][byte_idx]) begin
                mem_q[addr_i[port]][byte_idx * ByteWidth +: ByteWidth] <=
                    wdata_i[port][byte_idx * ByteWidth +: ByteWidth];
              end
            end
          end else begin
            rdata_q[port] <= mem_q[addr_i[port]];
          end
        end
      end
    end
  end

  for (genvar port = 0; port < NumPorts; port = port + 1) begin : gen_rdata
    assign rdata_o[port] = rdata_q[port];
  end

endmodule
