import logging
import re
from datetime import datetime, timedelta

import requests

from core.config import GITHUB_TOKEN, GITHUB_DELAY
from config.sources import GITHUB_REPOS
from processing.matcher import is_relevant, extract_matches
from scanners.base import BaseScanner, ScanResult

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"

DISCOVERY_QUERIES = [
    "intent+defi",
    "solver+blockchain",
]


class GitHubScanner(BaseScanner):
    name = "github"

    def _headers(self):
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        return headers

    def _get_last_page(self, response):
        """Extract the last page number from the Link header."""
        link_header = response.headers.get("Link", "")
        if not link_header:
            # If no Link header, count the items in the response
            return 1
        match = re.search(r'page=(\d+)>; rel="last"', link_header)
        if match:
            return int(match.group(1))
        return 1

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Scan configured repos
        for repo_path in GITHUB_REPOS:
            try:
                # Fetch repo info
                resp = requests.get(
                    f"{GITHUB_API}/repos/{repo_path}",
                    headers=self._headers(),
                    timeout=30,
                )
                resp.raise_for_status()
                repo = resp.json()

                metric_data = {
                    "project_name": repo.get("full_name", repo_path),
                    "source": "github",
                    "description": repo.get("description", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "open_issues": repo.get("open_issues_count", 0),
                    "last_push": repo.get("pushed_at", ""),
                    "language": repo.get("language", ""),
                    "collected_at": datetime.utcnow().isoformat(),
                }

                self._sleep(GITHUB_DELAY)

                # Fetch contributors count via per_page=1 and Link header
                try:
                    contrib_resp = requests.get(
                        f"{GITHUB_API}/repos/{repo_path}/contributors",
                        headers=self._headers(),
                        params={"per_page": 1, "anon": "true"},
                        timeout=30,
                    )
                    contrib_resp.raise_for_status()
                    metric_data["contributors_count"] = self._get_last_page(contrib_resp)
                except Exception as e:
                    metric_data["contributors_count"] = None
                    logger.debug(f"Could not fetch contributors for {repo_path}: {e}")

                self._sleep(GITHUB_DELAY)

                # Fetch recent commits count (last 30 days)
                try:
                    commits_resp = requests.get(
                        f"{GITHUB_API}/repos/{repo_path}/commits",
                        headers=self._headers(),
                        params={"since": thirty_days_ago, "per_page": 1},
                        timeout=30,
                    )
                    commits_resp.raise_for_status()
                    metric_data["recent_commits_30d"] = self._get_last_page(commits_resp)
                except Exception as e:
                    metric_data["recent_commits_30d"] = None
                    logger.debug(f"Could not fetch commits for {repo_path}: {e}")

                result.metrics.append(metric_data)

            except Exception as e:
                result.errors.append(f"GitHub repo error for {repo_path}: {e}")
                logger.warning(f"Failed to fetch GitHub repo {repo_path}: {e}")

            self._sleep(GITHUB_DELAY)

        # Discover new repos via search
        for query in DISCOVERY_QUERIES:
            try:
                resp = requests.get(
                    f"{GITHUB_API}/search/repositories",
                    headers=self._headers(),
                    params={"q": query, "sort": "updated", "per_page": 30},
                    timeout=30,
                )
                resp.raise_for_status()
                search_data = resp.json()

                existing_repos = {m.get("project_name") for m in result.metrics}

                for item in search_data.get("items", []):
                    full_name = item.get("full_name", "")
                    description = item.get("description", "") or ""
                    text = f"{full_name} {description}"

                    if full_name in existing_repos:
                        continue

                    if not is_relevant(text):
                        continue

                    metric_data = {
                        "project_name": full_name,
                        "source": "github_search",
                        "description": description,
                        "stars": item.get("stargazers_count", 0),
                        "forks": item.get("forks_count", 0),
                        "open_issues": item.get("open_issues_count", 0),
                        "last_push": item.get("pushed_at", ""),
                        "language": item.get("language", ""),
                        "discovered_via_query": query,
                        "keywords_matched": extract_matches(text),
                        "collected_at": datetime.utcnow().isoformat(),
                    }
                    result.metrics.append(metric_data)

            except Exception as e:
                result.errors.append(f"GitHub search error for '{query}': {e}")
                logger.warning(f"GitHub search failed for '{query}': {e}")

            self._sleep(GITHUB_DELAY)

        result.items_found = len(result.metrics)
        result.finished_at = datetime.utcnow()
        logger.info(f"GitHub scan complete: {result.items_found} repos tracked")
        return result
