---
verdict: approved
reviewer: reviewer-renata
cycle: 1
---

# WP00 Review — Cycle 1 (reviewer-renata)

**Verdict: APPROVED on technical merits.** All WP00 Definition-of-Done criteria
are met and independently re-verified (including a live non-vacuity re-check
performed by the reviewer). The `approved` lane transition is currently blocked
ONLY by the mission-level issue-matrix gate (a fill-once orchestrator
responsibility, NOT a WP00 defect) — see "Remaining gate" below. WP00 must NOT
be rejected to `planned`: there is no implementation defect to fix.

Profile/doctrine applied: reviewer-renata; DIRECTIVE_041 (tests-as-scaffold —
content-anchored ratchet keys, no vacuous guards), DIRECTIVE_024 (locality of
change), DIRECTIVE_030 (test/typecheck gate); tactics
test-scaffolding-as-design-smell, delete-the-assertion-not-the-test.

## Per-criterion findings

1. **Behavior preservation — PASS.** Detection logic
   (`_scan_source` token matchers, the `_find_raw_bypasses` AST walk),
   baseline literals, and the *set* of flagged offenders are unchanged. Only
   the allow-list KEY representation moved from `file:line` to the existing
   `(qualname, token_line)` composite (`_ratchet_keys.composite_key` /
   `composite_key_from_file`). `_Finding` gained a `source` field threaded from
   the already-in-scope scan source (no per-finding re-read).

2. **Non-vacuity — PASS (RE-VERIFIED LIVE BY REVIEWER, not trusting the WP note).**
   - File 1 (`test_no_write_side_rederivation.py`): reviewer planted
     `return coord_branch or _current_branch(repo_root)` inside
     `_ensure_spec_kitty_exclude` (core/worktree.py) — a DIFFERENT qualname but
     a token_line **byte-identical** to the single allow-listed entry (whose
     composite is `('_resolve_write_target', 'return coord_branch or _current_branch ( repo_root )')`).
     `test_adopted_modules_have_no_write_side_rederivation` went **RED** (flagged
     `worktree.py:36 [write_target_head_selector]`), proving `qualname` is a
     load-bearing component — a token_line-only key would have over-matched and
     silently exempted this offender. Reverted → GREEN.
   - File 2 (`test_single_mission_surface_resolver.py`): reviewer planted
     `return repo_root / KITTY_SPECS_DIR / mission_slug` in non-allowlisted
     worktree.py. `test_zero_functional_raw_bypass_on_collapsed_tree` went
     **RED** with the correct composite key
     `('_planted_raw_bypass', 'return repo_root / KITTY_SPECS_DIR / mission_slug')`.
     Reverted → GREEN.
   - Working tree confirmed clean after both reverts (`git status --short` empty).

3. **No hand-authored keys — PASS.** File 1 derives every key live via
   `_composite_key_for_seed(...)` over `_ALLOW_LIST_SEED`. File 2 derives via
   `_build_allowlisted_raw_joins()` calling `composite_key_from_file` over
   `_RAW_JOIN_SITES`. Zero hand-written `(qualname, token_line)` literals (NFR-004).

4. **Intent preserved — PASS.** `test_allow_list_is_line_scoped_not_a_blanket_file_escape`
   re-expressed for the composite shape (asserts a 2-tuple of non-empty strs,
   token_line non-empty — anti-blanket-escape intent intact, paula SF-2).
   `test_allow_listed_line_is_the_deferred_head_selector` preserved and
   strengthened (resolves composite back to live token_line; asserts the seed
   key is still in `_ALLOW_LIST`). DIAG/TBYD rationale strings and the carve-out
   entries (`surface_resolver.py:472/477`, `cycle.py:185`,
   `_read_path_resolver.py:885`, `mission_creation.py:328`) preserved verbatim.

5. **Dup deleted — PASS (with a minor non-blocking note).** The duplicated
   `_code_tokens_by_line` is deleted; the module now imports `code_tokens_by_line`
   from `_ratchet_keys`. Dead `import io`/`import tokenize` removed. The only
   remaining textual match for `_code_tokens_by_line` in `tests/` is a *prose*
   mention in `_ratchet_keys.py`'s docstring (line 26) describing the dup it
   consolidated — now slightly stale ("intentionally stays private"). This is a
   cross-file docstring narrative, NOT a code reference, and `_ratchet_keys.py`
   is outside WP00's owned files (editing it would expand scope, DIR-024).
   Non-blocking; suggest a one-line docstring tidy in a later touch of that file.

6. **Gates — PASS.** Both guard files: 25 passed. ruff clean (exit 0). mypy:
   "Success: no issues found in 2 source files". Full `tests/architectural/`:
   **428 passed, 1 failed**. The single failure
   (`test_pytest_marker_convention.py::test_support_helper_tree_is_exempt_from_marker_convention`)
   is genuinely pre-existing: that test file is byte-identical between lane base
   (`887d5b6d5`) and lane tip, WP00 does not touch it, and it fails on a
   discovery assertion ("expected the checker to find at least one candidate
   file") unrelated to ratchet keys. Confirmed independent of this diff.

7. **Scope — PASS.** Test-only; exactly the 2 owned files changed
   (`test_no_write_side_rederivation.py`, `test_single_mission_surface_resolver.py`);
   zero `src/` change; no `discover_rows()`/`audit.py` edit; no
   mutation/floor/selection-test edits; no reformat beyond touched lines (#1970).

## Remaining gate (orchestrator action, not a WP00 fix)

`spec-kitty agent tasks move-task WP00 --to approved` is blocked by the
issue-matrix acceptance gate: `issue-matrix.md` rows are all placeholder
(`unknown`) and the gate additionally requests rows for `#1619, #2008, #2069,
#2070`. Filling 25 issue verdicts requires the whole-mission WP→issue mapping
and is the orchestrator's fill-once responsibility — it is out of WP00's
test-only scope and cannot be substantiated from a per-WP review. Once the
matrix is filled (most issues `in-mission`, terminal before mission `done`),
re-run the approve; the WP00 technical review already passes.
