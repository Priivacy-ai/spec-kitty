---
work_package_id: WP07
title: Activation authority, absence semantics, and fail-closed delivery
dependencies:
- WP06
requirement_refs:
- C-006
- FR-012
- FR-017
- FR-018
- NFR-001
- NFR-002
- NFR-005
- NFR-006
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
created_at: '2026-07-28T19:48:12Z'
subtasks:
- T035
- T036
- T037
- T038
- T039
- T040
- T041
phase: Phase 3 - Activation
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/activation/pack_context.py
create_intent:
- src/specify_cli/upgrade/migrations/m_3_2_x_normalize_activation_absence.py
- tests/specify_cli/upgrade/test_normalize_activation_absence.py
- tests/charter/test_activation_authority.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/activation/pack_context.py
- src/charter/activation/compiler.py
- src/specify_cli/upgrade/migrations/m_3_2_x_normalize_activation_absence.py
- tests/specify_cli/upgrade/test_normalize_activation_absence.py
- tests/charter/test_activation_authority.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP07 — Activation authority, absence semantics, and fail-closed delivery

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show python-pedro`**. **Do not read the raw `*.agent.yaml`**.

---

## Objective

One activation authority; an omitted `activated_<kind>` key means **empty**, not "all built-ins"; and
activation failures **propagate** instead of degrading into a silent legacy render.

## Context — traps that have already bitten

- **The pointer field is `charter:`**, already shipping and honoured by `_load_charter_activation_source`
  (`pack_context.py`). **`charter_file:` exists nowhere.** Introducing it mints a competing pointer —
  the exact defect FR-017 removes. (My own research doc originally named `charter_file:` in error;
  do not follow it.)
- **Ordering: T035 before T036.** `_charter_activated_urns` (`test_extractor_projection.py:394-432`)
  reads `config.yaml`'s `activated_*` mirror. Delete the mirror before repointing the gate and its
  floor assertion fails while its stray guard goes **vacuously true**.
- **Absence is a documented three-state contract** — `None` means "all built-ins available". Harmless
  today only because the compact rail carries nothing; once delivery works (WP10/WP11), a project
  omitting `activated_procedures` would receive all 18 at every boundary. FR-018 retires it.
- **Two prior migrations already fought over this surface** — `m_unify_charter_activation.py` made
  `config.activated_*` the authority; `m_unify_charter_activation_finalize.py` folded it into
  `charter.yaml` and minted the pointer — and the mirror **survived both** (this checkout still carries
  it). FR-017 is the third pass; understand why the second did not take before writing the third.

Read [`contracts/activation-delivery.md`](../contracts/activation-delivery.md) §1 (V-1 to V-5) and the
NFR-006 fail-closed obligation.

## Subtasks

### T035 — Repoint `_charter_activated_urns` at the resolved source
1. Point it at the resolved activation source (`charter.yaml` via the `charter:` pointer), not the
   `config.yaml` mirror. **This must land before T036.**

### T036 — Remove the retired mirror
1. Remove `activated_*` from the `config.yaml` surface.
2. Verify no reader still consults it — grep for `config` + `activated`.

### T037 — Migration: absence -> explicit `[]`
1. `src/specify_cli/upgrade/migrations/m_3_2_x_normalize_activation_absence.py`: for each consumer
   project, write explicit `[]` where an `activated_<kind>` key is absent, and ensure the `charter:`
   pointer is present.
2. Model on an existing migration (`m_unify_charter_activation_finalize.py`). Auto-discovered — add
   its registration test.

### T038 — Retire the three-state contract at every read site
1. Every `_read_activated_*` in `pack_context.py` currently treats absence as "all built-ins". After
   migration, absence is `[]`. Retire the fallback so the two agree.

### T039 — Divergent-mirror fixture (SC-007)
1. A fixture where `config.yaml` and `charter.yaml` **disagree** on the activated set. Assert the
   charter wins. This is the only case that proves which store is authoritative — a no-op migration
   fails it.

### T040 — Fail-closed error propagation (FR-012 error half, NFR-006)
1. Activation resolution errors raise a typed, named error that **propagates**.
2. `src/runtime/next/prompt_builder.py`'s `except Exception: pass` (the seam that degrades to legacy)
   is replaced. The pattern to copy sits immediately above it
   (`except (CharterScopeConflict, CharterScopeNotFound): raise`).
3. **This is the authority half of FR-012** — the grain half is WP11's. Owning the raise here keeps
   raise-and-surface in one concern.

### T041 — Reconcile the two prior migrations
1. Read both prior migrations; document why the mirror survived the finalize pass.
2. Declare the ordering constraint the finalize migration's docstring already carries.

## Branch Strategy

Planning base and merge target `feat/doctrine-delivery-reachability`. Depends on WP06. `spec-kitty
implement WP07` resolves the workspace.

**File-ownership note**: `test_extractor_projection.py` is shared with WP08 (which renames a set).
This WP repoints `_charter_activated_urns` in that file; coordinate so the two do not collide — serialize
if in the same lane.

## Test strategy

```bash
PWHEADLESS=1 pytest tests/charter/test_activation_authority.py tests/specify_cli/upgrade/test_normalize_activation_absence.py tests/doctrine/drg/migration/test_extractor_projection.py -q
```

## Definition of Done

- [ ] `_charter_activated_urns` reads the resolved source, repointed **before** the mirror is removed
- [ ] The `config.yaml` `activated_*` mirror is gone; no reader consults it
- [ ] The pointer is `charter:`; `charter_file:` appears nowhere
- [ ] Absent keys migrate to explicit `[]`; the three-state fallback is retired
- [ ] The divergent-mirror fixture proves the charter wins
- [ ] Activation errors propagate; the `prompt_builder` swallow is gone
- [ ] The two prior migrations are reconciled in a written note
- [ ] A red commit precedes each green commit (C-006)
- [ ] `ruff` + `mypy --strict` clean

## Risks

| Risk | Mitigation |
|---|---|
| Mirror deleted before gate repointed -> vacuous green | T035 strictly before T036 |
| `charter_file:` reintroduced | It does not exist; use `charter:` |
| No-op migration passes SC-007 | Divergent-mirror fixture |
| Consumer configs mutated (NFR-001) | Permitted for this surface only; PR-body callout |

## Reviewer guidance

1. Check `git log` order: T035's repoint commit before T036's removal.
2. `grep -rn "charter_file" src/` — must be empty.
3. Run the divergent-mirror fixture; confirm the charter wins.
4. Break activation resolution deliberately; confirm the error surfaces rather than a degraded render.
