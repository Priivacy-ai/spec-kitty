# Research: Legacy Sparse-Checkout Cleanup and Review-Lock Hardening

**Mission**: `legacy-sparse-and-review-lock-hardening-01KP54ZW`
**Phase**: 0 (Research)
**Date**: 2026-04-14

This document records the investigations that resolved every planning ambiguity before the plan, data-model, and quickstart were drafted. Each finding concludes with a decision, a rationale, and the alternatives that were considered and rejected.

---

## R1. Historical path of sparse-checkout in spec-kitty

**Question**: When did spec-kitty add sparse-checkout support, when was it removed, and what migration (if any) was shipped alongside the removal?

**Finding**: Sparse-checkout was introduced in v0.11.0 via commit `d0c158f4` ("fix: Switch from symlinks to git sparse-checkout (proper solution)"), hardened in v0.15.0 via commit `8f5b56ed` ("refactor: consolidate sparse-checkout logic into VCS layer (Bug #120)"), and deleted in v3.0.0 / feature 057 via commit `5d238657` in PR #347 ("feat: Canonical Context Architecture Cleanup + Hybrid Agent Surface"). The commit message states that the change "deletes sparse checkout policy." The `src/specify_cli/core/vcs/protocol.py` header now reads "Creates a full-checkout workspace. Sparse checkout is not supported; all files are visible in every workspace."

**No user-repo migration shipped with v3.0.0.** Upgraded users retain whatever `core.sparseCheckout` and `.git/info/sparse-checkout` state was written by the pre-3.0 code paths.

**Decision**: This mission ships the missing migration as a doctor-offered remediation (not an automatic upgrade step), consistent with C-002. The remediation performs `git sparse-checkout disable`, unsets `core.sparseCheckout`, removes the pattern file, and refreshes the working tree with `git checkout HEAD -- .`.

**Alternatives rejected**:
- Automatic migration on upgrade — rejected because the refresh step discards uncommitted working-tree state in the sparse cone and must require explicit consent.
- Silent detection only (warn but never fix) — rejected because the condition is the root cause of an observed data-loss regression; warn-only leaves users stuck.

---

## R2. Mechanism of the phantom-deletion cascade

**Question**: What is the exact sequence by which a merge in a sparse-configured repo produces silent deletions on the target branch?

**Finding**: The sequence, verified by reading `src/specify_cli/cli/commands/merge.py` and `src/specify_cli/git/commit_helpers.py`:

1. `_run_lane_based_merge_locked` runs lane-to-mission and mission-to-target merges.
2. `git merge` advances `HEAD` to the merged tree. In a sparse checkout, `skip-worktree` bits on sparse-excluded paths leave the working tree unchanged for those paths.
3. The function then invokes `safe_commit(repo_path=main_repo, files_to_commit=[status.events.jsonl, status.json], commit_message="chore(...): record done transitions for merged WPs")`.
4. `safe_commit` uses `git stash` to preserve existing staging area, then stages only the requested files, commits, and `git stash pop`s. The `git stash` / `git stash pop` cycle — when run on a tree where `HEAD` has advanced ahead of the working tree due to sparse-checkout — promotes the sparse-excluded paths into the staging area as deletions.
5. The commit sweep produces a housekeeping commit whose actual diff includes those phantom deletions, even though `files_to_commit` only referenced the status files.

This produces the exact symptom Kent reported: commit `84bf7b6` on his `main` silently reverted 243 lines across four files.

**Decision**: Three defenses, in layers:
1. Fix the proximate cause in the merge path (FR-013 post-merge refresh + FR-014 invariant assertion) so `HEAD` and the working tree match before any subsequent commit runs.
2. Fix the root cause of silent data loss at the commit layer (FR-011 backstop in `safe_commit`) so that unexpected staged deletions cannot be committed regardless of which command triggered the cascade.
3. Block the cascade from entering the merge path at all by preflighting for sparse-checkout state (FR-006) on mission merge and (FR-007) on agent-action implement.

**Alternatives rejected**:
- Fixing `safe_commit` to use `git commit -- <file>` directly instead of the stash/pop dance — explored. The stash/pop dance exists to preserve unrelated staged state from the caller; removing it changes semantics for the many non-merge callers of `safe_commit` and would require a broader audit than this mission can absorb. The backstop approach protects every caller without changing existing semantics.

---

## R3. Cross-repo impact of the `--allow-sparse-checkout` audit requirement

**Question**: FR-008 originally said "recorded in an audit surface." What is the minimum-scope way to record the override?

**Finding**:

