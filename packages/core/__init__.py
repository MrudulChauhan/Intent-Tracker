"""Core package: shared config, database, models, and queries for intent-tracker.

Everything that the api/, scanner/, and dashboard/ apps need is exposed here so
there is one import surface and one source of truth for env + DB paths.
"""

from core.config import get_settings, settings
from core.db import DB_PATH, db_connection, get_connection, init_db
from core.paths import REPO_ROOT

__all__ = [
    "get_settings",
    "settings",
    "DB_PATH",
    "db_connection",
    "get_connection",
    "init_db",
    "REPO_ROOT",
]
