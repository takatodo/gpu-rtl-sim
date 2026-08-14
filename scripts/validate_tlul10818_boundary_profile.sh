#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

TLUL10818_BOUNDARY_PROFILE_ID="${TLUL10818_BOUNDARY_PROFILE_ID:-tlul10818_2x2_ordered_timing_full_enumeration_v1}"
TLUL10818_BOUNDARY_TARGET_CONFIG="${TLUL10818_BOUNDARY_TARGET_CONFIG:-config/tlul10818_boundary_benchmark.json}"
TLUL10818_BOUNDARY_PROFILE_SOURCE_DIR="${TLUL10818_BOUNDARY_PROFILE_SOURCE_DIR:-}"
TLUL10818_BOUNDARY_PROFILE_ARTIFACT_DIR="${TLUL10818_BOUNDARY_PROFILE_ARTIFACT_DIR:-}"

cd "${REPO_ROOT}"

if [[ -n "${TLUL10818_BOUNDARY_PROFILE_SOURCE_DIR}" ]]; then
  materialize_args=(
    --target-config "${TLUL10818_BOUNDARY_TARGET_CONFIG}"
    --profile-id "${TLUL10818_BOUNDARY_PROFILE_ID}"
    --source-dir "${TLUL10818_BOUNDARY_PROFILE_SOURCE_DIR}"
  )
  if [[ -n "${TLUL10818_BOUNDARY_PROFILE_ARTIFACT_DIR}" ]]; then
    materialize_args+=(--destination-dir "${TLUL10818_BOUNDARY_PROFILE_ARTIFACT_DIR}")
  fi
  python3 src/tools/materialize_tlul10818_boundary_profile.py "${materialize_args[@]}"
fi

validate_args=(
  --target-config "${TLUL10818_BOUNDARY_TARGET_CONFIG}"
  --profile-id "${TLUL10818_BOUNDARY_PROFILE_ID}"
)
if [[ -n "${TLUL10818_BOUNDARY_PROFILE_ARTIFACT_DIR}" ]]; then
  validate_args+=(--artifact-dir "${TLUL10818_BOUNDARY_PROFILE_ARTIFACT_DIR}")
fi

python3 src/tools/validate_tlul10818_boundary_profile.py "${validate_args[@]}"
