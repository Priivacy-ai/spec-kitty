---
work_package_id: WP05
title: 'CLI: retrospect create / backfill / summary tighten / synthesize tighten'
dependencies:
- WP02
- WP03
requirement_refs:
- FR-011
- FR-012
- FR-013
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
- T028
- T029
phase: Surface
assignee: ''
agent: "claude:claude-sonnet-4-6:reviewer-renata:reviewer"
shell_pid: "57311"
history:
- timestamp: '2026-05-19T13:29:59Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/retrospect.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/cli/commands/retrospect.py
- src/specify_cli/cli/commands/agent_retrospect.py
- tests/cli/commands/test_retrospect.py
role: implementer
tags: []
---

# Work Package Prompt: WP05 — CLI Surfaces (create / backfill / summary tighten / synthesize tighten)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Ship the real authoring CLI surfaces (`spec-kitty retrospect create` and `spec-kitty retrospect backfill`), surface the four record states in `summary` output (no semantic change, just better distinguishing), and tighten `agent retrospect synthesize`'s default-path to error on missing records while preserving the legacy fabrication behavior behind an explicit `--fabricate-empty` flag.

## Context

References:
- CLI contracts: [contracts/retrospect-cli.contract.md](../contracts/retrospect-cli.contract.md)
- Generator: WP02 provides `generate_retrospective(mission, policy, repo_root)`.
- Writer: WP03 provides `write_record(record, mode={"error","overwrite","update"}, repo_root)`.
- Quickstart: [quickstart.md](../quickstart.md) — operator-facing examples.

Existing surface:
- `src/specify_cli/cli/commands/agent_retrospect.py` — today's `agent retrospect synthesize` and possibly `summary` registrations.
- `src/specify_cli/retrospective/summary.py` — WP03 extends this with the 4-state classifier (T017).

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- Execution worktree resolved via `lanes.json` after `finalize-tasks`.

## Subtasks

### T024 — Implement `spec-kitty retrospect create --mission <handle>`

**Purpose**: A real authoring surface that runs the generator and writer for one completed mission.

**Steps**:

