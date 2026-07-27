# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

**Mission tooling touched:** `git apply --3way` (fix/2534 rebase), `uv run --extra test pytest` (the reliable
lane invocation — bare `uv run pytest` in a lane tests PRIMARY src, #2803), the pre-review gate + sync-daemon
env seams, `.github/workflows/ci-quality.yml` filter-groups.

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what happened, why it slowed you down. -->
- 2026-07-19 — This mission IS partly tooling-friction remediation: #2573 (gate reads as a hang), #2534 (gate
  alarms in consumer repos), #2812 (CI filter-guard skips the code it protects). Meta-note: the friction we
  hit running the loop is the product we're fixing.
