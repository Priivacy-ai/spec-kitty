---
affected_files:
- path: src/specify_cli/cli/commands/review/ERROR_CODES.md
- path: src/specify_cli/cli/commands/review/_dead_code.py
- path: src/specify_cli/cli/commands/review/_diagnostics.py
- path: src/specify_cli/cli/commands/review/_report.py
- path: tests/specify_cli/cli/commands/review/baselines/issue_2987_red_first.md
- path: tests/specify_cli/cli/commands/review/test_dead_code_baseline.py
- path: tests/specify_cli/cli/commands/review/test_diagnostic_codes_documented.py
- path: tests/specify_cli/cli/commands/test_review.py
cycle_number: 3
mission_slug: annoying-bugs-sweep-01KYHQ9F
reproduction_command: 'git archive HEAD | tar -x -C $SCRATCH && python -c "p=Path(''$SCRATCH/src/specify_cli/cli/commands/review/_dead_code.py''); p.write_text(p.read_text().replace(GOOD_PREDICATE, CYCLE1_BUGGY_PREDICATE))" && cd $SCRATCH && PWHEADLESS=1 PYTHONPATH=$SCRATCH/src python -m pytest tests/specify_cli/cli/commands/review/test_dead_code_baseline.py -q -p no:cacheprovider'
reviewed_at: '2026-07-27T15:01:52Z'
reviewer_agent: claude
verdict: approved
wp_id: WP02
---

# WP02 Review Cycle 2 — recorded as artifact 3

**Verdict**: Approved

## Why this artifact is numbered 3

This is the genuine, independent **cycle-2** review of WP02. It is recorded under the
`review-cycle-3.md` filename because the `review-cycle-2.md` slot was already occupied
before any cycle-2 review took place.

`review-cycle-2.md` is **not** an independent second rejection. Verified by direct diff:

```text
$ diff review-cycle-1.md review-cycle-2.md
0a1,11
> ---
> affected_files: []
> cycle_number: 2
> mission_slug: annoying-bugs-sweep-01KYHQ9F
> reproduction_command:
> reviewed_at: '2026-07-27T14:26:40Z'
> reviewer_agent: unknown
> verdict: rejected
> wp_id: WP02
> ---
>
```

`review-cycle-2.md` is cycle-1's **body verbatim** (73 lines, byte-identical) plus an
11-line machine-generated header block: a 10-line YAML frontmatter stanza with
`reviewer_agent: unknown`, `verdict: rejected`, `cycle_number: 2`, empty `affected_files`,
and empty `reproduction_command`, followed by one blank line. No reviewer rejected WP02 at
cycle 2. Both prior artifacts are preserved unmodified as the historical record.

### Root cause worth capturing

An **approving** review currently writes no verdict artifact. So when a WP is rejected at
cycle N and passes at cycle N+1, the stale rejected artifact remains the highest-numbered
one and permanently blocks both `move-task --to done` and the
`_enforce_review_artifact_consistency` preflight in `spec-kitty merge`. The `move-task`
guard offers `--skip-review-artifact-check` as the escape, but that flag asserts "a
reviewer rejected this and I am overriding them" — false here, and using it would write a
fabricated arbiter override into the durable evidence trail. The correct resolution is to
persist the real passing verdict, which is what this artifact does. WP03 has the identical
pathology.

## Cycle-1 finding: remediated

The cycle-1 blocking finding was that `src_python_paths or ...` at
`src/specify_cli/cli/commands/review/_dead_code.py:101` silently preferred the `src/`
subset, so a supported Python change outside `src/` was dropped from `supported_paths` and
its added public symbols were never extracted — yielding a false clean zero.

Remediated by commit `3e06a6032` ("fix(review): scan mixed Python layouts"), which replaces
the `or`-fallback with a single union predicate at `_dead_code.py:101-105`:

```python
supported_paths = tuple(
    path
    for path in changed_python_paths
    if path.startswith("src/") or "test" not in path
)
```

## Independent verification

