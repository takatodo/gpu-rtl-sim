// CPU reference driver for tlul_adapter_sram_10818_gpu_tb.
#include "Vtlul_adapter_sram_10818_gpu_tb.h"
#include "Vtlul_adapter_sram_10818_gpu_tb___024root.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

static void eval(Vtlul_adapter_sram_10818_gpu_tb& top, unsigned char clk) {
    top.clk_i = clk;
    top.eval();
}

int main(int argc, char** argv) {
    bool backpressure = false;
    bool malformed = false;
    const char* dump_path = nullptr;
    for (int index = 1; index < argc; ++index) {
        const std::string arg(argv[index]);
        if (arg == "--backpressure") backpressure = true;
        else if (arg == "--malformed") malformed = true;
        else if (arg == "--dump-state" && index + 1 < argc) dump_path = argv[++index];
        else {
            std::fprintf(stderr, "usage: %s [--malformed] [--backpressure] [--dump-state PATH]\n", argv[0]);
            return 2;
        }
    }

    Vtlul_adapter_sram_10818_gpu_tb top;
    top.rst_ni = 0;
    top.start_i = 0;
    top.malformed_i = malformed;
    top.d_backpressure_i = backpressure;
    eval(top, 0); eval(top, 1); eval(top, 0);
    top.rst_ni = 1;
    top.start_i = 1;
    eval(top, 1);
    top.start_i = 0;
    eval(top, 0); eval(top, 1); eval(top, 0); eval(top, 1); eval(top, 0); eval(top, 1);

    if (dump_path) {
        std::ofstream out(dump_path, std::ios::binary);
        out.write(reinterpret_cast<const char*>(top.rootp), sizeof(*top.rootp));
    }
    std::printf("RESULT done=%u oracle_violation=%u d_data=%08x d_error=%u intg_error=%u coverage=%x malformed=%u backpressure=%u\n",
                top.done_o, top.oracle_violation_o, top.observed_d_data_o,
                top.observed_d_error_o, top.observed_intg_error_o, top.action_coverage_o,
                malformed ? 1 : 0, backpressure ? 1 : 0);
    return top.done_o ? 0 : 1;
}
