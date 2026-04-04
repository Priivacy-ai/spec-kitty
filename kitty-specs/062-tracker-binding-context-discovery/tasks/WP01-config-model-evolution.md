---
work_package_id: WP01
title: Config Model Evolution
dependencies: []
requirement_refs:
- C-005
- FR-009
- FR-010
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: f35079bfa725abcac7cfe966c94f83d780374a37
created_at: '2026-04-04T09:34:46.177609+00:00'
subtasks: [T001, T002, T003, T004, T005]
shell_pid: "48243"
agent: "codex"
history:
- date: '2026-04-04T09:10:15Z'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/tracker/
execution_mode: code_change
owned_files: [src/specify_cli/tracker/config.py, tests/sync/tracker/test_config.py]
---

# WP01: Config Model Evolution

## Objective

Evolve `TrackerProjectConfig` in `src/specify_cli/tracker/config.py` to support `binding_ref` as the primary binding key alongside the legacy `project_slug`. Add cached display metadata fields. Implement unknown field passthrough to prevent data loss during round-trips.

## Context

- **Spec**: FR-009 (binding_ref as primary key), FR-010 (read precedence), C-005 (project_slug not removed)
- **Plan**: Config Layer in plan.md architecture section
- **Data Model**: TrackerProjectConfig entity in data-model.md
- **Current code**: `src/specify_cli/tracker/config.py` — TrackerProjectConfig dataclass (lines 28-88)
- **Current tests**: `tests/sync/tracker/test_config.py`

The current `TrackerProjectConfig` stores `provider`, `project_slug`, `workspace`, `doctrine_mode`, `doctrine_field_owners`. This WP adds three new fields and evolves `is_configured`, `to_dict()`, `from_dict()`.

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies — this WP can start immediately.

## Subtasks

### T001: Add New Fields to Dataclass

**Purpose**: Extend `TrackerProjectConfig` with the three new fields needed for host-resolved binding.

**Steps**:
1. Open `src/specify_cli/tracker/config.py`
2. Add fields to the `TrackerProjectConfig` dataclass after `project_slug`:
   ```python
   binding_ref: str | None = None
   display_label: str | None = None
   provider_context: dict[str, str] | None = None
   ```
3. Add a private `_extra` field (not serialized by name) for unknown field passthrough:
   ```python
   _extra: dict[str, Any] = field(default_factory=dict, repr=False)
   ```

**Files**: `src/specify_cli/tracker/config.py`

**Validation**:
- [ ] Three new public fields exist on the dataclass
- [ ] `_extra` field exists with `repr=False`
- [ ] Default values are all `None` / empty dict
- [ ] Existing fields unchanged

### T002: Update is_configured Property

**Purpose**: SaaS binding is now configured if `provider` is set AND (`binding_ref` is set OR `project_slug` is set). This enables dual-read.

**Steps**:
1. Update `is_configured` property (currently line 38-46):
   ```python
   @property
   def is_configured(self) -> bool:
       if not self.provider:
           return False
       if self.provider in SAAS_PROVIDERS:
           return bool(self.binding_ref) or bool(self.project_slug)
       if self.provider in LOCAL_PROVIDERS:
           return bool(self.workspace)
       return False
   ```

**Files**: `src/specify_cli/tracker/config.py`

**Validation**:
- [ ] `provider=linear, binding_ref=x` → True
- [ ] `provider=linear, project_slug=x` → True
- [ ] `provider=linear, binding_ref=x, project_slug=y` → True
- [ ] `provider=linear` (neither set) → False
- [ ] Local providers unchanged

### T003: Update to_dict()/from_dict() with _extra Passthrough

**Purpose**: Serialize new fields. Deserialize with backward compatibility (missing fields = None). Preserve unknown keys across round-trips.

**Steps**:
1. Update `to_dict()` (currently line 48-57):
   ```python
   def to_dict(self) -> dict[str, object]:
       result: dict[str, object] = {
           **self._extra,  # Unknown fields first (known fields override)
           "provider": self.provider,
           "binding_ref": self.binding_ref,
           "project_slug": self.project_slug,
           "display_label": self.display_label,
           "provider_context": dict(self.provider_context) if self.provider_context else None,
           "workspace": self.workspace,
           "doctrine": {
               "mode": self.doctrine_mode,
               "field_owners": dict(self.doctrine_field_owners),
           },
       }
       return result
   ```

