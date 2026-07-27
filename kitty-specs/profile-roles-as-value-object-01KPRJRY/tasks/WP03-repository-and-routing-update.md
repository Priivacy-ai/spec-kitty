---
work_package_id: WP03
title: Repository and Routing Update
dependencies:
- WP01
agent_profile: "python-pedro"
role: "implementer"
agent: "claude"
model: "claude-sonnet-4-6"
requirement_refs:
- FR-007
- FR-008
- FR-010
planning_base_branch: doctrine/profile_reinforcement
merge_target_branch: doctrine/profile_reinforcement
branch_strategy: Planning artifacts for this feature were generated on doctrine/profile_reinforcement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/profile_reinforcement unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
shell_pid: "356033"
history:
- at: '2026-04-21T18:24:37Z'
  event: created
authoritative_surface: src/doctrine/agent_profiles/repository.py
execution_mode: code_change
mission_slug: profile-roles-as-value-object-01KPRJRY
owned_files:
- src/doctrine/agent_profiles/repository.py
- tests/doctrine/test_profile_repository.py
tags: []
---

# WP03 — Repository and Routing Update

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Update `repository.py` so all role-based filtering, scoring, and lookup use
`profile.roles` (a list). Remove dead `isinstance(p.role, ...)` branches that
relied on the old `StrEnum | str` union. Write new tests for secondary-role
inclusion, primary scoring (1.0), and secondary scoring (0.5).

This WP can run in parallel with WP02 once WP01 is merged.

## Implementation Command

```bash
spec-kitty agent action implement WP03 --agent python-pedro
```

## Branch Strategy

- **Plan base**: `doctrine/profile_reinforcement`
- **Depends on**: WP01 lane — do not start until WP01 is merged
- **Parallelizes with**: WP02 (different files)
- **Merge target**: `doctrine/profile_reinforcement`

---

## Context

### Current `repository.py` (key functions)

```python
def _filter_candidates_by_role(
    candidates: list[AgentProfile], required_role: str
) -> list[AgentProfile]:
    role_str = required_role.lower()
    return [
        p for p in candidates
        if (isinstance(p.role, Role) and p.role.value == role_str)
        or (isinstance(p.role, str) and p.role.lower() == role_str)
        or p.profile_id == required_role
    ]


def _exact_id_signal(
    context: TaskContext, profile: AgentProfile
) -> float:
    req = context.required_role
    if req is None:
        return 0.0
    role_val = profile.role.value if isinstance(profile.role, Role) else str(profile.role).lower()
    return 1.0 if (req == profile.profile_id or req == role_val) else 0.0


def find_by_role(self, role: str | Role) -> list[AgentProfile]:
    role_lower = role.value.lower() if isinstance(role, Role) else role.lower()
    return [
        p for p in self._profiles.values()
        if (isinstance(p.role, Role) and p.role.value == role_lower)
        or (isinstance(p.role, str) and p.role.lower() == role_lower)
    ]
```

### After this WP

- `profile.role` is a `@property` returning `profile.roles[0]` — always a `Role` instance
- `profile.roles` is `list[Role]` — indexable, iterable
- No more `isinstance(p.role, Role)` / `isinstance(p.role, str)` branches

---

## Subtask Guidance

### T016 — Rewrite `_filter_candidates_by_role`

**File**: `src/doctrine/agent_profiles/repository.py`

Replace the existing function:

```python
def _filter_candidates_by_role(
    candidates: list[AgentProfile], required_role: str
) -> list[AgentProfile]:
    return [
        p for p in candidates
        if required_role in p.roles or p.profile_id == required_role
    ]
```

`required_role in p.roles` uses `str.__eq__` (since `Role` is a `str` subclass), so
string comparison with `Role` instances is seamless. Case sensitivity follows whatever
the caller passes; callers should already lower-case `required_role` before calling this
function. Check call sites and document the expectation with a brief inline note if the
old code was doing `.lower()` normalization.

---

### T017 — Rewrite `_exact_id_signal` with primary/secondary scoring

**File**: `src/doctrine/agent_profiles/repository.py`

```python
def _exact_id_signal(
    context: TaskContext, profile: AgentProfile
) -> float:
    req = context.required_role
    if req is None:
        return 0.0
    if req == profile.profile_id or req == profile.roles[0]:
        return 1.0
    if req in profile.roles[1:]:
        return 0.5
    return 0.0
```

**Scoring rules** (from data-model.md):
| Condition | Score |
|-----------|-------|
| `req` matches `profile.profile_id` | 1.0 |
| `req` matches `profile.roles[0]` (primary) | 1.0 |
| `req` is in `profile.roles[1:]` (secondary) | 0.5 |
| no match | 0.0 |

