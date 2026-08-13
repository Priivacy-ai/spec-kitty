---
work_package_id: WP01
title: Durable doc_status marker + validator propagation (IC-01 foundation)
dependencies: []
requirement_refs:
- C-004
- FR-002
- NFR-001
planning_base_branch: feat/docs-plans-tier3-closeout
merge_target_branch: feat/docs-plans-tier3-closeout
branch_strategy: Planning artifacts for this mission were generated on feat/docs-plans-tier3-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-plans-tier3-closeout unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-docs-plans-closeout-and-doctrine-diagrams-01KZTK2J
base_commit: a88b483c9104ca83b4fa13cd01d45fb61fa6860f
created_at: '2026-08-12T17:12:45.860973+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- at: '2026-08-12'
  note: Authored by /spec-kitty.tasks (post-plan-squad model). IC-01 predecessor of IC-02/IC-03/IC-04.
agent_profile: python-pedro
authoritative_surface: packs/built-in/directives/042-common-docs.directive.yaml
create_intent:
- tests/docs/test_doc_status_durable.py
execution_mode: code_change
owned_files:
- packs/built-in/directives/042-common-docs.directive.yaml
- scripts/docs/frontmatter_backfill.py
- packs/built-in/styleguides/common-docs.styleguide.yaml
- packs/built-in/styleguides/docs-freshness-sla.styleguide.yaml
- packs/built-in/tactics/common-docs-curation.tactic.yaml
- packs/built-in/tactics/common-docs-write.tactic.yaml
- packs/built-in/tactics/common-docs-scaffold.tactic.yaml
- tests/docs/test_doc_status_durable.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Apply its initialization, boundaries, directives, and tactics. Then read this WP, `spec.md` (FR-002, NFR-001, C-004), `plan.md` (IC-01), `research.md` (D1), and `contracts/doc-status-durable.md` (the authority chain).

## Objective

Add `durable` as a **reserved, never-retire** value to the `doc_status` documentation-lifecycle vocabulary, propagated across the full authority chain so a domain-plan throughline marked `doc_status: durable` is accepted at every enumerated validation site and never flagged point-in-time / stale. **This is the foundation WP — IC-02, IC-03, and IC-04 all depend on it** (any doc written with `doc_status: durable` fails validation until this lands).

## Context

- **The `doc_status` vocabulary is prose/enum-declared, not structurally schema-encoded.** There is no closed-set validator that rejects an unlisted value today (the styleguide even notes vocabulary enforcement is deferred). So the executable gates that could *misclassify* `durable` are: (a) the structural lint's `point_in_time_placement` — `durable` must NOT be in `point_in_time_markers`; (b) the structural lint's `frontmatter_contract` — a `durable` page still carries `doc_status` + `updated`; (c) the `DocStatus` StrEnum. `scripts/docs/check_docs_freshness.py` is a **lockfile-drift** gate (regenerate-from-frontmatter), NOT a `doc_status`-threshold gate, so it does not flag durable pages — do not invent a staleness threshold there.
- **Authority order matters (C-004):** directive `042-common-docs` is the authoritative vocabulary; the `DocStatus` enum **mirrors** it. Edit the directive first, then the enum, or you introduce doctrine/code drift.
- **`closeout` is NOT a `doc_status` value** — it is a point-in-time-marker / archive-directory convention that maps to `deprecated`. It already appears in `point_in_time_markers`. Do not touch that; do not add `durable` beside it.
- **ATDD-first (C-011):** the "durable accepted everywhere" test lands **red-first** as a separate first commit, RED on `feat/docs-plans-tier3-closeout` before any propagation edit, GREEN on the final commit.

### Subtask T001 — Red-first ATDD test: `tests/docs/test_doc_status_durable.py`

**Purpose**: Pin the user-observable contract before implementing it. Commit this test FIRST (separate commit); it must be RED on the planning base.

