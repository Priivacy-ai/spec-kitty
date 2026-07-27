# Specification: Profile Roles as Value Object

**Mission ID**: 01KPRJRY9WC8Q7PVRJ6AKTY109
**Status**: Draft
**Mission type**: software-dev
**Target branch**: doctrine/profile_reinforcement
**Created**: 2026-04-21

---

## Overview

Agent profiles in the doctrine framework currently carry a single `role` field
that declares what kind of agent the profile represents (e.g. `implementer`,
`reviewer`). In practice a single profile can fulfill several roles depending on
context — an architect can act as researcher, designer, and reviewer depending
on the task at hand. The current model cannot express this, forcing profiles to
either pick one identity or silently drop the others.

This feature replaces the single scalar `role` with a list of roles
(`roles: [...]`). The first entry in the list is the **primary role** used for
routing and display. Additional entries express secondary role capabilities.

The `Role` type itself is redesigned as a **half-open value object**: a set of
well-known, statically-declared constants (`implementer`, `reviewer`, …) that
any code can reference by name, combined with the ability to accept arbitrary
string values at runtime — so teams can introduce project-specific roles without
changing library code.

Existing profiles that use the old `role: <scalar>` YAML key continue to load
correctly (the value is promoted to a single-element list), but produce a
deprecation warning that tells the author exactly which field to update.

---

## Actors

| Actor | Description |
|-------|-------------|
| Profile author | A developer who writes or maintains an agent profile YAML (shipped or project-local) |
| Doctrine runtime | The Python code that loads, validates, and resolves agent profiles at runtime |
| Agent consumer | A routing algorithm or orchestrator that selects profiles based on role |

---

## User Scenarios & Testing

### Scenario A — Multi-role profile loaded and routed

A shipped profile declares `roles: [implementer, reviewer]`.
The routing algorithm selects the profile as a candidate for both `implementer`
tasks (primary) and `reviewer` tasks (secondary).
When sorting candidates for an `implementer` slot, this profile ranks using its
primary role signal.

### Scenario B — Custom role accepted without code change

A project-local profile declares `roles: [senior-tech-lead]`.
The doctrine runtime loads the profile successfully.
No exception is raised, no code change is required to support the new role.
A well-known-role check returns `false` for `"senior-tech-lead"` without
treating it as an error.

### Scenario C — Legacy scalar profile triggers deprecation warning

A profile YAML contains `role: implementer` (the old scalar key).
The runtime loads the profile and emits a `DeprecationWarning` whose message:
- names the profile by `profile-id`
- states that `role:` is deprecated
- gives the exact replacement: `roles: [implementer]`

The profile loads successfully with `roles` equal to `[Role.IMPLEMENTER]`.
No data is lost.

### Scenario D — All shipped profiles use the new list syntax

After migration, every file in `src/doctrine/agent_profiles/shipped/` uses
`roles: [...]`. Loading the shipped profile set produces zero deprecation
warnings.

### Scenario E — Routing uses primary role for priority

Two profiles declare the same language context but different primary roles.
A task requesting an `implementer` slot scores the profile whose primary role is
`implementer` higher than the profile whose primary role is `reviewer` (even if
the latter lists `implementer` as a secondary role).

### Scenario F — Avatar image field is present but optional

A shipped profile YAML includes `avatar-image: agent_profiles/avatars/jenny.png`.
The profile loads successfully and `profile.avatar_image` returns the path string.

A profile YAML that omits `avatar-image` loads successfully and
`profile.avatar_image` is `None`. No warning is emitted and no default
image is substituted.

### Scenario G — Shipped profiles carry character names

All profiles shipped with the doctrine package have `profile-id` values that
include a human character name (e.g. `reviewer-renata`, `architect-alphonso`).
A consumer browsing the profile list can identify profiles by the character name
without ambiguity. Generic base profiles (`implementer`, `human-in-charge`) are
exceptions reserved for structural/sentinel use only.



