---
work_package_id: WP04
title: Sonar regex hotspots + wall-clock tests
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-008
- FR-013
planning_base_branch: fix/quality-check-updates
merge_target_branch: fix/quality-check-updates
branch_strategy: Planning artifacts for this mission were generated on fix/quality-check-updates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/quality-check-updates unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1134116"
history:
- at: '2026-05-14'
  actor: planner
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/release/
execution_mode: code_change
mission_id: 01KRJGKH4DJCSF277K9QV3WBE7
mission_slug: quality-devex-hardening-3-2-01KRJGKH
owned_files:
- src/specify_cli/release/changelog.py
- tests/regressions/test_changelog_regex_redos.py
- kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP04.md
- kitty-specs/quality-devex-hardening-3-2-01KRJGKH/sonar-hotspot-rationales.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else below, load the assigned agent profile so your behavior, boundaries, and governance scope match the role:

```
/ad-hoc-profile-load python-pedro
```

The profile establishes your identity (Python Pedro). Load the assigned profile before touching code; do not improvise the role.

## Objective

Apply the pre-mission `secure-regex-catastrophic-backtracking` tactic (commit `380db5c2e`) to the regex hotspots in `src/specify_cli/release/changelog.py`. Each regex change carries a wall-clock regression test asserting completion in ≤ 100 ms on adversarial input (FR-008). Record Sonar rationale annotations so the hotspot review percentage moves toward 100 %.

## Context

### Sonar findings to address (this WP)

- `release/changelog.py:147` area — `python:S5852` / `python:S6353` flagged in `work/findings/595-sonar-coverage-debt.md`. The issue body of #595 explicitly names "regex backtracking warnings in `src/specify_cli/release/changelog.py`" as an actionable hotspot.

### Tactic summary (binding)

The `secure-regex-catastrophic-backtracking` tactic at `src/doctrine/tactics/shipped/secure-regex-catastrophic-backtracking.tactic.yaml` codifies:

1. Three dangerous repetition shapes (nested ambiguous quantifier; consecutive non-possessive repetitions; partial-match without anchor).
2. A rewrite ladder: bound quantifier → refactor nested → possessive / atomic group (Python 3.11+) → negated char class.
3. Escape hatches when linear rewrite is impossible: drop the regex, use RE2 via the `re2` package, multi-pass, bounded-input cap.
4. **Wall-clock regression test required for every fix.**

## Doctrine Citations

This WP applies:

- [`secure-regex-catastrophic-backtracking`](../../../src/doctrine/tactics/shipped/secure-regex-catastrophic-backtracking.tactic.yaml) — every regex change.
- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — the regression test asserts completion-within-budget as the observable outcome.

## Branch Strategy

- Planning / base branch: `fix/quality-check-updates`.
- Final merge target: `fix/quality-check-updates`.

## Subtasks

### T018 — Audit `release/changelog.py` regexes against the dangerous-shapes table

**Purpose**: Classify each regex in the file against the tactic's three dangerous shapes. Pedro must NOT proceed to rewrite until classification is recorded.

**Steps**:

1. List every regex literal in `src/specify_cli/release/changelog.py`:
   ```bash
   rg -n "re\.(compile|match|search|split|findall|sub|fullmatch)" src/specify_cli/release/changelog.py
   ```
2. For each match, classify the pattern against the four conditions in the tactic's step 1:
   - Nested ambiguous repetition (`(r)*` with `r` having multiple matches)
   - Consecutive non-possessive repetitions (`a*a*`, `.*_.*`)
   - Partial-match API on an unanchored regex
   - Adversarial-tail full-match
3. Record the classification in a top-of-WP audit note (commit as a comment block at the top of the regression test file, or as an audit table in the WP evidence).

**Validation**:

- Every regex in `release/changelog.py` has a classification line.
- The classification cites the tactic's shape number (1, 2, 3, or 4).

### T019 — Apply the rewrite ladder for each vulnerable pattern

**Purpose**: Make each flagged regex linear-time or document the bounded-input cap.

**Steps**:

