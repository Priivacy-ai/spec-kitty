# Analysis Report Coord-Worktree Fix & Recovery UX

## Overview

**Mission ID**: 01KV6DC9Y5FJ9FCYJMM1KA09XK  
**Mission Type**: software-dev  
**Status**: Proposed  
**GitHub Issue**: #1989 (related: #1981)

When a mission uses a coordination worktree, the `record-analysis` command
resolves the mission directory to the coord-worktree path — where `spec.md` is
absent — and fails before it can write the analysis report. Agents forced to
work around this write `analysis-report.md` directly in the intermediate carrier
format, which the implement gate rejects with an opaque error code and no
recovery guidance. Missions are fully blocked.

This mission fixes three root causes: (1) the write-path resolution anchoring
defect in `record-analysis`; (2) the missing named error code for
carrier-format files at the implement gate; and (3) the absent recovery
guidance in both the gate error output and the `spec-kitty.analyze` skill.

---

## User Scenarios & Testing

### Primary Scenario — record-analysis succeeds with coord worktree active

**Actor**: An AI agent executing a multi-WP software-dev mission that has a
coordination worktree.

**Trigger**: The agent completes `/spec-kitty.analyze` and pipes the output to
`spec-kitty agent mission record-analysis --mission <slug>`.

**Happy path**:
1. Agent runs `/spec-kitty.analyze` → receives a report body with the
   `analysis-findings/v1` carrier frontmatter prepended.
2. Agent pipes the report body to `record-analysis`.
3. `record-analysis` resolves the mission directory to the **main-checkout**
   path, finds `spec.md`, `plan.md`, and `tasks.md` there, and writes
   `analysis-report.md` in the accepted outer-wrapper format.
4. Agent runs `spec-kitty agent action implement WP01` → the implement gate
   reads `analysis-report.md`, finds `artifact_type: spec-kitty.analysis-report`,
   and passes. Implementation proceeds normally.

**Primary exception — carrier-format file already written**:
1. Agent previously wrote `analysis-report.md` directly in carrier format
   (due to a prior `record-analysis` failure).
2. Agent runs `spec-kitty agent action implement WP01`.
3. Implement gate detects the carrier format and emits a distinct error code
   plus an exact runnable recovery command.
4. Agent runs the recovery command → `analysis-report.md` is rewritten in the
   accepted outer-wrapper format.
5. Agent re-runs implement → gate passes.

**Key rule that must always hold**: `record-analysis` must write to the
main-checkout mission directory regardless of which worktree context the
command is invoked from. The implement gate must never accept a file in carrier
format, even if technically parseable.

---

### Secondary Scenario — missing analysis report

**Actor**: An agent that has not run `/spec-kitty.analyze` yet.

**Trigger**: Agent runs `spec-kitty agent action implement WP01`.

**Expected**: Gate emits a clear, two-step recovery command sequence:
first `/spec-kitty.analyze`, then `record-analysis`.

---

### Secondary Scenario — analyst reads the spec-kitty.analyze skill

**Actor**: An AI agent or human reading the `spec-kitty.analyze` skill to
understand how to persist an analysis report.