The `required_role` on `TaskContext` is now `Role | None` (after WP01 T008); `req == profile.roles[0]`
uses `str.__eq__` and handles both `Role` and plain `str` correctly.

---

### T018 — Rewrite `find_by_role`

**File**: `src/doctrine/agent_profiles/repository.py`

```python
def find_by_role(self, role: str | Role) -> list[AgentProfile]:
    return [
        p for p in self._profiles.values()
        if role in p.roles
    ]
```

`role in p.roles` iterates the list and uses `str.__eq__` for each comparison.

---

### T019 — Remove dead `isinstance` branches

**File**: `src/doctrine/agent_profiles/repository.py`

After T016–T018, search for any remaining `isinstance(p.role, Role)` or
`isinstance(p.role, str)` patterns:

```bash
rg "isinstance.*\.role" src/doctrine/agent_profiles/repository.py
```

Delete any dead branches. If there are guard checks like:
```python
if isinstance(p.role, Role):
    role_val = p.role.value
else:
    role_val = str(p.role)
```
these can be replaced with simply `role_val = p.role` (the property always returns a `Role`
instance, which is already a `str`).

Also remove the `from enum import StrEnum` import if `StrEnum` is no longer referenced
in `repository.py`.

---

### T020 — Audit existing tests + write new routing and lookup tests

**File**: `tests/doctrine/test_profile_repository.py`

#### Part A — Audit existing tests for old patterns (do this first)

Before adding new tests, scan and fix patterns left over from the `StrEnum` era:

```bash
rg "\.role\.value" tests/doctrine/test_profile_repository.py
rg "isinstance.*role.*Role" tests/doctrine/test_profile_repository.py
rg '"role":' tests/doctrine/test_profile_repository.py
```

For each hit:
- `profile.role.value` → replace with `profile.role` (already a `str`)
- `isinstance(x, Role)` assertions that rely on StrEnum behavior → update to `isinstance(x, str)` or a direct equality check
- `"role": "implementer"` fixture dicts → change to `"roles": ["implementer"]` (unless the test intentionally exercises the deprecation coercion path; if so, add a `warnings.catch_warnings` block and a comment)

#### Part B — Add two new test classes (do not remove existing tests)

