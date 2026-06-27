---
work_package_id: WP03
title: 'related: validator (ruler 1, report-only)'
dependencies:
- WP01
requirement_refs:
- FR-005
- NFR-001
tracker_refs: []
planning_base_branch: docs/2165-consolidation-research
merge_target_branch: docs/2165-consolidation-research
branch_strategy: Planning artifacts for this mission were generated on docs/2165-consolidation-research. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-consolidation-research unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: scripts/docs/related_validator.py
create_intent:
- scripts/docs/related_validator.py
- tests/docs/test_related_validator.py
execution_mode: code_change
owned_files:
- scripts/docs/related_validator.py
- tests/docs/test_related_validator.py
role: implementer
tags: []
shell_pid: "583049"
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Build the `related:`-graph **validator** as a standalone, **report-only** ruler — and prove it with a self-test. Mission B later flips it to blocking; here it must *exist and demonstrably bite*.

## Context

Depends on WP01 (the ADR confirms the `related:` resolvable-path form). The validator scans `docs/` markdown frontmatter `related:` lists. **It is report-only** (exit 0; C-002) — it prints findings, it does not fail CI. The **self-test is the real Definition of Done** (renata: a ruler that can't go RED is fake). No doc-tree mutation (C-006). No new dependencies (use stdlib + ruamel.yaml).

## Subtasks

### T013 — `scripts/docs/related_validator.py`
Walk `docs/**/*.md`, parse frontmatter `related:` (a flat list of repo-relative paths). For each entry, resolve it to an existing `.md`; collect non-resolving entries as dangling edges. Output `{ checked_count: int, dangling_edges: [{from, to}] }` and print a human summary. **Exit 0** (report-only). Add a `--strict` flag that is wired but defaults off (Mission B turns it on).

### T014 — Self-test (the DoD)
`tests/docs/test_related_validator.py`: a fixture tree with one deliberately-**dangling** `related:` asserts `dangling_edges` is non-empty (and, under `--strict`, the exit is non-zero); a good fixture asserts empty. **Also assert `checked_count > 0`** so "0 broken" cannot mean "0 checked."

### T015 — Report-only baseline
Run the validator over the live `docs/` tree, confirm exit 0, and record the current dangling count as the baseline Mission B must drive to zero (note it in the WP handoff / a comment).

## Branch Strategy

Planning + merge target: `docs/2165-consolidation-research`. Worktree per `lanes.json` (Lane C, after WP01; parallel to WP04).

## Definition of Done

- [ ] `related_validator.py` walks `docs/`, reports `checked_count` + dangling edges, exits 0.
- [ ] **Self-test goes RED on the dangling fixture** and green on the good fixture; asserts `checked_count > 0`.
- [ ] Report-only baseline count recorded.
- [ ] `ruff`/`mypy` clean; no new deps; no doc-tree mutation.

## Risks & Reviewer Guidance

- The fakeable failure: a no-op validator that always passes. Reviewer **must** confirm the self-test actually reds on the seeded dangling edge and that `checked_count > 0` is asserted.

## Activity Log

- 2026-06-27T06:56:06Z – claude:opus:python-pedro:implementer – shell_pid=559234 – Assigned agent via action command
- 2026-06-27T07:02:13Z – claude:opus:python-pedro:implementer – shell_pid=559234 – Ready for review
- 2026-06-27T07:03:00Z – claude:opus:reviewer-renata:reviewer – shell_pid=583049 – Started review via action command
- 2026-06-27T07:06:50Z – user – shell_pid=583049 – Review passed: report-only related: validator + self-test. Self-test genuinely bites (no-op stub reds 3/5: checked_count>0 guard x2 + --strict semantic). Live baseline 11 checked / 0 dangling, exit 0. .md-vs-file-existence call adjudicated SOUND: live related: lists legitimately target docfx.json/llms.txt/page-inventory.yaml; is_file() gate does not weaken dangling detection (any non-resolving path still reds). ruff/mypy clean, no doc-tree mutation, no new deps. Non-blocking notes: (1) ADR line 90 should read 'resolvable repo-relative path' not '.md'; (2) _read_related swallows OSError/YAMLError -> Mission B strict mode should surface parse errors; (3) T015 baseline (0 dangling) reproducible but not written to a handoff note.
