---
work_package_id: WP11
title: 'The counter pin: red-first under a non-terminating hook-level mutant'
dependencies: []
requirement_refs:
- FR-018
planning_base_branch: feat/verification-trust-3115
merge_target_branch: feat/verification-trust-3115
branch_strategy: Planning artifacts for this mission were generated on feat/verification-trust-3115. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verification-trust-3115 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verification-trust-3115-01KYVYWM
base_commit: 9ed8757b6fa46ef3fa51544ff791ded9765df4ee
created_at: '2026-07-31T17:31:59.149244+00:00'
subtasks:
- T033
- T034
- T035
history: []
authoritative_surface: tests/delivery/
create_intent:
- scripts/mutants/nonterminating_dispatch_3115.py
execution_mode: code_change
owned_files:
- tests/delivery/test_dispatch_window_consent_3030.py
- scripts/mutants/nonterminating_dispatch_3115.py
tags: []
tracker_refs: []
---

# WP11 — The counter pin

**A pin whose failure mode is a hang is not a pin.** Measured during `#3030`: a mutant produced **1,603
retried empty selections** and the suite reported nothing until the run was forced with
`--timeout-method=signal`; the first attempt to measure it was itself **killed mid-session, producing no
summary and therefore no verdict**.

The two loop-driving tests in `tests/delivery/test_dispatch_window_consent_3030.py` —
`test_no_non_consented_event_ever_enters_the_live_dispatch_window` (`:157`) and
`test_the_window_is_filled_with_consented_events_not_wasted_on_denied_ones` (`:218`) — drive
`_run_dispatch_batches`' 413-halving/regrowth loop through `_RecordingIngress` (`:68`) with **no
bound**, so non-termination hangs them.

## Measured on a tree with NO global timeout

**This is the reason WP12 is blocked on WP11, hard.** Once a global timeout exists, a non-terminating
dispatch loop reds on the **timeout**, and this WP's red-first becomes **unobservable** — the backstop
masks the missing pin. `Failed: Timeout (>Ns) from pytest-timeout` is explicitly **not** an acceptable
red (FR-018, SC-014).

## Definition of done — measurable evidence

### T033 — the counters

Both loop-driving tests gain a **hard cap on the recorded batch count that reds naming the count**,
mirroring `DISPATCH_CALL_CAP = 25` in `tests/delivery/test_nfr002_loop_permanence_3030.py:69`, asserted
at `:154-157`. **`#3030` already adopted this shape for exactly this reason** — reuse over reinvention.

### T034 — red first is a consequence, not a threshold flip

The **non-terminating-loop plugin mutant** `scripts/mutants/nonterminating_dispatch_3115.py`, obeying
the corrected contract in full:

1. **Loading**: importable via `PYTHONPATH=scripts/mutants` **and loaded with
   `-p nonterminating_dispatch_3115`, with the `-p` flag quoted in the evidence.** *`PYTHONPATH` alone
   loads no plugin* — a `PYTHONPATH`-only mutant is imported by nothing, binds nothing, and its run
   reads as a passing gate.
2. **Neutralisation site**: **hook level, in `pytest_configure`** — **never** as a same-named fixture,
   which loses to a conftest fixture for items under that conftest's directory.
3. **Self-proof**: it **asserts its own binding**; it **reports the per-site split** across every name
   the symbol is reachable by (an aggregate count cannot distinguish "both sites mutated" from "one
   mutated, one inert" — the fifth rot mode); and it **fails loudly if the patched symbol was never
   called** during the session.
4. **Reporting**: the run under the mutant quotes the mutant's own binding/suppression report **beside**
   its count line and collected count.

Under it, `_run_dispatch_batches` **fails to make progress**, and each test reds **on the counter,
naming the count** — and specifically **not** on `Failed: Timeout (>Ns) from pytest-timeout`. **A red
whose text is the timeout means the counter did not bind**, and does not satisfy this WP.

**No verdict may be drawn from a run whose mutant suppressed zero calls** — a zero suppressed count is a
finding about the mutant, not about the code, and it is precisely what makes *"the counter did not
bind"* falsifiable rather than automatic.

### T035 — both measurements, and which one is the acceptance

- **The threshold-flip measurement** — merely setting the cap below the legitimate batch count — proves
  **the assertion fires**.
- **The mutant measurement** proves it fires **on the defect**.
- **Both are reported. The mutant one is the acceptance.**

**The rule is recorded in the file**: *any assertion about termination needs a counter; the timeout is a
backstop for the harness, not a substitute for the pin.*

### Cross-cutting

**NFR-009**: merge the mission branch into the worktree before the first measurement; state the commit
and merge-base — **and state explicitly that the tree measured had no global timeout**. **NFR-003**:
output to a file, tail of the file read; quote the count line **with its assertion text**; **an empty
output file is no measurement**; a killed run is neither a pass nor a fail — re-run it narrowed, and
check elapsed time before attributing it. **NFR-007**: read the failure text, not the tally.

### Backstop vs. pin — the distinction this WP exists to hold

A **timeout** is a property of the *harness*: it bounds wall clock. A **counter** is a property of the
*code under test*: it bounds iterations. **Only the second can be an assertion about termination.**

## Files other agents hold

`pytest.ini` and `.github/workflows/ci-quality.yml` are **WP12's, and WP12's alone** — **no other WP may
register a marker or edit CI**, and this WP in particular must not add a `timeout` mark or an `addopts`
entry to make its own measurement more comfortable. `tests/delivery/test_nfr002_loop_permanence_3030.py`
is **nobody's write scope** — it is the shape this WP *mirrors*, read-only. `src/**` is nobody's.
