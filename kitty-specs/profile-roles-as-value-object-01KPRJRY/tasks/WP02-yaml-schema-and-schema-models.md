---
work_package_id: WP02
title: YAML Schema + Schema Models
dependencies:
- WP01
agent_profile: "reviewer-renata"
role: "reviewer"
agent: "claude"
model: "claude-sonnet-4-6"
requirement_refs:
- C-004
- FR-001
- FR-003
- FR-006
planning_base_branch: doctrine/profile_reinforcement
merge_target_branch: doctrine/profile_reinforcement
branch_strategy: Planning artifacts for this feature were generated on doctrine/profile_reinforcement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/profile_reinforcement unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
shell_pid: "352691"
history:
- at: '2026-04-21T18:24:37Z'
  event: created
authoritative_surface: src/doctrine/schemas/
execution_mode: code_change
mission_slug: profile-roles-as-value-object-01KPRJRY
owned_files:
- src/doctrine/schemas/agent-profile.schema.yaml
- src/doctrine/agent_profiles/schema_models.py
- src/doctrine/agent_profiles/validation.py
- tests/doctrine/test_schema_validation.py
tags: []
---

# WP02 — YAML Schema + Schema Models

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Update `agent-profile.schema.yaml` to accept `roles` (array of strings) and the
optional `avatar-image` field, keep `role` (scalar, deprecated) valid, and reject
profiles that supply neither. Mirror the schema changes in `schema_models.py`. Write
schema validation tests.

This WP depends on WP01 (the new `Role` type must exist before these tests can import it).

## Implementation Command

```bash
spec-kitty agent action implement WP02 --agent python-pedro
```

## Branch Strategy

- **Plan base**: `doctrine/profile_reinforcement`
- **Depends on**: WP01 lane — do not start until WP01 is merged
- **Merge target**: `doctrine/profile_reinforcement`

---

## Context

### Current schema (`agent-profile.schema.yaml` — relevant excerpt)

```yaml
properties:
  profile-id: {type: string}
  name:        {type: string}
  role:        {type: string}
  version:     {type: string}
required: [profile-id, name, role, version]
```

After this WP:
- `role` (scalar) remains valid but is no longer in `required`
- `roles` (array) is added
- A constraint ensures at least one of `role` / `roles` is present
- `avatar-image` optional string is added

### `schema_models.py` current state

```python
class AgentProfileSchemaModel(BaseModel):
    profile_id: str = Field(alias="profile-id")
    name: str
    role: str | None = None
    version: str | None = None
```

After this WP: add `roles: list[str] | None = None` and
`avatar_image: str | None = Field(default=None, alias="avatar-image")`.

---

## Subtask Guidance

### T011 — Add `roles` array property to JSON schema

**File**: `src/doctrine/schemas/agent-profile.schema.yaml`

In the `properties` section, add:

```yaml
roles:
  type: array
  items:
    type: string
  minItems: 1
```

Remove `role` from the `required` list (it is no longer mandatory — the constraint
in T013 will enforce "at least one of role / roles").

---

### T012 — Add `avatar-image` optional string to JSON schema

**File**: `src/doctrine/schemas/agent-profile.schema.yaml`

In the `properties` section, add:

```yaml
avatar-image:
  type: string
```

No entry in `required` — it is optional.

---

### T013 — Add neither-key rejection constraint

**File**: `src/doctrine/schemas/agent-profile.schema.yaml`

Add an `oneOf` / `anyOf` constraint at the schema root that requires at least one of
`role` or `roles` to be present. The cleanest JSON Schema approach for "at least one of
two optional properties must be present" uses `anyOf` with two `required` sub-schemas:

```yaml
anyOf:
  - required: [role]
  - required: [roles]
```

