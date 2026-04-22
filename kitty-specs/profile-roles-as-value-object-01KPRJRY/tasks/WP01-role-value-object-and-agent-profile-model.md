---
work_package_id: WP01
title: Role Value Object + AgentProfile Model
dependencies: []
requirement_refs:
- C-002
- C-003
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-009
- FR-010
- FR-014
- NFR-002
- NFR-004
planning_base_branch: doctrine/profile_reinforcement
merge_target_branch: doctrine/profile_reinforcement
branch_strategy: Planning artifacts for this feature were generated on doctrine/profile_reinforcement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/profile_reinforcement unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-profile-roles-as-value-object-01KPRJRY
base_commit: 29ee6cc8b992bffa0b494892802d2e53af3810fc
created_at: '2026-04-21T19:28:59.012485+00:00'
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
- T010
agent: claude
shell_pid: '336209'
history:
- at: '2026-04-21T18:24:37Z'
  event: created
agent_profile: reviewer-renata
authoritative_surface: src/doctrine/agent_profiles/
execution_mode: code_change
mission_slug: profile-roles-as-value-object-01KPRJRY
model: claude-sonnet-4-6
owned_files:
- src/doctrine/agent_profiles/profile.py
- src/doctrine/agent_profiles/capabilities.py
- tests/doctrine/test_role_value_object.py
role: reviewer
tags: []
---

# WP01 — Role Value Object + AgentProfile Model

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Replace the `Role(StrEnum)` class in `profile.py` with a half-open `str`-subclass value object,
update `AgentProfile` to expose `roles: list[Role]` (with a computed backward-compat `role`
property), add an optional `avatar_image` field, and write the unit tests that cover the new
model surface.

This WP owns **all of `profile.py`** and `capabilities.py`. No other WP touches these files.

## Implementation Command

```bash
spec-kitty agent action implement WP01 --agent python-pedro
```

## Branch Strategy

- **Plan base**: `doctrine/profile_reinforcement`
- **Execution worktree**: allocated by `finalize-tasks` lane resolution — check `lanes.json`
- **Merge target**: `doctrine/profile_reinforcement`

Do not branch from `main`.

---

## Context

### Current state of `profile.py` (relevant excerpt)

```python
class Role(StrEnum):
    IMPLEMENTER = "implementer"
    REVIEWER    = "reviewer"
    ARCHITECT   = "architect"
    DESIGNER    = "designer"
    PLANNER     = "planner"
    RESEARCHER  = "researcher"
    CURATOR     = "curator"
    MANAGER     = "manager"

def _coerce_role(value: Any) -> Role | str:
    try:
        return Role(value.lower())
    except ValueError:
        return str(value)

class AgentProfile(BaseModel):
    ...
    role: Annotated[Role | str, BeforeValidator(_coerce_role)] = Role.IMPLEMENTER
    ...
```

`capabilities.py` holds `DEFAULT_ROLE_CAPABILITIES: dict[Role, RoleCapabilities]` keyed on
the same enum constants. Because `Role("implementer") == Role.IMPLEMENTER` via `str.__eq__`,
the dict lookups continue to work unchanged after the refactor.

### Design decisions (from research.md)

- **Decision 1**: `str` subclass (`Role(str)`) — NOT `StrEnum`. Rationale: open extensibility
  (no code change for new roles); Pydantic serialises as plain string natively; `==` comparison
  with plain strings works via `str.__eq__`. `StrEnum` seals the set.
- **Decision 4**: Computed `@property role` returns `roles[0]` — no warning on read. Keeps
  callers in `wp_metadata.py` and `scanner.py` working without a separate refactor.
