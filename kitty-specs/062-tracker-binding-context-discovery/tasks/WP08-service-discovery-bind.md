---
work_package_id: WP08
title: Service Layer – Discovery & Bind
dependencies: []
requirement_refs:
- FR-003
- FR-007
- FR-008
- FR-015
- FR-016
- FR-020
- FR-021
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 30f1ff022d873a60c54903313878094bb01ce2a7
created_at: '2026-04-04T11:11:32.676135+00:00'
subtasks: [T036, T037, T038, T039, T040, T041]
shell_pid: "10022"
agent: "codex"
history:
- date: '2026-04-04T09:10:15Z'
  action: created
  by: spec-kitty.tasks
authoritative_surface: tests/sync/tracker/
execution_mode: code_change
owned_files: [tests/sync/tracker/test_saas_service_discovery.py]
---

# WP08: Service Layer – Discovery & Bind

## Objective

Add new service methods: `discover()` for resource inventory and `resolve_and_bind()` for the full discovery-selection-confirmation flow. Handle exact match, candidates, none, and candidate token retry.

## Context

- **Spec**: FR-001 (discover), FR-003 (bind with discovery), FR-007 (no candidates), FR-008 (re-bind), FR-016 (bind confirm)
- **Plan**: Discovery Bind Flow diagram in plan.md
- **Data Model**: ResolutionResult, BindCandidate, BindResult entities
- **Contracts**: bind-resolve.md, bind-confirm.md
- **Depends on**: WP02 (discovery types), WP04 (client methods), WP07 (routing infrastructure)

## Implementation Command

```bash
spec-kitty implement WP08 --base WP07
```

## Subtasks

### T036: Add discover() Method

**Purpose**: Resource inventory — calls client, parses into typed dataclasses.

**Steps**:
1. Add to `SaaSTrackerService`:
   ```python
   def discover(self, provider: str) -> list[BindableResource]:
       """List all bindable resources for the given provider."""
       result = self._client.resources(provider)
       return [BindableResource.from_api(r) for r in result.get("resources", [])]
   ```
2. Import `BindableResource` from `specify_cli.tracker.discovery`

**Files**: `src/specify_cli/tracker/saas_service.py`

### T037: Add resolve_and_bind() Orchestrator

**Purpose**: Full bind flow: resolve identity → evaluate → confirm → persist.

**Steps**:
1. Add method signature:
   ```python
   def resolve_and_bind(
       self,
       *,
       provider: str,
       project_identity: dict[str, Any],
       select_n: int | None = None,
       bind_ref: str | None = None,
   ) -> BindResult | ResolutionResult:
       """Orchestrate the discovery-bind flow.
       
       Returns BindResult on success (auto-bind or confirmed selection).
       Returns ResolutionResult with candidates if user selection needed.
       Raises TrackerServiceError on no-match or validation failure.
       """
   ```
2. Implement the flow based on plan.md Discovery Bind Flow diagram

**Files**: `src/specify_cli/tracker/saas_service.py`

### T038: Exact Match Handling

**Purpose**: Auto-bind when resolution returns exact match.

**Steps**:
1. Inside `resolve_and_bind()`:
   ```python
   resolution = ResolutionResult.from_api(
       self._client.bind_resolve(provider, project_identity)
   )
   
   if resolution.match_type == "exact":
       if resolution.binding_ref:
           # Existing mapping — persist directly
           self._persist_binding(provider, resolution.binding_ref,
                                 resolution.display_label, None)
           return BindResult(binding_ref=resolution.binding_ref, ...)
       else:
           # Need to confirm
           return self._confirm_and_persist(
               provider, resolution.candidate_token, project_identity
           )
   ```
2. Add `_persist_binding()` helper to write config:
   ```python
   def _persist_binding(self, provider, binding_ref, display_label, provider_context):
       self._config = TrackerProjectConfig(
           provider=provider,
           binding_ref=binding_ref,
           project_slug=self._config.project_slug,  # preserve legacy
           display_label=display_label,
           provider_context=provider_context,
       )
       save_tracker_config(self._repo_root, self._config)
   ```
3. Add `_confirm_and_persist()` helper:
   ```python
   def _confirm_and_persist(self, provider, candidate_token, project_identity):
       result = BindResult.from_api(
           self._client.bind_confirm(provider, candidate_token, project_identity)
       )
       self._persist_binding(provider, result.binding_ref, result.display_label,
                             result.provider_context)
       return result
   ```

