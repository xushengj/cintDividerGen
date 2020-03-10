import sys

def getModule(moduleName, divisor, inputWidth, radixWidth):
  # input validation
  if divisor <= 0 or inputWidth <= 0 or radixWidth <= 0:
    raise ValueError('All numeric arguments must be positive!')
  if 2**radixWidth < divisor:
    raise ValueError('Radix width is smaller than divisor bitwidth!')
  
  # compute derived localparams
  # carry width
  carryWidth = 1
  while 2**carryWidth < divisor:
    carryWidth += 1
  # slice count
  sliceNum = (inputWidth-1)//radixWidth + 1
  
  # start to write output
  module = []
  # first, the input output ports
  inputWidthDepStr = '[' + str(inputWidth-1) + ':0]'
  
  module.append('module {0} (\n'.format(moduleName))
  module.append( ('  input  logic                clk_i,\n'
  '  input  logic                rst_ni,\n'
  '  input  logic                flush_i,\n'
  '  input  logic                valid_i,\n'
  ))
  module.append('  input  logic {0}      value_i,\n'.format(inputWidthDepStr))
  module.append( (
  '  output logic                valid_o,\n'
  '  output logic                valid_next_o, // result will be valid in next cycle\n'
  ))
  module.append('  output logic {0}      quotient_o,\n'.format(inputWidthDepStr))
  module.append('  output logic {0}      remainder_o\n);\n'.format(inputWidthDepStr))
  
  # next, localparams
  module.append('localparam int unsigned VALUE_DIVISOR = {0};\n'.format(str(divisor)))
  module.append('localparam int unsigned WIDTH_INPUT   = {0};\n'.format(str(inputWidth)))
  module.append('localparam int unsigned WIDTH_RADIX   = {0};\n'.format(str(radixWidth)))
  module.append('localparam int unsigned WIDTH_CARRY   = {0};\n'.format(str(carryWidth)))
  module.append('localparam int unsigned NUM_SLICE     = {0};\n'.format(str(sliceNum)))
  module.append('\n')
  
  # now the gigantic big lookup table
  module.append('localparam logic [2**(WIDTH_RADIX+WIDTH_CARRY)-1:0][WIDTH_RADIX+WIDTH_CARRY-1:0] LookupTable = {\n')
  # note that saved carry is in upper bits and the bits from dividend is in lower bits
  for i in range(2**(radixWidth+carryWidth)-1, 0, -1):
    if i >= ((2**radixWidth) * divisor):
      module.append("{0}'d0,\n".format(str(radixWidth+carryWidth)));
    else:
      quot, rem = divmod(i, divisor)
      assert rem < 2**carryWidth
      outValue = (((quot % (2**radixWidth)) << carryWidth) + rem)
      module.append("{0}'d{1}, // value={2}, quot={3}, rem={4}\n".format(str(radixWidth+carryWidth), str(outValue), str(i), str(quot), str(rem)))
  module.append("{0}'d0\n}};\n".format(str(radixWidth+carryWidth)));
  
  # now the remaining code
  module.append("""
logic [NUM_SLICE-1:0][WIDTH_RADIX-1:0] value_e, value_d, value_q;

always_comb begin
  value_e = '0;
  for (int unsigned i = 0; i < WIDTH_INPUT; ++i) begin
    value_e[i/WIDTH_RADIX][i%WIDTH_RADIX] = value_i[i];
  end
end

assign value_d = (valid_i? value_e: value_q);

logic [NUM_SLICE-1:0] slice_zero;
logic [NUM_SLICE-1:0] slice_full;

generate
  for (genvar gi = 0; gi < NUM_SLICE; ++gi) begin
    assign slice_zero[gi] = ~|value_e[gi];
    assign slice_full[gi] = (value_e[gi] >= VALUE_DIVISOR);
  end
endgenerate

logic [$clog2(NUM_SLICE)-1:0] slice_index_first, slice_index_next, slice_index_d, slice_index_q;
always_comb begin
  slice_index_first = 0;
  for (int unsigned j = NUM_SLICE-1; j > 0; ++j) begin
    if (!slice_zero[j]) begin
      slice_index_first = slice_full[j]? j : (j-1);
      break;
    end
  end
end
assign slice_index_next = slice_index_q - 1;

logic [WIDTH_CARRY-1:0] carry_i, carry_d, carry_q;
assign carry_i = (slice_index_first == NUM_SLICE-1)? {WIDTH_CARRY{1'b0}} : value_e[slice_index_first+1][WIDTH_CARRY-1:0];

logic [WIDTH_RADIX+WIDTH_CARRY-1:0] divider_current;
assign divider_current = {carry_q, value_q[slice_index_q]};

logic [WIDTH_RADIX+WIDTH_CARRY-1:0] result_current;
assign result_current = LookupTable[divider_current];
logic [WIDTH_RADIX-1:0] quotient_current;
logic [WIDTH_CARRY-1:0] remainder_current;
assign quotient_current = result_current[WIDTH_RADIX+WIDTH_CARRY-1:WIDTH_CARRY];
assign remainder_current = result_current[WIDTH_CARRY-1:0];

logic [NUM_SLICE-1:0][WIDTH_RADIX-1:0] result_d, result_q;

assign remainder_o[WIDTH_INPUT-1:WIDTH_CARRY] = '0;
assign remainder_o[WIDTH_CARRY-1:0] = carry_q;
always_comb begin
  quotient_o = '0;
  for (int unsigned i = 0; i < WIDTH_INPUT; ++i) begin
    quotient_o[i] = result_q[i/WIDTH_RADIX][i%WIDTH_RADIX];
  end
end


enum logic [1:0] {
  IDLE,
  WORKING,
  DONE
} state_n, state_q;

always_comb begin
  // output assignment
  valid_o = '0;
  valid_next_o = '0;
  
  // internal states
  state_n = state_q;
  carry_d = carry_q;
  result_d = result_q;
  slice_index_d = '0;
  case (state_q)
    IDLE: begin
      result_d = '0;
      if (valid_i) begin
        carry_d = carry_i;
        slice_index_d = slice_index_first;
        state_n = WORKING;
      end
    end // IDLE
    WORKING: begin
      carry_d = remainder_current;
      result_d[slice_index_q] = quotient_current;
      if (slice_index_q == 0) begin
        state_n = DONE;
        valid_next_o = 1'b1;
      end else begin
        slice_index_d = slice_index_next;
      end
    end // WORKING
    DONE: begin
      valid_o = 1'b1;
      state_n = IDLE;
      // same as in IDLE
      result_d = '0;
      if (valid_i) begin
        carry_d = carry_i;
        slice_index_d = slice_index_first;
        state_n = WORKING;
      end
    end // DONE
  endcase
  if (flush_i) begin
    state_n = IDLE;
  end
end

always_ff @(posedge clk_i or negedge rst_ni) begin
  if(~rst_ni) begin
    state_q       <= IDLE;
    value_q       <= '0;
    slice_index_q <= '0;
    carry_q       <= '0;
    result_q      <= '0;
  end else begin
    state_q       <= state_n;
    value_q       <= value_d;
    slice_index_q <= slice_index_d;
    carry_q       <= carry_d;
    result_q      <= result_d;
  end
end

endmodule

""")
  return ''.join(module)

def printUsage():
  print("Usage: {0} <ModuleName> <Divisor> <InputBitWidth> <RadixBitWidth>".format(sys.argv[0]))
  return

if __name__ == "__main__":
  if len(sys.argv) != 5:
    printUsage()
    exit()
  ModuleName = sys.argv[1]
  Divisor = int(sys.argv[2])
  InputBitWidth = int(sys.argv[3])
  RadixBitWidth = int(sys.argv[4])
  module = getModule(ModuleName, Divisor, InputBitWidth, RadixBitWidth)
  print(module)
