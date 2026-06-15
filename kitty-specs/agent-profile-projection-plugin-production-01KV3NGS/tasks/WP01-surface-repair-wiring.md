---
work_package_id: WP01
title: Surface Repair Wiring into Init/Upgrade
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: feat/agent-profile-projection-plugin-production
merge_target_branch: feat/agent-profile-projection-plugin-production
branch_strategy: Planning artifacts for this mission were generated on feat/agent-profile-projection-plugin-production. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/agent-profile-projection-plugin-production unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-agent-profile-projection-plugin-production-01KV3NGS-01KV3NGS
base_commit: unknown
created_at: '2026-06-14T19:56:22.442627+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: claude
shell_pid: '46315'
history:
- at: '2026-06-14T00:00:00Z'
  event: created
  actor: claude
agent_profile: engineer
authoritative_surface: src/specify_cli/tool_surface/
create_intent:
- src/specify_cli/tool_surface/drift_policy.py
- src/specify_cli/upgrade/migrations/m_0_9_3_surface_repair_wiring.py
- tests/specify_cli/tool_surface/test_repair_wiring_unit.py
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/repair.py
- src/specify_cli/tool_surface/drift_policy.py
- src/specify_cli/cli/commands/init.py
- src/specify_cli/upgrade/runner.py
- src/specify_cli/upgrade/migrations/m_0_9_3_surface_repair_wiring.py
- tests/specify_cli/tool_surface/test_repair_wiring_unit.py
role: Senior Python Engineer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading any other section of this prompt, load your agent profile:

```
/ad-hoc-profile-load engineer
```

This loads governance context, tool preferences, and behavioral directives for this work package. Do not skip this step.

---

## Objective

Wire `SurfaceRepairService` into `spec-kitty init` and `spec-kitty upgrade` so that after every agent configuration write, the tool-surface repair registry runs automatically. Implement the 6-rule drift policy (auto-create missing, auto-repair stale, prompt-on-drift, report-only-non-interactive, `--repair-drift=overwrite` override, and `--yes` safety guard). Emit a human-readable summary of all actions taken.

This WP is foundational. WP02, WP03, and WP07 depend on it being shipped first.

---

## Context

`src/specify_cli/tool_surface/repair.py` already contains `SurfaceRepairService` and `RepairResult`, but `init` and `upgrade` do not call it. The drift-policy contract lives at `kitty-specs/agent-profile-projection-plugin-production-01KV3NGS/contracts/drift-policy.md`. Refer to it as the authoritative spec for all six rules.

Key principle from FR-003: `--yes` flag does NOT imply drift overwrite. A user who passes `--yes` to silence prompts must still explicitly pass `--repair-drift=overwrite` to overwrite drifted content. This is a deliberate safety guard.

Migration: create `m_0_9_3_surface_repair_wiring.py` following the config-aware migration pattern (`get_agent_dirs_for_project()`). Do not hardcode `AGENT_DIRS`.

---

## Subtask Guidance

### T001 — Audit `SurfaceRepairService.repair()` and extract `run_surface_repair()`

Read `src/specify_cli/tool_surface/repair.py` in full. Understand the current `RepairResult` shape:
- What surface kinds does `repair()` currently enumerate?
- What does it return when a surface is missing vs. stale vs. drifted?
- What side effects does `repair()` have today?

Then extract a thin public function:

```python
def run_surface_repair(
    project_root: Path,
    *,
    interactive: bool,
    repair_drift: bool = False,
) -> DriftPolicySummary:
    """Apply the 6-rule drift policy and return a structured summary."""
```

This function will be the sole entry point for `init` and `upgrade`. Do not mutate `SurfaceRepairService.repair()` itself if it would break existing callers; add the new function alongside it.

### T002 — Implement `DriftPolicySummary` and auto-create/auto-repair rules

Add `DriftPolicySummary` dataclass to `src/specify_cli/tool_surface/repair.py` (or a new `drift_policy.py` if it keeps the file cleaner):

```python
@dataclass
class DriftPolicySummary:
    created: list[Path]       # Rule 1: missing → auto-created
    repaired: list[Path]      # Rule 2: stale → auto-repaired
    drifted_overwritten: list[Path]   # Rule 5: --repair-drift=overwrite applied
    drifted_reported: list[Path]      # Rules 3/4: drifted, reported only
    skipped: list[Path]               # Rule 6: not_applicable, correctly skipped
```

Wire Rule 1 (Missing → auto-create silently) and Rule 2 (Stale → auto-repair silently) in `run_surface_repair()`. These two rules are unconditional and should never prompt.

**Stale detection requires computing the canonical hash** — the current `AgentProfilesProvider.probe()` only compares `disk_hash` to the manifest `file_hash` (installed-at hash), which distinguishes "drifted" (user-modified) from "present" (unchanged). To also detect "stale" (unchanged by user but outdated vs current template), the provider must:
1. Render the current canonical output via `renderer.render(profile)` → get `canonical_hash`
2. Compare: `disk_hash == file_hash AND disk_hash != canonical_hash` → `stale`
3. Compare: `disk_hash != file_hash AND disk_hash != canonical_hash` → `drifted`
4. Compare: `disk_hash == canonical_hash` → `present` (no update needed)

