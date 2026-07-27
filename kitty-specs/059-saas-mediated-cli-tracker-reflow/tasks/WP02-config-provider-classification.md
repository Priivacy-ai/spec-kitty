---
work_package_id: WP02
title: Config Model + Provider Classification
dependencies: []
requirement_refs:
- FR-001
- FR-012
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 856b78a1935a8f9ae3fea274c0424fd7d8d6c90a
created_at: '2026-03-30T19:25:39.176884+00:00'
subtasks: [T008, T009, T010, T011]
history:
- at: '2026-03-30T19:14:19+00:00'
  event: created
  actor: planner
authoritative_surface: src/specify_cli/tracker/config.py
execution_mode: code_change
mission_id: 01KN2371WW548PPDMY6HMSB7W1
owned_files:
- src/specify_cli/tracker/config.py
- tests/sync/tracker/test_config.py
wp_code: WP02
---

# WP02: Config Model + Provider Classification

## Objective

Update `TrackerProjectConfig` in `src/specify_cli/tracker/config.py` to support the SaaS-backed binding model (`provider + project_slug`) while preserving the local binding model (`provider + workspace`) for beads/fp. Define provider classification constants used by all downstream WPs.

## Context

- The frozen PRI-12 contract uses `provider` + `project_slug` as the routing key in API request bodies.
- `team_slug` comes from `CredentialStore.get_team_slug()` at call time — it is NOT stored in the tracker binding.
- `workspace` remains valid for beads/fp (local providers).
- The config lives in `.kittify/config.yaml` under the `tracker:` section.

## Implementation Command

```bash
spec-kitty implement WP02
```

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- No dependencies — branch directly from `main`. Can run in parallel with WP01.

---

## Subtask T008: Add project_slug to TrackerProjectConfig

**Purpose**: Extend the config dataclass so SaaS-backed bindings store `project_slug` instead of (or alongside) `workspace`.

**Steps**:

1. Open `src/specify_cli/tracker/config.py`
2. Add `project_slug: str | None = None` field to `TrackerProjectConfig` dataclass (after `provider`, before `workspace`)
3. Update `to_dict()` to include `project_slug` in serialized output:
   ```python
   def to_dict(self) -> dict[str, object]:
       return {
           "provider": self.provider,
           "project_slug": self.project_slug,
           "workspace": self.workspace,
           "doctrine": { ... },
       }
   ```
4. Update `from_dict()` to parse `project_slug`:
   ```python
   project_slug = data.get("project_slug")
   # ... same validation pattern as provider/workspace
   ```
5. Ensure YAML roundtrip preserves `project_slug` (the existing `save_tracker_config` + `load_tracker_config` flow should work since `to_dict`/`from_dict` are the serialization boundary)

**Files**: `src/specify_cli/tracker/config.py` (~15 lines changed)

---

## Subtask T009: Update is_configured Property

**Purpose**: Make the "is this tracker configured?" check provider-aware.

**Steps**:

1. Current `is_configured` just checks `bool(self.provider and self.workspace)`
2. Update to be provider-aware:
   ```python
   @property
   def is_configured(self) -> bool:
       if not self.provider:
           return False
       if self.provider in SAAS_PROVIDERS:
           return bool(self.project_slug)
       if self.provider in LOCAL_PROVIDERS:
           return bool(self.workspace)
       return False  # Unknown or removed provider
   ```
3. Import `SAAS_PROVIDERS` and `LOCAL_PROVIDERS` from the constants defined in T010

**Files**: `src/specify_cli/tracker/config.py` (~10 lines changed)

**Note**: This creates a circular dependency risk if constants are in a different module. Place constants in `config.py` itself or in a small `constants.py` if needed. See T010.

---

## Subtask T010: Define Provider Classification Constants

**Purpose**: Single source of truth for which providers are SaaS-backed, local, or removed.

**Steps**:

1. Add constants to `src/specify_cli/tracker/config.py` (top of file, after imports):
   ```python
   SAAS_PROVIDERS: frozenset[str] = frozenset({"linear", "jira", "github", "gitlab"})
   LOCAL_PROVIDERS: frozenset[str] = frozenset({"beads", "fp"})
   REMOVED_PROVIDERS: frozenset[str] = frozenset({"azure_devops"})
   ALL_SUPPORTED_PROVIDERS: frozenset[str] = SAAS_PROVIDERS | LOCAL_PROVIDERS
   ```

