#!/usr/bin/env python3
"""One-time interactive X/Twitter login helper (P1.4).

Usage
-----
Run once, by hand, from the repo root, **after** setting X_USERNAME,
X_EMAIL, and X_PASSWORD in your .env (see .env.example)::

    uv run python scripts/twitter_login.py

This logs into X via twikit, saves session cookies to the path pointed to
by X_COOKIES_FILE (default: ./data/x_cookies.json), and exits. From that
point on the scanner reads the cookies file instead of re-entering the
password -- which avoids retriggering X's anti-automation flow (captchas,
email codes, device-verification prompts) on every run.

Notes
-----
* Use a **throwaway** X account. twikit relies on the private web API;
  Anthropic /X's ToS doesn't love this, so bans happen. Don't sign in with
  your main.
* The account should already have email + phone verified via the X web
  UI before running this script, or the login call will fail.
* Re-run this script whenever the cookies go stale (symptom: scanner
  logs 401s or ``twikit.errors.Unauthorized``).
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


DEFAULT_COOKIES_PATH = Path("./data/x_cookies.json")


def _load_env() -> None:
    """Best-effort .env loader so the script works without `uv run`.

    If python-dotenv isn't installed we silently skip; env vars may still
    be set by the shell.
    """
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
    except ImportError:
        return
    # Look for .env in cwd then repo root.
    for candidate in (Path(".env"), Path(__file__).resolve().parent.parent / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            break


async def _login() -> int:
    try:
        from twikit import Client  # type: ignore[import-not-found]
    except ImportError:
        print(
            "ERROR: twikit is not installed. Run `uv sync` first.",
            file=sys.stderr,
        )
        return 2

    username = (os.getenv("X_USERNAME") or "").strip()
    email = (os.getenv("X_EMAIL") or "").strip()
    password = (os.getenv("X_PASSWORD") or "").strip()

    if not (username and email and password):
        print(
            "ERROR: X_USERNAME, X_EMAIL, and X_PASSWORD must all be set in "
            ".env before running this login helper.",
            file=sys.stderr,
        )
        return 2

    cookies_path = Path(
        (os.getenv("X_COOKIES_FILE") or str(DEFAULT_COOKIES_PATH)).strip()
    ).expanduser()
    cookies_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[twitter_login] Logging in as @{username} ...")
    client = Client("en-US")
    await client.login(
        auth_info_1=username,
        auth_info_2=email,
        password=password,
    )

    client.save_cookies(str(cookies_path))
    print(f"[twitter_login] OK. Cookies saved to {cookies_path}")
    print(
        "[twitter_login] Set TWITTER_SCANNER_ENABLED=true in .env to enable "
        "the scanner on the next run."
    )
    return 0


def main() -> int:
    _load_env()
    try:
        return asyncio.run(_login())
    except KeyboardInterrupt:
        print("\n[twitter_login] Interrupted.", file=sys.stderr)
        return 130
    except Exception as e:  # noqa: BLE001
        print(f"[twitter_login] Login failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
