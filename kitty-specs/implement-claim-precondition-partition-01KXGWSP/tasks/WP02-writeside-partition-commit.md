---
work_package_id: WP02
title: Write-side partition-aware planning-artifact commit
dependencies:
- WP01
requirement_refs:
- FR-003
- NFR-001
tracker_refs: []
planning_base_branch: mission/2533-pr-bound-coord-claim-precondition
merge_target_branch: mission/2533-pr-bound-coord-claim-precondition
branch_strategy: Planning artifacts for this mission were generated on mission/2533-pr-bound-coord-claim-precondition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/2533-pr-bound-coord-claim-precondition unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1278013"
shell_pid_created_at: "1784066037.61"
history:
- at: '2026-07-14T19:15:00Z'
  actor: claude
  note: WP authored after post-tasks squad — write-side partition split sized in per operator decision.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_implement_writeside.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/implement.py
- tests/specify_cli/cli/commands/test_implement_writeside.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration.
You are the **implementer**.

## Objective

Close the write-side half of #2533's partition inconsistency: when a genuinely-dirty
PRIMARY planning artifact must be committed on a `coord` mission, it must land on the
**primary/target ref**, never on the coordination branch. Today
`_commit_planning_artifacts_transaction` commits every file through one transaction to
a single `destination_ref` (the coord branch on a coord mission), violating FR-003 /
INV-1. Make the commit **partition-aware** (two transactions), mirroring
`commit_router._group_files_by_partition`.

**Depends on WP01** — reuse the same `is_coordination_artifact_residue_path` partition
predicate WP01 wired in; do not invent a second classification.

## Context

- **Read `../contracts/resolve-precondition-ref.md` (write-side section)** — authoritative.
- Target: `_commit_planning_artifacts_transaction` in `src/specify_cli/cli/commands/implement.py`
  (~`:577`). It computes `effective_destination_ref` (`:637-642`) and commits all
  `files_to_commit` through one `BookkeepingTransaction.acquire(..., destination_ref=…)`
  (`:652-657`).
- **Why the WP01 repro doesn't cover this**: in the reported bug the artifacts are
  already committed → `files_to_commit` is empty → the transaction never runs. This WP
  covers the *genuinely-dirty PRIMARY on coord* case, which needs its own red test.
- **Boundary (C-002)**: additively partition the existing transaction flow; do NOT
  restructure unrelated parts of `implement.py`; keep `mission_runtime/*` read-only.

## Subtasks

### T006 — RED test: dirty PRIMARY on coord lands on primary

1. Create `tests/specify_cli/cli/commands/test_implement_writeside.py` (real `tmp_path`
   git repo, `_make_meta(..., with_coord=True)`).
2. Construct a coord mission with a **genuinely-dirty** PRIMARY `spec.md` (modified,
   needs commit) plus a dirty COORD `status.events.jsonl`.
3. Drive `_commit_planning_artifacts_transaction` (via `_ensure_planning_artifacts_committed_git`
   with `auto_commit=True`, or the function directly).
4. Assert (RED against current code): `spec.md` is committed on the **primary/target
   branch** (not the coord branch), and `status.events.jsonl` on the coord branch.
   Current code commits both to the coord ref → the `spec.md`-on-primary assertion fails.

**Validation**: the test FAILS against current code with `spec.md` landing on coord.

### T007 — Partition-aware two-transaction commit

- In `_commit_planning_artifacts_transaction`, split `files_to_commit` into PRIMARY
  (`not is_coordination_artifact_residue_path(path)`) and COORD-residue groups.
- Commit the PRIMARY group to the primary/target ref and the COORD group to the coord
  ref (two `BookkeepingTransaction`s, or the existing transaction parameterized per
  group). Reuse the resolver/predicate from WP01 — one authority (NFR-004).
- Preserve existing behavior for single-branch/flat missions (one ref, one group) and
  for the empty-`files_to_commit` early return.

**Validation**: T006 turns GREEN; single-branch missions unaffected.

### T008 — Campsite (S1192) + quality gates

