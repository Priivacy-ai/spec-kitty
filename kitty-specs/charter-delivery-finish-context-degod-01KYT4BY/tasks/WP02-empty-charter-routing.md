---
work_package_id: WP02
title: 'US1: empty-charter routing fallback + warning (#3064)'
dependencies: []
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-006
planning_base_branch: feat/charter-delivery-finish-context-degod
merge_target_branch: feat/charter-delivery-finish-context-degod
branch_strategy: Planning artifacts for this mission were generated on feat/charter-delivery-finish-context-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-delivery-finish-context-degod unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-delivery-finish-context-degod-01KYT4BY
base_commit: 40e01d6b9005622be202e6d689467897c259e761
created_at: '2026-07-30T20:02:15.927154+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
history:
- at: '2026-07-30'
  actor: planner-priti
  note: WP authored from plan IC-02 + post-plan squad (composite predicate + surgical seam).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/invocation/
create_intent:
- src/specify_cli/invocation/empty_charter.py
- tests/specify_cli/invocation/test_empty_charter_fallback.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/invocation/empty_charter.py
- src/specify_cli/invocation/executor.py
- src/specify_cli/invocation/router.py
- src/specify_cli/cli/commands/dispatch.py
- tests/specify_cli/invocation/test_empty_charter_fallback.py
- tests/specify_cli/invocation/cli/test_dispatch.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```
Apply the resolved initialization/boundaries/directives/tactics; confirm which in one line, then proceed.

## Objective

Implement issue **#3064** routing half: when a dispatch auto-routes under a **wholly-empty charter**, pin the `generic-agent` and warn the user — **without** mutating the shared activation gate or `ProfileRegistry` (so explicit `--profile` still works). The governance-context scoping (FR-010) and the default asset (FR-005) are **WP03**.

Design authority: [`../spec.md`](../spec.md) (US1, FR-002/003/004/006), [`../contracts/empty-charter-fallback.md`](../contracts/empty-charter-fallback.md), [`../research.md`](../research.md) (Decisions 2, 3, 5, 11).

## Critical context (verified against code — do not re-litigate the seam)

- **Seam = the executor auto-route branch** `src/specify_cli/invocation/executor.py:255-259` (`elif self._router is not None:` / no-profile-hint path). This is the ONLY auto-route entry point (verified). Do NOT touch `ProfileRegistry` or the `charter/resolver.py` three-state gate.
- **Composite empty-charter predicate** (a narrower one FALSE-fallbacks on a configured repo):
  ```
  pc = PackContext.from_config(repo_root)
  is_empty = (charter_activated_urns(repo_root) == set())
             and pc.activated_agent_profiles is None
             and pc.activated_mission_step_contracts is None
             and pc.activated_glossary_packs is None
             and pc.org_roots == ()
  ```
  (`anti_pattern` is NOT charter-activatable → excluded.)
- `generic-agent` is a shipped built-in profile (`src/doctrine/agent_profiles/built-in/generic-agent.agent.yaml`) resolved through the ungated built-in repo. Pin it as a constant `GENERIC_AGENT_ID`.
- `RouterDecision.confidence` is a `Literal` (`router.py:161`); widen it. `router.route()` raises on no-match — the `resolve_generic_fallback(...) or self._router.route(...)` short-circuit must pre-empt that for the empty-charter case.
- **Payload footgun**: `InvocationPayload.__init__(**kwargs)` only sets provided keys and `to_dict` does `getattr(self, s, None)`. Always thread `empty_charter_fallback=` at the single construction site, and read via `getattr(payload, "empty_charter_fallback", False)` in `dispatch.py`.
- `self._repo_root` is available on the executor (set in `__init__`).

## Subtasks

### T006 — Red-first predicate + decision-shape test
Create `tests/specify_cli/invocation/test_empty_charter_fallback.py`. Truth table (RED before T007):
- nothing activated, no org packs → `resolve_generic_fallback` returns a decision with `profile_id == "generic-agent"`, `confidence == "generic_fallback"`, action derived from the request verb;
- URN-only / agent-profile-only (incl. `[]`) / glossary-pack-only / mission-step-contract-only / org-pack-present → returns `None`.
Build temp `.kittify/config.yaml` fixtures with realistic activation shapes.

### T007 — `empty_charter.py::resolve_generic_fallback`
New module `src/specify_cli/invocation/empty_charter.py`: `GENERIC_AGENT_ID = "generic-agent"`; `resolve_generic_fallback(repo_root, request_text) -> RouterDecision | None` applying the composite predicate; derive the action from the request verb reusing the router's canonical verb map (import, do not duplicate). Keep it pure of side effects beyond config reads. Complexity ≤ 15.

### T008 — Wire the executor + payload flag
At `executor.py:255-259`: `result = resolve_generic_fallback(self._repo_root, request_text) or self._router.route(request_text)`. Add an `empty_charter_fallback: bool` slot to `InvocationPayload` and **thread it at the single construction site** (default `False`). Ensure `to_dict` serializes it.

### T009 — Widen the `RouterDecision.confidence` Literal
Add `"generic_fallback"` to the `Literal[...]` in `router.py` and update the enumerating comment(s). Grep for any `match`/exhaustiveness over `.confidence` (there is none today) — keep mypy --strict clean.

### T010 — One-shot warning in `dispatch.py`
In `cli/commands/dispatch.py::_render_rich_payload`, when `getattr(payload, "empty_charter_fallback", False)` is true, render a single yellow panel: no charter activations found → routed to the generic agent; advise activating a charter or copying the scaffold (`spec-kitty doctrine asset path common-charter-scaffold-minimal`). `--json` callers get the boolean. Do NOT key the warning off `profile_id == "generic-agent"` (a user may `--profile generic-agent` deliberately).

### T011 — Dispatch integration test
Extend `tests/specify_cli/invocation/cli/test_dispatch.py`: empty charter + no hint → `payload.profile_id == "generic-agent"`, warning present, `--json` shows `empty_charter_fallback: true`, `software-dev` mission type still available; explicit `--profile architect-alphonso` under empty charter → specialist resolves (no fallback). (The governance-agreement assertion on the `Directive IDs:` block is WP03's red-first test.)

## Do NOT touch (regression proof — must stay green)
`tests/specify_cli/test_doctrine_service_factory.py`, `tests/specify_cli/invocation/test_registry_builtin_activation_parity.py`, `tests/charter/test_activation_authority.py`. If any of these go red, your change reached the shared gate — revert and re-seam.

## Branch strategy
Planning base `feat/charter-delivery-finish-context-degod`; merge target `main` (PR). Enter the resolved lane workspace via `spec-kitty agent action implement WP02 --agent claude`.

## Definition of Done
- [ ] T006 red-first truth-table committed before implementation.
- [ ] Composite predicate covers all 5 dimensions; configured-but-narrow charters do NOT fallback.
- [ ] Explicit `--profile` bypasses the fallback; `software-dev` stays available.
- [ ] Warning emitted once; `--json` flag present and defaulted safely.
- [ ] Shared-gate/parity fixtures untouched and green.
- [ ] ruff + mypy --strict clean.

## Risks
- Narrow predicate → false fallback on a configured repo (the exact defect the post-plan squad caught — test all dimensions).
- Payload slot default footgun (thread the kwarg + getattr).

## Reviewer guidance
Verify the seam is the executor branch (not registry); confirm the predicate reads all dimensions; confirm the gate/parity fixtures are untouched (grep the diff for `resolver.py`/`registry.py`/`doctrine_service_factory.py`); RED→GREEN on T006.
