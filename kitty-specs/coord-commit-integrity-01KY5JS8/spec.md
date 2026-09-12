# Mission Specification: Trusted mission-artifact commit path

**Mission Branch**: `remediation/coord-trust-2841` (coord topology)
**Created**: 2026-07-22
**Status**: Draft
**Input**: Pre-spec research `docs/plans/engineering-notes/coord-splitbrain-rootcause.md` (root cause) + `coord-trust-mission-scope.md` (scope), plus the operator-confirmed fold of #2861 into this mission (shared commit/actor seam; PR #2868/#2612 that attempted the coord-commit fix are CLOSED-unmerged). Remediates the coordination-branch split-brain (#2841) and the review-claim actor leak (#2861). Sibling missions #2803 (lane test env) and #2853 (ratchet gates) are OUT of scope.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A mission's bookkeeping lands in its declared home and commits correctly (Priority: P1)

An agent or the operator runs a mission through the implement-review-merge loop. Every bookkeeping
artifact the toolchain writes (status events, review-cycle verdicts, matrices, analysis reports) must
physically land in the partition its kind declares as home and commit there — so readers, gates, and
merge all see one consistent truth instead of a second, independently-writable copy that silently
diverges (the #2841 drift, discovered only at merge).

**Why this priority**: This is the spine. The split-brain corrupts the merge-time trust signal and
blocks coord missions from committing at all; it is the blocker parking `docs-structural-sanity-01KY53KJ`.

**Independent Test**: Drive a real coord-topology mission (real `git worktree add`) through a status
transition and a review cycle; assert the artifacts commit to the coordination branch, no primary
residue is produced, and a deliberately mis-placed write fails at `safe_commit` rather than diverging.

**Acceptance Scenarios**:

1. **Given** a coord-topology mission, **When** a `WORK_PACKAGE_TASK` artifact (e.g. `review-cycle-N.md`) is written, **Then** it lands on the PRIMARY partition (its declared home) and an `ANALYSIS_REPORT`/status artifact lands on COORD — neither can land on the other partition.
2. **Given** a coord mission whose coord files live under a gitignored `.worktrees/` path, **When** the commit path runs, **Then** it targets the coord worktree (both the `safe_commit` write-root and the porcelain pre-check) and actually commits — no phantom "already committed" short-circuit, no `SafeCommitPathPolicyError`.
3. **Given** any mission-artifact write, **When** it is staged, **Then** the bytes are written directly into the destination ref's worktree (never write-to-primary-then-copy), so no second-copy residue exists to drift.
4. **Given** a status transition on a coord mission, **When** the coord worktree is present, **Then** the event commits to coord — there is no primary-checkout-uncommitted fallback that leaves readers reading a stale coord log.

### User Story 2 — A manually-orchestrated review claim succeeds with a valid actor (Priority: P1)

An operator (not a dispatch Op) claims a WP review with `spec-kitty agent action review WP## --agent
tool:model:profile:role`. The claim must succeed with a valid actor payload and must not require the
`--force` workaround that manufactures false "hollow reviews" at merge.

**Why this priority**: #2861 blocks manual review entirely and pollutes the merge-time review-quality
signal; it lives on the same `workflow.py`/`emit.py` commit seam as User Story 1.

**Independent Test**: Live red-first repro through the real `agent action review` entry with a compact
`--agent` and no `--invocation-id`; assert exit 0, the WP flips `for_review → in_review`, the persisted
`WPStatusChanged` actor's `tool` is the bare token (not the whole compact string), and `force_count` is
not inflated.

**Acceptance Scenarios**:

1. **Given** a compact `--agent tool:model:profile:role` and no dispatch Op, **When** the review claim runs, **Then** the actor is `{tool, model, profile, role}` (parsed), not `{tool: "<whole compact string>", model: None, profile: None}`, and the claim commits.
2. **Given** a correctly-parsed dict-shaped actor, **When** the event is emitted, **Then** the emitter validator accepts it (dict actors are valid), not rejects it as a non-string.
3. **Given** the fix, **When** a manual review claim succeeds, **Then** no `--force` is needed and merge shows no false "hollow reviews" for that WP.

### User Story 3 — A mission's own runtime state does not trip the diff-compliance gate (Priority: P2)

A bulk-edit or review diff-compliance check runs while the mission's own `status.events.jsonl` /
`status.json` / review-cycle / matrices / notes have churned. The gate must auto-exempt the mission's
own runtime state — no hand-authored `occurrence_map.yaml` exception, no coord hand-commit.

**Independent Test**: Run the diff-compliance gate over a diff containing the mission's own runtime-state
files plus a non-runtime file under the same `feature_dir`; assert the runtime files are exempt and the
non-runtime file still classifies/violates.

**Acceptance Scenarios**:

1. **Given** a diff touching the mission's own `status.events.jsonl`, **When** the gate runs, **Then** that file is exempt (source "runtime-state", no violation) — no `occurrence_map` entry needed.
2. **Given** a bulk-edit that renames ANOTHER mission's runtime files, **When** the gate runs, **Then** those are NOT silently exempted (the allowlist is anchored to the running mission's own `feature_dir`).
3. **Given** a `spec.md`/`plan.md`/`tasks.md` change under the same `feature_dir`, **When** the gate runs, **Then** it still classifies (reviewable product surface is not exempted).