2. Update `from_dict()` (currently line 59-88):
   - Parse `binding_ref`, `display_label`, `provider_context` with same defensive pattern as existing fields
   - `provider_context`: parse as `dict[str, str]` if dict, else None
   - Capture all unrecognized top-level keys (not in known set) into `_extra`
   ```python
   _KNOWN_KEYS = {"provider", "binding_ref", "project_slug", "display_label",
                   "provider_context", "workspace", "doctrine"}
   
   # At end of from_dict:
   extra = {k: v for k, v in data.items() if k not in _KNOWN_KEYS}
   return cls(..., _extra=extra)
   ```

**Files**: `src/specify_cli/tracker/config.py`

**Validation**:
- [ ] New fields survive save → load round-trip
- [ ] Pre-062 config (no binding_ref etc.) loads without error
- [ ] Unknown keys survive round-trip (e.g., `future_field: 42`)
- [ ] `provider_context` dict parsed correctly
- [ ] None/missing values handled gracefully

### T004: Write Config Roundtrip Tests

**Purpose**: Verify backward compatibility and new field persistence.

**Steps**:
1. Add to `tests/sync/tracker/test_config.py`:
   - `test_binding_ref_roundtrip`: save with binding_ref, load, verify
   - `test_display_label_roundtrip`: save with display_label, load, verify
   - `test_provider_context_roundtrip`: save with provider_context dict, load, verify
   - `test_legacy_config_loads_without_binding_ref`: load pre-062 config, verify binding_ref=None
   - `test_unknown_field_passthrough`: save config, manually add unknown key to YAML, load, save again, verify key preserved
   - `test_all_new_fields_together`: save with all new + old fields, load, verify all

**Files**: `tests/sync/tracker/test_config.py`

**Validation**:
- [ ] All new tests pass
- [ ] All existing tests still pass

### T005: Write is_configured Tests

**Purpose**: Cover all SaaS binding state combinations.

**Steps**:
1. Add parametrized test to `tests/sync/tracker/test_config.py`:
   ```python
   @pytest.mark.parametrize("binding_ref,project_slug,expected", [
       ("ref", None, True),       # binding_ref only
       (None, "slug", True),      # project_slug only (legacy)
       ("ref", "slug", True),     # both
       (None, None, False),       # neither
   ])
   def test_is_configured_saas_dual_read(binding_ref, project_slug, expected):
       config = TrackerProjectConfig(provider="linear", binding_ref=binding_ref, project_slug=project_slug)
       assert config.is_configured == expected
   ```
2. Verify local provider behavior unchanged with similar parametrized test

**Files**: `tests/sync/tracker/test_config.py`

**Validation**:
- [ ] All parametrized test cases pass
- [ ] Local provider tests unchanged

## Definition of Done

- [ ] `TrackerProjectConfig` has `binding_ref`, `display_label`, `provider_context`, `_extra` fields
- [ ] `is_configured` returns True for SaaS when either `binding_ref` or `project_slug` is set
- [ ] `to_dict()`/`from_dict()` handle new fields + unknown passthrough
- [ ] Pre-062 configs load without error (backward compat)
- [ ] All tests pass: `python -m pytest tests/sync/tracker/test_config.py -x -q`
- [ ] `ruff check src/specify_cli/tracker/config.py`
- [ ] `mypy src/specify_cli/tracker/config.py`

## Risks

- **Dataclass slot conflict**: If `TrackerProjectConfig` uses `slots=True` (it does at line 28), the `_extra` field with `field(default_factory=dict)` works fine with slots. No risk.
- **YAML serialization of None**: `ruamel.yaml` serializes None as `null`. Verify this doesn't break existing config readers.

## Reviewer Guidance

- Verify `_extra` passthrough: add an unknown key to a YAML file, load, save, check key preserved
- Verify backward compat: a config with only `provider` + `project_slug` must load cleanly
- Check that `to_dict()` puts `_extra` first so known fields override on conflict

## Activity Log

- 2026-04-04T09:34:46Z – coordinator – shell_pid=32339 – Started implementation via workflow command
- 2026-04-04T09:38:22Z – coordinator – shell_pid=32339 – Ready for review: TrackerProjectConfig evolved with binding_ref, display_label, provider_context, _extra fields. Dual-read is_configured, backward compat, unknown field passthrough. 57 tests pass, ruff clean.
- 2026-04-04T09:39:08Z – codex – shell_pid=48243 – Started review via workflow command
