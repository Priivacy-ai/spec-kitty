---
title: Architecture Decision Records
description: 'Architecture Decision Records for Spec Kitty, organized by release era (1.x, 2.x, 3.x). Each ADR captures one decision and its rationale.'
doc_status: active
updated: '2026-06-27'
related:
- docs/adr/1.x/README.md
- docs/adr/2.x/README.md
- docs/adr/3.x/README.md
- docs/architecture/index.md
- docs/index.md
---
# Architecture Decision Records

Architecture Decision Records (ADRs) capture a single architectural decision and
the rationale behind it. They are organized by release era so the history of the
system is navigable across major versions.

## Eras

- [1.x ADRs](1.x/README.md) — decisions from the 1.x lineage.
- [2.x ADRs](2.x/README.md) — decisions from the 2.x lineage.
- [3.x ADRs](3.x/README.md) — current (3.x) decisions.

## Adding an ADR

After adding an ADR file under `docs/adr/<era>/`, run:

```bash
python scripts/docs/freshen_adr_inventory.py docs/adr/<era>/<your-adr>.md
```

This freshens **both** indexes the `docs-freshness` CI gate enforces — the
generated page-inventory lockfile (`docs/development/3-2-page-inventory.yaml`)
and the era `README.md` index table — in one idempotent, date-ordered pass.
Use `--all` to back-fill every missing row, or `--check` to verify without
writing.

## See also

- [Documentation home](../index.md)
- [Architecture](../architecture/index.md)