**Files**: `src/specify_cli/tracker/saas_service.py`

### T039: Candidates Handling

**Purpose**: Return candidates to caller for interactive selection.

**Steps**:
1. Inside `resolve_and_bind()`:
   ```python
   if resolution.match_type == "candidates":
       if select_n is not None:
           candidate = find_candidate_by_position(resolution.candidates, select_n)
           if candidate is None:
               raise TrackerServiceError(
                   f"Selection {select_n} is out of range. "
                   f"Valid range: 1-{len(resolution.candidates)}."
               )
           return self._confirm_and_persist(
               provider, candidate.candidate_token, project_identity
           )
       # Return resolution for CLI to handle interactive selection
       return resolution
   ```
2. For `match_type == "none"`:
   ```python
   if resolution.match_type == "none":
       raise TrackerServiceError(
           f"No bindable resources found for provider '{provider}'. "
           "Verify the tracker is connected in the SaaS dashboard."
       )
   ```

**Files**: `src/specify_cli/tracker/saas_service.py`

### T040: Candidate Token Retry

**Purpose**: If bind_confirm rejects the token, retry discovery once.

**Steps**:
1. In `_confirm_and_persist()`, catch token rejection:
   ```python
   def _confirm_and_persist(self, provider, candidate_token, project_identity):
       try:
           result = BindResult.from_api(
               self._client.bind_confirm(provider, candidate_token, project_identity)
           )
       except SaaSTrackerClientError as e:
           if e.error_code == "invalid_candidate_token":
               raise TrackerServiceError(
                   "Candidate token expired. Please retry the bind operation."
               ) from e
           raise
       self._persist_binding(...)
       return result
   ```
2. The CLI layer handles the retry by re-running the discovery flow. The service raises a clear error.

**Files**: `src/specify_cli/tracker/saas_service.py`

### T041: Write Service Tests

**Purpose**: Test discover, resolve, and bind flows.

**Steps**:
1. Add to `tests/sync/tracker/test_saas_service.py`:
   - `test_discover_parses_resources`: mock client.resources → verify list[BindableResource]
   - `test_discover_empty`: mock empty resources → verify empty list
   - `test_resolve_and_bind_exact_with_ref`: mock exact match with binding_ref → BindResult, config saved
   - `test_resolve_and_bind_exact_without_ref`: mock exact match, null binding_ref → calls bind_confirm
   - `test_resolve_and_bind_candidates_returns_resolution`: mock candidates → ResolutionResult returned
   - `test_resolve_and_bind_select_n`: mock candidates + select_n=2 → auto-selects, BindResult
   - `test_resolve_and_bind_select_out_of_range`: mock candidates + select_n=99 → TrackerServiceError
   - `test_resolve_and_bind_none`: mock none → TrackerServiceError
   - `test_confirm_token_rejected`: mock bind_confirm raises invalid_candidate_token → TrackerServiceError

**Files**: `tests/sync/tracker/test_saas_service.py`

## Definition of Done

- [ ] `discover()` returns `list[BindableResource]` from client.resources()
- [ ] `resolve_and_bind()` handles exact (with/without ref), candidates, none
- [ ] `select_n` auto-selects from candidates by sort_position
- [ ] Config persisted with binding_ref + display metadata after successful bind
- [ ] Token rejection raises clear error for CLI retry
- [ ] All tests pass: `python -m pytest tests/sync/tracker/test_saas_service.py -x -q`
- [ ] `ruff check src/specify_cli/tracker/saas_service.py`

## Reviewer Guidance

- Verify `_persist_binding` preserves existing `project_slug` (backward compat)
- Verify `select_n` maps 1-based to sort_position correctly
- Check that none match error message does NOT suggest typing raw metadata

## Activity Log

- 2026-04-04T11:11:33Z – coordinator – shell_pid=271 – Started implementation via workflow command
- 2026-04-04T11:16:33Z – coordinator – shell_pid=271 – Ready for review: discover(), resolve_and_bind() with exact/candidates/none handling, token retry, 13 new tests all passing
- 2026-04-04T11:17:07Z – codex – shell_pid=10022 – Started review via workflow command
