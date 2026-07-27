---
work_package_id: WP02
title: '`next` typed-error pass-through + M1 context-resolve'
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
tracker_refs: []
planning_base_branch: feat/read-path-error-fidelity
merge_target_branch: feat/read-path-error-fidelity
branch_strategy: Planning artifacts for this mission were generated on feat/read-path-error-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-path-error-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T038
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2585018"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/runtime/next/runtime_bridge.py
create_intent:
- tests/specify_cli/cli/commands/test_next_typed_error_passthrough.py
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge.py
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/context/resolver.py
- tests/specify_cli/cli/commands/test_next_typed_error_passthrough.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before any code, load the implementer profile and the binding contracts. Run:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order:

1. `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/spec.md` — **FR-001** (typed-error
   pass-through, the cheapest high-leverage cut) and **FR-002** (`next` typed diagnostics), plus
   **C-001** (no new authority).
2. `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/plan.md` — **IC-02** and decision **D-7**
   (M1 fold-in).
3. `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/contracts/behavioral-contracts.md` — the
   **C-IC02** contract (`next` typed-error pass-through obligations + the deletion proof).
4. `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/research/live-repro.md` — the **#15** repro
   (the exact failing path `runtime_bridge.py:3130` → `next_cmd.py:469-470`).
5. `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/research/investigation-2/debbie-reverify-missed.md`
   — the **M1** missed surface and the recurring naming-rider shape.

## Objective

Preserve `ActionContextError.code` **and** its `checked_paths` across the `next`-family catch-sites
and the net-new `context mission-resolve` surface (M1), instead of collapsing the typed error into a
generic `MISSION_NOT_FOUND` / "check the slug". This closes #12 / #14 / #15 (+ M1) **with no resolver
change** (C-001 — adopt, do not build).

