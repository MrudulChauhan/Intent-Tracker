"""
On-chain intent-fill scanner powered by Dune Analytics (P1.5).

For each configured intent protocol, this scanner:
  1. Fetches the latest pre-executed result of a public Dune query (via
     ``DuneClient.get_latest_result`` — no execution credits burned).
  2. Normalises each row into an ``intent_fills`` record and hands it to the
     writer for upsert-on-tx_hash.
  3. Aggregates the last 7 days of fills into per-(solver, date, protocol,
     chain) buckets and upserts them into ``solver_daily_stats``.

Only CoW Protocol ships with a real ``query_id`` today. The other five
entries are placeholders: once you fork a public dashboard on dune.com (see
``docs/onchain_scanner.md``), drop the query ID into ``DUNE_QUERIES`` and the
scanner picks it up automatically.

The scanner is registered in the scheduler behind ``ONCHAIN_SCANNER_ENABLED``
(default ``false``) so it cannot break existing nightly scans until it's
manually flipped on.
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

from scanners.base import BaseScanner, ScanResult

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Configuration — public Dune query IDs per protocol.
# -----------------------------------------------------------------------------
# Each entry maps a protocol slug to:
#   query_id : int | None   — public Dune query whose latest result we read
#   chain    : str          — default chain label written to intent_fills.chain
#                             when the row itself does not carry one
#
# Expected output columns from every query (case-insensitive, missing cols
# tolerated — see ``_normalise_row``):
#   block_time, tx_hash, solver, chain, amount_in_usd, token_in,
#   token_out, user_address
#
# TODO for any query_id=None: fork a public dashboard on dune.com that filters
# to solver fills with the above columns, save it, and paste the numeric ID
# here. Keep the select list aligned with _EXPECTED_COLUMNS below.
# -----------------------------------------------------------------------------
DUNE_QUERIES: dict[str, dict[str, Any]] = {
    "cow_protocol": {
        # CoW Swap V2 User Trade Data — maintained by CoW team / bh2smith.
        # https://dune.com/queries/1888958
        # Columns: block_time, tx_hash, solver, trader, sell_token, buy_token,
        # atoms_sold, atoms_bought, usd_value. Trade-level (per-fill).
        "query_id": 1888958,
        "chain": "ethereum",
    },
    "uniswap_x": {
        # Flashbots maintains the reference dashboard at
        # https://dune.com/flashbots/uniswap-x but the single "fills feed"
        # query_id was not identifiable from public search — pick it manually
        # from the dashboard. Candidate (aggregated, NOT per-fill): 4050151.
        "query_id": None,
        "chain": "ethereum",
    },
    "1inch_fusion": {
        # Public 1inch Fusion dashboards are aggregated (monthly/all-time),
        # not per-fill. Candidate aggregated: 2180755. For raw fills, author
        # a query against oneinch_fusion_*.SettlementExtension_evt_OrderFilled.
        "query_id": None,
        "chain": "ethereum",
    },
    "across_v3": {
        # Across V3 & V3.5 Fill Txs — per-fill granularity, multi-chain.
        # https://dune.com/queries/4717811
        # Columns: blockchain, evt_block_time, evt_tx_hash, evt_block_number,
        # depositId, relayer (=solver), inputToken/outputToken, depositor.
        "query_id": 4717811,
        "chain": "multichain",
    },
    "bebop": {
        # Only public query found is weekly-aggregate (1037190), not a fill
        # feed. Author a custom query against Bebop settlement events, OR
        # accept weekly aggregates only.
        "query_id": None,
        "chain": "ethereum",
    },
    "hashflow": {
        # Hashflow Txs 7d — per-tx rolling 7-day window, official Hashflow org.
        # https://dune.com/queries/3099694
        # Columns: block_time, contract_name, tx_hash, trader, amount_usd,
        # token_in/token_out, maker/mm_address.
        "query_id": 3099694,
        "chain": "multichain",
    },
}


# Tolerant column-name matching. Each canonical key maps to a list of aliases;
# the first alias that exists on the row wins. Keep lowercase.
_EXPECTED_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "block_time":    ("block_time", "blocktime", "evt_block_time", "time", "ts"),
    "tx_hash":       ("tx_hash", "hash", "evt_tx_hash", "transaction_hash"),
    "solver_address": ("solver", "solver_address", "filler", "resolver"),
    "chain":         ("chain", "blockchain"),
    "amount_in_usd": ("amount_in_usd", "volume_usd", "usd_value", "usd"),
    "token_in":      ("token_in", "sell_token", "src_token", "input_token"),
    "token_out":     ("token_out", "buy_token", "dst_token", "output_token"),
    "user_address":  ("user", "user_address", "trader", "owner"),
}


# Keep a modest delay between Dune calls so one cold-cache result fetch
# can't trip per-second rate limits even when all 6 protocols are live.
_REQUEST_DELAY_SEC = 1.5

# Rollup window (inclusive of today) for solver_daily_stats.
_ROLLUP_DAYS = 7


@dataclass
class _ProtocolOutcome:
    """Per-protocol scan outcome, used for logging & the final summary."""

    protocol: str
    fills_inserted: int = 0
    stats_upserted: int = 0
    error: str | None = None


class OnchainDuneScanner(BaseScanner):
    """Scanner that pulls intent-protocol fills from Dune, per solver."""

    name = "onchain_dune"

    def __init__(self, writer: Any | None = None) -> None:
        # Writer is injected by the scheduler in production; we keep the
        # default-None path so ``scripts/test_onchain_dune.py`` can import
        # and validate config without Supabase credentials.
        self._writer = writer
        self._client = None  # lazy — avoid importing dune_client at collect time

    # ---- public entry point --------------------------------------------------

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)

        api_key = os.environ.get("DUNE_API_KEY", "").strip()
        if not api_key:
            msg = "DUNE_API_KEY is not set — skipping onchain_dune scan"
            logger.warning(msg)
            result.errors.append(msg)
            result.finished_at = datetime.utcnow()
            return result

        try:
            self._client = self._build_client(api_key)
        except Exception as exc:  # pragma: no cover - import-time failure
            msg = f"Failed to construct DuneClient: {exc}"
            logger.exception(msg)
            result.errors.append(msg)
            result.finished_at = datetime.utcnow()
            return result

        outcomes: list[_ProtocolOutcome] = []
        total_fills = 0

        for protocol, cfg in DUNE_QUERIES.items():
            query_id = cfg.get("query_id")
            default_chain = cfg.get("chain", "ethereum")

            if query_id is None:
                logger.info(
                    "Skipping %s: no query_id configured (TODO — see DUNE_QUERIES).",
                    protocol,
                )
                continue

            outcome = _ProtocolOutcome(protocol=protocol)
            try:
                rows = self._fetch_latest_rows(int(query_id))
                logger.info("Dune %s (query %s) returned %d rows",
                            protocol, query_id, len(rows))

                normalised = [
                    self._normalise_row(protocol, default_chain, raw) for raw in rows
                ]
                normalised = [r for r in normalised if r is not None]

                if not normalised:
                    logger.info("No usable rows after normalisation for %s", protocol)
                else:
                    outcome.fills_inserted = self._write_fills(normalised)
                    outcome.stats_upserted = self._write_daily_rollups(
                        protocol, default_chain, normalised
                    )
                    total_fills += outcome.fills_inserted
            except Exception as exc:
                # One protocol blowing up must not take the others down.
                outcome.error = str(exc)
                logger.exception("onchain_dune: protocol %s failed: %s", protocol, exc)
                result.errors.append(f"{protocol}: {exc}")

            outcomes.append(outcome)
            time.sleep(_REQUEST_DELAY_SEC)

        result.items_found = total_fills
        result.finished_at = datetime.utcnow()
        logger.info(
            "onchain_dune scan complete: %d fills inserted across %d protocols; outcomes=%s",
            total_fills,
            sum(1 for o in outcomes if o.error is None and o.fills_inserted),
            [
                {
                    "protocol": o.protocol,
                    "fills": o.fills_inserted,
                    "stats": o.stats_upserted,
                    "error": o.error,
                }
                for o in outcomes
            ],
        )
        return result

    # ---- dune-client plumbing -----------------------------------------------

    @staticmethod
    def _build_client(api_key: str):
        """Import lazily so the scanner module loads even when dune-client
        isn't installed (e.g. in the dry-run test stub)."""
        from dune_client.client import DuneClient  # type: ignore

        return DuneClient(api_key=api_key)

    def _fetch_latest_rows(self, query_id: int) -> list[dict[str, Any]]:
        """Pull the most recent cached execution for ``query_id``.

        Uses ``get_latest_result`` so we never trigger a (billable) execution.
        Returns an empty list on empty results.
        """
        assert self._client is not None, "DuneClient not initialised"
        try:
            response = self._client.get_latest_result(query_id)
        except Exception:
            raise

        result = getattr(response, "result", None)
        if result is None:
            return []
        rows = getattr(result, "rows", None)
        if rows is None and isinstance(result, dict):
            rows = result.get("rows", [])
        return list(rows or [])

    # ---- normalisation -------------------------------------------------------

    @staticmethod
    def _pick(row: dict[str, Any], aliases: Iterable[str]) -> Any:
        lower = {k.lower(): v for k, v in row.items()}
        for alias in aliases:
            if alias in lower and lower[alias] not in (None, ""):
                return lower[alias]
        return None

    @classmethod
    def _normalise_row(
        cls, protocol: str, default_chain: str, raw: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Map a Dune result row onto our intent_fills schema. Drops rows
        missing tx_hash (the upsert key) since they'd collide on insert."""
        tx_hash = cls._pick(raw, _EXPECTED_COLUMN_ALIASES["tx_hash"])
        if not tx_hash:
            return None

        block_time_raw = cls._pick(raw, _EXPECTED_COLUMN_ALIASES["block_time"])
        block_time_iso = cls._coerce_iso_timestamp(block_time_raw)

        amount_raw = cls._pick(raw, _EXPECTED_COLUMN_ALIASES["amount_in_usd"])
        amount_usd: float | None
        try:
            amount_usd = float(amount_raw) if amount_raw is not None else None
        except (TypeError, ValueError):
            amount_usd = None

        return {
            "protocol": protocol,
            "solver_address": cls._lc(cls._pick(raw, _EXPECTED_COLUMN_ALIASES["solver_address"])),
            "tx_hash": cls._lc(tx_hash),
            "block_time": block_time_iso,
            "chain": (cls._pick(raw, _EXPECTED_COLUMN_ALIASES["chain"]) or default_chain),
            "amount_in_usd": amount_usd,
            "token_in": cls._lc(cls._pick(raw, _EXPECTED_COLUMN_ALIASES["token_in"])),
            "token_out": cls._lc(cls._pick(raw, _EXPECTED_COLUMN_ALIASES["token_out"])),
            "user_address": cls._lc(cls._pick(raw, _EXPECTED_COLUMN_ALIASES["user_address"])),
            "raw_event": raw,
        }

    @staticmethod
    def _lc(value: Any) -> Any:
        return value.lower() if isinstance(value, str) else value

    @staticmethod
    def _coerce_iso_timestamp(value: Any) -> str | None:
        """Accept datetime, epoch seconds/ms, or ISO strings → ISO-8601 UTC."""
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        if isinstance(value, (int, float)):
            # Heuristic: >1e12 = milliseconds, else seconds
            secs = float(value) / 1000.0 if float(value) > 1e12 else float(value)
            return datetime.fromtimestamp(secs, tz=timezone.utc).isoformat()
        if isinstance(value, str):
            # Accept Dune's typical "YYYY-MM-DD HH:MM:SS.SSS UTC" by stripping UTC
            cleaned = value.replace(" UTC", "").replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(cleaned)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.isoformat()
            except ValueError:
                return value  # best-effort — Postgres will coerce if valid
        return None

    # ---- writes --------------------------------------------------------------

    def _write_fills(self, fills: list[dict[str, Any]]) -> int:
        """Upsert each fill on tx_hash. Returns the number of rows the writer
        confirmed (insert or merge). Silently skips if no writer is attached
        (e.g. the dry-run test stub)."""
        if self._writer is None:
            logger.debug("No writer attached; skipping intent_fills write.")
            return 0

        inserted = 0
        for row in fills:
            try:
                if self._writer.insert_intent_fill(row) is not None:
                    inserted += 1
            except Exception as exc:
                logger.warning(
                    "insert_intent_fill failed for tx %s: %s", row.get("tx_hash"), exc
                )
        return inserted

    def _write_daily_rollups(
        self,
        protocol: str,
        default_chain: str,
        fills: list[dict[str, Any]],
    ) -> int:
        """Bucket fills into (solver, date, protocol, chain) cells over the
        last _ROLLUP_DAYS days and upsert each cell into solver_daily_stats."""
        if self._writer is None:
            return 0

        cutoff = datetime.now(tz=timezone.utc).date() - timedelta(days=_ROLLUP_DAYS - 1)

        buckets: dict[tuple[str, date, str, str], dict[str, Any]] = defaultdict(
            lambda: {"fills_count": 0, "volume_usd": 0.0, "users": set()}
        )

        for row in fills:
            bt_iso = row.get("block_time")
            if not bt_iso:
                continue
            try:
                bt = datetime.fromisoformat(bt_iso)
            except ValueError:
                continue
            d = bt.date()
            if d < cutoff:
                continue
            solver = row.get("solver_address") or "unknown"
            chain = row.get("chain") or default_chain
            key = (solver, d, protocol, chain)
            bucket = buckets[key]
            bucket["fills_count"] += 1
            if isinstance(row.get("amount_in_usd"), (int, float)):
                bucket["volume_usd"] += float(row["amount_in_usd"])
            if row.get("user_address"):
                bucket["users"].add(row["user_address"])

        upserted = 0
        for (solver, d, proto, chain), agg in buckets.items():
            stat_row = {
                "solver_address": solver,
                "date": d.isoformat(),
                "protocol": proto,
                "chain": chain,
                "fills_count": agg["fills_count"],
                "volume_usd": round(agg["volume_usd"], 2),
                "unique_users": len(agg["users"]),
            }
            try:
                if self._writer.upsert_solver_daily_stat(stat_row) is not None:
                    upserted += 1
            except Exception as exc:
                logger.warning(
                    "upsert_solver_daily_stat failed for %s/%s/%s: %s",
                    solver, d, proto, exc,
                )
        return upserted


# Convenience re-export for scripts/tests.
__all__ = ["OnchainDuneScanner", "DUNE_QUERIES"]
