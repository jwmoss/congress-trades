from __future__ import annotations

import os
import sys

import click
from dotenv import load_dotenv
from rich.console import Console

from congress_trades.cache import clear_cache, filter_new, load_seen, save_seen
from congress_trades.client import (
    FMPError,
    fetch_all_trades,
    fetch_house_trades,
    fetch_senate_trades,
)
from congress_trades.display import display_trades

console = Console()


def _get_api_key() -> str:
    load_dotenv()
    key = os.environ.get("FMP_API_KEY", "")
    if not key:
        console.print("[red]FMP_API_KEY not set. Export it or add to .env file.[/red]")
        sys.exit(1)
    return key


@click.command()
@click.option(
    "--chamber",
    "-c",
    type=click.Choice(["all", "senate", "house"], case_sensitive=False),
    default="all",
    help="Which chamber to fetch trades from.",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=100,
    help="Number of trades to fetch per chamber.",
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
def main(chamber: str, limit: int, show_all: bool, reset: bool) -> None:
    """Fetch and display recent congressional stock trades."""
    if reset:
        clear_cache()
        console.print("[green]Cache cleared.[/green]")
        return

    api_key = _get_api_key()

    try:
        match chamber:
            case "senate":
                trades = fetch_senate_trades(api_key, limit)
            case "house":
                trades = fetch_house_trades(api_key, limit)
            case _:
                trades = fetch_all_trades(api_key, limit)
    except FMPError as e:
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
