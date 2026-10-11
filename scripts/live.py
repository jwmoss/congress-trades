"""Check the installed CLI against the real Senate disclosure service."""

import json
import subprocess

subprocess.run(["congress-trades", "--version"], check=True, capture_output=True, timeout=10)
invalid = subprocess.run(
    ["congress-trades", "--timeout", "0"], capture_output=True, check=False, timeout=10
)
if invalid.returncode != 2 or invalid.stdout:
    raise SystemExit("invalid timeout must fail with exit 2 and empty stdout")
blocked = subprocess.run(
    ["congress-trades", "--dry-run", "--reset"],
    capture_output=True,
    check=False,
    timeout=10,
)
if blocked.returncode != 1 or blocked.stdout:
    raise SystemExit("dry-run must refuse cache reset")
result = subprocess.run(
    ["congress-trades", "--all", "--limit", "3", "--dry-run", "--json"],
    capture_output=True,
    text=True,
    check=False,
    timeout=180,
)
if result.returncode:
    raise SystemExit(
        f"live Senate CLI failed with exit {result.returncode}: {result.stderr.strip()}"
    )
trades = json.loads(result.stdout)
if not isinstance(trades, list) or not trades:
    raise SystemExit("live Senate response has no trades to validate")
if any(not trade.get("politician") or not trade.get("filing_date") for trade in trades):
    raise SystemExit("live Senate response omits required trade fields")
print(f"PASS: real Senate CLI returns {len(trades)} trades with required fields")
