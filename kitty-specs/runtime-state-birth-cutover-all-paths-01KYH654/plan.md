# Implementation Plan: Runtime-State Birth-Cutover (All Landing Paths)

**Branch**: `fix/runtime-state-birth-cutover-all-paths` | **Date**: 2026-07-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/runtime-state-birth-cutover-all-paths-01KYH654/spec.md`

## Summary

Close the structural cause of #2917: the runtime-state birth-cutover stamp fires
only inside `spec-kitty merge` (`merge/executor.py::_run_birth_cutover`), so
missions landed via GitHub-side squash/rebase arrive un-cut-over and re-red the
release-gating dogfood corpus test on `main`. Deliver two mutually-reinforcing
mechanisms, both reusing the single existing cutover authority
(`runtime_state_cutover.cutover_mission`):

1. **Auto-stamp** the cutover into the mission branch at the terminal `accept`
   seam (runtime state is final; committed pre-PR so it rides through any merge).
2. A **fail-closed, diff-scoped pre-merge CI guard** — the *binding* backstop —
   that evaluates every mission whose corpus appears in the PR diff via the
   acceptance test's event-log-evidence predicate (not bare `verify_backfill`),
   is wired to fire on corpus-only PRs, and is a required, non-skippable check.

Plus a `spec-kitty doctor cutover` on-demand audit (FR-007). The mechanical
re-green of the pre-existing backlog already shipped as hotfix #2968; this
mission removes the recurrence and makes it enforceable.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing `specify_cli` internals — `migration/runtime_state_cutover.py`, `migration/backfill_runtime_state.py`, `merge/executor.py`, `cli/commands/accept.py`, `cli/commands/doctor.py`; GitHub Actions CI (`.github/workflows/`)
**Storage**: committed corpus artifacts under `kitty-specs/<mission>/` — `meta.json` (PRIMARY partition, `status_phase`) and `status.events.jsonl` (COORD partition, seed events)
**Testing**: pytest; red-first per DIRECTIVE_041; a GitHub-squash-merge simulation for US1; reuse of the acceptance test's event-log eligibility body
**Target Platform**: Linux CI + local dev
**Project Type**: single (CLI tool + CI workflows)
**Performance Goals**: diff-scoped guard < 30s in CI (NFR-002); full-corpus acceptance lock remains the slower gate (NFR-001)
**Constraints**: no direct push to `origin/main` (C-001); Phase-2 `status_phase="1"` only (C-002); do not rewrite the ~319 migrated missions (C-003); no spec-kitty execution assumed at GitHub-merge time (C-004)
**Scale/Scope**: ~322-mission corpus; two landing paths; one CI change + two CLI seams + one audit subcommand

## Charter Check

*GATE: passes. Re-check after design.*

- **Single canonical authority** (charter + #2160 thesis): the new stamp caller
  reuses `cutover_mission`; the guard reuses the acceptance test's eligibility
  body. No forked writer, no parallel checker — FR-005/FR-009.
- **ATDD-first / red-first**: every unit of work lands its failing
  acceptance/regression test first (GitHub-squash simulation, native-mission
  vacuity, payload determinism, corpus-only-PR guard trigger).
- **Coord/primary partition discipline**: seed events → COORD, `meta.json` →
  PRIMARY; reuse `cutover_mission`'s two-leg spine; coordinate with deferred
  #2923 (route `_flip_phase` through the placement port) rather than re-solving.
- **No green-washing**: the acceptance test predicate is not relaxed (rejected
  twice on #2917); "cut over" is proven from event-log evidence, never a vacuous
  `verify_backfill.ok` or a bare `status_phase` flip.

## Project Structure

### Documentation (this mission)

```
kitty-specs/runtime-state-birth-cutover-all-paths-01KYH654/
├── plan.md              # this file
├── research.md          # pre-planning grounding synthesis
├── data-model.md        # "cut over" state definition
├── contracts/           # stamp-seam + guard behavioral contracts
└── tasks.md             # /spec-kitty.tasks output
```

### Source Code (repository root)

```
src/specify_cli/migration/runtime_state_cutover.py   # cutover_mission:234, _flip_phase:186, cutover_repo:315 (single authority — REUSE)
src/specify_cli/migration/backfill_runtime_state.py  # verify_backfill:888, anchor resolution:432-483 (pin leg — R5)
src/specify_cli/merge/executor.py                    # _run_birth_cutover:939 (reference wiring to mirror)
src/specify_cli/cli/commands/accept.py               # terminal stamp seam (_commit_residual_acceptance_artifacts)
src/specify_cli/cli/commands/doctor.py               # + `doctor cutover` shell → _cutover_doctor.py
src/specify_cli/cli/commands/<guard>                 # diff-scoped guard entrypoint (reuses eligibility body)
tests/specify_cli/migration/test_dogfood_corpus_backfilled.py  # _mission_carries_event_log_runtime:142, _assert_birth_invariant_holds:242 (REUSE predicate)
.github/workflows/                                   # host guard; add kitty-specs/** to on.pull_request.paths (R1)
```

**Structure Decision**: single-project CLI. No new top-level packages; the work
adds one CLI seam (accept-time stamp), one guard entrypoint, one doctor
subcommand module, and one CI job — all reusing existing cutover internals.

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Terminal-lifecycle auto-stamp (single authority)

- **Purpose**: Stamp the cutover into the mission branch at the terminal `accept`
  seam so the committed corpus is already cut over before the branch can land by
  any path.
- **Relevant requirements**: FR-001, FR-004, FR-005, FR-006.
- **Affected surfaces**: `cli/commands/accept.py`, `migration/runtime_state_cutover.py` (reuse `cutover_mission`), mirror of `merge/executor.py::_run_birth_cutover`.
- **Sequencing/depends-on**: IC-02 (needs the pinned anchor to avoid divergent payloads).
- **Risks**: R4 — `_flip_phase` writes but does not commit; must commit both partitions into the landing branch with no reliance on the status daemon; worktree `.git`-redirect (WP09/#2920) means write to the branch's own `meta.json`, resume-heal, post-target-safe. Fail closed on absent `mission_id` (R6).

### IC-02 — Pin claim-anchor resolution to one canonical leg

- **Purpose**: Make the seed *payload* (including the resolved claim anchor)
  byte-identical across runs, machines, and landing-path contexts.
- **Relevant requirements**: NFR-004.
- **Affected surfaces**: `migration/backfill_runtime_state.py` (anchor resolution 432-483).
- **Sequencing/depends-on**: none (prerequisite for IC-01).
- **Risks**: R5 — divergent anchors leave a flipped-but-unverifiable corpus (`status_phase=1` while `verify_backfill` reds). Must test payload-level, not just seed-id, determinism.

### IC-03 — Diff-scoped fail-closed guard (logic)

- **Purpose**: Reject any change set that would leave an un-cut-over mission in
  the corpus, evaluating every mission in the PR diff via event-log evidence.
- **Relevant requirements**: FR-002, FR-003, FR-009, NFR-002, NFR-003.
- **Affected surfaces**: new guard entrypoint under `cli/commands/`; reuses `_mission_carries_event_log_runtime` / `_assert_birth_invariant_holds` + `verify_backfill`.
- **Sequencing/depends-on**: none.
- **Risks**: R2 — must NOT key on bare `verify_backfill.ok` (vacuous for native missions); R3 — guard is the binding backstop for seam-bypass paths, so it must scan all diff-touched missions and print the exact remedy (`spec-kitty migrate backfill-runtime-state --mission <slug>`). Fail closed on verify error / ambiguity / absent `mission_id`.

### IC-04 — CI wiring (guard fires on corpus-only PRs, required + non-skippable)

- **Purpose**: Ensure the guard actually runs on a PR whose diff is only
  `kitty-specs/**` and cannot be silently skipped.
- **Relevant requirements**: FR-008.
- **Affected surfaces**: `.github/workflows/` (host job's `on.pull_request.paths`; branch-protection required-checks).
- **Sequencing/depends-on**: IC-03.
- **Risks**: R1 (critical) — today `kitty-specs/**` triggers no test workflow and the dogfood test is push-only; the guard host must add `kitty-specs/**` (or use a no-paths workflow), run on `pull_request`, sit outside the src `changes` filter, and be a required check that *executes* (a skipped required check passes silently). Verify live with a scratch corpus-only PR — do not trust path-filter reading (#2968 lesson).

### IC-05 — On-demand cut-over audit

- **Purpose**: Let an operator list every mission's cut-over status outside CI.
- **Relevant requirements**: FR-007.
- **Affected surfaces**: `cli/commands/doctor.py` + new `_cutover_doctor.py`; backed by `cutover_repo(dry_run=True)`.
- **Sequencing/depends-on**: none.
- **Risks**: keep it a thin shell per the doctor per-subcommand convention; do not shoehorn a corpus-wide audit into the per-feature `run_doctor` aggregation.

### IC-06 — Durable acceptance lock + regression suite

- **Purpose**: Keep the full-corpus lock green and add the regressions that prove
  each invariant.
- **Relevant requirements**: NFR-001, SC-001..SC-004.
- **Affected surfaces**: `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py` and new tests under `tests/specify_cli/`.
- **Sequencing/depends-on**: spans IC-01..IC-04 (red-first tests land within their owning WP).
- **Risks**: R7 — touched-only guard vs full-corpus green is resolved (#2968 cleared the backlog whole-corpus); measure the guard's 30s bound on the real corpus. Coverage: GitHub-squash simulation (US1), guard-reds-on-native-un-cut-over (US2/R2), payload-determinism-across-legs (R5), guard-fires-on-corpus-only-PR (R1).

## Key Risks (pre-planning adversarial squad)

- **R1 (critical)** — CI topology: corpus-only PRs trigger no test workflow; the
  dogfood test is push-only. IC-04 must fix the trigger *and* verify it live.
- **R2 (critical)** — `verify_backfill` is vacuous for natively-born missions;
  the guard must key on event-log evidence (IC-03/FR-009).
- **R3** — seam-bypass paths make the guard, not the stamp, the binding enforcer.
- **R4** — stamp writes but does not commit; commit both partitions into the
  landing branch, no status-daemon reliance.
- **R5** — double-stamp payload divergence → flipped-but-unverifiable corpus;
  pin the anchor leg (IC-02).
- **R6** — fail closed on absent `mission_id`; never slug-namespace seeds.
- **R7** — resolved via #2968's whole-corpus re-green; measure the 30s bound.

## Complexity Tracking

*No Charter Check violations.* The mission adds no new architecture; it adds a
second caller of an existing authority, a guard reusing an existing predicate, a
thin doctor subcommand, and a CI trigger fix.

## Out of Scope

Read-side placement (#2922), write-target consolidation (#2966 B/C), terminology
migration (#2964), and redoing the #2968 mechanical re-green (C-005).
