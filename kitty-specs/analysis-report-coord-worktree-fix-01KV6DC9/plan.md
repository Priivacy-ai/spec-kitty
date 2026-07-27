# Implementation Plan: Analysis Report Coord-Worktree Fix & Recovery UX

**Branch**: `fix/analysis-report-coord-worktree-fix` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `kitty-specs/analysis-report-coord-worktree-fix-01KV6DC9/spec.md`

## Summary

Fix three root causes that block `spec-kitty agent action implement` when a
coordination-worktree topology is active. The write-path in `record_analysis()`
is decoupled from the coord-aware read-path resolver so it always targets the
main-checkout mission directory. A new named reason code is added to
`check_analysis_report_current()` for the carrier-format case, and
`_require_current_analysis_report()` branches on reason codes to emit exact
recovery commands. The `spec-kitty.analyze` skill source template is updated to
document that `record-analysis` is the required persistence step.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: typer (CLI framework), rich (console output), ruamel.yaml (frontmatter parsing), pathlib (path resolution)  
**Storage**: File-based artifacts only (`analysis-report.md` in `kitty-specs/<mission>/`)  
**Testing**: pytest with ≥90% line coverage on modified modules; mypy --strict zero errors; ruff zero warnings  
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10+)  
**Project Type**: Single Python package (`src/specify_cli/`)  
**Performance Goals**: N/A — CLI tool, no latency SLA on error path  
**Constraints**: Zero ruff/mypy errors; outer-wrapper format (`artifact_type: spec-kitty.analysis-report`) remains sole accepted format at the gate; fix scope is limited to four surfaces; no broader `resolve_mission_read_path` refactoring  
**Scale/Scope**: Four targeted changes across three existing modules and one source template

## Charter Check

- ✅ **DIRECTIVE_001 (Architectural Integrity)**: The fix preserves component boundaries — read-path resolution remains in `_find_feature_directory()`; write-path anchoring is a local override in `record_analysis()` only, not a new abstraction.
- ✅ **DIRECTIVE_003 (Decision Documentation)**: The reason-code constant `ANALYSIS_REPORT_REASON_CARRIER_FORMAT` is named at the module level with inline rationale. The architectural decision to keep dual reasons (generic + carrier-specific) is documented in `research.md`.
- ✅ **DIRECTIVE_010 (Specification Fidelity)**: All six FRs map 1:1 to implementation concerns. No deviation from the spec.
- ✅ **Sonar complexity ceiling (15)**: `check_analysis_report_current()` gains one additional branch; current function complexity is well below 15. No extraction needed.
- ✅ **No suppressions**: No `# noqa`, `# type: ignore`, or per-file ignore additions are introduced.

## Project Structure

### Documentation (this mission)

```
kitty-specs/analysis-report-coord-worktree-fix-01KV6DC9/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (reason-code taxonomy)
├── contracts/
│   └── error-recovery-contract.md   # Phase 1 output (error message format contract)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (affected surfaces)

```
src/specify_cli/
├── analysis_report.py                        # IC-01, IC-02: new reason constant + carrier-detection branch
└── cli/commands/agent/
    ├── mission.py                            # IC-01: write-path anchor fix in record_analysis()
    └── workflow.py                           # IC-03: recovery-message branching in _require_current_analysis_report()

src/doctrine/missions/mission-steps/software-dev/
└── analyze/prompt.md                         # IC-04: document record-analysis as required persistence step

