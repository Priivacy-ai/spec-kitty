# Implementation Plan: Landing hygiene — review-prompt retention + coverage-allowlist guard

**Branch**: `fix/landing-hygiene` | **Mission**: `landing-hygiene-01KWYRE1`
**Spec**: `kitty-specs/landing-hygiene-01KWYRE1/spec.md`

## Summary
Two small, independent landing-followup fixes surfaced by epic #1931. No shared files → two parallel WPs.

## Technical Context
**Language/Version**: Python 3.11 (repo pinned)
**Primary Dependencies**: `pathlib`/`os` (retention prune, #2439); `tests/architectural/_gate_coverage.py::_diff_cover_critical_paths` (the canonical `--include` allowlist parser to reuse, #2443); `pytest` (`architectural` marker); GitHub Actions `ci-quality.yml`
**Storage**: `<tmpdir>/spec-kitty-review-prompts/<repo-id>/…` (the review-prompt tree — the only tree the prune touches); flat committed `ci-quality.yml`
**Testing**: unit tests for the retention prune (count/age, current-invocation-preserved, fail-safe); an existence guard added alongside `test_workflow_coherence.py`/`test_ci_quality_path_filters.py`, red-first against the dangling entry
**Target Platform**: local + CI
**Project Type**: single project — two independent hygiene fixes (no product-surface change)
**Performance Goals**: N/A — prune is best-effort O(files-in-one-WP-dir); the guard is a static parse
**Constraints**: prune must never delete the current invocation's file, never raise (NFR-002); #959's `<repo-id>` path scheme unchanged (NFR-001); #2443 fix records a determination + forbids bare removal without proof of coverage; reuse the canonical parser, no hand-rolled second parser; `ruff`+`mypy` clean; no suppression
**Scale/Scope**: `src/specify_cli/review/prompt_metadata.py` + its tests (#2439); `.github/workflows/ci-quality.yml` (`--include` allowlist) + the existence guard test (#2443)

## Charter Check
Two low-blast hygiene fixes; canonical-source discipline (reuse `_diff_cover_critical_paths`), no ratchet/suppression, red-first — charter-aligned.

## Implementation Concerns

### IC-01 — Review-prompt retention cap + cleanup (FR-001/FR-002) — #2439
- **Surface**: `src/specify_cli/review/prompt_metadata.py` — add a bounded prune invoked from `write_review_prompt_with_metadata()` after a successful write.
- **Approach**: after writing invocation `<id>.md` under `spec-kitty-review-prompts/<repo-id>/<mission>/<wp>/`, prune that WP dir to a **default cap** (newest-preserving, by count and/or mtime age), **never** deleting the just-written current-invocation file. The prune is **best-effort**: any error is swallowed (logged, not raised) so a review never fails on housekeeping (NFR-002). Path scheme + metadata unchanged (NFR-001).
- **Tests**: exceed the cap → only the retained set remains; the current invocation is never pruned; a simulated prune error (e.g. permission) does not raise / does not break the write.

### IC-02 — Correct the bogus allowlist entry + existence guard (FR-003/FR-004) — #2443
- **Determination first (FR-003)**: the entry `src/specify_cli/core/mission_detection.py` never existed; its logic is branch-based detection, **defined** at `src/specify_cli/lanes/branch_naming.py::parse_mission_slug_from_branch` (`core/vcs/detection.py` is a *consumer* that imports it; NOT `acceptance/__init__.py::detect_mission_slug`, which does no detection). Either (a) add the correct critical path if genuinely critical-path + unlisted, or (b) remove the bogus entry **and record in the PR** that the logic is covered by an existing allowlisted path. Bare removal without recorded proof is forbidden.
- **Lockstep second authority**: `tests/release/test_diff_coverage_policy.py:275` hardcodes the same phantom entry in its own `critical_path_modules` list + asserts membership — it MUST be updated in the same commit (per its own precedent, lines 279–282) or it reds when `ci-quality.yml` is edited.
- **Guard (FR-004)**: add an existence assertion — for every entry `_diff_cover_critical_paths(ci_quality.yml)` returns, the path exists on disk — **reusing that canonical parser** (do not re-parse the bash array). Land it alongside `test_workflow_coherence.py`/`test_ci_quality_path_filters.py`. Red-first against the current dangling entry, green after IC-02's correction.

## Project Structure (files touched)
```
src/specify_cli/review/prompt_metadata.py       # IC-01: retention prune
tests/specify_cli/review/test_prompt_retention.py  # IC-01: NEW retention tests
.github/workflows/ci-quality.yml                # IC-02: correct the --include allowlist entry
tests/release/test_diff_coverage_policy.py      # IC-02: update the hardcoded critical_path_modules copy in lockstep
tests/architectural/test_ci_quality_path_filters.py  # IC-02: NEW existence guard (reuses _diff_cover_critical_paths)
```

## Key Decisions
- **Retention default** (IC-01): a safe newest-preserving cap; current-invocation always kept; prune is fail-safe (swallow errors).
- **No bare removal** (IC-02): #2443's entry never existed → the fix records where the logic lives; removal only with proof of existing coverage.
- **Canonical parser reuse** (IC-02): the guard consumes `_diff_cover_critical_paths`, not a second hand-rolled parser (charter).
