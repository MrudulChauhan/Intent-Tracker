import logging
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from core.config import BLOG_DELAY
from config.sources import BLOG_SOURCES
from processing.matcher import is_relevant, extract_matches, score_relevance
from scanners.base import BaseScanner, ScanResult

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "intent-tracker/1.0 (research bot)",
}


class BlogScanner(BaseScanner):
    name = "blogs"

    def _extract_mirror_articles(self, soup, base_url):
        """Extract articles from Mirror.xyz pages."""
        articles = []
        # Mirror uses various card/link structures
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            # Mirror article links typically contain the full URL or a path
            if "/writing/" in href or href.startswith("https://mirror.xyz"):
                title_el = link.find(["h1", "h2", "h3", "p"])
                title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)
                if title and len(title) > 10:
                    full_url = href if href.startswith("http") else urljoin(base_url, href)
                    articles.append({"title": title, "url": full_url})
        return articles

    def _extract_medium_articles(self, soup, base_url):
        """Extract articles from Medium pages."""
        articles = []
        for article in soup.find_all("article"):
            link = article.find("a", href=True)
            title_el = article.find(["h1", "h2", "h3"])
            if link and title_el:
                title = title_el.get_text(strip=True)
                href = link.get("href", "")
                full_url = href if href.startswith("http") else urljoin(base_url, href)
                articles.append({"title": title, "url": full_url})

        # Fallback: look for h3 links (common Medium pattern)
        if not articles:
            for h3 in soup.find_all("h3"):
                parent_link = h3.find_parent("a", href=True)
                if parent_link:
                    title = h3.get_text(strip=True)
                    href = parent_link.get("href", "")
                    full_url = href if href.startswith("http") else urljoin(base_url, href)
                    articles.append({"title": title, "url": full_url})

        return articles

    def _extract_generic_articles(self, soup, base_url):
        """Generic extraction for blog-like pages."""
        articles = []
        # Look for article or post containers
        for container in soup.find_all(["article", "div"], class_=lambda c: c and any(
            kw in (c if isinstance(c, str) else " ".join(c))
            for kw in ["post", "article", "entry", "blog", "card"]
        )):
            link = container.find("a", href=True)
            title_el = container.find(["h1", "h2", "h3", "h4"])
            if link and title_el:
                title = title_el.get_text(strip=True)
                href = link.get("href", "")
                full_url = href if href.startswith("http") else urljoin(base_url, href)
                snippet_el = container.find("p")
                snippet = snippet_el.get_text(strip=True)[:300] if snippet_el else ""
                articles.append({"title": title, "url": full_url, "snippet": snippet})

        # Fallback: grab all heading links
        if not articles:
            for heading in soup.find_all(["h1", "h2", "h3"]):
                link = heading.find("a", href=True) or heading.find_parent("a", href=True)
                if link:
                    title = heading.get_text(strip=True)
                    href = link.get("href", "")
                    full_url = href if href.startswith("http") else urljoin(base_url, href)
                    articles.append({"title": title, "url": full_url})

        return articles

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)

        for protocol_name, blog_url in BLOG_SOURCES.items():
            try:
                resp = requests.get(blog_url, headers=HEADERS, timeout=30)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                # Choose extraction strategy based on URL
                if "mirror.xyz" in blog_url:
                    articles = self._extract_mirror_articles(soup, blog_url)
                elif "medium.com" in blog_url:
                    articles = self._extract_medium_articles(soup, blog_url)
                else:
                    articles = self._extract_generic_articles(soup, blog_url)

                for article in articles:
                    title = article.get("title", "")
                    snippet = article.get("snippet", "")
                    text = f"{title} {snippet}"

                    if not is_relevant(text):
                        continue

                    mention_data = {
                        "title": title,
                        "url": article.get("url", ""),
                        "text": snippet[:1000] if snippet else "",
                        "published": article.get("published", None),
                        "source": "blog",
                        "blog_url": blog_url,
                        "relevance_score": score_relevance(text),
                        "keywords_matched": extract_matches(text),
                    }
                    result.mentions.append(mention_data)

            except Exception as e:
                result.errors.append(f"Blog scan error for {blog_url}: {e}")
                logger.warning(f"Failed to scan blog {blog_url}: {e}")

            self._sleep(BLOG_DELAY)

        result.items_found = len(result.mentions)
        result.finished_at = datetime.utcnow()
        logger.info(f"Blog scan complete: {result.items_found} mentions found")
        return result
