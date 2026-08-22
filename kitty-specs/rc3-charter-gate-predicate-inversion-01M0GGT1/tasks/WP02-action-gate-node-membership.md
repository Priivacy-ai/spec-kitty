---
work_package_id: WP02
title: Action gate — node-URN membership predicate + vocabulary fold (surface A,
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-007
- FR-008
- FR-015
- NFR-001
planning_base_branch: pr/rc3-charter-gate-predicate-inversion
merge_target_branch: pr/rc3-charter-gate-predicate-inversion
branch_strategy: Planning artifacts for this mission were generated on pr/rc3-charter-gate-predicate-inversion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/rc3-charter-gate-predicate-inversion unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-charter-gate-predicate-inversion-01M0GGT1
base_commit: d82052e660f6042db6a45bb00b4e523ba7e6dde5
created_at: '2026-08-21T12:52:37.518378+00:00'
subtasks: []
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/context.py
create_intent:
- tests/charter/test_action_gate_single_load.py
- tests/charter/test_interview_action_acceptance.py
execution_mode: code_change
owned_files:
- src/charter/context.py
- src/charter/interview.py
- src/charter/compiler.py
- src/specify_cli/cli/commands/charter/context.py
- tests/charter/test_every_load_delivery.py
- tests/charter/test_context_schema_version_ledger.py
- tests/charter/test_context.py
- tests/charter/test_action_gate_single_load.py
- tests/charter/test_interview_action_acceptance.py
role: implementer
tags:
- charter
- action-gate
- red-by-design
tracker_refs: []
---

# WP02 — Action gate: node-URN membership + vocabulary fold (#3596)

## Context (see plan.md §1–§2, ADR)
Both `context.py` gates (`:255` plain-text, `:484` JSON) short-circuit any non-bootstrap action to `compact` before the bundle is built. Replace with a predicate on the declared DRG node. Fold the three copies of the 4-token frozenset into one fast-path constant.

**Every new test file MUST declare a routed `pytestmark` (CI collection gate, POST-TASKS §pedro):** `tests/charter/…` → `pytestmark = [pytest.mark.fast, pytest.mark.unit]` — use `pytest.mark.doctrine` (and add `pytest.mark.corpus`) instead of/with `unit` if the test reads the built-in DRG via `load_validated_graph` on `packs/built-in/**`.

## Red-first (ATDD — commit tests FIRST, RED on base)
1. **Reverse** `tests/charter/test_every_load_delivery.py::test_json_non_bootstrap_action_is_explicitly_ruled_out` and `tests/charter/test_context_schema_version_ledger.py::test_non_bootstrap_action_carries_stamped_version` (cite by NAME — line anchors drifted to :95) — `build_charter_context_json(action="tasks", mission_type="software-dev")` now returns `mode=bootstrap` + non-empty `directives`. Reference the ADR in the test docstring. Do NOT fix back.
2. **AC-3 retrospect half (owned, not a prose sweep — POST-TASKS §renata):** an owned red-first test asserts `build_charter_context_json(action="retrospect", mission_type="documentation")` **and** `…mission_type="research"` deliver `mode=bootstrap` + non-empty grain (the retrospect nodes are on-demand sequence-orphans per ADR/FR-015; a regression that starves them must red here).
3. **AC-2 companion** in `tests/charter/test_context.py`: `mission_type="software-dev"` + a genuinely undeclared action → `mode=compact` (isolates node-membership, not type-resolution). Keep `test_non_bootstrap_action_returns_compact` (`custom-action`, typeless) green.
4. **NEW `tests/charter/test_action_gate_single_load.py`** (NFR-001): patch `charter._drg_helpers.load_validated_graph` with a call counter; assert `build_charter_context_json(action="tasks", mission_type="software-dev")` triggers exactly **one** load. First **verify `_resolve_action_bundle` itself loads the graph once** (else the counter reds regardless of gate placement).
5. **NEW `tests/charter/test_interview_action_acceptance.py`** (AC-8): a `local_supporting_files` entry with `action: tasks` is retained, not warn-dropped.
6. **AC-7 structural guard (POST-TASKS §renata):** a cheap regression asserting a **single** definition site for the 4-token constant (e.g. `interview` imports the one `BOOTSTRAP_ACTIONS`, or an AST/grep guard) so a future fourth copy reds.

## Implementation
- **FR-001/003/004:** at both gates, resolve the bundle once (reuse `_resolve_action_bundle` → `.merged` carrier), then `bundle.merged is not None and f"action:{resolved_type}/{action}" in bundle.merged.node_urns()` (`src/doctrine/drg/models.py:413`). A declared-but-starved node → `bootstrap` + empty arrays is legitimate. Typeless → `None` → `compact`. NO memoization (the per-call carrier guarantees single-load).
- **FR-002:** keep the 4-token fast path (return `bootstrap` for `specify/plan/implement/review` without resolving the bundle).
- **FR-007:** one constant named for its fast-path role (e.g. keep `BOOTSTRAP_ACTIONS`); remove `interview.py:34 _KNOWN_ACTIONS` as a copy. **Also update the third consumer** `src/specify_cli/cli/commands/charter/context.py:199` — print the display header on `mode==bootstrap`, not set-membership (so now-delivering `tasks`/`retrospect` get their header).
- **FR-008:** interview validation consults the fast-path constant **plus** a declared-node source (two inputs); accept any label present on some action node (type-agnostic). Do not let the fast-path set become the closed acceptance allowlist.
- **FR-015:** record that action grain is delivered by direct `action:<type>/<step>` URN + `scope` edges; the retrospect nodes are on-demand sequence-orphans (acceptance note, per ADR).

## DoD / validation surface
`PWHEADLESS=1 pytest tests/charter/ -q` green; the two reversed tests + the new load-count + interview-acceptance tests pass; AC-1 bootstrap-unchanged for the 4 built-ins; ruff + mypy clean. **File the `_KNOWN_ACTIONS`-fold tracker issue and assign HiC before landing (DIR-012).**
