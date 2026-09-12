---
work_package_id: WP01
title: Census predicate hardening — .from_dict/factory readers red the census
dependencies: []
requirement_refs:
- FR-010
planning_base_branch: feat/verdict-seam-write-unification
merge_target_branch: feat/verdict-seam-write-unification
branch_strategy: Planning artifacts for this mission were generated on feat/verdict-seam-write-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verdict-seam-write-unification unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_verdict_seam_census.py
create_intent: []
execution_mode: code_change
owned_files:
- tests/architectural/test_verdict_seam_census.py
- tests/architectural/verdict_seam_census.yaml
- tests/architectural/census/verdict_seam_IC01.yaml
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned profile: run `/ad-hoc-profile-load python-pedro` (or
`spec-kitty charter context --action implement`). Do not start work until the profile is loaded.

## Objective

Extend the verdict-seam census AST derivation so a review-cycle verdict record constructed through a
`.from_dict` classmethod or a factory helper **reds the census** — not only records built by a direct
constructor call. Add named `_EXCLUDED_MODULE_REASONS` so event-authority deserializers **and** the
new provenance-backfill migration (WP02) stay excluded. This lands **first** (no dependencies) so the
census can *prove* reader retirement when WP05 collapses the readers.

## Context

- **Requirements**: FR-010 (census `.from_dict` blind-spot closed **before** the collapse), NFR-002
  (census fails on any uncounted member; ≥1 synthetic-poison + ≥1 real-data test), SC-006.
- **Contract**: [contracts/census-predicate.md](../contracts/census-predicate.md) — G1 completeness,
  G2 no over-match (named exclusions), G3 shrinkage-red.
