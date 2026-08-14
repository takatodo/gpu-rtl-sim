// CPU reference driver for edn_csrng_23526_gpu_tb.
#include "Vedn_csrng_23526_gpu_tb.h"
#include "Vedn_csrng_23526_gpu_tb___024root.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

static void eval(Vedn_csrng_23526_gpu_tb& top, unsigned char clk) {
    top.clk_i = clk;
    top.eval();
}

static void cycle(Vedn_csrng_23526_gpu_tb& top) {
    eval(top, 1);
    eval(top, 0);
}

int main(int argc, char** argv) {
    const char* dump_path = nullptr;
    for (int index = 1; index < argc; ++index) {
        const std::string arg(argv[index]);
        if (arg == "--dump-state" && index + 1 < argc) {
            dump_path = argv[++index];
        } else {
            std::fprintf(stderr, "usage: %s [--dump-state PATH]\n", argv[0]);
            return 2;
        }
    }

    Vedn_csrng_23526_gpu_tb top;
    top.rst_ni = 0;
    top.start_i = 0;
    eval(top, 0);
    cycle(top);
    cycle(top);

    top.rst_ni = 1;
    top.start_i = 1;
    int drive_cycles = 0;
    cycle(top);
    ++drive_cycles;
    top.start_i = 0;
    while (!top.done_o) {
        cycle(top);
        ++drive_cycles;
    }

    if (dump_path) {
        std::ofstream out(dump_path, std::ios::binary);
        out.write(reinterpret_cast<const char*>(top.rootp), sizeof(*top.rootp));
    }
    std::printf("RESULT done=%u protocol_violation=%u valid_after_error=%u valid_seen=%u coverage=%x drive_cycles=%d\n",
                top.done_o, top.protocol_violation_o, top.valid_after_error_o,
                top.csrng_req_valid_seen_o, top.action_coverage_o, drive_cycles);
    return top.done_o ? 0 : 1;
}
