---
work_package_id: WP06
title: Structured findings carrier (analysis-findings/v1) + verdict derivation
dependencies: []
requirement_refs:
- FR-004
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tooling-stability-guard-coherence-01KTRC04
base_commit: add42e46c5442ecd2d1c8c00015fab3fa5c727f1
created_at: '2026-06-10T14:51:25.743057+00:00'
subtasks:
- T023
- T024
- T025
- T026
- T027
phase: Phase 1 - Independent lanes
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "92560"
history:
- at: '2026-06-10T11:47:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/analysis_report.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/analysis_report.py
- src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Structured findings carrier

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; pick the best implementer match if none assigned.

---

## Objectives & Success Criteria
Fix #1819 at the root: the recorder substring-counts severity keywords in report PROSE (`infer_verdict`'s
literal "BLOCK" / "READY FOR IMPLEMENTATION" magic strings; `infer_issue_counts`' `\bCRITICAL\b` fallback).
- Define the **`analysis-findings/v1` frontmatter schema** (see `data-model.md` §2) — **REUSING the existing canonical severity vocabulary** (binding: `charter_runtime/lint/findings.py::SEVERITY_ORDER` encodes the ladder; the codebase has 8+ Severity models — minting a 9th is PROHIBITED; import/alias, don't redefine).
- `record-analysis` computes verdict + counts from the **validated frontmatter only**: any critical|high → `blocked`; else `ready`. Prose NEVER read. `verdict_hint` disagreement → loud error.
- **Write-path-only loud failure** (debby RISK-3): missing/malformed carrier on RECORD → structured error; the READ/freshness path (`check_analysis_report_current`, accept/review gates) tolerates pre-v1 legacy reports as `verdict: unknown` + remediation hint — never wedges existing missions, never fabricates.
- **Delete** `infer_verdict` + `infer_issue_counts` substring logic after cutover (deletions ledger).
- Update the **analyze command template** (SOURCE doctrine — your owned template file; agent copies regenerate via upgrade) so analyzing agents emit the frontmatter.
- **Done when:** C-FIND-1/2/3 repros pass (#1819).

## Context & Constraints
- Design (absolute): `kitty-specs/tooling-stability-guard-coherence-01KTRC04/{spec.md (FR-004), plan.md (IC-05), data-model.md §2, contracts/ (C-FIND-1/2/3)}`.
- Live repro material: 01KTPKST's findings F-006 — a clean report scored `blocked` because its prose said "no CRITICAL, no HIGH".
- The record-analysis CLI call-site lives in WP05-owned `cli/commands/agent/mission.py` — **keep ALL logic changes inside `analysis_report.py`** (the recorder function computes the verdict); if a one-line call-site adjustment is unavoidable, make it minimal with an out-of-map rationale and coordinate (WP05 may be in flight in parallel).
- Doctrine prose touched → run `pytest tests/architectural/test_no_legacy_terminology.py`.

## Branch Strategy
- Planning base / merge target: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance

### T023 — Schema (severity reuse)
- Implement the `analysis-findings/v1` frontmatter contract in `analysis_report.py`: `schema`, `findings[] {id, severity, category, summary}`, `counts`, optional `verdict_hint`. Severity values validate against the REUSED canonical vocabulary (import `SEVERITY_ORDER` or its enum; alias if a thin local name is needed — no new value set). `counts` must equal the findings tally.

### T024 — Verdict from structure; write-path-only loud failure
- `write_analysis_report`/record path: parse + validate the frontmatter; compute verdict (`blocked` iff any critical|high else `ready`); hint-disagreement → loud error. Read/freshness path: pre-v1 report (no carrier) → `verdict: unknown` + remediation hint, NO exception; verify `check_analysis_report_current` and the accept/review consumers tolerate `unknown`.

### T025 — Delete the substring logic
- Remove `infer_verdict` + `infer_issue_counts` (and their tests) after the structured path is green. `rg "READY FOR IMPLEMENTATION|\\bBLOCK\\b" src/specify_cli/analysis_report.py` → zero magic strings.

### T026 — Analyze template (SOURCE)
- Update `src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md` (and the persist-report step) to instruct agents: emit the frontmatter block with findings+severities; prose is presentation. Terminology guard green.

### T027 — C-FIND regression tests
- (1) clean frontmatter + scary prose ("CRITICAL", "BLOCK") → `ready`; (2) one critical row + reassuring prose → `blocked`; (3) unknown severity / counts≠tally / hint disagreement → loud structured error on write; (4) legacy report on the read path → `unknown`, no exception.

## Definition of Done
- C-FIND-1/2/3 + legacy-read tests green; substring logic deleted; terminology guard green; `ruff`+`mypy` clean.

## Risks & Mitigations
- *Wedging legacy missions* → the read-path tolerance test is mandatory (debby RISK-3).
- *9th severity model* → import-only; reviewer greps for a new enum definition.

## Review Guidance
- Recommended: **reviewer-renata**. Grep: no new Severity enum; no magic strings; write/read path asymmetry correct.

## Activity Log
- 2026-06-10T11:47:55Z – system – Prompt created.
- 2026-06-10T15:03:00Z – user – shell_pid=40446 – analysis-findings/v1 frontmatter carrier: verdict+counts derive from structured findings only (any high|critical -> blocked, else ready); prose never read. Severity vocabulary REUSED from charter_runtime/lint/findings.py::SEVERITY_ORDER (no 9th enum). Write-path-only loud failure (FindingsCarrierError) on unknown severity / counts!=tally / verdict_hint disagreement; legacy reports with no carrier record verdict:unknown with no exception; read/freshness path tolerates them. infer_verdict/infer_issue_counts/_count_from_patterns + magic strings DELETED. analyze template SOURCE emits the carrier. Gates: 90 targeted tests pass, ruff clean, mypy clean, terminology guard green. Commit 62e76f2e9.
- 2026-06-10T15:17:02Z – claude:opus:reviewer-renata:reviewer – shell_pid=92560 – Started review via action command
- 2026-06-10T15:26:30Z – user – shell_pid=92560 – Review passed (reviewer-renata): SEVERITY_ORDER reused; C-FIND-1 both ways; write/read asymmetry; substring logic deleted+guarded; 15/15 + terminology green