**Expected**: The skill explicitly states that `record-analysis` is the
required persistence step and that writing `analysis-report.md` directly
is not supported and will be rejected at the implement gate.

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | `record-analysis` must resolve the mission directory to the main-checkout path for its write operation, regardless of whether a coordination worktree exists for the mission. | Proposed |
| FR-002 | `analysis-report.md` written by `record-analysis` must always use the outer-wrapper format (`artifact_type: spec-kitty.analysis-report`), including when a coord worktree is active. | Proposed |
| FR-003 | When the implement gate reads an `analysis-report.md` that contains an `analysis-findings/v1` carrier frontmatter instead of the outer-wrapper format, it must emit a distinct named error code that is different from the generic artifact-type mismatch code. | Proposed |
| FR-004 | When the implement gate emits the carrier-format error (FR-003), it must include an exact, copy-pasteable recovery command that rewrites the file into the accepted format without requiring the agent to re-run the full analysis. | Proposed |
| FR-005 | When `analysis-report.md` is missing entirely, the implement gate must emit a two-step recovery sequence: first run `/spec-kitty.analyze`, then pipe the output to `record-analysis`. | Proposed |
| FR-006 | The `spec-kitty.analyze` skill source template must document that `record-analysis` is the required persistence step for analysis output and that writing `analysis-report.md` directly is unsupported and will be rejected by the implement gate. | Proposed |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | `record-analysis` must succeed from any invocation context (primary checkout, lane worktree, or coord worktree) as long as a valid `--mission` handle is provided and the mission's main-checkout directory exists. | 100% of context combinations tested pass | Proposed |
| NFR-002 | New and modified code paths must maintain the project's ≥90% test coverage requirement; regression tests must cover the coord-worktree resolution path and the carrier-format gate branch. Enforcement surface is the CI/Sonar new-code-coverage gate — no separate manual coverage step is required in a work package. | ≥90% line coverage on modified modules, enforced by the CI new-code-coverage gate | Proposed |
| NFR-003 | The implement gate error messages must be actionable: an agent reading the message alone (without the source code) must be able to identify the exact command to run to recover. Measured by the error message including a complete runnable command. | 100% of new error branches include a runnable command | Proposed |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | The outer-wrapper format (`artifact_type: spec-kitty.analysis-report`) remains the sole accepted format at the implement gate. Silent dual-format acceptance — where the gate would pass carrier-format files without conversion — is explicitly prohibited, as it would mask the root cause and create format-drift risk. | Proposed |
| C-002 | The fix to `record_analysis()` write-path resolution must not alter the read-path behavior of other commands that use the same mission-directory resolution primitive. Only the write destination of `record-analysis` changes. | Proposed |
| C-003 | In this (the spec-kitty source) repository, the only deliverable is the edit to the canonical source template (`src/doctrine/.../analyze/prompt.md`); direct edits to generated agent-directory copies are prohibited. Propagation to consumer-project agent directories happens **downstream**, when those projects run `spec-kitty upgrade` — it is not performed in this repo. (This source repo does not carry per-agent analyze copies, so no `spec-kitty upgrade` runs as part of this mission.) | Proposed |
| C-004 | The new named error code for the carrier-format case must be a stable string constant defined in `analysis_report.py` alongside the existing reason strings, not an inline literal. Any existing code that matches on `invalid_analysis_report_artifact_type` must not silently break; the new code is additive. | Proposed |

---

## Success Criteria

1. An agent running `record-analysis` on a mission with an active coordination
   worktree completes successfully in 100% of cases where the mission's
   main-checkout directory is present and contains the required planning
   artifacts.

2. An agent that previously wrote `analysis-report.md` in carrier format can
   recover and unblock implementation by running a single command surfaced in
   the gate error output — without re-running the full analysis.

3. An agent reading the `spec-kitty.analyze` skill finds an explicit statement
   that `record-analysis` is the required persistence step, preventing the
   class of manual-write workarounds that produced this defect.

4. Zero regressions: missions without a coordination worktree continue to
   function identically; the implement gate error behavior for missing and
   stale reports is unchanged.

---

## Assumptions

- The mission's `spec.md`, `plan.md`, and `tasks.md` are committed and present
  in the main-checkout mission directory. If they are not, `record-analysis`
  should continue to fail with its existing artifact-missing error (not the
  coord-worktree error).
- The `spec-kitty.analyze` skill is currently the only skill that instructs
  agents to produce analysis-report output; no other skill creates
  `analysis-report.md` directly.
- The carrier-format detection in `check_analysis_report_current()` can
  reliably distinguish carrier-format files from outer-wrapper files by the
  presence of the `schema: analysis-findings/v1` key in the frontmatter, since
  the outer-wrapper uses `artifact_type` (not `schema`) as its identity key.
- The `record-analysis --input-file` flag already accepts a file path argument,
  making it usable as a recovery command with an existing carrier-format file
  as input.

---

## Out of Scope

- Broader refactoring of `resolve_mission_read_path()` or other commands that
  use the same read-path resolution primitive (tracked separately via #1981).
- Changes to how the coordination worktree is populated or which files it
  contains.
- Auto-conversion of carrier-format files without explicit agent action (the
  gate must remain a hard check; recovery is explicit and agent-initiated).
- Changes to the `analysis-findings/v1` carrier schema or the outer-wrapper
  schema itself.