- **S1192 (ADJACENT)**: hoist `_BANNER_OPEN = "[bold yellow]"` / `_BANNER_CLOSE =
  "[/bold yellow]"` module constants and use them in `_print_workspace_ready_banner`
  (~`:1194`). Note the literal appears ~8× in `implement.py`; after hoisting, re-run
  `ruff`/verify Sonar S1192 is satisfied for the banner function (the `title=` uses at
  ~`:914/:928` may remain — leave them, different close tag).
- `uv run ruff check src/specify_cli/cli/commands/implement.py`;
  `uv run mypy --strict src/specify_cli/cli/commands/implement.py`; new test green.
  Zero new issues; complexity ≤ 15.

## Branch Strategy

- Planning/base + merge target: `mission/2533-pr-bound-coord-claim-precondition`.
- Depends on WP01 (partition predicate). Worktree allocated per lane from `lanes.json`
  by `spec-kitty agent action implement WP02 --agent claude`.

## Definition of Done

- [ ] `_commit_planning_artifacts_transaction` commits PRIMARY to primary ref, COORD to
      coord ref (two-transaction partition); FR-003 / INV-1 satisfied.
- [ ] T006 red-before / green-after; single-branch commit path unaffected.
- [ ] S1192 banner constants folded; ruff + mypy --strict zero new issues.
- [ ] Additive only — no unrelated restructuring of `implement.py`; `mission_runtime/*` untouched.

## Risks & Reviewer Guidance

- **Transaction semantics** — reviewer confirms two-transaction commit preserves
  atomicity expectations and the empty-set early return; no double-commit.
- **One authority** — the partition predicate is the WP01 `is_coordination_artifact_residue_path`
  path, not a new literal.
- **Red-first** — the dirty-PRIMARY-on-coord test must fail against pre-fix code.

## Activity Log

- 2026-07-14T21:28:15Z – claude:sonnet:python-pedro:implementer – shell_pid=1222107 – Assigned agent via action command
- 2026-07-14T21:53:09Z – claude:sonnet:python-pedro:implementer – shell_pid=1222107 – Ready for review: partition-aware two-transaction planning-artifact commit (T007) + S1192 banner constants (T008). RED-before/GREEN-after confirmed via git-stash verification. Existing WP01/WP03 tests unaffected.
- 2026-07-14T21:54:00Z – claude:opus:reviewer-renata:reviewer – shell_pid=1278013 – Started review via action command
- 2026-07-14T22:01:26Z – user – shell_pid=1278013 – Review passed (reviewer-renata). FR-003/INV-1 write-side partition verified: _commit_planning_artifacts_transaction splits files_to_commit via is_coordination_artifact_residue_path (WP01 authority, NFR-004) into PRIMARY->planning_branch and COORD-residue->coord ref, two transactions. RED-first proven: pre-fix spec.md landed on coord branch through one collapsed txn; post-fix lands on target. Boundary clean (only implement.py + new test_implement_writeside.py). C-004 respected: placement_ref-not-None seam path behavior-preserved, test_effective_destination_ref_is_placement_ref_verbatim green (5/5). Empty-set early return + flat/single-branch one-txn collapse preserved (regression test green). S1192 banner constants hoisted+used; title= bulk-edit banners correctly left (different close tag). ruff+mypy --strict clean, complexity<=15, 18/18 tests green. FALLBACK ADJUDICATION: the protected-branch elif is a SAFE edge-case guard, not an FR-003 hole. planning_branch=meta target_branch (real coord missions use a dedicated feature branch, never main/master); fallback needs corrupt/misconfigured meta (target_branch absent-or-protected while coordination_branch present) AND context-resolution failure (placement_ref None). In that degenerate state FR-003 is unsatisfiable anyway: WorkflowMutationPolicy.assert_allowed refuses protected-ref commits (PROTECTED_BRANCH_REFUSED), so partitioning PRIMARY->protected would hard-fail the claim; the fallback degrades gracefully to the historical coord txn per the C-004 strangler precedent. Not reachable for any valid mission shape. NOTE for PR body: (1) fallback elif branch has no direct unit test (Sonar new-code-coverage advisory; branch is unreachable-in-production defensive code); (2) the placement_ref-not-None seam still commits one-ref-for-everything, so FR-003 on that path remains open under #2160 (explicitly deferred by C-004); (3) trailing summary print says 'committed to coordination branch' even on the partition path where PRIMARY went to planning_branch -- cosmetic diagnostic imprecision, actual commits correct.
