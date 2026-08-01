---
work_package_id: WP06
title: 'The sleep-count attribution, within budget and above a recorded floor'
dependencies:
- WP04
requirement_refs:
- FR-005
planning_base_branch: feat/verification-trust-3115
merge_target_branch: feat/verification-trust-3115
branch_strategy: Planning artifacts for this mission were generated on feat/verification-trust-3115. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verification-trust-3115 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verification-trust-3115-01KYVYWM
base_commit: d8d0ad7eff9ddeb14e154afd82450cf2dfd5472d
created_at: '2026-07-31T12:00:00+00:00'
subtasks:
- T020
- T021
- T022
history: []
authoritative_surface: tests/sync/tracker/
execution_mode: code_change
owned_files:
- tests/sync/tracker/test_saas_client.py
- scripts/mutants/attribute_sleep_count_3115.py
create_intent:
- scripts/mutants/attribute_sleep_count_3115.py
tags: []
tracker_refs: []
---

# WP06 — The `sleep`-count attribution

`tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after` is
investigated as a **separate defect** from the CLI failures, whose measured cause is render width and
therefore **cannot be shared**.

## What is settled and must not be re-derived (FR-005)

`src/specify_cli/tracker/saas_client.py:19` is a bare `import time`, so
`@patch("specify_cli.tracker.saas_client.time.sleep")` resolves the **stdlib `time` module object**.
The mock is process-wide and its call recorder counts `time.sleep` calls from **any live thread in the
worker** during the patch window. The victim file's own `_advancing_clock` docstring
(`tests/sync/tracker/test_saas_client.py:32-50`) already documents this exact class for
`time.monotonic`.

**Two legs are closed in advance and are explicitly not funded:**

- **A leaked module-global retry/backoff value is structurally impossible.** `saas_client.py` has
  exactly two module-level names — `_SESSION_EXPIRED_MESSAGE` (`:36`) and `_UNAUTHENTICATED_CATEGORY`
  (`:39`) — and the backoff is **local variables** inside `_poll_operation`
  (`delay`/`cap`/`total_timeout`, `:466-468`).
- **`_poll_operation` threading**: nothing in the tree threads it.

**These two are the only exclusions permitted to be arguments from structure.** Every other excluded
mechanism carries a **named exclusion measurement**.

What remains open is **which live thread is sleeping inside the patch window**. The candidate source is
`src/specify_cli/sync/daemon.py` — threads `:587`, `:767`, `:828`; sleep loops `:584`, `:1382`.

## Definition of done — measurable evidence

### T020 — a FLOOR, recorded before the budget starts

This WP was previously closable with **zero test runs**: its non-converging branch required only
self-reported hours and a self-reported mechanism list. **Before any of the 6 hours are counted**,
WP06 records **one** of:

- **(F-a)** the symptom **observed red locally**, with its failure text quoted verbatim —
  `AssertionError: Expected 'sleep' to be called once. Called <n> times.` — the **exact selection** that
  produced it, and that selection's **collected count**; or
- **(F-b)** an explicit written statement that **it could not be reproduced locally**, enumerating
  **every selection tried with each one's collected count and outcome** — file-level, cone-level, with
  and without `-n auto --dist loadfile`, and with and without the daemon-spawning siblings.

**Neither branch may be closed without one of these two on the record.** *"I could not reproduce it"* is
admissible; *"I could not reproduce it"* **without the list of what was tried and what each collected**
is not.

### T021 — the attribution

A written attribution naming **(i)** a leaked live thread and its start site, **or (ii)** a specific
other mechanism, supported by a reproduction that **shows the call count moving** — **the count before
and the count after, both quoted with their assertion texts** (NFR-007). A tally moving is not
evidence; a `TypeError` from a changed signature is not evidence of the defect under test.

**Each excluded mechanism carries a named exclusion measurement** — the command run, the collected
count, and the observed `sleep` call count — **not an argument from structure**.

Any mutant used here obeys the corrected contract (C-003): `scripts/mutants/attribute_sleep_count_3115.py`
made importable with `PYTHONPATH=scripts/mutants` **and loaded with `-p attribute_sleep_count_3115`,
with the `-p` flag quoted in the evidence** — `PYTHONPATH` alone loads no plugin; neutralising or
instrumenting at **hook level** (`pytest_configure` / `pytest_fixture_setup`), **never** as a same-named
fixture, which loses to a conftest fixture; **asserting its own binding**; **reporting the per-site
split** across every name the symbol is reachable by; and **failing loudly if the symbol it patched was
never called**. **No verdict — least of all a null one — may be drawn from a run whose mutant reports a
zero suppressed count.**

### T022 — budget, and where the finding is recorded

- Budget: **at most 6 agent-hours and at most 3 candidate mechanisms**, measured **after WP04's
  inventory is complete and after the floor is recorded**. **Hours spent and mechanisms tried are
  reported** (FR-010).
- **Explicitly permitted**: *"the two symptoms have two different causes."* This is the expected
  outcome on present evidence.
- **Explicitly forbidden**: adopting the issue's *"common shape"* sentence as the finding — the CLI
  half's cause is measured and has nothing to do with globals, so that sentence is **falsified as an
  explanation** and must not be inherited as a finding.
- The finding is recorded **at the site**, in the victim file's docstring, in the voice
  `_advancing_clock`'s docstring already uses (`:32-50`).
- **Narrative goes to the PR body and to `notes/` via the orchestrator on the mission branch** — a lane
  may not write `kitty-specs/` (C-010, `commit_guard.py:84-89`).

### Cross-cutting

**NFR-009**: merge the mission branch into the worktree before the first measurement; state the commit
and merge-base. **NFR-003**: output to a file, tail of the file read; **an empty output file is no
measurement**; a killed run is neither a pass nor a fail — re-run it narrowed, check elapsed time
against the `timeout` value before attributing it. **NFR-004**: never run `tests/sync` and `tests/cli`
sessions concurrently on one machine. **NFR-002**: state the worktree import path — conclusions of
**sameness** taken without it are void.

## WP06 lands either way

Its **negative result** — which mechanisms were excluded and by what measurement, above the recorded
floor — **is a deliverable, not a failure**. WP14 then takes outcome A (remedy) or outcome B
(`deferred-with-followup` + successor issue). What is **never** permitted is closing the sync half on a
green shard while the cause is unidentified.

## Files other agents hold

`tests/sync/tracker/test_saas_client.py` is **shared with WP14 by construction** — same lane, WP14
after WP06, which is what makes WP14's outcome A a within-lane transfer. `tests/sync/conftest.py` and
the leak-guard probe are **WP05's**. `docs/development/process-global-inventory-3115.md` is **WP04's** —
this WP consumes it. `src/specify_cli/sync/daemon.py` and `src/specify_cli/tracker/saas_client.py` are
**read-only**; `src/**` is nobody's write scope.
