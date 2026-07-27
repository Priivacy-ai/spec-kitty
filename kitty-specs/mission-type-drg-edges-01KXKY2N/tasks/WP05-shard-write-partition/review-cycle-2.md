---
affected_files: []
cycle_number: 2
mission_slug: mission-type-drg-edges-01KXKY2N
reproduction_command: NO_COLOR=1 uv run pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_charter_facades_reexport_doctrine.py tests/architectural/test_ratchet_baselines.py -q
reviewed_at: '2026-07-16T12:51:54Z'
reviewer_agent: claude:opus:reviewer-renata:reviewer
verdict: approved
wp_id: WP05
---

# WP05 Review — Cycle 2 — APPROVED

**Reviewer:** reviewer-renata (claude:opus)
**Verdict:** APPROVED — both cycle-1 blockers fixed, no regression, no production-logic change.

Cycle-2 fix commit `0d479f7ca` touches exactly 3 files (`src/charter/drg.py`,
`tests/architectural/test_no_dead_symbols.py`,
`tests/doctrine/drg/migration/test_extractor.py`); the merge commit `dd9379116` on top
only syncs coord status artifacts. The approved cycle-1 core (extractor.py production
logic, `doctrine.py`, `test_sharded_layout.py`, the 10 `*.graph.yaml` fragments) is
byte-identical since `d5bbc1d1a` — verified via `git diff d5bbc1d1a..HEAD` over those
paths (empty).

## BLOCKER 1 — facade two-gate tension — FIXED

- `load_graph` restored to BOTH the `from doctrine.drg import (...)` block AND
  `charter.drg.__all__`. `built_in_graph_source` correctly stays ABSENT from `__all__`
  (not in the facade contract).
- Allowlist entry `SymbolKey("load_graph", "ae679d…", module_path="charter.drg")` is
  escalated to the `module_path` tier, documented with the facade-contract rationale
  (`charter-facade-modules.md`, MissionStep precedent) and tracker #2677 (FR-303), wired
  into `_SYMBOL_ALLOWLIST` via `_CATEGORY_C_MISSION_TYPE_DRG_EDGES_FACADE_REEXPORT`.
- **Hash legitimacy proven load-bearing, not guessed/inert:** removing the allowlist
  entry reds `test_no_public_symbol_in_all_is_unimported` on exactly
  `charter.drg::load_graph`; with the entry present the gate is green — so the hash
  matches the real offender.
- `test_auto_exempt_disjoint_from_hand_allowlist` green (no overlap with auto-exempt).
- **THE cycle-1 defect is gone — both facade gates + dead-symbol + ratchet GREEN
  TOGETHER:** `test_no_dead_symbols.py` + `test_charter_facades_reexport_doctrine.py` +
  `test_ratchet_baselines.py` → 60 passed.

## BLOCKER 2 — `_partition_by_kind` focused test — FIXED

- `TestPartitionByKind` (5 tests) pins: one fragment per populated kind incl. target-only
  (`TEMPLATE`, empty edges) [DD-8 totality]; node homogeneity; each edge in its SOURCE
  node's kind fragment [FR-007]; DD-11 order (nodes by URN, edges by
  `(source,target,relation)`); disjoint-union reconstruction.
- **Non-vacuity proven empirically:** perturbing `_partition_by_kind` to route edges by
  `edge.target` kind fails 3/5 assertions (source-routing, target-only empty-edges,
  intra-fragment order); reverted clean. The assertion is not something a target-routing
  bug could still satisfy.
- `extractor.py` production logic unchanged (test-only fix).

## Regression

- `ruff check` + `mypy --strict` clean on all 3 changed files.
- `NO_COLOR=1 uv run pytest tests/doctrine tests/architectural -q` → **3590 passed, 4
  skipped, 0 failed** (serial run; the two known parallel-isolation flakes did not
  surface).
- Anti-pattern checklist: all PASS (dead-code exempt entry is contract-required facade
  re-export; new `_partition_by_kind` clauses now have a live focused test; no silent
  returns; no frozen-surface or locked-decision violations; extractor write-step leeway
  documented).

Cycle-1 "Verified good" core (behaviour-preserving 280/757/10 flip, DD-8 totality, DD-7
atomic delete, transparent WP04-gate flip) was confirmed live in cycle 1 and is unchanged.
