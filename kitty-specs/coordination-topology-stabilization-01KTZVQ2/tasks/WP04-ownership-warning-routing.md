---
work_package_id: WP04
title: Ownership Warning Routing
dependencies: []
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "14316"
history:
- date: '2026-06-12'
  author: spec-kitty.tasks
  note: Initial generation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- src/doctrine/missions/mission-steps/software-dev/tasks-finalize/prompt.md
- tests/specify_cli/test_finalize_ownership_routing.py
priority: P2-High
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Make ownership warnings in `validate_glob_matches` visible and actionable:
- Literal-path zero-match → **hard error** (exit 1 + nearest-match suggestion)
- Glob-pattern zero-match → **warning** routed to stderr (existing soft behavior, now visible)
- `create_intent: true` WP frontmatter annotation → suppress zero-match error for planned-new-file paths
- Re-validate ownership at lane-compute time (downstream boundary guard)
- Update the `tasks-finalize` source template to require agents to act on warnings

---

## Context

### The Bug (Issue #1888)

`validate_glob_matches` at `cli/commands/agent/tasks.py:267–295` returns `ownership_warnings` as a field in the JSON response body. No CLI surface reads this field, no prompt instructs agents to look for it, and human-readable output doesn't show it. In mission-131, a phantom literal path entered `lanes.json` unchallenged because the warning was silently dropped.

### Classification Rule

```python
import glob

def is_glob_pattern(path: str) -> bool:
    return any(c in path for c in ("*", "?", "[", "{"))
```

- Literal path (`src/foo/bar.py`) + zero matches → **hard error**
- Glob pattern (`src/foo/*.py`) + zero matches → **warning** (may be in-flight work)
- `create_intent: true` in WP frontmatter for that path → suppress zero-match error

### `create_intent` Annotation

Add optional support for this frontmatter field on WP files:
```yaml
owned_files:
  - "src/specify_cli/new_module.py"
create_intent:
  - "src/specify_cli/new_module.py"  # planned but not yet created
```

When a path appears in both `owned_files` and `create_intent`, a zero-match is expected and does not trigger a hard error.

---

## Subtasks

### T015 — Classify literal vs glob entries in `validate_glob_matches`

1. Read `src/specify_cli/cli/commands/agent/tasks.py` lines 255–310.
2. Add `is_glob_pattern(path: str) -> bool` helper.
3. For each entry in `owned_files`, classify as literal or glob before checking matches.
4. Store classification in the result object or as a parallel list for use in T016/T018.

### T016 — Promote literal-path zero-match to hard error with nearest-match suggestion

1. In `validate_glob_matches`, after classifying entries:
   - If a literal path matches zero files AND is not in `create_intent` → collect as a hard error.
2. Compute a nearest-match suggestion using `difflib.get_close_matches(path, all_tracked_files, n=3)` (using `git ls-files` output).
3. Format the error:
   ```
   Error: owned_files literal path has no match: 'src/foo/bar.py'
   Did you mean one of: src/foo/bar_util.py, src/foo/bar_old.py?
   Add 'create_intent: [src/foo/bar.py]' to suppress this error for planned-new files.
   ```
4. Return exit 1 (or raise a structured error) when any hard error is collected.

### T017 — Add `create_intent: true` annotation support

1. Add parsing of the `create_intent` list from WP YAML frontmatter in the WP loader.
2. Pass the `create_intent` list to `validate_glob_matches`.
3. In `validate_glob_matches`, suppress zero-match hard error when the literal path appears in `create_intent`.
4. Still emit an info-level note: "Path 'src/foo/bar.py' has no match — suppressed by create_intent."

### T018 — Route `ownership_warnings` to stderr in JSON mode and human-readable output

1. In the `finalize_tasks` CLI command handler, after calling `validate_glob_matches`:
   - If `ownership_warnings` is non-empty, print each to stderr with a `WARNING:` prefix.
   - In JSON mode: include `ownership_warnings` in the JSON body AND print to stderr.
2. In human-readable mode: use `rich.console.Console(stderr=True)` for the warnings.
3. Confirm warnings are visible whether or not the command succeeds.

### T019 — Re-validate ownership at lane-compute time

1. Find where `lanes.json` is written (in `finalize_tasks` or a lane-compute helper).
2. Before writing `lanes.json`, re-run `validate_glob_matches` for all WPs.
3. If any hard error exists, abort lane compute with exit 1 and the error message.
4. This prevents a phantom literal path entering `lanes.json` even if the initial check was bypassed.

### T020 — Update `tasks-finalize` source prompt to require acting on warnings

**IMPORTANT**: Edit the SOURCE file, not the agent copy.

1. Read `src/doctrine/missions/mission-steps/software-dev/tasks-finalize/prompt.md`.
2. Add a section that instructs implementing agents:
   - Check `ownership_warnings` in the JSON output of `finalize-tasks`.
   - For each warning: fix the path or add `create_intent` annotation before proceeding.
   - Do NOT proceed to implement if any hard error is present.
3. The agent copies will be regenerated via `spec-kitty upgrade` — do not edit `.claude/commands/` or other generated copies.

---

## Branch Strategy

**Planning base**: `main` | **Merge target**: `main`

```bash
spec-kitty agent action implement WP04 --agent <name>
```

---

## Definition of Done

- [ ] `validate_glob_matches` classifies literal vs glob entries
- [ ] Literal-path zero-match is a hard error with nearest-match suggestion
- [ ] `create_intent` annotation suppresses hard error for planned-new-file paths
- [ ] `ownership_warnings` routed to stderr in both JSON and human modes
- [ ] Re-validation at lane-compute time blocks phantom paths from `lanes.json`
- [ ] `tasks-finalize/prompt.md` SOURCE updated (not agent copies)
- [ ] `test_finalize_ownership_routing.py` passes
- [ ] `mypy --strict` zero issues
- [ ] `ruff check .` zero issues

## Risks

- **Template propagation**: The `prompt.md` change won't propagate to agent copies until `spec-kitty upgrade` is run. Note this in the PR description.
- **`difflib.get_close_matches` performance**: `git ls-files` on large repos may be slow. Cache the output or limit to `kitty-specs/` paths.
- **`create_intent` frontmatter**: Adding a new frontmatter key requires updating the WP YAML schema if one exists — check `src/specify_cli/tasks/` or `finalize_tasks` for schema validation code.

## Activity Log

- 2026-06-13T07:59:22Z – claude:sonnet-4-6:implementer:implementer – shell_pid=55522 – Assigned agent via action command
- 2026-06-13T08:12:08Z – claude:sonnet-4-6:implementer:implementer – shell_pid=55522 – Ready for review: ownership warning routing implemented
- 2026-06-13T08:12:37Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=14316 – Started review via action command
- 2026-06-13T08:17:15Z – user – shell_pid=14316 – Review passed: GlobValidationResult API consistent, literal errors abort, ghost suppression via create_intent works
