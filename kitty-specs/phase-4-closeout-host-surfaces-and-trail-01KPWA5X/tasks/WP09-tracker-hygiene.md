---
work_package_id: WP09
title: Tracker Hygiene
dependencies:
- WP08
requirement_refs:
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T045
- T046
- T047
- T048
- T049
- T050
- T051
history:
- event: created
  at: '2026-04-23T05:10:00Z'
  note: Initial generation from /spec-kitty.tasks
authoritative_surface: kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/
execution_mode: planning_artifact
owned_files:
- kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/tracker-hygiene.md
tags: []
---

# WP09 — Tracker Hygiene

## Objective

Execute the GitHub tracker updates that FR-014 requires as part of the mission's Definition of Done. Close `#496` (Tranche A) and `#701` (Tranche B), update `#466` (Phase 4 tracker), cross-link `#534` to its Phase 5 unblockers, verify `#461` stays open, and record the hygiene actions in a mission-local artifact for audit.

This is the final WP of the mission. It runs after WP08 merges and typically executes in a single operator session around the time the mission PR merges to `main`.

## Context

Tracker hygiene is a deliberate FR because, per the mission brief: "decisive closeout stewardship" requires that the issues the mission addresses are actually closed with clear delivery records, and that the umbrella tracker (`#466` Phase 4) reflects the shipped state. Leaving issues open post-merge causes tracker drift and re-asks the same question in future planning passes.

**Auth note**: per project CLAUDE.md, organisation-repo `gh` commands may require unsetting `GITHUB_TOKEN` to use keyring auth. Use `unset GITHUB_TOKEN && gh ...` when organisation-level permissions are needed.

## Branch Strategy

- **Planning base**: `main`.
- **Final merge target**: `main`.
- **Execution worktree**: allocated from `lanes.json` at implement time. WP09 depends on WP08; it is the mission's terminal WP.

## Subtask Guidance

### T045 — Prepare and close `#496`

**Purpose**: Close the Phase 4 host-surface breadth follow-on with a delivery reference.

**Steps**:
1. Open the mission PR; note the PR number. (If this WP runs before the PR is created, draft the close comment with a placeholder that the release owner fills in.)
2. Verify `docs/host-surface-parity.md` exists and lists all 15 surfaces (sanity check against WP05 deliverable).
3. Run:
   ```bash
   unset GITHUB_TOKEN && gh issue close 496 --comment "Closed by mission phase-4-closeout-host-surfaces-and-trail-01KPWA5X (merge PR #<PR_NUMBER>).

   Host-surface breadth rollout complete:
   - 15 supported host surfaces audited and at parity (inline or pointer).
   - Matrix promoted to docs/host-surface-parity.md.
   - Coverage test in tests/specify_cli/docs/test_host_surface_inventory.py.
   - Dashboard Feature → Mission Run user-visible rename shipped (FR-003).
   - README Governance layer subsection shipped."
   ```
4. Verify the close succeeded: `gh issue view 496 --json state,closedAt`.

### T046 — Prepare and close `#701`

**Purpose**: Close the Phase 4 trail follow-on.

**Steps**:
1. Run:
   ```bash
   unset GITHUB_TOKEN && gh issue close 701 --comment "Closed by mission phase-4-closeout-host-surfaces-and-trail-01KPWA5X (merge PR #<PR_NUMBER>).

   Trail follow-on deliverables:
   - Correlation contract: append-only artifact_link / commit_link events on invocation JSONL; --artifact (repeatable) + --commit (singular) on profile-invocation complete. See ADR-001.
   - Mode of work runtime-derived and recorded on started event; enforced at Tier 2 promotion boundary. See ADR-002.
   - SaaS read-model policy: typed projection_policy.py module with POLICY_TABLE covering all (mode, event) pairs. See ADR-003.
   - Tier 2 SaaS projection decisively deferred; evidence remains local-only in 3.2.x. See ADR-004.

   Decisions recorded as ADRs in kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/decisions/.
   Operator docs updated in docs/trail-model.md."
   ```
2. Verify: `gh issue view 701 --json state,closedAt`.

### T047 — Update `#466` (Phase 4 tracker)

**Purpose**: Reflect that Phase 4 follow-on has shipped.

**Steps**:
1. Run:
   ```bash
   unset GITHUB_TOKEN && gh issue comment 466 --body "Phase 4 follow-on (mission phase-4-closeout-host-surfaces-and-trail-01KPWA5X) has shipped on main.

   Delivered in this closeout:
   - #496 host-surface breadth rollout — CLOSED
   - #701 trail follow-on — CLOSED
   - docs/trail-model.md updated with Mode of Work enforcement, Correlation Links, SaaS Read-Model Policy table, and Tier 2 SaaS Projection deferral.
   - docs/host-surface-parity.md is the new authoritative matrix.

   Remaining deferred: #534 spec-kitty explain (blocked on Phase 5 glossary foundation; see #499 and #759)."
   ```
2. Leave `#466` open if other Phase 4 scope remains; close if this was the last open child. Verify with `gh issue list --milestone "Phase 4"` or equivalent; at the operator's discretion.

