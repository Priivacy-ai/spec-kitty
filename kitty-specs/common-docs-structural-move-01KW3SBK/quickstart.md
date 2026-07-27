# Quickstart: Common Docs Structural Move (Mission B) — Validation Scenarios

**Phase 1 output** · Mission `common-docs-structural-move-01KW3SBK` · 2026-06-27

These are the **acceptance scenarios** that prove the move is correct and complete. Each maps to spec
Success Criteria / NFRs and to an Implementation Concern. Run them as the mission's exit gate; the
ruler-blocking and lockfile scenarios are also the **full-gate dry-run before merge** (C-005).

---

## S1 — Every captured baseline URL resolves (NFR-002, SC-003 · IC-05)

**Goal:** 100% URL continuity across the move.

```bash
# 1. (pre-move, captured at plan/start) the baseline-URL inventory exists and is non-empty
# 2. build the DocFX site + emit redirect stubs
python scripts/docs/redirect_stub_generator.py --redirect-map <map> --site _site
# 3. coverage check: every baseline URL resolves directly or via a <meta refresh> stub
python scripts/docs/redirect_stub_generator.py --check-coverage --baseline <baseline> --site _site
```

**PASS when:** the coverage check reports **0 uncovered baseline URLs** (denominator = captured
baseline set). **FAIL** if any baseline URL has no resolving target — that is a dead public URL.

---

## S2 — All 117 ADRs present, era-homed, frontmattered, content-invariant (NFR-001, SC-002 · IC-04)

**Goal:** no ADR lost or content-altered; the 47 byte-identical mirrors dropped, not lost.

```bash
# census: 117 unique ADRs under docs/adr/<era>/, each with title+status+date frontmatter
find docs/adr -name '*.md' | wc -l        # expect 117 unique (+ section index.md files)
# the 20 era-less migrated to docs/adr/3.x/; the flat architecture/adrs/ shim closed
test ! -d architecture/adrs
# content-invariance: body-minus-header byte-identical for every converted ADR
pytest tests/ -k adr_content_invariance
```

**PASS when:** 117 unique ADRs resolve under `adr/<era>/`; every ADR carries a **bare `status`** key
with MADR vocabulary; the content-invariance check is green for all 117 (the reconciliation-ADR
self-amendment is the one scoped-out exception); the flat shim is gone.

---

## S3 — The rulers are blocking (a re-introduced violation is rejected) (SC-005 · IC-06)

**Goal:** A's report-only rulers now fail CI on regression.

```bash
# anti-sprawl ratchet — blocking via --strict (second root / shadow tree / un-frontmattered ADR)
python scripts/docs/anti_sprawl_ratchet.py --strict ; echo "exit=$?"   # expect non-zero on a planted violation
# related: validator — blocking via --strict (dangling related edge)
python scripts/docs/related_validator.py --strict ; echo "exit=$?"     # expect non-zero on a planted dangling edge
# lockfile drift gate — blocking via CODE change (INVENTORY-LOCKFILE-DRIFT now severity=error)
python scripts/docs/check_docs_freshness.py ; echo "exit=$?"           # expect non-zero on planted drift
```

**PASS when:** each ruler **exits non-zero** on a planted violation (a second doc root, a missing
`index.md`, an un-frontmattered ADR, a dangling `related:` edge, lockfile drift) and **exits 0** on
the clean tree. **C-005:** this scenario runs as a **full-gate dry-run over the whole tree before
merge** — not scoped to the mission diff (gate-unmask cannot self-validate).

---

## S4 — Lockfile generate-and-compare is green (NFR-006, SC-006 · IC-05/FR-010)

**Goal:** metadata lives in one place (frontmatter); the inventory is a deterministic generated
lockfile; drift = 0.

```bash
# regenerate the lockfile FROM frontmatter and compare to the committed inventory
python scripts/docs/inventory_lockfile.py --strict ; echo "exit=$?"    # expect 0 (was: 252 removed / 296 changed)
```

**PASS when:** `--strict` exits **0** — generated == committed, **drift = 0**. **Ordering note:** this
only passes **after** the tree move (IC-03) lands all content under `docs/` **and** frontmatter is
backfilled from the 580-row inventory; running it earlier reports the expected false drift.

---

## S5 — DocFX builds and publishes green (NFR-003, SC-004 · IC-05/FR-007)

**Goal:** the rewritten `docfx.json` globs + every `toc.yml` keep the site green; no SEO regression.

```bash
# the 13-section content globs + TOCs build
docfx build docs/docfx.json
# every published page retains title+description (length 50–180); 0 broken internal links
pytest tests/ -k "docs_build or link_integrity"
```

**PASS when:** DocFX builds with **0 broken internal links / `related:` edges** (NFR-004); every
published page has `title`+`description` within 50–180 chars; canonical/301 preserved (NFR-003).

---

## S6 — Single root, glossary read-path intact (SC-001, C-006 · IC-03)

**Goal:** one entry point, no shadow tree, glossary seam preserved.

```bash
# exactly one docs root; architecture/ folded away; no docs/<version>x shadow tree
test ! -d architecture && test ! -d docs/1x && test ! -d docs/2x && test ! -d docs/3x
# the dashboard glossary read-path still resolves the seed files
pytest tests/ -k "glossary_seed or glossary_handler"
```

**PASS when:** a reader reaches any doc from `docs/index.md` (one root, zero parallel/shadow trees);
the dashboard `GlossaryHandler` still resolves terms via `load_seed_file()` over
`.kittify/glossaries/<scope>.yaml` (merge-blocker C-006); `docs/3x` was distilled+moved+redirected
(not blind-deleted, C-004) and its landing zone is recorded for #2053.

---

## Exit checklist (mission-level)

- [ ] S1 — 100% baseline URLs resolve (NFR-002)
- [ ] S2 — 117 ADRs present, frontmattered, content-invariant (NFR-001)
- [ ] S3 — rulers blocking; full-gate dry-run over the whole tree green (FR-011, C-005)
- [ ] S4 — lockfile drift = 0 (NFR-006)
- [ ] S5 — DocFX green, 0 broken links, SEO preserved (NFR-003/004)
- [ ] S6 — single root, glossary seam intact, `docs/3x` distilled not deleted (C-004/C-006)
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py` green (CI-only terminology gate)
- [ ] `LEAK-FRONTMATTER-MISMATCH` retired only after S4 proves the lockfile gate blocking (FR-014)
- [ ] Reconciliation-ADR Neutral note amended to "3 doctrine tactics" (FR-013)
