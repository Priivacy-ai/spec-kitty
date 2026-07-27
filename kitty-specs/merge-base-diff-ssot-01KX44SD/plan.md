# Implementation Plan: Consolidate git merge-base/diff idiom

**Branch**: `fix/merge-base-diff-ssot` | **Date**: 2026-07-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/merge-base-diff-ssot-01KX44SD/spec.md`

## Summary

Extract the **five** independent `git merge-base` → `git diff --name-only` copies (a post-plan brownfield squad corrected 4 → 5) onto one canonical surface in `src/specify_cli/core/vcs/git.py` — two primitives (`git_merge_base`, `git_diff_names`, the latter with optional `pathspec` + `diff_filter`) plus a HEAD-relative convenience (`merge_base_changed_files`) — and repoint the five call sites to it with **zero behaviour change** (NFR-001). The mechanics get direct tests (incl. a non-HEAD branch-target case and a range↔two-arg equivalence assertion); each site keeps a thin integration test. Behaviour-preserving strangler consolidation of a duplicated VCS primitive, per the 3.2.x no-shadow-paths / single-seam discipline.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: standard library only (`subprocess`, `pathlib`); no new third-party dependency. Target home `src/specify_cli/core/vcs/git.py` already exists (`GitVCS` + module-level git helpers).
**Storage**: N/A (operates on a git working tree via subprocess)
**Testing**: `pytest`; direct unit tests for the new helper (subprocess mocked / real temp-repo), thin integration tests retained at each of the 4 call sites. Run under the repo's parallel profile (`PWHEADLESS=1 pytest tests/ -n auto --dist loadfile`).
**Target Platform**: Linux/macOS dev + CI (any platform with `git` on PATH)
**Project Type**: single (Python CLI package under `src/specify_cli/`)
**Performance Goals**: unchanged — same two git subprocess calls per invocation as today; no added shell-outs.
**Constraints**: behaviour-preserving (C-001); no expected-value test assertion edits (NFR-001); ruff + mypy zero-issue, complexity ≤15 (NFR-003); helper new-code coverage ≥ repo gate (NFR-004); only incidental hardening allowed is standardizing `encoding="utf-8", errors="replace", check=False` (C-002).
**Scale/Scope**: 1 new helper surface (~3 functions) + **5 call-site repoints** + 1 secondary tidy (FR-007). ~6 files touched in `src/`, plus their tests. Two touched files are god-modules (`tasks_move_task.py` ~1848 LOC, `acceptance/__init__.py` ~1751 LOC) — repoint only, no scope expansion into their other debt.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`.kittify/charter/charter.md`); plan-action context loaded in `compact` mode (no action-scoped directives returned). Relevant standing orders and how this plan satisfies them:

- **Canonical single authority / no shadow paths** — this mission *is* a consolidation onto one authority; it removes duplication rather than adding a parallel path. ✅ (the whole point)
- **Campsite / brownfield logical-duplication consolidation** — one operation duplicated across 4 sites → one canonical seam. ✅ aligns with the doctrine directly.
- **Tests as scaffold, red-first discipline** — the helper gets direct tests exercising all failure branches; site tests keep observable-contract assertions (not re-proving git mechanics). Behaviour-preserving, so existing behavioural tests stay green unchanged (NFR-001). ✅
- **Architectural gate discipline** — full `tests/architectural/` sweep + terminology guard at closeout; ruff/mypy clean on new + boy-scout scope. ✅ (recorded in tasks)
- **Git/workflow discipline** — PR-bound; lands via PR to origin/main, never direct push. ✅

No charter violations → Complexity Tracking below is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/merge-base-diff-ssot-01KX44SD/
├── plan.md              # This file
├── spec.md              # Committed (cec9b25)
├── research.md          # Phase 0 output (this command)
├── data-model.md        # Phase 1 output (this command)
├── quickstart.md        # Phase 1 output (this command)
├── contracts/           # Phase 1 output (this command)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── core/vcs/git.py                              # + git_merge_base, git_diff_names(pathspec,diff_filter), merge_base_changed_files (NEW surface)
├── lanes/stale_check.py                         # FR-005: replace _git_merge_base/_git_diff_names with helper primitives
├── acceptance/__init__.py                       # FR-008: _changed_workflow_files -> merge_base_changed_files(pathspec=".github/workflows", diff_filter="AMR")  [5th copy]
└── cli/commands/agent/
    ├── tasks_move_task.py                        # FR-002: _mt_pre_review_changed_files -> merge_base_changed_files
    ├── tasks_shared.py                           # FR-003: first pass -> helper (pathspec=kitty-specs/), keep content re-check
    └── tasks_dependency_graph.py                 # FR-004: upstream check -> git_merge_base + git_diff_names(mb, check_branch)  [two-ref, NOT the HEAD convenience]

# FR-007 (secondary): src/specify_cli/review/pre_review_gate.py  # ScopeResult.from_override + retire hand-built construction in tasks_move_task FR-004 override tier

tests/
├── core/vcs/ (or tests/specify_cli/core/vcs/)    # NEW direct helper test (all 5 FR-006 branches)
├── lanes/test_stale_check*.py                     # thin integration retained
└── specify_cli/... (move_task / shared / dependency_graph site tests)  # patch-target repoint only, no expected-value edits
```

