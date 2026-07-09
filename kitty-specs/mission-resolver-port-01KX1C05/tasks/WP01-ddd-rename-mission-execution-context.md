---
work_package_id: WP01
title: DDD rename ExecutionContext → MissionExecutionContext
dependencies: []
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: feat/mission-resolver-port-2173
merge_target_branch: feat/mission-resolver-port-2173
branch_strategy: Planning artifacts for this mission were generated on feat/mission-resolver-port-2173. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-resolver-port-2173 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4171263"
history:
- at: '2026-07-08T18:06:06+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/context.py
create_intent: []
execution_mode: code_change
owned_files:
- src/mission_runtime/context.py
- src/mission_runtime/__init__.py
- docs/adr/3.x/2026-06-22-1-mission-topology-ssot.md
- docs/adr/3.x/2026-06-03-1-execution-state-domain-model.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile via `/ad-hoc-profile-load` for
`python-pedro` (implementer). Adopt its identity, governance scope, and boundaries. Then read
`kitty-specs/mission-resolver-port-01KX1C05/spec.md` (FR-012), `plan.md` (IC-00), and
`research.md` (D-10).

## Objective

Rename the frozen composite class `ExecutionContext` → `MissionExecutionContext` in
`src/mission_runtime/context.py` and everywhere it is used, so the code name matches the ubiquitous
language already used in its docstring, the `#1619` epic, and the parity test. This **also removes a
name collision** with the unrelated `class ExecutionContext(StrEnum)` in
`src/specify_cli/core/context_validation.py`. This is a **scoped bulk rename** and lands FIRST so every
downstream WP uses the corrected name.

## Hard exclusion (the whack-a-symbol trap)

**Do NOT rename `src/specify_cli/core/context_validation.py:41 class ExecutionContext(StrEnum)`** — it is a
different type. Rename ONLY the `mission_runtime.context` composite and references that resolve to it.
Verify by import origin, not by bare token match.

## Occurrence classification (scoped — apply the bulk-edit discipline)

| Category | Action |
|----------|--------|
| code_symbols | rename the composite class `ExecutionContext` → `MissionExecutionContext` |
| import_paths | update the ~12 `from mission_runtime.context import ExecutionContext` sites |
| tests_fixtures | update test references + the parity-test assertion string |
| user_facing_strings / docs | update the class docstring + the 2 ADR prose refs |
| filesystem_paths / serialized_keys / cli_commands / logs_telemetry | none |

## Subtasks

### T001 — Rename the class + docstring in `context.py`
- `src/mission_runtime/context.py:262` `class ExecutionContext:` → `class MissionExecutionContext:`.
- Update the module docstring (`:1`, `:11` already say `MissionExecutionContext` — leave those; they are now correct).
- Keep the frozen/`@dataclass(frozen=True)` semantics unchanged.

### T002 — Update the `ActionContext` alias
- `context.py:351` (line drifted from :349) `ActionContext = ExecutionContext` → `ActionContext = MissionExecutionContext` (keep the transitional alias pointing at the new name; do not delete it — its own retirement is a separate track).

### T003 — Update the public re-export + composite importers (documented out-of-map)
**MUST-FIX (squad):** `src/mission_runtime/__init__.py` re-exports the class (`:32` import, `:67` in
`__all__`) and the package docstring says consumers import ONLY from the root — so if you rename the class
in `context.py` and NOT here, `import mission_runtime` raises `ImportError` and the WHOLE suite fails at
collection. **`__init__.py` is in this WP's owned_files** — update its import and `__all__` entry
(`ExecutionContext` → `MissionExecutionContext`).
- Then update every composite-typed reference. The real composite-origin src consumers are exactly three
  files: `context.py` (def), `mission_runtime/__init__.py` (re-export), `mission_runtime/resolution.py`
  (consumer) — plus ~7 test files (`test_context_factory_invariant`, `test_context_fragments`,
  `test_resolve_context_for_mission_pure`, `test_execution_context_parity`, `test_mission_runtime_surface`,
  `test_surface_resolution_equivalence`, `test_mid8_direct_routing`).
- **Do NOT touch `runtime_bridge.py`** — its only `ExecutionContext` token is the unrelated
  `StepContractExecutionContext` (a phantom rename site; the original task list was wrong).