- **Decision 6**: `avatar_image: str | None = None` with YAML alias `avatar-image`. No path
  validation (deferred to issue #647).

---

## Subtask Guidance

### T001 — Write `Role(str)` class

**File**: `src/doctrine/agent_profiles/profile.py`

Replace the `Role(StrEnum)` class with:

```python
class Role(str):
    """Half-open role value object.

    Subclasses ``str`` instead of ``StrEnum`` so that custom roles (e.g.
    ``Role("senior-tech-lead")``) are first-class instances without any code
    change.  Well-known roles are declared as class-level constants and
    listed in ``_KNOWN``.

    Why ``str`` and not ``StrEnum``
    --------------------------------
    ``StrEnum`` seals the set of valid values at class definition time.
    Teams introducing project-specific roles (e.g. ``"retrospective-
    facilitator"`` for Phase 6 WP6.6) would need to fork or monkey-patch
    the library.  A plain ``str`` subclass carries the same ``role ==
    "implementer"`` ergonomics via ``str.__eq__`` while remaining fully
    open.

    Distinguishing well-known from custom roles
    -------------------------------------------
    ``Role.is_known(role)`` returns ``True`` iff the value belongs to the
    static constant set shipped with this library.  Use this for
    informational checks (capabilities lookup, DRG annotations); do **not**
    use it as a validity gate — custom roles are intentionally valid.

    Future extension points (do not add without a new spec)
    -------------------------------------------------------
    - ``description: str`` field in ``__init__`` to document role semantics
    - YAML-registry loading at import time (``Role.known_roles()``)
    """

    _KNOWN: ClassVar[frozenset[str]] = frozenset()  # populated after class body

    def __new__(cls, value: str) -> "Role":
        if not value:
            raise ValueError("Role value must be a non-empty string")
        return str.__new__(cls, value)

    @classmethod
    def is_known(cls, role: "Role | str") -> bool:
        """Return True iff *role* is one of the well-known static constants."""
        return str(role) in cls._KNOWN

    # ── Well-known constants ──────────────────────────────────────────────
    IMPLEMENTER: ClassVar["Role"]
    REVIEWER:    ClassVar["Role"]
    ARCHITECT:   ClassVar["Role"]
    DESIGNER:    ClassVar["Role"]
    PLANNER:     ClassVar["Role"]
    RESEARCHER:  ClassVar["Role"]
    CURATOR:     ClassVar["Role"]
    MANAGER:     ClassVar["Role"]


# Assign constants after the class body so __new__ is already defined
Role.IMPLEMENTER = Role("implementer")
Role.REVIEWER    = Role("reviewer")
Role.ARCHITECT   = Role("architect")
Role.DESIGNER    = Role("designer")
Role.PLANNER     = Role("planner")
Role.RESEARCHER  = Role("researcher")
Role.CURATOR     = Role("curator")
Role.MANAGER     = Role("manager")

# Populate _KNOWN after constants exist
Role._KNOWN = frozenset({
    str(Role.IMPLEMENTER), str(Role.REVIEWER), str(Role.ARCHITECT),
    str(Role.DESIGNER), str(Role.PLANNER), str(Role.RESEARCHER),
    str(Role.CURATOR), str(Role.MANAGER),
})
```

**Notes**:
- `ClassVar` declarations inside the body are type-annotation stubs only; the actual
  assignments happen after the class so `__new__` is available.
- The `_KNOWN: ClassVar[frozenset[str]] = frozenset()` placeholder is replaced by the
  `Role._KNOWN = frozenset(...)` assignment immediately after constants.
- The `ClassVar` annotations for `IMPLEMENTER`, etc. inside the class body are valid
  Python (they're annotations, not runtime assignments). The real assignments below the
  class body satisfy mypy.

**Required imports** to add / verify at top of `profile.py`:
```python
from __future__ import annotations
from typing import ClassVar, Any
```

---

### T002 — Write `Role` class docstring

The docstring is already included in the class body above (T001). Verify it covers:
1. Why `str` subclass and not `StrEnum` (open extensibility, Phase 6 WP6.6 use case)
2. `is_known()` contract
3. Future extension points note (description field, YAML registry) — must state
   "do not add without a new spec"

No separate step needed if T001 is done correctly; this task is a checklist reminder.

---

### T003 — Delete `Role(StrEnum)` class and `_coerce_role` function

Remove from `profile.py`:
- The `class Role(StrEnum): ...` class (all lines)
- The `def _coerce_role(value: Any) -> Role | str: ...` function
- The `from enum import StrEnum` import (only if nothing else uses it — verify)

After deletion `profile.py` should have the new `Role(str)` class from T001 in place.
Run `rg "StrEnum" src/doctrine/agent_profiles/profile.py` to confirm no residue.

---

### T004 — Verify `capabilities.py` unchanged

`capabilities.py` uses `Role` constants as dict keys:

```python
DEFAULT_ROLE_CAPABILITIES: dict[Role, RoleCapabilities] = {
    Role.IMPLEMENTER: RoleCapabilities(...),
    ...
}
```

Because the new `Role` subclasses `str`, `Role("implementer") == Role.IMPLEMENTER` is
`True` via `str.__eq__`, so all dict lookups continue to work.

**Action**: Run `pytest tests/doctrine/ -k "capabilities" -x` to confirm no failures.
If the test for `get_capabilities` is missing, the broader T010 test suite will cover it.

No code changes to `capabilities.py` are expected. If any are needed, make them and
document why.

---

### T005 — Add `model_validator(mode="before")` to `AgentProfile`

**File**: `src/doctrine/agent_profiles/profile.py`

Add inside `AgentProfile`:

```python
@model_validator(mode="before")
@classmethod
def _coerce_scalar_role(cls, data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    has_role  = "role"  in data
    has_roles = "roles" in data
    if has_role and not has_roles:
        value = data["role"]
        profile_id = data.get("profile-id", "<unknown>")
        warnings.warn(
            f"Profile '{profile_id}': the scalar 'role:' field is deprecated. "
            f"Replace with: roles: [{value}]",
            DeprecationWarning,
            stacklevel=2,
        )
        data = {**data, "roles": [value]}
        del data["role"]  # or pop; ensure "role" key is removed
    # if has_roles (with or without stale "role"), pass through
    # if neither: Pydantic will raise ValidationError via min_length=1 on roles
    return data
```

**Required imports** to add / verify:
```python
import warnings
from pydantic import model_validator
```

The `stacklevel=2` aims the warning at the call site that constructed the model (e.g.
the YAML loader), not at the validator internals.

---

### T006 — Replace `role` field with `roles: list[Role]` + `@property role`

**File**: `src/doctrine/agent_profiles/profile.py`

**Remove** the old field:
```python
role: Annotated[Role | str, BeforeValidator(_coerce_role)] = Role.IMPLEMENTER
```

**Add** in its place:
```python
roles: list[Role] = Field(min_length=1)
```

Pydantic will coerce each list item through `Role(value)` automatically because `Role`
is a `str` subclass and Pydantic's `list[Role]` coercion calls the constructor.
If explicit coercion is needed, use:
```python
roles: list[Annotated[Role, BeforeValidator(lambda v: Role(v) if not isinstance(v, Role) else v)]] = Field(min_length=1)
```

**Add** the computed property:
```python
@property
def role(self) -> Role:
    """Primary role — first entry in ``roles``."""
    return self.roles[0]
```

The property name `role` shadows any Pydantic field of the same name; after removing
the field declaration this is safe.

---

### T007 — Add `avatar_image` field

**File**: `src/doctrine/agent_profiles/profile.py`

Add to `AgentProfile`:
```python
avatar_image: str | None = Field(default=None, alias="avatar-image")
```

This must appear after `roles` (or anywhere in the model body — ordering doesn't matter
for Pydantic). Verify `model_config` already has `populate_by_name=True` (or equivalent)
so both `avatar_image` and `avatar-image` work as keys. If not, add it:
```python
model_config = ConfigDict(populate_by_name=True)
```

---

### T008 — Update `TaskContext.required_role`

**File**: `src/doctrine/agent_profiles/profile.py`

Locate `TaskContext` (or wherever `required_role` is declared). Update its annotation:

**Before**:
```python
required_role: Role | str | None = None
```

**After**:
```python
required_role: Annotated[Role | None, BeforeValidator(lambda v: Role(v.lower()) if isinstance(v, str) else v)] = None
```

This coerces string inputs (e.g. `"implementer"`) to `Role` instances at field
assignment time, keeping the type annotation truthful.

---

### T009 — Write `tests/doctrine/test_role_value_object.py`

Create `tests/doctrine/test_role_value_object.py` with the following test cases:

```python
"""Tests for the Role half-open value object."""
import json
import warnings
import pytest
from doctrine.agent_profiles.profile import Role


class TestRoleConstruction:
    def test_known_constant_is_role_instance(self):
        assert isinstance(Role.IMPLEMENTER, Role)

    def test_role_is_str_subclass(self):
        assert issubclass(Role, str)
        assert isinstance(Role.IMPLEMENTER, str)

    def test_custom_role_constructs_without_error(self):
        r = Role("senior-tech-lead")
        assert r == "senior-tech-lead"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            Role("")

    def test_constant_equality_with_plain_string(self):
        assert Role.IMPLEMENTER == "implementer"
        assert Role.REVIEWER    == "reviewer"
        assert Role.ARCHITECT   == "architect"
        assert Role.DESIGNER    == "designer"
        assert Role.PLANNER     == "planner"
        assert Role.RESEARCHER  == "researcher"
        assert Role.CURATOR     == "curator"
        assert Role.MANAGER     == "manager"

    def test_constant_equality_with_self(self):
        assert Role.IMPLEMENTER == Role("implementer")


class TestRoleIsKnown:
    def test_known_constant_returns_true(self):
        assert Role.is_known(Role.IMPLEMENTER)

    def test_plain_string_known_returns_true(self):
        assert Role.is_known("implementer")

    def test_custom_role_returns_false(self):
        assert not Role.is_known(Role("data-engineer"))

    def test_unknown_string_returns_false(self):
        assert not Role.is_known("unknown-role")


class TestRoleSerialization:
    def test_json_round_trip(self):
        r = Role.IMPLEMENTER
        serialised = json.dumps(r)
        rehydrated = Role(json.loads(serialised))
        assert rehydrated == r
        assert isinstance(rehydrated, Role)

    def test_custom_role_round_trip(self):
        r = Role("my-custom-role")
        assert Role(json.loads(json.dumps(r))) == r

    def test_pydantic_serialises_as_string(self):
        from doctrine.agent_profiles.profile import AgentProfile
        p = AgentProfile(**{
            "profile-id": "test", "name": "Test", "version": "1.0",
            "roles": ["implementer"],
        })
        dumped = p.model_dump()
        assert dumped["roles"] == ["implementer"]
        assert isinstance(dumped["roles"][0], str)
```

Adjust constructor args as needed to match the actual `AgentProfile` required fields.
Run `pytest tests/doctrine/test_role_value_object.py -v` to verify all pass.

---

### T010 — Write `AgentProfile` model tests

Add tests to `tests/doctrine/test_role_value_object.py` (or a new
`tests/doctrine/test_agent_profile_model.py` if preferred) covering:

```python
class TestAgentProfileModel:
    BASE = {"profile-id": "test-p", "name": "Test Profile", "version": "1.0"}

    def test_roles_list_accepted(self):
        p = AgentProfile(**self.BASE, roles=["implementer", "reviewer"])
        assert p.roles == [Role.IMPLEMENTER, Role.REVIEWER]
        assert p.role == Role.IMPLEMENTER  # computed property

    def test_scalar_role_coerces_to_list_with_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            p = AgentProfile(**self.BASE, role="implementer")
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "test-p" in str(w[0].message)
        assert "roles: [implementer]" in str(w[0].message)
        assert p.roles == [Role.IMPLEMENTER]

    def test_neither_role_nor_roles_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AgentProfile(**self.BASE)

    def test_both_keys_roles_wins(self):
        """If YAML has both role and roles (odd but possible), roles takes precedence."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            # Pydantic receives both; validator should not trigger because roles is present
            p = AgentProfile(**{**self.BASE, "roles": ["architect"], "role": "implementer"})
        assert p.roles == [Role.ARCHITECT]

    def test_avatar_present(self):
        p = AgentProfile(**self.BASE, roles=["implementer"],
                         **{"avatar-image": "agent_profiles/avatars/test.png"})
        assert p.avatar_image == "agent_profiles/avatars/test.png"

    def test_avatar_absent(self):
        p = AgentProfile(**self.BASE, roles=["implementer"])
        assert p.avatar_image is None

    def test_custom_role_accepted(self):
        p = AgentProfile(**self.BASE, roles=["my-custom-org-role"])
        assert p.roles[0] == "my-custom-org-role"
        assert isinstance(p.roles[0], Role)
        assert not Role.is_known(p.roles[0])
```

---

## Definition of Done

- [ ] `Role(str)` class exists with `__new__`, `_KNOWN`, `is_known`, and 8 class constants
- [ ] `Role` docstring covers: why str not StrEnum; is_known contract; Phase 6 note; extension points
- [ ] `Role(StrEnum)` and `_coerce_role` deleted from `profile.py`
- [ ] `AgentProfile.roles: list[Role]` field with `min_length=1`
- [ ] `AgentProfile.role` is a `@property` returning `roles[0]`
- [ ] `AgentProfile.avatar_image: str | None = Field(default=None, alias="avatar-image")`
- [ ] `model_validator(mode="before")` coerces scalar `role:` → single-element `roles` with `DeprecationWarning`
- [ ] Warning message includes profile-id and exact replacement syntax
- [ ] `TaskContext.required_role` updated to `Role | None` with string coercion
- [ ] `pytest tests/doctrine/test_role_value_object.py -v` passes
- [ ] `pytest tests/doctrine/ -x` passes (no regressions in existing tests)
- [ ] `mypy src/doctrine/agent_profiles/profile.py` reports no errors

## Risks

- **`model_config`**: If `AgentProfile` does not have `populate_by_name=True`, the
  `avatar-image` alias won't be readable by Python attribute name `avatar_image`. Check and
  add `ConfigDict(populate_by_name=True)` if missing.
- **`role` property vs field name conflict**: After removing the Pydantic field `role`, the
  `@property role` is safe. If mypy complains about a `@property` shadowing a field, suppress
  with `# type: ignore[override]` and note in a comment.
- **Capabilities dict**: `DEFAULT_ROLE_CAPABILITIES` keys are compared at runtime using
  `dict.get(role)`. Verify with `get_capabilities(Role("implementer"))` returning a value.

## Activity Log

- 2026-04-21T19:43:58Z – claude – shell_pid=336209 – Moved to for_review
- 2026-04-21T20:44:32Z – claude – shell_pid=336209 – Moved to in_review
- 2026-04-21T20:44:38Z – claude – shell_pid=336209 – Moved to approved
