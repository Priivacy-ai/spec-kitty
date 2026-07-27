---
work_package_id: WP07
title: Promote override-adjudication to production
dependencies: []
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: mission/doctrine-governance-fidelity
merge_target_branch: mission/doctrine-governance-fidelity
branch_strategy: Planning artifacts for this mission were generated on mission/doctrine-governance-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/doctrine-governance-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
phase: Lane C — override-governance runtime wiring
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "952174"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/
create_intent:
- tests/doctrine/drg/test_override_policy_predicates.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/override_policy.py
- tests/architectural/test_builtin_override_policy.py
- tests/doctrine/test_drg_merge.py
- tests/doctrine/drg/test_override_policy_predicates.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Promote override-adjudication to production

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` via the `/ad-hoc-profile-load` skill (read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`) and adopt its directives before implementing.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent**: `claude`

---

## Objectives & Success Criteria

- Promote `find_overridden_builtin_urns`, `find_unsanctioned_overrides`, and `UnsanctionedOverride` from the test module `tests/architectural/test_builtin_override_policy.py` into production at `src/doctrine/drg/override_policy.py` — pure, fail-closed, no I/O (FR-009).
- The promoted predicates are importable from `doctrine.drg.override_policy` and exported via `__all__`.
- The existing governance test (`test_builtin_override_policy.py`) and the six `replaceable-builtins` sites in `tests/doctrine/test_drg_merge.py` re-point their imports to production and stay **green** — no test deleted, no assertion softened (NFR-004).
- Lane C foundation: this WP unblocks WP08 (doctor wiring) and WP09 (allowlist retirement). It does NOT delete `override_policy.py`'s allowlist entries — that is WP09 once a runtime caller exists.

**Done when**: the three symbols live in `override_policy.py` (pure + fail-closed); `test_builtin_override_policy.py` imports them from production with its assertions intact and green; `test_drg_merge.py` imports unchanged-and-green; new focused unit tests in `tests/doctrine/drg/test_override_policy_predicates.py` cover sanctioned/unsanctioned/malformed-fail-closed; ruff + mypy clean; complexity ≤ 15.

## Context & Constraints

- **The predicates do NOT exist in production today.** `find_overridden_builtin_urns` / `find_unsanctioned_overrides` / `UnsanctionedOverride` currently live ONLY in `tests/architectural/test_builtin_override_policy.py` (~lines 42–112). `override_policy.py` ships only the allowlist loader (`load_replaceable_builtins`, `ReplaceableBuiltinsPolicy`, `ReplaceableBuiltin`, `POLICY_RELPATH`, `OverridePolicyError`). The promotion is a **move**, not a rewrite — preserve the existing docstrings and the intentional scope note (only `org:`-provenance overrides are adjudicated; project-tier overrides stay OUT of scope, FR-012).
- **`override_policy.py` is a DORMANT governance gate, not dead code.** It is consumed by `test_drg_merge.py` (6 `load_replaceable_builtins` sites) and `test_builtin_override_policy.py`. WIRE it — never delete. The dead-symbol/-module allowlists that currently shield it (`_CATEGORY_C_BUILTIN_OVERRIDE_POLICY`, `_CATEGORY_7_GRANDFATHERED_ORPHANS`) are retired in WP09, not here.
- **Pure + fail-closed (NFR-004):** the promoted predicates take already-loaded inputs (a merged `DRGGraph`, a `frozenset[str]` of built-in URNs, a `ReplaceableBuiltinsPolicy`) and return findings — no filesystem, no merge, no allowlist parsing inside them. Fail-closed semantics already hold in the test copy (`policy.is_allowed` returns `False` for unlisted URNs; directive overrides require a non-empty reason); preserve them byte-for-byte.
- **Imports the promoted code needs:** `DRGGraph` from `doctrine.drg.models`, `NodeKind` (for the directive-URN helper). Keep the existing `_is_directive_urn` private helper alongside the predicates. Avoid import cycles — `override_policy.py` already imports from within `doctrine.drg`; `models` is a sibling and safe.
- **C-005 red-first** through the pre-existing public surface (the override governance test). **C-007** realistic fixtures (real `OrgDRGFragment` / `DRGNode` shapes, not handcrafted stubs). **NFR-003** ruff/mypy clean, complexity ≤ 15, focused test per promoted predicate.

## Subtasks & Detailed Guidance

### Subtask T019 — Promote the three symbols into `override_policy.py`

- **Purpose**: Give the adjudication predicates a production home so a runtime caller (WP08 doctor) can import them.
- **Steps**:
  1. Move `UnsanctionedOverride` (frozen dataclass: `urn`, `kind`, `why`), `find_overridden_builtin_urns(merged, built_in_urns) -> dict[str, str]`, and `find_unsanctioned_overrides(targets, policy) -> list[UnsanctionedOverride]` from the test module into `src/doctrine/drg/override_policy.py`, verbatim in behavior. Bring the `_is_directive_urn` helper with them.
  2. Add the needed imports (`DRGGraph` from `doctrine.drg.models`, `NodeKind`). Keep them at module top, not function-local.
  3. Extend `__all__` to export `UnsanctionedOverride`, `find_overridden_builtin_urns`, `find_unsanctioned_overrides` (and confirm the existing five entries remain).
  4. Preserve the intentional scope docstring on `find_overridden_builtin_urns` (`org:`-provenance only; project-tier deliberately out of scope — this is the FR-012 boundary WP08 documents operator-side).
