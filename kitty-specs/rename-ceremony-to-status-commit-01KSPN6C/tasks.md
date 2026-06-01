# Tasks: Rename Ceremony Commit to Status Commit

**Mission**: `rename-ceremony-to-status-commit-01KSPN6C`
**Mission ID**: `01KSPN6C5DWX7MRFMCD2BG1SBT`
**Change mode**: `bulk_edit` (`occurrence_map.yaml` is the canonical edit map)
**Source**: [GitHub Issue #1325](https://github.com/Priivacy-ai/spec-kitty/issues/1325)
**Date**: 2026-05-28

## Overview

Pure terminology rename. Replace every active-source occurrence of "ceremony" and "status-writing" with the canonical "status commit", anchored in the glossary, enforced by an architectural test. 25 occurrences across 12 files, 1 new test, glossary edit. No runtime behavior changes.

Work is split into **6 work packages** along file-boundary lines (no two WPs touch the same files). WP01–WP05 are independent and run in parallel. WP06 (regression guard) depends on all of them so its test passes on first run.

| WP | Title | Subtasks | Est. lines | Deps |
|----|-------|----------|------------|------|
| WP01 | Glossary canonical + deprecated entries | 4 (T001–T004) | ~250 | none |
| WP02 | commit_helpers.py reconciliation | 3 (T005–T007) | ~230 | none |
| WP03 | Test fixtures + identifier renames | 7 (T008–T014) | ~420 | none |
| WP04 | Doctrine prose semantic rewrite | 4 (T015–T018) | ~270 | none |
| WP05 | Docs prose + F-09 flag rewrite | 5 (T019–T023) | ~310 | none |
| WP06 | Architectural regression guard | 3 (T024–T026) | ~250 | WP01, WP02, WP03, WP04, WP05 |

**Total**: 26 subtasks across 6 WPs. Parallelizable into 2 phases: WP01–WP05 in parallel, then WP06.

**MVP scope**: There is no smaller MVP than the full mission — every WP except WP06 is independently mergeable and reduces forbidden-term occurrences toward zero. WP06 is the lockdown that prevents regression.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add canonical `status commit` entry to glossary | WP01 | [P] |
| T002 | Add deprecated `ceremony commit` entry to glossary | WP01 | [P] |
| T003 | Add deprecated `status-writing operation` entry to glossary | WP01 | [P] |
| T004 | Verify glossary loads and contains all three entries | WP01 |  |
| T005 | Update line 141 comment in `commit_helpers.py` | WP02 | [P] |
| T006 | Update line 159 error string in `commit_helpers.py` | WP02 | [P] |
| T007 | Run targeted tests to confirm `commit_helpers.py` behavior | WP02 |  |
| T008 | Rename `E2E_CEREMONY_BRANCH` constant + literal value | WP03 | [P] |
| T009 | Rename `_checkout_e2e_ceremony_branch` fn + callers + docstrings | WP03 | [P] |
| T010 | Rename `mission-merge-ceremony` fixture ID | WP03 | [P] |
| T011 | Update assertion paired with T010 | WP03 |  |
| T012 | Rewrite `tests/architectural/_baselines.yaml` comment | WP03 | [P] |
| T013 | Run targeted tests | WP03 |  |
| T014 | Grep `tests/` for stragglers | WP03 |  |
| T015 | Rewrite `procedures/README.md:15` | WP04 | [P] |
| T016 | Rewrite `software-dev/tasks/guidelines.md:26` | WP04 | [P] |
| T017 | Rewrite 4 occurrences in `spec-kitty-program-orchestrate/SKILL.md` | WP04 | [P] |
| T018 | Grep `src/doctrine/` for stragglers | WP04 |  |
| T019 | Rewrite `org-doctrine-layer-architecture-review.md:481` | WP05 | [P] |
| T020 | Rewrite `3-2-publication-checklist.md:210` | WP05 | [P] |
| T021 | Rewrite `reflections/README.md:12` | WP05 | [P] |
| T022 | Rewrite 5 occurrences in F-09 findings doc (incl. flag rename) | WP05 | [P] |
| T023 | Grep `docs/` for stragglers | WP05 |  |
| T024 | Create `tests/architectural/test_no_legacy_terminology.py` | WP06 | [P] |
| T025 | Run new test from lane workspace | WP06 |  |
| T026 | Run full `tests/architectural/` to confirm no regression | WP06 |  |

The `[P]` markers in the Parallel column above are reference-only; status tracking lives in the per-WP checkbox rows below.

---

## Work Package 1 — Glossary Canonical + Deprecated Entries

**Prompt**: [tasks/WP01-glossary-entries.md](tasks/WP01-glossary-entries.md)

**Goal**: Anchor the canonical `status commit` term in `.kittify/glossaries/spec_kitty_core.yaml` and mark both legacy terms (`ceremony commit`, `status-writing operation`) as deprecated. Follows the existing schema for deprecation (see 5 prior `status: deprecated` entries).

**Priority**: Foundation for the regression guard. Run early so other WPs can already reference the canonical entry while they make edits.

**Independent test**: `python -c "import ruamel.yaml; d = ruamel.yaml.YAML(typ='safe').load(open('.kittify/glossaries/spec_kitty_core.yaml')); s = {t['surface']: t for t in d['terms']}; assert s['status commit']['status']=='active'; assert s['ceremony commit']['status']=='deprecated'; assert s['status-writing operation']['status']=='deprecated'"` returns success.

**Dependencies**: None.

**Risks**: YAML ordering churn if implementer uses `yaml.dump` instead of preserving ruamel.yaml's round-trip mode. Mitigation: edit by hand or use ruamel.yaml round-trip mode.

### Subtasks

- [x] T001 Add canonical `status commit` entry to `.kittify/glossaries/spec_kitty_core.yaml` w/ `status: active`, definition from spec FR-006, synonyms_to_avoid list (WP01)
- [x] T002 Add deprecated `ceremony commit` entry w/ `status: deprecated` and definition pointing to canonical (WP01)
- [x] T003 Add deprecated `status-writing operation` entry w/ `status: deprecated` and definition pointing to canonical (WP01)
- [x] T004 Verify glossary loads via ruamel.yaml and all three surfaces present w/ correct status values (WP01)

---

## Work Package 2 — commit_helpers.py Reconciliation

**Prompt**: [tasks/WP02-commit-helpers-reconciliation.md](tasks/WP02-commit-helpers-reconciliation.md)

**Goal**: Reconcile the partially-landed "status-writing" phrasings in `src/specify_cli/git/commit_helpers.py` to the canonical "status commit". Two lines change: line 141 (test-mode bypass comment) and line 159 (the user-visible protected-branch error string). The error string lands at spec FR-003's exact assertion.

**Priority**: User-visible artifact. Worth landing early so the protected-branch error message contributors see during day-to-day work matches the canonical term.

**Independent test**: Grep `src/specify_cli/git/commit_helpers.py` for `status-writing` returns zero hits. Existing tests in `tests/git_ops/test_safe_commit_helper_integration.py` and `tests/architectural/test_safe_commit_*` pass.

**Dependencies**: None. WP01 doesn't block this.

**Risks**: Tests may assert on the exact pre-rename error string. Mitigation: search `tests/` for `"status-writing operations"` and update test expectations to the canonical string.

### Subtasks

- [x] T005 Update `src/specify_cli/git/commit_helpers.py` line 141 comment ("status-writing commands" → "status commit operations") (WP02)
- [x] T006 Update line 159 error string to canonical: `"Run status commit operations from the mission lane branch/worktree."` matching spec FR-003 (WP02)
- [x] T007 Run targeted tests; if any test asserted the pre-rename error string, update to canonical (WP02)

---

## Work Package 3 — Test Fixtures + Identifier Renames

**Prompt**: [tasks/WP03-test-fixtures-rename.md](tasks/WP03-test-fixtures-rename.md)

**Goal**: Rename Python identifiers, fixture IDs, branch literals, and a comment in 4 test files. The two doctrine fixtures get a workflow-sense rename (`mission-merge-ceremony` → `mission-merge-workflow`); the e2e fixtures get a commit-class rename (`E2E_CEREMONY_BRANCH` → `E2E_STATUS_COMMIT_BRANCH`). All callers must be updated together — `mypy --strict` will catch stragglers.

**Priority**: Largest single WP. Run in parallel w/ WP01/02/04/05.

**Independent test**: `pytest tests/e2e/ tests/doctrine/procedures/ tests/architectural/` passes. `grep -rn 'ceremony' tests/` returns zero hits.

**Dependencies**: None.

**Risks**: Identifier rename across modules. If `E2E_CEREMONY_BRANCH` is imported by other test modules, all importers must be updated. Mitigation: grep the entire `tests/` tree for the identifier before declaring done.

### Subtasks

- [x] T008 Rename `E2E_CEREMONY_BRANCH = "e2e-ceremony"` → `E2E_STATUS_COMMIT_BRANCH = "e2e-status-commit"` in `tests/e2e/conftest.py:25` (WP03)
- [x] T009 Rename `_checkout_e2e_ceremony_branch` (def L214 + calls L324, L399) and rewrite its docstring (L215) + the comment at L232 (WP03)
- [x] T010 Rename `mission-merge-ceremony` fixture ID → `mission-merge-workflow` in `tests/doctrine/procedures/conftest.py:48` (WP03)
- [x] T011 Update assertion in `tests/doctrine/procedures/test_models.py:31` to match new fixture ID (WP03)
- [x] T012 Rewrite `tests/architectural/_baselines.yaml:17` comment ("no ceremony" → "no extra workflow steps") (WP03)
- [x] T013 Run `pytest tests/e2e/ tests/doctrine/procedures/ tests/architectural/` and confirm green (WP03)
- [x] T014 `grep -rn 'ceremony' tests/` from repo root and confirm zero hits in tests-scope (WP03)

---

## Work Package 4 — Doctrine Prose Semantic Rewrite

**Prompt**: [tasks/WP04-doctrine-prose.md](tasks/WP04-doctrine-prose.md)

**Goal**: Rewrite 6 prose occurrences in `src/doctrine/` according to Rule R2 (semantic rewrite per context, per decision `01KSPP3SSZ5GKHTTB1C9EJQ13V`). These are workflow-sense occurrences, not commit-class — mechanical substitution would produce nonsense like "full status commit".

**Priority**: Independent. Run in parallel.

**Independent test**: `grep -rn 'ceremony' src/doctrine/` returns zero hits.

**Dependencies**: None.

**Risks**: Reviewer disagrees with rewording choice. Mitigation: occurrence_map.yaml has explicit per-line replacement text — apply exactly.

### Subtasks

- [x] T015 Rewrite `src/doctrine/procedures/README.md:15` per occurrence_map dd-001 (WP04)
- [x] T016 Rewrite `src/doctrine/missions/software-dev/actions/tasks/guidelines.md:26` per occurrence_map dd-002 (WP04)
- [x] T017 Rewrite all 4 occurrences in `src/doctrine/skills/spec-kitty-program-orchestrate/SKILL.md` (lines 9, 269, 343, 366) per occurrence_map dd-003 through dd-006 (WP04)
- [x] T018 `grep -rn 'ceremony' src/doctrine/` returns zero hits (WP04)

---

## Work Package 5 — Docs Prose + F-09 Config Flag Rewrite

**Prompt**: [tasks/WP05-docs-prose.md](tasks/WP05-docs-prose.md)

**Goal**: Rewrite 7 occurrences in `docs/` across 4 files, including the F-09 findings doc that proposes the `vcs.allow_*_commits_on_target_branch` flag. Confirmed at plan time: flag does not exist in live code, so this is the only place its name appears.

**Priority**: Independent. Run in parallel.

**Independent test**: `grep -rn 'ceremony' docs/` returns zero hits.

**Dependencies**: None.

**Risks**: The F-09 findings doc quotes the live error string at line 264. The pre-rename quote was "Run ceremony write operations…"; the post-rename quote should match the new live error from WP02. If WP02 and WP05 land at different times, briefly the doc + code diverge. Acceptable — both land in the same PR.

### Subtasks

- [x] T019 Rewrite `docs/development/org-doctrine-layer-architecture-review.md:481` per occurrence_map dd-007 (English-idiom rewrite) (WP05)
- [x] T020 Rewrite `docs/development/3-2-publication-checklist.md:210` per occurrence_map dd-008 (WP05)
- [x] T021 Rewrite `docs/engineering_notes/reflections/README.md:12` per occurrence_map dd-009 (WP05)
- [x] T022 Rewrite all 5 occurrences in `docs/engineering_notes/finding/2026-05-24-mission-01KSAF14-orchestration-findings.md` (lines 257, 264, 272, 277, 280) per occurrence_map dd-010 through dd-014 — incl. flag-name rewrite at line 280 (WP05)
- [x] T023 `grep -rn 'ceremony' docs/` returns zero hits (WP05)

---

## Work Package 6 — Architectural Regression Guard

**Prompt**: [tasks/WP06-regression-guard.md](tasks/WP06-regression-guard.md)

**Goal**: Add a new architectural test at `tests/architectural/test_no_legacy_terminology.py` that runs a grep over `src/ tests/ docs/` for both forbidden terms ("ceremony", "status-writing") and fails CI if either reappears. Locks in the rename per spec FR-013 + FR-014 and decision `01KSPP3W3VW8GB4WCXFF7J7X1Z`. Excludes `kitty-specs/` historical artifacts and `.worktrees/`. The test must use string-construction tricks (e.g., `"".join(["cere", "mony"])`) to avoid flagging itself.

**Priority**: MUST run last. The test only passes when all preceding WPs have landed.

**Independent test**: From a clean lane workspace where all preceding WPs are merged, `pytest tests/architectural/test_no_legacy_terminology.py` exits 0.

**Dependencies**: WP01, WP02, WP03, WP04, WP05 (must all be merged before WP06's test passes).

**Risks**: The test scans its own file and would fail on its own mentions. Mitigation: build forbidden terms via string concatenation so the literal does not appear in the test source; alternatively exclude the test file from its own scan. Pick the string-construction approach — it's more durable than path exclusions.

### Subtasks

- [ ] T024 Create `tests/architectural/test_no_legacy_terminology.py` with grep-based test functions for "ceremony" and "status-writing"; exclude `kitty-specs/`, `.worktrees/`, `.venv/`, `node_modules/`; build forbidden terms from string fragments to avoid self-flag (WP06)
- [ ] T025 Run new test from lane workspace after preceding WPs are merged; confirm green (WP06)
- [ ] T026 Run full `pytest tests/architectural/` to confirm no regression in existing arch tests (WP06)

---

## Parallelization Plan

```
Phase 1 (parallel):
  ├── WP01 (glossary)
  ├── WP02 (commit_helpers)
  ├── WP03 (test fixtures)
  ├── WP04 (doctrine)
  └── WP05 (docs)

Phase 2 (sequential, after all of Phase 1):
  └── WP06 (regression guard)
```

Lane-based execution can run WP01–WP05 in up to 5 parallel lanes. WP06 must run in its own lane after Phase 1 merges.

## Recommended Implementation Order

1. **Start with WP01** if you want sequential — it's the smallest and unblocks the canonical reference.
2. Or **kick off WP01–WP05 in parallel** if you want maximum throughput.
3. **WP06 last** — the regression guard.
