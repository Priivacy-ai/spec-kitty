---
work_package_id: WP01
title: Docs-gate non-vacuity (publication resolver + related_validator)
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-008
planning_base_branch: docs/3253-docs-gaps
merge_target_branch: docs/3253-docs-gaps
branch_strategy: Planning artifacts for this mission were generated on docs/3253-docs-gaps. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/3253-docs-gaps unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
history:
- at: '2026-08-08T10:45:09Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: scripts/docs/_published_pages.py
create_intent:
- tests/docs/test_description_length_check_propagation.py
execution_mode: code_change
owned_files:
- scripts/docs/_published_pages.py
- scripts/docs/related_validator.py
- tests/docs/test_published_pages.py
- tests/docs/test_description_length_check_propagation.py
- tests/docs/test_related_validator.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile so you inherit its
initialization, boundaries, directives, and tactics:

```
/ad-hoc-profile-load python-pedro
```

Confirm in your first message which initialization/boundaries/directives you applied
(expect: TDD/red-first before production code; run pytest+ruff+mypy before handoff;
stay in the Python-implementation lane; no architectural re-seam — the seam is pinned
below). Then proceed.

## Objective

Make the docs page-collection gates **non-vacuous**: (a) the published-page resolver must
fail loud when any declared DocFX include glob resolves to zero pages *pre-exclusion*
(closing the silent-under-collection band the aggregate 500 floor leaves open — FR-003),
(b) that guard must propagate through the shared resolver's other consumer
(`description_length_check.py` — FR-004), and (c) `related_validator.py` must gain the
same missing non-vacuity floor as its sibling (#3264 folded — FR-008).

## Context

- **Grounded facts** (verified by the pre-spec/post-plan squads): `docs/docfx.json` declares
  only **2** content entries; the real doc subtrees (`guides/`=76, `adr/`=152, `api/`=22, …)
  are **include globs inside the single root entry**. `_collect_entry_pages`
  (`scripts/docs/_published_pages.py:237-251`) OR-collapses all globs via `_matches_any`
  and the union flattens into `candidates` (`:181-183`), so **per-glob attribution is gone**
  after collection. `_assert_non_vacuous` (`:260-278`) checks only the aggregate union.
- **Seam is PINNED — do not re-seam.** Add an **additive** helper that operates on the
  in-scope `entries` tuple (each `_ContentEntry` keeps `includes`/`globs`, which are
  index-parallel and md-filtered — confirmed 19==19). Do **not** change
  `_collect_entry_pages`' union semantics or the `PublishedPageSet` return type.
- **Pre-exclusion** matters: the `archive` entry glob yields 14 raw matches pre-exclusion,
  0 post-`DEFAULT_EXCLUSIONS`. The guard must count raw matches BEFORE `_apply_exclusions`
  (`:186`) or `archive` false-fails and reds main.
- Current tree is green under the new guard (all 19 root globs ≥1; min=1 for
  `integrations`/`security`/`core-concepts`/`updates`) — introduction must not red main.
- `related_validator.validate_related` (`scripts/docs/related_validator.py:75`) walks
  `docs_root.rglob("*.md")` and returns `checked_count=0` cleanly on an empty tree. Its
  sibling `relative_link_fixer.py` already has the floor idiom (`min_files`/`min_links` →
  `RuntimeError`, `:471,527`); mirror it. Test file `tests/docs/test_related_validator.py`
  exists (extend it).

## Subtasks

### T001 — Extract `_vacuity_error()` shared builder (tidy-first)
**Purpose**: Before adding a 3rd raise site, DRY the two existing vacuity raises so all
three emit through one builder (DIRECTIVE_025 tidy-first, behavior-preserving).
**Steps**:
1. In `_published_pages.py`, extract a `_vacuity_error(config_path, source_globs, detail) -> ValueError` helper from the two existing raises in `_assert_non_vacuous` (`:268-278`).
2. **Reproduce the load-bearing substrings verbatim** — existing/negative tests assert on them: `violates I-01`, `collapsed (violates I-02)`, `expected at least`.
3. Keep the change purely behavior-preserving (no message text drift).
**Validation**: existing `tests/docs/test_published_pages.py` passes unchanged.

### T002 — Per-`(entry, include-pattern)` non-vacuity helper
**Purpose**: Detect a dropped subtree that the aggregate floor hides.
**Steps**:
1. Add `_assert_each_glob_nonvacuous(entries: tuple[_ContentEntry, ...], *, config_path) -> None`.
2. For each `entry`, iterate its index-parallel `(include_pattern, human_glob)` pairs; do a **second raw** `rglob`/match pass (ignoring both the entry-level `exclude` and `DEFAULT_EXCLUSIONS`) and count matches.
3. If any pattern matches `< 1` file, raise via `_vacuity_error(...)` (a `ValueError`) naming the **glob and its content entry**.
4. Iterate per `(entry, pattern)` — NOT the deduped `source_globs` (preserve entry attribution).
**Validation**: unit-covered by T004.

### T003 — Wire the guard into `resolve_published_pages`
**Purpose**: Run the per-glob guard at the correct point.
**Steps**:
1. Call `_assert_each_glob_nonvacuous(entries, config_path=...)` after the collect loop (`:184`) and **before** `_apply_exclusions` (`:186`).
2. Leave the 500 aggregate floor (`_assert_non_vacuous`) intact and after exclusions (C-002 — additive).
3. Do not alter the `PublishedPageSet` return type or the two public callers.
**Validation**: `python -c "from scripts.docs._published_pages import resolve_published_pages; from pathlib import Path; print(len(resolve_published_pages(docs_root=Path('docs'))))"` still prints 675.

### T004 — Negative test: dropped glob, aggregate ≥500 → `ValueError`
**Steps**:
1. In `tests/docs/test_published_pages.py`, using the existing `_write_config`/`synthetic_docs` harness, declare two markdown globs — one populated (≥500 pages), one empty.
2. Assert `resolve_published_pages` raises `ValueError` naming the empty glob.
3. Add an assertion (comment or explicit) that an aggregate-only / per-entry check would have passed — documents why the seam is per-glob.
**Validation**: test RED before T002/T003, GREEN after.

### T005 — [P] FR-004 propagation test
**Steps**:
1. New file `tests/docs/test_description_length_check_propagation.py`.
2. Drive the empty-glob fixture through `description_length_check.py`'s own entry point (`validate_descriptions` / `_resolve_page_set`, `:250-263`).
3. Assert it surfaces as `CoverageError` (exit 2) — proving the shared-resolver consumer inherits the failure path. This is why T002 must raise `ValueError` (the consumer catches `(FileNotFoundError, ValueError)`).
**Validation**: fails if the guard raises a non-`ValueError` type.

### T006 — [P] `related_validator` non-vacuity floor (#3264 / FR-008)
**Steps**:
1. Add a `min_files: int = 1` parameter (or module constant) to `validate_related` in `scripts/docs/related_validator.py`.
2. After the walk, if `checked_count < min_files`, raise `RuntimeError` with an "expected at least {min_files} … non-vacuity guard" message, mirroring `relative_link_fixer.py:527`.
3. `RuntimeError` (not `ValueError`) — parity with the sibling gate; no `CoverageError` consumer here.
**Validation**: unit-covered by T007.

### T007 — [P] Zero-file negative test for related_validator
**Steps**:
1. In `tests/docs/test_related_validator.py`, add a test invoking `validate_related` against an empty/no-markdown tree.
2. Assert `RuntimeError` is raised; assert a populated tree still returns a report.
**Validation**: RED before T006, GREEN after.

## Branch Strategy

- **Planning/base branch**: `docs/3253-docs-gaps`. **Final merge target**: `docs/3253-docs-gaps`.
- Execution worktrees are allocated **per computed lane** from `lanes.json` (written by
  `finalize-tasks`); enter the workspace `spec-kitty implement WP01` resolves — do not
  reconstruct the path. WP01 is Lane A (independent).

## Test Strategy (ATDD, C-006)

Red-first: land T004/T005/T007 (and the guard code they exercise) so each negative test is
RED before the guard exists and GREEN after. Targeted surface only:
`pytest tests/docs/test_published_pages.py tests/docs/test_description_length_check_propagation.py tests/docs/test_related_validator.py`.
Run `ruff check scripts/docs/ tests/docs/` and `mypy` clean; keep new functions ≤15 complexity.

## Definition of Done

- Per-glob pre-exclusion guard live; dropping any declared glob raises `ValueError` naming it, even with aggregate ≥500 (SC-003/SC-004).
- Live tree still resolves 675 pages; no red main.
- FR-004 propagation proven through `description_length_check` (CoverageError).
- `related_validator` raises `RuntimeError` on a zero-file walk (SC-007, closes #3264).
- All new negative tests committed and non-vacuous (NFR-001); ruff + mypy clean.

## Risks / Reviewer guidance

- **Reviewer**: verify the guard iterates `entries` (not `candidates`), counts **raw**
  pre-exclusion, and did NOT change `_collect_entry_pages`' union semantics or the return
  type. Confirm `_vacuity_error` reproduced the `I-01`/`I-02`/`expected at least` substrings
  verbatim. Confirm the exception types (`ValueError` for the resolver, `RuntimeError` for
  related_validator) match the propagation contract.
