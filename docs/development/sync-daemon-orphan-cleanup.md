---
title: Sync Daemon Orphan Cleanup — Operator Runbook
description: How to inspect, classify, and clean up stale Spec Kitty sync daemons.
---

# Sync Daemon Orphan Cleanup — Operator Runbook

This runbook covers the two-command operator path for diagnosing and cleaning
up stale Spec Kitty sync daemons that accumulate after upgrades. It covers
what each cleanup class means, what is never touched, the JSON fields for
scripting, and the hosted-auth/sync test environment gate.

**Architectural background:**
[`docs/adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md`](../adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md)

---

## Why orphans accumulate

Normal `spec-kitty` upgrades leave the prior sync daemon running. Before this
mission shipped, the reaper skipped any candidate whose interpreter identity
differed from the current process — so every version upgrade made the prior
daemon permanently un-reapable. On one machine this produced 18 orphans on
ports `9401–9418` spanning versions `3.2.2`, `3.2.3`, and `3.2.4`.

Starting from this release, the reaper uses the **daemon-root scope marker**
(`--spec-kitty-daemon-root=<path>` embedded in the daemon's command line) as
the primary kill authority. Executable or interpreter identity is stale-version
*evidence only*, not a skip gate. Same-scope daemons from any prior version are
now auto-cleaned at startup.

---

## The two-command operator path (SC-005)

You have accumulated old sync daemons — for example, after several upgrades.

```bash
# Step 1 — Inspect (read-only, never kills anything)
spec-kitty auth doctor

# Output: one row per in-range listener
#   PID · PORT · VERSION · CLASS (safe_auto | operator_required) · REASON
```

```bash
# Step 2 — Clean the safe ones (same-scope stale daemons)
spec-kitty auth doctor --reset

# Output summary:
#   swept: N  (safe_auto daemons that were cleaned)
#   skipped: M  (operator_required — see step 3)
#   failed: K  (could not kill — permissions or race)
```

```bash
# Step 3 — Only when step 2 reported skipped operator_required daemons
#           that you recognise as yours (e.g. a stale cross-checkout daemon)
spec-kitty auth doctor --reset --force
```

That is the complete path from "many orphans" to "clean." No other commands or
manual `kill` invocations are needed for the standard upgrade case.

---

## Cleanup classes

Every in-range listener is assigned exactly one `cleanup_class` verdict.

### `safe_auto`

The daemon is:
- a Spec Kitty sync daemon (port in `[9400, 9450)`, live `/api/health` response)
- its self-reported PID/port match the actual listener
- its singleton scope is positively proven (scope marker present and matches
  this host's daemon state root)
- it is **not** the currently-recorded singleton

`safe_auto` daemons are cleaned automatically at startup (no user action
required) and also by `auth doctor --reset`.

### `operator_required`

The listener looks like a Spec Kitty sync daemon but one or more conditions
cannot be positively confirmed. Common sub-reasons:

| `skip_reason` | Meaning |
|---|---|
| `pre_marker` | No `--spec-kitty-daemon-root=` marker in command line. Daemon was spawned before the scope-marker was introduced. |
| `cross_root` | Scope marker is present but names a different daemon state root (different `$HOME` or container). |
| `unresponsive` | Listener did not answer `/api/health` (wedged/hung). |
| `pid_port_mismatch` | Health self-report PID/port differ from the actual OS listener. |
| `missing_pid` | Could not determine the PID of the process holding the port. |

`operator_required` daemons are **never** auto-killed at startup. They are
surfaced by `auth doctor` (with `skip_reason`) and cleaned only by
`auth doctor --reset --force` or interactive confirmation.

### `never_touch`

The process is not identifiable as a Spec Kitty sync daemon. This includes:

- **Dashboard daemons** (port range `[9237, 9337)`) — sync cleanup never
  touches the dashboard lifecycle.
- **Third-party listeners** — any process on a port in `[9400, 9450)` that
  does not identify as Spec Kitty sync.
- **Out-of-range processes** — a Spec Kitty-looking process listening outside
  both reserved ranges.

`never_touch` candidates are excluded from all cleanup paths and are never
reported in the `auth doctor` orphan table. They are invisible to the operator
intentionally.

---

## What is never touched

The following are **always** excluded from sync cleanup regardless of any
other identity signal:

- **Dashboard daemons** (`DaemonIntent.LOCAL_ONLY`, ports `9237–9336`). Sync
  and dashboard daemon lifecycles are fully separate (C-001, C-002).
- **Third-party applications** squatting on a port in `[9400, 9450)`. A
  foreign health response causes immediate `never_touch` classification.
- **Out-of-range processes** (outside `[9400, 9450)`).
- **The currently-recorded singleton** — the live daemon is never a cleanup
  candidate, even if a cleanup pass runs while it is active.

---

## JSON output for scripting and CI

```bash
# Inspect — full identity records per orphan
spec-kitty auth doctor --json | jq '.orphans[] | {port, pid, cleanup_class, skip_reason}'

# Reset — structured result
spec-kitty auth doctor --reset --json | jq '.reset_result'
# → { "swept": [...], "skipped": [...], "failed": [...] }
```

### `reset_result` fields

| Field | Type | Contents |
|---|---|---|
| `swept` | array | One entry per daemon cleaned. Fields: `pid`, `port`, `package_version`, `protocol_version`, `cleanup_path` (`http_shutdown` \| `terminate` \| `kill`), `reason`. |
| `skipped` | array | One entry per `operator_required` daemon not cleaned (because `--force` was absent). Fields: `pid`, `port`, `cleanup_class`, `skip_reason`. |
| `failed` | array | One entry per daemon that survived every escalation attempt (permission or race). Fields: `pid`, `port`, `failure_reason`. |

`swept[]`, `skipped[]`, and `failed[]` account for every candidate: no entry
is silently dropped from the result.

---

## Hosted auth / sync test environment gate (C-006)

On this development machine, hosted auth/sync test commands require the
`SPEC_KITTY_ENABLE_SAAS_SYNC=1` environment variable:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty auth doctor
SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty auth doctor --reset
```

Without this variable, the hosted auth/sync paths are gated off and the
commands operate in local-only mode. CI sets this variable explicitly for
jobs that require hosted connectivity.

---

## Developer / test quickstart

The venv is assumed warm. The live-subprocess test suite uses real loopback
ports and real PIDs; run it serially:

```bash
# Classification + reset (WP03 / T029):
PWHEADLESS=1 .venv/bin/pytest tests/sync/test_daemon_orphan_classification.py -n0 -q

# Boundary regression matrix (WP07 / T032–T035):
PWHEADLESS=1 .venv/bin/pytest tests/sync/test_daemon_cleanup_boundary.py -n0 -q

# #1071 singleton reconfirmation (WP08 / T038):
PWHEADLESS=1 .venv/bin/pytest tests/sync/test_issue_1071_singleton_reconfirmation.py -n0 -q
```

Lint and type gates (NFR-005):

```bash
.venv/bin/ruff check src/specify_cli/sync tests/sync
.venv/bin/mypy --strict src/specify_cli/sync
```

---

## #1071 status

Issue [#1071](https://github.com/Priivacy-ai/spec-kitty/issues/1071) (same-`$HOME`
singleton leak — multiple same-scope sync daemons accumulating under one
`$HOME`/runtime root) is **reconfirmed resolved** by the automated regression test
`tests/sync/test_issue_1071_singleton_reconfirmation.py`.

The test reproduces the #1071 scenario: it spawns multiple same-scope sync
daemons under a single shared `$HOME`/daemon-root, invokes the canonical reaper
(`reap_orphan_daemons`), and asserts that stale same-scope daemons are reaped
and exactly **one** singleton survives — no leak.

**Recommended action:** Close issue #1071, citing
`tests/sync/test_issue_1071_singleton_reconfirmation.py` as durable test
evidence. The operator performs the GitHub close action; it is not performed
automatically.

If any residual same-`$HOME` leak is found in the future, open a new scoped
issue rather than re-opening #1071, and add a targeted test case to the
reconfirmation suite.
