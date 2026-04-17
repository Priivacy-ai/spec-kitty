---
work_package_id: WP06
title: mypy Quarantine Cleanup
dependencies: []
requirement_refs:
- FR-007
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-ownership-consolidation-and-neutrality-hardening-01KPD880
base_commit: 443e4dc7b2f58b49bf9a4b7bfa6862272336c41d
created_at: '2026-04-17T09:28:43.813706+00:00'
subtasks:
- T021
- T022
- T023
phase: Phase 3 — Hygiene
assignee: ''
agent: "claude:opus-4-6:reviewer:reviewer"
shell_pid: "9880"
history:
- timestamp: '2026-04-17T09:03:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: pyproject.toml
execution_mode: code_change
owned_files:
- pyproject.toml
tags: []
---

# Work Package Prompt: WP06 – mypy Quarantine Cleanup

## Objective

Remove the stale `specify_cli.charter.context` entry from the `[[tool.mypy.overrides]]` "Transitional quarantine" block in `pyproject.toml`. The entry names a submodule that never existed at that path — the canonical module is `charter.context`. Gate the cleanup on a passing `mypy --strict` run against the canonical file (R-008).

## Context

Research note R-002 identified that `pyproject.toml` ships a "Transitional quarantine" block with an entry for `specify_cli.charter.context` that disables strict checks. Because that module never existed, the entry is dead configuration. Removing it (a) tidies the config, (b) removes a misleading signal that `specify_cli.charter.context` is a real surface, and (c) restores strict checking coverage for the canonical `charter.context` file (NFR-003).

Research note R-008 warned that if `charter/context.py` has latent strict-mode errors, removing the quarantine will surface them. The sequencing below addresses this: run the strict check FIRST, fix or re-scope, THEN remove the line.

## Branch Strategy

Planning base branch is `main`; merge target is `main`. Execution worktree path is resolved by the runtime from `lanes.json`.

## Implementation Sketch

### Subtask T021 — Run `mypy --strict src/charter/context.py` and record diagnostics

From worktree root:

```bash
mypy --strict src/charter/context.py 2>&1 | tee /tmp/mypy-context-strict.txt
```

Expected outcomes:

- **0 errors**: proceed to T023 (remove the quarantine line).
- **≥ 1 error**: proceed to T022 (fix or re-scope).

Record the raw diagnostic output in the PR body for reviewer traceability. The file has ~400 LOC and is type-annotated; the most likely strict findings are `Optional`-handling tightening or untyped-decorator complaints.

### Subtask T022 — Fix strict errors, OR rename quarantine entry

If T021 surfaced errors, the choice is:

**Preferred**: fix each strict error in `src/charter/context.py` directly. Small-scope fixes only — do not refactor this file beyond what mypy requires. Typical fixes:

- Add explicit `Optional[...]` annotations where `None` defaults are used.
- Add `-> None` to procedures.
- Narrow `Any` returns from `json.loads` / `yaml.safe_load` with `cast(...)`.

**Fallback**: if strict fixes are larger than a focused one-WP edit can absorb, **rename** the quarantine entry from `specify_cli.charter.context` to `charter.context`, with a `TODO(charter-strict-cleanup)` comment and a GitHub issue filed for follow-up. Do NOT leave the stale `specify_cli.charter.context` name in place — that keeps the dead-config problem alive.

**NEVER** expand the quarantine block beyond the single renamed entry. This WP shrinks the quarantine; it does not add new entries.

### Subtask T023 — Remove the stale line and verify

If T021/T022 confirms `charter.context` is clean under `--strict`:

1. Open `pyproject.toml`. Locate the `[[tool.mypy.overrides]]` block labeled "Transitional quarantine" (line ~238 per baseline audit).
2. Remove the specific entry for `specify_cli.charter.context`.
3. If that entry was the last one in the block, remove the entire `[[tool.mypy.overrides]]` table. Otherwise leave the block intact with its remaining entries.

Verify:

```bash
# pyproject.toml parses
python -c "import tomllib; tomllib.loads(open('pyproject.toml').read())"

# mypy config still valid
mypy --no-incremental --help > /dev/null

# strict check still passes on the canonical file
mypy --strict src/charter/context.py

# full project mypy still passes
mypy src/
```

All four commands must succeed.

Commit message should name the removed module path explicitly so a reviewer can verify scope from the log alone: e.g., `chore(mypy): remove stale specify_cli.charter.context quarantine entry`.

## Files

- **Edited**: `pyproject.toml` (1–3 line deletion in the quarantine block).

## Definition of Done

- [ ] `mypy --strict src/charter/context.py` returns zero errors.
- [ ] `pyproject.toml` no longer contains an override entry naming `specify_cli.charter.context`.
- [ ] `pyproject.toml` parses cleanly under `tomllib.loads`.
- [ ] `mypy src/` (the project-default run) continues to pass.
- [ ] The PR body records the T021 `mypy --strict` diagnostic (or "clean baseline — 0 errors").
- [ ] No new entries added to the quarantine block in this WP.

## Risks

- **Hidden strict errors**: the quarantine existed for a reason at some point; the canonical file may not be strict-clean. T021 surfaces this early. Mitigation: prefer small direct fixes; fallback is the rename-with-TODO path.
- **Accidental block removal**: deleting the whole `[[tool.mypy.overrides]]` table when other entries remain would silently drop their overrides. Mitigation: inspect the block first; remove only the specific entry unless it's the sole entry.
- **CI flake on unrelated strict errors**: `mypy src/` may surface pre-existing errors unrelated to this file. Those are out of scope; document them but do not fix them here. If project-level mypy was already red before this WP, the success gate is "no new errors introduced."
- **Tooling drift**: if the project uses a pinned mypy version and a newer version changes strict semantics, the check might disagree between local and CI. Use the version specified in `pyproject.toml` or CI config explicitly.

## Reviewer Checklist

- [ ] The removed line names exactly `specify_cli.charter.context`, not a broader pattern.
- [ ] No new quarantine entries were introduced.
- [ ] `pyproject.toml` still parses (reviewer can run `python -c "import tomllib; tomllib.loads(open('pyproject.toml').read())"` locally).
- [ ] The PR body includes the `mypy --strict src/charter/context.py` output or records that it was clean.
- [ ] If the fallback path was chosen (rename to `charter.context`), a follow-up GitHub issue is linked.

## Activity Log

- 2026-04-17T09:28:44Z – claude:sonnet-4-6:implementer:implementer – shell_pid=7815 – Assigned agent via action command
- 2026-04-17T09:36:09Z – claude:sonnet-4-6:implementer:implementer – shell_pid=7815 – Ready: stale quarantine removed; strict mypy clean on charter.context (5 context.py errors fixed with minimal-scope type annotations)
- 2026-04-17T09:39:53Z – claude:opus-4-6:reviewer:reviewer – shell_pid=9880 – Started review via action command
- 2026-04-17T09:41:29Z – claude:opus-4-6:reviewer:reviewer – shell_pid=9880 – Review passed: stale specify_cli.charter.context quarantine removed; context.py has 0 strict errors; no new quarantine entries; mypy src/ improved from 95 to 89 errors (no new errors introduced)
