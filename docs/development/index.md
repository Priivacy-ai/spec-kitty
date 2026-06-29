---
title: Development
description: Landing page for the retired docs/development working set, mapping where each former page moved under the durable operations, guides, and configuration sections.
doc_status: active
updated: '2026-06-27'
related:
- docs/configuration/index.md
- docs/guides/index.md
- docs/index.md
- docs/operations/index.md
- docs/plans/index.md
---
# Development

The former `docs/development/` working set has been **re-sectioned per-file**
into the durable-vs-ephemeral structure (Mission B, FR-001 / FR-012, resolving
[#2054](https://github.com/Priivacy-ai/spec-kitty/issues/2054)). Pages no longer
mix durable references with one-off tracking notes.

## Where the pages went

- **Durable operational runbooks** → [`../operations/`](../operations/index.md)
  (deploy keys, the identity-boundary CI gate).
- **Durable contributor how-tos** → [`../guides/`](../guides/index.md)
  (testing flakiness/parallel, contract pinning, review gates, local overrides).
- **Durable config / toolchain references** → [`../configuration/`](../configuration/index.md)
  (YAML library choice, linting cutoff policy).
- **Ephemeral working notes** (audits, debriefs, mission/effort-scoped plans,
  investigations, the former `engineering_notes/` and `tracking/` clusters)
  → [`../plans/`](../plans/index.md) under the distil-then-retire lifecycle.

## What stays here

- **`3-2-page-inventory.yaml`** — the page-inventory tooling artifact. It STAYS
  PUT by operator directive; the freshness/lockfile tooling
  (`scripts/docs/inventory_lockfile.py`, `check_docs_freshness.py`,
  `version_leakage_check.py`, `_inventory.py`) reads it at this stable path.
  A regression guard (`tests/docs/test_inventory_path_stable.py`) asserts the
  path cannot silently move.
- **`mutation-testing-tactic.yaml`** — a doctrine tactic artifact (non-page).

## See also

- [Documentation home](../index.md)
- [Contributing guide](../../CONTRIBUTING.md)
