# Quickstart / Validation — Mission A

Each scenario is a deterministic check an implementer/reviewer runs to confirm a concern is *really* done (not green-but-fake).

## 1. Rulers run report-only and emit a baseline (NFR-003, SC-004)

```bash
PYTHONPATH=. python scripts/docs/related_validator.py        # prints checked_count + dangling list; exit 0
PYTHONPATH=. python scripts/docs/inventory_lockfile.py --report
PYTHONPATH=. python scripts/docs/anti_sprawl_ratchet.py      # prints violations + baseline_count; exit 0
```
Expect: each exits 0 (report-only, C-002) and records a baseline violation count.

## 2. Every ruler self-test goes RED on its seeded violation (SC-003 — the real DoD)

```bash
pytest tests/docs/test_related_validator.py    # dangling-edge fixture asserts FAIL; checked_count > 0
pytest tests/docs/test_inventory_lockfile.py   # LINCHPIN: frontmatter tamper -> lockfile changes + gate RED; lockfile-only hand-edit -> rejected
pytest tests/docs/test_anti_sprawl_ratchet.py  # 4 injection fixtures (2nd root / missing index.md / un-frontmattered ADR / shadow tree) each detected; floor = 13 sections
```

## 3. The doctrine is governed + wired (SC-002)

```bash
spec-kitty doctrine regenerate-graph --check     # DRG freshness green with the 3 new nodes + relations
grep -R "<directive-id>" scripts/docs/anti_sprawl_ratchet.py   # the ratchet references the directive id (binding proven, C-003)
```

## 4. No doc-tree mutation (SC-005, C-006)

```bash
git diff --name-only origin/<merge-base> -- docs/ architecture/ | grep -vE '^architecture/3.x/adr/2026-06-27' || echo "clean: only the new ADR"
```
Expect: Mission A touches `src/doctrine/`, `scripts/docs/`, `tests/`, and adds the reconciliation ADR — and **moves/deletes no doc-tree file**.

## 5. The ADR closes every mechanism (SC-001)

The reconciliation ADR records D1–D7; Mission B opens with no undecided design (redirect mechanism, glossary read-path, era-less migration, status namespace, structure, curation).