- `status.events.jsonl` uses `StatusEvent` (a WP lane-transition record). Adding a new event variant would break the schema contract consumed by `spec-kitty-events` and `spec-kitty-saas`.
- `spec-kitty-events` has a full pydantic `MissionAudit*` event family (`mission_audit.py`, schema version 2.5.0, including a deterministic reducer), a `DecisionPointOverridden` event family (semantically exact for operator overrides — carries rationale, alternatives considered, evidence refs, and authority role), and a `WarningAcknowledged` event family. All families have JSON schema files in `src/spec_kitty_events/schemas/`.
- `spec-kitty-saas` has `apps/dossier/migrations/0002_missionauditlog.py` and downstream ingest / materialize / test code for the audit family.
- The spec-kitty CLI has **zero emission paths** for any of these event families. Grepped 2026-04-14: no matches for `MissionAudit`, `DecisionPointOverridden`, or `WarningAcknowledged` under `src/specify_cli/`.

**Decision**: FR-008 is softened to emit a structured log record (stable marker `spec_kitty.override.sparse_checkout`) at `WARNING` level; durable cross-repo audit wiring is deferred to Priivacy-ai/spec-kitty#617. That follow-up covers the full emitter wiring across all three repos (CLI emitter, events schema confirmation, SaaS ingest + dashboard surfacing) and identifies `DecisionPointOverridden` as the semantically correct event for operator-override use.

**Alternatives rejected**:
- Extending `status.events.jsonl` with a non-transition event variant — rejected per R3 above.
- Creating a new local-only file (e.g. `.kittify/overrides.log`) — rejected per user direction ("not ready to create a new state file").
- Immediately wiring `MissionAudit*` end-to-end for this one override use case — rejected because (a) `MissionAudit*` is semantically for post-hoc compliance audits, not operator overrides, and (b) the work spans three repos and a coordinated release.

---

## R4. Module layout for the new code

**Question**: Where should the sparse-checkout detection primitive, remediation logic, and related warning hook live?

**Finding**: The backstop (FR-011) must live in `src/specify_cli/git/commit_helpers.py` where `safe_commit` is defined. The detection primitive is a git-layer concept and has natural affinity with `commit_helpers.py`. Remediation composes operations on both the primary repo and child worktrees; it is distinct enough from detection to justify a separate file for readability.

**Decision**:
- New module `src/specify_cli/git/sparse_checkout.py` houses the detection primitive (FR-001) and the structured-log warning emitter (FR-010, the session-flag owner).
- Remediation logic lives in a companion `src/specify_cli/git/sparse_checkout_remediation.py` that imports detection and composes `git sparse-checkout disable`, `git config --unset`, and working-tree refresh across primary + lane worktrees.
- Existing `src/specify_cli/git/commit_helpers.py` receives the FR-011 staging-area backstop inline; no new file required.
- The `spec-kitty doctor` surface imports from both, adding the finding and the remediation action.
- The merge and implement preflights import detection from `sparse_checkout.py` (layer 1).
- All other state-mutating CLI commands import the session-warning emitter from `sparse_checkout.py` (layer 3).

**Alternatives rejected**:
- New top-level package `src/specify_cli/sparse_checkout/` — rejected as premature; two files do not justify a package.
- Placing detection in `src/specify_cli/core/` — rejected; sparse-checkout is a git-layer primitive and the `core/` package is for cross-cutting runtime concepts.

---

## R5. Session-warning once-per-process mechanism

**Question**: How is the once-per-process guarantee of FR-010 / NFR-005 implemented?

**Finding**: The spec-kitty CLI is a Typer application with short-lived processes; a module-level flag is sufficient for the single-process guarantee. Tests reset the flag via a fixture.

**Decision**: A module-level `_SparseWarningEmitted: bool = False` in `sparse_checkout.py`, flipped to `True` after the first emission. A corresponding `_reset_session_warning_state()` test helper is provided for pytest fixture use.

**Alternatives rejected**:
- Typer app state — rejected as over-engineered for a single boolean.
- Explicit `SessionState` class — rejected for the same reason; would expand scope.

---

## R6. Detection precision for `core.sparseCheckout=true` with no effective filter

**Question**: Should the detection primitive treat "config set but patterns include everything" as active sparse-checkout (trigger the block) or as inactive (allow through)?

**Finding**: The configuration flag is the canonical signal that a user is operating in sparse mode. Even if the current patterns happen to include everything, the flag being set means any future pattern update will immediately re-enable filtering. The safety of spec-kitty's post-merge refresh step depends on the assumption that the working tree mirrors `HEAD` unconditionally; `core.sparseCheckout=true` breaks that assumption whether or not the current patterns are inclusive.

