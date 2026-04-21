import logging
from datetime import datetime

import requests

from config.keywords import PRIMARY_TERMS
from core.config import COINGECKO_DELAY
from config.sources import COINGECKO_IDS
from processing.matcher import extract_matches, is_relevant
from scanners.base import BaseScanner, ScanResult

logger = logging.getLogger(__name__)

COINGECKO_COIN_URL = "https://api.coingecko.com/api/v3/coins/{coin_id}"
COINGECKO_SEARCH_URL = "https://api.coingecko.com/api/v3/search"


class CoinGeckoScanner(BaseScanner):
    name = "coingecko"

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)

        # Fetch each configured coin ID (values are the actual API slugs)
        for display_name, coin_id in COINGECKO_IDS.items():
            try:
                resp = requests.get(
                    COINGECKO_COIN_URL.format(coin_id=coin_id),
                    params={"localization": "false", "tickers": "false",
                            "community_data": "true", "developer_data": "true"},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()

                description_text = data.get("description", {}).get("en", "")
                categories = data.get("categories", [])
                market_data = data.get("market_data", {})

                project_data = {
                    "name": data.get("name", coin_id),
                    "coingecko_id": data.get("id", coin_id),
                    "description": description_text[:500] if description_text else "",
                    "categories": categories,
                    "links": data.get("links", {}),
                    "market_cap_usd": market_data.get("market_cap", {}).get("usd"),
                    "current_price_usd": market_data.get("current_price", {}).get("usd"),
                    "total_volume_usd": market_data.get("total_volume", {}).get("usd"),
                    "price_change_24h_pct": market_data.get("price_change_percentage_24h"),
                    "price_change_7d_pct": market_data.get("price_change_percentage_7d"),
                    "source": "coingecko",
                    "keywords_matched": extract_matches(f"{data.get('name', '')} {description_text}"),
                }
                result.projects.append(project_data)

            except Exception as e:
                result.errors.append(f"CoinGecko coin fetch error for {coin_id}: {e}")
                logger.warning(f"Failed to fetch CoinGecko coin {coin_id}: {e}")

            self._sleep(COINGECKO_DELAY)

        # Search for a few key terms to discover new projects
        search_terms = list(PRIMARY_TERMS)[:5]
        for term in search_terms:
            try:
                resp = requests.get(
                    COINGECKO_SEARCH_URL,
                    params={"query": term},
                    timeout=30,
                )
                resp.raise_for_status()
                search_data = resp.json()

                for coin in search_data.get("coins", []):
                    coin_name = coin.get("name", "")
                    coin_id_found = coin.get("id", "")
                    text = f"{coin_name} {coin.get('symbol', '')}"

                    if is_relevant(text):
                        # Avoid duplicates
                        existing_ids = {p.get("coingecko_id") for p in result.projects}
                        if coin_id_found not in existing_ids:
                            project_data = {
                                "name": coin_name,
                                "coingecko_id": coin_id_found,
                                "symbol": coin.get("symbol", ""),
                                "market_cap_rank": coin.get("market_cap_rank"),
                                "source": "coingecko_search",
                                "discovered_via_term": term,
                                "keywords_matched": extract_matches(text),
                            }
                            result.projects.append(project_data)

            except Exception as e:
                result.errors.append(f"CoinGecko search error for '{term}': {e}")
                logger.warning(f"CoinGecko search failed for '{term}': {e}")

            self._sleep(COINGECKO_DELAY)

        result.items_found = len(result.projects)
        result.finished_at = datetime.utcnow()
        logger.info(f"CoinGecko scan complete: {result.items_found} projects found")
        return result
