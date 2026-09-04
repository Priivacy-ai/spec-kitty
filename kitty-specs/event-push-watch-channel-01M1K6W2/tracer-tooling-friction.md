# Tracer: Tooling Friction — events-tail (`event-push-watch-channel-01M1K6W2`)

Seeded at plan phase (charter Standing Order #3). Intentionally near-empty — this file is
appended during implementation as real friction is hit, not pre-populated with speculation.

## Plan-phase friction (the little that surfaced before implementation)

- `scripts/docs/build_cli_reference.py`'s `capture_help()` hardcodes `cmd_runner = ("uv", "run",
  "spec-kitty")` — running it as shipped re-syncs the environment via `uv run` rather than using
  the already-built `.venv`. Worked around at plan time by citing the known monkeypatch-`main()`
  procedure rather than running the generator; not yet exercised for real (that happens in the
  CLI-shell WP). If the monkeypatch procedure turns out stale against the current script version,
  record that here.
- `hashlib.sha256` is a repo-wide TID251-banned import with no `tests/` directory exemption — not
  friction exactly (it's documented in `pyproject.toml`'s own comments), but easy to miss until a
  lint failure, so flagged in the plan itself rather than discovered here.

## To be appended during implementation

(Empty by design — implementation WPs append real friction as it is hit: surprising test
behavior, doc-generation drift, marker/CI-job mismatches discovered only at push time, etc.)

## WP02 friction

- **No `.venv/` inside the lane worktree.** `.venv/bin/spec-kitty`/`.venv/bin/python` do not exist
  under `.worktrees/event-push-watch-channel-01M1K6W2-lane-a/` — only the primary checkout has a
  built venv. The working pattern (also hinted at in this repo's own `CLAUDE.md` baseline-red
  gotcha section): invoke the primary checkout's `.venv/bin/python`/`.venv/bin/spec-kitty` binaries
  directly while `cwd` is the lane worktree, with `PYTHONPATH="$(pwd)/src"` set so the worktree's
  own (not the primary checkout's) source is imported and tested — e.g.
  `PYTHONPATH="$(pwd)/src" /path/to/primary/.venv/bin/python -m pytest ...`. `spec-kitty
  safe-commit` and other `.venv/bin/spec-kitty` subcommands work fine invoked this way too (they
  resolve the git repo from `cwd`, not from the binary's own location).
- **ATDD red-shape care needed for the hash-check test (T010).** A truncate-then-regrow fixture
  built from unrelated, differently-shaped replacement content produced a RED for the *wrong*
  reason against WP01's baseline: `poll_once()`'s existing FR-006 tear-tolerance parsing raised an
  uncaught `json.JSONDecodeError` (an interior non-`\n`-terminated-looking fragment at the stale
  offset), not the intended "silently accepts wrong data as legitimate growth" assertion failure
  the WP's ATDD-precision note requires. Fixed by constructing the regrown fixture's first N lines
  BYTE-LENGTH-IDENTICAL to the original (same key, same-length value) so the stale offset still
  lands on a clean line boundary in the regrown file — isolating the test to the ONE thing it must
  prove (content silently changed at that boundary) rather than incidentally also tripping a
  different, already-covered failure shape. Worth calling out explicitly in a WP's own "ATDD
  precision" guidance for any future truncate-then-regrow-style fixture: byte-boundary alignment of
  the *stale offset* against the *regrown* file is a real fixture-construction hazard, not just a
  content-difference concern.
- **`diff-cover`'s `--cov=` target must be the dotted module path, not a filesystem path**, when
  `PYTHONPATH` (not an installed package) is how the module resolves — `--cov=src/specify_cli/status/tail_reader`
  silently collects zero coverage data ("Module ... was never imported" / "No data was collected"),
  while `--cov=specify_cli.status.tail_reader` works. Easy to lose several minutes to before
  noticing the warning is the actual cause, not a real "0% coverage" regression.

## WP03 friction

- **`spec-kitty safe-commit` refuses `kitty-specs/` edits from the lane branch outright, with a
  hard ERROR (not merely the anticipated "Protected path" warning), unless `--to-branch` is
  passed explicitly.** Committing the operator-directed F1/E1 doc fixes (`spec.md`/`plan.md`
  under `kitty-specs/event-push-watch-channel-01M1K6W2/`) via `safe-commit <file> -m <msg>` with
  no `--to-branch` failed with: `Error: safe_commit: worktree ... HEAD is
  'kitty/mission-event-push-watch-channel-01M1K6W2-lane-a', expected
  'feat/event-push-watch-channel-3841'. Run \`git -C ... checkout
  feat/event-push-watch-channel-3841\` first.` -- i.e. the tool auto-inferred `kitty-specs/`
  changes must target the mission's `planning_base_branch`/`merge_target_branch`
  (`feat/event-push-watch-channel-3841`) and refused because the lane worktree's HEAD is on the
  lane branch instead, with no in-place override. Checking out the mission branch inside a lane
  worktree that must stay on its lane branch (per this WP's own dispatch instructions and the
  "one checkout, many agents" discipline) was not an option. Resolved by passing `--to-branch
  kitty/mission-event-push-watch-channel-01M1K6W2-lane-a` explicitly (asserting HEAD against the
  CURRENT branch instead of letting the tool auto-infer the mission branch) -- this then produced
  exactly the anticipated "Protected path" WARNING (non-fatal) this WP's dispatch prompt already
  named as expected friction: `[spec-kitty guard] WARNING: Protected path:
  kitty-specs/.../spec.md — implementation branches must not modify kitty-specs/`, and the commit
  succeeded. Net: the dispatch prompt's warning about a "Protected path" WARNING undersold the
  actual friction -- without `--to-branch`, it is a hard-blocking ERROR, not a warning, and the
  fix (pass `--to-branch <current-lane-branch>` explicitly) is not self-evident from the error
  message alone (the error's own suggested remedy -- `git checkout feat/...` -- would have been
  actively wrong to follow, since it instructs switching the lane worktree off its own branch).
