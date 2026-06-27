---
title: Running the test suite in parallel
description: 'How to run the Spec Kitty test suite in parallel locally and in CI: the one correct command, why it is shaped that way, and reproducing the coverage-neutrality gates.'
doc_status: active
updated: '2026-06-21'
related:
- docs/guides/testing-flakiness.md
---
# Running the test suite in parallel

The Spec Kitty test suite runs safely in parallel locally and in CI, typically
at least 2× faster on a machine with four or more cores. This page explains the
one correct local command, why it is shaped the way it is, and how to reproduce
the coverage-neutrality gates CI uses.

For what to do when a test goes red on CI *unrelated to your diff* — budget gates
vs. correctness flakes vs. environmental flakes, and why we never retry-to-green —
see the [test-flakiness handling policy](testing-flakiness.md).

## The local command

```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
# daemon/real-port tests run serially:
PWHEADLESS=1 pytest tests/sync/test_orphan_sweep.py -n0 -q
```

The first command runs the bulk of the suite across worker processes. The second
command runs the daemon/real-port tests serially. Run both; the parallel command
deliberately leaves the serial-only tests for the second pass.

## Why `--dist loadfile` (never bare `--dist load`)

`pytest-xdist` supports several distribution modes. We always use `loadfile`:

- **`loadfile`** keeps every test that lives in the same file on a single
  worker. File-scoped fixtures (`scope="module"`, file-level collection
  ordering, shared module state) keep working exactly as they do serially.
- **`load`** (the bare default) scatters a single file's tests across multiple
  workers. That breaks file-scoped fixtures and any test that relies on
  collection order within a file.

For that reason: **always pass `--dist loadfile`; never use bare `--dist
load`.** CI uses `loadfile` for the same reason.

`-p no:cacheprovider` disables pytest's cache plugin so a parallel run never
races on the shared `.pytest_cache` directory.

## Per-worker HOME isolation (the master enabler)

A parallel run **never touches the real `~/.spec-kitty`**. Each `pytest-xdist`
worker — and the serial "master" run when you omit `-n auto` — gets its own
isolated home directory. The isolation is set up in `tests/conftest.py`:

- `pytest_configure` points `HOME` / `USERPROFILE` and the XDG dirs
  (`XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`) at a per-worker base
  **before collection**, so modules that bind a home-derived path at import time
  (for example `specify_cli.sync.daemon.SPEC_KITTY_DIR`) resolve into the
  isolated home.
- An autouse, function-scoped fixture re-asserts the `HOME` / `USERPROFILE` / XDG
  env vars for every test, keyed by worker id, so call-time `Path.home()` reads
  are isolated too. It does **not** monkeypatch `Path.home` (that approach was the
  cycle-1 regression that broke ~16 `tests/sync` cases — the fixture relies on
  `Path.home()` natively resolving `HOME` via `expanduser`), so a test that sets
  up its own tmp home via `setenv('HOME', ...)` cleanly overrides the per-worker
  baseline.

The per-worker base is keyed by the xdist test-run UID and the worker id, so two
workers in the same run get distinct homes (no collision) and successive runs do
not reuse stale state. The regression guard
`tests/architectural/test_real_home_isolation_guard.py` (SC-006) and
`tests/test_worker_home_isolation.py` prove this invariant.

Because the real `~/.spec-kitty` is never bound, you do not need to back it up or
worry about a parallel run truncating your real `queue.db`.

## The serial daemon pass

Per-worker HOME isolation protects per-user state, but it does **not** protect
OS-global resources such as real TCP ports or singleton daemons. Tests that bind
the reserved daemon port range (9400–9449) — `tests/sync/test_orphan_sweep.py` —
must run in their own serial pass:

```bash
PWHEADLESS=1 pytest tests/sync/test_orphan_sweep.py -n0 -q
```

`-n0` forces serial execution even when xdist is installed. These tests are
excluded from the parallel pool so two workers never contend for the same port.

## Volume env gates (`SPEC_KITTY_ULID_VOLUME_FULL`)

Some tests exercise large-volume ULID generation. By default they run at a
**reduced** scale so the local default stays fast; the full scale is reachable
via an env gate (and is exercised on the nightly/full path). The assertion logic
is identical across scales — only the volume changes.

```bash
pytest <ulid_test> -q                               # reduced (fast, default)
SPEC_KITTY_ULID_VOLUME_FULL=1 pytest <ulid_test> -q  # full (nightly parity)
```

## Running the stability ratchet locally

Before any shard is flipped to parallel, it must pass the stability ratchet
(C-RATCHET): N consecutive green parallel runs with no new flakes. The same
entrypoint CI uses is available locally (the WP02 coverage-safety harness):

```bash
python -m tests._support.coverage_safety.ratchet -n 3 -- tests/agent -m "not slow"
```

Exit code `0` means all N runs were green and the flip is accepted; `1` means it
was rejected and the summary names any new or flaky failures. The Python API is
`run_ratchet(...)` from `tests._support.coverage_safety`. See
`tests/_support/coverage_safety/README.md` for the full harness (collection
equivalence and anti-vacuity mutation checks).

## Validate the acceleration (copy-pasteable)

These are the mission's reproducible validation steps. Run them from the repo
root to confirm the parallel run is coverage-neutral and at least 2× faster than
serial. (`.venv/bin/pytest` is the synced project interpreter; substitute
`pytest` if you run it directly.)

```bash
# 1. Serial baseline (whole-suite wall clock) and a per-shard nodeid reference.
time .venv/bin/pytest tests/ -q -p no:cacheprovider     # serial baseline
.venv/bin/pytest tests/charter --collect-only -q | sort > /tmp/charter-serial.nodeids

# 2. Collection equivalence: serial vs parallel must collect identical nodeids.
.venv/bin/pytest tests/charter -n auto --dist loadfile --collect-only -q \
  | sort > /tmp/charter-par.nodeids
diff /tmp/charter-serial.nodeids /tmp/charter-par.nodeids   # must be empty

# 3. Stability ratchet: 3 consecutive green parallel runs (the same gate CI uses).
python -m tests._support.coverage_safety.ratchet -n 3 -- \
  tests/charter -m "fast and not windows_ci"

# 4. Parallel-vs-serial timing: target ≥2× faster on a ≥4-core machine.
time PWHEADLESS=1 .venv/bin/pytest tests/ -n auto --dist loadfile -p no:cacheprovider \
  --deselect tests/sync/test_orphan_sweep.py
time PWHEADLESS=1 .venv/bin/pytest tests/sync/test_orphan_sweep.py -n0 -q   # serial pass

# 5. Real home untouched: mtime/inode unchanged (or path still absent) after the run.
ls -la ~/.spec-kitty 2>/dev/null
```

## Status: local default vs CI shard flips

- **Local parallel command — validated and safe now.** Per-worker HOME isolation
  (WP04) is in place, so the local command above runs without touching your real
  `~/.spec-kitty`. Use it today.
- **CI shard flips — pending 3×-green confirmation.** The mission's CI shard
  flips (WP05, in `.github/workflows/ci-quality.yml`) are gated on three
  consecutive green CI runs before they are considered locked in. The full
  "≥2× faster" claim is host-dependent and is confirmed against CI; locally you
  should still see a clear speedup on a multi-core machine.