tests/specify_cli/
└── test_analysis_report.py                   # Unit tests for IC-01 (coord-worktree write) + IC-02 (carrier detection)
tests/specify_cli/cli/commands/agent/
└── test_record_analysis_coord_worktree.py    # New: integration tests for IC-01
tests/architectural/
└── test_no_legacy_terminology.py             # Existing gate; verify skill template update passes
```

**Structure Decision**: Single Python package — all changes are within `src/specify_cli/` and the doctrine source template. No new modules; all changes are additive to existing files.

## Implementation Concern Map

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Write-Path Anchor in `record_analysis()`

- **Purpose**: Decouple `record_analysis()`'s write destination from the coord-aware read-path resolver so the command always writes to the main-checkout mission directory, eliminating the `spec.md not found` failure under coord-worktree topology.
- **Relevant requirements**: FR-001, FR-002
- **Affected surfaces**:
  - `src/specify_cli/cli/commands/agent/mission.py` — `record_analysis()` function (approx. line 1784–1835): after `_find_feature_directory()` resolves the mission (used for placement-ref and dirty-tree preflight), derive the write destination via the **topology-blind** `primary_feature_dir_for_mission(repo_root, resolved_feature_dir.name)` and pass it to `write_analysis_report()` instead of the resolved coord path. Do **not** use `candidate_feature_dir_for_mission` — it is topology-aware and returns the coord worktree, which would reproduce the bug.
  - `src/specify_cli/analysis_report.py` — `write_analysis_report()` and `collect_input_artifact_hashes()` are unchanged; the fix is at the caller.
- **Sequencing/depends-on**: none — this concern is independent.
- **Risks**: `_find_feature_directory()` is still called for the placement ref and dirty-tree preflight; the write-destination override must happen strictly after those uses so neither preflight regresses. Test coverage must include a coord-worktree fixture where `spec.md` is absent from the coord path but present in the main checkout.

### IC-02 — Named Reason Code for Carrier-Format Files

- **Purpose**: Add a distinct, stable named reason constant (`ANALYSIS_REPORT_REASON_CARRIER_FORMAT`) to `analysis_report.py` and detect the carrier-format case in `check_analysis_report_current()` before the generic artifact-type mismatch check, so downstream error handlers can branch on a specific signal rather than a catch-all string.
- **Relevant requirements**: FR-003, C-004
- **Affected surfaces**:
  - `src/specify_cli/analysis_report.py` — add module-level constant alongside existing reason strings; add carrier-detection branch in `check_analysis_report_current()` between the frontmatter-parse success and the `artifact_type` equality check (detection: `frontmatter.get("schema") == FINDINGS_SCHEMA_V1`).
- **Sequencing/depends-on**: none — this concern is independent of IC-01 and can be developed in parallel.
- **Risks**: The new branch must be ordered before the generic `artifact_type` check so a carrier-format file never falls through to the generic reason. Existing tests for `invalid_analysis_report_artifact_type` must remain valid for files that are neither outer-wrapper nor carrier (e.g., arbitrary frontmatter).

### IC-03 — Recovery-Message Branching in `_require_current_analysis_report()`

- **Purpose**: Replace the single-path error output with reason-code-specific branches that emit exact, copy-pasteable recovery commands for the carrier-format case, the missing-report case, and the stale case — so an agent reading the error alone can identify and run the next command without inspecting source code.
- **Relevant requirements**: FR-004, FR-005, NFR-003
- **Affected surfaces**:
  - `src/specify_cli/cli/commands/agent/workflow.py` — `_require_current_analysis_report()` (approx. line 1072–1087): branch on `analysis_freshness.reason` to emit distinct messages. Carrier-format branch emits: `"Recovery: spec-kitty agent mission record-analysis --mission <slug> --input-file <path>"`. Missing-report branch emits the two-step sequence. Stale branch retains the existing artifact-name list.
- **Sequencing/depends-on**: IC-02 (the new reason constant must be importable before the branching logic can reference it).
- **Risks**: The `mission_slug` is already available at the call site (passed as the third argument); the `path` for the carrier-format recovery command comes from `analysis_freshness.path`. Test coverage must include each new branch.

### IC-04 — `spec-kitty.analyze` Skill Source Template Update

- **Purpose**: Add an explicit note to the analyze skill's persistence step documenting that `record-analysis` is the required persistence mechanism and that writing `analysis-report.md` directly bypasses format wrapping and will be rejected at the implement gate — closing the documentation gap that led to the manual-write workaround.
- **Relevant requirements**: FR-006, C-003
- **Affected surfaces**:
  - `src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md` — section 7 ("Persist Report Artifact"): append a caution note after the existing `record-analysis` command examples.
- **Sequencing/depends-on**: none — documentation change; independent of all code concerns.
- **Risks**: The change propagates to all 19 agent directories only via `spec-kitty upgrade`. Running `spec-kitty upgrade` is a post-implementation step, not part of this mission's implementation WPs. The terminology guard (`tests/architectural/test_no_legacy_terminology.py`) must pass after the template update.
