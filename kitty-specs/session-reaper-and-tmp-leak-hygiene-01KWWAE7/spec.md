# Mission Specification: Session-scoped test reaper + /tmp prompt namespacing + workspace-context tombstone

**Status**: Draft
**Issues**: [#1842](https://github.com/Priivacy-ai/spec-kitty/issues/1842) (subsumes [#1634](https://github.com/Priivacy-ai/spec-kitty/issues/1634))

## User Scenarios & Testing *(mandatory)*

**Primary actors**: a contributor running the test suite against a live checkout; the operator whose `doctor`/mission surfaces get polluted by test residue.

**Grounding (fresh re-audit of `d63ec2152`, 2026-07-06)**: Stijn's 2026-06-11 8-class audit is 4 weeks / 100+ commits stale. **5 of 8 classes are already fixed** (LC-1 in-tree, LC-2, LC-5, LC-7 via #959, LC-8). The durable, still-live work:

- **LC-3 / LC-4** — two runtime writers dump prompts into a **flat shared `/tmp`** with no per-run namespace or sweep: `src/runtime/next/prompt_builder.py` (`spec-kitty-next-{agent}-{slug}-{action}[-{wp}].md`, ULID-in-name → **unbounded** accumulation) and `src/specify_cli/cli/commands/agent/workflow.py` (`spec-kitty-{implement|review}-*`). An e2e run leaves a `golden-path-demo` prompt behind.
- **N1 (new)** — `/tmp/spec-kitty-test-homes/<run_uid>/` (per-worker HOME isolation, `tests/conftest.py`) is **never cleaned**: **166 dirs / 144 MB**, +1 per run. Largest disk leak, cheap fix.
- **LC-6** — `.kittify/workspaces/<slug>-<lane|WP>.json` is written on claim but **never tombstoned** on merge-completion or cancel (`cleanup_orphaned_contexts` runs only from the manual `spec-kitty context` command). **14 orphans** for *merged* missions 059/060 are committed today.
- **LC-1 is fixed but masked** — `.gitignore:143-144` hides `test-feature-*` from `git status`, so a future regression is invisible (the mask *hides* rather than *prevents*).

**No session reaper exists** (zero `pytest_sessionfinish/sessionstart/unconfigure` hooks under `tests/`). The durable win is a single controller-gated session reaper + `/tmp` prompt-namespacing + the LC-6 tombstone.

### User Story 1 - Test residue self-heals (Priority: P1)
As a contributor, I want the suite to reap everything it created — `test-feature-*` missions/dirs + `kitty/mission-test-feature-*` branches + git-unregistered `.worktrees/` + its `/tmp` prompt residue — after the session, even on failure, so my checkout and `/tmp` stay clean and `doctor` isn't polluted.

**Independent test**: seed a `test-feature-*` dir + branch + an unregistered `.worktrees/` husk, run the session; the reaper removes exactly those, and leaves pre-existing tracked missions/branches/worktrees untouched.

### User Story 2 - A leak regression is visible, not masked (Priority: P1)
As a maintainer, I want the `.gitignore` `test-feature-*` masks retired and replaced by reap-then-assert, so a future leak surfaces (a pollution assertion reds) instead of hiding under a gitignore.

### User Story 3 - /tmp prompt writers are namespaced + sweepable (Priority: P2)
As a contributor, I want the `spec-kitty-next-*` / `spec-kitty-implement|review-*` prompt writers to use a per-repo/per-run temp namespace so they don't accumulate unbounded in a flat `/tmp` and are sweepable by the reaper.

### User Story 4 - Merged/cancelled missions leave no workspace-context orphan (Priority: P2)
As an operator, I want `.kittify/workspaces/*.json` tombstoned when a mission merges or is cancelled, so orphaned context files (like the 14 for merged 059/060) don't accumulate.

### Edge Cases
- Parallel (`xdist`) run — the reaper must NOT let one worker delete another's in-flight REPO_ROOT artifacts (controller-gated).
- A test legitimately leaves a pre-existing tracked `kitty-specs/*` mission — the snapshot-delta reaper must never delete it.
- `git worktree prune` cannot see a stray physical `.worktrees/` dir never `git worktree add`ed — the reaper must `rmtree` the delta not in `git worktree list --porcelain`.
- A failed/aborted test — teardown still runs (`sessionfinish` fires regardless).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
| --- | --- | --- | --- | --- |
| FR-001 | Controller-gated session reaper (snapshot-delta) | As a contributor, I want a `pytest_sessionfinish` hook in root `tests/conftest.py`, gated to the xdist **controller** (`session.config.workerinput is None`), that snapshots REPO_ROOT state at `sessionstart` and at finish reaps only the **delta** matching test patterns: `kitty-specs/test-feature-*`, `kitty-specs/*-123-test-feature`, `*golden-path-demo*` dirs; new `kitty/mission-test-feature-*` / `*golden-path*` branches (`git branch -D`); and git-unregistered `.worktrees/*` husks (`git worktree prune` then `rmtree` any `.worktrees/*` absent from `git worktree list --porcelain`). | High | Open |
| FR-002 | Reaper sweeps the current run's /tmp prompt + test-home residue | As a contributor, I want the reaper to also remove this run's `/tmp/spec-kitty-next-*`, `/tmp/spec-kitty-implement\|review-*`, **`/tmp/spec-kitty-composed-*`** (`decision.py`), and `/tmp/spec-kitty-test-homes/<run_uid>/` (N1), keyed to the current run so concurrent runs are unaffected. The prompt-prefix it matches on comes from the **shared temp-namespace constant** (FR-003), not hand-copied literals, so it cannot drift from the writers. | High | Open |
| FR-003 | /tmp prompt-writer namespacing (LC-3/LC-4) | As a contributor, I want **all three** flat-`/tmp` prompt writers routed through one per-repo/per-run-namespaced, sweepable temp-root helper: `prompt_builder.py` (`spec-kitty-next-*`), `workflow.py` (`spec-kitty-implement\|review-*`), and **`decision.py` (both `spec-kitty-composed-{action}-*` `mkstemp` sites ~:610/:656 — unbounded, unique suffix per call)**. The namespace prefix MUST come from **one shared constant/module consumed by BOTH the writers AND the reaper (FR-002)** — no hand-copied literals — and a test asserts a writer's output path falls under the reaper's swept root, so a prefix change cannot desynchronize the two. | Medium | Open |
| FR-004 | Retire the .gitignore masks; reap-then-assert | As a maintainer, I want `.gitignore:143-144` (`kitty-specs/test-feature-*`, `kitty-specs/*-123-test-feature`) removed and a pollution assertion (reusing the e2e `assert_no_source_pollution` shape) that reds if the reaped delta is non-empty at finish — so a leak surfaces instead of hiding. | High | Open |
| FR-005 | Tombstone workspace-context on merge/cancel (LC-6) | As an operator, I want `.kittify/workspaces/<slug>-*.json` tombstoned when a mission completes merge or is cancelled. **Writer map (corrected): `workspace/context.py:305 save_context`, called from `lanes/implement_support.py:127,167` AND `lanes/recovery.py:732`** (NOT `context/resolver.py:270`, which writes the separate `.kittify/runtime/contexts/` MissionContext surface). The **cancel** emit path is `move-task --to canceled` → `ports.coord.commit_status` → **`emit_status_transition_transactional`** (`coordination/status_transition.py:713`) — NOT `tasks_transition_core` (a pure decision core, no emit) nor `emit.emit_status_transition` (which fires only on the **non-coordination fallback**, :729). On **coord topology** (the target case — the per-lane context leak) it uses `_prepare_event` + `txn.append_event`, so the tombstone hook must sit on the transactional path covering **both** the coord-topology and fallback branches, gated on **all lane WPs terminal** (mirror `status/doctor.py`'s `all(wp.lane in {done, canceled})`), mapping WP→lane `workspace_name` (slug + lane_id) and calling targeted **`delete_context(workspace_name)`** (a pure `unlink` by name — its first external caller). Both cancel and **merge-completion** use targeted `delete_context`, which is **order-independent** (no worktree gate) — so there is NO ordering requirement vs worktree removal. Also remove the 14 committed orphans for merged 059/060. Preserve all other merge/cancel semantics. | Medium | Open |
| FR-006 | Non-vacuous proof for reaper + tombstone | As a maintainer, I want proof: seeded `test-feature-*` dir/branch/unregistered-worktree are reaped while a pre-existing tracked artifact is NOT (mutation-checkable); the pollution assertion reds on a seeded leak; a merged mission leaves no orphan context JSON. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | Controller-gated, no worker races | The reaper runs only in the xdist controller/serial process (`workerinput is None`); workers never delete shared REPO_ROOT artifacts. | Reliability | High | Open |
| NFR-002 | Snapshot-delta safety | The reaper NEVER deletes a pre-session (pre-existing) mission dir, branch, or worktree — only artifacts created during the session and matching the test patterns. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | Narrow name-pattern snapshot-delta (reuse the watched-roots concept, not the deep inventory) | Reuse the e2e pollution baseline's **watched-roots concept** (`kitty-specs`, `.worktrees`, `kitty/*` branches, `.kittify/workspaces`), but implement a **narrow name-pattern snapshot-delta** — list matching entries (`test-feature-*`, `*golden-path-demo*`, `kitty/mission-test-feature-*`, `.worktrees/*`) at `sessionstart`, reap the *new* ones at finish. Do NOT reuse `assert_no_source_pollution`'s deep per-file `rglob` mtime inventory (~6,900 files → slow + false-red-prone on the live shared REPO_ROOT). | Technical | High | Open |
| C-002 | Key on REPO_ROOT, not HOME | The reaper keys on the shared REPO_ROOT; per-worker HOME state is already auto-discarded (its residue is only N1's temp-home dir). | Technical | High | Open |
| C-003 | No new suppressions | `ruff` + `mypy --strict` clean; no new `# type: ignore` / `# noqa`. | Technical | High | Open |
| C-004 | Preserve merge/cancel semantics | FR-005 adds only the context tombstone; it must not change merge/cancel behavior otherwise. | Technical | High | Open |

### Key Entities
- **`tests/conftest.py`** — root conftest; home the reaper hooks here (`pytest_sessionstart` snapshot + `pytest_sessionfinish` reap).
- **`tests/e2e/conftest.py`** — `assert_no_source_pollution` (the shape to reuse).
- **`prompt_builder.py` / `workflow.py` / `decision.py`** — the **three** flat-`/tmp` prompt writers (LC-3/LC-4); `decision.py`'s `spec-kitty-composed-{action}-*` is unbounded (unique suffix per call).
- **`workspace/context.py` `save_context` (from `implement_support.py` + `recovery.py`) + `merge/executor.py`** — LC-6: `cleanup_orphaned_contexts` gates on `worktree_path.exists()` (no-op on cancel while the worktree lives) and is never wired into completion/cancel.
- **`.gitignore:143-144`** — the masks to retire.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: After a representative mission-creating + e2e slice, the reaper leaves 0 test-created `test-feature-*` dirs/branches, 0 git-unregistered `.worktrees/` husks, 0 leftover run prompt files (**next / implement\|review / composed**), and the run's `spec-kitty-test-homes/<run_uid>/` gone.
- **SC-002**: A seeded `test-feature-*` dir + branch + unregistered worktree are reaped; a pre-existing tracked `kitty-specs/*` mission + real branch + registered worktree are NOT touched (mutation-verified both directions).
- **SC-003**: `.gitignore:143-144` removed; the pollution assertion reds when a `test-feature-*` artifact is seeded and left, green otherwise.
- **SC-004**: A merged (or cancelled) mission leaves no `.kittify/workspaces/*.json` orphan; the 14 committed 059/060 orphans are removed; a regression test covers it.
- **SC-005**: `ruff` + `mypy --strict` clean; the reaper adds negligible suite runtime; full `tests/` green.

## Out of Scope
- The **99-file #2181 `/tmp` ratchet burn-down** (`tmp_ratchet_baseline.txt`) — spread across 21 dirs; deferred to a follow-up (cheap first tranche = `specify_cli`+`sync` = 43 files).
- LC-7's within-repo per-invocation prompt retention (no cross-repo collision remains).
- Re-remediating the already-fixed classes (LC-1 in-tree fix, LC-2, LC-5, LC-7, LC-8) — LC-1 is covered by the reaper + mask-retirement; the others need no work.

## Assumptions
- The re-audit's per-class verdicts hold at implementation time (re-verify LC-1's tree-fix + the LC-3/4/N1/LC-6 leaks before finalizing).
- `pytest_sessionfinish` fires on the controller after all xdist workers finish (standard pytest-xdist behavior).
