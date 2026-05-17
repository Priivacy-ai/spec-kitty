---
work_package_id: WP06
title: Org-Charter Pre-Fill Union + Collision Warnings + Missing-Pack Policy
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-008
- FR-014
- FR-015
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T002
- T026
- T027
- T028
- T029
- T030
- T031
agent: "claude:opus-4-7:reviewer-renata:reviewer"
agent_profile: python-pedro
authoritative_surface: src/specify_cli/doctrine/org_charter.py
execution_mode: code_change
owned_files:
- src/specify_cli/doctrine/org_charter.py
- src/specify_cli/doctrine/config.py
- src/doctrine/base.py
- tests/specify_cli/doctrine/test_org_charter_schema.py
- tests/specify_cli/doctrine/test_org_charter_union.py
- tests/specify_cli/doctrine/test_collision_warnings.py
- tests/specify_cli/doctrine/test_missing_pack_policy.py
role: implementer
history: []
tags: []
shell_pid: "1759901"
---

## Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Three independent-but-related extensions to org-charter behaviour:

1. **FR-003**: `apply_org_charter_to_interview` unions every `required_<kind>` into the project's matching `selected_<kind>`.
2. **FR-014**: `DoctrineLayerCollisionWarning` fires for collisions in all 8 artifact kinds (today: directives, tactics, agent_profiles only).
3. **FR-015**: Pack-registry loader hard-fails when a configured pack's `local_path` does not exist on disk — replaces today's silent-skip policy.

After this WP, Case 2 (org-pack styleguide) works end-to-end and the policy change is enforced loudly.

---

## Context

Today's `apply_org_charter_to_interview` (in `src/specify_cli/doctrine/org_charter.py:228`) handles only `required_directives`. The other 7 `required_<kind>` fields land in WP01; this WP wires their union.

`DoctrineLayerCollisionWarning` is emitted from `src/doctrine/base.py:BaseDoctrineRepository`. Today's emission is per-kind based on which kinds have org-layer support enabled (Mission A wired directives + tactics + agent_profiles). This WP completes the matrix for styleguides + toolguides + paradigms + procedures + mission_step_contracts.

`load_pack_registry` in `src/specify_cli/doctrine/config.py` silently filters missing `local_path` entries today. This WP changes that to hard-fail with a clear error.

See:
- [plan.md §2.2, §2.11](../plan.md)
- [contracts/selection-schema.md](../contracts/selection-schema.md)

---

## Branch Strategy

- **Planning/base**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP06 --agent claude`

---

## Subtasks

### T026 — Extend `apply_org_charter_to_interview` union

**File**: `src/specify_cli/doctrine/org_charter.py`

Today's function unions only `required_directives`. Extend to all 8 `required_<kind>` fields:

```python
for kind in (
    "directives", "tactics", "paradigms", "styleguides",
    "toolguides", "procedures", "agent_profiles", "mission_step_contracts",
):
    required_list = getattr(merged_policy, f"required_{kind}", [])
    selected_list = getattr(interview_data, f"selected_{kind}", None)
    if selected_list is None:
        # Interview data may not yet declare this attribute — initialize empty.
        setattr(interview_data, f"selected_{kind}", [])
        selected_list = getattr(interview_data, f"selected_{kind}")
    new_required = [d for d in required_list if d not in selected_list]
    if new_required:
        selected_list.extend(new_required)
        messages.append(
            f"Pre-selected {len(new_required)} {kind} from org charter required_{kind}."
        )
```

Verify the `CharterInterview` dataclass in `src/charter/interview.py` carries `selected_<kind>` attributes for every kind so the union has a target. If absent, add the defaults (additive — NFR-005 safe).

### T027 — Extend `load_org_charter_policies` merge

**File**: `src/specify_cli/doctrine/org_charter.py`

Replace the single `required_directives` merge loop with a per-kind loop covering all 8 kinds. Same union-preserving-first-seen-order semantic.

### T028 — Activations merge across packs

**File**: `src/specify_cli/doctrine/org_charter.py`

Add to `load_org_charter_policies`:

```python
merged_activations: list[ActivationEntry] = []
seen_activation_keys: dict[tuple, ActivationEntry] = {}
for pack in registry.packs:
    policy = load_org_charter_policy(pack.local_path)
    if policy is None:
        continue
    for entry in policy.activations:
        key = (
            json.dumps(entry.activation_context, sort_keys=True),
            entry.doctrine_pack_id,
            entry.artifact_id,
            entry.artifact_kind or "",
        )
        seen_activation_keys[key] = entry  # last wins
