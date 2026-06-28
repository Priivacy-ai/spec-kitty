---
work_package_id: WP01
title: WP-authoring contract SSOT
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: mission/lifecycle-tooling-friction
merge_target_branch: mission/lifecycle-tooling-friction
branch_strategy: Planning artifacts for this mission were generated on mission/lifecycle-tooling-friction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/lifecycle-tooling-friction unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
phase: Mission-Lifecycle Tooling Friction
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1788439"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt created
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/software-dev/
create_intent:
- tests/doctrine/test_wp_authoring_contract_roundtrip.py
execution_mode: code_change
owned_files:
- src/doctrine/missions/software-dev/actions/tasks/guidelines.md
- src/doctrine/missions/mission-steps/software-dev/tasks/guidelines.md
- src/doctrine/missions/software-dev/templates/task-prompt-template.md
- tests/doctrine/test_wp_authoring_contract_roundtrip.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – WP-authoring contract SSOT

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: update the Activity Log as you address each item.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``. Use language identifiers in code blocks: ` ```python `, ` ```bash `.

---

## Objectives & Success Criteria

- The WP-frontmatter authoring contract is expressed **identically** across all three surfaces: doctrine prose (both `tasks/guidelines.md` copies), the `task-prompt-template.md` frontmatter, and the ownership validator (which is already repo-root-relative and is the canonical authority — C-004).
- BOTH `guidelines.md` copies instruct **repo-root-relative** `owned_files` paths (the word "absolute" at line ~9 is removed/replaced).
- `task-prompt-template.md` frontmatter declares `owned_files`, `authoritative_surface`, `execution_mode`, and `create_intent`, each with a short guidance comment.
- A golden round-trip test (the SSOT ratchet) proves: a WP authored from the completed template with repo-relative placeholder paths passes `ownership` validation + `finalize-tasks` first time; an absolute-path entry fails consistently.
- **SC-001** is satisfied. `ruff` + `mypy` clean on new code; the new test carries an appropriate marker (`fast` or `unit`).

## Context & Constraints

- Spec: [spec.md](../spec.md) — User Story 1, FR-001/002/003, SC-001.
- Plan: [plan.md](../plan.md) — IC-01.
- Research: [research.md](../research.md) — `#2220 + #2221` are one defect (folded); the contract is independently encoded in three drifting places.
- **C-004 — code is the path authority**: align the doctrine TEXT to repo-relative; do **NOT** patch the validator to accept absolute. The ownership validator's `_CODE_PREFIXES = ("src/", "tests/")` (in `src/specify_cli/.../ownership/validation.py`) is repo-relative — that is the SSOT the prose and template must match.
- **C-006 — red-first + reuse-don't-rebuild**: drive the real validator + `finalize-tasks` path (paula's ratchet), not a `template-exists` assertion.
- Both doctrine copies must stay aligned or they re-diverge (the original defect). Fix BOTH.
- This is the canonical irony to model: `owned_files` in THIS prompt's own frontmatter are repo-root-relative — that is the correct form.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> Populated automatically by `spec-kitty agent mission tasks`. Do NOT edit manually.

## Subtasks & Detailed Guidance

### Subtask T001 – Align both `guidelines.md` copies to repo-root-relative

- **Purpose**: Remove the doctrine↔validator contradiction at its source (the word "absolute" contradicts the repo-relative validator).
- **Steps**:
  1. Open `src/doctrine/missions/software-dev/actions/tasks/guidelines.md`; locate the `owned_files` guidance (line ~9, "Use absolute paths").
  2. Reword to instruct **repo-root-relative** paths (e.g. `src/...`, `tests/...`), explicitly matching what the ownership validator accepts.
  3. Apply the identical reword to the second copy `src/doctrine/missions/mission-steps/software-dev/tasks/guidelines.md`.
  4. Diff both files to confirm the guidance text is now byte-aligned between copies.
- **Files**: both `tasks/guidelines.md` copies.
- **Parallel?**: With T002 (different files); T003 depends on both.
- **Notes**: Touching `src/doctrine/` triggers the CI-only terminology guard — run `pytest tests/architectural/test_no_legacy_terminology.py` before considering this done.

### Subtask T002 – Complete `task-prompt-template.md` frontmatter

- **Purpose**: Make template-authored WPs self-describing so they validate + finalize first time.
- **Steps**:
  1. Open `src/doctrine/missions/software-dev/templates/task-prompt-template.md`.
  2. Add `owned_files`, `authoritative_surface`, `execution_mode`, and `create_intent` to the frontmatter, each with a short inline/guidance comment describing the expected value (repo-root-relative paths for `owned_files`/`create_intent`; a repo-relative surface root for `authoritative_surface`; the `code_change`/`docs` etc. vocabulary for `execution_mode`).
  3. Ensure the placeholder `owned_files` examples use **repo-root-relative** form (model the correct shape) and that any new test file appears in BOTH `owned_files` and `create_intent`.
  4. Keep existing template fields and the body intact (locality — DIRECTIVE_024).