**Structure Decision**: single Python package. The canonical surface lives in the existing `core/vcs/git.py` (already the home of git subprocess helpers), keeping the VCS primitive in the VCS module and out of the four consumer modules.

## Complexity Tracking

*No Charter Check violations — none.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Canonical merge-base/diff surface + direct tests

- **Purpose**: Create the single source of truth for the merge-base→changed-files idiom so the git mechanics are defined and proven exactly once.
- **Relevant requirements**: FR-001, FR-006 (helper's own branches), NFR-002, NFR-003, NFR-004, C-002.
- **Affected surfaces**: `src/specify_cli/core/vcs/git.py` (add `git_merge_base`, `git_diff_names` with optional `pathspec` + `diff_filter`, `merge_base_changed_files`); new direct unit test module.
- **Sequencing/depends-on**: none (must land before or with the repoints; they import from it).
- **Mandatory test fences (from post-plan adversarial squad)**: FR-006 must include (1) a **non-HEAD branch-target** case — `git_diff_names(repo, mb, <branch≠HEAD>)` — so a lazy swap of `tasks_dependency_graph` to the HEAD convenience fails red (fences F1, the single most likely silent behaviour change, currently uncaught by any test); (2) a **range↔two-arg equivalence** assertion (helper two-arg output == raw `git diff --name-only <mb>..HEAD` on a real temp repo), documenting the silent rewrite three sites undergo; (3) a `diff_filter` case for the acceptance 5th copy.
- **Risks**: getting the primitive signatures general enough to serve all 5 variants (2-ref vs HEAD-relative merge-base; `..HEAD` vs `..branch` diff target; optional pathspec; optional `--diff-filter`) without a god-signature; standardizing subprocess kwargs (C-002) without altering output.

### IC-02 — Low-risk HEAD/branch repoints

- **Purpose**: Route the two straightforward copies through the surface.
- **Relevant requirements**: FR-002 (`tasks_move_task._mt_pre_review_changed_files` → `merge_base_changed_files`), FR-004 (`tasks_dependency_graph` → `git_merge_base` + `git_diff_names(mb, check_branch)`), NFR-001, C-001.
- **Affected surfaces**: `tasks_move_task.py`, `tasks_dependency_graph.py`. Tests largely survive unedited (global-`subprocess` ordered mocks + symbol-identity batteries; verified by the squad — patch-target edits mostly unnecessary).
- **Sequencing/depends-on**: IC-01.
- **Risks**: **F1 (CONFIRMED)** — `tasks_dependency_graph` diffs `..check_branch`, NOT `..HEAD`; it MUST use the two-ref primitive `git_diff_names(mb, check_branch)`, never the HEAD convenience (which would silently invert which commits are inspected). Named acceptance criterion + the IC-01 branch-target test guard this.

### IC-02b — Higher-touch repoints (isolate for review)

- **Purpose**: The two copies with extra behaviour to preserve get their own reviewable unit with named acceptance criteria.
- **Relevant requirements**: FR-003 (`tasks_shared` two-pass), FR-005 (`stale_check` primitive pair, the only site gaining C-002 encoding/errors + the only site that *deletes* symbols), FR-008 (`acceptance._changed_workflow_files`, the 5th copy with `--diff-filter=AMR` + three-dot), NFR-001, C-001, C-002, C-003.
- **Affected surfaces**: `tasks_shared.py`, `lanes/stale_check.py`, `acceptance/__init__.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: (a) `tasks_shared` — preserve the `startswith("kitty-specs/")` filter, dedup, and FR-007/#2274 content re-check (`tasks_shared.py:~691-705`) **verbatim**; only the diff *call* delegates. (b) `stale_check` — assert real-repo output byte-identical after adopting `encoding/errors` (C-002); deleting `_git_merge_base`/`_git_diff_names` may trip a dead-symbol/architectural guard — update it in-WP. (c) `acceptance` — three-dot `...HEAD` → helper two-arg equivalence is safe only because the merge-base is an ancestor of HEAD; pin it; do NOT expand into the god-module's other debt.

### IC-03 — Secondary: ScopeResult.from_override tidy (deferrable)

- **Purpose**: Retire the hand-built `ScopeResult` construction in `tasks_move_task`'s FR-004 override tier behind a `from_override` classmethod.
- **Relevant requirements**: FR-007.
- **Affected surfaces**: `src/specify_cli/review/pre_review_gate.py`, `tasks_move_task.py` override tier.
- **Sequencing/depends-on**: independent of IC-01/IC-02; may split to a follow-up WP or fast-follow if it widens the diff.
- **Risks**: scope creep — if `from_override` pulls in gate-policy changes it should be deferred, not expanded here. **F7**: `tasks_move_task` carries a `module_defs == set(_MOVE_SET)` symbol-identity guard (`test_tasks_move_task_seam.py:456`); adding/removing any module-level symbol here fails it — keep FR-007 in its own WP so this doesn't masquerade as an unrelated breakage in IC-02.
