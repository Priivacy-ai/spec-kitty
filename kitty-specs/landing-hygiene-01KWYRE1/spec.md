# Mission Specification: Landing hygiene — review-prompt retention + coverage-allowlist guard

**Status**: Draft
**Issues**: Closes #2439, Closes #2443

Two small, independent landing-followup fixes surfaced by the epic #1931 landings. Independent WPs; one cross-fork draft.

## User Scenarios & Testing *(mandatory)*

**Primary actors**: (a) a contributor whose repo accumulates unbounded per-invocation review-prompt files (#2439); (b) a maintainer relying on the internal `diff-coverage` gate whose critical-path allowlist has silently gone stale (#2443).

**Grounding** (confirmed against the live repo):
- **#2439**: `src/specify_cli/review/prompt_metadata.py` — `review_prompt_path()` (~:108) writes each review invocation to `<tmpdir>/spec-kitty-review-prompts/<repo-id>/<mission-slug>/<wp-id>/<invocation-id>.md` via `write_review_prompt_with_metadata()` (~:163). The cross-repo collision was fixed by #959 (`<repo-id>` = `safe_repo_identifier`); the residual (LC-7) is that **within a repo these accumulate with no retention cap or cleanup**.
- **#2443**: `.github/workflows/ci-quality.yml:2709` lists `'src/specify_cli/core/mission_detection.py'` in the `diff-coverage` `--include` critical-path allowlist — but that file **never existed anywhere in git history** (post-spec squad, verified across all commits): the entry is **bogus/aspirational, not merely moved**. The lost logic is **branch-based mission-slug detection** (`git-operations-matrix.md:28`: `core/mission_detection.py::_detect_from_branch()`); its real **defining home**, verified by the squads, is `src/specify_cli/lanes/branch_naming.py::parse_mission_slug_from_branch` (the definition at :778 — `core/vcs/detection.py:158` only *imports/consumes* it, and `branch_naming.py` is itself absent from the allowlist) — **NOT** `acceptance/__init__.py::detect_mission_slug`, which does *no* auto-detection ("Require an explicit mission slug"). A dangling entry silently contributes nothing to critical-path enforcement — the fix determines the intended path, not just deletes. **Existing infra to reuse**: `tests/architectural/_gate_coverage.py::_diff_cover_critical_paths()` (:442) already parses this allowlist; `test_workflow_coherence.py:231` + `test_ci_quality_path_filters.py:205` iterate it. **A SECOND hardcoded authority exists** (post-plan squad): `tests/release/test_diff_coverage_policy.py:275` lists the same phantom entry in its own `critical_path_modules` copy and asserts membership — editing `ci-quality.yml` reds it, so it MUST be updated in lockstep (per its own precedent, lines 279–282).

### User Story 1 — Review-prompt files don't grow unbounded (Priority: P2) — #2439
As a contributor, I want the per-invocation review-prompt files to be capped/cleaned so they don't accumulate forever within my repo.
**Independent test**: after N+K review invocations for a given (repo, mission, WP), at most the retained set remains on disk; older ones are pruned; no active-invocation file is deleted.

### User Story 2 — The coverage allowlist can't silently rot (Priority: P2) — #2443
As a maintainer, I want the `diff-coverage` `--include` allowlist refreshed to the module's current path AND a guard that every allowlist entry resolves to an existing file, so a moved/renamed module can't silently drop coverage enforcement again.
**Independent test**: the guard fails (red) against the current stale entry and passes after the allowlist is corrected; the corrected allowlist references only existing files.

### Edge Cases
- **#2439 retention must not delete a live invocation's own file** (the one currently being written/read). Prune by age or count, newest-preserving; the current invocation is always retained.
- **#2443**: determine where the mission-detection logic actually lives now — update the entry to the correct current path if the critical-path intent still holds, or **remove** the entry if that logic folded into an already-listed file (don't invent a path). The guard verifies existence; the allowlist's *intent* (which paths are critical) is a human call — preserve it.
- The guard should run in the same CI surface that enforces the gate (or as an architectural test), not only locally.

## Requirements *(mandatory)*

### Functional Requirements
| ID | Title | User Story | Priority | Status |
| --- | --- | --- | --- | --- |
| FR-001 | Review-prompt retention cap + cleanup | US1 — bound the per-invocation review-prompt files within a repo (by count and/or age, newest-preserving) and prune the excess on write, in `review/prompt_metadata.py`. Never delete the current invocation's file. | Medium | Open |
| FR-002 | Retention is configurable + safe-by-default | US1 — a sensible default cap; the cleanup is best-effort (a prune failure must never break a review) and scoped to the `spec-kitty-review-prompts/<repo-id>/…` tree only. | Medium | Open |
| FR-003 | Correct the bogus entry (recorded determination) + update both authorities in lockstep | US2 — name the file that **DEFINES** the mission-detection logic (`lanes/branch_naming.py::parse_mission_slug_from_branch`; `core/vcs/detection.py` is a consumer) and either **add that critical path** or **remove the entry** with a **PR-recorded determination that names the already-listed critical path which covers it** (objective, not free-text; **bare removal without that proof forbidden**). Update BOTH authorities in lockstep: `ci-quality.yml`'s `--include` AND the hardcoded copy in `tests/release/test_diff_coverage_policy.py`. | Medium | Open |
| FR-004 | Existence guard (glob-aware) — via the canonical parser | US2 — a guard **reusing** `_gate_coverage.py::_diff_cover_critical_paths` that, per `--include` entry: a **glob** (`*`) → expand via `Path.glob`, assert **≥1 match** (this also catches a vacuous glob that matches zero files — the `src/specify_cli/next/*` rot precedent); a **literal** → assert `.exists()`. Red-first evidence must show it reds **specifically on `mission_detection.py`** (named in the failure), not on unexpanded globs. Land alongside the existing critical_paths tests; no hand-rolled second parser. | Medium | Open |

### Non-Functional Requirements
| ID | Title | Requirement | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | No behavior regression | The retention change must not alter review-prompt *content*, metadata, or the path scheme (#959's `<repo-id>` isolation stays intact); the allowlist change must not weaken which paths are critical-path-enforced (only fix the stale reference). | Reliability | High | Open |
| NFR-002 | Cleanup is fail-safe | A cleanup/prune error is swallowed (logged, not raised) — review must never fail because of retention housekeeping. | Reliability | High | Open |

### Constraints
| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | Two independent WPs | #2439 (retention) and #2443 (allowlist guard) share no files — parallelizable, no ordering. | Technical | High | Open |
| C-002 | Quality gates | `ruff` + `mypy --strict` clean on new Python; red-first proof for both fixes; no suppression/ratchet; terminology guard clean. | Technical | High | Open |

### Key Entities
- **`src/specify_cli/review/prompt_metadata.py`** — the review-prompt writer (#2439 retention).
- **`.github/workflows/ci-quality.yml`** (`diff-coverage` `--include`) — the critical-path allowlist (#2443).
- **`_gate_coverage.py::_diff_cover_critical_paths`** — the existing canonical allowlist parser the guard reuses (#2443, FR-004); the guard lands alongside `test_workflow_coherence.py`/`test_ci_quality_path_filters.py`.

## Success Criteria *(mandatory)*
- **SC-001**: After exceeding the cap, the review-prompt tree for a (repo, mission, WP) retains only the intended set; the current invocation's file is never pruned; a prune failure does not fail the review (NFR-002).
- **SC-002**: The `diff-coverage` `--include` allowlist references only existing files; the guard (reusing `_diff_cover_critical_paths`) is red against the pre-fix dangling entry and green after. **The PR records the concrete determination** of where the mission-detection logic lives + that no critical-path coverage is silently dropped (no bare removal without proof).
- **SC-003**: No path-scheme/metadata change for review prompts (NFR-001); no weakening of critical-path enforcement; `ruff`+`mypy` clean; no suppression.

## Out of Scope
- The cross-repo review-prompt collision (already fixed by #959).
- Any broader review-prompt redesign or a global GC daemon.
- The contract-ownership boundary (#2441 — separate design-first mission).

## Assumptions
- The mission-detection logic's current home is discoverable in `src/` (the implementer locates it for FR-003).
- A count/age retention cap is acceptable UX (no need for user-configurable policy beyond a safe default).
