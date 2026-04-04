---
work_package_id: WP05
title: Existing Endpoint Evolution
dependencies: []
requirement_refs:
- FR-010
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 1199890fde424c22b3922bc570e62906a9b45522
created_at: '2026-04-04T10:06:50.376838+00:00'
subtasks: [T020, T021, T022, T023]
shell_pid: "14857"
agent: "coordinator"
history:
- date: '2026-04-04T09:10:15Z'
  action: created
  by: spec-kitty.tasks
authoritative_surface: tests/sync/tracker/
execution_mode: code_change
owned_files: [tests/sync/tracker/test_saas_client_routing.py]
---

# WP05: Existing Endpoint Evolution

## Objective

Update all 5 existing `SaaSTrackerClient` methods (`status`, `mappings`, `pull`, `push`, `run`) to accept optional `binding_ref` alongside `project_slug`. When `binding_ref` is provided, it is sent as the routing key instead of `project_slug`.

## Context

- **Spec**: FR-010 (binding_ref first, project_slug fallback), FR-013 (status uses binding_ref)
- **Plan**: Existing Endpoint Wire Evolution section in plan.md
- **Contract**: contracts/existing-endpoint-evolution.md
- **Current code**: `src/specify_cli/tracker/saas_client.py` — `status()` (line ~297), `mappings()` (line ~307), `pull()` (line ~273), `push()` (line ~388), `run()` (line ~421)

All 5 methods currently take `project_slug` as a required positional parameter. This WP makes it optional and adds `binding_ref` as a keyword-only alternative.

## Implementation Command

```bash
spec-kitty implement WP05 --base WP03
```

Depends on WP03 (enriched errors, same file). Cannot run in parallel with WP04 (both modify saas_client.py) — coordinate via --base.

## Subtasks

### T020: Update GET Method Signatures (status, mappings)

**Purpose**: Make project_slug optional, add binding_ref kwarg for GET endpoints.

**Steps**:
1. Update `status()`:
   ```python
   def status(
       self,
       provider: str,
       project_slug: str | None = None,
       *,
       binding_ref: str | None = None,
   ) -> dict[str, Any]:
   ```
2. Update `mappings()` with the same signature pattern
3. Update the params dict construction:
   ```python
   params: dict[str, str] = {"provider": provider}
   if binding_ref:
       params["binding_ref"] = binding_ref
   elif project_slug:
       params["project_slug"] = project_slug
   ```

**Files**: `src/specify_cli/tracker/saas_client.py`

### T021: Update POST Method Signatures (pull, push, run)

**Purpose**: Same pattern for POST endpoints.

**Steps**:
1. Update `pull()`, `push()`, `run()` signatures: `project_slug: str | None = None, *, binding_ref: str | None = None`
2. Update payload construction:
   ```python
   payload: dict[str, Any] = {"provider": provider}
   if binding_ref:
       payload["binding_ref"] = binding_ref
   elif project_slug:
       payload["project_slug"] = project_slug
   # ... rest of payload fields
   ```

**Files**: `src/specify_cli/tracker/saas_client.py`

### T022: Update Wire Format Logic

**Purpose**: Ensure binding_ref takes precedence when both are provided.

**Steps**:
1. For each method, the routing key logic is:
   - If `binding_ref` is provided → send `binding_ref` (ignore `project_slug`)
   - If only `project_slug` is provided → send `project_slug`
   - If neither → raise (handled in T023)
2. This is the same conditional for all 5 methods. Consider extracting a helper:
   ```python
   def _routing_params(
       self, provider: str, project_slug: str | None, binding_ref: str | None
   ) -> dict[str, str]:
       params: dict[str, str] = {"provider": provider}
       if binding_ref:
           params["binding_ref"] = binding_ref
       elif project_slug:
           params["project_slug"] = project_slug
       else:
           raise SaaSTrackerClientError(
               "Either project_slug or binding_ref must be provided.",
               error_code="missing_routing_key",
               status_code=None,
           )
       return params
   ```

**Files**: `src/specify_cli/tracker/saas_client.py`

### T023: Add Routing Key Validation

**Purpose**: Error clearly if neither routing key is provided.

**Steps**:
1. If using the `_routing_params` helper from T022, validation is built in
2. Otherwise, add validation at the top of each method:
   ```python
   if not binding_ref and not project_slug:
       raise SaaSTrackerClientError(
           "Either project_slug or binding_ref must be provided.",
           error_code="missing_routing_key",
       )
   ```

**Files**: `src/specify_cli/tracker/saas_client.py`

## Definition of Done

- [ ] All 5 existing methods accept optional `binding_ref` kwarg
- [ ] `project_slug` is no longer required (can be None if `binding_ref` provided)
- [ ] `binding_ref` takes precedence when both are provided
- [ ] Missing both raises `SaaSTrackerClientError` with `error_code="missing_routing_key"`
- [ ] Existing callers passing `project_slug` positionally still work
- [ ] `ruff check src/specify_cli/tracker/saas_client.py`
- [ ] `mypy src/specify_cli/tracker/saas_client.py`

## Risks

- **Breaking existing callers**: `project_slug` changes from required positional to optional positional with default None. Existing callers pass it positionally (`client.status("linear", "my-proj")`) which still works. Keyword callers (`project_slug="my-proj"`) also still work. No breakage.
- **File ownership conflict with WP04**: Both WP04 and WP05 modify `saas_client.py`. Use `--base WP03` for WP05 (or coordinate merge order). WP04 adds new methods, WP05 modifies existing ones — no line conflicts expected.

## Reviewer Guidance

- Verify that existing callers of `status()`, `pull()`, etc. in `saas_service.py` still compile
- Check that the routing key helper (if extracted) is consistent across all 5 methods
- Verify the error message is clear about which keys are expected

## Activity Log

- 2026-04-04T10:06:50Z – coordinator – shell_pid=14857 – Started implementation via workflow command
