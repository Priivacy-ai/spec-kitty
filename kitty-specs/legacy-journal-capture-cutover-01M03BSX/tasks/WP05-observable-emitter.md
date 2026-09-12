---
work_package_id: WP05
title: 'Observable emitter capture failure (folds #3391)'
dependencies:
- WP03
requirement_refs:
- FR-001
- FR-010
planning_base_branch: fix/legacy-journal-capture-cutover
merge_target_branch: fix/legacy-journal-capture-cutover
branch_strategy: Planning artifacts for this mission were generated on fix/legacy-journal-capture-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/legacy-journal-capture-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
history:
- at: '2026-08-15T00:00:00Z'
  actor: claude
  note: WP authored by tasks phase
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/sync/
create_intent:
- tests/sync/test_emitter_observability.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/emitter.py
- tests/sync/test_emitter_observability.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before touching any code, load your operating profile:

```
/ad-hoc-profile-load implementer-ivan
```

The profile carries your identity, boundaries, and the ATDD/red-first discipline
this WP is built around. Do not proceed on default behavior — the emitter contract
below is a footgun the profile's boundaries are meant to keep you inside of.

---

## Objective

Eliminate **silent-success capture** at the event emitter. Today a capture that
cannot land is swallowed into a stderr-only `[yellow]Warning:[/yellow]` and the host
command still reports success — the exact P0 shape of #3425, and the standing
grievance of #3391.

This WP delivers IC-05 (plan.md:179-185) / FR-001 + FR-010:

1. Fix **both** swallow sites in `src/specify_cli/sync/emitter.py`:
   - `_capture_to_journal` (`emitter.py:2114-2115`, `"Warning: event journal capture failed"`).
   - `_emit_for_project_context` (`emitter.py:2334-2335`, `"Warning: Explicit-context event
     capture failed"`) — **the live-reproduced site** (`mission create` printed this five
     times authoring this very mission; spec.md:19-23).
2. Surface a genuinely-unrecoverable capture failure at the **command boundary** via a
   **process-level captured-failure flag/counter** the command epilogue inspects and reports
   on (or non-zero-exits from).
3. Keep the surface **NON-FATAL** — a capture failure must never crash the host command.
4. Rate-limit the loud path so an exceptional failure cannot become a per-event
   warning-storm.

This folds #3391 (INV-1 "no silent success", data-model.md:69-71).

---

## Context

**CRITICAL — do NOT make `_emit` raise.** `_emit` (`emitter.py:2117`) is contractually
documented "Non-blocking: never raises" (`emitter.py:2130`) and is the **sole body behind
~30 public `emit_*` methods** (`emit_build_registered`, `emit_wp_status_changed`,
`emit_mission_created`, … — every `def emit_*` from `emitter.py:1012` onward). Those callers
ignore the return value and assume emission can never throw. Raising out of `_emit`, or out of
either helper it drives, would turn a swallowed warning into a crash across the entire status /
build / mission surface. That is a **regression, not a fix**. The observability signal must be
**out-of-band** (a process-level flag/counter), never an exception that escapes to a caller.

**The common case is already fixed upstream in this mission.** WP03 makes live writes on a
greenfield / cutover root actually succeed (fresh roots resolve `project_only` before any
LEGACY persist; legacy-with-data roots auto-migrate). So after WP03 there is normally **nothing
to swallow** — the loud path here is genuinely **exceptional** (a truly unrecoverable capture
failure). This is exactly why rate-limiting matters and why raising is the wrong lever: the
loud surface is a backstop for the residual unrecoverable case (research.md Decision 3, lines
43-57; Decision 10, lines 109-113), not the hot path.

**Coordinate with #3391 (assignee MOES-Media) — do NOT duplicate.** The emitter swallow shape
is #3391's territory (C-001/C-004, spec.md:178-181). This mission folds it (FR-010). Leave a
coordination note on #3391 stating that the observable-failure surface lands here so the fix
closes once, not twice — do not re-implement a competing surface. Use `unset GITHUB_TOKEN` for
`gh` if scopes are missing (CLAUDE.md GitHub CLI note).

