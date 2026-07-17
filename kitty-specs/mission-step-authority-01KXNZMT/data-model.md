# Data / Schema Model — Step authority (S-B)

## `MissionStep` (the authority) — schema changes

Current (`src/doctrine/missions/models.py:87`, `frozen`, `extra="forbid"`):
`id, display_name, step_type, prompt_template, agent_profile, guidance, delegates_to, depends_on`.

S-B adds (all must be registered in `_STEP_YAML_TO_MODEL`, `mission_step_repository.py:120`):

| Field | Type | Meaning | Notes |
|-------|------|---------|-------|
| `sequence_index` | `int \| None` | Position within the mission type's ordered sequence | Relocated from `action_sequence`; `None` when not in sequence |
| `in_action_sequence` | `bool` | Membership in the ordered sequence | software-dev: true for 5 of 12; false for `retrospect` etc. (keeps `scope` edges, D5) |
| `recommended_model_tier` | `str \| None` | Net-new advisory model-tier **offer** | Read via the override seam; charter/runtime override wins (D4) |
| `template` | `(artifact_key, template_file) \| None` | Reference to the step's content template | software-dev `specify`/`plan` → existing `spec-template.md`/`plan-template.md`; 3 types null. **Reference, not content** (C-004) |

`recommended_role` is **not** a new field — the existing `agent_profile` is the advisory role offer (DD-05).

**`prompt_template` stays required** (`str`, structure enforced — NOT made optional): documentation (7) + research (5) steps have `guidelines.md` but no `prompt.md`, and `plan` (4) has neither — 16 steps total. For those, seed a **blank/empty `prompt.md`** so the required field points at a real file; a **red test on prompt emptiness/dummy-content** flags each seeded blank until S-C fills it (FR-013). A blank placeholder is not fabricated content.

## Projections (derived, no longer authored)

- **`action_sequence`** = `[step.id for step in steps if step.in_action_sequence]` sorted by `sequence_index`.
  Removed from `mission_types/*.yaml`. The value is **injected by `MissionTypeRepository._load`** (project builtin
  steps with `pack_context=None`, feed into `model_validate`) — **not** a computed property on the frozen model.
  `default()` is memoized (`@functools.cache`, idiom at `mission_type_repository.py:140`) so the hot path doesn't
  re-load step.yaml per call (NFR-007). `_validate_action_sequence` (non-empty + unique) runs on the injected
  projection at construction.
- **`template_set`** = `{step.template.artifact_key: step.template.template_file for step in steps if step.template}`.
  Removed from the YAML. software-dev → `{spec: spec-template.md, plan: plan-template.md}`; 3 types → `null`.

## Projection seam (new module, doctrine layer)

`src/doctrine/missions/step_projection.py`:
- `project_action_sequence(steps: Iterable[MissionStep]) -> list[str]`
- `project_template_set(steps: Iterable[MissionStep]) -> dict[str, str] | None`

Pure, deterministic. Consumed by **both** the DRG extractor and the charter/runtime (one implementation).

## Invariants

1. **Parity (software-dev)** — `project_action_sequence(sw-dev steps)` == pre-mission `[specify, plan, tasks, implement, review]`; `project_template_set` == `{spec, plan}`. Byte-for-byte (NFR-001a).
2. **Referential integrity (3 types)** — projected `action_sequence` round-trips to the pre-mission value; every `template`/`prompt_template` ref that exists resolves to a moved-byte-identical file; missing → red test (NFR-001b).
3. **DRG 0-delta** — 280/757/10 fresh (NFR-002); FR-011 deferred → no contract edges.
4. **No routing leak** — a charter/runtime override always beats the step `recommended_model_tier` offer (NFR-003).
5. **Dispatch invariance** — adding step.yaml to the 3 types does not change `spec-kitty next` (NFR-006).

## Structural layout (unification, FR-005)

Target for all 4 types: `src/doctrine/missions/mission-steps/<type>/<step>/{step.yaml, prompt.md, guidelines.md}`
(software-dev's existing layout). Move documentation/research content in; `plan`'s 4 steps have no prompt → red test.