---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | An agent profile MUST declare one or more roles via a `roles` list field. The first entry in the list is the **primary role**. | Proposed |
| FR-002 | A `Role` value MUST be a half-open value object: the library ships a fixed set of well-known constants, AND any non-empty string is accepted as a valid `Role` at runtime without code changes. | Proposed |
| FR-003 | When a profile YAML contains the legacy `role: <scalar>` key, the runtime MUST promote the scalar to a single-element `roles` list and emit a `DeprecationWarning`. | Proposed |
| FR-004 | The deprecation warning from FR-003 MUST include: the profile's `profile-id`, the literal string `"role:"`, and the recommended replacement (`roles: [<value>]`). | Proposed |
| FR-005 | The profile MUST load successfully after scalar-to-list coercion (FR-003); no exception is raised and no data is lost. | Proposed |
| FR-006 | All profiles shipped with the doctrine package MUST be migrated to use `roles: [...]` and MUST produce zero deprecation warnings on load. | Proposed |
| FR-007 | Routing and matching logic MUST use the primary role (index 0 of `roles`) as the priority signal when ranking candidates for a role-constrained slot. | Proposed |
| FR-008 | Membership queries (e.g. "does this profile support role X?") MUST check all entries in `roles`, not only the primary role. | Proposed |
| FR-009 | The `Role` value object MUST expose all well-known role constants as named attributes (e.g. `Role.IMPLEMENTER`, `Role.REVIEWER`) so callers can reference them without bare strings. | Proposed |
| FR-010 | `TaskContext.required_role` MUST remain compatible: a caller may pass a well-known `Role` constant, a custom string, or `None`; matching is checked against all entries in `AgentProfile.roles`. | Proposed |
| FR-011 | The `DRG` node label for each agent-profile node MUST reflect the primary role of the profile as its role annotation. | Proposed |
| FR-012 | Every shipped agent profile MUST have a `profile-id` and `name` that include a human character name (e.g. `reviewer-renata`, `architect-alphonso`), following the same pattern already established by `java-jenny` and `python-pedro`. Generic role-only IDs (e.g. `implementer`, `reviewer`) are permitted only for base/sentinel profiles that are not intended to be assigned to a real agent. | Proposed |
| FR-013 | The existing generic base profiles (`implementer`, `reviewer`, `architect`, `designer`, `planner`, `researcher`, `curator`) MUST be evaluated: where a character-named profile does not yet exist as the primary shipping profile for that role, one MUST be created or the existing profile renamed. The decision (create vs. rename) is documented in the plan. | Proposed |
| FR-014 | `AgentProfile` MUST expose an optional `avatar_image` field that stores a path (string) pointing to an image asset bundled with the doctrine package (e.g. under `src/doctrine/agent_profiles/` or another bundled asset directory). When absent or `null`, profile behaviour is unchanged. The field is a forward-compatibility hook for issue #647 (WP card avatar display); no rendering or resolution logic is required by this feature. | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Profile load time for a directory of 20 shipped profiles MUST not regress measurably vs. the scalar-role baseline. | ≤ 5 % increase in load time (measured in the existing test suite) | Proposed |
| NFR-002 | The deprecation warning MUST be emitted via Python's standard `warnings.warn` with category `DeprecationWarning`, so callers can suppress or capture it with `warnings.filterwarnings`. | Standard `warnings` module, `DeprecationWarning` category | Proposed |
| NFR-003 | All existing passing tests in `tests/doctrine/` and `tests/charter/` MUST continue to pass after the change. | Zero regressions | Proposed |
| NFR-004 | Custom `Role` string values (not in the well-known set) MUST survive a round-trip through Pydantic serialisation (`model_dump`) and deserialisation without mutation or loss. | Value unchanged after round-trip | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Implementation targets the `doctrine/profile_reinforcement` branch; no changes to `main` until that branch merges. | Active |
| C-002 | Python 3.11+ and Pydantic v2 (existing codebase constraints). | Active |
| C-003 | The `Role` well-known constants MUST remain backward-compatible aliases: any code referencing `Role.IMPLEMENTER` today MUST continue to work unchanged after this feature. | Active |
| C-004 | YAML schema for agent profiles MUST accept both `role:` (deprecated scalar) and `roles:` (canonical list); validation MUST reject profiles that supply neither. | Active |
| C-005 | Profile renames (FR-012/FR-013) must follow the git `mv` + `profile-id` field update pattern already established by the `java-jenny` / `python-pedro` renames; the `mission_id` identity field in `meta.json` is never affected. | Active |

---

## Success Criteria

1. Every shipped profile in `src/doctrine/agent_profiles/shipped/` loads with zero deprecation warnings and a non-empty `roles` list.
2. Loading a hand-crafted profile YAML with `role: implementer` produces exactly one `DeprecationWarning` naming the profile and the replacement syntax, and the profile's `roles` field equals `[Role.IMPLEMENTER]`.
3. A profile declaring `roles: [architect, researcher]` is returned by a membership query for both `architect` and `researcher`; routing ranks it under its primary role `architect` for a slot that requests an architect.
4. A profile with `roles: [my-custom-org-role]` loads without error; `Role("my-custom-org-role")` compares equal to the value stored in `roles[0]`; serialisation round-trip preserves the string.
5. Full test suite (`pytest tests/doctrine/ tests/charter/ tests/specify_cli/`) passes with zero regressions.
6. Every shipped profile (excluding generic base profiles `implementer` and sentinel `human-in-charge`) has a `profile-id` containing a character name. The shipped profile set contains no role-only IDs that are used as the primary profile for their role.
7. A profile YAML with `avatar-image: <path>` loads with `profile.avatar_image == "<path>"`. A profile YAML without the field loads with `profile.avatar_image is None`. No exception or warning is raised in either case.

---

## Key Entities

| Entity | Description |
|--------|-------------|
| `Role` | Half-open value object. Static well-known constants (the "closed" part). Accepts any string as a valid runtime value (the "open" part). |
| `AgentProfile.roles` | Ordered list of `Role` values. First entry = primary role. Replaces the scalar `role` field. |
| `AgentProfile.role` | **Deprecated** scalar field. Accepted on load; coerced to a single-element `roles` list with a `DeprecationWarning`. |
| `TaskContext.required_role` | Input constraint for profile matching. Matched against all entries in `AgentProfile.roles`. |
| Shipped profile YAML | Any `.agent.yaml` file under `src/doctrine/agent_profiles/shipped/`. All must use `roles:` after migration. |
| `AgentProfile.avatar_image` | Optional string field. Holds a path to a bundled image asset. `None` when not declared. No rendering logic required by this feature. |

---

## Assumptions

- The existing `StrEnum`-based `Role` is replaced entirely; no code path retains the `StrEnum` after this feature lands.
- The DRG node label update (FR-011) is limited to the `label` annotation field; URNs (`agent_profile:<id>`) do not change.
- `AgentProfile.role` (singular) is kept as a computed property returning `roles[0]` for any code that still reads the single-role field, ensuring smooth transition for callers not yet updated.

---

## Out of Scope

- Adding new well-known `Role` constants beyond the existing set (that is a separate doctrine change).
- Changes to how `profile_id` or `name` are resolved.
- Any changes to the `sentinel` flag or sentinel profile behaviour.
- UI or dashboard rendering of multi-role badges.
- Resolving or validating `avatar_image` paths at load time (existence checks, URL resolution, or rendering are deferred to issue #647).
- Providing default avatar images for profiles that omit the field.