2. These constants will be imported by:
   - `saas_service.py` (WP03) — to validate provider is SaaS-backed
   - `local_service.py` (WP04) — to validate provider is local
   - `service.py` (WP05) — for façade dispatch
   - `tracker.py` CLI (WP06) — for provider list and help text
   - `factory.py` (WP05) — for supported provider list

**Files**: `src/specify_cli/tracker/config.py` (~5 lines added)

---

## Subtask T011: Write Config Tests

**Purpose**: Verify project_slug serialization roundtrip and provider-aware is_configured logic.

**Steps**:

1. Create `tests/sync/tracker/test_config.py`
2. Write tests:

   a. **project_slug roundtrip**:
   ```python
   def test_project_slug_roundtrip(tmp_path):
       config = TrackerProjectConfig(provider="linear", project_slug="my-proj")
       save_tracker_config(tmp_path, config)
       loaded = load_tracker_config(tmp_path)
       assert loaded.project_slug == "my-proj"
       assert loaded.provider == "linear"
   ```

   b. **workspace roundtrip preserved**:
   ```python
   def test_workspace_roundtrip(tmp_path):
       config = TrackerProjectConfig(provider="beads", workspace="my-ws")
       save_tracker_config(tmp_path, config)
       loaded = load_tracker_config(tmp_path)
       assert loaded.workspace == "my-ws"
   ```

   c. **is_configured for SaaS provider**:
   ```python
   def test_is_configured_saas_needs_project_slug():
       assert TrackerProjectConfig(provider="linear", project_slug="p").is_configured
       assert not TrackerProjectConfig(provider="linear").is_configured
       assert not TrackerProjectConfig(provider="linear", workspace="w").is_configured
   ```

   d. **is_configured for local provider**:
   ```python
   def test_is_configured_local_needs_workspace():
       assert TrackerProjectConfig(provider="beads", workspace="w").is_configured
       assert not TrackerProjectConfig(provider="beads").is_configured
       assert not TrackerProjectConfig(provider="beads", project_slug="p").is_configured
   ```

   e. **Provider constants**:
   ```python
   def test_provider_constants():
       assert "linear" in SAAS_PROVIDERS
       assert "beads" in LOCAL_PROVIDERS
       assert "azure_devops" in REMOVED_PROVIDERS
       assert SAAS_PROVIDERS & LOCAL_PROVIDERS == frozenset()
   ```

**Files**: `tests/sync/tracker/test_config.py` (new, ~80 lines)

---

## Definition of Done

- [ ] `project_slug` field added to `TrackerProjectConfig`
- [ ] `to_dict()` / `from_dict()` serialize and deserialize `project_slug`
- [ ] YAML roundtrip works for both `project_slug` (SaaS) and `workspace` (local)
- [ ] `is_configured` is provider-aware: checks `project_slug` for SaaS, `workspace` for local
- [ ] `SAAS_PROVIDERS`, `LOCAL_PROVIDERS`, `REMOVED_PROVIDERS`, `ALL_SUPPORTED_PROVIDERS` defined
- [ ] Tests cover roundtrip, is_configured, and constant completeness
- [ ] `mypy --strict` passes

## Risks

- **Existing config files**: Projects with existing `tracker:` section in `.kittify/config.yaml` will have `project_slug: null` after loading. This is fine — `is_configured` returns False for unknown providers, and PRI-17 handles migration.

## Reviewer Guidance

- Verify `project_slug` is never used as a storage location for `team_slug` — team_slug comes from auth credential store
- Verify `is_configured` returns False for removed providers (azure_devops)
- Verify constants are exhaustive — no provider is unclassified

## Activity Log

- 2026-03-30T19:25:39Z – orchestrator – shell_pid=46286 – lane=doing – Started implementation via workflow command
- 2026-03-30T19:29:48Z – orchestrator – shell_pid=46286 – lane=for_review – Ready for review: project_slug config field, provider-aware is_configured, classification constants, 29 tests passing
- 2026-03-30T19:30:31Z – codex – shell_pid=47115 – lane=doing – Started review via workflow command
- 2026-03-30T19:32:15Z – codex – shell_pid=47115 – lane=for_review – Fixing lane after confused Codex review
- 2026-03-30T19:32:28Z – codex – shell_pid=47115 – lane=approved – Review passed: project_slug config, provider-aware is_configured, constants, 29 tests. Approved.
- 2026-03-30T19:36:09Z – codex – shell_pid=47115 – lane=planned – Moved to planned
- 2026-03-30T19:38:30Z – codex – shell_pid=47115 – lane=approved – Re-approving WP02 (status reverted during WP01 review). Config changes verified: project_slug, is_configured, constants, 29 tests pass.
