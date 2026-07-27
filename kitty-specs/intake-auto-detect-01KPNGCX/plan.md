# Implementation Plan: Intake Auto-Detect from Harness Plan Artifacts

**Branch**: `main` | **Date**: 2026-04-20 | **Spec**: [spec.md](spec.md)  
**Mission**: `intake-auto-detect-01KPNGCX` | **Issue**: #703

---

## Summary

Add `spec-kitty intake --auto` which scans known harness plan-artifact locations and ingests the first (or user-selected) match without requiring an explicit file path. Backed by a new `intake_sources.py` module populated only from a verified research deliverable (`docs/reference/agent-plan-artifacts.md`). Two sequential work packages: WP01 produces the research deliverable and the scan module; WP02 adds the `--auto` flag to the CLI and all tests.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: typer, rich, pyyaml, pathlib, sys (all existing)  
**Storage**: Filesystem only — `.kittify/mission-brief.md`, `.kittify/brief-source.yaml`  
**Testing**: pytest + `typer.testing.CliRunner` + `tmp_path` fixtures  
**Target Platform**: macOS / Linux / Windows (cross-platform `pathlib.Path`)  
**Project Type**: Single Python CLI project  
**Performance Goals**: Scan completes under 200 ms (filesystem `Path.exists()` stat calls only; no subprocess)  
**Constraints**: No user-configurable scan paths; no subprocess invocations in scan logic; `HARNESS_PLAN_SOURCES` active entries from Verified-* confidence only

---

## Charter Check

No charter file present. Section skipped.

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/intake-auto-detect-01KPNGCX/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
└── tasks.md             ← /spec-kitty.tasks output (not yet created)
```

### Source Code (repository root)

```
src/specify_cli/
├── intake_sources.py                    ← NEW (WP01)
├── mission_brief.py                     ← MODIFY: add source_agent param (WP02)
└── cli/commands/
    └── intake.py                        ← MODIFY: add --auto flag (WP02)

docs/reference/
└── agent-plan-artifacts.md              ← NEW (WP01)

tests/specify_cli/
├── test_intake_sources.py               ← NEW (WP02)
└── cli/commands/
    └── test_intake.py                   ← NEW (WP02)
```

**Structure Decision**: Single project. All changes are additive (new module + two targeted modifications to existing modules + two test files).

---

## Work Packages

### WP01 — Research Deliverable & Scan Module

**Goal**: Produce the canonical harness reference document and the `intake_sources.py` module populated from verified entries.

**Deliverables**:
1. `docs/reference/agent-plan-artifacts.md` — for every harness (13 total), document: plan mode, artifact path(s), filename pattern, user-configurable, confidence, source, and `source_agent` mapping value. Research method priority: official docs → GitHub source → empirical test → community reports.
2. `src/specify_cli/intake_sources.py` — module containing:
   - `HARNESS_PLAN_SOURCES: list[tuple[str, str | None, list[str]]]` — priority-ordered list; Verified-* entries active, Inferred/Unknown in commented TODO blocks
   - `scan_for_plans(cwd: Path) -> list[tuple[Path, str, str | None]]` — returns `(file_path, harness_key, source_agent)` for each existing file found, in declaration order; silently skips non-existent or unreadable paths

**Acceptance**:
- `agent-plan-artifacts.md` covers all 13 harnesses with a confidence level for each
- `HARNESS_PLAN_SOURCES` has active entries only for Verified-docs or Verified-empirical harnesses; lower-confidence entries are in commented-out TODO blocks (empty active list is a valid outcome if none are verified)
- `scan_for_plans(cwd)` returns an empty list on an empty directory, not an exception

**Depends on**: Nothing (first WP)

---

### WP02 — CLI Implementation & Tests

**Goal**: Wire `--auto` into `spec-kitty intake`, extend `write_mission_brief()`, and add full test coverage.

**Deliverables**:

1. **`src/specify_cli/mission_brief.py`** — add `source_agent: str | None = None` kwarg to `write_mission_brief()`. When `source_agent` is not None, include it in the `source_data` dict written to `brief-source.yaml`; when None, omit the key entirely (do not write `source_agent: null`).

2. **`src/specify_cli/cli/commands/intake.py`** — add `--auto` flag:
   - Mutual exclusion: if `path` and `auto` are both set, print usage error and `raise typer.Exit(1)` before any scan
   - When `--auto`: call `scan_for_plans(Path.cwd())`
     - 0 results → print no-match message, `raise typer.Exit(1)`
     - 1 result → print `BRIEF DETECTED: <path> (source: <harness-name>)`, check `--force`, call `write_mission_brief(..., source_agent=<value>)`, exit 0
     - 2+ results → print numbered candidate list; if `sys.stdin.isatty()` prompt for selection; if not TTY print to stderr and `raise typer.Exit(1)`
   - `--force` interacts with `--auto` the same way it does with explicit-path intake (block if brief exists and no `--force`)

3. **`tests/specify_cli/test_intake_sources.py`** — unit tests for scan logic:
   - Empty `HARNESS_PLAN_SOURCES` → empty result
   - Single matching file → correct `(path, harness_key, source_agent)` returned
   - Multiple matching files across harnesses → all returned in declaration order
   - Non-existent paths silently skipped
   - Directory at candidate path skipped (not a file)
   - Unreadable file silently skipped

4. **`tests/specify_cli/cli/commands/test_intake.py`** — CLI tests using `CliRunner` + `tmp_path`:
   - `--auto` single match → exit 0, `BRIEF DETECTED` in output, `brief-source.yaml` has `source_agent`
   - `--auto` single match, existing brief, no `--force` → exit 1 with "already exists" message
   - `--auto` single match, existing brief, `--force` → exit 0, overwrites
   - `--auto` multiple matches, TTY (mock `sys.stdin.isatty` → True) → prompts for selection, ingests choice
   - `--auto` multiple matches, non-TTY (mock `sys.stdin.isatty` → False) → exit 1, candidates on stderr
   - `--auto` no matches → exit 1 with no-match message
   - `--auto` + positional path → exit 1 with usage error, no files written
   - `--show` unaffected: still works after `--auto` changes
   - Manual intake (`intake <path>`) → `brief-source.yaml` has no `source_agent` key at all

**Acceptance**:
- `ruff check src/specify_cli/intake_sources.py src/specify_cli/mission_brief.py src/specify_cli/cli/commands/intake.py` passes
- `pytest tests/specify_cli/test_intake_sources.py tests/specify_cli/cli/commands/test_intake.py -v` passes
- Existing non-`--auto` intake tests (if any) still pass
- `spec-kitty intake --help` shows `--auto` flag

**Depends on**: WP01 (needs `intake_sources.py` and `scan_for_plans` to exist)

---

## Complexity Tracking

No charter violations. All changes are additive and narrowly scoped.

---

## Gate Check

| Gate | Status |
|------|--------|
| No NEEDS CLARIFICATION markers remain | ✅ |
| All requirements testable | ✅ |
| Sequential WP dependency documented | ✅ |
| Configurable paths explicitly out of scope | ✅ |
| Research precedes implementation (C-002) | ✅ enforced by WP ordering |

---

## Branch Contract (repeated)

- **Current branch**: `main`
- **Planning/base branch**: `main`
- **Merge target**: `main`
- `branch_matches_target`: true ✅
