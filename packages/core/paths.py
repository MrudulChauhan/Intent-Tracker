"""Canonical filesystem paths for the monorepo.

Anything that needs to find the repo root, the DB file, the brand assets, or
the seed data should import from here. One source of truth — no duplicated
`Path(__file__).resolve().parent.parent...` chains scattered around the code.
"""

from pathlib import Path

# packages/core/paths.py -> packages/core -> packages -> REPO_ROOT
REPO_ROOT: Path = Path(__file__).resolve().parents[2]

DATA_DIR: Path = REPO_ROOT / "data"
SEEDS_DIR: Path = DATA_DIR / "seeds"
PACKAGES_DIR: Path = REPO_ROOT / "packages"
BRAND_DIR: Path = PACKAGES_DIR / "brand"
BRAND_LOGOS_DIR: Path = BRAND_DIR / "logos"
CONFIG_DIR: Path = REPO_ROOT / "config"
APPS_DIR: Path = REPO_ROOT / "apps"
WEB_PUBLIC_LOGOS_DIR: Path = APPS_DIR / "web" / "public" / "logos"

DEFAULT_DB_PATH: Path = DATA_DIR / "intent_tracker.db"
