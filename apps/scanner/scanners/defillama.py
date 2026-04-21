import logging
from datetime import datetime

import requests

from config.sources import DEFILLAMA_PROTOCOLS
from processing.matcher import is_relevant, extract_matches
from scanners.base import BaseScanner, ScanResult

logger = logging.getLogger(__name__)

DEFILLAMA_PROTOCOLS_URL = "https://api.llama.fi/protocols"


class DefiLlamaScanner(BaseScanner):
    name = "defillama"

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)

        try:
            resp = requests.get(DEFILLAMA_PROTOCOLS_URL, timeout=30)
            resp.raise_for_status()
            protocols = resp.json()
        except Exception as e:
            result.errors.append(f"Failed to fetch DefiLlama protocols: {e}")
            result.finished_at = datetime.utcnow()
            return result

        # Build a set of directly-configured protocol slugs (lowercase)
        configured = {p.lower() for p in DEFILLAMA_PROTOCOLS}

        for proto in protocols:
            name = proto.get("name", "")
            slug = proto.get("slug", "")
            description = proto.get("description", "")
            category = proto.get("category", "")

            # Check if this protocol is directly configured or matches keywords
            text = f"{name} {description} {category}"
            directly_configured = slug.lower() in configured or name.lower() in configured

            if not directly_configured:
                # For discovered protocols, require a higher threshold (0.5)
                # so only primary term or exact protocol name matches get through
                if not is_relevant(text, threshold=0.5):
                    continue

            from processing.matcher import score_relevance
            project_data = {
                "name": name,
                "description": description,
                "chains": proto.get("chains", []),
                "tvl": proto.get("tvl", 0),
                "category": category,
                "website": proto.get("url", ""),
                "slug": slug,
                "defillama_slug": slug,
                "source": "defillama",
                "relevance_score": score_relevance(text),
                "keywords_matched": extract_matches(text),
            }
            result.projects.append(project_data)

            metric_data = {
                "project_name": name,
                "source": "defillama",
                "tvl": proto.get("tvl", 0),
                "tvl_change_1d": proto.get("change_1d", None),
                "tvl_change_7d": proto.get("change_7d", None),
                "category": category,
                "chains": proto.get("chains", []),
                "collected_at": datetime.utcnow().isoformat(),
            }
            result.metrics.append(metric_data)

        result.items_found = len(result.projects)
        result.finished_at = datetime.utcnow()
        logger.info(f"DefiLlama scan complete: {result.items_found} protocols found")
        return result
