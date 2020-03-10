#include "Vdivider.h"

#include "verilated.h"
#include "verilated_vcd_c.h"

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <signal.h>
#include <unistd.h>
#include <chrono>
#include <random>

#include "config.h"

#ifndef DIVISOR
#define DIVISOR 3
#endif

#ifndef INPUT_WIDTH
#define INPUT_WIDTH 48
#endif

static_assert(INPUT_WIDTH <= 8*sizeof(std::size_t));

volatile bool stop = false;
bool isEnableTrace = false;

std::size_t TestsMade = 0;

void sighandler(int signo){
  (void) signo;
  stop = true;
}

void progressIndicator(int signo) {
  (void) signo;
  fprintf(stdout, "\rTest %zu", TestsMade);
  fflush(stdout);
  alarm(1);
}

namespace{

std::size_t totalCycle = 0;
Vdivider* top = nullptr;
VerilatedVcdC* tfp = nullptr;

void ADVANCE() {
  top->eval();
  if (isEnableTrace)
    tfp->dump(totalCycle);
  totalCycle+=1;
}

void clearTrace(char* filePath) {
  // clear existing trace so that the tester don't fill the disk
  tfp->close();
  tfp->open (filePath);
}

} // end of anonymous namespace

int main(int argc, char **argv, char **env) {
  Verilated::commandArgs(argc, argv);
  // init top verilog instance
  top = new Vdivider;

  char* filePath = argv[1];
  if (argc > 1) {
    fprintf(stdout, "VCD trace will be written to %s\n", filePath);
    isEnableTrace = true;
    Verilated::traceEverOn(true);
    tfp = new VerilatedVcdC;
    top->trace (tfp, 99);
    tfp->open (filePath);
  }

  signal(SIGTERM, sighandler);
  signal(SIGINT, sighandler);
  signal(SIGALRM, progressIndicator);
  alarm(1);

  top->clk_i = 1;
  top->rst_ni = 0;
  top->flush_i = 0;
  top->valid_i = 0;
  top->value_i = 0;
  
  for(int i = 0; i < 4; ++i){
    top->rst_ni = 0;
    top->clk_i = ~( i & 0x01);
    ADVANCE();
  }

  top->rst_ni = 1;
  
  // reference: http://www.cplusplus.com/reference/random/uniform_int_distribution/uniform_int_distribution/
  // construct a trivial random generator engine from a time-based seed:
  unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
  std::default_random_engine generator (seed);

  std::size_t max = (INPUT_WIDTH >= 8*sizeof(std::size_t))? std::numeric_limits<std::size_t>::max() : ((1ull<<INPUT_WIDTH)-1);
  std::uniform_int_distribution<std::size_t> distribution(0, max);
  
  while(!stop){
    std::size_t value = distribution(generator);
    std::size_t quot = value / DIVISOR;
    std::size_t rem = value % DIVISOR;
    // posedge
    top->value_i = value;
    top->valid_i = 1;
    top->clk_i = 1;
    ADVANCE();
    // negedge
    top->clk_i = 0;
    ADVANCE();
    top->value_i = 0;
    top->valid_i = 0;
    // loop and wait
    while (!stop && top->valid_o == 0) {
      top->clk_i = 1;
      ADVANCE();
      top->clk_i = 0;
      ADVANCE();
    }
    if (stop)
      break;
    TestsMade += 1;
    if (top->quotient_o != quot || top->remainder_o != rem) {
      stop = true;
      fprintf(stdout, "Test fail: %zu = %zu * %zu + %zu but got quotient %zu and remainder %zu",
        value, static_cast<std::size_t>(DIVISOR), quot, rem, top->quotient_o, top->remainder_o);
    }
  }
  
  if (isEnableTrace)
    tfp->close();
  return 0;
}
