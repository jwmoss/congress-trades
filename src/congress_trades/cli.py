from __future__ import annotations

import json
from dataclasses import asdict

import click
import httpx
from rich.console import Console

from congress_trades.cache import clear_cache, filter_new, load_seen, save_seen
from congress_trades.client import SenateClient, SenateEFDError
from congress_trades.display import display_trades

console = Console()


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="congress-trades")
@click.option("--json", "as_json", is_flag=True, help="Write JSON to stdout.")
@click.option("--plain", is_flag=True, help="Write tab-separated trade fields.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress human output.")
@click.option("--no-color", is_flag=True, help="Disable color.")
@click.option("--dry-run", is_flag=True, help="Read trades without changing the local cache.")
@click.option(
    "--timeout",
    type=click.FloatRange(min=0, min_open=True),
    default=30.0,
    help="HTTP timeout in seconds.",
)
@click.option(
    "--limit",
    "-l",
    type=click.IntRange(min=1),
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
def main(
    limit: int,
    show_all: bool,
    reset: bool,
    as_json: bool,
    plain: bool,
    quiet: bool,
    no_color: bool,
    dry_run: bool,
    timeout: float,
) -> None:
    """Fetch and display recent Senate stock trades."""
    if as_json and plain:
        raise click.UsageError("Choose only one of --json or --plain.")
    if no_color:
        console.no_color = True
    if reset:
        if dry_run:
            raise click.ClickException("dry-run: refusing to clear the local cache")
        clear_cache()
        if as_json:
            click.echo(json.dumps({"cleared": True}))
        elif not quiet:
            console.print("[green]Cache cleared.[/green]")
        return

    try:
        with SenateClient(timeout=timeout) as client:
            trades = client.fetch_trades(limit)
    except (SenateEFDError, httpx.HTTPError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    total_checked = len(trades)

    if not show_all:
        seen = load_seen()
        all_ids = seen | {t.trade_id for t in trades}
        trades = filter_new(trades, seen)
        if not dry_run:
            save_seen(all_ids)

    if as_json:
        click.echo(json.dumps([asdict(trade) for trade in trades]))
    elif not quiet and plain:
        for trade in trades:
            fields = (
                trade.politician,
                trade.symbol,
                trade.trade_type,
                trade.amount,
                trade.transaction_date,
                trade.filing_date,
            )
            click.echo("\t".join(value.replace("\t", " ").replace("\n", " ") for value in fields))
    elif not quiet:
        display_trades(trades, total_checked, no_color=no_color)
