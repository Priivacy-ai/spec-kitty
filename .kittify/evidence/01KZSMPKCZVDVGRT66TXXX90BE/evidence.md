# WP06 planning-gap feedback

The canonical command

`python -m scripts.docs.freshen_adr_inventory --check docs/adr/3.x/2026-08-12-1-checkout-ownership-for-mission-create-and-next.md`

reports:

- `ADR-README-ROW-MISSING 2026-08-12-1-checkout-ownership-for-mission-create-and-next.md`
- `INVENTORY-LOCKFILE-DRIFT (committed inventory is stale)`

WP06 currently owns only the ADR wildcard. Amend it minimally to own the two generated outputs required by `docs/adr/3.x/index.md`: `docs/adr/3.x/index.md` and `docs/development/3-2-page-inventory.yaml`. Map their refresh to T020 / FR-011 / NFR-004, then finalize and re-analyze before reclaiming implementation.
