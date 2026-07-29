---
affected_files:
- path: docs/api/environment-variables.md
- path: docs/api/upgrade-lifecycle.md
- path: docs/architecture/launch-readiness-future.md
- path: docs/guides/install-and-upgrade.md
- path: src/doctrine/styleguides/built-in/plain-language.styleguide.yaml
- path: tests/architectural/test_status_command_guidance.py
cycle_number: 4
mission_slug: annoying-bugs-sweep-01KYHQ9F
reproduction_command: "PWHEADLESS=1 python -m pytest tests/architectural/test_status_command_guidance.py -m 'arch_shard_1 and not windows_ci and (git_repo or integration or architectural) and not timing' --collect-only -q -p no:cacheprovider  # -> 5 tests collected; then PWHEADLESS=1 python -m pytest tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces -q -p no:cacheprovider  # -> 1 passed"
reviewed_at: '2026-07-27T16:40:12Z'
reviewer_agent: claude
verdict: approved
wp_id: WP04
---

# WP04 Review — cycle 4, commit `fbc019963`

**Verdict: approved.**

Cycle 3's single blocker — the guard carried no `pytestmark`, so the arch pole's
marker expression deselected all 5 tests and the guard would never have executed
in CI — is fixed and independently verified. One residual durability gap is
recorded below as a mandatory follow-up; it is out of WP04's declared ownership
and does not warrant a fifth cycle. Reasoning is spelled out rather than
asserted.

## 1. The guard actually runs in CI now

