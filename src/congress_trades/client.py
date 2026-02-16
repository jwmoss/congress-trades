from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum

import httpx

BASE_URL = "https://financialmodelingprep.com/stable"


class Chamber(StrEnum):
    SENATE = "senate"
    HOUSE = "house"


@dataclass(frozen=True, slots=True)
class Trade:
    symbol: str
    disclosure_date: str
    transaction_date: str
    first_name: str
    last_name: str
    office: str
    district: str
    owner: str
    asset_description: str
    asset_type: str
    trade_type: str
    amount: str
    comment: str
    link: str
    chamber: str

    @property
    def politician(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def trade_id(self) -> str:
        parts = [self.politician, self.symbol, self.transaction_date, self.trade_type, self.amount]
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def is_purchase(self) -> bool:
        return "purchase" in self.trade_type.lower()


class FMPError(Exception):
    pass


def _parse_trade(raw: dict, chamber: str) -> Trade:
    return Trade(
        symbol=raw.get("symbol", ""),
        disclosure_date=raw.get("disclosureDate", ""),
        transaction_date=raw.get("transactionDate", ""),
        first_name=raw.get("firstName", ""),
        last_name=raw.get("lastName", ""),
        office=raw.get("office", ""),
        district=raw.get("district", ""),
        owner=raw.get("owner", ""),
        asset_description=raw.get("assetDescription", ""),
        asset_type=raw.get("assetType", ""),
        trade_type=raw.get("type", ""),
        amount=raw.get("amount", ""),
        comment=raw.get("comment", ""),
        link=raw.get("link", ""),
        chamber=chamber,
    )


def _fetch_trades(
    client: httpx.Client,
    endpoint: str,
    api_key: str,
    limit: int,
) -> list[dict]:
    response = client.get(
        f"{BASE_URL}/{endpoint}",
        params={"apikey": api_key, "page": 0, "limit": limit},
    )
    if response.status_code == 401:
        raise FMPError("Invalid API key. Check your FMP_API_KEY.")
    if response.status_code == 429:
        raise FMPError("Rate limited by FMP API. Wait and try again.")
    if response.status_code != 200:
        raise FMPError(f"FMP API returned status {response.status_code}: {response.text}")

    data = response.json()
    if isinstance(data, dict) and "Error Message" in data:
        raise FMPError(f"FMP API error: {data['Error Message']}")
    if not isinstance(data, list):
        raise FMPError(f"Unexpected response format: {type(data)}")
    return data


def fetch_senate_trades(api_key: str, limit: int = 100) -> list[Trade]:
    with httpx.Client(timeout=30) as client:
        raw = _fetch_trades(client, "senate-latest", api_key, limit)
    return [_parse_trade(r, "Senate") for r in raw]


def fetch_house_trades(api_key: str, limit: int = 100) -> list[Trade]:
    with httpx.Client(timeout=30) as client:
        raw = _fetch_trades(client, "house-latest", api_key, limit)
    return [_parse_trade(r, "House") for r in raw]


def fetch_all_trades(api_key: str, limit: int = 100) -> list[Trade]:
    with httpx.Client(timeout=30) as client:
        senate_raw = _fetch_trades(client, "senate-latest", api_key, limit)
        house_raw = _fetch_trades(client, "house-latest", api_key, limit)

    trades = [_parse_trade(r, "Senate") for r in senate_raw]
    trades.extend(_parse_trade(r, "House") for r in house_raw)
    return trades