**Steps**:
1. Create `tests/docs/test_doc_status_durable.py` with the neighbour marker convention `pytestmark = pytest.mark.architectural` (matches `tests/docs/test_docs_structural_lint.py`, `test_frontmatter_backfill.py`, `test_related_validator.py`). Reuse their fixture harness: the lint asset is loaded via `importlib` from `packs/built-in/assets/docs_structural_lint.py` and configured with `load_config(STYLEGUIDE_PATH)`; the `_write(...)` helper builds a synthetic page — mirror it rather than re-inventing.
2. Assert these guarantees. **The load-bearing, genuinely red-first, non-tautological assertion is the directive↔enum set-equality (a) — it cross-checks two independent authority sources and is the machine-verified "042 and the enum agree" gate SC-004 claims** (there is no closed-set runtime validator to lean on, so this cross-source consistency check IS the gate):
   - **(a) Directive↔enum agreement (RED-first, the real gate)**: parse the `doc_status` vocabulary set out of `packs/built-in/directives/042-common-docs.directive.yaml` (the `draft / active / deprecated / superseded` line) into a `set[str]`; build `{s.value for s in DocStatus}` from `scripts.docs.frontmatter_backfill`; assert the two sets are **equal** AND `"durable"` is in both. This reds on the base (durable in neither) and reds if only one of directive/enum is edited (drift), so it is not a constant-assertion — it fails unless both authority sources actually mirror.
   - **(b) Prose propagation presence (RED-first)**: assert `"durable"` appears in the `common-docs.styleguide.yaml` vocabulary prose **and** in each of the three tactic restatements (`common-docs-curation`, `common-docs-write`, `common-docs-scaffold`). Reds on base until T004 lands.
   - **(c) Never point-in-time (green-on-base REGRESSION GUARD)**: assert `durable` is NOT among `structural_lint_config.point_in_time_markers` values. This is green on base by design — it is a guard that reds only if someone later wrongly adds durable there. Label it as such in the test.
   - **(d) Structural-lint acceptance (guard)**: build a synthetic `durable` page (`doc_status: durable`, `updated: <date>`) OUTSIDE `plans/` and run the real lint asset (mirror `test_docs_structural_lint.py`'s `_write`/`load_config` harness); assert `point_in_time_placement` does NOT flag it and `frontmatter_contract` passes. Also green-on-base (nothing rejects the string) — a guard, not the red signal.
3. Run it and confirm the suite is RED on the base via (a)+(b). Commit as the first WP commit.

**Files**: `tests/docs/test_doc_status_durable.py` (new, ~110 lines). **Do not** claim (c)/(d) as the red-first signal — they are green-on-base guards; (a)+(b) carry red→green.

### Subtask T002 — Edit the AUTHORITY: directive 042 vocabulary

**Purpose**: Add `durable` to the authoritative closed vocabulary FIRST.

**Steps**:
1. In `packs/built-in/directives/042-common-docs.directive.yaml`, the doc_status vocabulary is stated at the `doc_status` bullet (currently `draft / active / deprecated / superseded`). Add `durable` to that vocabulary list, with a short reserved-never-retire gloss.
2. **Do NOT** touch the MADR `status` lines (Proposed / Accepted / Deprecated / Superseded) — those are the ADR decision-status exception, a different vocabulary.
3. **Sweep the WHOLE pack, not just the directive**, for vocabulary restatements: `rg 'draft . active . deprecated . superseded' packs/`. Beyond the directive, this hits the styleguide (T004) and three tactics (T004) — every restatement must gain `durable` so the pack's own guidance does not contradict the authority (doctrine/doctrine drift).

**Files**: `packs/built-in/directives/042-common-docs.directive.yaml`.

### Subtask T003 — Mirror in the `DocStatus` enum

**Purpose**: Keep the code enum in lockstep with the directive.

**Steps**:
1. In `scripts/docs/frontmatter_backfill.py`, add `DURABLE = "durable"` to `class DocStatus(StrEnum)` (after `SUPERSEDED`), with a one-line docstring/comment noting it is the reserved never-retire member mirroring directive 042.
2. Do NOT add `durable` to `TAG_DOC_STATUS` or `derive_doc_status` — no version tag derives to durable; it is authored by hand on throughlines only.

**Files**: `scripts/docs/frontmatter_backfill.py`.

### Subtask T004 — Styleguide + 3 tactics vocabulary prose + `durable ∉ point_in_time_markers`

**Purpose**: Reconcile every prose restatement of the vocabulary (styleguide + tactics) so the pack agrees with the authority, and prove durable is never point-in-time.

**Steps**:
1. In `packs/built-in/styleguides/common-docs.styleguide.yaml`, update the controlled-vocabulary prose (the `doc_status` line currently reading `draft | active | deprecated | superseded`) to include `durable` with the reserved-never-retire gloss.
2. Add `durable` (same gloss) to the three tactic restatements the sweep found: `packs/built-in/tactics/common-docs-curation.tactic.yaml` (~line 24), `common-docs-write.tactic.yaml` (~lines 43–44), `common-docs-scaffold.tactic.yaml` (~lines 37–38). These are prose guidance (no validator), but leaving them at four values ships a pack whose own tactics tell an agent `durable` is invalid.
3. **Leave `structural_lint_config.point_in_time_markers` unchanged** — it must continue to list only `point_in_time` and `closeout`. `durable` must NOT appear there (it is the semantic opposite). The T001 test (c) asserts this.

**Files**: `packs/built-in/styleguides/common-docs.styleguide.yaml`, `packs/built-in/tactics/common-docs-{curation,write,scaffold}.tactic.yaml`.

### Subtask T005 — Freshness-SLA styleguide: durable is never-stale

**Purpose**: Record the durable-is-never-stale policy in the freshness doctrine.

**Steps**:
1. In `packs/built-in/styleguides/docs-freshness-sla.styleguide.yaml`, add a prose rule (near the deprecation/retirement rule) stating that `doc_status: durable` pages are throughlines exempt from the staleness sweep — they are re-verified on domain change, not aged out.
2. This is a **prose/policy** edit (there is no executable staleness-threshold gate keyed on doc_status today); do not fabricate one.

**Files**: `packs/built-in/styleguides/docs-freshness-sla.styleguide.yaml`.

### Subtask T006 — Turn the suite green + confirm no regressions

**Purpose**: Prove red→green and zero collateral breakage.

**Steps**:
1. Run `PWHEADLESS=1 python -m pytest tests/docs/ tests/doctrine/test_schema_generation_integrity.py -q` — the new durable test is GREEN; `test_docs_structural_lint.py` (esp. the `point_in_time_markers` round-trip assertion) and `test_frontmatter_backfill.py` still pass. **Note:** `test_schema_generation_integrity.py` is run here as a *no-regression* check (the generated schema does not enum-encode the doc_status vocabulary — the `point_in_time_marker.frontmatter_value` is a free string — so this test is green→green and does NOT itself verify durable; the directive↔enum agreement is verified by T001(a), not by the schema gate).
2. Run `pytest tests/architectural/test_no_legacy_terminology.py -q` and `python scripts/docs/check_docs_freshness.py` (0 errors).
3. Record the red→green evidence (base SHA red, final SHA green) in the activity log.

**Files**: none beyond the above.

## Branch Strategy

Planning/base branch: `feat/docs-plans-tier3-closeout`. Final merge target: `feat/docs-plans-tier3-closeout`. Execution worktrees are allocated per computed lane from `lanes.json`.

## Definition of Done

- `tests/docs/test_doc_status_durable.py` was RED on the planning base (via assertions (a) directive↔enum set-equality and (b) prose propagation) and is GREEN on the final commit (red→green evidence: base SHA red, final SHA green, recorded in the activity log).
- `durable` is present in: directive 042 vocabulary, `DocStatus` enum, common-docs styleguide vocabulary prose, the **three** `common-docs-*` tactics, and docs-freshness-sla prose — and T001(a) proves the directive vocabulary set and the enum value set are **equal** (SC-004 agreement, machine-verified by cross-source comparison, not by the schema gate).
- `durable` is **absent** from `point_in_time_markers`; `closeout` is **not** added to the enum; no MADR `status` line altered.
- `tests/docs/` + `tests/doctrine/test_schema_generation_integrity.py` (no-regression) + `tests/architectural/test_no_legacy_terminology.py` green; `check_docs_freshness.py` 0 errors.
- ruff + mypy clean on `scripts/docs/frontmatter_backfill.py` and the new test (zero suppressions).

## Reviewer guidance

- Verify the directive was edited **before/with** the enum (authority-first) and that T001(a) asserts directive-set == enum-set (the real red-first agreement gate) — not merely that each file contains the string "durable".
- The red-first signal is (a)+(b) (propagation presence across the authority sites); (c) `durable ∉ point_in_time_markers` and (d) structural-lint acceptance are **green-on-base regression guards** — do NOT reject the test for "not exercising a validator red-first," because no closed-set doc_status validator exists (that enforcement is deferred to a later mission). Do confirm (a) genuinely parses two independent sources.
- Confirm the schema-integrity test was run as a no-regression check only (it does not verify durable) and that the pack sweep caught all restatements (styleguide + 3 tactics), leaving no site at four values.
- Confirm `point_in_time_markers` is byte-for-byte unchanged and `closeout` was not added to the enum.
