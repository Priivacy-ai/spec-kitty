# Issue matrix — retire-mission-read-path-shim-01KVZNDS

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2048 | Retire dead backcompat shim: specify_cli.mission_read_path (01KVJPEQ follow-up) | fixed | commit bff013d49 — shim module deleted (zero src/ callers), 7 test importers re-pointed to canonical `specify_cli.missions._read_path_resolver` (aliased private worker), both architectural allowlist entries dropped, `category_4_backcompat_shims` baseline 9→8 (live frozenset size = 8); gates green (42 passed, ruff exit 0) |
| #2049 | Broader allowlist burn-down audit across all categories (sister issue) | deferred-with-followup | spec.md §Out of Scope (line 116) — explicitly tracked by sister issue #2049, not in scope of this mission; this WP only reverses the 01KVJPEQ-induced category_4 bump |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
