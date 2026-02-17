from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from congress_trades.client import Trade

console = Console()


def display_trades(trades: list[Trade], total_checked: int) -> None:
    if not trades:
        console.print("[dim]No new trades found.[/dim]")
        return

    table = Table(title="Senate Stock Trades", show_lines=False, expand=True)
    table.add_column("Politician", style="bold", no_wrap=True)
    table.add_column("Ticker", style="cyan", no_wrap=True)
    table.add_column("Type", no_wrap=True)
    table.add_column("Amount", no_wrap=True)
    table.add_column("Tx Date", no_wrap=True)
    table.add_column("Filed", no_wrap=True)

    for trade in trades:
        type_style = "green" if trade.is_purchase else "red"
        table.add_row(
            trade.politician,
            trade.symbol or trade.asset_description[:20],
            f"[{type_style}]{trade.trade_type}[/{type_style}]",
            trade.amount,
            trade.transaction_date,
            trade.filing_date,
        )

    console.print(table)
    console.print(
        f"\n[bold]{len(trades)}[/bold] new trades found ({total_checked} total checked)"
    )
