# Tasks — Canonical Producer Refactor

Six work packages. WP01 unblocks the rest by widening
`_validate_lifecycle_payload`. WP02 / WP03 are the core refactor and run
sequentially because they touch overlapping CI surfaces. WP04 is a
small fix. WP05 (conformance tests) lands on top of WP01-WP03. WP06
(lint burndown) lands last.

| WP   | Title                                                    | Depends |
|------|----------------------------------------------------------|---------|
| WP01 | Strict `_validate_lifecycle_payload` for known types     | (none)  |
| WP02 | Lifecycle producers via canonical pydantic models        | WP01    |
| WP03 | Sync emitter producers via canonical pydantic models     | WP01    |
| WP04 | `reset_handlers()` test-order pollution fix              | (none)  |
| WP05 | Producer conformance tests                               | WP02, WP03 |
| WP06 | Lint baseline burndown + remaining-entry justification   | WP02, WP03, WP04, WP05 |
