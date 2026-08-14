// CPU reference driver for entropy_src_main_sm_10983_gpu_tb.
#include "Ventropy_src_main_sm_10983_gpu_tb.h"
#include "Ventropy_src_main_sm_10983_gpu_tb___024root.h"

#include <cstdio>
#include <fstream>
#include <string>

static void eval(Ventropy_src_main_sm_10983_gpu_tb& top, unsigned char clk) {
    top.clk_i = clk;
    top.eval();
}

static void cycle(Ventropy_src_main_sm_10983_gpu_tb& top) {
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

    Ventropy_src_main_sm_10983_gpu_tb top;
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
    std::printf("RESULT done=%u early_sha3_process=%u sha3_process=%u fw_start=%u main_sm_err=%u state=%x coverage=%u drive_cycles=%d\n",
                top.done_o, top.early_sha3_process_o, top.sha3_process_o, top.fw_start_o,
                top.main_sm_err_o, top.state_o, top.action_coverage_o, drive_cycles);
    return top.done_o ? 0 : 1;
}
