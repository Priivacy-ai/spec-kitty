---
work_package_id: WP05
title: 'The sync leak guard: fail the polluter, not the victim'
dependencies:
- WP04
requirement_refs:
- FR-007
planning_base_branch: feat/verification-trust-3115
merge_target_branch: feat/verification-trust-3115
branch_strategy: Planning artifacts for this mission were generated on feat/verification-trust-3115. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verification-trust-3115 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verification-trust-3115-01KYVYWM
base_commit: d8d0ad7eff9ddeb14e154afd82450cf2dfd5472d
created_at: '2026-07-31T12:00:00+00:00'
subtasks:
- T016
- T017
- T018
- T019
history: []
authoritative_surface: tests/sync/
execution_mode: code_change
owned_files:
- tests/sync/conftest.py
- tests/sync/test_leak_guard_probe_3115.py
create_intent:
- tests/sync/test_leak_guard_probe_3115.py
tags: []
tracker_refs: []
---

# WP05 — The sync leak guard

An autouse guard in `tests/sync/conftest.py` that snapshots the globals **and the live-thread set**
WP04's inventory marks reachable, and **fails the test that leaves them dirty** — the polluter, not the
victim. **Scoped to WP04's inventory, not to WP06's answer**, so it ships whether or not the
attribution converges (H4).

## Explicit prohibition — stated in these words

> **Do not read, edit, refactor or "improve" the filename-token consent-grant fixture at
> `tests/sync/conftest.py:242-259` (`protected = ("consent", "capture_gate")`). It is out of scope, it
> is *armed* — replacing the token guard with a marker reds three `test_runtime.py` tests whose natural
> remedy would undo `#3030`'s T028 — and it needs its own mission.**

`tests/sync/conftest.py` is 259 lines and that guard is its **final fixture**. The friction record's
entry is *"A shared fixture whose guard is filename-matched can silence the pins it guards"*. This WP
adds a fixture to that file and touches nothing at `:242-259`.

## Note on the new probe file

`tests/sync/test_leak_guard_probe_3115.py` is declared so ownership and the lane entry exist — but see
the red-first clause below: **the preferred outcome is that this file is a thin harness pointing at a
real inventoried leak, not a synthetic leaker.** **An owned file with no diff is legal.**

## Definition of done — measurable evidence

### T016 — the guard

Autouse, snapshots the globals **and the live-thread set** WP04's inventory marks reachable, and
**fails the test that leaves them dirty, naming the symbol** (or the thread's `name` and target) **and
the node-id**. **Restore, do not clear** (C-002): a fixture touching process-global state restores the
value it found, in a `finally`; `reset`-to-empty is permitted only for state nothing outside the
fixture reads, and a registry is by definition not that.

### T017 — control your diagnostic, and it runs FIRST

**Before the guard's verdict on anything else is trusted**, point it at
`tests/specify_cli/invocation/test_propagator_consent_gate_3030.py`'s `wiring` fixture — the known
`reset_adapters()` leak, whose answer is **already known** — and **quote the outcome**.

**A guard that does not flag the known leak is an invalid probe, and every later verdict from it is
void.** (Standing rules: *"Control your diagnostic, not just your test."* The recorded instance: an
agent measured "0 gates", which reads as a serious finding, then ran the identical probe against a file
definitely covered — **also 0**. The probe was invalid; the file was fine.)

### T018 — red first, and the order of preference is binding

FR-007 forbids *"a purpose-written file that satisfies the criterion by construction"*, and the earlier
draft of this WP named exactly that file as its red-first mechanism. The contradiction is resolved by
this order:

1. **Bite a real inventoried leak from WP04.** An existing test in the `tests/sync/` cone that WP04's
   inventory marks as leaving an inventoried entry dirty is **named by node-id** and **failed by the
   guard on that test**. The probe file is then a **harness** (selection + assertion on the guard's own
   report), not a leaker.
2. **Only if WP04's inventory surfaces no such test** may a synthetic probe be used — and then the
   limitation is written down **in WP10's exact voice**: ***"the only demonstrated bite is the
   synthetic case"***, verbatim, in the probe file's docstring **and** in the WP's transition note.
   **Recording it is a pass; passing it off as a demonstrated bite is not.**

Either way, the probe mutates **exactly one inventoried entry and nothing else**, and **the probe
carries the failure, not a later victim**.

### T019 — positive control, rot control, cost

- **Positive control**: a clean selection is **not** flagged, and the guard reports **how many tests it
  inspected** *and* **which inventory entries it did not watch, with the reason** (H8, NFR-008). The
  positive control **must include a run where nothing leaks and nothing is flagged** — the guard
  becoming the polluter, by snapshotting state in a way that instantiates it, is R10.
- **It detects and fails; it does not repair.**
- **Rot control**: a renamed, moved or deleted watched symbol **fails loudly** rather than silently
  watching nothing.
- **NFR-006**: added wall clock over the `fast-tests-sync` selection measured **before/after at the
  same worker count and the same coverage state**. **Over 5% → change the guard's implementation
  (cheaper snapshot, per-module rather than per-test), never its reach.** Any reduction in watched
  surface is a spec change requiring a written justification and an updated FR-006 count, because a
  guard scoped down to fit a budget is the *"mechanism reporting success for having done nothing"*
  shape with a performance excuse.
- **NFR-004**: probe runs are **sequential, or explicitly partitioned by `SPEC_KITTY_HOME` and port
  range**. `tests/sync` and `tests/cli` sessions are never run in parallel on one machine — they spawn
  real daemons and `pgrep`/port-scan, so sibling sessions reap each other's. 16 recorded false reds.

### Cross-cutting

**NFR-009**: merge the mission branch into the worktree before the first measurement; state the commit
and merge-base. **NFR-003**: output to a file, tail of the file read; quote the count line with its
assertion text; **an empty output file is no measurement**; a killed run is neither a pass nor a fail —
re-run it narrowed.

### R6 — the new probe file must be gate-selected

WP05 adds a test file, so `tests/architectural/test_gate_coverage.py`'s orphan ratchet applies. State
**which gate selects it and under which marker**, with that selection's collected count. **Never widen
`tests/architectural/_gate_coverage_baseline.json`** — it is on the nobody-may-edit list.

## Files other agents hold

`docs/development/process-global-inventory-3115.md` is **WP04's** — this WP *consumes* the inventory,
it does not edit it. `tests/sync/tracker/test_saas_client.py` is **WP06's, then WP14's**.
`tests/sync/test_sync_consent_default_deny.py` is **WP09's**.
`tests/specify_cli/invocation/test_propagator_consent_gate_3030.py` is **nobody's write scope** — it is
the control case this WP *points the guard at*, read-only.