deduped_activations = list(seen_activation_keys.values())
```

Pass `activations=deduped_activations` to the final `OrgCharterPolicy(...)` constructor.

### T029 — Extend `DoctrineLayerCollisionWarning` to all kinds

**File**: `src/doctrine/base.py`

Audit `BaseDoctrineRepository` for where the collision warning fires. Verify it fires for every kind (the base class is shared; the issue is per-kind subclasses that may have opted out). Extend the warning message format to always include the artifact kind, satisfying:

```
str(warning.message) contains both <id> and <kind>
```

(Pinned by `test_case_2_org_styleguide_collision_with_builtin_warns`.)

### T030 — Implement strict missing-pack policy

**File**: `src/specify_cli/doctrine/config.py`

In `load_pack_registry` (or its consumer), replace silent-skip with hard-fail:

```python
class PackNotFoundError(RuntimeError):
    """Raised when a configured doctrine pack's local_path does not exist."""


def _validate_pack_local_paths(packs: list[Pack]) -> None:
    for pack in packs:
        if not pack.local_path.exists():
            raise PackNotFoundError(
                f"Doctrine pack `{pack.name}` configured at "
                f"`{pack.local_path}` does not exist on disk. Run "
                f"`spec-kitty doctrine fetch --pack {pack.name}` to populate it, "
                f"or remove the pack from .kittify/config.yaml."
            )
```

Wire the validation into `build_charter_context` so the error surfaces at context-resolution time (the ATDD test path).

Update `docs/explanation/org-doctrine-layer.md` (or equivalent) to call out the policy change (C-006).

### T031 — Unit tests

**Files**:
- `tests/specify_cli/doctrine/test_org_charter_union.py` — parametrised tests covering each `required_<kind>` union into `selected_<kind>`. Non-destructive semantic verified.
- `tests/specify_cli/doctrine/test_collision_warnings.py` — fixture per kind: org pack ships an artifact whose ID collides with built-in; assert warning fires with both id and kind in the message.
- `tests/specify_cli/doctrine/test_missing_pack_policy.py` — fixture: `config.yaml` references a non-existent path; assert `PackNotFoundError` raised with named path.

---

## Definition of Done

- ✅ `tests/integration/test_org_pack_artifact_lifecycle.py::test_case_2_org_pack_styleguide_appears_in_consumer_prompt` turns GREEN
- ✅ `tests/integration/test_org_pack_artifact_lifecycle.py::test_case_2_required_styleguides_in_org_charter_pre_fills` turns GREEN
- ✅ `tests/integration/test_org_pack_artifact_lifecycle.py::test_case_2_org_styleguide_collision_with_builtin_warns` turns GREEN
- ✅ `tests/integration/test_org_pack_artifact_lifecycle.py::test_case_2_consumer_without_fetched_pack_fails_loudly` turns GREEN
- ✅ `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — 23/23 stays green
- ✅ New unit tests for each kind union + each kind collision + missing-pack policy

---

## Risks

| Risk | Mitigation |
|------|------------|
| Existing user `config.yaml` files reference packs that haven't been fetched → breaking change | C-006 mandates the user-doc update. The error message is actionable. Migration note: run `spec-kitty doctrine fetch` once before upgrading. |
| `CharterInterview` dataclass changes break interactive flow | Additive only — new attributes default to empty lists. Verified by existing interview tests. |
| Collision warnings now firing for kinds that previously were silent → noisy for users | The warning is informational (operator can dismiss); the change reflects FR-014 intent. |
| `PackNotFoundError` raised inside `build_charter_context` interrupts WP prompts mid-build | Validate packs upfront before any rendering work. Caller catches at CLI boundary and prints a clear diagnostic. |

---

## Reviewer Guidance

- Verify the per-kind loop in `apply_org_charter_to_interview` is data-driven (no 8-copy-pasted blocks).
- Verify `PackNotFoundError` message names BOTH the pack name AND the path.
- Verify the collision warning message format change doesn't break Mission A's existing assertions (run the Mission A test suite as a check).
- Verify the user-doc update lands in this WP (C-006).

## Activity Log

- 2026-05-17T17:41:57Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1736199 – Started implementation via action command
- 2026-05-17T18:03:00Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1736199 – OrgCharterPolicy extended (8 required_<kind> fields); 5 org-pack ATDD tests green; selection_completeness 3/3 green; missing-pack now hard-fails per FR-015
- 2026-05-17T18:03:40Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1759901 – Started review via action command
- 2026-05-17T18:08:26Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1759901 – Moved to planned
