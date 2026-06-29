# Data Model: Common Docs Structural Move (Mission B)

**Phase 1 output** · Mission `common-docs-structural-move-01KW3SBK` · 2026-06-27

This mission moves files and metadata; the "data model" is the set of **document-metadata entities**
and the **invariants** that must hold across the move. No database — every entity is a file or a
generated artifact on disk.

---

## Entities

### 1. Doc page

A single `.md` file under the unified `docs/` root, carrying **in-file YAML frontmatter as the sole
metadata SSOT** (A's D1, directive 042).

| Field | Type | Notes |
|-------|------|-------|
| `title` | string | Required; consumed by DocFX + SEO gate. |
| `description` | string | Required; **length 50–180** (NFR-003 SEO). |
| `doc_status` | enum | `draft \| active \| deprecated \| superseded`. The **page-lifecycle** key. **Bare `status` is prohibited** for pages (collides with WP-lane status; directive 042). |
| `updated` | date `YYYY-MM-DD` | Freshness date. |
| `related` | list[repo-relative `.md` path] | Cross-references; resolvable, validated at build time (replaces the dead `citation_refs`). |
| `version_tag` / `divio_type` / `owning_workstream` | string | Rolled up into the lockfile. |

- **Location**: one of the **13 Common Docs sections** under `docs/` (`index`, `context`,
  `architecture`, `adr`, `plans`, `api`, `configuration`, `integrations`, `security`, `guides`,
  `operations`, `migrations`, `changelog`). Each section directory carries its own `index.md`.
- **SSOT direction**: frontmatter is authoritative; the inventory lockfile is **derived from** it.

### 2. ADR (Architecture Decision Record)

An immutable decision record under **`docs/adr/<era>/`** (`1.x` / `2.x` / `3.x`).

| Field | Type | Notes |
|-------|------|-------|
| `title` | string | Required (`ADR_FRONTMATTER_REQUIRED_KEYS`). |
| `status` | enum | **Bare `status`** — `Proposed \| Accepted \| Deprecated \| Superseded` (MADR vocabulary). The **sanctioned exception** to the bare-`status` prohibition (directive 042). |
| `date` | date | Required. |
| *body* | markdown | **Immutable decision content** — only location + header format may change (C-002). |

- **Census (live)**: **117 unique** ADRs = 97 era + 20 era-less. The 20 era-less (flat
  `architecture/adrs/`) migrate to `adr/3.x/` by dated filename. **47 byte-identical flat mirrors are
  dropped** (lossless) as the flat shim closes.
- **Header dialects**: ~12 markdown-table, ~34 bold-inline, **0 with YAML frontmatter today** — both
  dialects converted by the two parsers (D-R2).

### 3. Page-inventory lockfile

`docs/development/3-2-page-inventory.yaml` — a **generated** rollup, regenerated FROM frontmatter via
`scripts/docs/inventory_lockfile.py`.

| Aspect | Value |
|--------|-------|
| Generation | `run_generate_and_compare(docs_root, inventory, repo_root, strict)` → `InventoryDrift(added, removed, changed)` |
| Authority | **Derived** — frontmatter is SSOT (D1); the lockfile is the asserted rollup |
| Rollup semantics (load-bearing, must survive) | completeness ("every `.md` inventoried"), workstream ownership, deterministic alphabetical diff |
| Current state | **580 rows**; live `--strict` drift **252 removed / 296 changed / 0 added** (= FR-010 backfill workload) |
| Target state | drift **= 0** (generated == committed) — only AFTER the move + backfill |

### 4. Redirect map

A **checked-in** old-path → new-path mapping, consumed by `scripts/docs/redirect_stub_generator.py`
to emit `<meta http-equiv="refresh">` stub pages per old path into the DocFX `_site` output.

| Field | Type | Notes |
|-------|------|-------|
| `old_path` | URL/path | The pre-move published path (key). |
| `new_path` | URL/path | The post-move target. |
| *denominator* | baseline-URL inventory | The captured pre-move published URL set — the NFR-002 "100% resolve" denominator. |

- **Baseline-anchored**: every entry traces to a captured baseline URL; coverage = every baseline URL
  resolves directly or via a stub.

### 5. Occurrence map

`occurrence_map.yaml` — the **8-category** bulk-edit classification of every reference rewrite.
**(Owned by a parallel task; modeled here, not authored by this mission.)**

| Aspect | Value |
|--------|-------|
| Unit | **path-pair** (old-path → new-path) — the #1815 structural-restructure extension (D-R1) |
| Categories | the 8 bulk-edit occurrence categories (exceptions, not exemptions) |
| Scope | `src/` (runtime-critical first), doctrine, `kitty-specs/`, tests, docs |
| Sizing | **regenerated from the live tree** — historical ~571 files is a likely-LOW estimate |

---

## Invariants

| Invariant | Statement | Enforced by |
|-----------|-----------|-------------|
| **Content-invariance (ADR)** | For every moved ADR, **body-minus-header bytes are identical** before and after conversion; **0 decision-content mutated, 0 lost** (the 47 byte-identical mirrors drop losslessly). The reconciliation-ADR self-amendment (FR-013) is the **one sanctioned exception** — scoped out of the check. | Content-invariance check (contracts/content-invariance.md); NFR-001, C-002 |
| **URL-continuity** | **100%** of captured-baseline public URLs resolve directly or via a generated `<meta refresh>` stub. | Redirect-stub generator + coverage check (contracts/redirect-stub.md); NFR-002 |
| **Single-root** | Exactly **one** `docs/` documentation root; **no** second root (`architecture/` removed) and **no** `docs/<version>x` shadow tree survives; every section carries `index.md`. | Anti-sprawl ratchet (blocking, FR-011); SC-001/SC-005 |
| **Frontmatter-SSOT / lockfile-sync** | Per-page metadata lives in **exactly one place** (frontmatter); the inventory lockfile **regenerates deterministically** and **generated == committed** (drift = 0). | Lockfile drift gate (blocking via code change, FR-011); NFR-006, SC-006 |
| **Link integrity** | **0** broken internal doc links; **0** dangling `related:` edges. | `related:` validator (blocking, FR-011); NFR-004 |
| **Glossary read-path (merge-blocker)** | The `.kittify/glossaries/<scope>.yaml` seed read-path and the doctrine-extraction source resolve after the `context/` move; only the human markdown relocates. | Manual + dashboard `GlossaryHandler` / `load_seed_file()` verification; C-006 |
| **ADR completeness** | All **117 unique** ADRs present post-move under `adr/<era>/` with era + frontmatter. | ADR census check; NFR-001, SC-002 |

---

## State transitions (the serial spine)

```
occurrence-map (IC-01)
  → src/ runtime-critical reads rewritten + resolution-tested (IC-02)   [BEFORE any move — C-003]
    → tree move: two-root collapse + glossary (IC-03)                   [gates IC-04, IC-05]
      ├─ ADR conversion: 117 → adr/<era>/ frontmattered (IC-04)         ⎫ parallel — disjoint
      └─ refs + redirects + frontmatter backfill (IC-05)                ⎭ surfaces
        → lockfile drift closes to 0 (FR-010 — only AFTER move+backfill)
          → rulers flip to blocking (IC-06) + full-gate dry-run (C-005)
            → ADR-note amendment (FR-013) + LEAK retirement (FR-014) (IC-07)
```

**Investigation-note lifecycle (D7, FR-008/FR-009):** `doc_status: draft|active` (in-flight in
`plans/`) → **distil** durable finding into `adr/` or `architecture/` → `doc_status: deprecated` →
delete-stale retirement.
