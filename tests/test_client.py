from __future__ import annotations

import httpx
import pytest

from congress_trades.client import (
    SenateClient,
    SenateEFDError,
    Trade,
    _extract_ptr_link,
    _TradeTableParser,
)

SAMPLE_PTR_HTML = """
<table>
<thead><tr><th>#</th><th>Transaction Date</th><th>Owner</th><th>Ticker</th>
<th>Asset Name</th><th>Asset Type</th><th>Type</th><th>Amount</th><th>Comment</th></tr></thead>
<tbody>
<tr>
<td>1</td><td>01/15/2026</td><td>Self</td><td>AAPL</td>
<td>Apple Inc</td><td>Stock</td><td>Purchase</td><td>$1,001 - $15,000</td><td></td>
</tr>
<tr>
<td>2</td><td>01/16/2026</td><td>Spouse</td><td>MSFT</td>
<td>Microsoft Corp</td><td>Stock</td><td>Sale (Full)</td><td>$15,001 - $50,000</td><td>Planned</td>
</tr>
</tbody>
</table>
"""

SAMPLE_REPORT_JSON = {
    "recordsTotal": 2,
    "data": [
        [
            "John",
            "Boozman",
            "Boozman, John (Senator)",
            '<a href="/search/view/ptr/abc-123/">Periodic Transaction Report for 02/15/2026</a>',
            "02/15/2026",
        ],
        [
            "Lisa",
            "Murkowski",
            "Murkowski, Lisa (Senator)",
            '<a href="/search/view/ptr/def-456/">Periodic Transaction Report for 02/14/2026</a>',
            "02/14/2026",
        ],
    ],
}