Re-ran the **full** CI expression myself against all three shards (not the
implementer's transcript):

```text
$ PWHEADLESS=1 python -m pytest tests/architectural/test_status_command_guidance.py \
    -m 'arch_shard_1 and not windows_ci and (git_repo or integration or architectural) and not timing' \
    --collect-only -q -p no:cacheprovider
tests/architectural/test_status_command_guidance.py::test_scoped_guidance_only_names_real_commands
tests/architectural/test_status_command_guidance.py::test_top_level_status_command_is_still_absent
tests/architectural/test_status_command_guidance.py::test_resolution_uses_click_names_not_callback_names
tests/architectural/test_status_command_guidance.py::test_extraction_ignores_prose_and_package_names
tests/architectural/test_status_command_guidance.py::test_guard_reddens_on_a_planted_phantom_command
5 tests collected in 38.41s

$ ... -m 'arch_shard_2 and ...' --collect-only -q
no tests collected (5 deselected) in 47.51s

$ ... -m 'arch_shard_3 and ...' --collect-only -q
no tests collected (5 deselected) in 39.31s
```

Exactly as claimed: `arch_shard_1` collects all 5, shards 2 and 3 deselect. The
shard assignment is the deterministic hash-bucket fallback — the file is
deliberately *not* in `tests/_arch_shard_map.py`, and that module's own docstring
states the `arch` group sets `default_fallback=True` so "a brand-new file is
auto-covered by construction — no manual table edit is required just to keep main
green." Correct mechanism, no drift introduced.

## 2. The markers are correct, not merely sufficient

- **Both registered.** `pytest.ini:45` (`architectural`) and `pytest.ini:52`
  (`docs_scoped`). No unknown-marker warning.
- **`docs_scoped` is mandated, not decorative.** Its registry text says: "New
  docs-scanning arch tests MUST carry this marker (guarded by
  `tests/architectural/test_docs_scoped_arch_coverage.py`)." This guard scans four
  real `docs/` pages, so the marker is obligatory. It is also load-bearing, not
  cosmetic: `.github/workflows/ci-quality.yml:1920-1957` makes the two legs
  **mutually exclusive** — on a docs-only PR the pole runs *only*
  `-m '<shard> and docs_scoped and not windows_ci'`; the full selection sits in
  the `else`. A docs-only PR is precisely the change class that can reintroduce
  `spec-kitty status` into these four Markdown pages.
- **Sibling parity is exact.** `test_docs_cli_reference_parity.py:63` and
  `test_unregistered_shim_scanner.py:14` both declare
  `[pytest.mark.architectural, pytest.mark.docs_scoped]` — the identical pair.
- **Omitting `git_repo` is right.** The marker means "tests that create real git
  repositories (subprocess git init)" (`pytest.ini:36`).
  `grep -nE "subprocess|\bgit\b|Repo\(" tests/architectural/test_status_command_guidance.py`
  returns nothing — the guard reads files and builds a Click tree in-process.
  `test_no_legacy_terminology.py:25` adds `git_repo` only because it genuinely
  shells out to git. Declaring it here would be a false declaration and would
  wrongly pull the guard into `git_repo`-selecting gates; it is also redundant for
  selection, since `architectural` already satisfies the
  `(git_repo or integration or architectural)` clause. Correctly omitted.

## 3. `test_no_new_orphan_surfaces` passes — and the transition is real

```text
$ PWHEADLESS=1 python -m pytest tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces -q -p no:cacheprovider
1 passed in 88.57s (0:01:28)
```

Reproduced the transition myself by deleting the `pytestmark` line from the
working tree and re-running the identical node:

```text
E   AssertionError: 1 test file(s) are selected by ZERO CI gates and are not in the recorded baseline — they will never run in CI:
E       tests/architectural/test_status_command_guidance.py
1 failed in 89.29s (0:01:29)
```

Restored with `git checkout --`; `git status --porcelain` empty. So the
*rejected* defect — "guard never runs in CI" — is now itself gate-protected: it
cannot silently recur.

### Count discrepancy — settled, no selection bug

Cycle 3 reported that file as "1 failed, 37 passed" (38); the implementer could
only collect 31. Both are right, and collection does **not** vary:

```text
test_gate_coverage.py                    -> 31 tests collected
test_arch_shard_marker_completeness.py   ->  7 tests collected
test_gate_coverage.py + test_arch_shard_marker_completeness.py -> 38 tests collected
```

31 + 7 = 38. Cycle 3's figure came from a combined two-file invocation, not from a
varying selection. `test_gate_coverage.py` is deterministic at 31: 29 test
functions, one of which (`test_gc2b_current_selection_matches_baseline`) is
parametrized over the static 3-entry `gc.BASELINE_TARGETS`
(`tests/architectural/_gate_coverage.py:1594`), giving 29 − 1 + 3 = 31.
Informational only; nothing to fix.

## 4. Mutation proof still reddens the gate

Planted the exact #2983 defect into the **real** styleguide and ran the shipping
guard:

```text
E   AssertionError: #2983 scoped guidance names a command the CLI does not expose:
E       - plain-language.styleguide.yaml:55: spec-kitty status
FAILED tests/architectural/test_status_command_guidance.py::test_scoped_guidance_only_names_real_commands
FAILED tests/architectural/test_status_command_guidance.py::test_guard_reddens_on_a_planted_phantom_command
2 failed, 3 passed in 34.00s
```

Same 2-failed/3-passed shape cycle 3 recorded. Styleguide restored;
`git status --porcelain` empty. The gate is non-vacuous (Standing Order 5:
concrete floor — 5 sources / 79 invocations — plus a self-mutation test, and now
real CI selection).

## 5. Scope — clean

`git diff kitty/mission-annoying-bugs-sweep-01KYHQ9F..HEAD --stat` is exactly the
six files in `affected_files`, every one of which is in WP04's `owned_files` /
`create_intent` frontmatter. The cycle-3 delta `fbc019963` is **one file, +11
lines, 0 deletions** — the `import pytest`, an 8-line rationale comment, and the
`pytestmark`. No extraction logic, denominator, or resolution behaviour changed.
Nothing crept in.

## Adjudication — the residual `docs_scoped` durability gap

The implementer surfaced this itself and backed out its own fix when the commit
hook raised `ACTIVE_WP_SCOPE_VIOLATION`. I verified the gap is real, not
theoretical, by executing the detector directly:

```text
reads_repo_docs(test_status_command_guidance.py)   = False   <- detector MISSES it
reads_repo_docs(test_docs_cli_reference_parity.py) = True    <- sibling IS detected
module_marks_docs_scoped(guard)                    = True    <- a pin would bite
guard in _KNOWN_DOCS_SCANNERS                      = False
```

and by dropping only `docs_scoped` from the working tree:

```text
tests/architectural/test_docs_scoped_arch_coverage.py            -> 10 passed
tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces -> 1 passed
```

Both silent. So `docs_scoped` **is** silently droppable today. **Approving anyway.
The reasoning:**

1. **The rejected defect is fully closed; the residual is strictly narrower.**
   Cycle 3's blocker was "selected by zero gates." Removing the whole `pytestmark`
   still reddens `test_no_new_orphan_surfaces` (proof above). What remains
   droppable is only the docs-only-trim membership — the guard keeps running on
   every non-docs-only PR, push and dispatch. A re-droppable `docs_scoped`
   narrows coverage; it does not reinstate the defect.
2. **The fix is outside WP04's ownership, and the governance gate said so.**
   WP04's `owned_files` frontmatter enumerates six paths;
   `tests/architectural/test_docs_scoped_arch_coverage.py` is not among them. The
   `ACTIVE_WP_SCOPE_VIOLATION` hook was correct and the implementer backing out was
   the correct action under Standing Orders 7–8 and C-005. Rejecting a WP for
   declining to make an edit the repo's own scope gate prohibits would be a
   reviewer error, not rigour.
3. **The gap is pre-existing and general, not authored by WP04.**
   `reads_repo_docs` is a documented best-effort AST heuristic — a
   `("src","tests","docs")` literal or a `root / "docs"` division chain. It misses
   *any* docs scanner that addresses pages by plain string literal. That is exactly
   why `_KNOWN_DOCS_SCANNERS` exists and already pins five files. WP04 is the sixth
   instance of a known limitation in an adjacent guard, not its cause. Holding this
   WP hostage to hardening that guard is scope creep onto a different defect class.
4. **The threat model is weak.** Dropping `docs_scoped` requires deliberately
   editing a `pytestmark` that carries an eight-line comment directly above it
   explaining why both markers are present and which CI leg each one buys. That is
   a deliberate act against a documented rationale, not silent drift.

**Follow-up — on record, must land:** add
`"tests/architectural/test_status_command_guidance.py"` to `_KNOWN_DOCS_SCANNERS`
in `tests/architectural/test_docs_scoped_arch_coverage.py:102`, either on the
planning branch or as a separate WP. Verified it would bite: `module_marks_docs_scoped`
already returns `True`, so once pinned, removing `docs_scoped` reddens
`test_known_docs_scanners_are_docs_scoped` naming this file. No lane in this
mission (a/b/c/e) touches that file, so there is no overlap risk. Consider also
teaching `reads_repo_docs` to recognise `Path("docs/...")` string literals, which
would close the class rather than one instance.

## Gates — verbatim

```text
$ PWHEADLESS=1 python -m pytest tests/architectural/test_status_command_guidance.py -q -p no:cacheprovider
5 passed in 33.96s

$ PWHEADLESS=1 python -m pytest tests/architectural/test_gate_coverage.py -q -p no:cacheprovider
31 passed in 330.72s (0:05:30)

$ PWHEADLESS=1 python -m pytest tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces -q -p no:cacheprovider
1 passed in 88.57s (0:01:28)

$ PWHEADLESS=1 python -m pytest tests/architectural/test_docs_scoped_arch_coverage.py tests/architectural/test_arch_shard_marker_completeness.py -q -p no:cacheprovider
17 passed in 87.08s (0:01:27)

$ PWHEADLESS=1 python -m pytest tests/architectural/test_no_legacy_terminology.py -q -p no:cacheprovider
4 passed in 33.01s

$ python -m ruff check tests/architectural/test_status_command_guidance.py
All checks passed!

$ python -m mypy tests/architectural/test_status_command_guidance.py
Success: no issues found in 1 source file
```

### Base-vs-HEAD node diff

Ran the adjacent suite (`tests/architectural/` +
`tests/integration/test_mission_type_resolution_integration.py`) at HEAD and at the
mission base `kitty/mission-annoying-bugs-sweep-01KYHQ9F` (`0f71459da`, in a
dedicated detached worktree), `-n auto --dist loadfile`:

```text
HEAD: 1 failed, 1180 passed, 4 skipped in 347.33s (0:05:47)
BASE: 1 failed, 1175 passed, 4 skipped in 384.74s (0:06:24)

HEAD FAILED: tests/architectural/test_no_raw_mission_spec_paths.py::test_constant_based_mission_spec_path_construction_stays_in_constructor_files
BASE FAILED: tests/architectural/test_no_raw_mission_spec_paths.py::test_constant_based_mission_spec_path_construction_stays_in_constructor_files
```

**Zero introduced, zero masked.** The failing-node sets are identical singletons,
and the single failure is the same pre-existing red with the same offender —
`src/specify_cli/cli/commands/accept.py:239: (coord_worktree_root / KITTY_SPECS_DIR / mission_slug)`
— in a file WP04 does not touch (category 1 under the baseline-red gotcha; I also
reproduced it standalone at base: `1 failed in 52.31s`). The +5 passed at HEAD is
exactly the guard's five tests, which do not exist on the base.

Replacement correctness spot-checked against the live compiled tree (resolved from
the lane-d checkout, avoiding the ambient `specify_cli` trap):
`spec-kitty upgrade` exposes `--cli`, `--dry-run`, `--no-nag`;
`spec-kitty agent tasks status` exposes `--mission` and no bare `--feature`
(Terminology Canon compliant); no top-level `status` command exists.

### `ruff format --check` attribution — implementer is right, and it is repo-wide

`ruff format --check` does want to reformat the file, but this is neither a WP04
defect nor a cycle-3 regression:

- **It is not gated.** No workflow, Makefile target, or pre-commit hook runs
  `ruff format`. CI runs `ruff check src tests` (advisory, comment-only) and
  `ruff check src tests --select TID251` (blocking). Both pass.
- **It is a repo-wide baseline condition.** `ruff format --check tests/architectural/`
  reports **131 files would be reformatted, 14 files already formatted**. The guard
  is one of the 131, not an outlier.
- **The cause is configuration, not sloppiness.** `pyproject.toml:195` sets
  `line-length = 164`; the file is hand-wrapped at ~88, so `ruff format` wants to
  *join* lines. Every hunk it proposes is a line-joining, not a correctness change.
- **Cycle 3 introduced none of it.** The proposed hunks start at line 89
  (`@@ -89,9 +89,7 @@` … `@@ -312,10 +285,7 @@`); the cycle-3 addition occupies
  lines ~37-47 and is untouched by any hunk.

Attribution accepted as stated.

## Anti-pattern checklist

1. **Dead code — PASS** (was the cycle-3 FAIL). The guard is now selected by
   `arch_shard_1` under the real CI expression, and the orphan ratchet reddens if
   the marker is removed.
2. **Synthetic-fixture test — PASS.** The mutation proof runs against the real
   styleguide through the shipping `unresolved_invocations` path.
3. **Silent empty return — PASS.** `command_position_path` returns `None` as an
   explicit, documented "not in command position" signal.
4. **FR coverage — PASS.** FR-012's regression gate now executes in CI.
5. **Frozen surface — PASS.** No `CHANGELOG.md` or `kitty-specs/**` authorship in
   the implementer's commits.
6. **Locked decision — PASS.** No top-level `status` command added;
   `test_top_level_status_command_is_still_absent` blocks that cheat path.
7. **Shared-file ownership — PASS.** Diffed lanes a/b/c/e against the mission
   branch: none touches a WP04-owned file. C-005 disjointness holds.
8. **Production fragility — N/A.** No production code path changed.

## Non-blocking observations (do not re-open)

- Module-level `os.environ.setdefault("SPEC_KITTY_ENABLE_SAAS_SYNC", ...)` /
  `..._NO_UPGRADE_CHECK` is the established repo idiom — six other test modules do
  exactly the same, including the sibling `test_docs_cli_reference_parity.py:47-48`.
- Cycle 3's three observations still stand and remain acceptable: shell-comment
  invocations inside fences are not extracted; trailing segments after a non-Group
  leaf resolve `True` by design; flag-first forms (`spec-kitty --verbose status`)
  break the subcommand walk. None occurs in the scoped corpus.