**Depends on WP03.** WP03 (layout resolution / cutover) must be `approved`/`done` before this
WP is claimed — the loud path is only correct once the common case is already succeeding. If
WP03 is not yet satisfied, the dependency gate refuses the claim; do not force past it. Building
this surface before WP03 lands would make the flag fire on the *common* case (every greenfield
emit), which is precisely the storm this WP is designed to avoid.

**Only the `except` handlers change.** This WP is deliberately narrow: it rewrites the two
swallow `except` blocks and adds the process-level surface + epilogue read. It does not touch
`_emit`'s routing, the validation pipeline, `_queue_event_locally`, or the ProjectSyncStore
selection (owned elsewhere in the mission / kept per C-003).

---

## Subtasks

### T022 — Red-first: unrecoverable capture failure is boundary-observable AND non-fatal

Author `tests/sync/test_emitter_observability.py` (new file; `create_intent`). Write these
tests **red first** — they must fail against the current `emitter.py` before any production
change. This subtask pins the two orthogonal guarantees the rest of the WP must not violate:
non-fatal (no exception escapes) and observable (a process-level signal is set). It maps
directly to US1 acceptance scenario 3 (spec.md:52) and INV-1 (data-model.md:69-71).

- **Non-fatal pin**: drive an emit through a public `emit_*` method (e.g. `emit_history_added`,
  `emitter.py:1756`, or `emit_wp_status_changed`, `emitter.py:1109`) with the underlying queue
  append forced to raise — monkeypatch `_queue_event_locally` (called from `_capture_to_journal`,
  `emitter.py:2112`) to throw a representative `RuntimeError`. Assert **no exception escapes** —
  the `emit_*` call returns normally (`None` or the event, per the method). This locks the
  never-raises contract (`emitter.py:2130`) so T023/T024/T025 cannot regress it.
- **Observable pin**: after that failed capture, assert the **process-level captured-failure
  flag is set / counter incremented** (the surface T025 introduces). Assert the signal is
  readable **without a filesystem rescan** — an in-process module/class attribute queried via
  the T025 read API (e.g. `captured_failures()`), mirroring the `skipped_profiles`
  no-rescan-diagnostics pattern (CLAUDE.md Profile Load Diagnostics).
- **Both sites**: parametrize or duplicate so **both** swallow sites drive the flag when their
  inner write fails — `_capture_to_journal` (`emitter.py:2095`) and `_emit_for_project_context`
  (`emitter.py:2265`, whose inner `OfflineQueue(...).queue_event` refusal raises the
  `RuntimeError` at `emitter.py:2330`). Since this is red-first, these assertions FAIL now
  (today both sites only `_console.print`).
- **Reset/isolation pin**: assert the read/reset API leaves a clean slate between cases so one
  test's failure count does not bleed into the next (drives the T025 `reset_captured_failures()`
  design).
- Use isolated temp roots via `SPEC_KITTY_HOME` / `HOME` fixtures — **never** the live
  machine-global `~/.spec-kitty` (this dev box is itself a legacy root; plan.md:30,
  research.md:120-121). Confirm each test is red against current `emitter.py` before moving on.

File anchors: `src/specify_cli/sync/emitter.py:2095`, `:2114`, `:2265`, `:2334`; new test at
`tests/sync/test_emitter_observability.py`.

### T023 — Fix `_capture_to_journal` swallow (`emitter.py:2114-2115`)

Replace the silent `except Exception as exc: _console.print(... "event journal capture
failed" ...)` at `emitter.py:2114-2115` so that, in addition to the (rate-limited) warning, the
failure **records into the process-level captured-failure surface** from T025.

