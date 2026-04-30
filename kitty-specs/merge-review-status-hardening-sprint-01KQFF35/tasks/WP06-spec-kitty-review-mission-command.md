---
work_package_id: WP06
title: spec-kitty review --mission command
dependencies: []
requirement_refs:
- FR-013
- FR-014
- FR-015
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning and merge target are both main. Execution worktree is allocated per lanes.json.
subtasks:
- T029
- T030
- T031
- T032
- T033
- T034
agent: claude
history:
- date: '2026-04-30'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/review.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/review.py
- src/specify_cli/cli/commands/__init__.py
- tests/specify_cli/cli/commands/test_review.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Create `spec-kitty review --mission <slug>` as a first-class post-merge validation gate. The command performs four checks and writes `kitty-specs/<slug>/mission-review-report.md` with a machine-readable verdict.

**The four checks**:
1. All WPs for the mission are in `done` lane (hard failure if not)
2. New public symbols in the mission diff have at least one non-test caller (informational)
3. `# noqa: BLE001` suppressions in `auth/` and `cli/commands/` have inline justification (informational)
4. Write the report

## Context

Currently, the mission lifecycle ends at `done` with no structured gate between merge and release. Operators have to manually check for dead code and stale suppressions. This command automates the three most common post-merge validation concerns.

**Scope for this WP**: MVP only — no external calls, no SaaS sync, no interactive prompts.

**CLI registration pattern**: All single-function commands follow this pattern:
```python
# In __init__.py register_commands():
from . import review as review_module
app.command(name="review")(review_module.review_mission)
```

**Reference output format**: See `contracts/review-command-interface.md` in this mission's kitty-specs dir.

**Key facts**:
- `baseline_merge_commit` is a field in `meta.json` (absent for pre-083 missions → skip dead-code step with warning)
- Mission resolver: use `spec-kitty agent context resolve --mission <handle> --json` or the Python resolver already used in other commands
- `materialize()` in `src/specify_cli/status/reducer.py` returns a lane snapshot from the event log

## Branch Strategy

- **Planning branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: resolved by `spec-kitty agent action implement WP06 --agent claude`

---

## Subtask T029 — Create `review.py` with mission resolver and WP lane check

**Purpose**: Scaffold the command, resolve the mission, and check all WPs are in `done`.

**Steps**:
1. Create `src/specify_cli/cli/commands/review.py`:
   ```python
   """spec-kitty review --mission <handle>: Post-merge mission validation gate."""
   from __future__ import annotations

   from pathlib import Path
   from datetime import datetime, timezone
   from typing import Annotated

   import typer

   app = typer.Typer()


   def review_mission(
       mission: Annotated[str, typer.Option("--mission", help="Mission handle (id, mid8, or slug).")] = "",
   ) -> None:
       """Validate a merged mission: WP lane check, dead-code scan, BLE001 audit."""
       from rich.console import Console
       console = Console()
       # ... implementation
   ```

2. Resolve the feature dir from `--mission`:
   - Check how other commands (e.g., `merge.py`, `implement.py`) resolve feature dirs from a mission handle.
   - Use the same resolver pattern. Typically involves `resolve_mission_handle()` or `get_feature_dir_for_mission()` from a core module.
   - If the handle is empty or unresolvable, print an error and `raise typer.Exit(2)`.

3. Read `meta.json` from the feature dir. Extract `mission_slug`, `friendly_name`, `baseline_merge_commit`.

4. Load status events and call `materialize()`:
   ```python
   from specify_cli.status.store import read_events
   from specify_cli.status.reducer import materialize
   events_path = feature_dir / "status.events.jsonl"
   events = read_events(events_path)
   snapshot = materialize(feature_dir)
   ```

5. WP lane check:
   ```python
   findings: list[dict] = []
   non_done = [wp_id for wp_id, lane in snapshot.lanes.items() if lane != "done"]
   if non_done:
       for wp_id in non_done:
           findings.append({"type": "wp_not_done", "wp_id": wp_id, "lane": snapshot.lanes[wp_id]})
       console.print(f"[red]✗[/red]  WP lane check: {len(non_done)} WP(s) not in done")
       for wp_id in non_done:
           console.print(f"      {wp_id}: {snapshot.lanes[wp_id]}")
   else:
       console.print(f"[green]✓[/green]  WP lane check: all {len(snapshot.lanes)} WP(s) in done")
   ```

**Files**: `src/specify_cli/cli/commands/review.py` (new)

**Validation**: `spec-kitty review --mission <slug>` with a mission that has non-done WPs exits with a clear list.

---

## Subtask T030 — Dead-code scan step

**Purpose**: Detect new public functions/classes introduced by the mission that have no non-test callers.