- **`--to-branch` omission deprecation warning fires on every `safe-commit` call in this
  mission** (`warning: --to-branch will be required in v3.3; pass it explicitly`), including for
  the `src/`/`tests/` commits where the branch inference worked fine without it. Confirms the
  above finding is the early edge of a real upcoming behavior change, not a one-off glitch --
  future WPs in this and other missions should pass `--to-branch <lane-branch>` explicitly on
  every `safe-commit` call from the start, not just when the `kitty-specs/` hard error forces the
  issue.

## WP04 friction (resumed after a rate-limit interruption)

- **Shared `.venv` editable-installs against whichever lane last had it built, not the lane
  actually being worked.** This workspace's `.venv` lives at the workspace root
  (`/home/.../3841/.venv`), shared across all lane worktrees, and its `spec-kitty-cli` editable
  install (`_editable_impl_spec_kitty_cli.pth`) pointed at `lane-a`'s `src/`, not `lane-b`'s --
  meaning a naive `.venv/bin/python -m pytest` run from `lane-b` would have silently imported
  `lane-a`'s `specify_cli` (a DIFFERENT lane's code) while collecting `lane-b`'s test files,
  producing plausible-looking but WRONG results. Confirmed via `python -c "import specify_cli;
  print(specify_cli.__file__)"`. Worked around with `PYTHONPATH=<lane-b>/src` prepended ahead of
  the venv's site-packages for every invocation (verified this resolves `specify_cli` to
  `lane-b`'s own tree) -- deliberately did NOT re-run `pip install -e .` against the shared venv,
  since that would silently break whatever lane (e.g. `lane-a`) was relying on the editable
  install pointing at it (this mission's own "One checkout, many agents" discipline: never mutate
  shared state under a concurrent lane). Future WPs resuming in a multi-lane workspace should
  verify `specify_cli.__file__` resolves to THEIR OWN lane before trusting any test run, not just
  before their first run.
