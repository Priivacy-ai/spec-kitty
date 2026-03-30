---
work_package_id: WP06
title: CLI Command Updates
dependencies: []
requirement_refs:
- FR-001
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-013
- FR-024
- FR-025
- FR-026
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 7acde442e94db133fd61ed13584feee8ba58ecc9
created_at: '2026-03-30T20:02:39.142045+00:00'
subtasks: [T028, T029, T030, T031, T032, T033, T034]
shell_pid: "52369"
agent: "orchestrator"
history:
- at: '2026-03-30T19:14:19+00:00'
  event: created
  actor: planner
authoritative_surface: src/specify_cli/cli/commands/tracker.py
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/cli/commands/tracker.py
- tests/agent/cli/commands/test_tracker.py
---

# WP06: CLI Command Updates

## Objective

Update all tracker CLI commands in `src/specify_cli/cli/commands/tracker.py` to work with the refactored service façade. Add `--project-slug` for SaaS-backed bind. Implement hard-break guidance for legacy operations. Update help text to distinguish SaaS-backed vs local behavior. Ensure JSON output reflects SaaS envelope structures.

## Context

- The `TrackerService` façade (WP05) dispatches to SaaS or local backends.
- The CLI layer's job is: parse arguments, call service methods, format output.
- Hard-break guidance must be deterministic and contract-aligned (see FR-010, FR-008, FR-009).
- The feature flag `SPEC_KITTY_ENABLE_SAAS_SYNC` remains the gate for all tracker commands.

## Implementation Command

```bash
spec-kitty implement WP06 --base WP05
```

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Depends on WP05 (façade). Branch from WP05.

---

## Subtask T028: Update bind Command

**Purpose**: Support two binding modes — SaaS-backed (project_slug) and local (workspace + credentials).

**Steps**:

1. Open `src/specify_cli/cli/commands/tracker.py`, find `bind_command()`
2. Add `--project-slug` option (new):
   ```python
   project_slug: Annotated[str | None, typer.Option("--project-slug", help="SaaS project identifier for tracker routing")] = None,
   ```
3. Keep existing `--workspace`, `--provider`, `--doctrine-mode`, `--field-owner` options
4. Add validation logic at top of command:
   ```python
   from specify_cli.tracker.config import SAAS_PROVIDERS, REMOVED_PROVIDERS

   provider_normalized = normalize_provider(provider)

   if provider_normalized in REMOVED_PROVIDERS:
       # FR-013: Hard-fail for Azure DevOps
       console.print("[red]Error:[/] Provider 'azure_devops' is no longer supported.")
       raise typer.Exit(code=1)

   if provider_normalized in SAAS_PROVIDERS:
       # FR-010: Hard-fail --credential for SaaS providers
       if credential:
           console.print(
               "[red]Error:[/] Provider credentials are not accepted for SaaS-backed providers.\n"
               "SaaS-backed providers authenticate through Spec Kitty SaaS.\n"
               "If you haven't already, run [bold]spec-kitty auth login[/bold] to authenticate.\n"
               "Then connect your provider in the Spec Kitty dashboard."
           )
           raise typer.Exit(code=1)

       if not project_slug:
           console.print("[red]Error:[/] --project-slug is required for SaaS-backed providers.")
           raise typer.Exit(code=1)

       # FR-001: SaaS bind stores provider + project_slug only
       service.bind(provider=provider_normalized, project_slug=project_slug)
   else:
       # Local provider — existing bind path
       service.bind(
           provider=provider_normalized, workspace=workspace,
           doctrine_mode=doctrine_mode, doctrine_field_owners=...,
           credentials=parse_kv_pairs(credential),
       )
   ```

5. Update help text to mention both modes

**Files**: `src/specify_cli/cli/commands/tracker.py` (~50 lines changed)

**Hard-break guidance for --credential** (FR-010): The error message must:
- Not assume the user is unauthenticated
- Direct them to authenticate AND connect the provider in the SaaS dashboard
- Mention both `spec-kitty auth login` and the dashboard

---

## Subtask T029: Update unbind/status Commands

**Purpose**: These commands dispatch through the façade and display appropriate output.

**Steps**:

