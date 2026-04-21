"""
Dune Analytics scanner for intent protocol metrics.

Queries pre-built public Dune queries for UniswapX and CoW Protocol volume,
and searches for relevant intent-related analytics queries.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Any

import requests

from core.config import settings
from scanners.base import BaseScanner, ScanResult

logger = logging.getLogger(__name__)

DUNE_BASE_URL = "https://api.dune.com/api/v1"

# Pre-built public query IDs for intent protocol metrics
QUERY_IDS = {
    "uniswapx_volume": 3462023,
    "cow_protocol_volume": 3109611,
}

# Conservative rate limit: small delay between requests to stay within free tier
REQUEST_DELAY = 2.0


class DuneScanner(BaseScanner):
    name = "dune"

    def __init__(self):
        self.api_key = settings.dune_api_key
        self.headers = {"X-Dune-API-Key": self.api_key}

    def _get_query_results(self, query_id: int) -> Dict[str, Any]:
        """Fetch results of an already-executed Dune query."""
        url = f"{DUNE_BASE_URL}/query/{query_id}/results"
        try:
            resp = requests.get(url, headers=self.headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                logger.warning("Dune rate limit hit for query %d", query_id)
            raise
        except Exception as e:
            logger.error("Failed to fetch Dune query %d: %s", query_id, e)
            raise

    def _search_queries(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search Dune for relevant public queries."""
        url = f"{DUNE_BASE_URL}/search"
        params = {"q": search_term, "limit": limit}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json().get("queries", [])
        except Exception as e:
            logger.warning("Dune search failed for '%s': %s", search_term, e)
            return []

    def _extract_volume_from_results(self, data: Dict, protocol_name: str) -> Dict[str, Any]:
        """Extract volume metric from Dune query results."""
        result = data.get("result", {})
        rows = result.get("rows", [])

        if not rows:
            return None

        # Try to find a total volume field in the most recent row
        latest = rows[0] if rows else {}
        volume = None

        # Common column names for volume in Dune queries
        volume_keys = ["volume", "total_volume", "volume_usd", "total_volume_usd",
                       "usd_volume", "cumulative_volume"]
        for key in volume_keys:
            if key in latest:
                volume = latest[key]
                break

        # Fallback: use the first numeric value
        if volume is None:
            for val in latest.values():
                if isinstance(val, (int, float)) and val > 0:
                    volume = val
                    break

        if volume is not None:
            return {
                "project_name": protocol_name,
                "tvl": volume,
                "volume_24h": None,
                "chains": ["Ethereum"],
                "source": "dune",
            }
        return None

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)

        if not self.api_key:
            result.errors.append("DUNE_API_KEY not configured")
            result.finished_at = datetime.utcnow()
            return result

        # Query pre-built public queries (conservative - only 2 queries)
        protocol_map = {
            "uniswapx_volume": "UniswapX",
            "cow_protocol_volume": "CoW Protocol",
        }

        for query_key, protocol_name in protocol_map.items():
            query_id = QUERY_IDS[query_key]
            try:
                data = self._get_query_results(query_id)
                metric = self._extract_volume_from_results(data, protocol_name)
                if metric:
                    result.metrics.append(metric)
                    logger.info("Got Dune metric for %s", protocol_name)
            except Exception as e:
                result.errors.append(f"Failed query {query_id} ({protocol_name}): {e}")

            time.sleep(REQUEST_DELAY)

        # Search for additional intent-related queries (one search call)
        try:
            search_results = self._search_queries("intent defi", limit=10)
            logger.info("Dune search returned %d queries", len(search_results))
            # Log discovered queries for future use but don't execute them
            # to conserve credits on free tier
            for q in search_results[:5]:
                logger.info(
                    "Discovered Dune query: id=%s name='%s'",
                    q.get("query_id"),
                    q.get("name", ""),
                )
        except Exception as e:
            result.errors.append(f"Dune search failed: {e}")

        result.finished_at = datetime.utcnow()
        result.items_found = len(result.metrics)
        return result
