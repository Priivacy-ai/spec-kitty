# `tests/regression/` — issue-pinned P0 reproductions

## What this suite is for

`@pytest.mark.regression` means exactly one thing: **an intentionally-red,
issue-pinned P0 reproduction, executed only by the `regression tests
(blocking)` CI job.** Every other test suite in this repository is expected
to run green; a red anywhere else is a real signal, never noise from a
marker doing double duty.

That is legitimate — not a process failure to hide — per
[`docs/adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md`](../../docs/adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md):
a red mainline is the honest signal of an accepted, release-blocking (P0)
defect, and a failing reproduction test is the self-documenting, un-loseable
proof of it. See also
[`docs/development/red-main-and-release-readiness.md`](../../docs/development/red-main-and-release-readiness.md).

## Entry rule

A test earns `@pytest.mark.regression` when it is:

1. A **red-first reproduction** of an accepted, open, release-blocking (P0)
   issue — it fails today, through the real, pre-existing production entry
   point, for the documented reason (not a fixture/setup error).
2. **Pinned to an open issue number** in its docstring, with the root cause
   and the desired (post-fix) outcome spelled out, so a future reader does
   not have to reconstruct the defect from the assertions alone.
3. Never `xfail`/`skip`/quarantined to hide the red. The red is the point —
   maintainers clear it by fixing the product, never by weakening the test.

If a test you are adding is a red-first P0 reproduction, add it under this
directory (or extract it here if the natural home file already has
unrelated, passing tests — see "Extraction, not a file move" below) and mark
it `@pytest.mark.regression`. Only the dedicated `regression tests
(blocking)` CI job (`python -m pytest tests/ -m regression`) selects this
marker; every other CI job's selection excludes it (by marker exclusion
and/or by not touching this path), so the marker's membership and this
job's collection stay in lockstep with "every other suite is green".

## Exit rule

Once a red-first reproduction turns green — the product defect is fixed —
it **leaves this suite**:

1. Move the test to the functional slice that matches the module it
   exercises (look at where its siblings already live — e.g. a merge-executor
   test belongs in `tests/merge/`, a CLI-command test in
   `tests/specify_cli/cli/commands/`).
2. Drop `@pytest.mark.regression`.
3. Add the canonical marks for that functional suite and test type, taken
   from [`docs/context/testing-taxonomy.md`](../../docs/context/testing-taxonomy.md)
   (e.g. `integration` + `git_repo`, or `unit` + `fast`) — never invent a
   marker outside that vocabulary.
4. Update the docstring: it is now a permanent regression *guard* against
   the defect recurring, not a red-first reproduction. Keep the issue
   reference as history and say the defect is fixed.

The 2026-08 landing fold that wrote this README is the worked example: eleven
stale, now-passing reproductions were relocated out of this directory this
way (see the fold's commit history for the mapping), and several
still-resident-but-mismarked permanent tests (behavioral guards,
integration coverage that had been copy-pasted from a `regression`-marked
sibling) were simply un-marked in place, because their functional home
already was `tests/regression/`'s neighboring directory.

### Extraction, not a file move

Sometimes a red-first reproduction is added to a file that also holds
several unrelated, passing tests (the natural place to add coverage for a
command is next to its existing tests). In that case, moving the *whole*
file into `tests/regression/` would misfile the passing tests. Extract only
the regression-marked test (plus the fixtures/helpers/constants it actually
needs) into its own module here, named `test_issue_<NNNN>_<slug>.py`, and
leave the rest of the source file working undisturbed. The reverse applies
on exit: if the whole file's remaining content belongs together (e.g. one
red-first test living among several already-permanent, unmarked tests that
share its module and topic), move the *whole* file to its functional home
instead of leaving an orphaned regression-only file behind.

## CI: this is the one routed home

`@pytest.mark.regression` is selected by exactly one CI job:
`regression tests (blocking)` (`.github/workflows/ci-quality.yml`), which
runs `python -m pytest tests/ -m regression`. It is **blocking** — a member
of the `quality-gate` aggregation — because an open P0 red-first reproduction
is expected to red mainline, and CI is the release authority (ADR
2026-07-17-1): a non-blocking regression lane would fake-green P0s and lose
the signal the marker exists to give.

Every other CI job either does not select `tests/regression/` at all, or
excludes the `regression` marker explicitly (`and not regression` in its `-m`
expression) so a P0 reproduction can never be silently double-counted as a
"pass" or a "fail" in a job this repo does not treat as release-gating.

## Never "fix" a test to make it pass here

A red-first reproduction in this directory must never be turned green by
weakening the assertion, adding a skip/xfail, or loosening the match — that
would hide the defect it exists to prove. The product fix is separate,
dedicated work; once it lands, the test turns green on its own and then
exits per the rule above.