The fix claim was **not** taken on trust. Two separate proofs were performed.

### 1. Reviewer-built reproduction of the mixed-layout scenario

I constructed the scenario from scratch — a fresh `git init` repository with a committed
baseline, then a single commit adding both a top-level `src/marker.py` (containing only
`VALUE = 1`) and a `package/dead.py` containing an unreferenced
`def PublicMixedDead(): return None` — and called `scan_dead_code()` against the baseline:

```text
discovery.error   = None
discovery.changed = ['package/dead.py', 'src/marker.py']
discovery.symbols = (('PublicMixedDead', 'package/dead.py'),)
corpus paths      = ['package/dead.py', 'src/marker.py']  err=None
findings          = [{'type': 'dead_code', 'symbol': 'PublicMixedDead', 'file': 'package/dead.py'}]
clean-zero shown  = False
```

Two control cases confirmed the fix does not over-report:

```text
### mixed layout, non-src symbol referenced from src
findings          = []
clean-zero shown  = True

### mixed layout, outside-src dir name contains "test" (latest/)
discovery.changed = ['src/marker.py']
findings          = []
clean-zero shown  = True     # C-008-mandated substring filter, see observations
```

### 2. Mutation proof — the committed tests genuinely guard the fix

To rule out a passing-but-toothless test, I exported the lane HEAD to a scratch tree with
`git archive` (no file in the reviewed worktree was modified), restored the exact cycle-1
buggy predicate in the scratch copy, and ran the committed test file there:

```text
FAILED tests/specify_cli/cli/commands/review/test_dead_code_baseline.py::test_mixed_python_layout_discovers_every_supported_path
FAILED tests/specify_cli/cli/commands/review/test_dead_code_baseline.py::test_real_post_merge_cli_uses_git_as_only_path_executable
2 failed, 10 passed in 64.13s (0:01:04)
```

Failure detail from the real-CLI node under mutation:

```text
E   AssertionError: assert '1 unreferenced public symbol(s)' in
    '... ✓ ...\nVerdict: pass  (0 finding(s))\n...'
```

A side-by-side run of the mutated and shipped modules against my own fixture:

```text
MUTATED (cycle-1 bug)    findings=[] clean_zero=True
CURRENT (fixed)          findings=[{'type': 'dead_code', 'symbol': 'PublicMixedDead',
                                    'file': 'package/dead.py'}] clean_zero=False
```

This matches the implementer's recorded red-first claim in `issue_2987_red_first.md` exactly
(`2 failed`, the same two node IDs). The guards are real, not synthetic fixtures.

## Verbatim gate results

```text
$ PWHEADLESS=1 python -m pytest tests/specify_cli/cli/commands/review/test_dead_code_baseline.py -q -p no:cacheprovider
12 passed in 45.92s

$ PWHEADLESS=1 python -m pytest tests/specify_cli/cli/commands/review/ tests/specify_cli/cli/commands/test_review.py -q -p no:cacheprovider
126 passed in 47.42s

$ ruff check src/specify_cli/cli/commands/review/_dead_code.py \
    src/specify_cli/cli/commands/review/_diagnostics.py \
    src/specify_cli/cli/commands/review/_report.py \
    tests/specify_cli/cli/commands/review/test_dead_code_baseline.py \
    tests/specify_cli/cli/commands/test_review.py \
    tests/specify_cli/cli/commands/review/test_diagnostic_codes_documented.py
All checks passed!
exit=0

$ mypy src/specify_cli/cli/commands/review/_dead_code.py
Success: no issues found in 1 source file

$ git diff --check kitty/mission-annoying-bugs-sweep-01KYHQ9F..HEAD
exit=0

$ ... --cov=specify_cli.cli.commands.review._dead_code --cov-report=term-missing
Name                                                Stmts   Miss  Cover   Missing
src/specify_cli/cli/commands/review/_dead_code.py     110      6    95%   97, 115, 117, 149-150, 161
```

