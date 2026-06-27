---
work_package_id: WP01
title: Charter documentation-policy interpolation
dependencies: []
requirement_refs:
- FR-001
- FR-002
tracker_refs: []
planning_base_branch: mission/doctrine-governance-fidelity
merge_target_branch: mission/doctrine-governance-fidelity
branch_strategy: Planning artifacts for this mission were generated on mission/doctrine-governance-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/doctrine-governance-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
phase: Lane A — charter generation fidelity
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "942506"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_compiler_documentation_policy.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/compiler.py
- tests/charter/test_compiler_documentation_policy.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Charter documentation-policy interpolation

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` via the `/ad-hoc-profile-load` skill (read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`) and adopt its directives before implementing.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent**: `claude`

---

## Objectives & Success Criteria

- `spec-kitty charter generate --from-interview` renders the operator's `documentation_policy` answer into the generated `charter.md` Project Directives section — mirroring how `risk_boundaries` is interpolated (FR-001).
- The empty-`documentation_policy` branch emits **no** directive line (FR-002).
- Closes #2153.

**Done when**: a seeded `documentation_policy: "SENTINEL_DOCS: …"` appears verbatim in `charter.md`; the empty-answer case emits nothing; ruff + mypy clean; tests green.

## Context & Constraints

- Root cause (research.md): `src/charter/compiler.py:942-944` reads `docs = interview.answers.get("documentation_policy")`, gates `if docs:`, but emits a **hardcoded** string. The adjacent `risk_boundaries` at `:937-939` IS interpolated.
- **Single sink** — directive output flows only to `charter.md` Project Directives; no `directives.yaml` emitted here (research-confirmed). Do not touch the synthesizer styleguide path.
- **C-005 red-first** through the pre-existing `charter generate --from-interview` surface. **C-007** realistic sentinel prose. **NFR-003** ruff/mypy clean, complexity ≤ 15.

## Subtasks & Detailed Guidance

### Subtask T001 — RED test through `charter generate --from-interview`

- **Purpose**: Witness the dropped answer before fixing.
- **Steps**: In `tests/charter/test_compiler_documentation_policy.py`, build an interview-answers fixture with `documentation_policy: "SENTINEL_DOCS: maintain CHANGELOG + CONTRIBUTING; adopt Divio"` and `risk_boundaries: "SENTINEL_RISK: privacy non-negotiable"`. Drive the public generation path (prefer `charter generate --from-interview` via CliRunner, or the directive-render entry it calls). Assert the generated charter contains `SENTINEL_DOCS` **and** `SENTINEL_RISK`. Confirm it is RED today (SENTINEL_DOCS absent).
- **Files**: `tests/charter/test_compiler_documentation_policy.py`.

### Subtask T002 — Interpolate the answer

- **Purpose**: Honour the answer.
- **Steps**: At `src/charter/compiler.py:944`, change the hardcoded line to interpolate `docs`, mirroring the `risk` shape, e.g. `lines.append(f"{index}. Keep documentation synchronized with workflow and behavior changes: {docs}")`. Keep the `if docs:` gate and `index += 1`.
- **Files**: `src/charter/compiler.py`.

### Subtask T003 — Empty-answer regression test

- **Purpose**: No spurious line when the answer is absent.
- **Steps**: Add a test with `documentation_policy` absent/empty → assert no documentation directive line is emitted and the surrounding directives still render.
- **Files**: `tests/charter/test_compiler_documentation_policy.py`.

## Test Strategy

- Run: `PWHEADLESS=1 pytest tests/charter/test_compiler_documentation_policy.py -q`.
- Prove T001 RED against pre-fix code, then GREEN after T002.

## Risks & Mitigations

- Empty-answer regression → T003. Wrong sink assumption → research confirms single sink; do not edit `directives.yaml`/synthesizer.

## Review Guidance

- Verify red-first ordering (T001 fails pre-fix). Verify the interpolation shape matches `risk_boundaries`. Verify no synthesizer/`user-project-profile.md` changes leaked in.

## Post-Tasks Squad Remediations (BINDING)

- **T003 is a REGRESSION GUARD, not red-first.** The empty-`documentation_policy` branch is already green pre-fix; only **T001** (SENTINEL_DOCS present) is the C-005 red-first proof. Do not count T003 toward red-first.

---

## Activity Log

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T09:49:59Z – claude:opus:python-pedro:implementer – shell_pid=914981 – Assigned agent via action command
- 2026-06-27T09:57:55Z – claude:opus:python-pedro:implementer – shell_pid=914981 – Red-first proven (T001 SENTINEL_DOCS absent pre-fix, present after; SENTINEL_RISK control); documentation_policy interpolated at compiler.py:944 mirroring risk_boundaries, if-gate kept; T003 regression guard green. Diff-scoped ruff exit 0; mypy only pre-existing compiler.py:279 error (unrelated, fails on base) deferred per locality. 2 passed.
- 2026-06-27T09:58:40Z – claude:opus:reviewer-renata:reviewer – shell_pid=942506 – Started review via action command
- 2026-06-27T10:05:13Z – user – shell_pid=942506 – reviewer-renata APPROVE: red-first verified; scope clean
