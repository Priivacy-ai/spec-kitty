# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

**Prompting questions**
- What tooling or command did you have to work around?
- What blocked you unexpectedly, and how long did it take to unblock?
- Was this a known issue or something discovered fresh?

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what happened, why it slowed you down. -->

- 2026-07-29 — Seeded at planning. (No friction yet.) Watch items carried from the prior
  delivery slice: (a) `test_every_load_delivery` local false-red from ambient
  `context-state.json` — this mission fixes it as FR-009; (b) full `tests/architectural/` runs
  break the session — use targeted node-ids only; (c) `bare python`/`pytest` in a lane imports
  PRIMARY src — always `uv run`; (d) org monthly spend limit was active in sibling sessions —
  watch for dispatch terminations.
