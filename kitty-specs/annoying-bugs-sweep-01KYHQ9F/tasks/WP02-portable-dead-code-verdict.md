---
work_package_id: WP02
title: P0 portable and honest dead-code review gate
dependencies: []
requirement_refs:
- C-005
- C-008
- C-009
- FR-014
- FR-015
- FR-016
- NFR-002
- NFR-004
planning_base_branch: fix/annoying-bugs-sweep
merge_target_branch: fix/annoying-bugs-sweep
branch_strategy: Planning artifacts for this mission were generated on fix/annoying-bugs-sweep. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/annoying-bugs-sweep unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-annoying-bugs-sweep-01KYHQ9F
base_commit: 35f4f880fb27a51c1e1a42c30de84c82a4ed0186
created_at: '2026-07-27T13:54:37.325883+00:00'
subtasks:
- T028
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Release-critical P0
history:
- at: '2026-07-27T13:34:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/review/
create_intent:
- tests/specify_cli/cli/commands/review/baselines/issue_2987_red_first.md
execution_mode: code_change
model: gpt-5.6-sol
owned_files:
- src/specify_cli/cli/commands/review/_dead_code.py
- src/specify_cli/cli/commands/review/_diagnostics.py
- src/specify_cli/cli/commands/review/ERROR_CODES.md
- tests/specify_cli/cli/commands/review/test_dead_code_baseline.py
- tests/specify_cli/cli/commands/review/baselines/issue_2987_red_first.md
role: implementer
tags: []
tracker_refs:
- '#2987'
---

# Work Package Prompt: WP02 - P0 portable and honest dead-code review gate

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load`, resolve `python-pedro` with
`spec-kitty agent profile show python-pedro`, and load
`spec-kitty charter context --action implement --json` before reading further.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

## Objective

Close both halves of #2987: the post-merge dead-code gate must run without POSIX `grep`, and it must
never report a clean zero when source discovery did not establish a supported denominator.

## Context And Constraints

- Read `spec.md` US2, `research.md` R3/R4, `data-model.md`, and
  `contracts/dead-code-verdict.md`.
- Portability and vacuity are independent defects. A reference-search replacement alone does not
  fix the `git diff -- src/` discovery scope.
- Preserve the existing POSIX symbol set, cwd-relative comparison, and `"test" not in path`
  substring filter.
- Do not attempt universal polyglot analysis. Unsupported layouts must be explicit
  `undeterminable`, not clean.
- Coordinate with the reporter before implementation, as required by C-009.

## Branch Strategy

- **Planning base**: `fix/annoying-bugs-sweep`
- **Merge target**: `fix/annoying-bugs-sweep`
- Use the workspace resolved from `lanes.json`.

## Subtasks

### T028 - Open the WP: tracker, ownership, and campsite

Before code changes, assign #2987 to the current Human-in-Charge and add a tracker comment naming
this mission. Record both links in the evidence file. Re-check the actual diff against C-005 and all
other WP ownership, then perform a bounded domain-matched Sonar/complexity scout of the owned review
surfaces. Land necessary behavior-preserving cleanup first with focused tests, or record a clean
finding. Stop and update ownership before touching an undeclared file.

### T007 - Reporter coordination

Comment on #2987 before code changes. State that `git grep` addresses FR-014 only, ask whether their
work is active, and record the permalink/outcome in the evidence file. Do not block the honest
discovery half on an option that cannot satisfy it.

### T008 - Red-first tests

Retarget the existing non-git `tmp_path` case from clean-zero to undeterminable. Add a fast test
that injects `FileNotFoundError` at the subprocess boundary; do not patch `shutil.which`. Add a
supported POSIX fixture that captures the exact symbol result set before refactoring.

Also invoke the real `spec-kitty review --mode post-merge` CLI path in a valid temporary Git
repository with a supported symbol-bearing diff. Use a subprocess spy/PATH fixture that permits Git
but raises if any external reference-search executable is attempted. Assert the command completes,
gate 2 reports the deliberately unreferenced symbol as non-clean, no clean-zero is emitted, and the
observed subprocess executable set contains Git only.

The tests must distinguish:

- failed diff;
- unsupported non-Python/non-`src` changes;
- supported Python diff with no public symbols;
- supported Python diff with referenced and unreferenced symbols.

### T009 - Pure-Python reference scan

Extract deterministic, directly testable file enumeration and symbol-reference helpers. Search the
same effective Python corpus as the existing filesystem scan, including untracked files where
applicable. Handle unreadable files through the verdict contract rather than a traceback.

### T010 - Honest discovery

Remove the hardcoded `src/` pathspec from the discovery authority. Classify changed paths and earn a
clean result only when the gate successfully examined a supported source set. Check subprocess
return codes; stderr/exit failure cannot collapse to empty stdout.

### T011 - Stable diagnostic

Add a JSON-stable review diagnostic for undeterminable dead-code analysis and document its trigger,
meaning, and remediation in `ERROR_CODES.md`. Append a structured finding that makes the overall
review verdict non-clean. Do not overload the legacy missing-baseline diagnostic.

### T012 - Compatibility and gates

Run:

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/review/test_dead_code_baseline.py -q
ruff check src/specify_cli/cli/commands/review/_dead_code.py src/specify_cli/cli/commands/review/_diagnostics.py tests/specify_cli/cli/commands/review/test_dead_code_baseline.py
mypy src/specify_cli/cli/commands/review/_dead_code.py
```

Record the pre/post symbol-set comparison and red-first node IDs in the evidence file.

## Definition Of Done

- Missing `grep` cannot crash the gate.
- Failed or unsupported discovery emits a stable, actionable undeterminable finding.
- Clean-zero requires a successful, non-vacuous supported scan.
- Current POSIX supported behavior is pinned and unchanged.
- Fast tests directly guard both defect halves.
- The real post-merge CLI path works with Git available and no external `grep`.
- The actual changed-file set remains disjoint from every other WP.

## Reviewer Guidance

Reject a `shutil.which`-only guard, a `git grep`-only replacement, ignored subprocess return codes,
or any path that renders undeterminable as green. Verify the supported zero-symbol case remains
possible and earned.