```python
class TestMultiRoleRouting:
    """Tests for profiles that carry multiple roles."""

    def _make_profile(self, profile_id: str, roles: list[str]) -> AgentProfile:
        return AgentProfile(**{
            "profile-id": profile_id,
            "name": f"Test {profile_id}",
            "version": "1.0",
            "roles": roles,
        })

    def test_secondary_role_included_in_filter(self):
        """A profile with secondary role still passes the role filter."""
        p = self._make_profile("arch-alex", ["architect", "researcher"])
        result = _filter_candidates_by_role([p], "researcher")
        assert p in result

    def test_primary_role_included_in_filter(self):
        p = self._make_profile("arch-alex", ["architect", "researcher"])
        result = _filter_candidates_by_role([p], "architect")
        assert p in result

    def test_unrelated_role_excluded_from_filter(self):
        p = self._make_profile("arch-alex", ["architect", "researcher"])
        result = _filter_candidates_by_role([p], "implementer")
        assert p not in result

    def test_primary_role_signal_is_1_0(self):
        p = self._make_profile("arch-alex", ["architect", "researcher"])
        ctx = TaskContext(required_role=Role("architect"))
        assert _exact_id_signal(ctx, p) == 1.0

    def test_secondary_role_signal_is_0_5(self):
        p = self._make_profile("arch-alex", ["architect", "researcher"])
        ctx = TaskContext(required_role=Role("researcher"))
        assert _exact_id_signal(ctx, p) == 0.5

    def test_no_match_signal_is_0_0(self):
        p = self._make_profile("arch-alex", ["architect", "researcher"])
        ctx = TaskContext(required_role=Role("implementer"))
        assert _exact_id_signal(ctx, p) == 0.0

    def test_profile_id_match_signal_is_1_0(self):
        p = self._make_profile("arch-alex", ["architect"])
        ctx = TaskContext(required_role=Role("arch-alex"))
        assert _exact_id_signal(ctx, p) == 1.0


class TestRoleLookup:
    """find_by_role returns ALL profiles that list the role (primary or secondary).
    get() returns the unique profile for a profile_id or None.
    """

    def _repo_with(self, *profiles: AgentProfile) -> AgentProfileRepository:
        repo = AgentProfileRepository.__new__(AgentProfileRepository)
        repo._profiles = {p.profile_id: p for p in profiles}
        repo._hierarchy_index = None
        return repo

    def _make_profile(self, profile_id: str, roles: list[str]) -> AgentProfile:
        return AgentProfile(**{
            "profile-id": profile_id,
            "name": f"Test {profile_id}",
            "version": "1.0",
            "roles": roles,
        })

    # ── find_by_role: role-based search, many results ─────────────────────

    def test_find_by_role_returns_primary_role_profile(self):
        p = self._make_profile("arch-alex", ["architect"])
        repo = self._repo_with(p)
        assert p in repo.find_by_role("architect")

    def test_find_by_role_returns_secondary_role_profile(self):
        """find_by_role checks all roles, not just the primary."""
        p = self._make_profile("arch-bob", ["implementer", "architect"])
        repo = self._repo_with(p)
        assert p in repo.find_by_role("architect")

    def test_find_by_role_returns_multiple_profiles_sharing_a_role(self):
        """When several profiles list the same role, all are returned."""
        primary   = self._make_profile("arch-alex", ["architect"])
        secondary = self._make_profile("arch-bob",  ["implementer", "architect"])
        repo = self._repo_with(primary, secondary)

        result = repo.find_by_role("architect")
        assert len(result) == 2
        assert primary   in result
        assert secondary in result

    def test_find_by_role_returns_empty_when_no_match(self):
        p = self._make_profile("arch-alex", ["architect"])
        repo = self._repo_with(p)
        assert repo.find_by_role("implementer") == []

    def test_find_by_role_with_role_instance(self):
        """find_by_role accepts a Role instance, not just a plain string."""
        p = self._make_profile("impl-ivan", ["implementer"])
        repo = self._repo_with(p)
        assert p in repo.find_by_role(Role.IMPLEMENTER)

    # ── get(): profile_id lookup, unique result ───────────────────────────

    def test_get_returns_profile_for_known_id(self):
        p = self._make_profile("arch-alex", ["architect"])
        repo = self._repo_with(p)
        assert repo.get("arch-alex") is p

    def test_get_returns_none_for_unknown_id(self):
        repo = self._repo_with()
        assert repo.get("nonexistent") is None

    def test_get_is_unique_two_profiles_with_different_ids(self):
        """Different profile_ids never collide — dict guarantees uniqueness."""
        p1 = self._make_profile("arch-alex", ["architect"])
        p2 = self._make_profile("arch-bob",  ["architect"])
        repo = self._repo_with(p1, p2)
        assert repo.get("arch-alex") is p1
        assert repo.get("arch-bob")  is p2
        assert repo.get("arch-alex") is not p2
```

Adjust imports and `TaskContext` / `AgentProfileRepository` construction to match
actual module paths. Run `pytest tests/doctrine/test_profile_repository.py -v` to confirm all pass.

---

## Definition of Done

- [ ] `_filter_candidates_by_role` checks `required_role in profile.roles` (any position)
- [ ] `_exact_id_signal` returns 1.0 for primary match, 0.5 for secondary, 0.0 for none
- [ ] `find_by_role(role)` checks `role in profile.roles` — returns **all** profiles that list the role at any position; multiple results are expected and correct
- [ ] `get(profile_id)` returns the unique profile for that ID or `None` — uniqueness is guaranteed by the dict key; no profile_id maps to more than one result
- [ ] No `isinstance(p.role, Role)` or `isinstance(p.role, str)` branches remain
- [ ] Existing tests audited: no `.role.value`, no StrEnum-dependent `isinstance` checks, no scalar `"role":` fixture dicts (unless intentionally testing coercion path with comment)
- [ ] `pytest tests/doctrine/test_profile_repository.py -v` passes (old + new tests)
- [ ] `TestRoleLookup::test_find_by_role_returns_multiple_profiles_sharing_a_role` explicitly verifies the many-results case
- [ ] `TestRoleLookup::test_get_is_unique_two_profiles_with_different_ids` explicitly verifies profile_id uniqueness

## Risks

- **Case sensitivity**: Old code called `.lower()` on role strings before comparison. The
  new `Role("implementer")` is already lowercase (by convention). Verify call sites pass
  normalized values; add a `req = str(req).lower()` normalization inside the functions if
  the broader codebase passes un-normalized strings.
- **`profile_id` matching**: `p.profile_id == required_role` is a string equality check.
  Profile IDs are like `"implementer-ivan"`. If callers pass `Role("implementer-ivan")`,
  this works via `str.__eq__`. Confirm with a test.

## Activity Log

- 2026-04-21T20:50:58Z – claude – shell_pid=356033 – Started implementation via action command
