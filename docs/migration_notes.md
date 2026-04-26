# Migration Notes

## weakest_point

The exploration repository contains valuable knowledge, but most of its generated artifacts and historical decision logs should not be copied.

## carry

```text
runtime_core:
  - src/hybrid/run_vl_hybrid.c
  - src/hybrid/host_abi.h
  - src/hybrid/tlul_slice_host_probe.cpp
  - src/hybrid/tlul_fifo_sync_cpu_replay_host_probe.cpp
  - src/passes/VlGpuPasses.cpp
  - src/passes/vlgpugen.cpp

first_seed:
  - tlul_fifo_sync source/config only
```

## do_not_carry

```text
- work/
- output/
- obj_dir/
- __pycache__/
- broad MobileViT side branches
- historical campaign decision artifact history
```
