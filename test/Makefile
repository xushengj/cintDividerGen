TB = obj_dir/Vdivider

DIVISOR=3
INPUTWIDTH=48
RADIX=8

SVSRC = divider.sv
CPPSRC = tester.cpp
CPPCONFIGH = config.h
SCRIPT = ../DividerGen.py

PYTHON=python3

all: $(TB)

$(TB): $(SCRIPT) $(CPPSRC)
	$(PYTHON) $(SCRIPT) divider $(DIVISOR) $(INPUTWIDTH) $(RADIX) > $(SVSRC)
	echo "#define DIVISOR $(DIVISOR)" > $(CPPCONFIGH)
	echo "#define INPUT_WIDTH $(INPUTWIDTH)" >> $(CPPCONFIGH)
	verilator -Wall --Wno-fatal --trace --cc $(SVSRC) --top-module divider --exe $(CPPSRC)
	make OPT_FAST='-O2' -j -C obj_dir -f Vdivider.mk Vdivider

run: $(TB)
	$(TB)

clean:
	rm -rf obj_dir trace.vcd $(SVSRC) $(CPPCONFIGH)