- **Decision**: research.md **D-PLAN-14** — the real `.from_dict` gap site is `status/models.py:570`
  (a `ReviewApproval`/override deserializer), **not** `backfill_runtime_state.py::_runtime_repair_delta`,
  which uses a *direct* constructor the current predicate already matches. **Verify this before
  claiming the gap.** IC-01 in [plan.md](../plan.md#ic-01--census-predicate-hardening-lands-first).
- **Why first**: C-008 — census hardening precedes the collapse; the shared `verdict_seam_census.yaml`
  forbids parallel lanes, so this WP opens the serial census chain (WP01→WP02→WP05→WP06).

The census owner is `tests/architectural/test_verdict_seam_census.py::_derive_census` with the
enumerated fixture `verdict_seam_census.yaml` and the IC-shard `census/verdict_seam_IC01.yaml`. The
scope regex / constructor classifier lives in `_RECORD_CTOR_CALL_RE`, `_contains_ctor`,
`_call_base_name`.

## Subtasks

### T001 — Red-first: synthetic `.from_dict` poison test
- **Purpose**: Establish the failing anchor. No `.from_dict` reference exists in the census today, so
  this test must be **red before** the predicate is extended (spec C-002).
- **Steps**: In `test_verdict_seam_census.py`, add a test that injects a synthetic module source (in a
  tmp path fed to `_derive_census`, or via the existing test harness) whose function constructs a
  review record via `ReviewOverride.from_dict(...)` / `ReviewCycleArtifact.from_dict(...)`. Assert the
  derivation classifies the function as a census member (US5 scenario 1). Confirm it is RED against the
  current predicate.
- **Files**: `tests/architectural/test_verdict_seam_census.py`.
- **Validation**: `pytest tests/architectural/test_verdict_seam_census.py -k from_dict_poison -q` fails
  with "uncounted member not classified" *before* T003.

### T002 — Verify the real gap site, don't assume it
- **Purpose**: Ground the change in live code (D-PLAN-14): confirm `status/models.py:570` is the actual
  `.from_dict` reader the current predicate misses, and confirm `_runtime_repair_delta` uses a direct
  ctor already matched (so it is *not* the gap).
- **Steps**: Read `status/models.py` around line 570 and `migration/backfill_runtime_state.py`
  `_runtime_repair_delta`. Record in the test module a short comment naming the verified gap site.
  If the anchor drifted, grep `\.from_dict\(` under `src/specify_cli/status` + `review` and pick the
  review-cycle verdict deserializer.
- **Files**: (read-only verification) `tests/architectural/test_verdict_seam_census.py` comment.
- **Validation**: the exclusion added in T004 names the *verified* module, not a guessed line.

### T003 — Extend the derivation to recognize `.from_dict`/factory construction
- **Purpose**: Make G1 hold — a helper/`.from_dict`-constructed reader reds the census.
- **Steps**: Extend `_RECORD_CTOR_CALL_RE` (or the classifier) to recognize `<Record>.from_dict(` via
  `_call_base_name`, per [contracts/census-predicate.md](../contracts/census-predicate.md). Optionally
  key the *reader* predicate on "opens a path matching `review-cycle-*.md` by name" rather than a fixed
  verb list (contract Predicate-extension). Keep the change minimal and typed.
- **Files**: `tests/architectural/test_verdict_seam_census.py`.
- **Validation**: T001's poison test goes GREEN; the real-data test (T005) classifies the verified gap.

### T004 — Named `_EXCLUDED_MODULE_REASONS` for event-authority deserializers + the backfill module
- **Purpose**: G2 (no over-match). The broadened predicate must not sweep event-authority
  deserializers (`status/reducer.py`, `status/models.py`, `status/wp_review.py`,
  `_snapshot_review_override`) or the WP02 provenance-backfill migration into the reader set.
- **Steps**: Add named entries to `_EXCLUDED_MODULE_REASONS` with a one-line rationale each, including a
  forward-declared entry for `migration/verdict_provenance_backfill.py` (WP02's new module — it
  *writes* the event authority, it is not a frontmatter verdict reader) **and** a forward-declared entry
  for `status/verdict_vocab.py` (WP04's new pure vocabulary-mapping surface — it maps `{approved,
  rejected}` strings, it does not read/write/resolve a review-cycle verdict record). Authoring **both**
  forward-declared exclusions here (WP01 owns `test_verdict_seam_census.py`) is deliberate: it means
  neither WP02 nor WP04 ever edits the census test, so there is no concurrent-edit race on the
  exclusion list (paula F2). Ensure `test_review_slot_is_event_authoritative…` stays green.
- **Files**: `tests/architectural/test_verdict_seam_census.py`.
- **Validation**: negative-control test (T005) asserts an event-authority deserializer stays excluded
  by a *named* reason (US5 scenario 2) — no silent over-match.

### T005 — Real-data + negative-control tests; reconcile fixtures
- **Purpose**: NFR-002 requires ≥1 real-data test in addition to the synthetic poison; G3 requires the
  derived active set to equal the fixture exactly.
- **Steps**: Add a real-data test asserting the verified gap site (T002) is classified. Add the
  negative control (exclusion holds). Re-derive and reconcile `verdict_seam_census.yaml` +
  `census/verdict_seam_IC01.yaml` so the derived set == fixture (this WP adds no `status: retire` rows
  yet — retirements land in WP05/WP06). Run the full census test.
- **Files**: `tests/architectural/test_verdict_seam_census.py`, `verdict_seam_census.yaml`,
  `census/verdict_seam_IC01.yaml`.
- **Validation**: `pytest tests/architectural/test_verdict_seam_census.py -q` green.

## Branch Strategy note

Planning artifacts were generated on `feat/verdict-seam-write-unification`; completed changes merge
back into it. `branch_strategy: already-confirmed`. Prepare the workspace with
`spec-kitty implement WP01` — it resolves the coord-topology lane worktree from `lanes.json`; do not
reconstruct the path. This WP is the head of the census serial chain — merge it before WP02 starts
editing the shared `verdict_seam_census.yaml`.

## Definition of Done

- SC-006: the census reds on a `.from_dict`/factory-constructed reader; the synthetic-poison test and
  the real-data test both pass; the event-authority-deserializer negative control stays excluded.
- Fixture equals the derived active set (G3); no `status: retire` rows added here.
- Gate: `pytest tests/architectural/test_verdict_seam_census.py -q` green;
  `ruff check tests/architectural/test_verdict_seam_census.py` and `mypy --strict` clean; NFR-003.

## Risks

- **Over-match** — mitigated by named `_EXCLUDED_MODULE_REASONS` (T004) and the negative control.
- **Anchor drift** — `models.py:570` may move; T002 re-verifies by grep, does not trust the line.

## Reviewer guidance

Confirm the poison test was red-first (check the diff order / commit trail). Confirm the exclusions are
**named with rationale**, not a blanket skip. Confirm no `status: retire` row leaked in — this WP only
*broadens* the predicate; shrinkage belongs to WP05/WP06.
