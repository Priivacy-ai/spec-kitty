---
work_package_id: WP01
title: Org activations resolve-time wiring (shared seams + union + validation + durable invariant)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-001
- NFR-002
- NFR-003
- C-001
- C-002
- C-003
- C-004
tracker_refs:
- '2365'
planning_base_branch: design/org-charter-activations-2365
merge_target_branch: design/org-charter-activations-2365
branch_strategy: Planning artifacts for this mission were generated on design/org-charter-activations-2365. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/org-charter-activations-2365 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
- T009
phase: Phase 1 - Implementation
assignee: ''
agent: ''
history:
- at: '2026-07-04T15:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_org_activations_reach_context.py
- tests/charter/test_org_activations_resolution.py
- tests/charter/test_iter_org_charter_docs.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/context.py
- src/charter/activations.py
- src/specify_cli/doctrine/org_charter.py
- tests/charter/test_context_org_governance.py
- tests/charter/test_org_activations_reach_context.py
- tests/charter/test_org_activations_resolution.py
- tests/charter/test_iter_org_charter_docs.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Org activations resolve-time wiring

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the implementer profile before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Close issue **#2365**: org-pack `activations:` are parsed/folded (`OrgCharterPolicy.activations`) but discarded — no runtime consumer reads them, so an org pack cannot ship action-scoped doctrine to consumers. Wire them into the runtime charter-context **text bootstrap stanza** via a **resolve-time org∪project union**, mirroring the `required_<kind>` → `selected_<kind>` precedent.

Done when (from spec rev 2):
- **SC-001** — org-declared activation (matching `{mission_type, action}`) surfaces in `build_charter_context(...).text` `"Selected activations:"` stanza in **bootstrap mode**, in a consumer with NO project-local `activations:` block. Red on pre-fix HEAD.
- **SC-002** — org∪project union deduped by the 4-tuple identity key; distinct entries both present; project first-seen order preserved.
- **SC-003** — malformed entry in a **present** org pack raises a clear, pack-named error (propagated past the defensive `except`); **missing** pack is skipped.
- **SC-004** — a refactor-stable, bootstrap-mode-forced regression invariant guards the merged-but-never-rendered class; `governance.yaml` verified org-pure; non-org repos byte-identical.

## Context & Constraints

- **Precedent to mirror** (union/order ONLY): `_read_org_required_selections` (`src/charter/context.py:732`) + `_load_doctrine_selection` (`:768`). Enumerator: `_enumerate_org_pack_paths` (`:682`).
- **Attach point** (load-bearing): the org read+validate+union must sit **before** `_render_activation_block`'s `except Exception: return ""` — beside `_load_governance_activations` — so the FR-004 raise escapes to `build_charter_context`. Inside the `try` it is swallowed and FR-004 is defeated.
- **Layer boundary (C-001, ADR 2026-03-27-1)**: `src/charter/` MUST NOT import `specify_cli.doctrine.org_charter` (verified: context.py has zero `specify_cli` imports). The shared identity key moves **down** into `src/charter/activations.py`; `org_charter.py:44` already imports `ActivationEntry` from there and its `_activation_identity_key` caller is a single site at `:450`.
- **Scope fence (C-004)**: TEXT stanza only. Do NOT touch `build_charter_context_json`'s `directives`/`tactics` arrays (DRG-fed, activation-blind) or compact-mode rendering — both are deferred (spec Deferred Items) and affect project + org equally.
- **Error-handling divergence (C-002)**: mirror union/order semantics of `_read_org_required_selections`, but NOT its blanket `except (...): continue` silent skip — malformed present-pack entries RAISE (FR-004).
- Charter: `.kittify/charter/charter.md`; plan: `../plan.md`; research: `../research.md`; spec: `../spec.md`.

## Subtasks (red-first — NFR-001)

- **T001** [red-first] `tests/charter/test_org_activations_reach_context.py` — the FR-005 durable invariant. Org pack (harness `tests/charter/test_context_org_governance.py::_write_org_pack`/`_write_config`) with an `activations:` entry, no project-local block → assert it appears in `build_charter_context(...).text` `"Selected activations:"` stanza in **bootstrap mode** (omit `context-state.json` / depth ≥ 2). Assert stanza contents, not internal symbols (refactor-stable). Capture RED vs pre-fix HEAD.
- **T002** [red-first] `tests/charter/test_org_activations_resolution.py` — union/dedup (SC-002), malformed-present-pack raise (SC-003), missing-pack skip. Capture RED.
- **T003** [FR-003] Relocate `_activation_identity_key` from `org_charter.py:286` → `src/charter/activations.py`; re-import at `org_charter.py:450`. Behavior-preserving; confirm no `org_charter`-local dependency.
- **T004** [FR-006] Extract `_iter_org_charter_docs(repo_root)` in `context.py`; refactor `_read_org_required_selections` onto it (behavior-preserving — existing `required_<kind>` tests gate it). Add `tests/charter/test_iter_org_charter_docs.py`.
- **T005** [FR-001/002/004] `_read_org_activations(repo_root)` consuming T004's reader: `ActivationEntry.model_validate` each entry (raise on malformed present-pack; skip missing pack).
- **T006** [FR-001/002] Union org activations into `_load_governance_activations`'s list, dedup on the shared key (T003), project first-seen order preserved, placed pre-`except` at `_render_activation_block`.
- **T007** [NFR-002/003] Assert `governance.yaml` org-pure + non-org byte-identity; extend `tests/charter/test_context_org_governance.py`.
- **T008** Turn T001/T002 GREEN; run `tests/charter/` + `tests/specify_cli/doctrine/test_org_charter*.py`; confirm T004 left `required_<kind>` paths green.
- **T009** `ruff check` + `mypy` zero-issue on new + boy-scout-touched; complexity ≤ 15; no ≥3× literals (S1192); zero suppressions.

## Branch Strategy

- **Strategy**: single_branch (flat). Planning base + merge target: `design/org-charter-activations-2365`.

## Definition of Done

- All 9 subtasks complete; SC-001..SC-004 satisfied; NFR-001 red-first proven through `build_charter_context(...).text` (NOT `render_activation_stanza`/`resolve_for_context`).
- Layer boundary intact (no `charter → specify_cli` import); `governance.yaml` org-pure; non-org repos byte-identical.
- ruff + mypy clean; no suppressions; complexity ≤ 15.
- #2365 issue-close comment drafted correcting the reporter's `--json`-arrays expectation → point at the delivered text-stanza surface + the deferred JSON follow-up.
