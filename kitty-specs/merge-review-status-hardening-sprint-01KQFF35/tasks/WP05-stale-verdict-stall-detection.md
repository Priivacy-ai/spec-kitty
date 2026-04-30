---
work_package_id: WP05
title: Stale verdict status warning + stalled reviewer detection
dependencies: []
requirement_refs:
- FR-008
- FR-017
- FR-018
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-merge-review-status-hardening-sprint-01KQFF35
base_commit: 26df0d78b45a9f86e0e48171a3831bc0b242da17
created_at: '2026-04-30T15:47:26.728610+00:00'
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
agent: "claude:claude-sonnet-4-6:python-pedro:reviewer"
shell_pid: "6129"
history:
- date: '2026-04-30'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/agent_utils/
execution_mode: code_change
owned_files:
- src/specify_cli/agent_utils/status.py
- src/specify_cli/cli/commands/next_cmd.py
- tests/specify_cli/agent_utils/test_status.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Two improvements to the status board and `spec-kitty next` output:

1. **Stale verdict warning** (#904-status): When `spec-kitty agent tasks status` renders the kanban board, warn next to any WP in `approved` or `done` lane whose latest `review-cycle-N.md` has `verdict: rejected`.

2. **Stalled reviewer detection** (#909): WPs in `in_review` with no status event for more than the stall threshold (default 30 min) are marked `⚠ STALLED — no move-task in Xm`. `spec-kitty next` surfaces these as actionable items with intervention commands.

## Context

**Stale verdict**: After a force-approve, review artifacts can be left in `rejected` state silently. WP02 blocks the transition going forward; this WP adds retrospective detection to the status board for existing stale verdicts.

**Stall detection**: Reviewer subagents can get stuck (timeout, crash, context overflow). When a WP sits in `in_review` for more than 30 minutes with no `move-task` event, that's a signal the orchestrator should intervene. Currently the board is silent.

**Key files**:
- `src/specify_cli/agent_utils/status.py:28` — `show_kanban_status()` function
- Status event log: `kitty-specs/<slug>/status.events.jsonl` (each line has `at` ISO timestamp and `to_lane`, `wp_id` fields)
- Config: `.kittify/config.yaml` — add optional `review.stall_threshold_minutes: 30`
- `spec-kitty next`: `src/specify_cli/cli/commands/next_cmd.py`

## Branch Strategy

- **Planning branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: resolved by `spec-kitty agent action implement WP05 --agent claude`

---

## Subtask T023 — Stale verdict warning in `show_kanban_status()`

**Purpose**: Add a warning next to `approved`/`done` WPs that have `verdict: rejected` in their latest review artifact.

**Steps**:
1. Read `src/specify_cli/agent_utils/status.py` in full.
2. Add a private helper `_get_wp_review_verdict(wp_dir: Path) -> str | None` that:
   - Globs `review-cycle-*.md` files in `wp_dir`, sorted by N (highest = latest).
   - Parses YAML frontmatter (between first `---` pair) and returns `verdict` field.
   - Returns `None` on any error (file absent, malformed YAML, no frontmatter).
   ```python
   import re
   from pathlib import Path

   def _get_wp_review_verdict(wp_dir: Path) -> str | None:
       cycles = sorted(
           wp_dir.glob("review-cycle-*.md"),
           key=lambda p: int(m.group(1)) if (m := re.search(r"review-cycle-(\d+)\.md", p.name)) else 0,
       )
       if not cycles:
           return None
       try:
           text = cycles[-1].read_text(encoding="utf-8")
           match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
           if not match:
               return None
           import yaml
           fm = yaml.safe_load(match.group(1)) or {}
           return fm.get("verdict")
       except Exception:  # noqa: BLE001 — review artifact may be absent or malformed; fail-open
           return None
   ```
3. In `show_kanban_status()`, after building the lane snapshot, iterate WPs in `approved` and `done` lanes. For each, resolve `wp_dir` (the WP's task directory under `kitty-specs/<slug>/tasks/`). Call `_get_wp_review_verdict(wp_dir)`. If it returns `"rejected"`, append a warning to the WP's display row: `⚠ review artifact: verdict=rejected`.
4. Return a `stale_verdicts` key in the return dict: list of `{"wp_id": ..., "artifact": ...}`.

**Files**: `src/specify_cli/agent_utils/status.py`

**Validation**: A WP in `done` lane with `review-cycle-1.md` containing `verdict: rejected` shows the warning in status output.

---

## Subtask T024 — `_get_last_event_time()` helper

**Purpose**: Extract the most recent event timestamp for a given WP from the event log.

**Steps**:
1. Add to `agent_utils/status.py`:
   ```python
   from datetime import datetime, timezone

   def _get_last_event_time(events: list, wp_id: str) -> datetime | None:
       """Return the `at` datetime of the most recent event for wp_id, or None."""
       wp_events = [e for e in events if e.get("wp_id") == wp_id]
       if not wp_events:
           return None
       latest = max(wp_events, key=lambda e: e.get("at", ""))
       at_str = latest.get("at")
       if not at_str:
           return None
       try:
           return datetime.fromisoformat(at_str)
       except ValueError:
           return None
   ```
2. The event log is loaded by `read_events()` from `specify_cli.status.store` (check existing imports in `status.py`).
3. If events are already loaded elsewhere in `show_kanban_status()`, reuse that loaded list.

**Files**: `src/specify_cli/agent_utils/status.py`

---

## Subtask T025 — Stall detection loop in `show_kanban_status()`

**Purpose**: For each `in_review` WP, compute age and flag if over threshold.

**Steps**:
1. In `show_kanban_status()`, load the stall threshold:
   ```python
   from specify_cli.core.config import load_project_config  # or whatever the config loader is
   config = load_project_config(repo_root)
   threshold_minutes = (
       config.get("review", {}).get("stall_threshold_minutes", 30)
       if isinstance(config, dict)
       else 30
   )
   ```
   Use the existing config loading pattern from the file (check imports).

2. Iterate WPs in `in_review` lane. For each:
   ```python
   now = datetime.now(timezone.utc)
   last_event = _get_last_event_time(events, wp_id)
   if last_event:
       age_minutes = (now - last_event).total_seconds() / 60
       if age_minutes > threshold_minutes:
           stall_label = f"⚠ STALLED — no move-task in {int(age_minutes)}m"
           # append to WP's display row
   ```

3. Match the display row append pattern used for the stale verdict warning in T023.

**Files**: `src/specify_cli/agent_utils/status.py`

---

## Subtask T026 — Return stalled WPs from `show_kanban_status()`

**Purpose**: Surface stalled WPs to callers so `spec-kitty next` can act on them.

**Steps**:
1. Collect stalled WP info during the loop in T025:
   ```python
   stalled_wps: list[dict] = []
   # inside the loop:
   if age_minutes > threshold_minutes:
       stalled_wps.append({"wp_id": wp_id, "age_minutes": int(age_minutes), "mission_slug": mission_slug})
   ```
2. Return `stalled_wps` in the existing return dict from `show_kanban_status()`. Example:
   ```python
   return {
       ...,
       "stalled_wps": stalled_wps,
       "stale_verdicts": stale_verdicts,
   }
   ```
3. Ensure backward compatibility: callers that don't use these keys are unaffected (dict access with `.get()`).

**Files**: `src/specify_cli/agent_utils/status.py`

---

## Subtask T027 — Stalled WP intervention in `next_cmd.py`

**Purpose**: Have `spec-kitty next` surface stalled review agents as actionable items.

**Steps**:
1. Read `src/specify_cli/cli/commands/next_cmd.py` to understand how it calls `show_kanban_status()` or equivalent.
2. After the status call, check for stalled WPs:
   ```python
   stalled = status_result.get("stalled_wps", [])
   for stall in stalled:
       wp_id = stall["wp_id"]
       age_m = stall["age_minutes"]
       slug = stall.get("mission_slug", "<mission>")
       console.print(
           f"\n⚠  {wp_id} has been in_review for {age_m}m — reviewer may be stalled.\n"
           f"   Intervention options:\n"
           f"     spec-kitty agent tasks move-task {wp_id} --to approved --force "
           f"--note 'Approved after {age_m}m stall' --mission {slug}\n"
           f"     spec-kitty agent tasks move-task {wp_id} --to planned "
           f"--review-feedback-file <path> --mission {slug}"
       )
   ```
3. Only print the block if `stalled` is non-empty.
4. Use `console.print` (Rich) if the rest of `next_cmd.py` uses Rich; otherwise `print`.

**Files**: `src/specify_cli/cli/commands/next_cmd.py`

**Validation**: A mocked `show_kanban_status()` return with a stalled WP causes `spec-kitty next` output to include the two intervention commands.

---

## Subtask T028 — Tests

**Purpose**: Cover stale verdict warning, stall detection, and next intervention output.

**Steps**:
1. Find or create `tests/specify_cli/agent_utils/test_status.py`.

2. **Test `test_stale_verdict_warning_shown_in_done_lane`**:
   - Setup: mission with WP01 in `done` lane; `review-cycle-1.md` has `verdict: rejected`.
   - Call `show_kanban_status(mission_slug)`.
   - Assert the return dict contains `stale_verdicts` with WP01.
   - Assert the rendered board output includes `verdict=rejected`.

3. **Test `test_stale_verdict_clean_no_warning`**:
   - WP01 in `done` with `verdict: approved`. Assert no stale verdicts.

4. **Test `test_stall_detected_above_threshold`**:
   - WP02 in `in_review`; last event is 45 minutes ago (mock `datetime.now`).
   - Threshold is 30 minutes.
   - Assert `stalled_wps` contains WP02 with `age_minutes >= 45`.
   - Assert board output contains `⚠ STALLED`.

5. **Test `test_stall_not_detected_below_threshold`**:
   - WP02 in `in_review`; last event is 10 minutes ago.
   - Assert `stalled_wps` is empty.

6. **Test `test_next_cmd_prints_intervention_for_stalled_wp`** (optional, if `next_cmd` is testable):
   - Mock `show_kanban_status()` to return a stalled WP.
   - Capture stdout from `next_step`.
   - Assert intervention command text appears.

7. Run `uv run pytest tests/specify_cli/agent_utils/test_status.py -x`.
8. Run `uv run mypy --strict src/specify_cli/agent_utils/status.py src/specify_cli/cli/commands/next_cmd.py`.

---

## Definition of Done

- [ ] `show_kanban_status()` displays `⚠ review artifact: verdict=rejected` next to `done`/`approved` WPs with stale verdict
- [ ] `show_kanban_status()` displays `⚠ STALLED — no move-task in Xm` for `in_review` WPs over threshold
- [ ] `show_kanban_status()` returns `stalled_wps` and `stale_verdicts` in return dict
- [ ] `spec-kitty next` prints intervention commands when stalled WPs are present
- [ ] Stall threshold defaults to 30 min; reads `review.stall_threshold_minutes` from config when present
- [ ] Tests pass: `test_stale_verdict_warning_shown_in_done_lane`, `test_stale_verdict_clean_no_warning`, `test_stall_detected_above_threshold`, `test_stall_not_detected_below_threshold`
- [ ] `uv run mypy --strict` passes on modified files

## Reviewer Guidance

- Create a mock `status.events.jsonl` with an `in_review` event 35 minutes in the past; run `spec-kitty agent tasks status` and verify the `STALLED` marker appears.
- Verify the intervention commands in `spec-kitty next` output include the correct WP ID and mission slug.
- Confirm the stall check is purely read-only (no files written, no events emitted).

## Activity Log

- 2026-04-30T17:41:07Z – claude:claude-sonnet-4-6:python-pedro:reviewer – shell_pid=6129 – Started review via action command
- 2026-04-30T17:43:16Z – claude:claude-sonnet-4-6:python-pedro:reviewer – shell_pid=6129 – Review passed: stall detection and stale verdict warnings verified with passing tests
- 2026-04-30T17:59:17Z – claude:claude-sonnet-4-6:python-pedro:reviewer – shell_pid=6129 – Done override: Mission squash-merged at cbca2025 on main; merge command recorded WP01 done but hung on remaining WPs
