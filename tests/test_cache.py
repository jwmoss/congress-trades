from __future__ import annotations

import json
from typing import TYPE_CHECKING

from congress_trades.cache import clear_cache, filter_new, load_seen, save_seen
from congress_trades.client import Trade

if TYPE_CHECKING:
    from pathlib import Path


def _make_trade(symbol: str = "AAPL", trade_type: str = "Purchase") -> Trade:
    return Trade(
        politician="Doe, Jane (Senator)",
        symbol=symbol,
        transaction_date="01/15/2026",
        filing_date="02/15/2026",
        owner="Self",
        asset_description="Apple Inc",
        asset_type="Stock",
        trade_type=trade_type,
        amount="$1,001 - $15,000",
        comment="",
        link="https://example.com",
    )


class TestLoadSeen:
    def test_returns_empty_when_no_file(self, tmp_path: Path) -> None:
        result = load_seen(tmp_path / "nonexistent.json")
        assert result == set()

    def test_loads_existing_cache(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "seen.json"
        cache_file.write_text(json.dumps(["abc123", "def456"]))

        result = load_seen(cache_file)
        assert result == {"abc123", "def456"}

    def test_handles_corrupted_cache(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "seen.json"
        cache_file.write_text(json.dumps({"not": "a list"}))

        result = load_seen(cache_file)
        assert result == set()


class TestSaveSeen:
    def test_creates_file_and_dirs(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "sub" / "dir" / "seen.json"
        save_seen({"abc123"}, cache_file)

        assert cache_file.exists()
        data = json.loads(cache_file.read_text())
        assert data == ["abc123"]

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "seen.json"
        save_seen({"old"}, cache_file)
        save_seen({"new1", "new2"}, cache_file)

        data = json.loads(cache_file.read_text())
        assert set(data) == {"new1", "new2"}


class TestFilterNew:
    def test_filters_seen_trades(self) -> None:
        t1 = _make_trade("AAPL")
        t2 = _make_trade("MSFT")

        seen = {t1.trade_id}
        result = filter_new([t1, t2], seen)

        assert len(result) == 1
        assert result[0].symbol == "MSFT"

    def test_returns_all_when_none_seen(self) -> None:
        t1 = _make_trade("AAPL")
        t2 = _make_trade("MSFT")

        result = filter_new([t1, t2], set())
        assert len(result) == 2

    def test_returns_empty_when_all_seen(self) -> None:
        t1 = _make_trade("AAPL")
        seen = {t1.trade_id}

        result = filter_new([t1], seen)
        assert result == []


class TestClearCache:
    def test_removes_cache_file(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "seen.json"
        cache_file.write_text("[]")

        clear_cache(cache_file)
        assert not cache_file.exists()

    def test_no_error_when_no_file(self, tmp_path: Path) -> None:
        clear_cache(tmp_path / "nonexistent.json")
