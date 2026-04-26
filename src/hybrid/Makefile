# Minimal hybrid runner (CUDA Driver API). Requires: cuda.h + libcuda.
# Override: make CUDA_HOME=/path/to/cuda
#           make CUDA_INCLUDE_DIR=/path/to/include CUDA_LIB_DIR=/path/to/lib

CUDA_HOME ?= /usr/local/cuda
CUDA_INCLUDE_DIR ?=
CUDA_LIB_DIR ?=

CXX      ?= g++
CXXFLAGS ?= -O2 -Wall -Wextra
VERILATOR_ROOT ?= $(shell verilator --getenv VERILATOR_ROOT 2>/dev/null || echo /usr/local/share/verilator)
TLUL_MDIR ?= artifacts/tlul_fifo_sync_obj_dir

ifeq ($(strip $(CUDA_INCLUDE_DIR)),)
  ifneq ($(wildcard $(CUDA_HOME)/include/cuda.h),)
    CUDA_INCLUDE_DIR := $(CUDA_HOME)/include
  else ifneq ($(wildcard /usr/lib/cuda/include/cuda.h),)
    CUDA_INCLUDE_DIR := /usr/lib/cuda/include
  else ifneq ($(wildcard /usr/include/cuda.h),)
    CUDA_INCLUDE_DIR := /usr/include
  endif
endif

ifeq ($(strip $(CUDA_LIB_DIR)),)
  ifneq ($(wildcard $(CUDA_HOME)/lib64/libcuda.so),)
    CUDA_LIB_DIR := $(CUDA_HOME)/lib64
  else ifneq ($(wildcard /usr/lib/wsl/lib/libcuda.so),)
    CUDA_LIB_DIR := /usr/lib/wsl/lib
  else ifneq ($(wildcard /usr/lib/x86_64-linux-gnu/libcuda.so),)
    CUDA_LIB_DIR := /usr/lib/x86_64-linux-gnu
  endif
endif

INCLUDES = -I$(CUDA_INCLUDE_DIR)
LDFLAGS  = -L$(CUDA_LIB_DIR) -Wl,-rpath,$(CUDA_LIB_DIR)
LDLIBS   = -lcuda

.PHONY: all clean tlul_slice_host_probe

all: run_vl_hybrid

run_vl_hybrid: run_vl_hybrid.c
	@test -n "$(CUDA_INCLUDE_DIR)" -a -f $(CUDA_INCLUDE_DIR)/cuda.h || \
		(echo "Set CUDA_HOME or CUDA_INCLUDE_DIR so cuda.h is available"; exit 1)
	@test -n "$(CUDA_LIB_DIR)" -a -e $(CUDA_LIB_DIR)/libcuda.so || \
		(echo "Set CUDA_LIB_DIR so libcuda.so is available"; exit 1)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $@ $< $(LDFLAGS) $(LDLIBS)

../../$(TLUL_MDIR)/tlul_slice_host_probe: tlul_slice_host_probe.cpp
	$(CXX) -std=c++20 -fcoroutines -O2 -w \
		-I../../$(TLUL_MDIR) \
		-I$(VERILATOR_ROOT)/include \
		-I$(VERILATOR_ROOT)/include/vltstd \
		-DMODEL_HEADER='"Vtlul_fifo_sync_gpu_cov_tb.h"' \
		-DROOT_HEADER='"Vtlul_fifo_sync_gpu_cov_tb___024root.h"' \
		-DMODEL_CLASS=Vtlul_fifo_sync_gpu_cov_tb \
		-DROOT_CLASS=Vtlul_fifo_sync_gpu_cov_tb___024root \
		-DROOT_CLK_FIELD=tlul_fifo_sync_gpu_cov_tb__DOT__clk_i \
		-DROOT_CLK_REPORT_NAME='"clk_i"' \
		-DROOT_RST_FIELD=tlul_fifo_sync_gpu_cov_tb__DOT__reset_like_w \
		-DROOT_RST_REPORT_NAME='"reset_like_w"' \
		-DROOT_RST_ASSERTED_VALUE=1U \
		-DROOT_RST_DEASSERTED_VALUE=0U \
		-DHOST_CLOCK_CONTROL=1 \
		-DHOST_RESET_CONTROL=1 \
		-DTARGET_NAME='"tlul_fifo_sync_gpu_cov_tb"' \
		tlul_slice_host_probe.cpp \
		../../$(TLUL_MDIR)/Vtlul_fifo_sync_gpu_cov_tb.cpp \
		../../$(TLUL_MDIR)/Vtlul_fifo_sync_gpu_cov_tb___024root__0.cpp \
		../../$(TLUL_MDIR)/Vtlul_fifo_sync_gpu_cov_tb___024root__1.cpp \
		../../$(TLUL_MDIR)/Vtlul_fifo_sync_gpu_cov_tb___024root__2.cpp \
		../../$(TLUL_MDIR)/Vtlul_fifo_sync_gpu_cov_tb___024root__3.cpp \
		../../$(TLUL_MDIR)/Vtlul_fifo_sync_gpu_cov_tb___024root__Slow.cpp \
		../../$(TLUL_MDIR)/Vtlul_fifo_sync_gpu_cov_tb___024root__0__Slow.cpp \
		../../$(TLUL_MDIR)/Vtlul_fifo_sync_gpu_cov_tb___024root__1__Slow.cpp \
		../../$(TLUL_MDIR)/Vtlul_fifo_sync_gpu_cov_tb__Syms__Slow.cpp \
		$(VERILATOR_ROOT)/include/verilated.cpp \
		$(VERILATOR_ROOT)/include/verilated_timing.cpp \
		$(VERILATOR_ROOT)/include/verilated_threads.cpp \
		-pthread \
		-o $@

tlul_slice_host_probe: ../../$(TLUL_MDIR)/tlul_slice_host_probe

clean:
	rm -f run_vl_hybrid ../../$(TLUL_MDIR)/tlul_slice_host_probe
