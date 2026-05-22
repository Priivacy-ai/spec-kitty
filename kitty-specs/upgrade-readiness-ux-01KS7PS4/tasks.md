# Tasks: Upgrade Readiness UX

| WP | Title | Dependencies | Scope |
|---|---|---|---|
| WP01 | NagCacheRecord schema extension | — | Add 5 optional fields; backward-compat reader |
| WP02 | Installer safety helper | — | `is_safe_for_auto_upgrade()` colocated in install_method.py |
| WP03 | upgrade_ux module (cadence + state machine + env resolution) | WP01, WP02 | Pure logic; no I/O; injectable clock |
| WP04 | Coordinator wiring + suppression integration | WP03 | Route through `_evaluate_uncached` behind hosted gate |
| WP05 | Test matrix | WP01-WP04 | Unit + integration + suppression matrix |

All WPs are single-lane (no parallelization gain on a 5-WP chain with tight deps).
