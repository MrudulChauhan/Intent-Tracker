import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any


@dataclass
class ScanResult:
    scanner_name: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime = None
    items_found: int = 0
    projects: List[Dict[str, Any]] = field(default_factory=list)
    mentions: List[Dict[str, Any]] = field(default_factory=list)
    metrics: List[Dict[str, Any]] = field(default_factory=list)
    funding_rounds: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class BaseScanner:
    name: str = "base"

    def scan(self) -> ScanResult:
        raise NotImplementedError

    def _sleep(self, seconds: float):
        time.sleep(seconds)
