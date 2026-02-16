from __future__ import annotations

from io import StringIO

from rich.console import Console

from congress_trades.client import Trade
from congress_trades.display import display_trades


def _make_trade(symbol: str = "AAPL", trade_type: str = "Purchase") -> Trade:
    return Trade(
        symbol=symbol,
        disclosure_date="2025-01-31",
        transaction_date="2025-01-15",
        first_name="Jane",
        last_name="Doe",
        office="Jane Doe",
        district="CA",
        owner="Self",
        asset_description="Apple Inc",
        asset_type="Stock",
        trade_type=trade_type,
        amount="$1,001 - $15,000",
        comment="",
        link="https://example.com",
        chamber="Senate",
    )


def _capture_display(trades: list[Trade], total: int) -> str:
    buf = StringIO()
    import congress_trades.display as mod

    original = mod.console
    mod.console = Console(file=buf, no_color=True, width=200)
    try:
        display_trades(trades, total)
    finally:
        mod.console = original
    return buf.getvalue()


class TestDisplayTrades:
    def test_shows_no_trades_message(self) -> None:
        output = _capture_display([], 50)
        assert "No new trades found" in output

    def test_shows_trade_data(self) -> None:
        trade = _make_trade("AAPL", "Purchase")
        output = _capture_display([trade], 10)

        assert "Jane Doe" in output
        assert "AAPL" in output
        assert "Purchase" in output
        assert "1 new trades found" in output

    def test_shows_sale(self) -> None:
        trade = _make_trade("TSLA", "Sale (Full)")
        output = _capture_display([trade], 5)

        assert "TSLA" in output
        assert "Sale (Full)" in output

    def test_summary_counts(self) -> None:
        trades = [_make_trade("AAPL"), _make_trade("MSFT")]
        output = _capture_display(trades, 100)

        assert "2 new trades found (100 total checked)" in output