### T048 — Cross-link `#534` to Phase 5 unblockers

**Purpose**: Make the Phase 5 glossary foundation dependency explicit on the deferred-explain issue.

**Steps**:
1. Run:
   ```bash
   unset GITHUB_TOKEN && gh issue comment 534 --body "Deferral confirmed by Phase 4 closeout (mission phase-4-closeout-host-surfaces-and-trail-01KPWA5X).

   \`spec-kitty explain\` requires DRG glossary addressability to produce fully-cited answers. Phase 5 glossary foundation shipped as #759; further glossary addressability work is tracked in #499. This issue remains blocked on those until a fully-cited explain surface is achievable.

   See ADR-004-tier2-saas-deferral.md (same mission) for the closeout's decisive-deferral pattern."
   ```
2. Do NOT close `#534` — the deferral is indefinite pending Phase 5 outcomes. Verify: `gh issue view 534 --json state` should remain `OPEN`.

### T049 — Verify `#461` (umbrella roadmap) left open

**Purpose**: Confirm the umbrella tracker stays open for future phases.

**Steps**:
1. `unset GITHUB_TOKEN && gh issue view 461 --json state,title`.
2. Expected: `state=OPEN`. If unexpectedly closed, reopen: `gh issue reopen 461 --comment "Keeping umbrella roadmap open for subsequent phases."`. No other action.

### T050 — Retitle `#496` if needed

**Purpose**: Make the tracker title match the delivered scope.

**Steps**:
1. Current title: `[Phase 4] WP4.7 — Update Spec Kitty skill packs for host-LLM advise/execute model`.
2. Since `#496` is now closed, retitle is cosmetic. If the mission closeout wants the closed-issue title to read cleanly as a delivered record, retitle:
   ```bash
   unset GITHUB_TOKEN && gh issue edit 496 --title "[Phase 4] Host-surface breadth rollout — delivered"
   ```
3. Retitle is optional; skip if the operator prefers to preserve the original issue title for historical clarity.

### T051 — Record completed hygiene actions in mission artifact + PR description

**Purpose**: Durable audit record of the tracker actions.

**Steps**:
1. Create or append to `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/tracker-hygiene.md`:

   ```markdown
   # Tracker Hygiene — Executed

   Mission: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
   Executed by: <operator handle>
   Executed at: <ISO-8601 timestamp>
   Merge PR: #<PR_NUMBER>

   ## Actions

   | Issue | Action | Verified |
   |-------|--------|----------|
   | #496 | Closed with delivery comment | ✓ gh issue view 496 → CLOSED |
   | #701 | Closed with delivery comment | ✓ gh issue view 701 → CLOSED |
   | #466 | Commented: Phase 4 follow-on shipped | ✓ comment visible |
   | #534 | Cross-linked to #499 and #759 | ✓ comment visible; state remains OPEN |
   | #461 | Verified open | ✓ state=OPEN |
   | #496 | (optional) Retitled to delivered record | ✓ / skipped |

   ## Notes

   - All actions executed with organisation-scoped auth (GITHUB_TOKEN unset; keyring token used).
   ```

2. Also include a one-line summary in the mission's PR description:
   ```
   Tracker hygiene: closes #496, closes #701; comments on #466, #534; keeps #461 open. Full record in kitty-specs/.../artifacts/tracker-hygiene.md.
   ```

## Definition of Done

- [ ] `#496` closed with a delivery-referencing comment.
- [ ] `#701` closed with a delivery-referencing comment.
- [ ] `#466` has a Phase-4-shipped comment.
- [ ] `#534` has the Phase 5 cross-link comment; state is still OPEN.
- [ ] `#461` verified OPEN.
- [ ] (Optional) `#496` retitled to reflect delivered scope.
- [ ] `artifacts/tracker-hygiene.md` records each action with verification.
- [ ] PR description contains the one-line hygiene summary.

## Risks

- **Wrong issue numbers**: the closing commands use explicit numbers. Mitigation: re-verify numbers against the mission spec (`#461`, `#466`, `#496`, `#534`, `#701`). No manual derivation.
- **Insufficient auth scopes**: `GITHUB_TOKEN` from CI may not have `repo` scope. Mitigation: `unset GITHUB_TOKEN && gh …` per project CLAUDE.md guidance.
- **Comment formatting**: multi-line comments via `--body` must escape quotes correctly; use the HEREDOC pattern from project CLAUDE.md if the body grows complex.
- **Premature execution**: running WP09 before the mission PR exists leaves `<PR_NUMBER>` placeholder. Mitigation: WP09 runs after merge or immediately before merge with the PR number filled in.
- **Closed-by-mistake**: if `#461` is accidentally closed, the reopen step catches it. If `#466` is closed prematurely while other Phase 4 scope remains open, decide with the release owner.

## Reviewer Guidance

Reviewer should:
- Read `artifacts/tracker-hygiene.md` and confirm every action has a verification checkbox.
- Spot-check 2 of the 5 issues (open them on GitHub and confirm the comment / closure is live).
- Confirm the PR description contains the hygiene summary line.
- Confirm `#534` is still OPEN after the cross-link comment.
- Confirm `#461` is still OPEN.
