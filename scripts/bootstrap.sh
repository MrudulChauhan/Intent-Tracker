#!/usr/bin/env bash
# One-shot setup: create Python venv via uv, sync npm workspaces, init DB,
# copy logos into apps/web/public/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "→ 1/5 Creating Python env via uv"
cd "${REPO_ROOT}"
uv sync --all-extras

echo "→ 2/5 Installing npm workspaces"
npm install

echo "→ 3/5 Ensuring .env exists"
if [[ ! -f "${REPO_ROOT}/.env" ]]; then
  cp "${REPO_ROOT}/.env.example" "${REPO_ROOT}/.env"
  echo "  Created .env from .env.example — fill in your keys!"
fi

echo "→ 4/5 Syncing brand logos into apps/web/public"
bash "${SCRIPT_DIR}/sync_logos.sh"

echo "→ 5/5 Initializing database"
bash "${SCRIPT_DIR}/init_db.sh"

echo "Done. Next steps:"
echo "  npm run dev:api"
echo "  npm run dev:web"
