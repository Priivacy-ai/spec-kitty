---
work_package_id: WP05
title: 'Class-closing guard (#2709): driver-registry-completeness + no-blind-copy lint'
dependencies:
- WP03
requirement_refs:
- FR-008
tracker_refs:
- '2709'
planning_base_branch: fix/red-handling-policy-and-drg-regression-marks
merge_target_branch: fix/red-handling-policy-and-drg-regression-marks
branch_strategy: Planning artifacts for this mission were generated on fix/red-handling-policy-and-drg-regression-marks. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/red-handling-policy-and-drg-regression-marks unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
phase: Phase 3 - Class guard (#2709 chain)
assignee: ''
agent: ''
shell_pid: "4036093"
shell_pid_created_at: "1784358506.8"
history:
- timestamp: '2026-07-17T20:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_merge_reconciliation_class_guard.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_merge_reconciliation_class_guard.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Class-closing guard (#2709)

## Objective
Close the "merge silently overwrites target-newer canonical state" defect class **by
construction**, covering BOTH loss mechanisms — not a re-run of WP01 (FR-008, SC-005).

## Fix (two non-vacuous lints in `tests/architectural/`, precedent: `test_merge_pipeline_ratchets.py` AST per-call-site lints)
- **T012 — no-blind-copy AST lint** over the `merge/` projection path: fail on any
  `write_bytes`/`write_text` of a foreign status/meta/trace source onto a target-surface path
  in `merge/` (the `write_bytes` vector — catches a regression of FR-005).
- **T013 — driver-registry-completeness lint** (the primary #2709 vector, blind to the projection
  lint): assert every both-sides-divergent `kitty-specs/**` canonical artifact carries a
  **registered merge driver** in root `.gitattributes`. **Non-tautology requirement:** the set of
  canonical artifact globs MUST be sourced from an **independent canonical-artifact registry**
  (the mission-artifact-kind registry), NOT enumerated from `.gitattributes` itself (else the
  completeness check is a tautology that only catches removal of a KNOWN driver). This is what
  stops a future net-new artifact from silently re-inheriting #2709 via `-X theirs`.

## Acceptance criteria
- The no-blind-copy lint FAILS on a synthetic reintroduction of a blind `write_bytes` in `merge/` (SC-005), PASSES on the fixed tree.
- The driver-registry lint FAILS on **two** distinct self-mutations: (a) dropping an existing `.gitattributes` driver entry, AND (b) **registering a NEW canonical `kitty-specs/**` artifact in the registry with no corresponding driver** — proving it catches future artifacts, not just known-driver removal. PASSES on the fixed tree.
- The lints are NOT a re-run of WP01's outcome test.

## Validation
- `PWHEADLESS=1 uv run pytest tests/architectural/ -q` (new lints GREEN on fixed tree)
- Self-mutation proof: (i) reintroduce a blind `write_bytes` → no-blind-copy lint RED; (ii) drop a `.gitattributes` driver entry → registry lint RED; (iii) add a canonical artifact to the registry with no driver → registry lint RED. Revert each.

## Ownership
Owns: new lint(s) under `tests/architectural/`. Campsite: remove the tracked temp artifact `tests/architectural/tmp_ratchet_baseline.txt` if still present.

## Notes
Rebase-first (C-003). Co-delivered with the #2709 fix; independent of the #2711 chain.