Baseline-red attribution: not applicable. Zero test failures were observed on the lane at
any point, so no failure needed classifying against the merge base.

## Requirement verification

- **FR-014** (portability): `_dead_code.py` imports no `shutil` and invokes no `grep`;
  `_run_git_diff` wraps the subprocess boundary in `try/except FileNotFoundError`.
  `test_missing_git_at_subprocess_boundary_is_undeterminable` injects `FileNotFoundError`
  at `subprocess.run` — it does **not** patch `shutil.which`, as the contract demands.
- **FR-015** (no vacuous pass): the hardcoded `-- src/` pathspec is gone;
  `_discover_changed_symbols` classifies the change set and returns an explicit error for a
  failed diff, an empty diff, and an unsupported change set. Verified reachable by
  `test_non_git_repository_is_undeterminable`,
  `test_unsupported_non_python_change_is_undeterminable`, and
  `test_unreadable_python_corpus_is_undeterminable`. Both `git diff` return codes are
  checked; neither collapses to empty stdout.
- **FR-016** (regression-guarded): module-level `pytestmark = pytest.mark.fast`, plus the
  non-Python-layout fixture. Both halves guarded.
- **C-008** (POSIX semantics unchanged): pinned by
  `test_supported_symbol_result_set_matches_posix_baseline`, which reproduces the legacy
  result set including the untracked-caller and `src/`-scoped-corpus quirks.
- **C-009** (reporter coordination): verified live against the tracker, not just the
  evidence file. Issue #2987 is assigned to `stijn-dejongh`; comments `5091367887`
  (2026-07-27T12:36:44Z, folds the issue into this mission) and `5092277027`
  (2026-07-27T13:58:55Z, states the `git grep` option closes FR-014 only) both exist and
  name this mission.
- **NFR-004** (attribution, not green-washing): red-first baseline committed at
  `tests/specify_cli/cli/commands/review/baselines/issue_2987_red_first.md`; its claims were
  independently re-derived above rather than accepted.

## Anti-pattern checklist

1. **Dead code — PASS.** All eight new helpers (`_Discovery`, `_run_git_diff`,
   `_extract_added_symbols`, `_discover_changed_symbols`, `_load_python_corpus`,
   `_unreferenced_symbols`, `_append_undeterminable`, `_handle_missing_baseline`) are
   private with in-module callers. `scan_dead_code` has a production caller at
   `src/specify_cli/cli/commands/review/__init__.py:249`. The new
   `MissionReviewDiagnostic.DEAD_CODE_UNDETERMINABLE` member is consumed by `_dead_code.py`,
   `_report.py`, and `ERROR_CODES.md`.
2. **Synthetic-fixture test — PASS.** Mutation-proved above: deleting the fix turns the
   guards red. The CLI node spawns a real `python -m specify_cli review --mode post-merge`
   subprocess against a real Git repository with a PATH containing only executable spies,
   and asserts the observed executable set is exactly `{"git"}`.
3. **Silent empty return — PASS.** Every early return carries an explicit reason that
   funnels into `_append_undeterminable`: `_run_git_diff` returns `None` only on
   `FileNotFoundError` (documented in its docstring, converted to a verdict by both
   callers); `_load_python_corpus` returns `(), "<reason>"` for enumeration and decode
   failures. No bare `pass`, and no `return None`/`return []`/`return {}` without a reason.
4. **FR coverage — PASS.** Every FR and constraint in `requirement_refs` has a behavioral
   assertion, enumerated in the section above.
5. **Frozen surface — PASS.** `CHANGELOG.md` and `docs/changelog/CHANGELOG.md` are untouched
   (C-005's excepted file, FR-012's exclusion). No file marked frozen by `spec.md`,
   `plan.md`, or `contracts/` appears in the diff.