- **Real defect found in T022's already-committed `events.py`**: the `--mission` option's own
  help string read `"...tail (never --feature*, C-003)."` -- literally containing the substring
  `--feature`, which tripped `tests/specify_cli/cli/test_no_visible_feature_alias.py`'s FR-006
  surface-invariant guard (rendered `--help` text must never contain the `--feature` token). The
  guard is checking the LITERAL substring, not intent, so a help string documenting "never use
  `--feature`" is itself a violation. Fixed by rewording to "(no legacy feature-alias flag,
  C-003)" -- the lesson generalizes: never write the literal token `--feature` inside any
  user-visible help/error string anywhere in the CLI, even inside a sentence forbidding it.
- **Real defect found in T027's already-committed CLI registration**: `src/specify_cli/cli/commands/__init__.py`'s
  registration of the new `events` Typer app was correct, but `src/specify_cli/_completion_manifest.json`
  (the shell-completion fast-path manifest) was never regenerated to include it, so
  `tests/specify_cli/cli/commands/test_completion_fast_path.py`'s three drift guards
  (`test_manifest_matches_live_cli`, `test_fast_path_output_matches_full_app`,
  `test_top_level_completion_covers_all_user_facing_commands`) all failed in the
  integration-tests-cli tier. This is a general trap: registering a new top-level Typer command
  group has (at least) two required companion updates in this repo --
  `docs/api/cli-commands.md` (T028, already in WP04's `owned_files`) AND
  `src/specify_cli/_completion_manifest.json` (NOT in WP04's `owned_files`, and easy to miss
  since it never surfaces in the `fast-tests-cli` tier, only in `integration-tests-cli`).
  Regenerated in-process via `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/python -m
  specify_cli.completion --regenerate` (no subprocess-per-command sweep, no `uv run`); the diff
  was purely additive (12 lines) and scoped to the new `events`/`events tail` entries.
  **Recommendation**: any future WP that registers a new top-level command should add
  `src/specify_cli/_completion_manifest.json` to its `owned_files` alongside
  `docs/api/cli-commands.md`, since both are load-bearing companion artifacts of the same
  registration change.
- **Real marker-discipline defect confirmed in the prior (rate-limited) session's drafted
  `test_events_tail_real_fixture_end_to_end`**: it was appended under
  `tests/cli/test_events_tail.py`'s existing module-level `pytestmark = [pytest.mark.fast]`.
  pytest marks STACK rather than override -- a function cannot un-mark itself with a
  function-level decorator once its module has applied a mark -- so a bare `@pytest.mark.integration`
  `@pytest.mark.git_repo` decorator on that one function would have left it carrying `fast` AND
  `integration`/`git_repo` simultaneously, wrongly collected by BOTH `fast-tests-cli`'s
  `-m "fast and not windows_ci"` selector (confirmed via a real `--collect-only` run: it appeared
  there, 10/10 tests) AND absent from `integration-tests-cli`'s `-m "not windows_ci and
  (git_repo or integration)"` selector (confirmed: 0/10 collected). Fixed by extracting the test
  into its own file, `tests/cli/test_events_tail_real_fixture.py`, with a module-level
  `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]` and no `fast` marker --
  mirroring this repo's own established pattern for git_repo-only test modules (e.g.
  `tests/cli/commands/test_agent_mission_commit_to_branch.py`, module-level
  `pytestmark = pytest.mark.git_repo`, no `fast`). Note for future WPs: this repo's actual
  established split pattern for a fast/non-fast marker mix within one logical test suite is a
  SEPARATE FILE per marker set, never a function-level override layered on a module-level
  `pytestmark`; the WP04 prompt's own suggested precedent (`tests/status/test_tail_reader.py` vs
  `test_tail_reader_truncation.py`) turned out to both be `fast`-only in the actual current repo
  state, so that specific pair was not literally the right example -- but the underlying
  file-split principle it was gesturing at is correct and is what this fix follows.

## WP05 friction

