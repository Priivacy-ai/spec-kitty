# WP07 Review — reviewer-renata — Cycle 1: Changes requested

Overall this WP is very close. The documented commands are verbatim-correct, the
pending-CI caveat is honest and well-separated, terminology is green, the ratchet
entrypoint exists and is exported as documented, and a real parallel slice
(`tests/doctrine -n auto --dist loadfile -p no:cacheprovider`) ran 2210 passed
with the real `~/.spec-kitty` untouched. One accuracy defect blocks approval.

## Issue 1 (BLOCKING — implementation mismatch): docs claim a `Path.home` monkeypatch that the code deliberately removed

In `docs/development/testing-parallel.md`, the "Per-worker HOME isolation (the
master enabler)" section states:

> "An autouse, function-scoped fixture **re-asserts the `Path.home` monkeypatch**
>  and env for every test, keyed by worker id, so call-time `Path.home()` reads
>  are isolated too."

This misdescribes the actual implementation. The `_isolated_worker_home` fixture
in `tests/conftest.py` (lines 205-229) **deliberately does NOT hard-patch
`Path.home`**. Its docstring is explicit that a previously-used
`monkeypatch.setattr(Path, "home", lambda: home_base)` was the **cycle-1
regression** that broke ~16 `tests/sync` cases, and was removed; the fixture now
establishes the worker home **only via the `HOME`/`USERPROFILE`/XDG env vars**,
relying on `Path.home()` natively resolving `HOME` so in-test overrides win.

Why this matters (not cosmetic):
- It misleads contributors about how isolation works.
- Worse, a future maintainer "aligning code to docs" could re-introduce the
  `Path.home` monkeypatch — re-triggering the exact cycle-1 regression the
  conftest docstring warns against.

**Fix**: Reword that sentence to match the env-var mechanism, e.g.:

> "An autouse, function-scoped fixture re-asserts the `HOME`/`USERPROFILE`/XDG
>  env vars for every test, keyed by worker id, so call-time `Path.home()` reads
>  (which natively resolve `HOME`) stay isolated too. The fixture deliberately
>  does *not* monkeypatch `Path.home`, so a test that sets up its own tmp home
>  via `setenv('HOME', ...)` cleanly overrides the per-worker baseline."

The AGENTS.md / CLAUDE.md block does not have this error — only the docs page
sentence needs the one-line correction.

## Non-blocking note (no action required this cycle)

- The single failing test observed during review,
  `tests/doctrine/test_tactic_compliance.py::test_tactic_schema_valid[mutation-testing-workflow]`,
  is a **pre-existing** tactic-YAML schema failure that fails serially too and is
  in a file WP07 does not touch (WP07's diff is docs-only). It is unrelated to
  this WP and is correctly out of scope.
