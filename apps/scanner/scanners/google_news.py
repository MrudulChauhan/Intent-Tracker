import logging
from datetime import datetime
from urllib.parse import quote_plus

import feedparser

from config.keywords import PROTOCOL_NAMES
from core.config import BLOG_DELAY
from processing.matcher import is_relevant, extract_matches, score_relevance
from scanners.base import BaseScanner, ScanResult

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

BASE_QUERIES = [
    # Intent-DeFi news & research
    "intent based DeFi",
    "DeFi solver network",
    "cross-chain intents",
    "intent-centric rollup",
    "order flow auction DeFi",
    "solver competition DeFi",
    "chain abstraction intents",
    # Common intent-DeFi narratives
    "UniswapX solver",
    "CoW Protocol settlement",
    "1inch Fusion",
    "Across relayer",
    "Anoma intents",
    # X/Twitter-indexed content — news articles citing tweets, plus the
    # occasional tweet that Google News does index. Signal is thin compared
    # to a live X scraper; useful for catching widely-shared discussions.
    'site:x.com ("intent" OR "solver") DeFi',
    'site:twitter.com ("intent-based" OR "order flow") DeFi',
]


class GoogleNewsScanner(BaseScanner):
    name = "google_news"

    def _build_queries(self):
        queries = list(BASE_QUERIES)
        for protocol in PROTOCOL_NAMES:
            queries.append(f"{protocol} funding")
            queries.append(f"{protocol} raise")
        return queries

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)
        seen_urls = set()

        queries = self._build_queries()

        for query in queries:
            try:
                url = GOOGLE_NEWS_RSS.format(query=quote_plus(query))
                feed = feedparser.parse(url)

                if feed.bozo and not feed.entries:
                    result.errors.append(f"Google News parse error for '{query}': {feed.bozo_exception}")
                    continue

                for entry in feed.entries:
                    link = entry.get("link", "")
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)

                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    text = f"{title} {summary}"

                    if not is_relevant(text):
                        continue

                    published = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            published = datetime(*entry.published_parsed[:6]).isoformat()
                        except Exception:
                            published = entry.get("published", None)

                    mention_data = {
                        "title": title,
                        "url": link,
                        "text": summary[:1000] if summary else "",
                        "published": published,
                        "source": "google_news",
                        "search_query": query,
                        "relevance_score": score_relevance(text),
                        "keywords_matched": extract_matches(text),
                    }
                    result.mentions.append(mention_data)

            except Exception as e:
                result.errors.append(f"Google News error for '{query}': {e}")
                logger.warning(f"Google News fetch failed for '{query}': {e}")

            self._sleep(BLOG_DELAY)

        result.items_found = len(result.mentions)
        result.finished_at = datetime.utcnow()
        logger.info(f"Google News scan complete: {result.items_found} mentions found")
        return result
