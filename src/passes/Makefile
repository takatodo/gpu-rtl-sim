LLVM_CONFIG ?= llvm-config-18
CXX         ?= clang++-18
OUT_DIR     ?= ../../artifacts/tool_bins/passes

CXXFLAGS := $(shell $(LLVM_CONFIG) --cxxflags) -fPIC
LDFLAGS  := $(shell $(LLVM_CONFIG) --ldflags)
LIBS     := -lLLVM-18
PASSES_SO := $(OUT_DIR)/VlGpuPasses.so
VLGPUGEN  := $(OUT_DIR)/vlgpugen

.PHONY: all clean VlGpuPasses.so vlgpugen

all: $(PASSES_SO) $(VLGPUGEN)

VlGpuPasses.so: $(PASSES_SO)

vlgpugen: $(VLGPUGEN)

$(OUT_DIR):
	mkdir -p $@

$(PASSES_SO): VlGpuPasses.cpp | $(OUT_DIR)
	$(CXX) $(CXXFLAGS) -shared -o $@ $< $(LDFLAGS)

$(VLGPUGEN): vlgpugen.cpp | $(OUT_DIR)
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS) $(LIBS)

clean:
	rm -f $(PASSES_SO) $(VLGPUGEN) VlGpuPasses.so vlgpugen
