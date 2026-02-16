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

    table = Table(title="Congressional Stock Trades", show_lines=False)
    table.add_column("Politician", style="bold")
    table.add_column("Chamber")
    table.add_column("District")
    table.add_column("Ticker", style="cyan")
    table.add_column("Type")
    table.add_column("Amount")
    table.add_column("Transaction Date")
    table.add_column("Disclosed")

    for trade in trades:
        type_style = "green" if trade.is_purchase else "red"
        table.add_row(
            trade.politician,
            trade.chamber,
            trade.district,
            trade.symbol or trade.asset_description[:20],
            f"[{type_style}]{trade.trade_type}[/{type_style}]",
            trade.amount,
            trade.transaction_date,
            trade.disclosure_date,
        )

    console.print(table)
    console.print(f"\n[bold]{len(trades)}[/bold] new trades found ({total_checked} total checked)")
