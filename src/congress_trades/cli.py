from __future__ import annotations

import sys

import click
from rich.console import Console

from congress_trades.cache import clear_cache, filter_new, load_seen, save_seen
from congress_trades.client import SenateClient, SenateEFDError
from congress_trades.display import display_trades

console = Console()


@click.command()
@click.option(
    "--limit",
    "-l",
    type=int,
    default=10,
    help="Number of PTR filings to fetch.",
)
@click.option(
    "--all",
    "-a",
    "show_all",
    is_flag=True,
    help="Show all trades, not just new ones.",
)
@click.option(
    "--reset",
    is_flag=True,
    help="Clear the seen trades cache.",
)
def main(limit: int, show_all: bool, reset: bool) -> None:
    """Fetch and display recent Senate stock trades."""
    if reset:
        clear_cache()
        console.print("[green]Cache cleared.[/green]")
        return

    try:
        with SenateClient() as client:
            trades = client.fetch_trades(limit)
    except SenateEFDError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    total_checked = len(trades)

    if show_all:
        display_trades(trades, total_checked)
    else:
        seen = load_seen()
        new_trades = filter_new(trades, seen)
        display_trades(new_trades, total_checked)
        all_ids = seen | {t.trade_id for t in trades}
        save_seen(all_ids)
