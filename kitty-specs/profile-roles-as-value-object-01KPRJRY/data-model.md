# Data Model: Profile Roles as Value Object

**Mission**: profile-roles-as-value-object-01KPRJRY

---

## `Role` — Half-Open Value Object

```
Role(str)
├── class constants (closed set — shipped with the library)
│   ├── IMPLEMENTER = Role("implementer")
│   ├── REVIEWER    = Role("reviewer")
│   ├── ARCHITECT   = Role("architect")
│   ├── DESIGNER    = Role("designer")
│   ├── PLANNER     = Role("planner")
│   ├── RESEARCHER  = Role("researcher")
│   ├── CURATOR     = Role("curator")
│   └── MANAGER     = Role("manager")
│
└── runtime values (open set — any non-empty string)
    ├── Role("senior-tech-lead")   ← user-defined
    ├── Role("data-engineer")      ← user-defined
    └── ...
```

**Identity rules**:
- `Role("implementer") == "implementer"` → `True` (str.__eq__)
- `Role("implementer") == Role.IMPLEMENTER` → `True`
- `Role("custom") is not None` → `True`; accepted without error
- `Role.is_known(role)` → `True` iff the value is in the static constant set

**Serialisation**: a `Role` serialises as a plain string via Pydantic `model_dump`.
Round-trip fidelity: `Role(json_string) == original_role` for all values.

---

## `AgentProfile` — Updated Fields

### Changed field: `roles`

```
roles: list[Role]
  - replaces the scalar role field
  - minimum length: 1 (validated)
  - index 0 = primary role (used by routing priority signal)
  - index 1+ = secondary roles (used by membership queries, scored at 0.5)
  - YAML key: "roles" (new canonical) or "role" (deprecated scalar, coerced)
```

### New computed property: `role`

```
role: Role   (read-only @property)
  - returns roles[0]
  - backward-compatible accessor for callers that read a single role
  - no deprecation warning on read
```

### New field: `avatar_image`

```
avatar_image: str | None
  - YAML key: "avatar-image"
  - default: None
  - stores a path string relative to the doctrine package root
    (e.g. "agent_profiles/avatars/java-jenny.png")
  - no path validation at load time
  - forward-compatibility hook for issue #647
```

---

## YAML Schema — Supported Forms

### Canonical (new):
```yaml
roles:
  - implementer
  - reviewer
```

### Deprecated (backward compat — scalar coerced to list):
```yaml
role: implementer   # → roles: [Role("implementer")] + DeprecationWarning
```

### Rejection (neither key present):
```yaml
# No role/roles key → schema validation error
```

### DeprecationWarning message template:
```
Profile '<profile-id>': the scalar 'role:' field is deprecated.
Replace with: roles: [<value>]
```

---

## Routing Model — Updated Scoring

`_exact_id_signal(context, profile) -> float`

| Condition | Score |
|-----------|-------|
| `required_role` matches `profile.profile_id` | 1.0 |
| `required_role` matches `profile.roles[0]` (primary) | 1.0 |
| `required_role` matches any of `profile.roles[1:]` (secondary) | 0.5 |
| no match | 0.0 |

`_filter_candidates_by_role(candidates, required_role)`
- Includes a profile if `required_role` is in `profile.roles` (any position) or matches `profile.profile_id`

`find_by_role(role)` on `AgentProfileRepository`
- Returns all profiles where `role` appears anywhere in `profile.roles`

---

## Profile ID Rename Map

| Old `profile-id` | New `profile-id` | `name` change |
|-----------------|-----------------|---------------|
| `architect` | `architect-alphonso` | none |
| `curator` | `curator-carla` | none |
| `designer` | `designer-dagmar` | none |
| `implementer` | `implementer-ivan` | none |
| `planner` | `planner-priti` | "Planner Petra" → "Planner Priti" |
| `researcher` | `researcher-robbie` | "Researcher Rosa" → "Researcher Robbie" |
| `reviewer` | `reviewer-renata` | none |
| `generic-agent` | `generic-agent` | unchanged (base/fallback) |
| `human-in-charge` | `human-in-charge` | unchanged (sentinel) |
| `java-jenny` | `java-jenny` | already done |
| `python-pedro` | `python-pedro` | already done |

---

## `RoleCapabilities` — No structural change

`DEFAULT_ROLE_CAPABILITIES: dict[Role, RoleCapabilities]` keys remain the static
`Role` constants. The dict continues to work because `Role("implementer") == Role.IMPLEMENTER`
via `str.__eq__`. `get_capabilities(role)` gains a direct `Role` lookup path since
the half-open `Role` is already a `str`; the `isinstance(role, Role)` branch returns
the mapped capabilities for known roles, `None` for custom roles.