Update `AgentProfilesProvider.probe()` in `src/specify_cli/tool_surface/providers/agent_profiles.py` to add this canonical-hash comparison. Without it, stale profiles will be reported as `present` and auto-repair will never trigger for templates that have been updated by spec-kitty itself.

### T003 — Implement drift-protection rules (Rules 3-5) with `--yes` guard

Rules 3, 4, and 5 from the contract:
- **Rule 3 (Interactive + no --repair-drift)**: prompt the user `Drifted: <path>. Overwrite? [y/N]`; only overwrite on `y`. If the user picks `N` or is non-interactive, report in summary.
- **Rule 4 (Non-interactive, no --repair-drift)**: report in summary only — never overwrite.
- **Rule 5 (--repair-drift=overwrite)**: overwrite unconditionally regardless of interactive mode.
- **Rule 6 (not_applicable)**: skip silently; add to `summary.skipped`.

**CRITICAL guard**: `interactive=True` does NOT mean `repair_drift=True`. The `--yes` flag on `init`/`upgrade` sets `interactive=False`, not `repair_drift=True`. Check the drift-policy contract again: the `--yes` flag makes the session non-interactive, which triggers Rule 4 (report-only), NOT Rule 5 (overwrite).

Implement `is_interactive` detection using `sys.stdin.isatty()` if no explicit flag is passed, but prefer the caller-passed `interactive` argument.

### T004 — Wire into `spec-kitty init`

In `src/specify_cli/cli/commands/init.py`, locate the point after all agent directories and config files have been written. At that point, call:

```python
summary = run_surface_repair(
    project_root,
    interactive=not ctx.obj.get("yes_flag", False),
    repair_drift=ctx.obj.get("repair_drift_overwrite", False),
)
_print_surface_repair_summary(summary)
```

Emit a Rich panel (or plain text if Rich unavailable) showing counts:
```
✔  Surface repair: 3 created, 1 repaired, 0 drifted (use --repair-drift=overwrite to overwrite)
```

If all counts are zero, emit a single quiet line: `✔  Tool surfaces already up to date.`

Ensure `run_surface_repair()` is idempotent: running `init` twice on the same project produces the same files and zero on the second run.

### T005 — Wire into `spec-kitty upgrade` and verify idempotency

In `src/specify_cli/upgrade/runner.py`, locate the point after all migrations have been applied (the "post-migration" hook). Call `run_surface_repair()` there with the same flag forwarding as T004.

Add a new migration `m_0_9_3_surface_repair_wiring.py` that does NOT mutate files itself — its role is to establish the migration record so the migration framework knows this version has been applied. The actual repair logic lives in `run_surface_repair()` which runs post-migration.

Use `get_agent_dirs_for_project()` if the migration needs to enumerate agent directories. Do not hardcode `AGENT_DIRS`.

Idempotency test: run `spec-kitty upgrade` on a clean project twice; assert that the second run emits "0 created, 0 repaired" in the summary.

---

## Branch Strategy

- **Planning base branch**: `feat/agent-profile-projection-plugin-production`
- **Final merge target**: `feat/agent-profile-projection-plugin-production`
- **Worktree**: allocated by `spec-kitty agent action implement WP01` from `lanes.json`; do not create manually

To start work: `spec-kitty agent action implement WP01 --agent claude`

---

## Definition of Done

- [ ] `run_surface_repair()` extracted and callable from `init` and `upgrade`
- [ ] `DriftPolicySummary` dataclass exists and is populated correctly
- [ ] Rules 1-6 implemented per `contracts/drift-policy.md`
- [ ] `--yes` flag does NOT trigger drift overwrite (Rule 4 applies, not Rule 5)
- [ ] `spec-kitty init` calls `run_surface_repair()` post-agent-config-write
- [ ] `spec-kitty upgrade` calls `run_surface_repair()` post-migrations
- [ ] Second `upgrade` run on clean project emits zero counts
- [ ] Migration `m_0_9_3_surface_repair_wiring.py` registered
- [ ] `ruff check` and `mypy --strict` pass on all changed modules
- [ ] Unit tests in `test_repair_wiring_unit.py` covering Rules 1-6

---

## Risks

- `SurfaceRepairService.repair()` may have hidden side effects that break if called from `upgrade` mid-migration — audit before extracting
- Rich prompt input from `run_surface_repair()` inside `init` may interfere with `--json` output mode — gate prompts behind `not json_output`
- `get_agent_dirs_for_project()` returns only configured agents; newly created agent dirs may not appear on first call if config hasn't been flushed — ensure repair runs after config is written and flushed to disk

---

## Reviewer Notes

- Verify that the `--yes` guard is correct: run `spec-kitty upgrade --yes` on a project with a drifted file and confirm it does NOT overwrite
- Verify idempotency: run `spec-kitty upgrade` twice and check the second run reports zero counts
- Complexity ceiling is 15 (ruff C901); extract helpers if `run_surface_repair` grows beyond it
