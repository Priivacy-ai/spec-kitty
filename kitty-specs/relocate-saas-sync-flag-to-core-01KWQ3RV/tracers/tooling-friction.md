# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

**Prompting questions**
- What tooling or command did you have to work around?
- What blocked you unexpectedly, and how long did it take to unblock?
- Was this a known issue or something discovered fresh?

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what happened, why it slowed you down. -->

2026-07-04 — Touches: the CORE↛INTEGRATION architectural boundary guard (`test_integration_boundary.py`), the `saas`/`sync`/`tracker` feature-flag re-export chain, an ADR, and an archived-mission stability contract that is round-trip-tested. Friction watch: (1) charter now mandates SCOPED test runs (not full suite) — remember to target packages; (2) charter synthesis-manifest churn on every spec-kitty command trips move-task guards (seen in prior missions — discard/--force); (3) the stability contract lives in a COMPLETED mission's folder (kitty-specs/082-...), which tensions with archived-artifact immutability — plan must decide edit-in-place vs superseding note.
