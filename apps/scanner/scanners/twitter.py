"""X/Twitter scanner (P1.4).

Uses the unofficial ``twikit`` library (requires a logged-in X account --
use a throwaway, not your primary). Fetches the latest tweets from a
curated seed list, filters by relevance via the shared matcher, and emits
mention rows for ``social_mentions``.

Cookie-file auth is preferred over password auth: cookies avoid triggering
X's anti-automation flows (email verification, captchas) on every run.
Password auth is kept as a fallback for first-time setup.

This scanner never follows / likes / posts -- read-only.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Any

from config.twitter_seeds import SEED_ACCOUNTS, get_all_seeds
from processing.dedup import normalize_url
from processing.matcher import extract_matches, score_relevance
from scanners.base import BaseScanner, ScanResult


logger = logging.getLogger(__name__)


RELEVANCE_THRESHOLD = 0.3
TWEETS_PER_SEED = 20
SECONDS_BETWEEN_SEEDS = 1.0
MAX_BACKOFF_SECONDS = 300.0
INITIAL_BACKOFF_SECONDS = 15.0
MAX_RATE_LIMIT_RETRIES = 3


def _env(name: str) -> str:
    """Read an env var, stripping whitespace; return ''."""
    return (os.getenv(name) or "").strip()


class TwitterScanner(BaseScanner):
    """Daily scrape of seed accounts' latest tweets via twikit."""

    name = "twitter"

    def __init__(
        self,
        relevance_threshold: float = RELEVANCE_THRESHOLD,
        tweets_per_seed: int = TWEETS_PER_SEED,
        seconds_between_seeds: float = SECONDS_BETWEEN_SEEDS,
    ) -> None:
        self.relevance_threshold = relevance_threshold
        self.tweets_per_seed = tweets_per_seed
        self.seconds_between_seeds = seconds_between_seeds

    # ----- BaseScanner interface (synchronous) -------------------------------

    def scan(self) -> ScanResult:
        """Run the scan synchronously by wrapping the async core."""
        result = ScanResult(scanner_name=self.name)
        try:
            asyncio.run(self._scan_async(result))
        except RuntimeError as e:
            # asyncio.run inside an already-running loop (edge case: Jupyter)
            msg = f"TwitterScanner could not start event loop: {e}"
            logger.warning(msg)
            result.errors.append(msg)
        except Exception as e:  # noqa: BLE001 -- top-level guard
            msg = f"TwitterScanner top-level failure: {e}"
            logger.exception(msg)
            result.errors.append(msg)
        finally:
            result.items_found = len(result.mentions)
            result.finished_at = datetime.utcnow()
        return result

    # ----- Auth / client bootstrap -------------------------------------------

    def _resolve_auth(self) -> dict[str, Any]:
        """Return an auth descriptor, preferring cookies over password.

        Raises ValueError if neither a cookies file nor full credentials are
        available -- the scanner should be skipped (scheduler handles the
        resulting error).
        """
        cookies_file = _env("X_COOKIES_FILE")
        if cookies_file:
            path = Path(cookies_file).expanduser()
            if path.is_file():
                return {"mode": "cookies", "path": path}
            logger.warning(
                "X_COOKIES_FILE=%s is set but the file does not exist; "
                "falling back to password auth if available.",
                cookies_file,
            )

        username = _env("X_USERNAME")
        email = _env("X_EMAIL")
        password = _env("X_PASSWORD")
        if username and email and password:
            return {
                "mode": "password",
                "username": username,
                "email": email,
                "password": password,
            }

        raise ValueError(
            "TwitterScanner requires either X_COOKIES_FILE (preferred, pointing "
            "at a saved cookies JSON from scripts/twitter_login.py) OR all of "
            "X_USERNAME, X_EMAIL, X_PASSWORD. None were found."
        )

    async def _build_client(self):  # type: ignore[no-untyped-def]
        """Instantiate a twikit Client and authenticate."""
        # Import lazily so a missing twikit install doesn't break import-time
        # of the scheduler (mirrors the Reddit scanner's lazy praw import).
        try:
            from twikit import Client  # type: ignore[import-not-found]
        except ImportError as e:
            raise ImportError(
                "twikit is not installed. Add it to pyproject.toml and run "
                "`uv sync`."
            ) from e

        auth = self._resolve_auth()
        client = Client("en-US")

        if auth["mode"] == "cookies":
            client.load_cookies(str(auth["path"]))
            logger.info("TwitterScanner: loaded cookies from %s", auth["path"])
        else:
            logger.info(
                "TwitterScanner: logging in with password auth as %s",
                auth["username"],
            )
            await client.login(
                auth_info_1=auth["username"],
                auth_info_2=auth["email"],
                password=auth["password"],
            )
        return client

    # ----- Core async scan ---------------------------------------------------

    async def _scan_async(self, result: ScanResult) -> None:
        try:
            client = await self._build_client()
        except Exception as e:  # noqa: BLE001
            msg = f"TwitterScanner auth/client setup failed: {e}"
            logger.error(msg)
            result.errors.append(msg)
            return

        seeds = get_all_seeds()
        logger.info(
            "TwitterScanner starting: %d seed accounts across %d categories",
            len(seeds),
            len(SEED_ACCOUNTS),
        )

        seen_urls: set[str] = set()
        total_considered = 0
        total_kept = 0

        for idx, handle in enumerate(seeds):
            try:
                tweets = await self._fetch_with_backoff(client, handle)
            except Exception as e:  # noqa: BLE001 -- one seed failure shouldn't kill the whole scan
                msg = f"TwitterScanner: fetch failed for @{handle}: {e}"
                logger.warning(msg)
                result.errors.append(msg)
                await asyncio.sleep(self.seconds_between_seeds)
                continue

            considered_for_seed = 0
            kept_for_seed = 0

            for tweet in tweets or []:
                total_considered += 1
                considered_for_seed += 1

                if not self._is_authorable(tweet, handle):
                    continue

                text = self._tweet_text(tweet)
                relevance = score_relevance(text)
                if relevance < self.relevance_threshold:
                    continue

                mention = self._to_mention(tweet, handle, relevance, text)
                normalized = normalize_url(mention["url"])
                if normalized in seen_urls:
                    continue
                seen_urls.add(normalized)

                result.mentions.append(mention)
                kept_for_seed += 1
                total_kept += 1

            logger.info(
                "TwitterScanner seed @%s: considered=%d kept=%d",
                handle, considered_for_seed, kept_for_seed,
            )

            # Polite delay between seeds regardless of success.
            if idx < len(seeds) - 1:
                await asyncio.sleep(self.seconds_between_seeds)

        logger.info(
            "TwitterScanner complete: seeds=%d considered=%d kept=%d errors=%d",
            len(seeds), total_considered, total_kept, len(result.errors),
        )

    async def _fetch_with_backoff(self, client, handle: str):  # type: ignore[no-untyped-def]
        """Fetch recent tweets for a handle, honouring TooManyRequests.

        Uses exponential backoff with jitter. Gives up after
        ``MAX_RATE_LIMIT_RETRIES`` attempts and lets the caller log the error.
        """
        try:
            from twikit.errors import TooManyRequests  # type: ignore[import-not-found]
        except ImportError:
            TooManyRequests = Exception  # type: ignore[assignment]

        backoff = INITIAL_BACKOFF_SECONDS
        attempt = 0
        while True:
            try:
                return await client.get_user_tweets(
                    handle, "Tweets", count=self.tweets_per_seed
                )
            except TooManyRequests as e:
                attempt += 1
                if attempt > MAX_RATE_LIMIT_RETRIES:
                    raise
                sleep_for = min(
                    backoff + random.uniform(0, backoff / 2),  # noqa: S311 -- jitter, not crypto
                    MAX_BACKOFF_SECONDS,
                )
                logger.warning(
                    "TwitterScanner: rate-limited on @%s (attempt %d), "
                    "sleeping %.1fs: %s",
                    handle, attempt, sleep_for, e,
                )
                await asyncio.sleep(sleep_for)
                backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)

    # ----- Tweet shaping -----------------------------------------------------

    @staticmethod
    def _is_authorable(tweet: Any, handle: str) -> bool:
        """Filter out retweets and replies-to-others.

        Keep:
          - Original tweets by the seed account.
          - Quote tweets (author is commenting on another tweet).
        Drop:
          - Plain retweets.
          - Replies whose target is not the seed account itself.
        """
        # twikit exposes `retweeted_tweet` / `is_quote_status` attrs; defensive getattr.
        if getattr(tweet, "retweeted_tweet", None):
            return False

        in_reply_to = getattr(tweet, "in_reply_to", None) or getattr(
            tweet, "in_reply_to_screen_name", None
        )
        is_quote = bool(getattr(tweet, "is_quote_status", False)) or bool(
            getattr(tweet, "quoted_tweet", None)
        )

        if in_reply_to and not is_quote:
            target = str(in_reply_to).lstrip("@").lower()
            if target and target != handle.lower():
                return False
        return True

    @staticmethod
    def _tweet_text(tweet: Any) -> str:
        # twikit Tweet exposes `.text` (and sometimes `.full_text`); normalize.
        return (
            getattr(tweet, "full_text", None)
            or getattr(tweet, "text", None)
            or ""
        )

    @staticmethod
    def _tweet_published_at(tweet: Any) -> str | None:
        # twikit gives `created_at` as a string; also exposes `created_at_datetime`.
        dt = getattr(tweet, "created_at_datetime", None)
        if isinstance(dt, datetime):
            return dt.isoformat()
        raw = getattr(tweet, "created_at", None)
        if isinstance(raw, datetime):
            return raw.isoformat()
        return raw if raw else None

    def _to_mention(
        self,
        tweet: Any,
        handle: str,
        relevance: float,
        text: str,
    ) -> dict[str, Any]:
        tweet_id = getattr(tweet, "id", None) or getattr(tweet, "rest_id", "")
        favorites = (
            getattr(tweet, "favorite_count", None)
            or getattr(tweet, "favorites", 0)
            or 0
        )
        return {
            "source": "twitter",
            "title": text[:200],
            "url": f"https://x.com/{handle}/status/{tweet_id}",
            "author": f"@{handle}",
            "content_snippet": text,
            "published_at": self._tweet_published_at(tweet),
            "sentiment_score": None,
            "upvotes": favorites,
            "relevance_score": relevance,
            "keywords_matched": extract_matches(text),
        }