- **Files**: `src/doctrine/drg/override_policy.py`.
- **Notes**: This is a pure move — do not change return shapes (`{urn: kind}` map; sorted findings list). Keep the module free of side effects on import.

### Subtask T020 — Re-point the consuming tests to production

- **Purpose**: Prove the promotion is behavior-preserving by keeping the governance gate green against the production symbols (C-005: the gate IS the pre-existing public surface).
- **Steps**:
  1. In `tests/architectural/test_builtin_override_policy.py`, DELETE the local definitions of `UnsanctionedOverride` / `find_overridden_builtin_urns` / `find_unsanctioned_overrides` / `_is_directive_urn` and import them from `doctrine.drg.override_policy` instead. Keep every test (`test_builtin_overrides_are_sanctioned`, `test_real_merge_override_is_detected_and_governed`, and the pure-adjudication coverage) and its assertions intact.
  2. Confirm `tests/doctrine/test_drg_merge.py` still imports `load_replaceable_builtins` (and friends) from `doctrine.drg.override_policy` unchanged — these six sites already point at production, so they need no edit; verify they remain green after the promotion. (Owned here so the WP can adjust an import if a name collision surfaces; do NOT otherwise modify its assertions.)
  3. Run both files red-first-then-green: confirm they FAIL with an `ImportError`/`NameError` against the pre-T019 production module (the symbols are not yet there), then GREEN after T019.
- **Files**: `tests/architectural/test_builtin_override_policy.py`, `tests/doctrine/test_drg_merge.py`.
- **Notes**: Re-pointing imports, not deleting tests — this is the "delete-the-assertion-not-the-test" inverse: keep the assertions, change the source of the symbols.

### Subtask T021 — Focused unit tests for the promoted predicates

- **Purpose**: Pin the predicates directly at their new production home (new-code coverage; Sonar new-code gate).
- **Steps**: Create `tests/doctrine/drg/test_override_policy_predicates.py` importing from `doctrine.drg.override_policy`. Cover, with real-format inputs:
  - `find_overridden_builtin_urns`: a merged `DRGGraph` containing an `org:`-provenance node at a built-in URN is detected; a `project`-provenance node at a built-in URN is NOT (FR-012 scope boundary); a node at a non-built-in URN is ignored.
  - `find_unsanctioned_overrides`: unlisted URN → flagged (fail-closed); allowlisted non-directive → cleared; directive override with empty/whitespace reason → flagged; directive override with a real reason → cleared.
  - Malformed-allowlist fail-closed: an empty `ReplaceableBuiltinsPolicy(entries=())` sanctions nothing.
- **Files**: `tests/doctrine/drg/test_override_policy_predicates.py`.
- **Notes**: Build inputs from real `DRGGraph`/`DRGNode`/`OrgDRGFragment` constructors (mirror the fixtures in `test_builtin_override_policy.py`), not placeholder strings (C-007).

## Test Strategy

- Run: `PWHEADLESS=1 pytest tests/architectural/test_builtin_override_policy.py tests/doctrine/test_drg_merge.py tests/doctrine/drg/test_override_policy_predicates.py -q`.
- Prove T020/T021 RED against the pre-T019 production module (symbols absent → import error), then GREEN after the promotion.
- `ruff check src/doctrine/drg/override_policy.py tests/` and `mypy src/doctrine/drg/override_policy.py` clean.

## Risks & Mitigations

- Breaking the existing governance test → T020 re-points imports and keeps assertions, never deletes (NFR-004).
- Import cycle from pulling `DRGGraph`/`NodeKind` into `override_policy.py` → both are siblings in `doctrine.drg`; keep imports module-level and confirm no cycle via a clean `python -c "import doctrine.drg.override_policy"`.
- Accidentally retiring the allowlist entries here → OUT of scope; WP09 does that once WP08 wires a live caller. Leave `_CATEGORY_C_*` / `_CATEGORY_7_*` untouched.

## Review Guidance

- Verify the three symbols are a behavior-preserving MOVE (diff the promoted bodies against the test-module originals).
- Verify `__all__` exports the new names and retains the existing five.
- Verify red-first ordering on T020/T021 and that NO test was deleted or softened.
- Verify purity: no filesystem/merge calls inside the promoted predicates; inputs are already-loaded objects.

## Activity Log

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T09:51:12Z – claude:opus:python-pedro:implementer – shell_pid=918445 – Assigned agent via action command
- 2026-06-27T09:58:06Z – user – shell_pid=918445 – WP07: predicates promoted; existing governance test + 6 drg-merge sites re-pointed green (60 passed); fail-closed unit tests; ruff 0 / mypy 0
- 2026-06-27T09:58:08Z – user – shell_pid=918445 – WP07: predicates promoted; existing governance test + 6 drg-merge sites re-pointed green (60 passed); fail-closed unit tests; ruff 0 / mypy 0
- 2026-06-27T10:00:04Z – claude:opus:python-pedro:implementer – shell_pid=918445 – WP07: predicates promoted to override_policy.py (pure/fail-closed); governance test + 6 drg-merge sites re-pointed green (60 passed); fail-closed unit tests; ruff 0 / mypy 0
- 2026-06-27T10:00:57Z – claude:opus:reviewer-renata:reviewer – shell_pid=952174 – Started review via action command
- 2026-06-27T10:05:15Z – user – shell_pid=952174 – reviewer-renata APPROVE: byte-for-byte promotion; 60 passed
