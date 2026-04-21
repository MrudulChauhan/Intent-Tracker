import logging
import time
from datetime import datetime

import feedparser

from config.sources import RSS_FEEDS, REDDIT_RSS_FEEDS
from processing.matcher import is_relevant, extract_matches, score_relevance
from scanners.base import BaseScanner, ScanResult

logger = logging.getLogger(__name__)

# Reddit blocks default feedparser UA
REDDIT_HEADERS = {
    "User-Agent": "IntentTracker/1.0 (research bot; +https://github.com)"
}


class RSSScanner(BaseScanner):
    name = "rss"

    def _parse_feed(self, feed_url, source_label, result):
        """Parse a single feed and append relevant mentions to result."""
        try:
            # Reddit needs custom headers
            if "reddit.com" in feed_url:
                feed = feedparser.parse(feed_url, request_headers=REDDIT_HEADERS)
            else:
                feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                result.errors.append(f"Failed to parse feed {feed_url}: {feed.bozo_exception}")
                return 0

            count = 0
            for entry in feed.entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                # Reddit entries often have content in 'content' field
                content = ""
                if hasattr(entry, "content") and entry.content:
                    content = entry.content[0].get("value", "")

                text = f"{title} {summary} {content}"

                if not is_relevant(text):
                    continue

                # Parse published date
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6]).isoformat()
                    except Exception:
                        published = entry.get("published", None)
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    try:
                        published = datetime(*entry.updated_parsed[:6]).isoformat()
                    except Exception:
                        published = entry.get("updated", None)

                # Deduplicate by URL within this scan
                url = entry.get("link", "")
                existing_urls = {m.get("url") for m in result.mentions}
                if url in existing_urls:
                    continue

                mention_data = {
                    "title": title,
                    "url": url,
                    "text": (summary or content)[:1000],
                    "published": published,
                    "author": entry.get("author", ""),
                    "source": source_label,
                    "feed_url": feed_url,
                    "relevance_score": score_relevance(text),
                    "keywords_matched": extract_matches(text),
                }
                result.mentions.append(mention_data)
                count += 1

            return count

        except Exception as e:
            result.errors.append(f"RSS feed error for {feed_url}: {e}")
            logger.warning(f"Failed to process RSS feed {feed_url}: {e}")
            return 0

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)

        # Process news RSS feeds
        for feed_url in RSS_FEEDS:
            found = self._parse_feed(feed_url, "rss", result)
            logger.debug(f"RSS feed {feed_url}: {found} relevant items")

        # Process Reddit RSS feeds (with rate limiting to avoid 429s)
        reddit_count = 0
        for i, feed_url in enumerate(REDDIT_RSS_FEEDS):
            found = self._parse_feed(feed_url, "reddit", result)
            reddit_count += found
            # Rate limit: 1 request per second for Reddit
            if i < len(REDDIT_RSS_FEEDS) - 1:
                time.sleep(1.0)

        logger.info(f"Reddit RSS: {reddit_count} relevant mentions from {len(REDDIT_RSS_FEEDS)} feeds")

        result.items_found = len(result.mentions)
        result.finished_at = datetime.utcnow()
        logger.info(f"RSS scan complete: {result.items_found} mentions found")
        return result