Place this at the top level of the schema object (same level as `properties`,
`required`, `type`). JSON Schema validators (jsonschema, pydantic's jsonschema mode)
evaluate `anyOf` against the full document.

**Verify**: a document with neither `role` nor `roles` fails validation; a document
with only `role` passes; a document with only `roles` passes; a document with both passes.

Also add a bump to the schema `$comment` or `description` (if present) to note the
version so that the `@lru_cache` on `_load_agent_profile_schema` (if any) is invalidated
across test runs. If no `$comment` exists, add one:

```yaml
$comment: "schema-version: 2 — roles list support added"
```

---

### T014 — Update `schema_models.py`

**File**: `src/doctrine/agent_profiles/schema_models.py`

Add to `AgentProfileSchemaModel`:

```python
roles: list[str] | None = None
avatar_image: str | None = Field(default=None, alias="avatar-image")
```

Ensure `model_config` includes `populate_by_name=True` if not already set.

The `role` field remains for backward compat (legacy profiles still carry it as a
scalar string before Pydantic coercion).

---

### T015 — Write schema validation tests

Create or extend `tests/doctrine/test_schema_validation.py`.

Test cases to include:

```python
"""Schema validation tests for agent-profile.schema.yaml."""
import pytest
from doctrine.agent_profiles.validation import validate_agent_profile_yaml  # or equivalent


MINIMAL_BASE = {
    "profile-id": "test-p",
    "name": "Test Profile",
    "version": "1.0",
}


class TestRolesArraySchema:
    def test_roles_array_accepted(self):
        validate_agent_profile_yaml({**MINIMAL_BASE, "roles": ["implementer"]})

    def test_roles_array_multi_accepted(self):
        validate_agent_profile_yaml({**MINIMAL_BASE, "roles": ["implementer", "reviewer"]})

    def test_roles_empty_array_rejected(self):
        with pytest.raises(Exception):  # use specific exception type if known
            validate_agent_profile_yaml({**MINIMAL_BASE, "roles": []})

    def test_legacy_scalar_role_accepted(self):
        validate_agent_profile_yaml({**MINIMAL_BASE, "role": "implementer"})

    def test_neither_role_nor_roles_rejected(self):
        with pytest.raises(Exception):
            validate_agent_profile_yaml({**MINIMAL_BASE})

    def test_both_role_and_roles_accepted(self):
        validate_agent_profile_yaml({**MINIMAL_BASE, "role": "implementer", "roles": ["architect"]})


class TestAvatarImageSchema:
    def test_avatar_image_accepted(self):
        validate_agent_profile_yaml({**MINIMAL_BASE, "roles": ["implementer"],
                                     "avatar-image": "agent_profiles/avatars/test.png"})

    def test_avatar_image_absent_accepted(self):
        validate_agent_profile_yaml({**MINIMAL_BASE, "roles": ["implementer"]})
```

Adjust the import and the exception type to match what `validation.py` actually raises
(likely `jsonschema.ValidationError`).

---

## Definition of Done

- [ ] `agent-profile.schema.yaml` accepts `roles: [string, ...]` with `minItems: 1`
- [ ] `agent-profile.schema.yaml` still accepts legacy `role: string`
- [ ] `agent-profile.schema.yaml` rejects profiles with neither `role` nor `roles`
- [ ] `agent-profile.schema.yaml` rejects `roles: []`
- [ ] `agent-profile.schema.yaml` accepts optional `avatar-image: string`
- [ ] `schema_models.py` has `roles: list[str] | None` and `avatar_image: str | None`
- [ ] `pytest tests/doctrine/test_schema_validation.py -v` passes

## Risks

- **`lru_cache` on schema loader**: If `_load_agent_profile_schema` is cached, tests
  that run in the same process as an earlier test loading the old schema may see stale
  data. Use `cache_clear()` in a test fixture if needed:
  ```python
  @pytest.fixture(autouse=True)
  def clear_schema_cache():
      from doctrine.agent_profiles.validation import _load_agent_profile_schema
      _load_agent_profile_schema.cache_clear()
  ```
- **`anyOf` placement**: Some YAML schema validators require `anyOf` at the root of the
  `$schema` object. If the file uses a `$defs` / `definitions` structure, ensure the
  constraint is on the top-level schema or the main profile schema sub-object.

## Activity Log

- 2026-04-21T20:44:44Z – claude – shell_pid=352691 – Started implementation via action command
- 2026-04-21T20:50:16Z – claude – shell_pid=352691 – Moved to for_review
- 2026-04-21T20:50:46Z – claude – shell_pid=352691 – Moved to in_review
- 2026-04-21T20:50:52Z – claude – shell_pid=352691 – Moved to approved
