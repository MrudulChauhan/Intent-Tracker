#!/usr/bin/env bash
# Start the FastAPI backend.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_env.sh"

PORT="${API_PORT:-8000}"

cd "${REPO_ROOT}"
exec uv run uvicorn apps.api.main:app --reload --host 127.0.0.1 --port "${PORT}"
