import logging
from datetime import datetime

from config.keywords import PRIMARY_TERMS, PROTOCOL_NAMES
from core.config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from config.sources import SUBREDDITS
from processing.matcher import score_relevance, extract_matches
from scanners.base import BaseScanner, ScanResult

logger = logging.getLogger(__name__)

RELEVANCE_THRESHOLD = 0.3


class RedditScanner(BaseScanner):
    name = "reddit"

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)

        if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
            msg = "Reddit credentials not set — skipping Reddit scan"
            logger.warning(msg)
            result.errors.append(msg)
            result.finished_at = datetime.utcnow()
            return result

        try:
            import praw
        except ImportError:
            msg = "praw not installed — skipping Reddit scan"
            logger.warning(msg)
            result.errors.append(msg)
            result.finished_at = datetime.utcnow()
            return result

        try:
            reddit = praw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent=REDDIT_USER_AGENT or "intent-tracker/1.0",
            )
        except Exception as e:
            result.errors.append(f"Failed to initialize Reddit client: {e}")
            result.finished_at = datetime.utcnow()
            return result

        search_terms = list(PRIMARY_TERMS) + list(PROTOCOL_NAMES)
        seen_post_ids = set()

        for subreddit_name in SUBREDDITS:
            try:
                subreddit = reddit.subreddit(subreddit_name)
            except Exception as e:
                result.errors.append(f"Failed to access r/{subreddit_name}: {e}")
                continue

            for term in search_terms:
                try:
                    posts = subreddit.search(term, sort="new", time_filter="week", limit=25)
                    for post in posts:
                        if post.id in seen_post_ids:
                            continue
                        seen_post_ids.add(post.id)

                        text = f"{post.title} {post.selftext or ''}"
                        relevance = score_relevance(text)

                        if relevance < RELEVANCE_THRESHOLD:
                            continue

                        mention_data = {
                            "title": post.title,
                            "url": f"https://reddit.com{post.permalink}",
                            "text": (post.selftext or "")[:1000],
                            "author": str(post.author) if post.author else "[deleted]",
                            "score": post.score,
                            "created_utc": datetime.utcfromtimestamp(post.created_utc).isoformat(),
                            "subreddit": subreddit_name,
                            "relevance_score": relevance,
                            "source": "reddit",
                            "search_term": term,
                            "keywords_matched": extract_matches(text),
                        }
                        result.mentions.append(mention_data)

                except Exception as e:
                    result.errors.append(
                        f"Reddit search error in r/{subreddit_name} for '{term}': {e}"
                    )
                    logger.warning(f"Reddit search failed in r/{subreddit_name} for '{term}': {e}")

        result.items_found = len(result.mentions)
        result.finished_at = datetime.utcnow()
        logger.info(f"Reddit scan complete: {result.items_found} mentions found")
        return result
