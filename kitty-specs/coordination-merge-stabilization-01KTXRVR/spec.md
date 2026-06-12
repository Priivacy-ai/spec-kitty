# Mission Specification: Coordination and Merge Stabilization

**Mission ID**: `01KTXRVR2HPMKGMH20K18JZ1SA` (mid8 `01KTXRVR`)
**Created**: 2026-06-12
**Mission Type**: software-dev (bug-fix / stabilization)
**Target Release**: 3.2.0 (current rc line rc39–rc42)
**Status**: Draft

## Purpose

**TL;DR**: Close the remaining live coordination/merge git bugs so 3.2.0 ships without pernicious merge failures.

The 3.2.0 release gate identified a cluster of 13 coordination-topology merge bugs where git operations break under specific worktree states. A joint Debugger-Debbie / Paula-Patterns validation pass against HEAD (956ab0e3e) confirmed that the cluster's structural spine was already drained by PR #1850 (commit 8544012fa), rc41 (c5a10ce56), and rc42 (9c8bff06f) — seven issues are stale-open describing retired behavior. What remains live is three root-cause classes plus narrow residuals of two drained classes. This mission ships those small, localized fixes with regression ratchets so unattended merges complete reliably, and performs the issue hygiene that stops the tracker from double-counting fixed defects.

**Source analyses** (committed with this mission): [validation/cluster-validation-brief.md](validation/cluster-validation-brief.md), [validation/debbie-analysis.md](validation/debbie-analysis.md), [validation/paula-analysis.md](validation/paula-analysis.md). Findings were also recorded as comments on each GitHub issue on 2026-06-12.

## User Scenarios & Testing

### Primary Scenario — Unattended coordination-topology merge (Class B, #1826)

An operator runs `spec-kitty merge` on a coordination-topology mission with two or more lane work packages. Today, the Stage-1 lane merges and mission-number baking advance the mission branch ref from detached temporary worktrees, leaving the coordination worktree behind its own checked-out branch; the subsequent bookkeeping commit trips the safe-commit backstop ("working tree is behind HEAD") and the merge halts mid-flight, requiring a manual hard reset. **Expected**: the merge runs to completion unattended; after every internal ref advance, the coordination worktree is consistent with its branch; the backstop never fires on this self-inflicted divergence.

### Scenario 2 — Validation that does not move the operator's checkout (Class C, #1861 Part 1)

An operator on a working branch runs `finalize-tasks --validate-only` to check planning artifacts. Today the command switches the git checkout to the mission target branch even in validate-only mode — a nominally read-only command mutating repository state. **Expected**: validate-only mode leaves the current branch, index, and working tree untouched.

### Scenario 3 — Honest failure on broken lane workspaces (Class D, #1833)

A review claim previously minted an empty "husk" directory under `.worktrees/` (no git metadata inside). When the operator later runs a task move, the workspace resolver accepts the husk, and git commands silently fall through to the primary repository — producing false verdicts like "No implementation commits on lane branch!" or dirty-tree failures sourced from the primary checkout's bookkeeping noise. **Expected**: a directory that is not an actual git worktree is treated as a resolution *failure* with a structured, named error; a failed worktree creation is an error, not a warning; a doctor check lists (and can remove) husk entries so operators self-recover.

### Scenario 4 — Coordination missions not blocked by finalize residue (Class A residual, #1814)

After task finalization on a coordination-topology mission, untracked copies of lane metadata and task files remain on the primary checkout. A later analysis-recording step refuses to run because the primary tree looks dirty — a deadlock the operator cannot resolve through any documented command. **Expected**: finalize staging leaves no residue on the primary checkout; analysis recording proceeds under coordination placement.

### Scenario 5 — Merge-driver hardening holds the line (Class F residuals, #1736)

The status-event JSONL merge driver and lane-merge subprocesses currently rely on inline environment construction, a broad exception mask that can swallow genesis-corruption signals, and untested mixed-timestamp sorting. **Expected**: the environment is built by one helper used by every subprocess call; the lane-status read catches only the two expected error types; mixed-schema event logs sort deterministically under test.

### Edge Cases

