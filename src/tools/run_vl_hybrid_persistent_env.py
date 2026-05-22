from __future__ import annotations

import argparse
from pathlib import Path

from run_vl_hybrid_args import persistent_phase_dump_parts as _persistent_phase_dump_parts


PERSISTENT_RESIDENT_HANDLE_ENV = "RUN_VL_HYBRID_PERSISTENT_RESIDENT_STATE_HANDLE"
PERSISTENT_RESIDENT_PHASE_ENV = "RUN_VL_HYBRID_PERSISTENT_RESIDENT_STATE_PHASE"
PERSISTENT_RESIDENT_PHASE_COUNT_ENV = "RUN_VL_HYBRID_PERSISTENT_RESIDENT_PHASE_COUNT"
PERSISTENT_RESIDENT_PHASE_DUMPS_ENV = "RUN_VL_HYBRID_PERSISTENT_RESIDENT_PHASE_DUMPS"


def configure_persistent_resident_env(
    env: dict[str, str],
    args: argparse.Namespace,
) -> None:
    if args.persistent_resident_state_abi_handle is not None:
        env[PERSISTENT_RESIDENT_HANDLE_ENV] = args.persistent_resident_state_abi_handle
        env[PERSISTENT_RESIDENT_PHASE_ENV] = str(args.persistent_resident_state_abi_phase)
        if args.persistent_resident_state_abi_phases is not None:
            env[PERSISTENT_RESIDENT_PHASE_COUNT_ENV] = str(args.persistent_resident_state_abi_phases)
        else:
            env.pop(PERSISTENT_RESIDENT_PHASE_COUNT_ENV, None)
        phase_dumps = _persistent_phase_dump_parts(args)
        if phase_dumps is not None:
            dump_paths = [str(Path(part).resolve()) for part in phase_dumps]
            for dump_path in dump_paths:
                Path(dump_path).parent.mkdir(parents=True, exist_ok=True)
            env[PERSISTENT_RESIDENT_PHASE_DUMPS_ENV] = ",".join(dump_paths)
        else:
            env.pop(PERSISTENT_RESIDENT_PHASE_DUMPS_ENV, None)
    else:
        env.pop(PERSISTENT_RESIDENT_HANDLE_ENV, None)
        env.pop(PERSISTENT_RESIDENT_PHASE_ENV, None)
        env.pop(PERSISTENT_RESIDENT_PHASE_COUNT_ENV, None)
        env.pop(PERSISTENT_RESIDENT_PHASE_DUMPS_ENV, None)
