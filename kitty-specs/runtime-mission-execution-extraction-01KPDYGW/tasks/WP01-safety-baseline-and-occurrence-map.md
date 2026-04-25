---
work_package_id: WP01
title: Safety Baseline + Occurrence Map
dependencies: []
requirement_refs:
- FR-011
- FR-012
- FR-015
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
base_commit: ce0438aa33dcf873f5ee84e2f51ea5c2ee44e642
created_at: '2026-04-22T20:40:46.526530+00:00'
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:claude-sonnet-4-6:python-pedro:reviewer"
shell_pid: "684364"
history:
- date: '2026-04-22T20:03:51Z'
  author: architect-alphonso
  event: created
agent_profile: python-pedro
authoritative_surface: tests/regression/runtime/
execution_mode: code_change
owned_files:
- tests/regression/runtime/fixtures/**
- tests/regression/runtime/__init__.py
- kitty-specs/runtime-mission-execution-extraction-01KPDYGW/occurrence_map.yaml
- kitty-specs/runtime-mission-execution-extraction-01KPDYGW/research.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading further, load the assigned agent profile for this session:

```
/ad-hoc-profile-load python-pedro
```

This profile scopes your role, boundaries, and self-review gates. Do not begin implementation until the profile is active.

---

## Objective

Establish the safety baseline and bulk-edit artefact for the runtime extraction mission before any source code moves. This WP does NOT move any code — it only audits, captures, and enumerates.

**Why first**: Every subsequent WP depends on these outputs. The regression snapshots are the behavioral anchor that proves extraction is safe. The occurrence map is the canonical list of every file that must be updated across WP05/WP06/WP09/WP10.

---

## Context

**Mission**: `runtime-mission-execution-extraction-01KPDYGW` — extracting `src/specify_cli/next/` and `src/specify_cli/runtime/` to a canonical top-level `src/runtime/` package.

**Branch**: Work in the lane worktree allocated by `spec-kitty agent action implement WP01 --agent claude`. Do not run `spec-kitty implement` manually.

**Key dependencies of this WP's output**:
- T001 audit result → shapes `PresentationSink` API in WP02
- T002+T003 fixture + snapshots → drive WP08 regression assertions
- T004 occurrence_map.yaml → drives WP05, WP06, WP09, WP10 scope

---

## Subtask T001 — Audit `runtime_bridge.py` Sync Imports

**Purpose**: Spec Assumption A3 says runtime has limited Rich/Typer usage. PR #761 added `sync/runtime_event_emitter` imports to `runtime_bridge.py`. Before anything moves to `src/runtime/`, confirm whether these imports transitively pull in `rich.*` or `typer.*`. If they do, the PresentationSink Protocol in WP02 must route them.

**Steps**:

1. Read `src/specify_cli/next/runtime_bridge.py` and identify every import from `specify_cli.sync.*`:
   ```bash
   rg "from specify_cli.sync|import specify_cli.sync" src/specify_cli/next/runtime_bridge.py
   ```

2. For each sync module imported, trace its imports:
   ```bash
   rg "^from rich|^import rich|^from typer|^import typer" \
     src/specify_cli/sync/runtime_event_emitter.py \
     src/specify_cli/sync/emitter.py \
     src/specify_cli/sync/events.py
   ```

3. Also check `runtime_bridge.py` itself for direct Rich imports:
   ```bash
   rg "^from rich|^import rich" src/specify_cli/next/runtime_bridge.py
   ```

4. Write findings to the `research.md` file in the feature dir under a new section **"## Addendum — 2026-04-22: sync import audit"**:
   - If transitive Rich found: list the exact symbols and the PresentationSink methods needed to route them
   - If no Rich found: confirm the boundary is clean — PresentationSink can be minimal (one `write_line` method)

**Files touched**: `kitty-specs/runtime-mission-execution-extraction-01KPDYGW/research.md`

**Validation**: The addendum section exists in research.md and contains an explicit verdict: "CLEAN" or "TAINTED: [symbols]".

---

## Subtask T002 — Create Reference Mission Fixture

**Purpose**: The regression harness (WP08) needs a real mission directory to run CLI commands against. Build a minimal but valid mission at `tests/regression/runtime/fixtures/reference_mission/`.

**Steps**:

1. Create the directory structure:
   ```
   tests/regression/runtime/
   ├── __init__.py
   └── fixtures/
       ├── reference_mission/
       │   ├── meta.json
       │   ├── spec.md
       │   ├── plan.md
       │   ├── tasks/
       │   │   └── WP01-baseline-work.md
       │   ├── tasks.md
       │   └── status.events.jsonl
       └── snapshots/   ← populated in T003
   ```

2. Write `meta.json` — use a static test ULID so snapshots are deterministic:
   ```json
   {
     "created_at": "2026-04-22T00:00:00+00:00",
     "friendly_name": "runtime regression reference",
     "mission_id": "01KPDYGW000000000REGRTEST1",
     "mission_number": null,
     "mission_slug": "runtime-regression-reference-01KPDYGW",
     "mission_type": "software-dev",
     "slug": "runtime-regression-reference-01KPDYGW",
     "target_branch": "kitty/mission-runtime-mission-execution-extraction-01KPDYGW"
   }
   ```

3. Write minimal `spec.md` (10 lines is enough — a placeholder header + one FR line).

4. Write minimal `plan.md` (10 lines — placeholder).

5. Write minimal `tasks.md` with one WP entry (WP01).

6. Write `tasks/WP01-baseline-work.md` with valid frontmatter (work_package_id, dependencies: [], subtasks: ["T001"]).

7. Write `status.events.jsonl` with pre-baked events that put WP01 in `in_progress` lane:
   ```json
   {"actor":"claude","at":"2026-04-22T10:00:00+00:00","event_id":"01KPDYGW000AAAA0000000PLAN","evidence":null,"execution_mode":"worktree","feature_slug":"runtime-regression-reference-01KPDYGW","force":false,"from_lane":null,"reason":null,"review_ref":null,"to_lane":"planned","wp_id":"WP01"}
   {"actor":"claude","at":"2026-04-22T10:01:00+00:00","event_id":"01KPDYGW000AAAA0000000CLMD","evidence":null,"execution_mode":"worktree","feature_slug":"runtime-regression-reference-01KPDYGW","force":false,"from_lane":"planned","reason":null,"review_ref":null,"to_lane":"claimed","wp_id":"WP01"}
   {"actor":"claude","at":"2026-04-22T10:02:00+00:00","event_id":"01KPDYGW000AAAA0000000IPRO","evidence":null,"execution_mode":"worktree","feature_slug":"runtime-regression-reference-01KPDYGW","force":false,"from_lane":"claimed","reason":null,"review_ref":null,"to_lane":"in_progress","wp_id":"WP01"}
   ```

**Files touched**: `tests/regression/runtime/__init__.py`, `tests/regression/runtime/fixtures/reference_mission/*`

**Validation**: `python -c "from specify_cli.status.store import read_events; from pathlib import Path; print(len(read_events(Path('tests/regression/runtime/fixtures/reference_mission'))))"`  → prints 3.

---

## Subtask T003 — Capture Baseline CLI JSON Snapshots

**Purpose**: Run the 4 CLI commands against the reference fixture and commit their `--json` output. These snapshots become the behavioural contract WP08 asserts against post-extraction.

**Steps**:

1. Create `tests/regression/runtime/fixtures/snapshots/` directory.

2. For each command, run against the reference mission and capture JSON output. Use `--mission runtime-regression-reference-01KPDYGW` and ensure the reference fixture is on `KITTIFY_HOME`-compatible path. Commands to run (adapt paths as needed):

   ```bash
   spec-kitty next --agent claude --mission runtime-regression-reference-01KPDYGW --json \
     > tests/regression/runtime/fixtures/snapshots/next.json

   spec-kitty agent action implement WP01 --agent claude \
     --mission runtime-regression-reference-01KPDYGW --json \
     > tests/regression/runtime/fixtures/snapshots/implement.json

   spec-kitty agent action review WP01 --agent claude \
     --mission runtime-regression-reference-01KPDYGW --json \
     > tests/regression/runtime/fixtures/snapshots/review.json

   spec-kitty merge runtime-regression-reference-01KPDYGW --json \
     > tests/regression/runtime/fixtures/snapshots/merge.json
   ```

3. Inspect each snapshot for obvious issues (empty JSON, error keys). If a command errors, investigate the fixture setup from T002 — do NOT adjust the snapshot to hide errors.

4. Add a `snapshots/README.md` documenting: when captured, against which spec-kitty version (3.2.0a4), and the normalization rules for the regression harness (strip timestamps, strip absolute paths).

**Files touched**: `tests/regression/runtime/fixtures/snapshots/*.json`, `tests/regression/runtime/fixtures/snapshots/README.md`

**Validation**: All 4 JSON files exist and are valid JSON (`python -m json.tool < file`).

---

## Subtask T004 — Generate `occurrence_map.yaml`

**Purpose**: Enumerate every internal caller of `specify_cli.next.*` and `specify_cli.runtime.*` across the entire codebase. This drives the bulk-edit classification and lets WP05, WP09, WP10 implementers work from a known-complete list rather than searching on their own.

**Steps**:

1. Search for all callers:
   ```bash
   rg "from specify_cli\.next|import specify_cli\.next|from specify_cli\.runtime|import specify_cli\.runtime" \
     src/ tests/ --include="*.py" -l | sort > /tmp/callers.txt
   cat /tmp/callers.txt
   ```

2. Categorise each file into one of four categories:
   - `cli_adapter`: files in `src/specify_cli/cli/commands/` that are being rewritten to thin adapters (WP05)
   - `shim_source`: the `src/specify_cli/next/` and `src/specify_cli/runtime/` files being converted to shims (WP06)
   - `source_caller`: other `src/` files that need import rewrites (WP09)
   - `test_caller`: `tests/` files that need import rewrites (WP10)

3. For each file, list the specific import lines being replaced. Write `occurrence_map.yaml` in the feature dir:

   ```yaml
   # occurrence_map.yaml
   # Mission: runtime-mission-execution-extraction-01KPDYGW
   # Generated: 2026-04-22
   # Schema: DIRECTIVE_035 bulk-edit occurrence map
   
   change_mode: bulk_edit
   canonical_import_prefix: "runtime"
   
   occurrences:
     cli_adapter:
       - file: "src/specify_cli/cli/commands/next_cmd.py"
         imports:
           - from: "from specify_cli.next.decision import decide_next"
             to: "from runtime.decisioning.decision import decide_next"
           # ... enumerate all import lines in this file
     shim_source:
       - file: "src/specify_cli/next/__init__.py"
         action: "convert_to_shim"
         canonical_target: "runtime"
       # ... one entry per file
     source_caller:
       - file: "src/doctrine/resolver.py"
         imports:
           - from: "..."
             to: "..."
       # ... one entry per file
     test_caller:
       - file: "tests/next/test_decision_unit.py"
         imports:
           - from: "..."
             to: "..."
       # ... one entry per file
   
   summary:
     cli_adapter_count: N
     shim_source_count: 14
     source_caller_count: N
     test_caller_count: N
     total_files: N
     total_import_lines: N
   ```

4. Verify the map is complete: every file in `/tmp/callers.txt` appears in exactly one category.

**Files touched**: `kitty-specs/runtime-mission-execution-extraction-01KPDYGW/occurrence_map.yaml`

**Validation**: `python -c "import yaml; d=yaml.safe_load(open('kitty-specs/runtime-mission-execution-extraction-01KPDYGW/occurrence_map.yaml')); print(d['summary'])"` prints a non-zero summary.

---

## Branch Strategy

Work in the execution worktree allocated by `spec-kitty agent action implement WP01 --agent claude`. Do not manually create branches or worktrees.

- **Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- **Merge target**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- Lane and worktree path: resolved by `spec-kitty agent action implement WP01 --agent claude`

**Before starting**: Assign GitHub issue [#612](https://github.com/Priivacy-ai/spec-kitty/issues/612) to the Human-in-Charge (HiC) per charter DIR-001. Use `gh issue edit 612 --add-assignee <hic-username> --repo Priivacy-ai/spec-kitty`.

---

## Definition of Done

- [ ] research.md has the sync import audit addendum with an explicit CLEAN or TAINTED verdict
- [ ] `tests/regression/runtime/fixtures/reference_mission/` exists with all required files
- [ ] All 4 snapshot JSON files exist and are valid JSON
- [ ] `occurrence_map.yaml` exists in the feature dir with all callers categorised and a complete summary section
- [ ] No source code has been moved or modified (this WP is audit-and-capture only)
- [ ] All new files are committed to the planning branch

---

## Reviewer Guidance

- Verify the occurrence_map.yaml `total_files` matches `wc -l /tmp/callers.txt`
- Open one snapshot file and confirm it is non-empty, valid JSON, and contains the expected keys for the given command
- Confirm research.md addendum exists and has an explicit verdict on Rich/Typer exposure
- Confirm NO source files in `src/specify_cli/next/` or `src/specify_cli/runtime/` were modified

## Activity Log

- 2026-04-22T20:53:36Z – claude – shell_pid=674372 – Ready for review: sync audit complete (TAINTED: rich.console.Console via lazy import chain), baseline fixture + snapshots captured, occurrence_map.yaml with 34 files across 4 categories. No source code moved.
- 2026-04-22T21:12:04Z – claude:claude-sonnet-4-6:python-pedro:reviewer – shell_pid=684364 – Started review via action command
- 2026-04-22T21:13:48Z – claude:claude-sonnet-4-6:python-pedro:reviewer – shell_pid=684364 – Review passed: TAINTED audit documented (rich.console.Console via lazy import chain, safely contained), reference mission fixture complete with 3 status events, all 4 snapshots valid JSON (3 wrapped errors with explanatory notes per spec), occurrence_map.yaml has 34 files across 4 categories with complete summary, no source code moved or modified
