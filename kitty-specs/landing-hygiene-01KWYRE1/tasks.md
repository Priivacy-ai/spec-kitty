# Tasks: Landing hygiene — review-prompt retention + coverage-allowlist guard

**Mission**: `landing-hygiene-01KWYRE1` | **Branch**: `fix/landing-hygiene`

2 independent work packages (no shared files) — parallelizable.

## Subtask Index
| ID | Description | WP | Parallel |
| --- | --- | --- | --- |
| T001 | Retention cap + fail-safe prune in `review/prompt_metadata.py` | WP01 | [P] |
| T002 | Retention tests (cap, current-invocation-preserved, fail-safe) | WP01 | [P] |
| T003 | Determine mission-detection home + correct the allowlist in both authorities | WP02 | [P] |
| T004 | Existence guard reusing `_diff_cover_critical_paths` (red-first) | WP02 | [P] |

## WP01 — Review-prompt retention (#2439) — P2
Goal: cap + clean up per-invocation review-prompt files within a repo; never delete the current invocation's file; fail-safe. FR-001, FR-002, NFR-001, NFR-002.
- [ ] T001 Add a bounded, newest-preserving prune to `write_review_prompt_with_metadata()` — default cap, best-effort (swallow errors), scoped to `spec-kitty-review-prompts/<repo-id>/…`, never deletes the just-written file (WP01)
- [ ] T002 Tests: exceed cap → only retained set remains; current invocation never pruned; simulated prune error does not raise/break the write (WP01)
**Independent test**: after N+K invocations for a (repo,mission,WP), only the retained set remains; a prune error doesn't fail the review.

## WP02 — Coverage-allowlist determination + guard (#2443) — P2
Goal: correct the phantom `mission_detection.py` allowlist entry (recorded determination, no bare removal) across BOTH authorities + add an existence guard reusing the canonical parser. FR-003, FR-004, NFR-001.
- [ ] T003 Determine the real home (`core/vcs/detection.py::parse_mission_slug_from_branch`); add the correct critical path OR remove with a PR-recorded coverage determination; update BOTH `ci-quality.yml` `--include` AND the hardcoded copy in `tests/release/test_diff_coverage_policy.py` in lockstep (WP02)
- [ ] T004 Existence guard reusing `_gate_coverage.py::_diff_cover_critical_paths` (every `--include` entry exists on disk), landed alongside `test_ci_quality_path_filters.py`/`test_workflow_coherence.py`; red-first against the phantom entry (WP02)
**Independent test**: the guard reds against the pre-fix phantom entry, greens after; `test_diff_coverage_policy.py` stays green (lockstep).

**MVP**: either WP (both small). **Dependencies**: none — WP01 ∥ WP02.
