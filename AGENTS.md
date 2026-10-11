# Agent instructions

Use `make check` for static checks and builds.
Use `make test` for real Senate API end-to-end checks.
Keep only live end-to-end tests and static checks.
Do not add unit tests, mocks, or fake servers.
Keep data on stdout and errors on stderr.
Preserve the cache path and the existing default display.
`--dry-run` permits reads and blocks local cache changes.
