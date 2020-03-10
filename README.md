# cintDividerGen
A generator script for division by a small constant int in SystemVerilog. The generated division module use a LUT based high radix algorithm to compute more than one bits of quotients in each cycle.

Disclaimer: this divider is not optimized in any means.

## List of files
### DividerGen.py
The Python3 script for generating the divider module. The output is written to stdout.

    python3 DividerGen.py <ModuleName> <Divisor> <InputBitWidth> <RadixBitWidth> > module.sv

Arguments:
- ModuleName: the SystemVerilog module name in the generated module
- Divisor: The small constant int that a dividend is divided against.
- InputBitWidth: The width of dividend, in number of bits
- RadixBitWidth: How many bits of quotient to generate per cycle. Note that it may cause trouble for synthesis or simulation if the width is too large.

### DividerTemplate.sv
A "preview" of how the generated divider module would look like. Note that DividerGen.py do not need this file to work.

### test
This directory contains a test case using [verilator](https://www.veripool.org/projects/verilator/wiki/Installing "verilator"). Run `make && make run` to run the test.
