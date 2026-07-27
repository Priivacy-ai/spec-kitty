# Data Model: Remove hidden --feature alias

**Mission**: `feature-alias-removal-01KW0N87`
**Scope**: Selector-resolution contract (minimal — this mission has no new persistent entities)

---

## Selector-Resolution Contract (post-alias-removal)

This mission simplifies the selector-resolution path. The following contract replaces the
`resolve_selector(alias_value=feature, alias_flag="--feature", ...)` pattern in all 8 in-scope files.

### Inline Guard — Canonical Form

```python
# Applied in: research, next_cmd, context, lifecycle.plan, lifecycle.tasks, mission_type.current
mission_norm = mission.strip() if isinstance(mission, str) else None
if not mission_norm:
    raise typer.BadParameter("--mission <slug> is required")
mission_slug = mission_norm
```

**Input**: `mission: str | None` — Typer-parsed value of `--mission` option; may be `None` if omitted,
a non-empty string, or (edge case) a whitespace-only string.

**Behaviour**:
1. `None` input → raises `typer.BadParameter` (Typer maps to exit code 2)
2. Whitespace-only string → normalized to `None` → raises `typer.BadParameter`
3. Non-empty string after strip → passed downstream as `mission_slug`

**Exit code on failure**: 2 (standard Typer `BadParameter` exit code)

**Message shape**: `"Error: Invalid value for '--mission': --mission <slug> is required"` (Typer default
`BadParameter` format)

### accept.py Variant (uses resolve_mission_handle — no resolve_selector)

```python
# accept.py — replaces `raw_handle = mission or feature`
raw_handle = mission.strip() if isinstance(mission, str) else None
if not raw_handle:
    # ... emit error message ...
    raise typer.Exit(2)
resolved = resolve_mission_handle(raw_handle, repo_root, json_mode=json_output)
```

### merge.py Variant (uses _resolve_slug_or_exit helper — no resolve_selector)

```python
# _resolve_slug_or_exit — replaces `(mission or feature or "").strip() or None`
mission_slug_raw = (mission or "").strip() or None
```

No-selector at merge.py end-of-flow (`if not resolved_mission`) → `raise typer.Exit(2)`.

### implement.py Variant (uses detect_feature_context — no resolve_selector)

`detect_feature_context()` is updated to remove `feature_flag` param:

```python
def detect_feature_context(
    mission_flag: str | None = None,
    repo_root: Path | None = None,
) -> tuple[str | None, str]:
    raw_handle = mission_flag.strip() if isinstance(mission_flag, str) else None
    if raw_handle is None:
        raise typer.BadParameter("--mission <slug> is required")
    # ... resolver logic unchanged ...
```

---

## Preserved Contracts (out-of-scope, unchanged)

| Contract | Location | Status |
|----------|----------|--------|
| `resolve_selector` function signature | `selector_resolution.py:123` | **Retained** (C-005) |
| `resolve_mission_handle` function | `selector_resolution.py:185` | Retained |
| `feature_slug` JSON field keys | all persisted artifacts | **Immutable** (C-003) |
| `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` env var | `selector_resolution.py` | Retained but inert after this mission |

---

## No New Entities

This mission introduces no new domain entities, database tables, or persistent data structures.
All changes are confined to the CLI surface layer and Python variable names.
