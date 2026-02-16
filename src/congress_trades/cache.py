from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from congress_trades.client import Trade

CACHE_DIR = Path.home() / ".local" / "share" / "congress-trades"
CACHE_FILE = CACHE_DIR / "seen.json"


def load_seen(cache_file: Path = CACHE_FILE) -> set[str]:
    if not cache_file.exists():
        return set()
    data = json.loads(cache_file.read_text())
    if not isinstance(data, list):
        return set()
    return set(data)


def save_seen(seen: set[str], cache_file: Path = CACHE_FILE) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(sorted(seen)))


def filter_new(trades: list[Trade], seen: set[str]) -> list[Trade]:
    return [t for t in trades if t.trade_id not in seen]


def clear_cache(cache_file: Path = CACHE_FILE) -> None:
    if cache_file.exists():
        cache_file.unlink()