1. For each vulnerable pattern from T018, apply the rewrite ladder in order:
   - Option 1: **Bound the quantifier.** Replace `+` / `*` with `{1,N}` where `N` is the maximum legitimate input size. Comment the bound's rationale.
   - Option 2: **Refactor nested quantifiers.** Pattern like `(ba+)+` is safe; `(a+)+` is not — rewrite so the inner group has exactly one way to match.
   - Option 3: **Possessive / atomic group.** Python 3.11+ supports `a++`, `a*+`, `(?>a*)`. Use these where rewrite (1) and (2) are infeasible.
   - Option 4: **Negated character class.** `.*_.*` → `[^_]*_.*` (linearizes the first repetition).
2. If no ladder option is viable, switch to a non-regex implementation (string ops, multi-pass) or to `re2` import (under the localized `# type: ignore[import-untyped]` per WP01's research).
3. Validate each rewrite preserves match semantics on the happy-path corpus — write a happy-path correctness test that exercises legitimate inputs and asserts the output equals the pre-rewrite output.

**Files**: `src/specify_cli/release/changelog.py` (modified, ~5–20 lines per regex change).

**Validation**:

- Every flagged regex is rewritten to linear time or has a documented bounded-input cap.
- Happy-path correctness tests pass before and after the rewrite (the rewrite preserves semantics).

### T020 — Wall-clock regression test in `tests/regressions/test_changelog_regex_redos.py`

**Purpose**: FR-008 contract — every regex change carries a wall-clock test that fails today on a vulnerable pattern and passes after the rewrite.

**Steps**:

1. Create `tests/regressions/test_changelog_regex_redos.py`.
2. For each rewritten regex, author a test:
   ```python
   import time
   import pytest
   from specify_cli.release.changelog import <function-using-the-regex>

   ADVERSARIAL_INPUT = "a" * 100_000 + "X"  # tune to the regex shape

   def test_<regex_function>_completes_in_linear_time():
       start = time.perf_counter()
       result = <function>(ADVERSARIAL_INPUT)
       elapsed = time.perf_counter() - start
       assert elapsed < 0.1, f"regex took {elapsed*1000:.1f}ms — should be <100ms on linear regex"
       # Optionally assert on result shape if it's stable enough
   ```
3. Tune the adversarial input to each regex's shape (a run of the ambiguous character + a mismatching tail).
4. Run the test **with the pre-rewrite regex** (locally, via git stash) — it MUST hang or fail. Document this in the WP evidence.

**Files**: `tests/regressions/test_changelog_regex_redos.py` (new, ~80–150 lines).

**Validation**:

- Test passes against the rewritten code with `elapsed < 0.1`.
- Test fails against the pre-rewrite code (verified locally; the failure is the proof that the regex was actually vulnerable).

### T021 — Draft Sonar hotspot rationales for operator to apply

**Purpose**: Move `new_security_hotspots_reviewed` toward 100 %. Each remediated hotspot needs a Sonar UI annotation citing the code fix. Sonar UI write access lives with the operator (HiC), not the implementing agent.

**Steps**:

1. For each Sonar regex hotspot Pedro touched, draft a one-paragraph rationale citing:
   - The commit hash of the rewrite.
   - The rewritten regex shape and which tactic-ladder option was applied.
   - The wall-clock regression-test name.
2. Append the drafted rationales to `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/sonar-hotspot-rationales.md` (create if not present) under a `## Regex hotspots` heading.
3. **Hand off to operator**: the WP's commit message includes a "Sonar handoff:" block listing each hotspot ID and the file path of the draft rationale; the operator applies the rationale in the Sonar UI as part of the mission-merge review.

**Files**: `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/sonar-hotspot-rationales.md` (new or appended).

**Validation**:

- Each regex hotspot Pedro touched has a draft rationale in the file.
- WP07 will verify the operator applied them once the gate state is holistically green.

### T022 — Glossary fragment for "catastrophic backtracking"

**Purpose**: FR-013.

**Steps**:

1. Author `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP04.md` with entry:
   - **`catastrophic backtracking`**: "A regular-expression engine failure mode in which a vulnerable pattern combined with adversarial input drives matching time into exponential or polynomial complexity. The `secure-regex-catastrophic-backtracking` tactic codifies the prevention rules. Synonym 'ReDoS' is acceptable only as a parenthetical." Confidence 0.95. Status active.
2. Stage and commit.

**Files**: `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP04.md` (new, ~10 lines).

## Test Strategy

- **Wall-clock regression test** for every rewritten regex (T020). Test asserts the completion-within-budget — the observable outcome.
- **Happy-path correctness test** for every rewritten regex (T019). Asserts the rewrite preserves match semantics on legitimate inputs.
- No structural assertions; no mock-call assertions.

## Definition of Done

- [ ] Every regex in `release/changelog.py` is classified against the dangerous-shapes table.
- [ ] Every vulnerable regex is rewritten per the tactic's ladder, or documented with a bounded-input cap.
- [ ] `tests/regressions/test_changelog_regex_redos.py` covers each rewrite with a wall-clock budget test.
- [ ] Each test passes (`< 100 ms` for `100_000`-char adversarial input) against the rewritten code.
- [ ] Sonar hotspot annotations recorded for every regex-related hotspot in `release/changelog.py`.
- [ ] `glossary-fragments/WP04.md` carries the "catastrophic backtracking" entry.
- [ ] Existing test suite remains green.

## Risks

- **A rewrite changes match semantics.** The wall-clock test catches performance regressions, NOT correctness regressions. The happy-path correctness test (authored alongside the rewrite) is the safeguard.
- **The 100 ms budget is too tight on a slow CI runner.** Tune to `< 0.5` seconds if a flaky run materializes; document the loosening in the test docstring.
- **Sonar UI annotation requires authentication.** If the operator cannot annotate directly, record the rationale text in the WP evidence and ask the maintainer with Sonar admin rights to apply it.

## Reviewer Guidance

When reviewing this WP, check:

1. Every rewritten regex has both a wall-clock test AND a happy-path correctness test. Reject if the rewrite has no correctness assertion.
2. The rewrite cites a specific tactic ladder step in a code comment (e.g. `# secure-regex tactic, ladder option 2 (bound quantifier)`).
3. No regex was "fixed" by simply switching to `re2` without first attempting the ladder options. Document why each option failed if `re2` is used.
4. The wall-clock budget is reasonable (≤ 100 ms for 100 000-char inputs is the default; ≤ 500 ms acceptable on slow CI).

## Implementation command

```bash
spec-kitty agent action implement WP04 --agent claude
```

## Activity Log

- 2026-05-14T09:33:40Z – claude:sonnet:python-pedro:implementer – shell_pid=1129826 – Started implementation via action command
- 2026-05-14T09:42:36Z – claude:sonnet:python-pedro:implementer – shell_pid=1129826 – Ready: T018 audit found changelog.py has ZERO active regexes (all 3 Sonar-flagged patterns already fixed in commit 4e94c341f / PR #592 before this mission). Wall-clock regression test (T020) guards against re-introduction: 3 adversarial tests + 17 correctness tests, all <20ms vs 100ms budget. Happy-path correctness corpus preserved. Sonar rationales drafted in sonar-hotspot-rationales.md for operator UI application (3 changelog hotspots Safe + 2 cosmetic S6353 Safe + loopback/review-lock deferred to WP07). Glossary fragment authored for 'catastrophic backtracking' (FR-013). Pre-existing test failure test_strict_exits_0_on_success is unrelated to WP04.
- 2026-05-14T09:43:32Z – claude:opus:reviewer-renata:reviewer – shell_pid=1134116 – Started review via action command
- 2026-05-14T09:45:20Z – claude:opus:reviewer-renata:reviewer – shell_pid=1134116 – Approved: pre-mission PR #592 (commit 4e94c341f) already removed the regex hotspots in release/changelog.py; WP04 adds defensive wall-clock regression tests (3 perf + 17 correctness, all green, slowest 0.01s) as future-regression guard per secure-regex-catastrophic-backtracking tactic; Sonar rationales drafted for operator UI application (Safe verdict for 3 hotspots: 1x S5852 + 2x S6353 documented with verbatim paste-ready text); glossary fragment 'catastrophic backtracking' (confidence 0.95, status active) added on planning branch with tactic citation; function-over-form-testing audit clean (elapsed-budget + return-value assertions only, no mock/structural assertions); no locality violations on cycle.py / mission_state.py (WP04 modified zero source files). NOTE: test_strict_exits_0_on_success pre-existing failure flagged 3x now -- propose follow-up sub-WP or WP07 absorption.
