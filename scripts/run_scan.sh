#!/usr/bin/env bash
# Run the scanner orchestrator once (or pass --scanner <name> to run just one).
# Usage:
#   ./scripts/run_scan.sh            # all scanners, single run
#   ./scripts/run_scan.sh --scanner github

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_env.sh"

cd "${REPO_ROOT}/apps/scanner"

if [[ $# -eq 0 ]]; then
  exec uv run python -m scheduler.scheduler --once
else
  exec uv run python -m scheduler.scheduler "$@"
fi
