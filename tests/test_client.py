from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from congress_trades.client import FMPError, _fetch_trades, _parse_trade


def _make_raw_trade(**overrides: str) -> dict:
    defaults = {
        "symbol": "AAPL",
        "disclosureDate": "2025-01-31",
        "transactionDate": "2025-01-15",
        "firstName": "Jane",
        "lastName": "Doe",
        "office": "Jane Doe",
        "district": "CA",
        "owner": "Self",
        "assetDescription": "Apple Inc",
        "assetType": "Stock",
        "type": "Purchase",
        "amount": "$1,001 - $15,000",
        "comment": "",
        "link": "https://example.com/filing",
    }
    defaults.update(overrides)
    return defaults


class TestParseTrade:
    def test_parses_all_fields(self) -> None:
        raw = _make_raw_trade()
        trade = _parse_trade(raw, "Senate")

        assert trade.symbol == "AAPL"
        assert trade.first_name == "Jane"
        assert trade.last_name == "Doe"
        assert trade.chamber == "Senate"
        assert trade.trade_type == "Purchase"
        assert trade.is_purchase is True

    def test_sale_is_not_purchase(self) -> None:
        raw = _make_raw_trade(type="Sale (Full)")
        trade = _parse_trade(raw, "House")

        assert trade.is_purchase is False
        assert trade.chamber == "House"

    def test_missing_fields_default_to_empty(self) -> None:
        trade = _parse_trade({}, "Senate")

        assert trade.symbol == ""
        assert trade.first_name == ""
        assert trade.trade_type == ""

    def test_trade_id_is_deterministic(self) -> None:
        raw = _make_raw_trade()
        trade1 = _parse_trade(raw, "Senate")
        trade2 = _parse_trade(raw, "Senate")

        assert trade1.trade_id == trade2.trade_id

    def test_trade_id_differs_for_different_trades(self) -> None:
        trade1 = _parse_trade(_make_raw_trade(symbol="AAPL"), "Senate")
        trade2 = _parse_trade(_make_raw_trade(symbol="MSFT"), "Senate")

        assert trade1.trade_id != trade2.trade_id

    def test_politician_full_name(self) -> None:
        trade = _parse_trade(_make_raw_trade(), "Senate")
        assert trade.politician == "Jane Doe"


class TestFetchTrades:
    def test_returns_list_on_success(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [_make_raw_trade()]

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        result = _fetch_trades(mock_client, "senate-latest", "fake-key", 100)
        assert len(result) == 1
        assert result[0]["symbol"] == "AAPL"

    def test_raises_on_401(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        with pytest.raises(FMPError, match="Invalid API key"):
            _fetch_trades(mock_client, "senate-latest", "bad-key", 100)

    def test_raises_on_429(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 429

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        with pytest.raises(FMPError, match="Rate limited"):
            _fetch_trades(mock_client, "senate-latest", "key", 100)

    def test_raises_on_error_message_in_body(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Error Message": "Limit reached"}

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        with pytest.raises(FMPError, match="Limit reached"):
            _fetch_trades(mock_client, "senate-latest", "key", 100)

    def test_raises_on_unexpected_format(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = "not a list"

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        with pytest.raises(FMPError, match="Unexpected response format"):
            _fetch_trades(mock_client, "senate-latest", "key", 100)

    def test_returns_empty_list(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        result = _fetch_trades(mock_client, "senate-latest", "key", 100)
        assert result == []