- Keep the method's `-> None` signature (`_capture_to_journal`, `emitter.py:2095-2103`) and its
  non-raising behavior unchanged — callers of `_capture_to_journal` still see no exception.
- Do NOT re-raise; do NOT change the docstring's capture-is-local contract
  (`emitter.py:2104-2109`) — capture stays independent of hosted consent (FR-006 note there).
- The recorded entry should carry enough to be actionable at the epilogue (site name +
  `repr(exc)`/summary) **without leaking the full envelope** (no payload, no credential
  material) — the emitter handles identity-bearing data.
- Order of operations inside the `except`: record into the surface first (so the count is
  always exact even if the console print is throttled/suppressed by T026), then emit the
  human warning.

Verify the T022 "both sites" pin for this site now goes green while the non-fatal pin stays
green. Ties to FR-001 (no silent-success capture) and NFR-001 (0 swallowed to stderr-only).

### T024 — Fix `_emit_for_project_context` swallow (`emitter.py:2334-2335`) — live-reproduced site

Replace the silent `except Exception as exc: ... "Explicit-context event capture failed" ...;
return None` at `emitter.py:2334-2335` so the failure **records into the same process-level
surface** from T025, then still `return None` (preserving the explicit-context contract that a
refused capture yields `None`, `emitter.py:2329-2331`).

- This is the site `mission create` hit five times while authoring this very mission
  (spec.md:19-23) — it is the highest-value fix in the WP; call that out in the commit body and
  the PR description.
- Keep it non-fatal: `_emit_for_project_context` (`emitter.py:2265`) must not raise out to its
  caller; the internal `RuntimeError("canonical project outbox refused dossier event capture")`
  at `emitter.py:2330` must stay **caught** at `emitter.py:2334` — it is the refusal signal —
  now routed to the loud surface instead of stderr-only, then still `return None`.
- Preserve the other guards in the `try` body untouched: the identity-override `ValueError`
  (`emitter.py:2319`), `_validate_event` short-circuit returning `None` (`emitter.py:2326`),
  and `validate_outbound_payload` — this WP only changes the `except` handler, not the
  validation flow.
- Same record-then-warn ordering as T023 so the count is exact under T026 throttling.

Verify the T022 pin for this site goes green; the non-fatal pin stays green. Ties to US1
scenario 3 (spec.md:52) and FR-010.

### T025 — Process-level captured-failure flag/counter threaded to the command epilogue

Introduce a **process-level captured-failure surface** — a module-level (or `EventEmitter`
class-level, `emitter.py:853`) flag + counter/record list — that both swallow sites (T023,
T024) record into. The **command epilogue inspects it and reports / non-zero-exits** on a
genuinely-unrecoverable failure. This is the mechanism the plan mandates (plan.md:119-121,
183; research.md Decision 10, lines 109-113): boundary observability delivered *by inspecting
a flag*, not by raising.

- **Do NOT change the ~30 `emit_*` method signatures** and **do NOT change `_emit`'s
  never-raises contract** (`emitter.py:2130`). The signal is strictly out-of-band: every
  `emit_*` caller (from `emitter.py:1012` onward) keeps calling exactly as today and still
  ignores the return; only the epilogue reads the flag afterward. Any diff that threads a new
  parameter or return channel through `_emit` or the `emit_*` surface is out of contract —
  the whole point is that the ~30 callers are untouched.
- Expose a small read/reset API on the surface — e.g. `captured_failures()` returning the
  recorded failures (site name + exception summary, no full envelope) and
  `reset_captured_failures()` clearing them — so the epilogue can inspect at command end and so
  tests (T022/T026) can assert and isolate between cases. Reset at command **entry** so the
  flag is per-invocation and never leaks across a long-lived process or across missions.
- Wire the epilogue inspection at the command boundary — the CLI command wrapper that runs an
  emit-bearing command. Keep the behavior **non-fatal by default** but **observable**: at
  minimum a surfaced end-of-command summary of unrecoverable captures; a non-zero exit is
  acceptable for the unrecoverable case *as long as it is the epilogue, not `_emit`, that
  decides it* — the emitter never crashes the command mid-flight.