1. **unbind**: No changes needed — the façade handles dispatch. The command just calls `service.unbind()`.

2. **status** (FR-006): Update output display for SaaS-backed providers:
   - The SaaS status response has a different structure than local status
   - Format the response using rich console:
     ```python
     result = service.status()
     # For SaaS-backed: display identity_path, sync state, provider info
     # For local: display existing local status format
     ```
   - Use `--json` flag to output raw dict when requested

**Files**: `src/specify_cli/cli/commands/tracker.py` (~30 lines changed)

---

## Subtask T030: Update sync pull/push/run Commands

**Purpose**: Display SaaS envelope results for SaaS-backed providers.

**Steps**:

1. **sync pull** (FR-002):
   - Call `service.sync_pull(limit=limit)`
   - For SaaS-backed: response is a `PullResultEnvelope` dict
   - Display: `status`, `summary.total/succeeded/failed/skipped`, item count
   - Show `identity_path.type` and `identity_path.provider` for transparency
   - Handle pagination info (`has_more`, `next_cursor`)

2. **sync push** (FR-003):
   - Call `service.sync_push()`
   - For SaaS-backed: response is `PushResultEnvelope` dict
   - Display: `status`, `summary`, per-item outcomes (created/updated/transitioned)
   - Note: The service/client handles 200 vs 202 internally — the CLI sees the final result

3. **sync run** (FR-004):
   - Call `service.sync_run(limit=limit)`
   - For SaaS-backed: response is `RunResultEnvelope` dict
   - Display: `status`, `summary`, pull phase results, push phase results

4. For all three:
   - `--json` flag: output raw response dict
   - Non-JSON: use rich tables/panels for formatted output
   - On error: the service raises `TrackerServiceError` with the error envelope message — let the existing CLI error handler display it

**Files**: `src/specify_cli/cli/commands/tracker.py` (~60 lines changed)

---

## Subtask T031: Update sync publish + map add/list

**Purpose**: Hard-fail sync publish and map add for SaaS-backed providers.

**Steps**:

1. **sync publish** (FR-009):
   - The service's `sync_publish()` already hard-fails for SaaS-backed providers (via SaaSTrackerService)
   - The CLI just needs to call `service.sync_publish(...)` and let the error propagate
   - For local providers: sync_publish was never a thing — the LocalTrackerService can also hard-fail or raise NotImplementedError
   - Consider removing the `sync publish` command entirely since it serves no purpose post-migration
   - If keeping: simplify to just call through façade (which will fail for SaaS)

2. **map add** (FR-008):
   - The service's `map_add()` already hard-fails for SaaS-backed
   - CLI calls through, error propagates
   - For local: existing behavior preserved

3. **map list** (FR-007):
   - CLI calls `service.map_list()`
   - For SaaS-backed: displays SaaS-authoritative mappings from `/api/v1/tracker/mappings`
   - For local: displays local SQLite mappings (existing behavior)
   - Format: table with WP ID, external ID, external key, external URL

**Files**: `src/specify_cli/cli/commands/tracker.py` (~30 lines changed)

---

## Subtask T032: Update providers List + Help Text

**Purpose**: Provider list and help text reflect the new reality.

**Steps**:

1. **providers command** (FR-012):
   - Update to use `TrackerService.supported_providers()` which returns `(beads, fp, github, gitlab, jira, linear)` — sorted, no azure_devops
   - Display with category labels:
     ```
     SaaS-backed: github, gitlab, jira, linear
     Local:       beads, fp
     ```

2. **Help text** (FR-025):
   - Update command-level help strings to mention the SaaS vs local distinction
   - Example for `tracker bind`:
     ```
     Bind a tracker provider to this project.

     For SaaS-backed providers (linear, jira, github, gitlab):
       Requires --provider and --project-slug. Authentication via spec-kitty auth login.

     For local providers (beads, fp):
       Requires --provider, --workspace, and --credential flags.
     ```
   - Update help for `sync pull/push/run` to mention SaaS routing
   - Update help for `map add` to note it's only available for local providers

**Files**: `src/specify_cli/cli/commands/tracker.py` (~40 lines changed)

---

## Subtask T033: Update JSON Output

