#!/usr/bin/env bash
# Initialize the SQLite database (idempotent) and optionally seed it.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_env.sh"

cd "${REPO_ROOT}"

uv run python -c "from core.db import init_db; init_db(); print('DB initialized at', __import__('core.db', fromlist=['DB_PATH']).DB_PATH)"

if [[ "${1:-}" == "--seed" ]]; then
  uv run python data/seeds/seed_projects.py
  echo "Seeded."
fi