- Coordination worktree carries uncommitted unique state at resync time → resync MUST refuse loudly (no silent `reset --hard` data discard). (FR-001 guard)
- Pre-existing husk directories on operator machines start producing explicit errors after the Class D fix → doctor check ships in the same release so recovery is self-serve. (FR-003/FR-007)
- Narrowed exception handling in coordination status reads may surface previously-swallowed errors → land with/after the resync fix so stale-worktree reads don't newly throw. (C-004)
- A crash between baseline recording and its commit leaves a pending baseline on re-run (#1827 edge) → covered by the new regression test; behavior documented.
- Any *new* `update-ref` call site added during this mission would re-inherit #1826 → ratchet test forbids raw `update-ref` outside the shared path. (FR-008)

## Requirements

### Functional Requirements

| ID | Requirement | Source issues | Status |
|---|---|---|---|
| FR-001 | After every internal ref advance performed by the merge pipeline (lane→mission merges, mission-number baking), any worktree that has the advanced branch checked out is resynchronized so its index and working tree match the branch head; resync refuses with a loud, named error if that worktree holds uncommitted unique state. | #1826 | Proposed |
| FR-002 | `finalize-tasks --validate-only` performs no git checkout, branch switch, staging, or any other working-tree mutation; the operator's `HEAD` is identical before and after. | #1861 Part 1 | Proposed |
| FR-003 | A resolved lane workspace must be an actual git worktree: existence checks require git metadata (not bare directory existence); workspace resolution that falls through to a non-worktree path is a structured failure, never a silent success against the primary repository. | #1833 | Proposed |
| FR-004 | Failed lane-worktree creation during review claim is a hard error (not a warning), and the review lock is acquired only after the workspace exists. | #1833 | Proposed |
| FR-005 | Task-move operations verify the resolved workspace is the git toplevel they expect before issuing any git command, and report a structured resolution-failure error otherwise. | #1833 | Proposed |
| FR-006 | Task finalization on coordination-topology missions leaves no untracked planning-artifact residue (lane metadata, task files, matrices) on the primary checkout; analysis recording is not blocked by such residue. | #1814 | Proposed |
| FR-007 | A doctor check reports `.worktrees/` entries that are not actual git worktrees (husks) and offers removal, so operators self-recover from pre-existing husks. | #1833 | Proposed |
| FR-008 | Regression ratchets exist for each fixed class: (a) no raw branch-ref advance outside the shared resync path; (b) every lane-merge subprocess uses the shared environment helper; (c) mixed-timestamp event logs sort deterministically; (d) coordination status reads catch only expected error types; (e) status reads in retrospective gating route through the canonical status surface. | #1826, #1736, #1735 | Proposed |
| FR-009 | The two remaining coordination-unaware status reads (retrospective completion gate and retrospect command surface) route through the canonical status-surface resolver. | #1735 | Proposed |
| FR-010 | A coordination-topology regression test proves the post-merge baseline commit is recorded in the merged target branch (closing the #1827 test gap). | #1827 | Proposed |
| FR-011 | The seven stale-open fixed issues are closed citing the landed commits, and the four partially-fixed issues are re-scoped to their residuals: close #1770, #1789, #1816, #1771, #1571, plus #1784-core (dup of #1777) and #1735-core; update #1814, #1736, #1833, #1861 to residual scope. | all | Proposed |
| FR-012 | The safe-commit backstop message names the actual divergence cause (which worktree, which ref, what state) instead of a generic "working tree is behind HEAD"; failing layers in the fixed paths name the resolution they used. | #1784 P3, #1826 | Proposed |
| FR-013 | `upgrade --dry-run` does not print a success message implying changes were applied. | #1784 P3 | Proposed |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | Unattended completion: a coordination-topology mission with ≥2 lane merges plus mission-number baking completes `spec-kitty merge` with zero manual git interventions. | 0 interventions in the end-to-end regression test | Proposed |
| NFR-002 | No silent data discard: every automated resync/cleanup either proves the target holds no unique uncommitted state or aborts with a named error. | 100% of resync paths guarded; covered by test | Proposed |
| NFR-003 | Diagnostic quality: every new failure path names the workspace/ref/placement it resolved, never a raw git error alone. | All new error strings include resolution context; asserted in tests | Proposed |
| NFR-004 | Code quality gate: new code passes ruff and mypy --strict with zero suppressions; new-code test coverage ≥90%. | 0 new `noqa`/`type: ignore`; coverage report ≥90% on changed lines | Proposed |
| NFR-005 | Existing ratchets stay green: the #1850/#1719 regression suites (git-op guard, daemon reaper, retrospect committability, execution-context parity) pass unmodified. | 0 regressions in named ratchet tests | Proposed |

### Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Stability only — no architecture rework. No coordination-topology changes, no safe-commit semantics changes, no resolver API redesign, no status-model or daemon work, no worktree-naming allocator unification, no removal of the branch-positioning shim. These are deferred to one umbrella issue under epic #1666. | Accepted |
| C-002 | Fix scope is the three known ref-advance sites only; the "retire all direct ref advances" invariant beyond the merge pipeline is follow-up. | Accepted |
| C-003 | #1814 fix is cleanup-at-source (writer side); the coordination-owned-status-files exclusion list must NOT also be widened (no double mechanism). | Accepted |
| C-004 | Ordering: issue hygiene first (unblocks triage); the exception-narrowing in coordination status reads lands with or after the worktree resync fix; backstop message wording lands with or after the resync fix to avoid churn. Otherwise fixes are mutually independent. | Accepted |
| C-005 | All work lands via PR to origin/main; `spec-kitty merge` touches local main only; terminology guard (`pytest tests/architectural/test_no_legacy_terminology.py`) runs before push. | Accepted |

## Success Criteria

1. **Unattended merge reliability**: A coordination-topology mission with two lanes merges end-to-end without manual intervention — verified by a new integration test that previously failed with the backstop error. (maps: FR-001, NFR-001)
2. **Read-only commands are read-only**: validate-only finalization leaves `HEAD` byte-identical; verified by before/after assertion in test. (FR-002)
3. **No silent fall-through**: With a planted husk directory, every affected command surface produces a structured resolution error naming the husk path — zero git commands execute against the primary repo from a husk resolution. (FR-003–FR-005)
4. **No residue deadlock**: After finalize on a coordination mission, `git status --porcelain` on the primary checkout shows no planning-artifact residue, and analysis recording succeeds. (FR-006)
5. **Class cannot silently return**: All five ratchets (FR-008) and the baseline regression test (FR-010) are in the tree and green in CI. (FR-008, FR-010)
6. **Tracker reflects reality**: 0 of the 13 cluster issues remain open with stale scope — 7 closed citing commits, 4 re-scoped to residuals, #1826/#1861 closed by this mission's fixes. (FR-011)

## Key Entities

- **Coordination worktree**: the checkout of the mission coordination branch under `.worktrees/`, owner of planning/status artifacts under coordination topology.
- **Primary checkout**: the operator's main repository checkout; must stay clean of coordination residue.
- **Lane worktree**: per-lane execution workspace; must be an actual git worktree to be resolvable.
- **Husk**: a directory under `.worktrees/` lacking git metadata — a failed/partial workspace creation artifact; must be treated as resolution failure.
- **Safe-commit backstop**: the last-line guard detecting working-tree/HEAD divergence before bookkeeping commits; the detector, not the defect.
- **Ref advance**: an internal plumbing-level branch-pointer update performed by the merge pipeline outside any checkout.

## Domain Language

- Canonical: **Mission** (never "feature" in new text); **coordination topology** (not "coord mode"); **husk** for non-worktree `.worktrees/` entries (term introduced by issue #1833 — keep it).
- "Resync" means making a worktree consistent with its checked-out branch after an external ref advance — it is not a merge and not a rebase.

## Assumptions

1. PR #1850 (8544012fa), rc41 (c5a10ce56), rc42 (9c8bff06f) remain on main and are not reverted; the seven "fixed at HEAD" verdicts depend on them.
2. The coordination worktree carries no unique uncommitted state *by design* during merge bookkeeping; FR-001's guard converts a violation of this design assumption into a loud error rather than silent discard.
3. GitHub issue hygiene (FR-011) is authorized — validation comments were already posted to all 13 issues on 2026-06-12 with the user's approval.
4. The follow-up architecture umbrella (resolver strangler completion, single ref-advance helper rollout, allocator unification, AC10 lint expansion) will be filed under epic #1666 during this mission's hygiene work but is explicitly out of scope to implement.

## Out of Scope

See C-001/C-002. Additionally: the foreground `materialize()` write of tracked status files (accepted residual of closed Class E), `doctor.py` god-module split (#1623), and any change to merge strategy semantics.

## Review & Acceptance Checklist

*Updated by `/spec-kitty.analyze` and review phases.*

- [ ] All FRs map to at least one acceptance test
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Constraints C-001..C-005 respected by the plan
- [ ] Success criteria measurable and technology-agnostic
