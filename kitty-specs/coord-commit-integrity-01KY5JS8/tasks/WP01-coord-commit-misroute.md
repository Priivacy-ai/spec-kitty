---
work_package_id: WP01
title: 'Coord-commit correctness + #2861 causation'
dependencies: []
requirement_refs:
- FR-002
- NFR-001
- NFR-002
planning_base_branch: remediation/coord-trust-2841
merge_target_branch: remediation/coord-trust-2841
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-trust-2841. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-trust-2841 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-coord-commit-integrity-01KY5JS8
base_commit: e5261b2740fca195fc35a2965f6975e573dac830
created_at: '2026-07-22T20:05:09.183358+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- at: '2026-07-22T19:33:57Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/regression/test_coord_commit_integrity_e2e.py
- tests/regression/test_2861_causation_repro.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- tests/regression/test_coord_commit_integrity_e2e.py
- tests/regression/test_2861_causation_repro.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned profile from the doctrine pack and adopt its directives/tactics:

```
/ad-hoc-profile-load python-pedro
```

(If that command is unavailable, read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` directly.) State which directives/tactics you applied in your handoff note. This is `spec-kitty` core coordination code — high rigour.

## Objective

Close the real manual-review blocker. The pre-plan squad established (and you must confirm LIVE) that
#2861's "commit refused" is the **misroute-to-legacy** coord-commit bug (`SafeCommitHeadMismatch`), NOT the
actor-shape bug. Make that misroute unrepresentable, and prove the modern path is already correct — with a
REAL-repo e2e (no stubbed `safe_commit`).

Read `plan.md` (IC-01), `research.md` (Decisions A, B, G), `contracts/commit-path-contract.md`, and
`data-model.md` (the commit-path routing diagram) before coding. `git/commit_helpers.py` (`safe_commit`) is
READ-ONLY — it is already correct; you feed it the right worktree root.

## Branch Strategy

Planning base + merge target: **`remediation/coord-trust-2841`** (coord topology). Worktree per lane via
`spec-kitty implement WP01`. Lane a; WP02 follows you sequentially in this lane. Do not create worktrees by hand.
Use `SPEC_KITTY_SYNC_MINIMAL_IMPORT=1` if a daemon `safe_commit` race appears.

## Subtasks

### T001 — NFR-002 live #2861 causation repro FIRST (red-first)

Before touching product code, write `tests/regression/test_2861_causation_repro.py`. **Reusable fixture
(pedro):** `tests/characterization/test_trio_json_envelope.py::coord_repo_for_review`
(`_build_mission_repo(coord=True, materialize_coord=True, wp_lane="for_review")`) is the exact shape — it
already seeds the WP into `for_review` via REAL status-event transitions (frontmatter-lane seeding alone
won't satisfy the event-log-sole-authority model). Drive `agent action review WP## --agent
claude:opus:reviewer-renata:reviewer` with NO `--invocation-id`.

**The verdict MUST be a PERSISTED ASSERTION (renata — not a prose checkbox):** the test asserts the concrete
failure mode, e.g. `assert failure_mode is FailureMode.MISROUTE_TO_LEGACY` / `SafeCommitHeadMismatch` in the
output, AND `assert` the actor "invalid value" warning is non-fatal. The test goes RED if the causation is
other than recorded. A handoff note alone does NOT satisfy T001. This assertion is the object WP02's US2 AC-3
gate reads (see WP02).

### T002 — Campsite (complexity headroom) BEFORE the guard

- Extract `_handle_commit_failure(...)` from the two copy-paste rollback + `_record_receipt("refused")`
  except-arms in `workflow_executor.py:~140` (`commit_workflow_change`) — this buys headroom before T003
  adds the guard (the function is C14; do NOT push it over 15).
- Delete the dead triplicate `workflow.py:~672 _resolve_git_common_dir` (grep confirms zero production
  callers — only a stale test whose real callers moved to `workflow_cores.py`) + retire that stale test.

### T003 — FR-002(a) misroute-to-legacy fail-loud guard

In `workflow_executor.py:~217` (the `_load_coord_branch_meta` → path split, ~`commit_workflow_change`): a
**coord-routed topology** whose identity triple `(coordination_branch, mission_id, mid8)` is INCOMPLETE must
**fail loud** — it must NOT fall through to `_commit_via_legacy_safe_commit` and commit coord paths from
`repo_root`. Either raise a clear error, or resolve the coord worktree via `CoordinationWorkspace.resolve`
and route to the modern path. Add a red-first unit test proving the incomplete-triple coord case fails loud.

### T004 — FR-002(b) legacy porcelain pre-check against the resolved root

In `workflow.py:~599` (`_commit_via_legacy_safe_commit`, the #2684 nothing-to-commit guard): the
`git status --porcelain` pre-check runs at `cwd=repo_root`, returning empty for gitignored `.worktrees/`
coord files → a phantom "already committed" early-return. Run the pre-check against the **resolved worktree
root** (via `CoordinationWorkspace.resolve`), scoping paths relative to it — so a coord file is correctly
seen as dirty. Reuse the ONE `CoordinationWorkspace.resolve` authority (coordinate the shared helper with WP04).

### T005 — NFR-001 real-repo e2e (no stubbed safe_commit) + modern-path regression

`tests/regression/test_coord_commit_integrity_e2e.py`: real `git init` + real `git worktree add` (via
production `CoordinationWorkspace.resolve`), `CliRunner` on `agent action implement`/`review`. Assert
placement via `git show <coord_ref>:<path>` vs `git show <target_ref>:<path>` (NOT filesystem state, so a
stray uncommitted file can't false-pass). **Scope trimmed to WP01-owned invariants (paula — do NOT reach
into WP03-owned behavior):**
- status.events.jsonl on coord, absent on target (WP01-observable modern-path regression);
- negative case: `safe_commit(worktree_root != destination_ref)` → `SafeCommitHeadMismatch`;
- a regression proving `_commit_via_coordination_transaction` (modern) still threads the coord worktree root
  (NO code change to the modern path).
**The review-cycle-PRIMARY placement assertion is REMOVED from here and MOVED to WP03** (it is WP03-owned;
WP01↔WP03 have no dependency edge, so an `xfail` here would never flip inside WP01's lane — a green-washed
hole). Do NOT add an `xfail` for it.
**Anti-stub guard (renata):** this e2e drives ALL commits solely through `CliRunner.invoke(agent action …)`;
the test module contains NO monkeypatch/Mock of `safe_commit`, `CoordinationWorkspace.resolve`, or the git
plumbing, and performs NO test-side commit of mission artifacts (a stubbed resolve + test-side commit would
false-pass `git show`).

## Definition of Done

- [ ] T001 repro lands FIRST and records the #2861 causation verdict (FR-002 vs FR-006).
- [ ] Misroute-to-legacy is fail-loud for coord topology + incomplete triple (never commits coord paths from repo_root).
- [ ] Legacy porcelain pre-check runs against the resolved worktree root; no phantom "already committed" for coord files.
- [ ] Modern path unchanged (regression proves it); `safe_commit` untouched (`git/` read-only).
- [ ] Real-repo e2e green (real `git worktree add`, `git show`-based assertions, `SafeCommitHeadMismatch` negative case) — NO stubbed `safe_commit`.
- [ ] Campsite: `_handle_commit_failure` extracted; dead `_resolve_git_common_dir` triplicate + stale test deleted.
- [ ] `uv run --extra test ruff check` + `uv run --extra test mypy` clean on owned files; every touched function ≤15 (do NOT inflate `workflow_executor.py:845`).
- [ ] Tests green FOREGROUND with `uv run --extra test pytest` (NOT bare `pytest` — lane venv; see #2803 hazard).

## Reviewer guidance

Verify: the causation repro actually ran and recorded a verdict; the misroute guard fails loud (not a
silent reroute that could hide a real topology bug); the porcelain runs against the coord root; the e2e uses
a REAL worktree and `git show` (not filesystem/stubs); the modern path has zero code change. Confirm
`safe_commit` and `commit_helpers.py` are untouched.

## Risks

- Blanket "route everything to modern" would regress legitimately-legacy callers — prefer fail-loud + the leaf fix.
- Stubbing `safe_commit` in the e2e would defeat NFR-001 — use the real harness.
- `uv run pytest` (bare) in a lane silently tests PRIMARY src (#2803) — ALWAYS `uv run --extra test pytest`.
