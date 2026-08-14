#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

BOUNDARY_ADJUDICATOR_BIN="${BOUNDARY_ADJUDICATOR_BIN:-verilator-model-sidecar}"
CONTRACT="${CONTRACT:-artifacts/tlul10818_boundary_benchmark/experiment_contract.json}"
EVIDENCE="${EVIDENCE:-artifacts/tlul10818_boundary_benchmark/evidence_bundle.json}"
OUTPUT="${OUTPUT:-artifacts/tlul10818_boundary_benchmark/pipeline_result.json}"

cd "${REPO_ROOT}"

"${BOUNDARY_ADJUDICATOR_BIN}" adjudicate-boundary-benchmark \
  --experiment-contract "${CONTRACT}" \
  --evidence "${EVIDENCE}" \
  --output "${OUTPUT}"
