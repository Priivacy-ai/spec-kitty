# Implementation Plan: Burn down the 99 grandfathered /tmp-literal test offenders

**Branch**: `fix/tmp-literal-offender-burndown` | **Issue**: Closes #1842 | **Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

## Summary

Sweep the **98 live** (+1 stale) grandfathered `/tmp`-literal test files (`tmp_ratchet_baseline.txt`) off literal `/tmp`: category-A write-leaks → `tmp_path`/fixtures with teardown (real isolation, FR-007 — not `/dev/shm`/`mkdtemp` evasion); category-B path-literals → non-`/tmp` absolute sentinels preserving mock/assertion semantics. Then a single **gate WP** empties the baseline and flips the ratchet from "frozen baseline (>50)" to a self-consistent hard gate (fragment-constructed `/tmp/` needle + `__file__` self-exclude + a positive self-test replacing the `>50` floor). Closes #1842; sibling to the structural PR #2429.

## Technical Context

**Language/Version**: Python 3.11
**Testing**: `pytest` (`tmp_path` fixture), the ratchet `tests/architectural/test_no_tmp_paths_in_tests.py`
**Project Type**: single project — test-suite hygiene sweep + one gate-mechanism change
**Constraints**: NFR-001 (no xfail/skip/delete/loosening); real isolation not evasion (FR-007); `ruff`+`mypy --strict` clean; no new suppressions; gate must not flag itself.
**Scale/Scope**: 98 files across 22 dirs + the ratchet file + the baseline file.

## Critical sequencing (the whole plan hinges on this)

- **Conversion WPs never touch `tmp_ratchet_baseline.txt`.** A file that is still baselined but no longer contains `/tmp/` is simply *skipped* by `_collect_violations` (no violation). So converting files while leaving them baselined keeps the ratchet green throughout, and — crucially — the anti-vacuity `>50` floor never trips mid-sweep. The baseline file is owned solely by the gate WP → no parallel-edit conflicts.
- **The gate WP runs last** (depends on every conversion WP): only once all 98 files are `/tmp`-free can the baseline be emptied and the hard gate turned on without self-failure.

## Charter Check

- **No masking / no weakening** (NFR-001) — real conversions; FR-007 forbids the substring-evasion shortcuts. ✅
- **Non-vacuous / red-first** — the gate's positive self-test flags a synthetic offender; cat-A residue-freedom verified across the set. ✅
- **Canonical sources** — the self-reference fix mirrors the existing `test_no_legacy_terminology.py` pattern (fragment needle + `__file__` exclude), not a new mechanism. ✅
- **No new suppressions**; `ruff`+`mypy --strict` clean. ✅

## Implementation Concern Map → Work Packages

Conversion WPs are grouped by directory to keep each ≤ ~15–18 files and give one owner per file (no overlap). All conversion WPs are independent (parallel); the gate WP depends on all of them.

| WP | Scope | Files | Dep |
| --- | --- | --- | --- |
| WP01 | `tests/specify_cli/` group A (~first 15) | ~15 | — |
| WP02 | `tests/specify_cli/` group B (~remaining 14; **drop stale `cli/commands/test_review.py`**) | ~14 | — |
| WP03 | `tests/sync/` | 13 | — |
| WP04 | `tests/charter/` (7) + `tests/status/` (4) | 11 | — |
| WP05 | `tests/doctrine/` (6) + `tests/agent/` (6) | 12 | — |
| WP06 | `tests/next/` (3) + `runtime/` (2) + `unit/` (3) + `integration/` (3) + `cli/` (3) + `dossier/` (3) + `contract/` (1) | ~18 | — |
| WP07 | `tests/adversarial/` (2) + `audit/` (1) + `auth/` (2) + `core/` (1) + `git_ops/` (1) + `glossary/` (2) + `kernel/` (1) + `paths/` (2) + the 2 non-gate `architectural/` files | ~14 | — |
| WP08 | **Gate**: empty `tmp_ratchet_baseline.txt`; make the gate file **genuinely literal-free (all 14 `/tmp/` lines)** — fragment-construct the `_TMP_LITERAL` needle (:73) AND the self-test payload (:182), **reword** the 9 docstring/comment + 3 assertion-message lines (4,13,22,83,110,133,143,147,170,157,158,185); keep `__file__` self-exclude in `_collect_violations` (belt-and-suspenders); replace `test_baseline_is_non_empty_anti_vacuous` (`>50`) with a positive self-test; add the FR-007 cat-A isolation-adoption check; **assert SC-001's exact grep on the gate file returns 0** | 2 (`test_no_tmp_paths_in_tests.py`, `tmp_ratchet_baseline.txt`) | WP01–07 |

### Per-file method (every conversion WP)
1. Read each baselined file; classify per literal occurrence: **A** (writes under `/tmp` → route through `tmp_path`/fixture with teardown) or **B** (arbitrary absolute path in mock/test-data/assertion → non-`/tmp` POSIX sentinel, e.g. a clearly-fake `/nonexistent/...` or a `tmp_path`-derived string, preserving the exact assertion).
2. Preserve intent (C-001): absolute-path-rejection tests stay absolute-path tests; Windows-literal edge cases keep cross-platform coverage; assertion-message substrings updated in lockstep.
3. Run the file's tests green; confirm no `/tmp/` remains (`grep`), no residue for cat-A.
4. **Do not edit the baseline** (WP08 owns it).

## Project Structure
```
kitty-specs/tmp-literal-offender-burndown-01KWWRW2/  spec · research · plan · tasks
tests/**/<98 offender files>                          # WP01–07 (by dir group)
tests/architectural/test_no_tmp_paths_in_tests.py     # WP08 gate flip
tests/architectural/tmp_ratchet_baseline.txt          # WP08 empty
```
**Structure Decision**: single project; 7 parallel conversion WPs (partitioned by directory, disjoint file ownership) + 1 dependent gate WP.
