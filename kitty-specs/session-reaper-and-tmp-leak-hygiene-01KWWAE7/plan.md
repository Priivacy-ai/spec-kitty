# Implementation Plan: Session-scoped test reaper + /tmp prompt namespacing + workspace-context tombstone

**Branch**: `fix/session-reaper-and-tmp-leak-hygiene` | **Issues**: #1842 (subsumes #1634) | **Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

## Summary

A fresh re-audit (`d63ec2152`) shows 5 of 8 leak classes already fixed; the durable, still-live work is three concerns that decompose into three WPs: (1) a **controller-gated `pytest_sessionfinish` snapshot-delta reaper** in root `tests/conftest.py` that self-heals test-created `test-feature-*` missions/branches + git-unregistered `.worktrees/` husks + the current run's `/tmp` residue, plus retiring the `.gitignore` masks and adding a reap-then-assert pollution check (FR-001/002/004/006, NFR-001/002); (2) **`/tmp` prompt-writer namespacing** for the three flat-`/tmp` writers — `prompt_builder.py`, `workflow.py`, and `decision.py`'s two unbounded `spec-kitty-composed-*` `mkstemp` sites (FR-003); (3) the **LC-6 workspace-context tombstone** — targeted `delete_context` on cancel (since `cleanup_orphaned_contexts` no-ops while a worktree lives) and a merge-completion hook ordered *after* `executor.py`'s worktree removal, plus removing the 14 committed 059/060 orphans (FR-005). Build on #2181's frozen `/tmp` ratchet; defer its 99-file burn-down.

## Technical Context

**Language/Version**: Python 3.11 (repo pinned)
**Primary Dependencies**: `pytest` + `pytest-xdist` (session hooks, controller detection), `pathlib`/`shutil`/`subprocess` (git worktree/branch ops), `tempfile`
**Storage**: REPO_ROOT working tree (`kitty-specs/`, `.worktrees/`, `.kittify/workspaces/`) + shared `/tmp`
**Testing**: root `tests/conftest.py` (reaper), `tests/e2e/conftest.py` (pollution-baseline shape to reuse), unit tests for the reaper/namespacing/tombstone
**Target Platform**: local (serial + `-n auto` xdist) + CI
**Project Type**: single project (test-infra reaper + two runtime changes)
**Performance Goals**: reaper adds negligible session time (one snapshot + one delta reap on the controller)
**Constraints**: controller-gated (no worker races); snapshot-delta (never delete pre-existing); reuse the e2e pollution-baseline shape; preserve merge/cancel semantics; `mypy --strict` + `ruff` clean; no new suppressions
**Scale/Scope**: test-side (`tests/conftest.py`, `.gitignore`, reaper unit tests) + runtime (`prompt_builder.py`, `workflow.py`, `decision.py`, `merge/executor.py`, cancel path, `workspace/context.py` consumers) + remove 14 orphan JSONs

## Charter Check

*GATE: must pass before task decomposition.*

- **Evidence-first / re-audited** — grounded in a fresh `d63ec2152` re-audit (not the 4-week-stale audit); the post-spec squad already corrected a missed writer + the LC-6 model. ✅
- **Non-vacuous / red-first** — the reaper is proven by seeding an artifact (reaped) vs a pre-existing one (untouched); the pollution assertion reds on a seeded leak; the tombstone proven by a merged mission leaving no orphan. ✅
- **Canonical sources** — reuse the e2e pollution-baseline shape + the existing `delete_context`/`cleanup_orphaned_contexts` API; do not invent a new snapshot mechanism. ✅
- **Never retry-to-green / no masking** — retire the `.gitignore` masks (surface leaks) rather than hide them. ✅
- **Draft-PR-first / operator decides**; **quality gates** — `ruff` + `mypy --strict` clean. ✅

No violations → Complexity Tracking not required.

## Project Structure

### Documentation (this mission)
```
kitty-specs/session-reaper-and-tmp-leak-hygiene-01KWWAE7/
├── spec.md · research.md · plan.md · tasks.md
```

### Source / deliverables (repository root)
```
tests/conftest.py                                   # WP01: sessionstart snapshot + sessionfinish reaper (controller-gated, snapshot-delta)
.gitignore                                          # WP01: retire the test-feature-* masks (143-144)
tests/architectural/ or tests/.../test_reaper*.py   # WP01: reaper unit tests + pollution assertion
src/runtime/next/_tmp_namespace.py (or shared const) # WP02: SINGLE source of truth for the /tmp prompt-namespace prefix — consumed by the 3 writers AND WP01's reaper (no drift)
src/runtime/next/prompt_builder.py                  # WP02: route spec-kitty-next-* through the shared namespace
src/runtime/next/decision.py                        # WP02: route both spec-kitty-composed-* mkstemp sites through the shared namespace
src/specify_cli/cli/commands/agent/workflow.py      # WP02: route spec-kitty-implement|review-* through the shared namespace
src/specify_cli/merge/executor.py                   # WP03: merge-completion targeted delete_context (order-independent — no worktree-removal ordering)
src/specify_cli/coordination/status_transition.py (emit_status_transition_transactional) + status/emit.py (fallback)  # WP03: cancel tombstone — coord topology uses append_event NOT emit.py; gate all-lane-terminal, WP->workspace_name -> delete_context
.kittify/workspaces/059-*.json, 060-*.json          # WP03: remove the 14 committed orphans
```