- Keep the module-level `_console` (`emitter.py:98`, a stderr `Console`) for the human-readable
  warning; the flag/counter is the machine-observable half. The two are complementary — the
  warning is throttled (T026), the counter is exact.
- **Boundary consumer ownership (resolved post-tasks):** WP05 delivers the mechanism entirely
  inside `emitter.py` — both swallow sites fixed + the `captured_failures()`/`reset_captured_failures()`
  read API. The concrete command-boundary **consumer** is delivered by **WP04's T031** at the
  cutover-command epilogue (`migrate_cmd.py`), which now `depends_on` WP05. Do NOT reach across
  the boundary from here into command files you do not own; expose the read API and let WP04
  consume it. (This closes post-tasks finding MAJOR-1/O-2.)

Anchors: `emitter.py:98` (`_console`), `:853` (`EventEmitter`), `:1012` (first `emit_*`),
`:2114`, `:2334`.

### T026 — Rate-limit the loud path (no per-event warning-storm)

Guard both sites so a burst of unrecoverable failures does not emit one warning per event.

- Deduplicate/throttle the `_console.print` (e.g. print-once-per-distinct-failure keyed on
  site + exception type, or a bounded count with an "N more suppressed" summary surfaced at the
  epilogue) while still **counting every failure** in the T025 counter — suppression is for the
  human warning only, never for the machine signal (INV-1 must still see the true count, so the
  epilogue's non-zero/report decision is on real data).
- Apply the throttle at **both** sites (`emitter.py:2114`, `:2334`) via the shared surface, so
  a mixed burst across the two sites is still bounded, not doubled.
- Add a red-first test in `tests/sync/test_emitter_observability.py`: force many consecutive
  capture failures (e.g. 50), assert the warning is emitted at most once (or the bounded cap)
  **and** the counter equals the true failure count (50). Capture console output via the test
  harness rather than asserting on the live terminal.
- Rationale: WP03 makes the common case succeed, so a storm here means a real systemic fault —
  it should be loud once and counted fully, not drown the console (plan.md:185,
  research.md:52-54). A per-event flood is a reviewer-reject shape.

---

## Branch Strategy

- **Planning base / merge target**: `fix/legacy-journal-capture-cutover` (both). This WP lands
  on the mission branch, not `main`.
- **Lane worktree**: `branch_strategy: lane` — a per-lane worktree is allocated by the runtime;
  do not hand-construct the path.
- **Prepare the workspace via the resolver — the only supported entry point**:

  ```
  spec-kitty agent action implement WP05 --agent <name>
  ```

- **Dependency gate**: WP03 must be `approved` or `done` before WP05 can be claimed
  (dependency readiness; CLAUDE.md Status Model). Do not start against an unmet dependency.
- Do NOT modify files outside `owned_files`. Do NOT commit from this authoring step.

---

## Test Strategy

- **Red-first (C-011)**: every subtask that changes behavior lands its failing test first
  (T022 before T023/T024; T026's storm test before its throttle). Confirm red against current
  `emitter.py`, then green.
- **Isolation is mandatory**: all tests use isolated temp roots via `SPEC_KITTY_HOME` / `HOME`
  fixtures. Never touch the live machine-global `~/.spec-kitty` — this box is a live legacy root
  (plan.md:30, research.md:120-121).
- **Two independent assertions per failure path**:
  1. **Non-fatal** — no exception escapes any public `emit_*` call when the inner write raises.
  2. **Observable** — the process-level flag is set / counter incremented, and the epilogue
     surfaces it.
- Run the new file green and confirm no collateral red in the emitter suite:

  ```
  SPEC_KITTY_SYNC_DISABLE=1 PWHEADLESS=1 .venv/bin/python -m pytest \
    tests/sync/test_emitter_observability.py -q
  ```

  (`SPEC_KITTY_SYNC_DISABLE=1` avoids the pre-review full-suite hang; use `.venv/bin/python`,
  not bare `uv run`, per CLAUDE.md.)
- Do NOT run the full suite in-session (≈1h, breaks the session). Targeted only; CI is the
  release authority.

---

## Definition of Done

- [ ] **Both** swallow sites fixed: `_capture_to_journal` (`emitter.py:2114-2115`) and
      `_emit_for_project_context` (`emitter.py:2334-2335`) record into the process-level
      captured-failure surface.
- [ ] A genuinely-unrecoverable capture failure is **boundary-observable** — the command
      epilogue inspects the flag/counter and reports (or non-zero-exits).
- [ ] **Non-fatal preserved**: `_emit`'s never-raises contract (`emitter.py:2130`) is intact;
      no exception escapes any `emit_*` caller; the ~30 `emit_*` signatures are unchanged.
- [ ] The loud path is **rate-limited** — no per-event warning-storm; the counter still reflects
      the true failure count.
- [ ] New `tests/sync/test_emitter_observability.py` is green (non-fatal + observable + throttle
      pins), authored red-first, temp-root isolated.
- [ ] `ruff check .` and `mypy` clean on the changed files — no new `# noqa` / `# type: ignore`
      / per-file ignores.
- [ ] Coordination note left on #3391 (fold, do not collide).

---

## Risks & Reviewer Guidance

- **Breaking the never-raises contract (highest risk).** The tempting-but-wrong fix is to
  re-raise from `_emit` / the helpers so the failure "propagates". That crashes ~30 `emit_*`
  call sites that assume emission never throws. **Reviewer action**: grep the `emit_*` callers
  and confirm none can now receive an exception —
  `grep -rn "\.emit_" src/specify_cli | head` plus a read of `_emit`'s docstring
  (`emitter.py:2130`). Confirm the observability signal is out-of-band (flag/counter), not an
  exception. The T022 non-fatal pin is the regression guard; it must exist and be green.
- **Warning-storm.** Because WP03 makes the common case succeed, a residual failure is
  systemic — one loud-once warning plus a full count is correct; a per-event flood is a
  reviewer reject. Confirm T026's throttle test asserts both the bounded warning count and the
  true counter.
- **#3391 coordination.** The swallow shape belongs to #3391 (MOES-Media). Confirm a
  coordination note exists and that this WP folds — not duplicates — the fix (C-001/C-004,
  spec.md:178-181). Do not ship a second competing surface.
- **Scope discipline.** Only `emitter.py` + the new test file are `owned_files`. The command
  epilogue wiring must consume the emitter's flag API without widening the blast radius into
  other packages; if the epilogue truly needs an edit outside `owned_files`, flag it for a
  sibling WP rather than reaching across the boundary here.
- **Record content leakage.** Reviewer should confirm the recorded failure entries carry only
  a site label and an exception summary — no event payload, correlation ids, or credential
  material. The emitter is the identity-selection surface; the captured-failure record must not
  become an accidental exfiltration channel at the epilogue.
- **Reset hygiene.** Confirm `reset_captured_failures()` runs at command entry so a long-lived
  process (or a mission that emits across many commands) does not accumulate a stale count that
  makes a later, clean command non-zero-exit on someone else's failure.

## Reviewer Checklist (quick)

- [ ] `grep -rn "\.emit_" src/specify_cli | head` — no `emit_*` caller can now receive an
      exception; signatures unchanged.
- [ ] `_emit` docstring at `emitter.py:2130` still reads "Non-blocking: never raises" and is
      still true.
- [ ] Both `except` handlers (`emitter.py:2114`, `:2334`) record into the surface AND warn
      (throttled), in that order.
- [ ] T022 non-fatal + observable pins and T026 throttle+count pin are present and green.
- [ ] Coordination note on #3391 present; no duplicate surface shipped.
