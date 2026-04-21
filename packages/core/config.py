"""Single settings module for the whole monorepo.

Loads .env once from the repo root, validates via pydantic, and exposes a
module-level `settings` singleton + `get_settings()` for DI-style usage.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.paths import DEFAULT_DB_PATH, REPO_ROOT


Environment = Literal["dev", "staging", "production"]


class Settings(BaseSettings):
    """All environment-driven config in one place."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Runtime ---------------------------------------------------------
    environment: Environment = Field(default="dev", validation_alias="ENVIRONMENT")

    # ---- Reddit ----------------------------------------------------------
    reddit_client_id: str = Field(default="", validation_alias="REDDIT_CLIENT_ID")
    reddit_client_secret: str = Field(default="", validation_alias="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field(
        default="intent-tracker/1.0", validation_alias="REDDIT_USER_AGENT"
    )

    # ---- GitHub / Dune ---------------------------------------------------
    github_token: str = Field(default="", validation_alias="GITHUB_TOKEN")
    dune_api_key: str = Field(default="", validation_alias="DUNE_API_KEY")

    # ---- Server ports ----------------------------------------------------
    api_port: int = Field(default=8000, validation_alias="API_PORT")
    web_port: int = Field(default=3000, validation_alias="WEB_PORT")

    # ---- CORS ------------------------------------------------------------
    # Comma-separated origin list. Empty string = use dev defaults.
    allowed_origins: str = Field(default="", validation_alias="ALLOWED_ORIGINS")

    # ---- API auth --------------------------------------------------------
    # Shared secret for /api/scan. Leave empty in dev (check is skipped when
    # environment=dev). In staging/production, a non-empty value is required.
    scan_token: str = Field(default="", validation_alias="SCAN_TOKEN")

    # ---- Scheduler -------------------------------------------------------
    scan_day: str = Field(default="*", validation_alias="SCAN_DAY")
    scan_hour: int = Field(default=6, validation_alias="SCAN_HOUR")
    scan_minute: int = Field(default=0, validation_alias="SCAN_MINUTE")

    # ---- Database --------------------------------------------------------
    db_path: Path = Field(default=DEFAULT_DB_PATH, validation_alias="DB_PATH")

    # ---- Supabase (when set, scanner writes go to Postgres instead of SQLite)
    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_service_key: str = Field(
        default="", validation_alias="SUPABASE_SERVICE_KEY"
    )
    supabase_anon_key: str = Field(default="", validation_alias="SUPABASE_ANON_KEY")

    # ---- Rate-limit delays (seconds) -------------------------------------
    coingecko_delay: float = 2.0
    github_delay: float = 1.0
    blog_delay: float = 3.0

    def get_allowed_origins(self) -> list[str]:
        """Return the CORS allow-list.

        - In dev (default): if ALLOWED_ORIGINS is empty, fall back to
          localhost:WEB_PORT / 127.0.0.1:WEB_PORT.
        - In staging/production: ALLOWED_ORIGINS must be set to a non-empty
          comma-separated list, otherwise fail closed (return []) so the
          browser blocks all cross-origin requests rather than silently
          accepting a permissive default.
        """
        if self.allowed_origins.strip():
            return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]
        if self.environment == "dev":
            return [
                f"http://localhost:{self.web_port}",
                f"http://127.0.0.1:{self.web_port}",
            ]
        # Fail closed in non-dev environments
        return []

    @field_validator("scan_token", mode="after")
    @classmethod
    def _require_scan_token_outside_dev(cls, value: str, info) -> str:
        env = info.data.get("environment", "dev")
        if env != "dev" and not value:
            raise ValueError(
                "SCAN_TOKEN must be set when ENVIRONMENT is staging or production"
            )
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance. Prefer this over importing `settings`."""
    return Settings()


# Module-level singleton for convenience
settings = get_settings()


# ---------------------------------------------------------------------------
# Legacy uppercase aliases
# ---------------------------------------------------------------------------
# Mirror the old `config.settings` API so existing imports of the form
# `from core.config import GITHUB_TOKEN` keep working. New code should prefer
# `settings.github_token` via the pydantic model.

REDDIT_CLIENT_ID = settings.reddit_client_id
REDDIT_CLIENT_SECRET = settings.reddit_client_secret
REDDIT_USER_AGENT = settings.reddit_user_agent
GITHUB_TOKEN = settings.github_token
DUNE_API_KEY = settings.dune_api_key
API_PORT = settings.api_port
WEB_PORT = settings.web_port
ENVIRONMENT = settings.environment
ALLOWED_ORIGINS = settings.allowed_origins
SCAN_TOKEN = settings.scan_token
SCAN_DAY = settings.scan_day
SCAN_HOUR = settings.scan_hour
SCAN_MINUTE = settings.scan_minute
COINGECKO_DELAY = settings.coingecko_delay
GITHUB_DELAY = settings.github_delay
BLOG_DELAY = settings.blog_delay
