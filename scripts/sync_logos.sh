#!/usr/bin/env bash
# Copy brand logos → apps/web/public/logos so Next.js can serve them.
# Source of truth: packages/brand/logos/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_env.sh"

SRC="${REPO_ROOT}/packages/brand/logos"
DST="${REPO_ROOT}/apps/web/public"

mkdir -p "${DST}/logos/chains" "${DST}/logos/protocols"

# Root logos (SVG) — served from /logo.svg, /logo-light.svg, /favicon.svg
cp "${SRC}/logo.svg" "${DST}/logo.svg"
cp "${SRC}/logo-light.svg" "${DST}/logo-light.svg"
cp "${SRC}/favicon.svg" "${DST}/favicon.svg"

# Chain + protocol logos
rsync -a --delete "${SRC}/chains/" "${DST}/logos/chains/"
rsync -a --delete "${SRC}/protocols/" "${DST}/logos/protocols/"

echo "Synced brand logos → ${DST}/logos"
