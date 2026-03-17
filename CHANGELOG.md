# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-03-17

### Fixed
- Fixed `SHOW DATABASES` and all `SHOW` commands returning `Error calling tool execute_sql: {}` (issue #48) — removed special-case handling for `SHOW TABLES`; all result-set queries now use unified CSV output
- Fixed error messages being empty when `str(e)` was blank — now uses `e.msg` attribute from MySQL connector
- Fixed NULL values being rendered as the string `"None"` in query results — now rendered as empty strings

### Added
- `MYSQL_DATABASE` is now optional (issue #68, #81) — when omitted, the server operates in multi-database mode: `list_resources` returns all user databases, and you can switch with `USE <database>`
- SSE/HTTP transport support (issue #60) — set `MCP_TRANSPORT=sse` to run as an HTTP server; configurable via `MCP_SSE_HOST` (default `127.0.0.1`) and `MCP_SSE_PORT` (default `8000`); requires `pip install mysql_mcp_server[sse]`
- `MYSQL_CONNECT_TIMEOUT` environment variable (default `10` seconds) for controlling connection timeout
- `validate_identifier()` utility function for strict MySQL identifier validation (`^[a-zA-Z0-9_$]+$`)
- `read_resource` now supports `mysql://database/<name>` URIs to list tables within a specific database

### Security
- Replaced ad-hoc table name validation with `validate_identifier()` using a strict regex whitelist
- Upgraded `black` dev dependency to `>=24.0.0` to fix ReDoS vulnerability (CVE-2024-21503)
- Synchronized `mcp>=1.2.0` in `requirements.txt` to match `pyproject.toml`

### Changed
- `get_db_config()` now only requires `MYSQL_USER` and `MYSQL_PASSWORD`; `MYSQL_DATABASE` is optional
- `main()` refactored into `_run_stdio_server()` and `_run_sse_server()` for clarity
- `list_resources()` returns databases (filtered by system databases) when no default database is configured

## [0.2.3] - 2026-03-17

### Fixed
- Fixed empty password validation: `MYSQL_PASSWORD` can now be an empty string for passwordless MySQL (issue #43)
- Added `list_resource_templates` handler to prevent errors in Visual Studio Code (issue #77)
- Fixed SQL injection risk in `read_resource` by validating table names and using backtick-quoted identifiers (issue #84)
- Fixed README VSCode `mcp.json` example — missing closing brace (issue #42)

### Added
- SSL/TLS support via `MYSQL_SSL_MODE` env var (`DISABLED`, `REQUIRED`, `VERIFY_CA`, `VERIFY_IDENTITY`) (issue #71)
- Optional `MYSQL_SSL_CA` env var for specifying CA certificate path

### Security
- Dockerfile no longer exposes `MYSQL_PASSWORD` via `ENV`; secrets should be passed at `docker run` time
- Dockerfile now runs as a non-root user (`appuser`)
- Upgraded minimum `mcp` dependency to `>=1.2.0` to resolve known DoS and DNS-rebinding vulnerabilities

## [0.2.2] - 2025-04-18

### Fixed
- Fixed handling of SQL commands that return result sets, including `SHOW INDEX`, `SHOW CREATE TABLE`, and `DESCRIBE`
- Added improved error handling for result fetching operations
- Added additional debug output to aid in troubleshooting

## [0.2.1] - 2025-02-15

### Added
- Support for MYSQL_PORT configuration through environment variables
- Documentation for PORT configuration in README

### Changed
- Updated tests to use handler functions directly
- Refactored database configuration to runtime

## [0.2.0] - 2025-01-20

### Added
- Initial release with MCP server implementation
- Support for SQL queries through MCP interface
- Ability to list tables and read data