- **Files**: `templates/task-prompt-template.md`.
- **Parallel?**: With T001.
- **Notes**: This is the surface the round-trip test renders from in T003 — keep the placeholders fillable with valid repo-relative paths.

### Subtask T003 – Golden round-trip ratchet test

- **Purpose**: Lock the SSOT so the three encodings cannot re-drift.
- **Steps**:
  1. Create `tests/doctrine/test_wp_authoring_contract_roundtrip.py`.
  2. **Mandatory prose ratchet** (not "if cheap"): read BOTH `tasks/guidelines.md` copies from disk and assert each one instructs **repo-root-relative** `owned_files` AND that **neither** copy contains the literal string `absolute path` (the original drift vector). This pins the doctrine text, not just the validator.
  3. GREEN case — drive the REAL template from disk: read the actual `src/doctrine/missions/software-dev/templates/task-prompt-template.md` frontmatter from disk and assert the four keys (`owned_files`, `authoritative_surface`, `execution_mode`, `create_intent`) are present IN that file; then build the WP from THAT on-disk frontmatter with repo-relative placeholder `owned_files` (real-format paths under `src/`/`tests/`, C-007) and run it through the actual `ownership` validation + `finalize-tasks` path; assert it passes. Do NOT hand-construct the frontmatter inline — the test must fail if the keys are missing from the real template file (forbids the `template-exists`-by-fabrication anti-pattern).
  4. RED case: seed an absolute path (e.g. `/abs/...`) into `owned_files`; assert validation/finalize fails consistently, surfacing the ownership error.
  5. Mark the test `@pytest.mark.fast` (pure-logic) or `@pytest.mark.unit` as fits the actual call surface.
- **Files**: `tests/doctrine/test_wp_authoring_contract_roundtrip.py` (new — in `owned_files` + `create_intent`).
- **Parallel?**: After T001 + T002.
- **Notes**: Exercise the REAL validator + finalize path (paula). Do NOT assert merely that the template declares the keys — that is the `template-exists` anti-pattern. The four-key assertion MUST read the real template file from disk and feed that frontmatter through `ownership/validation`; hand-constructing the frontmatter inline defeats the ratchet.

## Test Strategy

- New test: `tests/doctrine/test_wp_authoring_contract_roundtrip.py`.
- Red-first: write the absolute-path-fails case first and confirm it would currently mis-pass against a template lacking the keys, then complete T001/T002 to make the green case pass.
- Run: `PWHEADLESS=1 pytest tests/doctrine/test_wp_authoring_contract_roundtrip.py -q` and `pytest tests/architectural/test_no_legacy_terminology.py`.
- Use real-format placeholder paths (C-007), not toy strings.

## Risks & Mitigations

- **Two copies re-diverge**: fix both `guidelines.md` files and diff them; T003's mandatory prose ratchet (BOTH copies say repo-root-relative, NEITHER contains the literal "absolute path") guards the contract directly — this assertion is required, not optional.
- **Test green for the wrong reason**: drive the real validator + finalize, not a structural template assertion (C-006).
- **Terminology regression**: doctrine prose edits can trip the CI-only guard — run it locally before push.

## Review Guidance

- Confirm BOTH `guidelines.md` copies say repo-root-relative and neither says "absolute".
- Confirm the template frontmatter now declares all four keys with guidance comments and repo-relative examples.
- Confirm the round-trip test exercises the actual ownership/finalize path and has both a pass (relative) and fail (absolute) case.
- Confirm `ruff`/`mypy` clean and the terminology guard passes.

## Activity Log

> **CRITICAL**: Append new entries at the END in chronological order. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T16:22:59Z – claude:opus:python-pedro:implementer – shell_pid=1733719 – Assigned agent via action command
- 2026-06-27T16:37:31Z – user – shell_pid=1733719 – WP01 claimed (implementer)
- 2026-06-27T16:37:33Z – user – shell_pid=1733719 – WP01 in_progress (implementer)
- 2026-06-27T16:40:36Z – claude:opus:python-pedro:implementer – shell_pid=1733719 – Ready: both guidelines repo-relative, template frontmatter complete, golden round-trip red-first proven green
- 2026-06-27T16:41:28Z – claude:opus:reviewer-renata:reviewer – shell_pid=1788439 – Started review via action command
- 2026-06-27T16:44:50Z – user – shell_pid=1788439 – Review APPROVE (reviewer-renata, isolated): both guidelines byte-identically repo-relative (no 'absolute'), template frontmatter complete (4 keys), golden round-trip drives REAL validate_ownership+glob seam with delete-the-validator RED case; terminology guard + ruff + mypy green; scope = 4 owned files