- **`seed_wp_to_planned`'s deterministic-looking seed ids are only deterministic WITHIN one
  call sequence, not ACROSS two independent seed passes in the same test process.**
  `tests/status/conftest.py`'s `_make_seed_event_id()` counter (`_SEED_COUNTER`) is a single
  process-global monotonic counter, by design -- it exists to give every seed call across the
  whole test run a unique id, not to reproduce the same id sequence twice. WP05's T031 test
  seeds two `feature_dir`s (control, then concurrent) in the SAME test function to build a
  byte-identical comparison; the seed counter kept incrementing across both passes, so the
  control run's seed lines read `...0001`/`...0002` and the concurrent run's read
  `...0003`/`...0004` -- a real byte-level diff, even though the harness's OWN pinned
  `event_id`/`at` generation (a separate `_DeterministicIdSource`, reset explicitly between
  runs) was already correct. This was T031's actual observed RED. Confirmed it was a harness
  determinism gap, not a concurrency-induced defect, by reproducing the identical divergence
  with two purely SEQUENTIAL (non-threaded) runs of the same script -- concurrency was never
  the cause. Fix: `monkeypatch.setattr(conftest_module, "_SEED_COUNTER", 0)` before each seed
  pass. **Lesson for future WPs**: any test that seeds more than one `feature_dir` via
  `seed_wp_to_planned` and then compares their logs byte-for-byte must also reset
  `_SEED_COUNTER` between passes -- resetting only a test-local id/clock source is not enough
  if the shared fixture helper carries its own independent global counter.
- **A cold-start `.venv/bin/python -m pytest` run from a lane worktree with no prior
  `git_repo`-tier run in that worktree triggers a one-time, several-second `pip install`/wheel
  build** (confirmed via `tests/conftest.py`'s session-scoped `test_venv` autouse fixture,
  which creates/caches an ISOLATED subprocess-test venv under
  `.pytest_cache/spec-kitty-test-venv/` for `git_repo`/CLI-subprocess tests -- separate from
  the shared repo-root `.venv/`). Not a defect: confirmed the shared repo-root `.venv`'s own
  `_editable_impl_spec_kitty_cli.pth` was untouched (still pointed at lane-a's `src/`,
  unrelated to this isolated per-worktree cache) before and after. Re-running the same test
  afterward is fast (~0.4s, no reinstall) since the cache persists. Worth knowing up front so a
  first `git_repo`-tier run's ~25s wall time isn't mistaken for a hang.
- **Clarifies (does not contradict) WP02's PYTHONPATH note above**: for a plain
  `.venv/bin/python -m pytest ...` invocation with `cwd` set to the lane worktree, this repo's
  own `pytest.ini` (`pythonpath = src`) is sufficient on its own to resolve `specify_cli` to
  THAT worktree's own `src/` (verified via `--collect-only` and a real full-suite run
  succeeding against WP04's real `events.py`, which only exists in lane-b/lane-c, never
  lane-a) -- no explicit `PYTHONPATH=<lane>/src` environment variable is required for a
  same-process `pytest` invocation specifically. WP02's original note about needing an
  explicit `PYTHONPATH` still stands for whatever direct/bare `python -c "import specify_cli"`
  or subprocess invocation prompted it; the two are not the same code path, and this WP did
  not need to set `PYTHONPATH` for any of its `pytest` runs.
- **Pre-existing (not this WP's) mypy finding surfaces incidentally**: running
  `mypy tests/status/test_events_tail_concurrency.py` pulls in `tests/status/conftest.py` as a
  dependency and reports `conftest.py:124: error: The return type of a generator function
  should be "Generator" or one of its supertypes [misc]` on
  `_restore_default_saas_handlers_after_each_status_test`. Confirmed pre-existing via
  `git blame` (introduced by commit `6966cd6e95`, 2026-05-22, long before this mission) and
  reproduced identically running `mypy` on `conftest.py` alone. Left untouched -- out of this
  WP's `owned_files`/locality of change; flagged here so a future WP does not misattribute it.