**Structure Decision**: single project, three cohesive WPs — a test-side reaper (WP01), runtime prompt-writer namespacing (WP02), and the runtime workspace-context tombstone (WP03).

## Implementation Concern Map

### IC-01 → WP01 — Session reaper + mask retirement + pollution assertion
- **Purpose**: self-heal all test-created REPO_ROOT + `/tmp` residue; make a leak regression visible.
- **Relevant requirements**: FR-001, FR-002, FR-004, FR-006; NFR-001, NFR-002; SC-001, SC-002, SC-003.
- **Affected surfaces**: root `tests/conftest.py` — `pytest_sessionstart` snapshots (`kitty-specs/*`, `git branch --list 'kitty/*'`, `.worktrees/*`, `.kittify/workspaces/*.json`); `pytest_sessionfinish` (controller-gated `session.config.workerinput is None`) reaps the delta matching `test-feature-*` / `*-123-test-feature` / `*golden-path-demo*` dirs + branches + git-unregistered `.worktrees/*` (`prune` then `rmtree` the not-in-`git worktree list --porcelain` delta) + current-run `/tmp/spec-kitty-{next,implement,review,composed}-*` + `spec-kitty-test-homes/<run_uid>/`. Retire `.gitignore:143-144`; add a pollution assertion (reuse `assert_no_source_pollution` shape) that reds if the reaped delta was non-empty.
- **Snapshot shape (C-001)**: a **narrow name-pattern list** at `sessionstart` (matching entries only), reap the *new* ones at finish — NOT the e2e `assert_no_source_pollution` deep per-file `rglob` mtime inventory (~6,900 files → slow + false-red on the live REPO_ROOT).
- **Sequencing/depends-on**: the `/tmp` sweep **imports the shared temp-namespace constant from WP02** (single source of truth — no hand-coordinated prefix), so WP01's reaper and WP02's writers cannot drift; a test asserts a writer's output falls under the reaper's swept root.
- **Risks**: worker races (mitigate via controller gate `workerinput is None`); deleting pre-existing artifacts (mitigate via snapshot-delta); the `git worktree prune`-blind husk case (explicit `rmtree` of the delta).

### IC-02 → WP02 — /tmp prompt-writer namespacing (three writers)
- **Purpose**: stop the flat-`/tmp` accumulation (esp. the unbounded `spec-kitty-next-*` and `spec-kitty-composed-*`).
- **Relevant requirements**: FR-003; SC-001.
- **Affected surfaces**: one shared per-repo/per-run-namespaced sweepable temp-root helper, applied to `prompt_builder.py` (`spec-kitty-next-*`), `decision.py` (both `spec-kitty-composed-{action}-*` `mkstemp` sites ~:610/:656), and `workflow.py` (`spec-kitty-implement|review-*`). The namespace prefix lives in **one shared constant/module** that WP01's reaper imports (single source of truth); add a test asserting a writer's output path falls under the reaper's swept root (drift-proof).
- **Sequencing/depends-on**: WP01's reaper imports the shared constant — **no manual prefix coordination** across WPs.
- **Risks**: consumers read the returned path — preserve the return contract; don't break the runtime `next` loop.

### IC-03 → WP03 — LC-6 workspace-context tombstone (runtime)
- **Purpose**: tombstone `.kittify/workspaces/*.json` on merge-completion + cancel; remove the existing 14 orphans.
- **Relevant requirements**: FR-005, FR-006; C-004; SC-004.
- **Affected surfaces**: **cancel seam** → hook `emit_status_transition_transactional` (`coordination/status_transition.py`, **BOTH** coord-topology + fallback branches — `emit.py` alone never fires for a coord mission, which is the target case); gate on **all lane WPs terminal** (mirror `status/doctor.py`'s `all(wp.lane in {done, canceled})`), map WP→lane `workspace_name`, call targeted `delete_context(workspace_name)` (a pure unlink, its **first external caller**; `cleanup_orphaned_contexts` no-ops while the worktree lives — don't use it). **Merge-completion** → the same targeted `delete_context` in `merge/executor.py` — **order-independent** (no worktree-removal ordering). Remove the 14 committed `059-*`/`060-*` JSONs. Writers for context: `workspace/context.py:305 save_context` from `implement_support.py:127,167` + `recovery.py:732`.
- **Verify-before-implement**: confirm the lane worktree actually persists through cancel (so the tombstone is testable) and pin the exact transition seam before decomposing WP03.
- **Sequencing/depends-on**: independent of WP01/WP02.
- **Risks**: ordering (pre-removal cleanup finds a live worktree → no-op); breaking merge/cancel semantics (add only the tombstone — C-004); the cancel no-op trap (use targeted delete).