### User Story 4 — Coord-branch staleness is surfaced, and safely resynced only when unambiguous (Priority: P2)

The coordination branch is a one-time snapshot of `target_branch`; `target_branch` moves afterward. The
toolchain must surface that staleness non-blockingly and offer a safe fast-forward only when there is no
divergence risk.

**Independent Test**: With coord a strict ancestor of a moved target, `doctor coordination
--check-staleness` reports stale and `--fix` fast-forwards; with coord diverged, `--fix` fails loud with
a diff and mutates nothing.

**Acceptance Scenarios**:

1. **Given** coord is a strict ancestor of `target_branch`, **When** `doctor coordination --check-staleness` runs, **Then** it reports stale (non-blocking) and `finalize-tasks` prints a non-blocking WARN with the recovery command.
2. **Given** the stale-ancestor case, **When** `doctor coordination --fix` runs and the coord worktree is clean, **Then** it fast-forwards the coord branch to include target's new commits.
3. **Given** coord has diverged from `target_branch` (not a strict ancestor) OR the coord worktree is dirty, **When** `--fix` runs, **Then** it fails loud with a unified diff and mutates nothing.

### Edge Cases

- Coord worktree missing/unregistered at write time on a COORD-routed mission → the write must materialize/target the coord worktree (do not silently fall back to a primary-uncommitted write); the misroute-to-legacy path must fail loud rather than commit coord paths from `repo_root`.
- Legacy / non-coord (SINGLE_BRANCH / LANES / flattened) missions → the placement port routes to PRIMARY and the non-transactional primary write is CORRECT; the FR-004 conditionalization must PRESERVE this path — no coord path is forced, no regression.
- The review *verdict* has dual authority (authored `verdict:` frontmatter + event-log `review` override) during the transition → keep the existing cross-store consistency check as a fail-loud net; do not delete it.
- `traces/` is unclassified in the partition SSOT (doctrine says COORD, code sites it PRIMARY/lane + union-merge) → out of scope to reclassify here; note it as a follow-up, do not let the placement port crash on it.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Single kind-keyed placement port | The commit ROUTING is already unified (`commit_for_mission → resolve_placement_only(kind)`); FR-001's target is the disk-WRITE step — write bytes directly in the destination ref's worktree instead of authoring to the wrong partition. Retire the kind-blind `candidate_feature_dir_for_mission` write at `review/cycle.py:~272` (review-cycle → its PRIMARY home, wireable cleanly). (analysis-report authorship is resolved by the FR-003 re-home, not a separate routing change.) | US1 | Open |
| FR-002 | Close the coord-commit misroute (re-grounded) | The MODERN `_commit_via_coordination_transaction` already threads the coord sub-worktree root and is correct — it needs an NFR-001 regression, not a code change. The real residual: (a) make the **misroute-to-legacy** unrepresentable — a coord-routed topology must never reach `_commit_via_legacy_safe_commit` (fail loud, or have the leaf resolve the coord worktree) when `_load_coord_branch_meta` returns an incomplete identity triple; (b) fix the legacy leaf's phantom "already committed" porcelain pre-check (a **#2684** guard at `workflow.py:~599`, run from `repo_root` → empty over gitignored coord files) to run against the resolved worktree root. NOTE: this misroute (→ `SafeCommitHeadMismatch`) is the LIKELY cause of #2861's blocking "commit refused" — confirm live (NFR-002) first. | US1 | Open |
| FR-003 | No second-copy residue (+ analysis-report re-home) | Remove the write-to-primary-then-`shutil.copy2`-into-coord residue factory (`coordination/commit_router.py:~703`) so no second, independently-writable copy drifts. **`ANALYSIS_REPORT` is re-homed COORD→PRIMARY** (operator decision): its writer, freshness gate, and siblings (spec/plan/tasks) already live on PRIMARY, so the SSOT declaration is corrected to match — this dissolves the sibling-coupling that forced its write-then-copy, drops its coord copy, and retires its `is_coordination_artifact_residue_path` entry. Verify issue-matrix / acceptance-matrix write-sites can write-in-coord-home (no sibling coupling) at implement. | US1 | Open |
| FR-004 | Single status write-authority (topology-conditional) | For COORD topology, a status event must materialize/target the coord worktree and commit there (not the primary-uncommitted fallback at `status_transition.py:~924`). PRESERVE that fallback for coord-less topologies (`SINGLE_BRANCH`/`LANES`), where the non-transactional primary write is correct — this is a conditionalize-on-topology, NOT a blanket delete (a delete would regress flat missions). | US1 | Open |
| FR-005 | Boundary-normalize the compact --agent | Parse `--agent tool:model:profile:role` at the CLI input boundary — the live claim path does NO boundary parse today; the whole string leaks into `actor.tool` at all 3 seams (`workflow_executor.py:648`/`:1465`, `tasks_move_task.py:1542`). Pass the bare `tool` token to `build_resolved_actor` and widen it with self-asserted `profile`/`model` kwargs. Do NOT reuse the frontmatter parser's synthetic defaults (`"unknown-model"`, `"{tool}-default"`) for the actor — absent segments stay absent (self-asserted, not fabricated). Do NOT synthesize a `ResolvedBinding` (preserves C-007). | US2 | Open |
| FR-006 | Dict-actor validator (SaaS-fanout fidelity) | Widen the emitter's `WPStatusChanged` (`emitter.py:434`) and `WPCreated` (`:452`) actor validators to accept a dict actor (`Union[str, Dict]`, matching installed `spec_kitty_events`). NOTE: this is the SaaS/local-sync fan-out path — it warns-and-skips, it does NOT refuse the git commit (the local JSONL append is already dict-safe), so FR-006 fixes fidelity, not the block. `WPAssigned` has no actor field (out of scope). | US2 | Open |
| FR-007 | Runtime-state gate exemption | The bulk-edit diff-compliance gate auto-exempts the running mission's own runtime state via a named allowlist (`status.events.jsonl`, `status.json`, `review-cycle-N.md`, matrices, notes) anchored to the mission's own `feature_dir`, threaded from `check_review_diff_compliance` into the classifier. | US3 | Open |
| FR-008 | Coord staleness detector + doctor mode | A coord-vs-target staleness detector (strict-ancestor → stale-fast-forwardable; diverged → warn) surfaced via `spec-kitty doctor coordination --check-staleness` and a non-blocking WARN at `finalize-tasks`. | US4 | Open |
| FR-009 | Safe coord fast-forward under --fix | `doctor coordination --fix` fast-forwards the coord branch only when it is a strict ancestor of target AND the coord worktree is clean; otherwise it fails loud with a unified diff and mutates nothing. | US4 | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Real-repo e2e proof | A wrong-partition write being unrepresentable at commit, and a real coord mission committing correctly, are proven by a REAL-repo end-to-end test (real `git worktree add` + real `safe_commit`), NOT a stubbed `safe_commit`. | Reliability | High | Open |
| NFR-002 | Live red-first repro decides #2861 causation FIRST | Before finalizing the FR-005/006 fix shape, a live red-first reproduction through the real `agent action review` entry (compact `--agent`, no `--invocation-id`) must establish WHICH bug causes the blocking "commit refused": the squad's convergent hypothesis is that it is the FR-002 coord-commit misroute (`SafeCommitHeadMismatch`), NOT the actor-shape bug (whose validator is a non-fatal SaaS-fanout warning). If confirmed, FR-002 is what unblocks the manual review claim (US2 AC-3); FR-005/006 fixes actor correctness + fanout fidelity but does not, by itself, satisfy AC-3. | Reliability | High | Open |
| NFR-003 | No regression / fail-loud nets preserved | Existing green tests stay green; the cross-store review-artifact consistency check (now in `merge/`) is preserved as a fail-loud net, not deleted; the residue predicate becomes vestigial, not load-bearing. | Reliability | High | Open |
| NFR-004 | Quality gates clean | `ruff` + `mypy --strict` report 0 issues on touched modules; cyclomatic complexity ≤15; every new branch/helper carries a focused test; no new suppressions. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Partition contract STRUCTURE unchanged; one authorized re-home | The partition contract's STRUCTURE (`artifact_home_for` symmetry read==write, disjoint-and-total via `assert_partition_invariant`) stays untouched — this mission enforces write-placement *realization*, not the contract shape. The ONE authorized membership change (operator-signed-off) is re-homing `ANALYSIS_REPORT` COORD→PRIMARY, a mis-classification correction (its writer/gate/siblings are already PRIMARY). The partition MUST remain disjoint-and-total afterward (`assert_partition_invariant` stays green). No other kind moves. | Technical | High | Open |
| C-002 | Preserve C-007 provenance | A `ResolvedBinding` means a genuinely dispatch-resolved identity (backed by a durable Op record). Do NOT synthesize one from a self-asserted `--agent` string; self-asserted profile/model live on the `actor`, not a fabricated binding. | Technical | High | Open |
| C-003 | Keep doctor --fix minimized | Do NOT grow `doctor coordination --fix` into a general "repair arbitrary drift" command. Prevention (the placement port) removes that need; the reconciliation gate's existence is the split-brain fingerprint. Gap-1 staleness is the ONLY residual fail-loud detect/resync. | Scope | High | Open |
| C-004 | Exemption is a named, own-feature_dir allowlist | The Symptom-B exemption is a NAMED allowlist anchored to the running mission's OWN `feature_dir` — NOT everything under `feature_dir` (spec/plan/tasks stay reviewable) and NOT another mission's files. | Technical | High | Open |
| C-005 | Staleness is warn-first, FF-only-when-safe | Staleness is a non-blocking WARN + explicit `doctor` flag; fast-forward only under `--fix` when strict-ancestor AND clean, else fail loud (D1/D3). Never mutate silently. | Technical | High | Open |
| C-006 | Re-grounded against current main (pre-plan squad, DONE) | Re-grounding results: residue factory is LIVE at `coordination/commit_router.py:703` (not moved — an earlier wrong-path grep was corrected); the write-side partition guard (`PrimaryKindReachedCoordStagingError`, the #2834-class fix) already landed and FR-001 builds on it; the phantom porcelain pre-check is a **#2684** guard in the **legacy leaf only** (`workflow.py:~599`) — the modern transaction path is already correct; `review_artifact_consistency` moved into `merge/` (re-verify the review-cycle read partition before touching it). Line numbers in FRs are current-main approximations — re-confirm at implement (campsite). | Technical | Medium | Open |
| C-007 | Sibling missions out of scope | #2803 (lane test env / `uv run pytest`) and #2853 (ratchet-baseline gates) are separate sibling missions — do NOT include them. | Scope | High | Open |

### Key Entities

- **Placement port**: the single write seam keyed on `kind_for_mission_file(path)` → `resolve_placement_only(kind).ref`; stages bytes in that ref's worktree.
- **Partition (COORD / PRIMARY)**: the disjoint-and-total kind partition; every artifact kind has one home.
- **Coord worktree**: the checked-out coordination branch under `.worktrees/`; the destination for COORD writes and coord commits.
- **Actor payload**: the `{role, tool, model, profile}` identity on a status event; may be a bare string or a dict; self-asserted vs dispatch-resolved (`ResolvedBinding`).
- **Runtime-state allowlist**: the named set of the mission's own bookkeeping basenames exempt from the diff-compliance gate, anchored to its `feature_dir`.
- **Coord staleness**: coord-branch tip vs `target_branch` (strict-ancestor = fast-forwardable; diverged = fail-loud).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A deliberately mis-placed mission-artifact write fails at `safe_commit` (unrepresentable), and a real coord mission's status + review artifacts commit correctly to the coordination branch with no primary residue — proven by a real-repo e2e test.
- **SC-002**: A coord mission whose files live under gitignored `.worktrees/` commits without a phantom "already committed" short-circuit and without `SafeCommitPathPolicyError`, on both the legacy and modern commit paths.
- **SC-003**: A manual `agent action review --agent tool:model:profile:role` (no dispatch Op) claim succeeds with a parsed actor and requires no `--force`; merge shows no false "hollow reviews" for that WP.
- **SC-004**: A diff-compliance run over the mission's own runtime state passes with no `occurrence_map` exception; a non-runtime file (and another mission's runtime file) under the same tree still classifies.
- **SC-005**: Coord staleness surfaces as a non-blocking WARN + `doctor coordination --check-staleness`; `--fix` fast-forwards only when strict-ancestor + clean, else fails loud with a diff.
- **SC-006**: The parked `docs-structural-sanity-01KY53KJ` coord `safe_commit` blocker is resolved — its failing scenario now commits.