The disease (live-confirmed, #15): the resolver produces a precise typed error
(`COORDINATION_BRANCH_DELETED`, a `STATUS_READ_PATH_NOT_FOUND` subclass) with the real repair
remediation, and `next` discards all of it and substitutes `MISSION_NOT_FOUND` + "run mission list" —
pointing the operator the wrong way (the mission is not missing; the read-path is broken). The fix is
verbatim pass-through: catch the `ActionContextError`, preserve its `code` + `checked_paths`, and
surface them through the JSON envelope with a **read-path** remediation.

Concretely — enumerate **ALL** next-family collapse sites (the earlier "three catch-sites" framing
missed a fourth raise):

- `runtime_bridge.py:3128-3130` (`query_current_state`): stop `raise MissionNotFoundError(...) from
  exc`; preserve the typed `code` + `checked_paths`.
- `runtime_bridge.py:3132-3134` (`query_current_state`, the **second** `MissionNotFoundError` raise on
  the resolved-but-not-on-disk / `not feature_dir.is_dir()` branch): decide explicitly whether this is
  a genuine missing mission (legitimately `MISSION_NOT_FOUND`) or a read-path miss masquerading as
  `MISSION_NOT_FOUND` — and if the latter, preserve the typed `ActionContextError.code` +
  `checked_paths` here too. Do not leave it silently uncovered (the deletion proof will not catch it
  otherwise).
- `runtime_bridge.py:3265-3274` (`answer_decision_via_runtime`): preserve the code **identically** on
  the decision-answer path.
- `next_cmd.py:361` (`_resolve_mission_slug`): stop the collapse
  (`raise MissionNotFoundError(raw_handle) from exc`); carry the typed code through.
  > ⚠️ **Symbol fix:** the canonical function is **`_resolve_mission_slug`** (def `next_cmd.py:323`;
  > the collapse is at `:361`), **NOT** `_find_mission_slug`. `_find_mission_slug` is a **DIFFERENT**
  > function living in `agent/status.py:58` — do **NOT** edit that file. An implementer grepping for
  > `_find_mission_slug` in `next_cmd.py` finds only a comment and could edit the wrong module.

Each collapse site above MUST preserve `ActionContextError.code` + `checked_paths`.
- `next_cmd.py:374-408` (emitter): surface the typed code + checked paths in the JSON envelope,
  **mirroring** the existing `QueryModeValidationError` branch at `next_cmd.py:474-491` (which already
  threads a typed code + actionable `next_step` into the envelope). Copy the correct reference pattern
  from `agent context resolve` (`src/specify_cli/cli/commands/agent/context.py:158`).
- **M1 (T038):** `src/specify_cli/context/resolver.py:164` flattens the typed error into
  `FeatureNotFoundError("…Check that the mission slug is correct.")`, dropping `exc.code` +
  checked-paths + remediation. Apply the **same** fix — preserve the resolver's `.code` and
  checked-paths (copy the `agent/context.py:88-93` translation pattern, which already preserves the
  signal).

## Context (binding discipline)

- **Function-over-form + verification-by-deletion.** The proof adoption is complete is the **deletion
  proof** in C-IC02: removing the `MISSION_NOT_FOUND` collapse at the catch-sites keeps the suite green
  because the typed envelope now flows through. Do not re-wrap the typed error in a new error type.
- **TDD-first.** Write `test_next_typed_error_passthrough.py` first (T007). It must FAIL on HEAD: today
  `next` on a read-path miss emits `MISSION_NOT_FOUND`.
- **Topology-true fixtures (NFR-002).** Reproduce the #15 topology faithfully: a single git repo with
  one mission whose `meta.json` declares a `coordination_branch` but with **no coord branch and no
  coord worktree materialized** (the #1718/#1692 fail-closed trigger). Use a **full 26-char ULID**
  `mission_id` (e.g. `01KV8NPC…`, 26 chars) — **NO fabricated short id**. The mission dir + spec exist
  on disk. Assert `next --json` emits the typed read-path code (`STATUS_READ_PATH_NOT_FOUND` /
  `COORDINATION_BRANCH_DELETED`) and the checked paths, NEVER `MISSION_NOT_FOUND`.
- **Quality gates (NFR-004).** `ruff` + `mypy` zero issues, **complexity ≤ 15**, **no suppressions**.
- **WP01 dependency.** This WP consumes the frozen/factory-built `ExecutionContext` from WP01; it does
  not touch the resolver construction itself (C-001).

## Subtasks

### T007 — TDD: next read-path-miss → typed code, not MISSION_NOT_FOUND
- Add `tests/specify_cli/cli/commands/test_next_typed_error_passthrough.py`.
- Build the topology-true #15 fixture (coord declared, no coord worktree; full 26-char ULID).
- Drive `spec-kitty next --mission <slug> --json` (query path) and assert the JSON `error_code` is the
  **exact witnessed code** the live resolver produces for this fixture
  (`COORDINATION_BRANCH_DELETED` — a `STATUS_READ_PATH_NOT_FOUND` subclass), the payload carries a
  non-empty `checked_paths` containing the coord candidate path, and the remediation is a **read-path**
  remediation — **NOT** `MISSION_NOT_FOUND` / "run mission list". Positive-only "emits the resolver's
  real code" is **insufficient**: pin the most-specific witnessed code, not the parent code or "any
  non-mission-not-found code".
- **Captured-red (BLOCKER, hard requirement — not prose):** the test MUST FAIL FIRST on HEAD with the
  witnessed-wrong value (HEAD emits `MISSION_NOT_FOUND`). Capture the red output (e.g. run against
  `git stash`-ed source) and paste it into the Activity Log so the green after the fix is trustworthy.
  A test written after the fix, or one that passes on HEAD, is a gaming defect. Assert that the
  pre-fix value would be `MISSION_NOT_FOUND` (broken-baseline expectation) so the delta is visible.
- **Validation:** FAILS on HEAD (emits `MISSION_NOT_FOUND`); run
  `python -m pytest tests/specify_cli/cli/commands/test_next_typed_error_passthrough.py`.

### T008 — Preserve code+paths at runtime_bridge query_current_state
- Remove the `raise MissionNotFoundError(mission_slug) from exc` collapse; let the typed
  `ActionContextError` (with `code` + `checked_paths`) propagate to the command layer.
- **file:line:** `src/runtime/next/runtime_bridge.py:3128-3130`.
- **Validation:** the query path no longer constructs `MissionNotFoundError` from an
  `ActionContextError`.

### T009 — Preserve code+paths at runtime_bridge answer_decision_via_runtime
- Apply the identical pass-through on the decision-answer path so the code survives there too
  (**C-IC02:** the decision-answer path MUST preserve the code identically).
- **file:line:** `src/runtime/next/runtime_bridge.py:3265-3274`.
- **Validation:** a decision-answer on the #15 topology surfaces the same typed code as the query path.

### T010 — Preserve code at next_cmd _resolve_mission_slug
- Stop the collapse in **`_resolve_mission_slug`** (def `next_cmd.py:323`; collapse
  `raise MissionNotFoundError(raw_handle) from exc` at `:361`); carry the typed `ActionContextError`
  code through to the emitter.
- ⚠️ **Symbol fix:** the function is **`_resolve_mission_slug`**, NOT `_find_mission_slug`.
  `_find_mission_slug` is a different function in `agent/status.py:58` — do NOT edit it.
- **file:line:** `src/specify_cli/cli/commands/next_cmd.py:361` (collapse), def `:323`.
- **Validation:** no reclassification to `MISSION_NOT_FOUND` in this helper.

### T011 — Emitter surfaces typed code+paths (mirror QueryModeValidationError)
- Update the emitter to surface the typed `code` + `checked_paths` + read-path remediation in the JSON
  envelope, mirroring the existing `QueryModeValidationError` branch (the reference for how a typed
  code + actionable `next_step` reaches the envelope — folds #1911's richer `next_step`).
- **file:line:** emitter at `src/specify_cli/cli/commands/next_cmd.py:374-408`; reference branch at
  `:474-491`; correct translation reference at `agent/context.py:158`.
- **Validation:** T007 now passes (envelope carries the typed code + paths + read-path remediation).

### T012 — Verification-by-deletion: collapse removed, suite green
- Confirm the `MISSION_NOT_FOUND` collapse is *removed* (not flagged off) at **every** next-family
  collapse site — `runtime_bridge.py:3128-3130` + `:3132-3134` + `:3265-3274`, and
  `next_cmd.py:361` — and run the full suite. (The earlier "three catch-sites" count missed the
  `:3132-3134` raise; reconcile to these four sites.) Each must preserve
  `ActionContextError.code` + `checked_paths` or — for `:3132-3134` only — carry a *consciously
  decided* `MISSION_NOT_FOUND` if it is a genuine missing mission (see Objective).
- **Validation:** full suite green (parallel run per CLAUDE.md); the deletion proof of C-IC02 holds.

### T038 — M1: context mission-resolve preserves the typed code
- Fix `context mission-resolve` (`src/specify_cli/context/resolver.py:164`): stop flattening
  the typed `ActionContextError` into `FeatureNotFoundError("…Check that the mission slug is
  correct.")`. Preserve `exc.code` + checked-paths + remediation (same #15 class on a different
  operator entrypoint). Copy the `agent/context.py:88-93` pattern.
- Add a topology-true assertion in the test module: `context mission-resolve` on the #15 fixture emits
  the resolver's real code, not "check the slug".
- **file:line:** `src/specify_cli/context/resolver.py:164`.
- **Validation:** the M1 assertion passes; verification-by-deletion — removing the flatten keeps the
  suite green.

## Branch Strategy

Planning artifacts were generated on **feat/read-path-error-fidelity**. During
`/spec-kitty.implement` this WP may branch from a dependency-specific base (WP01 must be approved
first — it is the precondition), but completed changes **merge back into
feat/read-path-error-fidelity** unless the human explicitly redirects the landing branch. The
execution workspace (worktree) is the one `spec-kitty implement WP02` resolves from `lanes.json` — do
not reconstruct the path by hand.

## Definition of Done

- [ ] `tests/specify_cli/cli/commands/test_next_typed_error_passthrough.py` added; T007 **FAILED FIRST
      on HEAD with the witnessed-wrong value** (`MISSION_NOT_FOUND`), the **captured red is pasted into
      the Activity Log**, and the test passes after the fix (TDD-first witnessed), using a topology-true
      coord-declared-no-worktree fixture with a full 26-char ULID. A positive-only test that does not
      capture the red is a gaming defect.
- [ ] `next` (query path) on a read-path miss emits the **exact witnessed code**
      (`COORDINATION_BRANCH_DELETED` and/or `STATUS_READ_PATH_NOT_FOUND` — the most-specific code the
      live resolver produces, not the parent or "any non-mission-not-found code") + non-empty checked
      paths + a read-path remediation (**C-IC02**).
- [ ] `next` **MUST NOT** emit `MISSION_NOT_FOUND` / "run mission list" for a read-path miss
      (**C-IC02**).
- [ ] The decision-answer path (`answer_decision_via_runtime`) preserves the code identically
      (**C-IC02**).
- [ ] The `MISSION_NOT_FOUND` collapse is **deleted** at **all four** next-family raise sites
      (`runtime_bridge.py:3128-3130` + `:3132-3134` + `:3265-3274`, `next_cmd.py:361`); the
      `:3132-3134` resolved-but-not-on-disk branch was explicitly decided (genuine not-found vs
      read-path miss); the suite stays green (**C-IC02 deletion proof**).
- [ ] **M1:** `context mission-resolve` preserves the typed code (no "check the slug" flatten).
- [ ] No new error type or resolver introduced (**C-001**).
- [ ] `ruff check .` clean, `mypy` clean on the three owned source files, every touched function at
      **complexity ≤ 15**, **no suppressions** added.
- [ ] Full suite green (parallel run).

## Risks / reviewer guidance

- **Stale/misleading comment at `runtime_bridge.py:3129`.** The in-code comment there attributes the
  collapse to "FR-004 / WP03" (the same comment rides the `:3132-3134` branch). That attribution is
  **misleading/stale** — the collapse is owned by **THIS WP** (FR-001/FR-002), not FR-004/WP03. Do NOT
  trust it; correct or remove the comment as part of the deletion so it no longer claims another WP
  owns the collapse, and do not leave a half-fix because the comment implies the behavior is
  intentional elsewhere.
- **Wrong symbol trap (`next_cmd.py`).** The canonical function is **`_resolve_mission_slug`** (def
  `:323`, collapse `:361`), NOT `_find_mission_slug`. `_find_mission_slug` is a different function in
  `agent/status.py:58` — editing it is a wrong-file regression.
- **No-suppression rule.** The edited `query_current_state` may already carry a `# noqa: C901`. Do NOT
  add suppressions and do NOT rely on the inherited one — if your edit changes complexity, extract
  small helpers to keep every touched function at **complexity ≤ 15** (NFR-004). Removing the inherited
  `# noqa` once the function is ≤15 is the correct boy-scout move; leaving it as a crutch is not.
- **Two pass-through sites, not one.** The decision-answer path (`:3265-3274`) is easy to miss; C-IC02
  requires it to preserve the code *identically*. Reviewer: assert both query and decision-answer
  surface the same typed code on the same fixture.
- **Mirror the existing QueryModeValidationError branch — do not invent a new envelope shape.** The
  emitter already knows how to thread a typed code + actionable `next_step` (the #1911 reference). Copy
  that shape so the JSON contract stays stable.
- **M1 is the same disease on a different door.** `context mission-resolver.py:164` is a separate
  operator entrypoint; folding it here keeps the fix coherent. Use the `agent/context.py:88-93`
  translation that already preserves the signal — do not hand-roll a new translation.
- **Read-path remediation, not mission-list remediation.** The whole point is fidelity: the remediation
  must match the real failure class (read-path repair / flatten the mission), never "run mission list".
- **WP01 ordering.** This WP depends on WP01 (frozen factory). Do not start the pass-through work
  against the still-mutable composite.

## Activity Log

- _(empty — append implementation notes during /spec-kitty.implement)_
- 2026-06-16T21:03:38Z – claude:opus:python-pedro:implementer – shell_pid=2432976 – Assigned agent via action command
- 2026-06-16T21:29:23Z – claude:opus:python-pedro:implementer – shell_pid=2432976 – Ready: 4 next-family sites + M1; ground-truth captured-red (COORDINATION_BRANCH_DELETED); 495 next tests green; removed noqa C901
- 2026-06-16T21:29:32Z – claude:opus:reviewer-renata:reviewer – shell_pid=2585018 – Started review via action command
- 2026-06-16T21:40:24Z – user – shell_pid=2585018 – Review PASS (renata): 4 next-family sites + M1; captured-red genuine; C-001 held; suite green
