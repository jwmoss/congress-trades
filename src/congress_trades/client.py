from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

BASE_URL = "https://efdsearch.senate.gov"
SEARCH_HOME = f"{BASE_URL}/search/home/"
REPORT_DATA = f"{BASE_URL}/search/report/data/"


class SenateEFDError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Trade:
    politician: str
    symbol: str
    transaction_date: str
    filing_date: str
    owner: str
    asset_description: str
    asset_type: str
    trade_type: str
    amount: str
    comment: str
    link: str

    @property
    def trade_id(self) -> str:
        parts = [self.politician, self.symbol, self.transaction_date, self.trade_type, self.amount]
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def is_purchase(self) -> bool:
        return "purchase" in self.trade_type.lower()


class _TradeTableParser(HTMLParser):
    """Parses the trade table from a Senate eFD PTR detail page."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._in_tbody = False
        self._in_row = False
        self._in_cell = False
        self._current_row: list[str] = []
        self._current_cell = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self._in_row = True
            self._current_row = []
        elif tag == "td" and self._in_row:
            self._in_cell = True
            self._current_cell = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "tbody":
            self._in_tbody = False
        elif tag == "tr" and self._in_row:
            self._in_row = False
            if self._current_row:
                self.rows.append(self._current_row)
        elif tag == "td" and self._in_cell:
            self._in_cell = False
            self._current_row.append(self._current_cell.strip())

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell += data


def _extract_ptr_link(html_snippet: str) -> tuple[str, str]:
    """Extract URL and filing date from the PTR listing HTML snippet.

    The snippet looks like:
    <a href="/search/view/ptr/UUID/">Periodic Transaction Report for MM/DD/YYYY</a>
    """

    class _LinkParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.href = ""
            self.text = ""
            self._in_a = False

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag == "a":
                self._in_a = True
                for name, value in attrs:
                    if name == "href" and value:
                        self.href = value

        def handle_data(self, data: str) -> None:
            if self._in_a:
                self.text += data

        def handle_endtag(self, tag: str) -> None:
            if tag == "a":
                self._in_a = False

    parser = _LinkParser()
    parser.feed(html_snippet)
    return parser.href, parser.text


class SenateClient:
    """Client for the Senate Electronic Financial Disclosure system."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        if client is not None:
            self._client = client
            self._owned = False
        else:
            self._client = httpx.Client(timeout=30, follow_redirects=True)
            self._owned = True
        self._accept_agreement()

    def _accept_agreement(self) -> None:
        response = self._client.get(SEARCH_HOME)
        if response.status_code != 200:
            raise SenateEFDError(
                f"Failed to load eFD search page (status {response.status_code})"
            )
        csrf_token = self._client.cookies.get("csrftoken", "")
        if not csrf_token:
            raise SenateEFDError("No CSRF token received from eFD search page")

        response = self._client.post(
            SEARCH_HOME,
            data={"prohibition_agreement": "1", "csrfmiddlewaretoken": csrf_token},
            headers={"Referer": SEARCH_HOME},
        )
        if response.status_code != 200:
            raise SenateEFDError(
                f"Failed to accept eFD agreement (status {response.status_code})"
            )

    def fetch_reports(self, limit: int = 10) -> list[dict]:
        """Fetch recent PTR report listings from the eFD search."""
        csrf_token = self._client.cookies.get("csrftoken", "")
        response = self._client.post(
            REPORT_DATA,
            data={
                "start": "0",
                "length": str(limit),
                "report_types": "[11]",
                "csrfmiddlewaretoken": csrf_token,
            },
            headers={"Referer": SEARCH_HOME},
        )
        if response.status_code == 503:
            raise SenateEFDError(
                "Senate eFD site is under maintenance. Try again later."
            )
        if response.status_code != 200:
            raise SenateEFDError(
                f"Failed to fetch report data (status {response.status_code})"
            )

        body = response.json()
        if not isinstance(body, dict) or "data" not in body:
            raise SenateEFDError(f"Unexpected report data format: {type(body)}")

        reports = []
        for row in body["data"]:
            if len(row) < 5:
                continue
            first_name, last_name, full_name, ptr_html, filing_date = row[:5]
            href, _link_text = _extract_ptr_link(ptr_html)
            reports.append({
                "first_name": first_name,
                "last_name": last_name,
                "politician": full_name,
                "link": href,
                "filing_date": filing_date,
            })
        return reports

    def fetch_trades_from_report(self, report: dict) -> list[Trade]:
        """Fetch individual trades from a PTR detail page."""
        link = report["link"]
        if not link:
            return []

        url = f"{BASE_URL}{link}" if link.startswith("/") else link
        response = self._client.get(url)
        if response.status_code != 200:
            return []

        parser = _TradeTableParser()
        parser.feed(response.text)

        politician = report.get("politician", "")
        filing_date = report.get("filing_date", "")

        trades = []
        for row in parser.rows:
            if len(row) < 9:
                continue
            trades.append(Trade(
                politician=politician,
                transaction_date=row[1],
                owner=row[2],
                symbol=row[3],
                asset_description=row[4],
                asset_type=row[5],
                trade_type=row[6],
                amount=row[7],
                comment=row[8] if len(row) > 8 else "",
                filing_date=filing_date,
                link=url,
            ))
        return trades

    def fetch_trades(self, limit: int = 10) -> list[Trade]:
        """Fetch trades from the most recent PTR filings."""
        reports = self.fetch_reports(limit)
        all_trades: list[Trade] = []
        for i, report in enumerate(reports):
            all_trades.extend(self.fetch_trades_from_report(report))
            if i < len(reports) - 1:
                time.sleep(1)
        return all_trades

    def close(self) -> None:
        if self._owned:
            self._client.close()

    def __enter__(self) -> SenateClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