6. **Locked decision — PASS.** No `MUST NOT` clause is contradicted. Against the WP's own
   reviewer guidance: not a `shutil.which`-only guard (no `shutil` import at all); not a
   `git grep`-only replacement (a pure-Python corpus scan); subprocess return codes are
   checked on both diff invocations; `dead_code_undeterminable` is registered in
   `_HARD_FAILURE_FINDING_TYPES` in `_report.py`, so undeterminable can never render green;
   and the earned zero-symbol case remains reachable, proved by
   `test_supported_python_change_with_no_public_symbols_is_clean`.
7. **Shared-file ownership — PASS with recorded note.** See the scope-creep section below.
8. **Production fragility — PASS.** No new `raise` on any production code path. The gate
   fails closed by appending a structured finding, not by throwing.

## Scope creep and ownership

Three files in the diff sit outside WP02's declared `owned_files`:

- `src/specify_cli/cli/commands/review/_report.py` — required, or the new structured
  undeterminable finding would be silently dropped from `mission-review-report.md`.
- `tests/specify_cli/cli/commands/test_review.py` — its fixtures asserted fake-clean results
  against non-Git `tmp_path` directories.
- `tests/specify_cli/cli/commands/review/test_diagnostic_codes_documented.py` — hardcoded
  enum member count.

All three are direct regression-contract fallout, and all three are authorized on the record
in `issue_2987_red_first.md`.

**C-005 (P0 file-set separability) holds.** I verified this against the *actual* lane diffs,
not the declared ownership maps: `git diff --name-only` on lanes a, c, d, and e yields sets
entirely disjoint from WP02's. No other work package touches any file in WP02's change set.

**Non-blocking process nit (T028).** T028 states "Stop and update ownership before touching
an undeclared file." The authorization was obtained and recorded in the evidence file, but
the `owned_files` frontmatter in
`kitty-specs/annoying-bugs-sweep-01KYHQ9F/tasks/WP02-portable-dead-code-verdict.md` was
never amended to list the three adjunct files, and no `history:` entry records the ownership
change. The durable WP record therefore understates the WP's real surface. This does not
block approval — the substantive invariant (C-005 disjointness) is satisfied and the
authorization is auditable — but the frontmatter should be reconciled before merge so the
mission-level ownership map matches reality.

## Non-blocking observations

1. **Six uncovered defensive statements (95% coverage).** Lines 97 (`git diff reported no
   changed files`), 115 and 117 (Git disappearing or failing between the two diff
   invocations), 149-150 (`OSError` during `rglob` enumeration), and 161 (`Python source
   corpus is empty`). Each is a `return`-with-reason that funnels into the same
   `_append_undeterminable` sink already exercised by four passing tests; none carries
   independent logic. Line 97 is the only realistically reachable one (baseline equal to
   HEAD) and would benefit from a focused test under NFR-002, but the behavior is identical
   in kind to the tested `changed source set contains no supported Python files` path.
2. **Two deliberate legacy quirks preserved, both C-008-mandated, neither a new defect.**
   (a) The `"test" not in path` **substring** filter means an outside-`src/` directory whose
   name merely contains "test" — for example `latest/dead.py` — is dropped from the
   supported set; I reproduced this and it can still yield a clean zero. The contract states
   verbatim that this substring filter "remains unchanged," so this is required behavior.
   (b) When every supported changed path is under `src/`, `_load_python_corpus` scopes the
   corpus to `repo_root / "src"`, so a caller living outside `src/` does not count — a
   possible false positive, but noisy rather than silent, and explicitly pinned by
   `test_supported_symbol_result_set_matches_posix_baseline`.
3. **Performance is not a concern.** Measured against this repository: the whole-repo corpus
   is 3676 files / 42.1 MB, loading in 0.64 s; a 50-symbol reference scan over that corpus
   takes 0.43 s. The `src/`-scoped path loads 1155 files in 0.07 s. No unreadable file
   exists in the real tree, so the gate does not spuriously go undeterminable here.
4. **Terminology canon — clean.** No `--feature` occurrence in any added line of the diff.

## Conclusion

All acceptance criteria in the WP's Definition of Done are met. The cycle-1 defect is
genuinely fixed and genuinely guarded. **Approved.**
