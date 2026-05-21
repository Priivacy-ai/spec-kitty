---
work_package_id: WP07
title: Rebuilt CLI reference + agent-subcommands + meta-issue file
dependencies:
- WP06
requirement_refs:
- FR-009
- FR-010
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
agent: "claude:opus-4-7:curator-carla:implementer"
shell_pid: "56291"
history:
- actor: planner
  at: '2026-05-21T06:52:04Z'
  action: wp_authored
  notes: Initial authorship by tasks phase.
agent_profile: curator-carla
authoritative_surface: docs/reference/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- docs/reference/cli-commands.md
- docs/reference/agent-subcommands.md
- docs/development/3-2-cli-reference-audit-meta-issues.md
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load curator-carla
```

## Objective

Regenerate the public 3.2 CLI reference using the WP06 builder, preserve hand-authored prose, and populate the meta-issue file with every CLI/help/docs mismatch surfaced by the audit. **No silent code edits**: any code/help discrepancy lands as a meta-issue row, not a Typer change.

## Context

- Builder: `scripts/docs/build_cli_reference.py --mode hybrid` (from WP06).
- Freshness checker: `scripts/docs/check_cli_reference_freshness.py` (from WP06).
- Methodology: `docs/development/3-2-cli-reference-methodology.md` (from WP05).
- Meta-issue schema: `MetaIssueEntry` shape in [`data-model.md`](../data-model.md).
- Audit findings already captured in [`cli-audit-3-2.md`](../../../cli-audit-3-2.md) §"Stale or Suspicious Documentation References" and §"Code/Help Accuracy Issues To Turn Into Meta Issues" are the seed rows for the meta-issue file.
- C-002 forbids changing Typer code, help text, or `docs/toc.yml` during this mission. C-006 mandates that CLI/help mismatches land in the meta-issue file.

## Subtasks

### T021 — Run builder in hybrid mode

```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
export SPEC_KITTY_NO_UPGRADE_CHECK=1
uv run python scripts/docs/build_cli_reference.py \
  --output docs/reference/cli-commands.md \
  --agent-output docs/reference/agent-subcommands.md \
  --mode hybrid
```

- Review the diff before committing.
- If the builder refuses with `BUILD-TARGET-DIRTY`, the implementer commits or stashes the conflicting edit and re-runs (never `--force` in this WP).

### T022 — Preserve hand-authored prose

- Inspect the existing `docs/reference/cli-commands.md` and `docs/reference/agent-subcommands.md` for prose blocks (preambles, examples, callouts) that should survive regeneration.
- Move any prose that lives **between** generated entries into either:
  - the **outside** of the `<!-- BEGIN/END GENERATED -->` block (preserved across runs), or
  - the meta-issue file if the prose contradicted current behaviour (the prose flagged a known issue).
- Re-run the builder if prose was moved; confirm idempotent output.

### T023 — Author meta-issue file

Create `docs/development/3-2-cli-reference-audit-meta-issues.md` with:

- Header naming the schema (cite `data-model.md` §"MetaIssueEntry").
- A markdown table with the seven required columns: `command_path | source_file | source_function | observed_help | observed_behavior_or_test_evidence | problem_type | recommended_fix | owner_area | blocking_status`.
- Seed rows from `cli-audit-3-2.md`:
  1. `spec-kitty implement` help says "Internal" but the command is top-level visible — `problem_type: confusing`, `blocking_status: blocking`.
  2. `agent context update-context` no longer exists; docs still mention it — `problem_type: stale`, `blocking_status: blocking`.
  3. `agent workflow implement` renamed to `agent action implement`; docs still reference the old form — `problem_type: stale`, `blocking_status: blocking`.
  4. `agent feature` and `agent workflow` legacy aliases — `problem_type: stale`, `blocking_status: non_blocking`.
  5. `mission switch` and `mission-type switch` deprecated but render help — `problem_type: confusing`, `blocking_status: non_blocking`.
  6. `agent profile` hidden parent vs `agent profile list` visible child asymmetry — `problem_type: confusing`, `blocking_status: non_blocking`.
- Any additional rows surfaced by running the builder + freshness check on the live tree at implement time.

### T024 — Confirm freshness checker exits 0

```bash
uv run python scripts/docs/check_cli_reference_freshness.py \
  --reference docs/reference/cli-commands.md \
  --agent-reference docs/reference/agent-subcommands.md \
  --ci
```

- Exit code must be 0.
- Also run the architectural test: `pytest tests/architectural/test_docs_cli_reference_parity.py -v`.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Lane: `B`. Reuses the lane-B worktree.

## Test Strategy

- Acceptance gate: freshness checker exits 0; architectural parity test passes.
- Reviewer gate: meta-issue file has all seed rows with the required columns.

## Definition of Done

- [ ] `docs/reference/cli-commands.md` regenerated; hand-authored prose preserved.
- [ ] `docs/reference/agent-subcommands.md` regenerated.
- [ ] `docs/development/3-2-cli-reference-audit-meta-issues.md` exists with the schema-driven table and all seed rows.
- [ ] `check_cli_reference_freshness.py` exits 0.
- [ ] `test_docs_cli_reference_parity.py` passes.
- [ ] No files outside `owned_files` modified.
- [ ] No Typer code touched.

## Risks

- **Lost hand-authored prose** — Mitigation: review the diff carefully; the `--mode hybrid` contract preserves outside-block prose by design.
- **Meta-issue file becomes a dumping ground for opinions** — Mitigation: every row must have `observed_behavior_or_test_evidence` populated (cite a file/line or a test).

## Reviewer Guidance

- Confirm the diff against the previous reference is plausible (counts match `cli-audit-3-2.md`).
- Confirm no Typer or command code edits in `git diff --stat`.
- Confirm meta-issue rows cite evidence, not opinion.
- Run the freshness checker locally to reproduce exit 0.

## Implement command

```bash
spec-kitty agent action implement WP07 --agent claude
```

## Activity Log

- 2026-05-21T08:02:46Z – claude:opus-4-7:curator-carla:implementer – shell_pid=56291 – Started implementation via action command