**Decision**: Treat `core.sparseCheckout=true` as definitively sparse, regardless of pattern contents. The detection primitive returns a structured result (`SparseCheckoutState` dataclass) that exposes `config_enabled`, `pattern_file_present`, `pattern_file_path`, and a summary boolean `is_active`. `is_active` is true iff `config_enabled` is true.

**Alternatives rejected**:
- Parsing pattern contents to decide — rejected; requires implementing git's pattern matcher, brittle, and trades a bright-line rule for a complex one.
- Config-only detection that ignores the pattern file — rejected; the pattern file's presence is still useful audit context for the doctor finding and the remediation plan.

---

## R7. CI / non-interactive detection for FR-023

**Question**: How is a non-interactive environment detected for the purpose of skipping doctor's interactive remediation prompt?

**Finding**: Standard Python is `sys.stdin.isatty()`. Common CI indicators: `CI=true`, `GITHUB_ACTIONS=true`, `GITLAB_CI=true`, `BUILDKITE=true`. Combining both gives a robust signal.

**Decision**: Helper `_is_interactive_environment() -> bool` returns true iff `sys.stdin.isatty()` is true AND no well-known CI environment variable is set to a truthy value. Doctor's remediation prompt short-circuits to "exit non-zero with remediation one-liner" whenever this helper returns false.

**Alternatives rejected**:
- `isatty` only — rejected; some CI runners provide a TTY.
- CI env vars only — rejected; misses local non-interactive pipelines (e.g. `spec-kitty doctor | less`).

---

## R8. Remediation for existing lane worktrees

**Question**: When a user ran pre-3.0 spec-kitty and later ran 3.x, `git worktree add` inherited `core.sparseCheckout=true` from the primary into each lane worktree. The sparse patterns, however, live per-worktree in `.git/worktrees/<lane>/info/sparse-checkout`. What does remediation need to do for each worktree?

**Finding**: For each lane worktree under `.worktrees/*`:
1. Run `git sparse-checkout disable` inside the worktree.
2. Unset `core.sparseCheckout` in the worktree's git config (the worktree has its own config overrides when non-default values are set).
3. Remove the per-worktree `.git/worktrees/<lane>/info/sparse-checkout` pattern file if present.
4. Run `git checkout HEAD -- .` inside the worktree to refresh.
5. Assert `git status --porcelain` is clean.

Step 1 (`git sparse-checkout disable`) is documented to handle both config unset and working-tree refresh; however, relying on it alone would couple remediation to git's implementation details. The multi-step approach is explicit and testable.

**Decision**: Remediation iterates `.worktrees/*` after repairing the primary, applies the above five steps per worktree, and aggregates any failures into a single user-facing report.

**Alternatives rejected**:
- Primary-only remediation — rejected because lane worktrees that inherited the state are still broken and will misbehave on next use.
- Rely on `git sparse-checkout disable` as a single-step fix — rejected for implementation-coupling reasons above.

---

## R9. ADR candidacy

**Question**: Charter tactics include `adr-drafting-workflow`. Does this mission warrant an ADR?

**Finding**: The layered-hybrid preflight architecture is a material decision with rejected alternatives (pure-merge-only and pure-blanket-gate). The Decision Log in the spec captures this under DIRECTIVE_003, but an ADR in `architecture/1.x/adr/` would formalize it for future contributors.

**Decision**: Draft an ADR in `architecture/1.x/adr/2026-04-14-1-sparse-checkout-defense-in-depth.md` as part of the implementation. The ADR describes the four-layer architecture, records the rejected alternatives, and notes the commit-time backstop as the universal defense that applies regardless of the entry point.

**Alternatives rejected**:
- Skip the ADR and rely on the spec's Decision Log — rejected; the architecture is load-bearing across four files and future contributors should find the reasoning in the canonical ADR location.

---

## Summary of decisions

| Topic | Decision |
|---|---|
| Remediation kind | Doctor-offered; not automatic on upgrade |
| Data-loss defense | Three layers: merge-path refresh (proximate), commit-layer backstop (root), preflight (prevention) |
| `--allow-sparse-checkout` audit | Structured log record; durable event deferred to Priivacy-ai/spec-kitty#617 |
| Module layout | `src/specify_cli/git/sparse_checkout.py` + `sparse_checkout_remediation.py`; backstop in existing `commit_helpers.py` |
| Session-warning mechanism | Module-level flag |
| Detection rule | `core.sparseCheckout=true` ⇒ active, irrespective of pattern contents |
| Non-interactive detection | `isatty` AND no common CI env var |
| Worktree remediation | Iterate `.worktrees/*`, apply 5-step repair per worktree |
| ADR | Draft `architecture/1.x/adr/2026-04-14-1-sparse-checkout-defense-in-depth.md` |