1. Create `src/specify_cli/cli/commands/retrospect.py` as a new Typer subapp registered at `spec-kitty retrospect`. (The existing `summary` command lives under `agent retrospect` today — keep both top-level and `agent` namespaces for back-compat.)
2. Implement the `create` command per [contracts/retrospect-cli.contract.md § create](../contracts/retrospect-cli.contract.md#spec-kitty-retrospect-create):
   ```python
   @app.command("create")
   def create(
       mission: str = typer.Option(..., "--mission", help="..."),
       overwrite: bool = typer.Option(False, "--overwrite"),
       update: bool = typer.Option(False, "--update"),
       json_output: bool = typer.Option(False, "--json"),
   ):
       if overwrite and update:
           raise typer.BadParameter("--overwrite and --update are mutually exclusive")
       handle = resolve_mission_handle(mission)  # mission_id > mid8 > slug; structured error on ambiguity
       if not mission_is_completed(handle):
           emit_error("MISSION_NOT_COMPLETED", open_wps=...)
           raise typer.Exit(1)
       policy, source_map = resolve_policy(repo_root)
       record = generate_retrospective(handle, policy, repo_root)
       record.provenance = Provenance(kind="explicit_create", ...)
       mode = "overwrite" if overwrite else ("update" if update else "error")
       try:
           path = write_record(record, mode=mode, repo_root=repo_root)
       except RecordExistsError:
           emit_error("RETROSPECTIVE_RECORD_EXISTS", record_path=...)
           raise typer.Exit(1)
       emit_captured(record, repo_root, provenance_kind="explicit_create", actor=cli_actor())
       emit_success_or_json(path, record, json_output)
   ```
3. JSON output shape exactly matches the contract (success and error variants).
4. Auto-commit behavior: if `.kittify/config.yaml#agents.auto_commit: true` (project default), commit the record + event-log change with a structured message (e.g. `chore(retrospective): author retrospective for <slug>`). Otherwise the operator commits.

**Files**:
- `src/specify_cli/cli/commands/retrospect.py` (new, ~150 lines for create + shared helpers)

**Validation**:
- [ ] `spec-kitty retrospect create --mission <known-completed-handle> --json` returns success JSON
- [ ] Re-running without `--overwrite` returns `RETROSPECTIVE_RECORD_EXISTS` exit 1
- [ ] Ambiguous mission handle returns `MISSION_AMBIGUOUS_SELECTOR` with candidate list

---

### T025 — `--overwrite` / `--update` / `--json` flag plumbing

**Purpose**: Wire the three flags + structured error codes per the CLI contract.

**Steps**:

1. Mutual exclusion: `--overwrite` and `--update` cannot both be set. Typer raises `BadParameter`.
2. Error codes (from CLI contract):
   - `RETROSPECTIVE_RECORD_EXISTS` — record already on disk + no flag
   - `MISSION_NOT_COMPLETED` — open WPs in non-terminal lanes
   - `MISSION_AMBIGUOUS_SELECTOR` — handle resolves to multiple missions
   - `MISSION_NOT_FOUND` — no mission resolves
   - `POLICY_RESOLUTION_ERROR` — passes through from resolver
3. JSON output uniform across all error paths: `{result: "blocked", code: <CODE>, ...context fields, blocked_reason: <human msg>, exit_code: 1}`
4. Human (non-`--json`) output uses Rich for color/formatting; same content with `Rich.panel` for emphasis.

**Files**:
- `src/specify_cli/cli/commands/retrospect.py` (extend with `_emit_error` helper, ~40 lines)

**Validation**:
- [ ] All 5 error codes produce the documented JSON shape
- [ ] Human output is Rich-formatted and contains the same key information

---

### T026 — Implement `spec-kitty retrospect backfill`

**Purpose**: Author records for historical missions in bulk.

**Steps**:

1. Add `backfill` command to `retrospect.py`:
   ```python
   @app.command("backfill")
   def backfill(
       since: str = typer.Option(None, "--since", help="ISO date"),
       until: str = typer.Option(None, "--until", help="ISO date"),
       mission: str = typer.Option(None, "--mission"),
       dry_run: bool = typer.Option(False, "--dry-run"),
       emit_skipped: bool = typer.Option(False, "--emit-skipped"),
       emit_failures: bool = typer.Option(False, "--emit-failures"),
       json_output: bool = typer.Option(False, "--json"),
   ):
       window = parse_window(since, until)  # default since = 30 days ago
       candidates = discover_completed_missions(repo_root, window, mission_filter=mission)
       result = BackfillResult(window=window, scanned=len(candidates))
       for handle in candidates:
           record_path = canonical_record_path(handle)
           if record_path.exists():
               result.skipped.append({...reason: "already_exists"})
               if emit_skipped and not dry_run: emit_captured(... provenance="backfill", ...)  # actually no — skipped means don't emit captured; review
               continue
           try:
               policy, source_map = resolve_policy(repo_root)
               record = generate_retrospective(handle, policy, repo_root)
               record.provenance = Provenance(kind="backfill", ...)
               if not dry_run:
                   write_record(record, mode="error", repo_root=repo_root)
                   emit_captured(record, repo_root, provenance_kind="backfill", actor=cli_actor())
               result.created.append({...})
           except (FileNotFoundError, IsADirectoryError) as exc:
               result.failed.append({...failure_category: "missing_artifacts", missing: [...]})
               if emit_failures and not dry_run: emit_capture_failed(...)
           except Exception as exc:
               result.failed.append({...failure_category: "generator_exception"})
               if emit_failures and not dry_run: emit_capture_failed(...)
       result.next_actions = compute_next_actions(result)
       emit_summary(result, json_output)
   ```
2. Use Rich progress bar in non-`--json` mode. In `--json` mode emit a single aggregate object (NOT line-delimited) at the end.
3. Skip reasons (structured enum): `already_exists`, `not_completed`, `out_of_window`, `mission_filter_excluded`.
4. Window default: last 30 days. `--since` and `--until` are ISO 8601 date or datetime strings.
5. Failure handling: per-mission failures are NOT fatal; aggregate report shows them. Only `--json` parse errors of `--since`/`--until` are fatal (exit 2 with `BadParameter`).

**Files**:
- `src/specify_cli/cli/commands/retrospect.py` (extend, ~180 lines for backfill)

**Validation**:
- [ ] `backfill --dry-run` reports created/skipped/failed counts without writing anything
- [ ] `backfill --since 2026-01-01` on a repo with mixed completed missions processes only the ones in window
- [ ] Existing records skip with reason `already_exists`; NOT overwritten
- [ ] Progress bar shows in non-JSON mode; absent in JSON mode

---

### T027 — Tighten `retrospect summary` (4 record states, no semantic change)

**Purpose**: `summary` now distinguishes `has_findings` / `ran_no_findings` / `missing` / `failed` in its output. Read-only invariant preserved.

**Steps**:

1. The classifier from WP03 T017 lives in `src/specify_cli/retrospective/summary.py`. This subtask wires the CLI command's output formatting to expose the four-state distinction.
2. Locate the existing `summary` CLI registration (currently `agent retrospect summary`, possibly also `retrospect summary`). Extend its output JSON shape:
   ```json
   {
     "missions": [
       {
         "mission_id": "...",
         "mission_slug": "...",
         "findings_status": "has_findings" | "ran_no_findings" | "missing" | "failed",
         "policy_source": {...},  // snapshot from most recent Captured event; null if missing
         ...existing fields...
       }
     ],
     "aggregate": {
       "has_findings": <int>,
       "ran_no_findings": <int>,
       "missing": <int>,
       "failed": <int>
     }
   }
   ```
3. Add `--filter` flag (`--filter <state>`): only show missions in the given state.
4. **No semantic change**: `summary` MUST NOT write, mutate, or author. Tests assert no files change on disk during a summary run.
5. Re-export the command from `retrospect.py` so `spec-kitty retrospect summary` works (top-level surface) alongside the existing `spec-kitty agent retrospect summary` (kept for back-compat).

**Files**:
- `src/specify_cli/cli/commands/retrospect.py` (re-export + extend, ~60 lines)
- `src/specify_cli/cli/commands/agent_retrospect.py` (light additions to extend output shape — coordinate via owned_files, this file is in WP05's ownership for the summary change scope only)

**Validation**:
- [ ] Output contains the new `findings_status` and `policy_source` keys per mission
- [ ] Aggregate counts add up to total mission count
- [ ] No filesystem mutation during a summary run (assert via `tmp_path` snapshot before/after)
- [ ] Back-compat: existing keys preserved

---

### T028 — Tighten `agent retrospect synthesize` default-path; add `--fabricate-empty`

**Purpose**: Default path errors on missing records. `--fabricate-empty` preserves legacy fabrication behavior with explicit actor-attributed provenance.

**Steps**:

1. In `src/specify_cli/cli/commands/agent_retrospect.py`, locate the `synthesize` command.
2. **Default-path change**: when invoked on a mission with no `retrospective.yaml`, error:
   ```json
   {
     "result": "blocked",
     "code": "RETROSPECTIVE_RECORD_MISSING",
     "mission_id": "...",
     "mission_slug": "...",
     "blocked_reason": "No retrospective record found for this mission. Author one with: spec-kitty retrospect create --mission <handle>",
     "exit_code": 1
   }
   ```
3. **Legacy fabrication path**: add `--fabricate-empty` flag. When set AND record is missing:
   - Generate a minimal record with empty `helped/not_helpful/gaps/proposals` lists
   - `findings_status = "ran_no_findings"` (per FR-014 invariant — WP03's writer enforces)
   - `provenance.kind = "synthesize_fabricate"`, `provenance.command = "agent retrospect synthesize --fabricate-empty"`
   - `policy_source` from the resolver
   - Actor attribution from `cli_actor()`
   - Write via `write_record(..., mode="error", ...)` — record must not exist, else error
   - Emit `RetrospectiveCaptured(provenance_kind="explicit_create")` — synthesize_fabricate is a sub-flavor of explicit-create for event purposes (matches contracts).
4. Other modes (`--preview`, `--apply <id>`) unchanged from current behavior.
5. Test both paths: default-error AND `--fabricate-empty` produces a writer-validated record.

**Files**:
- `src/specify_cli/cli/commands/agent_retrospect.py` (extend, ~120 lines)

**Validation**:
- [ ] Default `synthesize` on missing record → `RETROSPECTIVE_RECORD_MISSING` exit 1
- [ ] `--fabricate-empty` on missing record → record with `findings_status=ran_no_findings` + `provenance.kind=synthesize_fabricate`
- [ ] Writer rejects a `synthesize_fabricate` record with `findings_status=has_findings` (defense-in-depth from WP03 T014)
- [ ] `--preview` and `--apply` still work as before

---

### T029 — CLI tests + JSON contract assertions

**Purpose**: Lock all CLI surfaces with byte-for-byte JSON contract assertions.

**Steps**:

1. Create `tests/cli/commands/test_retrospect.py` with classes:
   - `TestCreateCommand` — success, RecordExists error, MissionNotCompleted error, AmbiguousSelector error, --overwrite, --update, --json
   - `TestBackfillCommand` — dry-run, real run, since/until filtering, mission filter, emit-skipped/failures, JSON shape
   - `TestSummaryReadOnlyInvariant` — assert no filesystem mutation; assert 4-state output
   - `TestSynthesizeTighteningDefault` — missing record error
   - `TestSynthesizeFabricateEmpty` — flag preserves legacy behavior with the invariant enforced
2. Use Typer's `CliRunner` for in-process testing. Set up `tmp_path` mission directories matching WP02 fixture format.
3. For each contract assertion, load a JSON shape from `kitty-specs/retrospective-default-policy-01KS049J/contracts/retrospect-cli.contract.md` (parse from the contract doc or hand-replicate the shape in test data).

**Files**:
- `tests/cli/commands/test_retrospect.py` (new, ~400 lines)

**Validation**:
- [ ] `uv run pytest tests/cli/commands/test_retrospect.py -q` exits 0
- [ ] Coverage on `src/specify_cli/cli/commands/retrospect.py` and the touched portions of `agent_retrospect.py` ≥ 90%
- [ ] All documented JSON contract shapes have a corresponding assertion

---

## Definition of Done

- [ ] All 6 subtasks complete
- [ ] `uv run pytest tests/cli/commands/test_retrospect.py tests/retrospective/ -q` exits 0
- [ ] `uv run ruff check src/specify_cli/cli/commands/ tests/cli/commands/test_retrospect.py` exits 0
- [ ] `spec-kitty retrospect --help` lists `create`, `backfill`, `summary`
- [ ] `spec-kitty retrospect create --help`, `backfill --help`, `summary --help` show documented flags
- [ ] Coverage on touched files ≥ 90% (NFR-004)
- [ ] No edits outside `owned_files`

## Risks & Reviewer Guidance

- **Owned-files coordination**: WP05 touches `agent_retrospect.py` (existing surface). Coordinate with WP03 which also touches `summary.py` for the classifier. Resolution: this WP edits `agent_retrospect.py` for the `synthesize` tightening and the `summary` output shape extension; WP03 owns `summary.py` for the classifier logic itself.
- **Backfill at scale (R-3)**: a repo with 200+ missions could take noticeable time. Mitigation: progress bar in non-JSON mode; JSON output is a single aggregate (don't buffer per-mission objects in memory unnecessarily — stream or use generators).
- **Concurrency (R-2)**: parallel `retrospect create` on the same mission could race. Out of scope for this WP; document as a known limitation in `quickstart.md`.
- **Reviewer**: verify the back-compat path: `spec-kitty agent retrospect summary` (legacy invocation) still works AND surfaces the new `findings_status` keys.

## Next

After this WP merges, WP07 (Docs/Skills) documents the new commands.

Implementation command:

```bash
spec-kitty agent action implement WP05 --agent claude
```

## Activity Log

- 2026-05-19T16:26:01Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=44928 – Started implementation via action command
- 2026-05-19T16:46:11Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=44928 – Moved to for_review
- 2026-05-19T16:46:28Z – claude:claude-sonnet-4-6:reviewer-renata:reviewer – shell_pid=53834 – Started review via action command
- 2026-05-19T16:54:04Z – claude:claude-sonnet-4-6:reviewer-renata:reviewer – shell_pid=53834 – Moved to planned
- 2026-05-19T16:54:38Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=55085 – Started implementation via action command
- 2026-05-19T17:05:31Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=55085 – Cycle 2: fixed synthesize_fabricate provenance gap AND emit-skipped dead-flag. End-to-end test verifies the written record provenance.kind; emit_skipped emits per-mission RetrospectiveSkipped events on backfill skips. 91 tests pass, retrospect.py=99% coverage.
- 2026-05-19T17:06:01Z – claude:claude-sonnet-4-6:reviewer-renata:reviewer – shell_pid=57311 – Started review via action command
- 2026-05-19T17:10:09Z – claude:claude-sonnet-4-6:reviewer-renata:reviewer – shell_pid=57311 – Review passed cycle 2: Both blockers resolved. Blocker 1: _create_empty_retrospective_record correctly produces GenRetrospectiveRecord(provenance.kind=synthesize_fabricate), written via write_gen_record, event emitted with provenance_kind=explicit_create; two new tests confirm disk round-trip and writer rejects synthesize_fabricate+has_findings. Blocker 2: emit_skipped no longer dead -- _maybe_emit_skip closure correctly gates on emit_skipped and not dry_run with skip_reason_source=cli_flag (in-contract enum value); three tests confirm writes, non-write, and dry-run-suppressed cases. 91 tests pass (495 total suite). retrospect.py=99% coverage. agent_retrospect.py WP05-touched portions covered; pre-existing paths are the gap. Ruff clean. Help shows 3 commands. RetrospectiveSkipped semantic stretch accepted: skip_reason_source=cli_flag is in-contract enum.
- 2026-05-19T18:05:04Z – claude:claude-sonnet-4-6:reviewer-renata:reviewer – shell_pid=57311 – Moved to done
