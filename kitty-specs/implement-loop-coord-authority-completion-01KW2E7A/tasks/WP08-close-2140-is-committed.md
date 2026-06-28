---
work_package_id: WP08
title: 'Close #2140 — is_committed docstring + negative regression pin'
dependencies:
- WP01
requirement_refs:
- C-004
- FR-010
tracker_refs: []
planning_base_branch: design/coord-authority-remediation-2160
merge_target_branch: design/coord-authority-remediation-2160
branch_strategy: Planning artifacts for this mission were generated on design/coord-authority-remediation-2160. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-authority-remediation-2160 unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
phase: Phase 3 - Closeout
assignee: ''
shell_pid: ''
agent: claude
history:
- at: '2026-06-26T18:29:45Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/
create_intent:
- tests/integration/test_is_committed_contract.py
execution_mode: code_change
owned_files:
- src/specify_cli/missions/_substantive.py
- tests/integration/test_is_committed_contract.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – Close #2140 (is_committed)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

`is_committed` was verified already-remediated by #2106 (squad CONFIRMED-UNREACHABLE). This WP
adds the durable guard so it cannot silently regress, and refreshes the stale docstring.

Done when: the `is_committed` docstring describes the **primary-surface** read (no coord
narration); a regression test pins the contract with a **negative** assertion; #2140 can be
closed as resolved-by-#2106 + pinned.

## Context & Constraints

- Spec FR-010, C-004. `is_committed` at `src/specify_cli/missions/_substantive.py:301`;
  stale docstring at `:316-323` (still narrates the coord-worktree spec read).
- It is a **single-surface** check derived from the path argument — the pin must NOT mandate
  a multi-leg OR (C-004).
- The negative assertion is the load-bearing part (a positive-only assertion is tautological):
  `is_committed(<coord-husk spec path with no spec.md>, repo_root) == False`.
- Uses the WP01 fixture for a realistic coord husk path.

## Branch Strategy

- **Strategy**: already-confirmed
- **Planning base branch**: design/coord-authority-remediation-2160
- **Merge target branch**: design/coord-authority-remediation-2160

## Subtasks & Detailed Guidance

### Subtask T035 – Refresh ONLY the stale sentence (keep path-derived framing)
- **Squad correction:** `is_committed` is single-surface / path-derived and its docstring
  already describes that correctly (C-004). Do NOT rewrite it to "primary for all topologies"
  — that would be wrong (the function checks whatever path it is handed). Update ONLY the one
  stale sentence (~`:320-325`) that narrates "for a materialized coordination topology the
  read resolves to the coord worktree" → reflect that the **caller** now resolves the spec on
  primary post-#2106. The path-derived contract description stays.

### Subtask T036 – Caller-contract regression pin (drive the CALLER, not is_committed directly)
- **Squad HIGH:** calling `is_committed(husk_path)` directly only pins its path-handling
  (always False with no spec.md) — it does NOT catch the real #2140 vector, which is the
  **caller** (`mission_setup_plan.py` `_enforce_spec_gate`/`_planning_read_dir(spec)`)
  resolving coord vs primary. Drive the **pre-existing caller** (`setup_plan`) on the WP01
  coord fixture: assert it resolves the spec on PRIMARY → committed spec reads True; and a
  reversion that re-points the caller's spec read to the coord husk yields False. Document
  the RED as a husk-resolution failure through `setup_plan`, not a bare `is_committed` call.
  File: `tests/integration/test_is_committed_contract.py`.

## Test Strategy

`PWHEADLESS=1 pytest tests/integration/test_is_committed_contract.py -q`. The negative
assertion must fail if a future change re-points the spec read to the coord surface.

## Risks & Mitigations

- **Tautological pin** (positive-only) → no protection. Mitigation: the negative assertion is required.
- **Multi-leg OR creep** → violates C-004. Mitigation: assert single-surface behavior.

## Review Guidance

- Confirm the negative assertion exists and is meaningful.
- Confirm no behavioral change to `is_committed` itself (docstring + test only).

## Activity Log

- 2026-06-26T18:29:45Z – system – Prompt created.
- 2026-06-26T20:04:37Z – user – flat claim
- 2026-06-26T20:04:39Z – user – flat; #2140 on design branch
- 2026-06-26T20:16:18Z – claude – #2140 close (aa2d428b2): caller-driven negative pin + docstring; 2 passed
- 2026-06-26T20:20:58Z – user – renata review done
- 2026-06-26T20:21:00Z – user – Approved by reviewer-renata (flat): #2140/FR-010. Positive test is the genuine caller-vector pin (asserts real unpatched _planning_read_dir(spec)==primary before committed check → RED on coord-repoint). Docstring C-004-preserved (code untouched). renata MEDIUM addressed: negative test relabeled as failure-mode illustration (no longer overclaims). 2 passed.
