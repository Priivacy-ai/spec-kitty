---
work_package_id: WP04
title: CHANGELOG and Final Gate
dependencies:
- WP03
requirement_refs:
- C-001
- C-006
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
agent: claude
history:
- date: '2026-06-06'
  event: created
  note: Initial task generation
agent_profile: curator-carla
authoritative_surface: CHANGELOG.md
execution_mode: code_change
owned_files:
- CHANGELOG.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned profile:

```
/ad-hoc-profile-load curator-carla
```

---

## Objective

Write the `CHANGELOG.md` entry for this fix, run the full validation suite as a final gate, and confirm that all mission artifacts (audit comment in merge.py, spec statuses) are in order.

This is the closeout WP. Do not start it until WP03 (regression tests passing) is done.

---

## Context

This fix closes a class recurrence from issue #1589 (facet 3). The `CHANGELOG.md` entry should accurately describe:
- The symptom
- The root cause (structural, not incidental)
- The class recurrence note
- What changed and where

The final gate run confirms the full repository is clean before the mission is marked done.

---

## Subtask T019: Write CHANGELOG.md Entry

**Purpose**: Document the fix for future maintainers and users.

**Steps**:

1. Read `CHANGELOG.md` to find the current unreleased / development section heading and the entry format used in the project.

2. Add an entry under the appropriate section (e.g., `## [Unreleased]` or the next version heading). Follow the project's existing format exactly. Example structure:

```markdown
### Fixed

- **Merge done-marking surface divergence** (`merge.py`, `coordination/`): After `spec-kitty merge`,
  WPs that were `approved` would show as `Completed: 0 (80.0%)` instead of `Completed: 1 (100%)`
  when the mission carried a `coordination_branch`. Root cause: `_mark_wp_merged_done` wrote done
  events to the coordination branch surface via `BookkeepingTransaction`, while
  `_assert_merged_wps_reached_done` read back from the primary checkout via plain `Path.read_text()`.
  Fix: introduced `coordination.surface_resolver.resolve_status_surface(repo_root, mission_slug)`
  as the single canonical surface resolver consumed by both functions. Class recurrence of
  issue #1589 facet 3 (the same divergence on the runtime read path, fixed earlier).
  Closes [#1726](https://github.com/Priivacy-ai/spec-kitty/issues/1726). ([#1672](https://github.com/Priivacy-ai/spec-kitty/issues/1672) parity ratchet)
```

Adapt the format to match the project's existing style. Keep it accurate and specific — future maintainers need to understand this was a structural fix, not a point patch.

---

## Subtask T020: Run Full Validation Suite

**Purpose**: Final gate — confirm the entire test suite is clean with all WP changes in place.

**Steps**:

1. Run the full test suite:
   ```bash
   .venv/bin/pytest tests/ -v --tb=short 2>&1 | tail -30
   ```

2. Run mypy on the full source:
   ```bash
   .venv/bin/mypy --strict src/specify_cli/ 2>&1 | tail -20
   ```

3. Run ruff:
   ```bash
   .venv/bin/ruff check src/ tests/ 2>&1 | tail -20
   ```

4. **If pre-existing failures are found** (failures that existed before this mission's changes):
   Per DIR-013, open a GitHub issue for each pre-existing failure before continuing:
   ```bash
   unset GITHUB_TOKEN && gh issue create \
     --repo Priivacy-ai/spec-kitty \
     --title "Pre-existing test failure: <test name>" \
     --body "Found while running final gate for mission merge-done-surface-resolver-01KTDVHZ. Command: pytest tests/ -v. Failure: <paste relevant output>. Believed pre-existing because: <reason>."
   ```
   Record the issue URL, then continue.

5. **If new failures are found** (introduced by this mission's changes): Do NOT continue. Investigate and fix before closing the gate.

---

## Subtask T021: Verify Artifacts and Update Spec Statuses

**Purpose**: Confirm all mission deliverables are in order and close out the spec.

**Steps**:

1. Verify the audit comment is present in `merge.py`:
   ```bash
   grep -in "merge-path status surface audit" src/specify_cli/cli/commands/merge.py
   ```
   If it is missing, escalate to the mission owner.

2. Update `spec.md` FR statuses from `Proposed` to `Accepted` for all implemented requirements:
   - Open `kitty-specs/merge-done-surface-resolver-01KTDVHZ/spec.md`
   - Change `| Proposed |` → `| Accepted |` for FR-001 through FR-010 that were implemented
   - Change `| Proposed |` → `| Accepted |` for NFR-001 through NFR-003 if thresholds were met
   - Constraints remain `Binding` (no status change needed)

3. Commit all closeout changes:
   ```bash
   git add CHANGELOG.md
   git add kitty-specs/merge-done-surface-resolver-01KTDVHZ/spec.md
   git commit -m "chore(merge-done-surface-resolver): add changelog entry and close mission spec

   Fixes #1726. Full test suite clean. Audit comment in merge.py committed.
   surface_resolver.py 90%+ coverage confirmed."
   ```

---

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: allocated per `lanes.json` when `spec-kitty implement WP04` is run

**To implement this WP**:
```bash
spec-kitty agent action implement WP04 --agent claude
```

---

## Definition of Done

- [ ] `CHANGELOG.md` has an entry describing the fix, root cause, and class recurrence
- [ ] Full test suite (`pytest tests/`) passes
- [ ] `mypy --strict src/specify_cli/` passes
- [ ] `ruff check src/ tests/` passes
- [ ] Any pre-existing failures are reported in GitHub issues (per DIR-013)
- [ ] Audit comment (`grep -in "merge-path status surface audit" merge.py`) is present and committed
- [ ] `spec.md` FR statuses updated to `Accepted` for implemented requirements
- [ ] Closeout commit created

---

## Risks

- **Pre-existing test failures**: The full suite may have failures unrelated to this mission. Handle per DIR-013 (open GitHub issues) rather than ignoring or failing the WP.
- **Audit comment missing**: If WP02 did not add the audit comment in `merge.py`, this WP is blocked for T021. Verify before proceeding to T020.
