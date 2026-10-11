# Congress Trades

Read recent Senate stock trades from the public Senate disclosure site.

```bash
uv run congress-trades --help
uv run congress-trades --version
uv run congress-trades --all --limit 3 --json
uv run congress-trades --dry-run --plain
```

Use `--json` for machine output or `--plain` for tab-separated fields.
Errors go to stderr. `--timeout` sets the HTTP timeout in seconds.
`--quiet` suppresses human output; `--no-color` disables color.
`--dry-run` permits remote reads and prevents local cache writes or resets.
The Senate service uses POST requests for disclosure searches and its access agreement.

## Development

Run `make check` for lint, format, compile, and package checks.
Run `make test` for real CLI reads against the Senate service.
The live test changes no cache files and prints no trade records.
An unavailable service fails the test; it does not count as a pass.
There are no unit tests, mocks, or fake-server tests.
