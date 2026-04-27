---
work_package_id: WP08
title: Synthesizer CLI Surface
dependencies:
- WP07
requirement_refs:
- FR-021
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
- T039
- T040
- T041
history:
- at: '2026-04-27T08:18:00Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
mission_slug: mission-retrospective-learning-loop-01KQ6YEG
owned_files:
- src/specify_cli/cli/commands/agent_retrospect.py
- tests/cli/test_agent_retrospect_synthesize.py
priority: P2
status: planned
tags: []
---

# WP08 — Synthesizer CLI Surface

## Objective

Wire `spec-kitty agent retrospect synthesize` (Q3-C) per [`../contracts/cli_surfaces.md`](../contracts/cli_surfaces.md). The default is `--dry-run`; `--apply` is the explicit opt-in to mutation (FR-021).

## Spec coverage

- **FR-021** synthesizer runs as an explicit operator/agent action.
- Supporting cover for **FR-019**, **FR-020**, **FR-022**, **FR-023** (driven through the CLI).

## Context

Source-of-truth contract is in [`../contracts/cli_surfaces.md`](../contracts/cli_surfaces.md). The new command goes under the existing `spec-kitty agent` typer namespace. Mission handle resolution uses the standard handle resolver (`mission_id` / `mid8` / `mission_slug`); ambiguous handles produce structured `MISSION_AMBIGUOUS_SELECTOR` errors.

## Subtasks

### T037 — `cli/commands/agent_retrospect.py` synthesize subcommand

Create the typer subcommand. Look at an existing `agent` subcommand for the registration pattern (e.g., `src/specify_cli/cli/commands/agent/...`); mirror it.

```python
@app.command("synthesize")
def synthesize_cmd(
    mission: Annotated[str, typer.Option("--mission", help="Mission handle")],
    apply: Annotated[bool, typer.Option("--apply", help="Apply changes (default is dry-run)")] = False,
    proposal_id: Annotated[list[str] | None, typer.Option("--proposal-id")] = None,
    json_out: Annotated[Path | None, typer.Option("--json-out")] = None,
    json_only: Annotated[bool, typer.Option("--json")] = False,
    actor_id: Annotated[str | None, typer.Option("--actor-id")] = None,
) -> None: ...
```

The function:

1. Resolves the mission handle to a `mission_id` via the existing resolver.
2. Loads the retrospective record from the canonical path. Missing → exit 3.
3. Computes the proposal batch.
4. Calls `apply_proposals(..., dry_run=not apply)`.
5. Renders Rich + (optionally) JSON.
6. Returns the appropriate exit code.

### T038 — Flag parsing

Per `cli_surfaces.md`:

| Flag | Default | Behavior |
|---|---|---|
| `--mission HANDLE` | required | Mission handle |
| `--dry-run` | implicit (default) | Plan + checks; no mutation |
| `--apply` | False | Execute application |
| `--proposal-id ID` | repeatable | Restrict batch |
| `--json` | False | Stdout JSON only |
| `--json-out PATH` | None | Also write JSON to file |
| `--actor-id ID` | None | Override provenance actor |

Mutual exclusion: `--apply` and `--dry-run` are not both flags; `--apply` flips the default off.

### T039 — Exit codes

Per contract:

| Exit | Meaning |
|---|---|
| 0 | Dry-run complete; OR apply succeeded with no conflicts/rejections |
| 1 | Mission handle unresolvable |
| 2 | I/O error reading retrospective |
| 3 | Retrospective record malformed |
| 4 | Apply attempted; conflicts present; nothing applied |
| 5 | Apply attempted; staleness/invalid-payload rejections; nothing applied |

Implement these explicitly via `typer.Exit(code=N)` or equivalent.

### T040 — Rich + JSON output renderers (informational equivalence)

Rich rendering: a clean table of planned applications, conflicts, and rejections; with `--apply`, an "Applied" section summarizing each successful change with the artifact path.

JSON envelope per contract:

```json
{
  "schema_version": "1",
  "command": "agent.retrospect.synthesize",
  "generated_at": "2026-04-27T11:35:00+00:00",
  "dry_run": true,
  "result": { ... }  // SynthesisResult.model_dump()
}
```

The Rich rendering and JSON `result` MUST be informationally equivalent (CHK034). Tests assert this via a small comparison helper.

### T041 — Tests

In `tests/cli/test_agent_retrospect_synthesize.py`:

- Resolves a valid mission handle → exit 0 (dry-run on a fixture record).
- Ambiguous handle → exit 1 with structured error message.
- Missing record → exit 3.
- Conflict batch with `--apply` → exit 4.
- Stale evidence with `--apply` → exit 5.
- `--json` output schema matches expected structure.
- Rich and JSON outputs informationally equivalent (count + key fields match).

Use `typer.testing.CliRunner` against the agent-retrospect typer app.

## Definition of Done

- [ ] Default behavior is `--dry-run`; `--apply` is explicit.
- [ ] All exit codes match the contract.
- [ ] JSON envelope matches the schema; Rich and JSON are informationally equivalent.
- [ ] Tests cover every exit code path.
- [ ] `mypy --strict` passes.
- [ ] Coverage ≥ 90%.
- [ ] No changes outside `owned_files` (typer-app registration may require a one-line edit in the parent `agent/__init__.py` — note this if it occurs and confirm with reviewer).

## Risks

- **Typer subcommand registration**: needs a small edit in the parent `agent/` typer app. Keep that edit minimal and explicit.
- **Mission handle resolution**: reuse existing resolver; do not duplicate.

## Reviewer guidance

- Run `spec-kitty agent retrospect synthesize --help` and verify the contract help text.
- Walk every exit code with a fixture record.
- Confirm `--apply` truly mutates only when asked.

## Implementation command

```bash
spec-kitty agent action implement WP08 --agent <name>
```