**Steps**:
1. If `baseline_merge_commit` is absent from `meta.json`, print:
   `"⚠  Dead-code scan skipped: no baseline_merge_commit in meta.json (pre-083 mission)"` and skip this step.

2. Run the diff:
   ```python
   import subprocess
   result = subprocess.run(
       ["git", "diff", f"{baseline_merge_commit}..HEAD", "--", "src/"],
       cwd=repo_root,
       capture_output=True,
       text=True,
   )
   diff_output = result.stdout
   ```

3. Parse added lines for new public symbols (heuristic — not perfect AST analysis):
   ```python
   import re
   new_symbols: list[tuple[str, str]] = []  # (symbol_name, context_hint)
   current_file = ""
   for line in diff_output.splitlines():
       if line.startswith("+++ b/"):
           current_file = line[6:]
       elif line.startswith("+") and not line.startswith("+++"):
           # Match `def public_name(` or `class PublicName(`
           m = re.match(r"^\+\s*(def|class)\s+([A-Za-z][A-Za-z0-9_]*)\s*[\(:]", line)
           if m and not m.group(2).startswith("_"):  # skip private symbols
               new_symbols.append((m.group(2), current_file))
   ```

4. For each new symbol, check for non-test callers:
   ```python
   dead_symbols = []
   for symbol, defined_in in new_symbols:
       grep_result = subprocess.run(
           ["grep", "-r", "--include=*.py", "-l", symbol, "src/"],
           cwd=repo_root,
           capture_output=True,
           text=True,
       )
       callers = [
           f for f in grep_result.stdout.strip().splitlines()
           if f != defined_in and "test" not in f
       ]
       if not callers:
           dead_symbols.append({"symbol": symbol, "file": defined_in})
           findings.append({"type": "dead_code", "symbol": symbol, "file": defined_in})
   ```

5. Print results:
   ```python
   if dead_symbols:
       console.print(f"[red]✗[/red]  Dead-code scan: {len(dead_symbols)} unreferenced public symbol(s)")
       for d in dead_symbols:
           console.print(f"       {d['file']}  {d['symbol']}")
   else:
       console.print(f"[green]✓[/green]  Dead-code scan: 0 unreferenced public symbols")
   ```

**Known false-positives**: `__all__` exports, entry points, dynamic dispatch. Document in `--help` docstring.

**Files**: `src/specify_cli/cli/commands/review.py`

---

## Subtask T031 — BLE001 unjustified suppression audit

**Purpose**: Flag `# noqa: BLE001` suppressions in `auth/` and `cli/commands/` that lack inline justification.

**Steps**:
1. Grep the two directories:
   ```python
   search_dirs = [
       repo_root / "src" / "specify_cli" / "auth",
       repo_root / "src" / "specify_cli" / "cli" / "commands",
   ]
   ble001_findings = []
   for d in search_dirs:
       result = subprocess.run(
           ["grep", "-rn", "noqa: BLE001", str(d)],
           capture_output=True, text=True,
       )
       for line in result.stdout.strip().splitlines():
           # Format: path:lineno:content
           parts = line.split(":", 2)
           if len(parts) < 3:
               continue
           content = parts[2]
           # Check if there's justification text after "BLE001"
           ble_match = re.search(r"noqa: BLE001(.*)$", content)
           if ble_match:
               after = ble_match.group(1).strip().lstrip(",").strip()
               # Remove other rule codes like ", S110"
               after = re.sub(r"^[A-Z0-9,\s]+", "", after).strip()
               if not after or after in ("—", "-", "–"):
                   # Bare suppression
                   ble001_findings.append({"file": parts[0], "line": parts[1], "content": content.strip()})
                   findings.append({"type": "ble001_suppression", "file": parts[0], "line": parts[1]})
   ```
2. Print results:
   ```python
   if ble001_findings:
       console.print(f"[red]✗[/red]  BLE001 audit: {len(ble001_findings)} unjustified suppression(s)")
       for f in ble001_findings:
           console.print(f"       {f['file']}:{f['line']}")
   else:
       console.print("[green]✓[/green]  BLE001 audit: 0 unjustified suppressions")
   ```

**Files**: `src/specify_cli/cli/commands/review.py`

**Note**: After WP03 completes, this check should return 0 findings for the `cli/commands/` directory. But the command tests against the live codebase state, not a fixed expected result.

---

## Subtask T032 — Report writer

**Purpose**: Write `kitty-specs/<slug>/mission-review-report.md` with a machine-readable frontmatter verdict.

**Steps**:
1. Determine verdict:
   ```python
   wp_not_done_count = sum(1 for f in findings if f["type"] == "wp_not_done")
   if wp_not_done_count > 0:
       verdict = "fail"
   elif findings:
       verdict = "pass_with_notes"
   else:
       verdict = "pass"
   ```
2. Build the report body:
   ```python
   from specify_cli.core.yaml_utils import dump_frontmatter  # or build manually
   reviewed_at = datetime.now(timezone.utc).isoformat()
   report_lines = [
       "---",
       f"verdict: {verdict}",
       f"reviewed_at: {reviewed_at}",
       f"findings: {len(findings)}",
       "---",
       "",
   ]
   if findings:
       report_lines.append("## Findings")
       report_lines.append("")
       for f in findings:
           if f["type"] == "wp_not_done":
               report_lines.append(f"- **wp_not_done** `{f['wp_id']}`: lane is `{f.get('lane','unknown')}`")
           elif f["type"] == "dead_code":
               report_lines.append(f"- **dead_code** `{f['file']}` — `{f['symbol']}`: no non-test callers found")
           elif f["type"] == "ble001_suppression":
               report_lines.append(f"- **ble001_suppression** `{f['file']}:{f['line']}`: no inline justification")
   else:
       report_lines.append("No findings.")
   ```
3. Write to disk:
   ```python
   report_path = feature_dir / "mission-review-report.md"
   report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
   ```
4. Print summary and exit:
   ```python
   verdict_color = "green" if verdict == "pass" else ("yellow" if verdict == "pass_with_notes" else "red")
   console.print(f"\nVerdict: [{verdict_color}]{verdict}[/{verdict_color}]  ({len(findings)} finding(s))")
   console.print(f"Report written: {report_path.relative_to(repo_root)}")
   if verdict == "fail":
       raise typer.Exit(1)
   ```

**Files**: `src/specify_cli/cli/commands/review.py`

---

## Subtask T033 — Register command in `__init__.py`

**Purpose**: Make `spec-kitty review --mission <slug>` available on the CLI.

**Steps**:
1. Open `src/specify_cli/cli/commands/__init__.py`.
2. Add import (alphabetically with the other single-command imports):
   ```python
   from . import review as review_module
   ```
3. Add registration (near the other `app.command()` registrations, after `research`):
   ```python
   app.command(name="review")(review_module.review_mission)
   ```
4. Verify `spec-kitty --help` lists `review` after the change.

**Files**: `src/specify_cli/cli/commands/__init__.py`

**Validation**: `spec-kitty review --help` shows the mission option.

---

## Subtask T034 — Integration test

**Purpose**: Verify the command works end-to-end with a minimal mission fixture.

**Steps**:
1. Create `tests/specify_cli/cli/commands/test_review.py`.
2. Write `test_review_passes_when_all_done`:
   - Setup: a tmp dir with `meta.json` (no `baseline_merge_commit`), `status.events.jsonl` with all WPs in `done`, no review-cycle artifacts.
   - Invoke `review_mission(mission=<slug>)` (or via Typer test runner).
   - Assert exit 0 and `mission-review-report.md` written with `verdict: pass`.
3. Write `test_review_fails_when_wp_not_done`:
   - Setup: same fixture but WP01 in `in_progress`.
   - Assert exit 1 and `verdict: fail` in report.
4. Write `test_review_report_frontmatter_structure`:
   - Assert the report file has valid frontmatter with `verdict`, `reviewed_at`, `findings` keys.
5. Run `uv run pytest tests/specify_cli/cli/commands/test_review.py -x`.
6. Run `uv run mypy --strict src/specify_cli/cli/commands/review.py src/specify_cli/cli/commands/__init__.py`.

---

## Definition of Done

- [ ] `spec-kitty review --mission <slug>` exits 0 when all WPs are done and no findings
- [ ] Exits 1 with `verdict: fail` when WPs are not done
- [ ] Dead-code scan reports unreferenced public symbols (skipped with warning if no `baseline_merge_commit`)
- [ ] BLE001 audit flags suppressions without inline justification in `auth/` and `cli/commands/`
- [ ] `mission-review-report.md` written with `verdict`, `reviewed_at`, `findings` frontmatter
- [ ] `spec-kitty review --help` shows `--mission` option
- [ ] `spec-kitty --help` lists `review` command
- [ ] Tests pass: `test_review_passes_when_all_done`, `test_review_fails_when_wp_not_done`, `test_review_report_frontmatter_structure`
- [ ] `uv run mypy --strict src/specify_cli/cli/commands/review.py` — zero errors

## Reviewer Guidance

- Run `spec-kitty review --mission merge-review-status-hardening-sprint-01KQFF35` after all WPs are done; report should be written with `verdict: pass`.
- Check `spec-kitty review --help` for `--mission` option and docstring mentioning known false-positives.
- Read `mission-review-report.md` — verify frontmatter is valid YAML and findings are human-readable.
- The dead-code scan is heuristic: confirm the docstring documents known false-positive scenarios (`__all__` exports, entry points).