**Purpose**: `--json` output reflects SaaS envelope structures for SaaS-backed providers (FR-024).

**Steps**:

1. For each command that supports `--json`:
   - SaaS-backed: output the raw SaaS envelope dict (PullResultEnvelope, PushResultEnvelope, etc.)
   - Local: output the existing dict structure
   - The structures will differ by provider type — this is expected and documented

2. For `status --json`:
   - SaaS-backed: output the SaaS status response
   - Local: output the existing local status dict

3. Ensure `typer.echo(json.dumps(result, indent=2, default=str))` is used consistently

**Files**: `src/specify_cli/cli/commands/tracker.py` (~20 lines changed)

---

## Subtask T034: Update test_tracker.py

**Purpose**: Test CLI command paths for both SaaS and local providers.

**Steps**:

1. Open `tests/agent/cli/commands/test_tracker.py`
2. The existing file is small (~77 lines). Expand with:

   a. **SaaS bind test**:
   - Mock TrackerService, invoke `bind --provider linear --project-slug my-proj`
   - Verify service.bind called with provider="linear", project_slug="my-proj"

   b. **SaaS bind --credential hard-fail test**:
   - Invoke `bind --provider linear --project-slug p --credential api_key=xxx`
   - Verify exit code 1, error message mentions SaaS dashboard

   c. **Azure DevOps bind hard-fail test**:
   - Invoke `bind --provider azure_devops --workspace w`
   - Verify exit code 1, error message mentions "no longer supported"

   d. **Local bind test**:
   - Invoke `bind --provider beads --workspace w --credential command=beads`
   - Verify service.bind called with credentials

   e. **sync pull JSON output test**:
   - Mock service.sync_pull to return PullResultEnvelope dict
   - Invoke `sync pull --json`
   - Verify JSON output contains expected envelope fields

   f. **providers list test**:
   - Invoke `providers`
   - Verify output includes linear, jira, github, gitlab, beads, fp
   - Verify azure_devops NOT in output

**Files**: `tests/agent/cli/commands/test_tracker.py` (expand from ~77 to ~200 lines)

---

## Definition of Done

- [ ] `bind` accepts `--project-slug` for SaaS providers, hard-fails `--credential` with dashboard guidance
- [ ] `bind` hard-fails Azure DevOps with "no longer supported" message
- [ ] `unbind`, `status` dispatch through façade correctly
- [ ] `sync pull/push/run` display SaaS envelope results with summary info
- [ ] `sync publish` hard-fails for SaaS providers
- [ ] `map add` hard-fails for SaaS providers; `map list` displays SaaS mappings
- [ ] `providers` list shows 6 providers (no azure_devops), categorized SaaS vs local
- [ ] Help text clearly distinguishes SaaS vs local behavior
- [ ] JSON output (`--json`) returns raw envelope dicts for SaaS-backed operations
- [ ] Feature flag `SPEC_KITTY_ENABLE_SAAS_SYNC` still gates all commands
- [ ] CLI integration tests cover SaaS bind, local bind, hard-fails, JSON output
- [ ] `mypy --strict` passes

## Risks

- **Output format changes**: Existing tools parsing JSON output may break. Since there are zero live users, this is acceptable.
- **Help text verbosity**: Don't over-explain. Keep help text concise with examples.

## Reviewer Guidance

- Verify hard-break messages match the frozen contract guidance (not just "run auth login")
- Verify `--credential` rejection message mentions BOTH `spec-kitty auth login` AND the SaaS dashboard
- Verify JSON output for SaaS operations returns the actual envelope dict, not a wrapper
- Verify feature flag still gates all commands (check `tracker_callback`)
- Test with `--help` flag on each command to verify help text is coherent
- Verify no reference to Azure DevOps in any help text or error message (except the explicit "no longer supported" rejection)

## Activity Log

- 2026-03-30T20:02:39Z – orchestrator – shell_pid=52369 – lane=doing – Started implementation via workflow command
- 2026-03-30T20:06:55Z – orchestrator – shell_pid=52369 – lane=for_review – Ready for review - final WP: CLI command updates with SaaS dispatch, hard-breaks, categorized providers, and JSON envelope output
