#!/usr/bin/env bash
# Common env setup sourced by every run_*.sh script.
# Resolves REPO_ROOT, sets PYTHONPATH so core/brand/scanners are importable.
# Works under both bash (BASH_SOURCE) and zsh (%x / ${(%):-%x}).

set -eu

# Locate this script in a shell-agnostic way
if [ -n "${BASH_SOURCE[0]:-}" ]; then
  _SELF="${BASH_SOURCE[0]}"
elif [ -n "${ZSH_VERSION:-}" ]; then
  _SELF="${(%):-%N}"
else
  _SELF="$0"
fi
SCRIPT_DIR="$(cd "$(dirname "${_SELF}")" && pwd)"
export REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Make packages/core, packages/brand, apps/scanner, and the repo root importable.
# Order matters: core/brand first so `core.*` / `brand.*` resolve cleanly.
export PYTHONPATH="${REPO_ROOT}/packages:${REPO_ROOT}/apps/scanner:${REPO_ROOT}/apps:${REPO_ROOT}:${PYTHONPATH:-}"

# Load .env if present (export all, then stop)
if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env"
  set +a
fi