def _mock_transport(responses: dict[str, httpx.Response]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        for pattern, response in responses.items():
            if pattern in str(request.url):
                return response
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _make_client_with_mock(responses: dict[str, httpx.Response]) -> httpx.Client:
    transport = _mock_transport(responses)
    client = httpx.Client(transport=transport)
    client.cookies.set("csrftoken", "fake-csrf-token")
    return client


class TestExtractPtrLink:
    def test_extracts_href_and_text(self) -> None:
        html = '<a href="/search/view/ptr/abc-123/">PTR for 02/15/2026</a>'
        href, text = _extract_ptr_link(html)
        assert href == "/search/view/ptr/abc-123/"
        assert text == "PTR for 02/15/2026"

    def test_empty_input(self) -> None:
        href, text = _extract_ptr_link("")
        assert href == ""
        assert text == ""


class TestTradeTableParser:
    def test_parses_rows(self) -> None:
        parser = _TradeTableParser()
        parser.feed(SAMPLE_PTR_HTML)
        assert len(parser.rows) == 2
        assert parser.rows[0][3] == "AAPL"
        assert parser.rows[1][3] == "MSFT"

    def test_empty_table(self) -> None:
        parser = _TradeTableParser()
        parser.feed("<table><tbody></tbody></table>")
        assert parser.rows == []

    def test_no_tbody(self) -> None:
        parser = _TradeTableParser()
        parser.feed("<table><tr><td>data</td></tr></table>")
        assert parser.rows == []


class TestTrade:
    def test_trade_id_deterministic(self) -> None:
        t1 = Trade(
            politician="Doe, Jane",
            symbol="AAPL",
            transaction_date="01/15/2026",
            filing_date="02/15/2026",
            owner="Self",
            asset_description="Apple Inc",
            asset_type="Stock",
            trade_type="Purchase",
            amount="$1,001 - $15,000",
            comment="",
            link="https://example.com",
        )
        t2 = Trade(
            politician="Doe, Jane",
            symbol="AAPL",
            transaction_date="01/15/2026",
            filing_date="02/15/2026",
            owner="Self",
            asset_description="Apple Inc",
            asset_type="Stock",
            trade_type="Purchase",
            amount="$1,001 - $15,000",
            comment="",
            link="https://example.com",
        )
        assert t1.trade_id == t2.trade_id

    def test_trade_id_differs_for_different_symbols(self) -> None:
        kwargs = {
            "politician": "Doe, Jane",
            "transaction_date": "01/15/2026",
            "filing_date": "02/15/2026",
            "owner": "Self",
            "asset_description": "Stock",
            "asset_type": "Stock",
            "trade_type": "Purchase",
            "amount": "$1,001 - $15,000",
            "comment": "",
            "link": "https://example.com",
        }
        t1 = Trade(symbol="AAPL", **kwargs)
        t2 = Trade(symbol="MSFT", **kwargs)
        assert t1.trade_id != t2.trade_id

    def test_is_purchase(self) -> None:
        trade = Trade(
            politician="X",
            symbol="X",
            transaction_date="",
            filing_date="",
            owner="",
            asset_description="",
            asset_type="",
            trade_type="Purchase",
            amount="",
            comment="",
            link="",
        )
        assert trade.is_purchase is True

    def test_sale_is_not_purchase(self) -> None:
        trade = Trade(
            politician="X",
            symbol="X",
            transaction_date="",
            filing_date="",
            owner="",
            asset_description="",
            asset_type="",
            trade_type="Sale (Full)",
            amount="",
            comment="",
            link="",
        )
        assert trade.is_purchase is False


class TestSenateClient:
    def test_accept_agreement_failure(self) -> None:
        transport = _mock_transport({
            "/search/home/": httpx.Response(500),
        })
        client = httpx.Client(transport=transport)
        with pytest.raises(SenateEFDError, match="Failed to load"):
            SenateClient(client=client)

    def test_missing_csrf_token(self) -> None:
        transport = _mock_transport({
            "/search/home/": httpx.Response(200),
        })
        client = httpx.Client(transport=transport)
        with pytest.raises(SenateEFDError, match="No CSRF token"):
            SenateClient(client=client)

    def test_fetch_reports(self) -> None:
        mock_client = _make_client_with_mock({
            "/search/home/": httpx.Response(200),
            "/search/report/data/": httpx.Response(200, json=SAMPLE_REPORT_JSON),
        })
        senate = SenateClient(client=mock_client)
        reports = senate.fetch_reports(limit=10)

        assert len(reports) == 2
        assert reports[0]["politician"] == "Boozman, John (Senator)"
        assert reports[0]["link"] == "/search/view/ptr/abc-123/"
        assert reports[1]["filing_date"] == "02/14/2026"

    def test_fetch_reports_error(self) -> None:
        mock_client = _make_client_with_mock({
            "/search/home/": httpx.Response(200),
            "/search/report/data/": httpx.Response(500),
        })
        senate = SenateClient(client=mock_client)
        with pytest.raises(SenateEFDError, match="Failed to fetch report data"):
            senate.fetch_reports()

    def test_fetch_trades_from_report(self) -> None:
        mock_client = _make_client_with_mock({
            "/search/home/": httpx.Response(200),
            "/search/view/ptr/abc-123/": httpx.Response(200, text=SAMPLE_PTR_HTML),
        })
        senate = SenateClient(client=mock_client)
        report = {
            "politician": "Boozman, John (Senator)",
            "link": "/search/view/ptr/abc-123/",
            "filing_date": "02/15/2026",
        }
        trades = senate.fetch_trades_from_report(report)

        assert len(trades) == 2
        assert trades[0].symbol == "AAPL"
        assert trades[0].politician == "Boozman, John (Senator)"
        assert trades[0].trade_type == "Purchase"
        assert trades[1].symbol == "MSFT"
        assert trades[1].trade_type == "Sale (Full)"

    def test_fetch_trades_from_report_empty_link(self) -> None:
        mock_client = _make_client_with_mock({
            "/search/home/": httpx.Response(200),
        })
        senate = SenateClient(client=mock_client)
        report = {"politician": "X", "link": "", "filing_date": ""}
        assert senate.fetch_trades_from_report(report) == []

    def test_fetch_trades_from_report_404(self) -> None:
        mock_client = _make_client_with_mock({
            "/search/home/": httpx.Response(200),
        })
        senate = SenateClient(client=mock_client)
        report = {
            "politician": "X",
            "link": "/search/view/ptr/nonexistent/",
            "filing_date": "",
        }
        assert senate.fetch_trades_from_report(report) == []
