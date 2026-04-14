# Legacy Sparse-Checkout Cleanup and Review-Lock Hardening

**Feature**: `legacy-sparse-and-review-lock-hardening-01KP54ZW`
**Mission ID**: `01KP54ZWEEPCC2VC3YKRX1HT8W`
**Mission Type**: software-dev
**Target Branch**: `main`
**Created**: 2026-04-14
**Status**: Draft

## 1. Overview

Two post-3.0.0 regressions surfaced together in normal production use and must be addressed in one release:

1. **Silent data loss during `spec-kitty agent mission merge`** on repositories that still carry sparse-checkout state from pre-3.0.0 spec-kitty runs. Reported as Priivacy-ai/spec-kitty#588. First reproduction caused a real commit that reverted 243 lines across 4 files on a merged `main`; second reproduction was caught before landing.
2. **Review-lock file triggers spec-kitty's own uncommitted-changes guard**, forcing reviewers to pass `--force` on every `move-task --to approved` / `--to done` transition. Reported as Priivacy-ai/spec-kitty#589. Reproduces on every lane-worktree review.

Both regressions were introduced in v3.0.0 ("Canonical Context Architecture Cleanup", PR #347). Issue #588 is the data-loss regression: v3.0.0 deleted the code that *writes* sparse-checkout configuration but did not ship a migration that *removes* the sparse-checkout configuration already present on disk in user repos. Issue #589 is the self-collision regression: the 3.0.0 review-lock mechanism writes runtime state inside the lane worktree but does not exclude that state from the guard that blocks lane transitions.

This mission closes both regressions and, on the data-loss side, adds defence-in-depth that protects against similar HEAD-vs-working-tree mismatches no matter what configuration caused them.

## 2. User Scenarios & Testing

### 2.1 Primary User Story

Kent Gale (or any spec-kitty user who upgraded from a pre-3.0 release) opens a terminal in their primary repo, runs missions through the standard lifecycle, and expects the tool not to lose their work or block routine transitions.

### 2.2 Scenarios

**Scenario A — Detect and remediate legacy sparse-checkout state.**
A user whose primary repo still has `core.sparseCheckout=true` from a pre-3.0.0 run executes `spec-kitty doctor`. The tool reports the finding, explains the risk in plain language, and offers a remediation command. The user runs the remediation; afterwards `git config --get core.sparseCheckout` returns empty and the working tree matches `HEAD` in both the primary and every existing lane worktree.

**Scenario B — Merge aborts safely rather than silently losing work.**
A user who has not yet run the doctor remediation invokes `spec-kitty agent mission merge`. The merge refuses to proceed, names the offending configuration, and points at the remediation command. No commits are made to the target branch as a result of this invocation. After the user runs the remediation and re-invokes merge, the merge completes and `git status` on the primary is clean.

**Scenario C — Commit-time guard catches unexpected phantom deletions.**
A user in any repo configuration encounters a situation where `safe_commit` is about to commit paths it was not asked to commit (e.g. phantom deletions from a working tree that lags `HEAD`). The commit aborts before producing an artifact and the user sees an error that identifies the unexpected paths and instructs recovery.

**Scenario D — Approve a work package without `--force`.**
A reviewer in a lane worktree has run `spec-kitty agent action review WP##`, performed the review, and invokes `spec-kitty agent tasks move-task WP## --to approved`. The only untracked content in the worktree is spec-kitty's own `.spec-kitty/` directory. The transition succeeds, the retry guidance (if the transition had failed for a different reason) names the actual target lane rather than `for_review`, and the lock file and its parent directory are removed as part of the transition.

**Scenario E — Reject a work package without `--force`.**
A reviewer rejects a work package via `spec-kitty agent tasks move-task WP## --to planned --review-feedback-file feedback.md`. The dirty-tree guard does not trip on `.spec-kitty/`; the rejection records feedback and transitions the work package normally.

**Scenario F — Post-hoc recovery for users already hit.**
A user who previously ran `spec-kitty agent mission merge` in a sparse-affected state and only later discovered missing content in `main` reads the CHANGELOG entry for this release, follows the documented recovery recipe, and restores the reverted content from the merge commit that originally introduced it.

**Scenario G — Power user with legitimate sparse checkout.**
A user has intentionally configured sparse-checkout in a monorepo after 3.0.0 and is aware of the risks. They invoke merge or implement with an explicit `--allow-sparse-checkout` override; the command proceeds, emits an audit log entry recording the override, and relies on the commit-time backstop for data-loss prevention.

### 2.3 Edge Cases

- **External HEAD advance.** A user `git pull`s outside spec-kitty between spec-kitty commands. The next spec-kitty command that commits through `safe_commit` must not silently sweep working-tree-versus-HEAD deltas into the commit.
- **Pre-existing lane worktrees inherited sparse config.** A user has lane worktrees already on disk that were created from the sparse-affected primary and therefore inherited `core.sparseCheckout=true`. Remediation must repair these worktrees too, not only the primary.
- **Dirty working tree at remediation time.** The user has uncommitted work in paths currently inside the sparse cone. Remediation must not discard that work; it must refuse to run on a dirty tree and instruct the user to commit or stash first.
- **CI / non-interactive environment.** Preflight and doctor run in a CI pipeline. No interactive prompts may hang the session; the command must exit non-zero with a deterministic message that points at local remediation.
- **Sparse-checkout configured but not restricting anything.** A repo has `core.sparseCheckout=true` with patterns that effectively include every file. The detection primitive must be precise enough that this does not produce a false-positive block (either "block anyway because the config is still set" or "allow because nothing is filtered" is defensible, but the decision must be explicit, documented, and consistent across all four layers that call the primitive).
- **Reject transition carrying review-lock state.** A reject (`--to planned`) transition hits the same dirty-tree guard as approve. It must not trip on `.spec-kitty/` and it must release the lock on exit.
- **Unrelated untracked content alongside `.spec-kitty/`.** When the reviewer has both spec-kitty runtime state and genuine uncommitted work, the guard must still block on the genuine work while ignoring the runtime state.
- **Audit trail for `--allow-sparse-checkout`.** Every use of the override must be recorded somewhere persistent (event log or dedicated audit surface) so that if data loss later occurs it can be traced.
- **Secondary state anomaly in approve output.** Issue #589 flagged that approving a work package reports the transition as `from in_progress` rather than `from for_review`. Whether this is the same bug or a separate one must be determined and either fixed or documented with a definitive explanation.

## 3. Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | Provide a single canonical detection primitive that determines whether a given git repository or worktree is currently operating under sparse-checkout. The primitive must inspect both `core.sparseCheckout` configuration and per-worktree sparse pattern state. | proposed |
| FR-002 | `spec-kitty doctor` surfaces a distinct finding when sparse-checkout state is detected in the primary repository or any existing lane worktree, with plain-language explanation of the risk and a single-command remediation. | proposed |
| FR-003 | A remediation action (offered by doctor) disables sparse-checkout configuration, removes the sparse pattern file, and refreshes the working tree to match `HEAD` in the primary repository. | proposed |
| FR-004 | The remediation action additionally repairs every existing lane worktree under `.worktrees/*` that inherited sparse-checkout configuration from the primary repository. | proposed |
| FR-005 | The remediation action refuses to run when the repository or any target worktree has a dirty working tree (uncommitted tracked changes). The refusal message instructs the user to commit or stash those changes and re-run. | proposed |
| FR-006 | `spec-kitty agent mission merge` runs a preflight check that refuses to proceed when sparse-checkout state is detected. The refusal message names the remediation command. | proposed |
| FR-007 | `spec-kitty agent action implement` runs the same preflight check before creating a new lane worktree and refuses to proceed when sparse-checkout state is detected. | proposed |
| FR-008 | Both `mission merge` and `agent action implement` support an explicit `--allow-sparse-checkout` override flag that permits proceeding despite the preflight. Each use of the override emits a structured log record at `WARNING` level with a stable marker (`spec_kitty.override.sparse_checkout`) naming the command, mission identity, actor, and timestamp. A durable cross-repo audit event is deferred to Priivacy-ai/spec-kitty#617 (the `MissionAudit*` / `DecisionPointOverridden` wiring follow-up). | proposed |
| FR-009 | The `--allow-sparse-checkout` override is distinct from `--force`. `--force` alone does not bypass the sparse-checkout preflight. | proposed |
| FR-010 | Other state-mutating CLI commands (for example `move-task`, `tasks-finalize`, `mark-status`, `charter sync`) emit a single non-blocking warning the first time in a process that they observe sparse-checkout state. The warning names the doctor command that offers remediation. | proposed |
| FR-011 | `safe_commit` (the shared helper at the data-writing layer) compares the staging area against `HEAD` before creating a commit and aborts the commit when the staging area contains paths that were not explicitly passed to `safe_commit` as targets. The abort message lists the unexpected paths and the requested paths. | proposed |
| FR-012 | The abort in FR-011 is not bypassable by `--force` on the calling command. | proposed |
| FR-013 | `spec-kitty agent mission merge` explicitly refreshes the primary checkout's working tree to match `HEAD` after the mission-to-target merge completes and before any subsequent commit runs. | proposed |
| FR-014 | After a successful merge, `spec-kitty agent mission merge` asserts that the primary checkout's working tree matches `HEAD` and aborts with a diagnostic message if it does not. | proposed |
| FR-015 | The uncommitted-changes guard used on transitions to `for_review`, `approved`, and `done` filters spec-kitty's own runtime state directories from its drift scan. The filter is a named deny-list (currently `.spec-kitty/` and `.kittify/`), not a pattern-based rule. | proposed |
| FR-016 | When a lane worktree is created, spec-kitty writes `.spec-kitty/` to that worktree's `.git/worktrees/<lane>/info/exclude` so that spec-kitty runtime state does not appear as untracked content to `git status`. | proposed |
| FR-017 | The retry guidance emitted by the uncommitted-changes guard names the actual target lane the caller requested (`for_review`, `approved`, `done`, or `planned`) rather than hard-coding `for_review`. | proposed |
| FR-018 | A successful transition out of review (`approved` or `planned`) releases the review lock. Lock release removes the lock file and removes the parent `.spec-kitty/` directory if it becomes empty. | proposed |
| FR-019 | Rejection (`move-task --to planned --review-feedback-file ...`) of a work package under active review does not trip the uncommitted-changes guard on `.spec-kitty/` runtime state. | proposed |
| FR-020 | The reporter-flagged anomaly that approve output names the source lane as `in_progress` instead of `for_review` is either fixed (so the output matches the actual lane history) or documented with an authoritative explanation of why the observed output is correct. | proposed |
| FR-021 | The CHANGELOG entry for the release that contains these fixes describes (a) the sparse-checkout cleanup migration, (b) the commit-time data-loss backstop, (c) the review-lock fix, and (d) a recovery recipe for users whose repos already have a phantom-deletion commit on their target branch from a prior merge under sparse-checkout. | proposed |
| FR-022 | A diagnostic comment is posted to Priivacy-ai/spec-kitty#588 that asks the reporter to confirm the origin of the sparse-checkout state on his repository. The comment is posted before this mission closes; it is not a blocker for the mission's implementation. | proposed |
| FR-023 | When the sparse-checkout preflight runs in a non-interactive or CI environment (detected via standard environment indicators or non-TTY stdin), the preflight exits with a non-zero status code and a deterministic one-line remediation pointer. No interactive prompt is shown. | proposed |

## 4. Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | The sparse-checkout detection primitive must complete fast enough that adding it to session-start warning paths does not regress CLI responsiveness. | Adds no more than 20 ms wall-clock to any CLI command on a repository with fewer than 10 worktrees. | proposed |
| NFR-002 | `safe_commit`'s staging-area diff check must not regress merge-time throughput on a typical mission. | Adds no more than 200 ms wall-clock to a merge that produces fewer than 50 commits. | proposed |
| NFR-003 | The remediation action, when it runs, must leave the repository in a state that passes `git status` cleanly in both the primary and every touched lane worktree. | 100% of successful remediation runs produce a clean `git status` afterwards (verified in integration tests). | proposed |
| NFR-004 | The commit-time backstop (FR-011) must produce zero false positives on the existing spec-kitty test corpus. | 100% pass rate of the existing test suite under the new backstop. | proposed |
| NFR-005 | The session-scoped warning from FR-010 must appear exactly once per process, regardless of how many state-mutating commands run inside that process. | Verified by integration test that invokes three state-mutating commands in one process and asserts exactly one warning emission. | proposed |

## 5. Constraints

| ID | Constraint | Rationale | Status |
|---|---|---|---|
| C-001 | The mission must not reintroduce sparse-checkout support. Feature 057 / v3.0.0 intentionally removed the policy; this mission only cleans up legacy state. | Scope discipline and backwards-fitness with the 3.x architectural choice. | proposed |
| C-002 | The remediation action is offered by `spec-kitty doctor` only. It must not run automatically on upgrade or as a side effect of another command. | Remediation calls `git checkout HEAD -- .` which is destructive to sparse-excluded local state; the user must consent explicitly. | proposed |
| C-003 | The dirty-tree guard's new exclude filter is a fixed named list of directories, not a pattern or regex. | Pattern-based excludes can silently swallow genuine drift; a fixed list limits blast radius. | proposed |
| C-004 | The uncommitted-changes guard must continue to block transitions when the worktree contains genuine uncommitted implementation work. The new filter only removes spec-kitty-owned runtime state from the drift scan. | The guard exists for a reason; this mission fixes a self-collision, not the guard's core function. | proposed |
| C-005 | The commit-time backstop (FR-011) must be implemented inside `safe_commit` so that every caller — present and future — inherits the protection without opt-in. | The data-loss cascade can originate from any command that calls `safe_commit`; the guard belongs at the commit layer. | proposed |
| C-006 | The preflight in FR-006 and FR-007 must use the single detection primitive from FR-001, not a re-derived check. | Multiple copies of detection logic will drift; the primitive owns the subtle cases. | proposed |
| C-007 | The `--allow-sparse-checkout` override cannot disable the commit-time backstop (FR-011). The backstop is the defence against silent data loss regardless of configuration. | The override allows users to proceed under sparse; it does not make proceeding safe. | proposed |
| C-008 | Existing public behaviour of `move-task`, `agent action review`, and `agent action implement` must be preserved for non-sparse repositories. Users on clean 3.x-born repos see no behavioural change except the FR-015 filter, the FR-017 guidance fix, and the FR-018 lock release. | Do not regress the installed base to fix the regressions in the affected base. | proposed |

## 6. Success Criteria

| ID | Criterion | Verification |
|---|---|---|
| SC-001 | A repository that carries pre-3.0 sparse-checkout state can be restored to a 3.x-compliant state by running exactly one user-facing command. | End-to-end test that sets up a sparse-configured repo, runs the remediation command, and asserts clean state. |
| SC-002 | Running `spec-kitty agent mission merge` on a sparse-configured repo without remediation never produces a commit on the target branch that reverts content from the merge. | Integration test that sets up a sparse-configured repo, invokes merge, and asserts no new commits appear on the target branch. |
| SC-003 | A lane-worktree review can be approved without passing `--force` on the `move-task` invocation. | Integration test that runs implement → commit → move-task for_review → review → move-task approved without `--force` and asserts success. |
| SC-004 | A lane-worktree review can be rejected without passing `--force`. | Integration test mirroring SC-003 but ending in rejection. |
| SC-005 | The commit-time backstop prevents every reproducible variant of the phantom-deletion cascade, including the specific sequence reported in Priivacy-ai/spec-kitty#588. | Regression test that reproduces the reported sequence, asserts the commit aborts, and asserts no silent deletion. |
| SC-006 | After a successful merge on a non-sparse repo, `git status` in the primary checkout reports a clean tree. | Integration test in the existing merge suite. |
| SC-007 | Every new guard (FR-006, FR-007, FR-011, FR-014) produces an error message that names the exact remediation command. Messages must not be generic. | Documentation audit plus test-level assertions on error strings. |
| SC-008 | The CHANGELOG entry produced for this release enables a user who has already been bitten to recover without contacting the maintainers. | Documentation review. |

## 7. Key Entities

- **Sparse-checkout state primitive** — the single function called by doctor, by the merge preflight, by the implement preflight, and by the session-start warning hook. Inspects `core.sparseCheckout` configuration and per-worktree pattern files.
- **Remediation action** — the operation offered by `spec-kitty doctor` that disables sparse-checkout configuration, removes pattern files, refreshes the working tree, and iterates over lane worktrees to repair each one.
- **Commit-time backstop** — the staging-area diff check inside `safe_commit` that rejects unexpected staged paths.
- **Post-merge working-tree refresh** — the step in `_run_lane_based_merge_locked` that ensures `HEAD` and working tree match before any housekeeping commit runs.
- **Uncommitted-changes guard runtime-state filter** — the deny-list used by `_validate_ready_for_review` that excludes `.spec-kitty/` and `.kittify/` from the drift scan.
- **Per-worktree ignore file** — the `.git/worktrees/<lane>/info/exclude` entry written at worktree creation that holds `.spec-kitty/` so `git status` does not surface it as untracked.
- **Review-lock release** — the cleanup step invoked on approved / planned transitions that removes the lock file and the parent directory if it is empty.
- **`--allow-sparse-checkout` override** — the explicit opt-in flag on `mission merge` and `agent action implement` for users with legitimate sparse configurations. Logged on each use.
- **Audit surface for override use** — the persistent record of each `--allow-sparse-checkout` invocation.

## 8. Dependencies and Assumptions

### 8.1 Dependencies

- Current `spec-kitty doctor` command surface and its output channels.
- The `safe_commit` helper at `src/specify_cli/git/commit_helpers.py`.
- The `_run_lane_based_merge_locked` function at `src/specify_cli/cli/commands/merge.py`.
- The `_validate_ready_for_review` function at `src/specify_cli/cli/commands/agent/tasks.py`.
- The `ReviewLock` lifecycle at `src/specify_cli/review/lock.py`.
- The worktree creation path in `src/specify_cli/core/worktree.py` and its VCS protocol implementation.

### 8.2 Assumptions

- The reporter's environment (kentonium3, 3.1.1, macOS) is representative of the affected user base. Other users who upgraded from pre-3.0 versions are likely to carry similar state.
- Users will accept a one-command remediation step rather than demanding an automatic in-place upgrade; this is consistent with spec-kitty's existing doctor-offered remediation pattern.
- Pre-3.0 spec-kitty wrote `core.sparseCheckout` configuration and at least one pattern file. The detection primitive can rely on the presence of either signal as evidence of legacy state.
- The existing test infrastructure supports parameterised fixtures for sparse-configured repositories; if it does not, a small fixture helper will be added as part of the planning phase.

## 9. Out of Scope

- Reintroducing sparse-checkout support in any form.
- Changing the merge strategy or the worktree lifecycle beyond what FR-013 and FR-014 require.
- Changes to `MergeState` persistence, resume, or preflight conflict forecasting beyond what is needed for the sparse-checkout preflight.
- Behavioural changes to the uncommitted-changes guard beyond the runtime-state filter (FR-015), the guidance fix (FR-017), and the lock release (FR-018).
- General refactors of the guard or of `safe_commit` beyond the specific changes named in the functional requirements.
- Cross-platform behaviour changes other than those required by FR-023 (non-interactive detection).
- Durable cross-repo audit event for `--allow-sparse-checkout` use. Investigation during planning (see Decision Log) confirmed that adding a new event type to the pipeline would require coordinated work across `spec-kitty-events`, `spec-kitty-saas`, and this repo. That work is tracked as Priivacy-ai/spec-kitty#617. Until that issue ships, this mission emits a structured log line at the CLI layer only.

## 10. Reporter and Environment

- **Reporter**: Kent Gale (kentonium3).
- **spec-kitty-cli version at reproduction**: 3.1.1 (installed via pipx).
- **Operating system**: macOS Darwin 25.3.0.
- **Python**: 3.13.13.
- **Primary checkout**: `/Users/kentgale/repos/kg-automation` (sparse-configured, origin of state unknown until FR-022 confirmation lands).
- **Lane worktrees**: `.worktrees/*-lane-a` under the same primary.
- **Affected missions observed**: `023-agent-identity-whatsapp-header` (issue #588 first reproduction, commit `84bf7b6` on `main`), `025-vikunja-date-timezone-bug` (second reproduction caught before landing, plus both reproductions of issue #589 on WP02 and WP03).

## 11. References

- Issue: Priivacy-ai/spec-kitty#588 — Bug Report: Sparse-checkout staleness after mission merge silently reverts merged WP content.
- Issue: Priivacy-ai/spec-kitty#589 — Bug Report: review-lock.json triggers spec-kitty's own uncommitted-changes guard, blocking approve transition.
- Historical context: commit `d0c158f4` (v0.11.0) — "fix: Switch from symlinks to git sparse-checkout (proper solution)", the introduction of sparse-checkout management in spec-kitty.
- Historical context: commit `8f5b56ed` (v0.15.0) — "refactor: consolidate sparse-checkout logic into VCS layer (Bug #120)", the hardening of that code path.
- Historical context: commit `5d238657` (v3.0.0, PR #347) — "feat: Canonical Context Architecture Cleanup + Hybrid Agent Surface", the commit that deleted the sparse-checkout policy without shipping a migration for existing user repos.
- Follow-up: Priivacy-ai/spec-kitty#617 — "Wire the MissionAudit and operator-override event families across CLI, events, and SaaS", the scoped follow-up mission for the durable audit surface deferred by this mission.

## 12. Decision Log

- **2026-04-14 — Layered hybrid for the sparse-checkout preflight.** The preflight is a hard block on `mission merge` and `agent action implement` (the two highest-leverage, highest-blast-radius entry points), with the commit-time backstop in `safe_commit` as the universal defence, a session-scoped warning at other state-mutating entry points, and `spec-kitty doctor` as the primary discovery surface. Alternatives considered: pure merge-only (rejected — misses the lane-worktree inheritance hazard and the external-pull cascade), pure blanket-gate on every state-mutating command (rejected — redundant with the backstop at the commit layer, worsens the escape-hatch experience for legitimate-sparse users). Rationale recorded here per DIRECTIVE_003.
- **2026-04-14 — `--allow-sparse-checkout` is distinct from `--force`.** `--force` is used elsewhere in the codebase to bypass guards that protect against routine friction; this override protects against silent data loss and must not be conflated. Recorded per DIRECTIVE_003.
- **2026-04-14 — Structured log record instead of a durable audit event for `--allow-sparse-checkout` use.** The original spec called for the override to be "recorded in an audit surface." Planning investigation confirmed that the two plausible surfaces — extending `status.events.jsonl` (single-purpose lane-transition schema, consumed by `spec-kitty-events` and `spec-kitty-saas`) or emitting a new cross-repo event via the existing pipeline — both require coordinated work across three repositories that is out of scope for a bugfix mission. The `MissionAudit*` schema family is defined in `spec-kitty-events` and its ingest is wired in `spec-kitty-saas`, but no emitter exists in the CLI; wiring the full surface is tracked as Priivacy-ai/spec-kitty#617 (which also identifies `DecisionPointOverridden` as the correct event for this specific override). Until that issue ships, FR-008 emits a stable structured log line (`spec_kitty.override.sparse_checkout`) at `WARNING` level; log collectors and shell redirection cover the short-term audit need. Alternatives considered: (a) extending `status.events.jsonl` with a non-lane-transition variant — rejected because it breaks the consumer schema contract, (b) creating a new local-only `.kittify/overrides.log` file — rejected because the user explicitly declined a new state file, (c) piggybacking on the existing but-unemitted `MissionAudit*` schema immediately — rejected because that family is semantically for post-hoc compliance audits, not for operator overrides, and `DecisionPointOverridden` is the semantically correct event. Recorded per DIRECTIVE_003.