- **Method — import-origin, NOT bare grep.** The naive `grep -v StrEnum` / `grep -v context_validation`
  recipe does NOT exclude StrEnum *consumers* (e.g. `tests/agent/test_context_validation_unit.py` has 24
  refs, `tests/conftest.py` uses `ExecutionContext.MAIN_REPO`). Discriminate by import origin: a reference
  is a rename target ONLY if it resolves to `mission_runtime.context.ExecutionContext`, NOT to
  `core.context_validation.ExecutionContext(StrEnum)`. Record the one-line rationale ("WP01 rename FR-012")
  for the out-of-map file touches (resolution.py etc. are owned by later WPs but land after WP01, so no
  collision).

### T004 — Update ADR prose
- `docs/adr/3.x/2026-06-22-1-mission-topology-ssot.md` and `docs/adr/3.x/2026-06-03-1-execution-state-domain-model.md`
  reference `ExecutionContext` as a canonical seam — update to `MissionExecutionContext` where they mean
  the composite (leave any reference that means the StrEnum / a different `ExecutionContext`).

### T005 — Verify (the collision + the surface pin)
- **Flip the surface-test pin (MUST-FIX, sanctioned out-of-map):** `tests/architectural/test_mission_runtime_surface.py:53`
  `_PUBLIC_SURFACE` contains the literal `"ExecutionContext"`, and `:111` asserts
  `mission_runtime.__all__ == _PUBLIC_SURFACE`. Update that literal to `"MissionExecutionContext"` (the
  test file already carries a precedent comment endorsing this surface-pin edit). Without this, the surface
  test reds even after `__init__.py` is fixed.
- `grep -rn "class ExecutionContext" src` → exactly one hit remains: `core/context_validation.py` (StrEnum).
- Confirm no composite reference survives by **import-origin**, not a bare grep (StrEnum consumers like
  `test_context_validation_unit.py` are legitimate `ExecutionContext` refs and must remain).
- Run the FULL `tests/architectural/` suite + `test_execution_context_parity.py` +
  `test_mission_runtime_surface.py`; confirm green. Run `ruff` + `mypy` clean.

### Note — Contextive glossary term (decide, don't silently skip)
`.contextive/execution.yml:20` defines the domain term `"ExecutionContext"` and `workflow.py:1113`
mentions it in prose. If the ubiquitous term is now `MissionExecutionContext`, make a deliberate keep-or-
rename call on the Contextive term and record it (low severity; terminology-canon surface). Not a code
rename — a glossary decision.

## Branch Strategy

Planning happened on `feat/mission-resolver-port-2173`; that is also the merge target. The execution
worktree for this WP is allocated per computed lane from `lanes.json` at `/spec-kitty.implement`. Do not
push to `origin`.

## Definition of Done
- The composite class is `MissionExecutionContext` everywhere; the `ActionContext` alias points to it.
- The `ExecutionContext(StrEnum)` is untouched.
- Full `tests/architectural/` + parity + surface gates green; `ruff`/`mypy` clean.
- ADR prose updated.

## Risks / reviewer guidance
- **Collision**: reviewer greps `class ExecutionContext` (must be 1, the StrEnum) and spot-checks that no
  StrEnum reference was renamed.
- **Out-of-map touches**: expected and documented (FR-012 codebase rename); confirm they are pure symbol
  renames, no behavior change.
- Sonar campsite (operator standing instruction): census the touched files; fold SAFE trivia, note ADJACENT.

## Activity Log

- 2026-07-08T18:35:02Z – claude:sonnet:python-pedro:implementer – shell_pid=4120284 – Assigned agent via action command
- 2026-07-08T18:59:40Z – claude:sonnet:python-pedro:implementer – shell_pid=4120284 – Ready for review: renamed composite ExecutionContext->MissionExecutionContext (FR-012); StrEnum untouched (1 class ExecutionContext remains, the StrEnum); full tests/architectural/ green 827 passed/4 skipped; parity+surface gates green; diff-scoped ruff+mypy exit 0.
- 2026-07-08T19:00:49Z – claude:opus:reviewer-renata:reviewer – shell_pid=4171263 – Started review via action command
- 2026-07-08T19:07:25Z – user – shell_pid=4171263 – Review passed (reviewer-renata): composite ExecutionContext->MissionExecutionContext renamed (class+docstrings+ActionContext alias); grep 'class ExecutionContext' src=EXACTLY 1 (context_validation StrEnum untouched, all consumers intact); __init__ re-export+__all__ + surface _PUBLIC_SURFACE flipped, import mission_runtime + MissionExecutionContext OK; runtime_bridge/StepContractExecutionContext NOT touched; 2 boy-scout mypy typing fixes in-diff/minimal; parity+surface gates 29 passed, diff-scoped ruff clean. Contextive term + workflow.py prose deliberately kept (WP-sanctioned low-sev glossary). Issue-matrix #1619/#2173 set in-mission (epics span the 7-WP mission).
