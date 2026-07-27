---
work_package_id: WP01
title: Dead-code gate — first-party dynamic-access awareness
dependencies: []
requirement_refs:
- FR-001
- FR-016
- NFR-002
tracker_refs:
- '2559'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/_symbol_key.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/_symbol_key.py
role: implementer
tags: []
shell_pid: "3019175"
shell_pid_created_at: "1783953675.37"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read, in order:
[spec.md](../spec.md) FR-001/FR-002 + NFR-002, [plan.md](../plan.md) §IC-01 and the "Lane & WP shaping
directives" (this WP MUST stay Lane-0-local by extending existing files — it must NOT spawn a new arch
file), and the contract [contracts/dead-code-dynamic-access.md](../contracts/dead-code-dynamic-access.md).

## Objective

Teach the dead-code scanner to resolve first-party `module.attr` **dynamic access** (e.g.
`_runtime_bridge_module().get_or_start_run`) as a **live** reference site, so a symbol reachable only via
dynamic access is classified live, not dead. This is pure tooling — **no allowlist-row edits** (those are
owned by WP05). It is the NFR-001 safety predecessor: the whole Lane-0 deshim (WP02→WP05) depends on this
gate becoming the automated proof that a deleted delegate is truly dead.

## Context

- The scanner lives in `tests/architectural/_symbol_key.py` (reachability key) and is exercised by
  `tests/architectural/test_no_dead_symbols.py` (the whole-codebase gate).
- Today a `module.attr` access where `module` is a first-party module object obtained from a local factory
  (the `_runtime_bridge_module()` shape) is **not** counted as a reference — so live façade symbols get
  parked on a permanent allowlist. That is the blind spot #2559 exists to kill.
- The 4 known casualties: `get_or_start_run`, `query_current_state`, `answer_decision_via_runtime`,
  `QueryModeValidationError` (all in `runtime.next.runtime_bridge`).

## Subtask guidance

- **T001 — resolution logic.** In `_symbol_key.py`, extend the reference-collection AST walk so that an
  `ast.Attribute` whose value resolves to a first-party module (import alias, or a call returning a known
  module, e.g. `_runtime_bridge_module()`) records a reference site for `<module>.<attr>`. Resolve the
  **accessor shape generally** — do NOT special-case `runtime_bridge` by name. Scope liveness to
  **first-party module resolution**; do NOT widen to *any* attribute access (that would mask real dead code
  — see the contract's anti-goals). Keep complexity ≤ 15 by extracting a small resolver helper.
- **T002 — positive-direction AST test.** Add a fixture-based test to `test_no_dead_symbols.py` proving a
  symbol referenced ONLY via first-party dynamic access is classified **live**. Drive it against a small
  in-memory/tmp fixture module tree, not the live repo tree. **Recorded out-of-map edit**: this WP adds
  fixture-based AST tests to the gate's own module; allowlist ownership stays with WP05 — this is safe
  because Lane 0 is a strict serial chain and WP05 rebases on this file after WP02–WP04.
- **T003 — negative-direction AST test.** Add the companion fixture proving a symbol with **no** static
  import and **no** first-party dynamic access is still classified **dead** (the gate must not go blind).
- **T004 — live-tree verification.** Confirm the 4 known `runtime_bridge` façade symbols now resolve as
  recognised-live via their dynamic accessors WITHOUT any allowlist entry. Do NOT remove their allowlist
  rows here (WP05 owns that removal); just prove reachability is now detected. Run the gate:
  `.venv/bin/python -m pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_dead_modules.py -q`.
- **T005 — gates + tracer.** `.venv/bin/ruff check .` and `.venv/bin/mypy` clean on the diff. Append the
  ratchet/parity catalog rows (below).

## Branch Strategy

Planning artifacts were generated on `feat/test-suite-friction-remediation`. This WP branches from the
mission base during `/spec-kitty.implement` (per-lane worktree, `lanes` topology) and merges back into
`feat/test-suite-friction-remediation`. **Lane 0 is a strict serial chain — WP01 lands first.**

## Definition of Done (non-fakeable — NFR-002)

- [ ] `_symbol_key.py` resolves first-party `module.attr` dynamic access as a live reference, generally
      (no `runtime_bridge` name special-case).
- [ ] Focused AST fixtures exercise **both** directions: dynamic-access→live AND unreferenced→dead, against
      fixtures (not the live tree only).
- [ ] The 4 known façade symbols (`get_or_start_run`, `query_current_state`, `answer_decision_via_runtime`,
      `QueryModeValidationError`) are recognised-live by the scanner without needing an allowlist row
      (verified in-place; row removal is WP05).
- [ ] `pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_dead_modules.py`
      green on the real tree.
- [ ] `ruff` + `mypy` clean on the diff; complexity ≤ 15.
- [ ] **Tracer (FR-016 / NFR-007):** append a row to `../tracer-design-decisions.md` cataloguing the
      dead-code gate as a ratchet suite (columns: category = reachability-ratchet, pins-invariant-or-shape =
      *invariant* now that dynamic access is seen, CaaCS churn, verdict = keep/consolidate/retire hypothesis)
      AND log any tooling friction hit to `../tracer-tooling-friction.md`. Dated, in-the-moment.

## Risks

- **False-positive liveness** could hide a truly-dead symbol — the negative-direction fixture (T003) is the
  guardrail; keep the resolver scoped to first-party module objects only.
- **Over-broad accessor matching** — resolve the general dynamic-accessor shape; do not hard-code the
  runtime_bridge accessor. A too-narrow match re-opens the blind spot; a too-broad match masks dead code.

## Reviewer guidance (reviewer-renata, opus, in the loop)

- Confirm the resolver is name-agnostic (grep the diff for any literal `runtime_bridge` in `_symbol_key.py`
  → must be 0).
- Confirm both AST directions are fixture-driven, not tautological restatements of the live tree.
- Confirm zero allowlist rows were touched in this WP (that is WP05's surface).

## Activity Log

- 2026-07-13T14:12:14Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – Assigned agent via action command
- 2026-07-13T14:38:54Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – dead-code dynamic-access resolver committed 7b1f56b03; agent stalled post-commit
- 2026-07-13T14:41:22Z – claude:opus:reviewer-renata:reviewer – shell_pid=3019175 – Started review via action command
- 2026-07-13T15:02:35Z – user – shell_pid=3019175 – Approved: all 5 functional checks passed (reviewer-renata); reject basis (missing tracer) was a stale lane-branch read — WP01 tracer entry + WP05 fold-in flag ARE on mission branch HEAD; commit citation true. WP05 must fold the overlay into _imports_by_target when removing the 4 rows.
