# Implementation Plan: Coordination Topology Stabilization

**Branch**: `main` | **Date**: 2026-06-13 | **Spec**: [spec.md](spec.md)
**Mission**: coordination-topology-stabilization-01KTZVQ2 (01KTZVQ2KB742M37VB5V2380CN)
**Input**: Feature specification from `kitty-specs/coordination-topology-stabilization-01KTZVQ2/spec.md`

## Summary

Eight confirmed defects in spec-kitty's coordination branch topology are fixed in dependency order across eight workstreams. The root cause cluster is a write/read split: write paths were migrated to commit on a per-mission coordination branch, but read surfaces (gates, cleanliness checks, path anchoring) still treat the primary checkout as the sole authority. Fixes introduce a shared coord-topology-aware read primitive (WS1) that all other gate fixes extend, stop `.worktrees/` paths leaking into the git index (WS2), make the accept gate transactional (WS3), reduce the ff-merge operator tax (WS4), harden `next` query error handling (WS5), route ownership warnings correctly (WS6), suppress stale-assertion false positives (WS7), and add retrospective triggering to the merge-completion path (WS8).

The validated engineering brief is `WORKING-PLAN-coordination-stabilization-2026-06-12.md` in the repository root, produced by eight Debugger Debbie investigators with codebase-level evidence for each issue.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy (strict), ruff; spec-kitty-events 6.0.0, spec-kitty-tracker (external PyPI); GitPython (for git operations in accept/merge/safe-commit paths)
**Storage**: JSONL event log (`status.events.jsonl`), YAML/JSON frontmatter, `acceptance-matrix.json`, `lanes.json`, `meta.json`; no external database
**Testing**: pytest, mypy --strict, ruff; 90%+ line coverage for new code; integration tests for all CLI commands modified; architectural tests in `tests/architectural/`; regression tests added for each confirmed bug (one per FR)
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform CLI); coordination topology requires git 2.x worktrees
**Project Type**: Single Python CLI package (`src/specify_cli/`)
**Performance Goals**: No measurable regression on existing test suite runtime; gate checks must complete within existing CLI response-time envelope
**Constraints**: Fixes must not break flat (non-coordination) topology. All code merged via PR to `main`. `ruff` and `mypy --strict` must pass with zero issues. No blanket `# noqa` or `# type: ignore` suppressions.
**Scale/Scope**: Affects `src/specify_cli/acceptance/`, `src/specify_cli/cli/commands/accept.py`, `src/specify_cli/missions/software_dev/_substantive.py`, `src/specify_cli/post_merge/retrospective_terminus.py`, `src/specify_cli/post_merge/retrospective/generator.py`, `src/specify_cli/next/`, `src/specify_cli/merge/`, `src/specify_cli/stale_assertions.py`, `src/specify_cli/cli/commands/agent/tasks.py` (validate_glob_matches), `tests/architectural/`

## Charter Check

**Gate**: PASS

- Python 3.11+ ✓ (no legacy Python support required)
- Cross-platform ✓ (no platform-specific logic added)
- typer/rich/ruamel.yaml/pytest/mypy ✓ (all existing dependencies; no new ones required)
- mypy --strict required ✓ (all new code must pass)
- 90%+ test coverage for new code ✓ (enforced by NFR-003)
- PyPI distribution via automated release workflow ✓ (no release process changes)
- DIRECTIVE_003 (Decision Documentation Requirement): material decisions documented in research.md and data-model.md
- DIRECTIVE_010 (Specification Fidelity Requirement): implementation must match the approved FR set; deviations require explicit doc before accept

Re-check after Phase 1 design: no conflicts identified.

## Project Structure

### Documentation (this mission)

```
kitty-specs/coordination-topology-stabilization-01KTZVQ2/
├── plan.md              # This file
├── research.md          # Phase 0: engineering decisions
├── data-model.md        # Phase 1: affected modules, interfaces, state machines
├── contracts/           # Phase 1: gate contracts, error-code contracts
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/specify_cli/
├── acceptance/
│   ├── __init__.py          # WS3: git_dirty gate, matrix write modes
│   └── matrix.py            # WS3: mutate_matrix gate
├── cli/commands/
│   ├── accept.py            # WS3: --no-commit → mutate_matrix=False
│   └── agent/
│       └── tasks.py         # WS6: validate_glob_matches severity + routing
├── missions/software_dev/
│   └── _substantive.py      # WS1: is_committed() coordination-aware
├── next/
│   └── runtime_bridge.py    # WS5: query_current_state fail-closed
├── merge/
│   ├── executor.py          # WS2: _feature_dir_file_paths root fix; WS4: advance_branch_ref rollout
│   └── safe_commit.py       # WS2: path_is_under_worktrees rejection
├── post_merge/
│   ├── retrospective_terminus.py  # WS8: triggering path
│   └── retrospective/
│       └── generator.py           # WS8: artifact ingestors
└── stale_assertions.py            # WS7: message-content classification

tests/
├── architectural/
│   └── test_worktrees_index_clean.py  # WS2: ratchet
├── specify_cli/
│   ├── test_accept_gate_convergence.py    # WS3 regression
│   ├── test_is_committed_coord_aware.py   # WS1 regression
│   ├── test_next_fail_closed.py           # WS5 regression
│   ├── test_stale_assertions_message.py   # WS7 regression
│   ├── test_finalize_ownership_routing.py # WS6 regression
│   └── test_retrospective_triggering.py   # WS8 regression
```

**Structure Decision**: Single Python CLI package. No new packages, modules, or project roots introduced.

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Coordination-Aware Read Primitive

- **Purpose**: Provide a single `is_committed(file, repo_root, placement)` function that consults the mission's coordination branch (via `git cat-file -e <coord-ref>:<rel>`) before falling back to primary HEAD, so all gate checks see coordination-branch commits as valid committed artifacts.
- **Relevant requirements**: FR-003; supports FR-001, FR-005
- **Affected surfaces**: `src/specify_cli/missions/software_dev/_substantive.py:214-239`; `src/specify_cli/cli/commands/agent/mission.py` (setup-plan entry gate caller); `src/specify_cli/missions/software_dev/mission.py:603-621` (silent fallbacks in `_planning_commit_worktree`)
- **Sequencing/depends-on**: none (foundational; all other gate ICs build on this)
- **Risks**: Must preserve flat-topology behavior. Coordinate with PR #1895 which may already address the FR-001 slice. `resolve_placement_only` must not be called for missions without a coordination branch (guard against `KeyError`/`None`).

### IC-02 — .worktrees/ Index Leakage: Writer Fix + Ratchet + Cleanup

- **Purpose**: Stop `.worktrees/<coord>/` paths from entering the git index; add a fail-closed guard at every commit choke point; land an architectural ratchet test; remove the 26 already-tracked paths from `origin/main`.
- **Relevant requirements**: FR-005
- **Affected surfaces**: `src/specify_cli/merge/executor.py:441` (`_feature_dir_file_paths`); `src/specify_cli/merge/safe_commit.py` (backstop); `src/specify_cli/bookkeeping/transaction.py` (`BookkeepingTransaction.write_artifact`); `tests/architectural/` (ratchet); `kitty-specs/` (26 leaked path removal)
- **Sequencing/depends-on**: Writer fix first → ratchet test → cleanup PR (in that order per C-005)
- **Risks**: Removing the 26 leaked paths changes `is_committed` behavior for the legacy `do-dispatch-open-op-lifecycle-01KTSJ2H-coord` mission (IC-01/IC-02 interaction defect). Test both states.

### IC-03 — Accept Gate Transactional Ownership

- **Purpose**: Make `--no-commit` truly read-only; make the git_dirty gate exclude accept-owned derived artifacts; fold residue into a commit on all writing exit paths so retries converge.
- **Relevant requirements**: FR-001, FR-002
- **Affected surfaces**: `src/specify_cli/acceptance/__init__.py` (git_dirty gate, collect_feature_summary); `src/specify_cli/cli/commands/accept.py:284` (mutate_matrix); `src/specify_cli/acceptance/matrix.py` (write_acceptance_matrix gating)
- **Sequencing/depends-on**: IC-01 (coord-aware read primitive for write-target split fix)
- **Risks**: Encoding-normalization retry path (`src/specify_cli/scripts/tasks/tasks_cli.py:157-191`) creates a true same-run self-defeat; must be covered by the same fix or an explicit follow-up. Frontmatter lost-update race (unlocked read-modify-write in `agent/tasks.py:3662-3688` and `status/emit.py:359-364`) is a companion defect; address or explicitly defer.

### IC-04 — ff-merge Treadmill Elimination

- **Purpose**: Roll out `advance_branch_ref` as the standard post-write primary-ref sync everywhere the coordination branch is written, so operators never need to run `git merge --ff-only` manually.
- **Relevant requirements**: FR-010
- **Affected surfaces**: `src/specify_cli/merge/executor.py` (`advance_branch_ref` call sites); `src/specify_cli/missions/software_dev/mission.py:2512-2515` (`_ensure_branch_checked_out` shim); coord-owned residue exclusion shared with IC-03's #1814 pattern
- **Sequencing/depends-on**: IC-01, IC-03 (advance_branch_ref must share the coord-owned-residue exclusion before rollout)
- **Risks**: `advance_branch_ref` currently refuses on coord-owned residue (status.events.jsonl, status.json, tasks/.gitkeep). Must share the exclusion list from IC-03/#1814 or will abort on valid residue.

### IC-05 — Fail-Closed next Query Mode

- **Purpose**: Replace the silent exit-0 "unknown" stub in `query_current_state` with a structured named error (`MISSION_NOT_FOUND`) that exits non-zero in both human and JSON modes.
- **Relevant requirements**: FR-004
- **Affected surfaces**: `src/specify_cli/next/runtime_bridge.py:3074-3097`; `src/specify_cli/cli/commands/next.py:331-357` (`_resolve_mission_slug`)
- **Sequencing/depends-on**: none (independent; coordinate with PR #1895 which may already implement this)
- **Risks**: Two near-identical "unknown" branches in runtime_bridge.py (at :3074 and :3087-3097); both must be replaced. The `StatusReadPathNotFound` swallow in `_resolve_mission_slug` and the advancing-mode `--result` path need the same treatment.

### IC-06 — Ownership Validation Warning Routing

- **Purpose**: Make ownership warnings emitted by `validate_glob_matches` visible to operators (stderr in JSON mode; human-readable report) and promote literal-path zero-match from warning to hard error with nearest-match suggestion.
- **Relevant requirements**: FR-006
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/tasks.py` (`validate_glob_matches`, `finalize_tasks`); `src/doctrine/missions/mission-steps/software-dev/tasks-finalize/prompt.md` (source template requiring prompt update to react to warnings); agent copies in `.claude/`, `.github/`, etc. (generated; updated via `spec-kitty upgrade`)
- **Sequencing/depends-on**: none (independent)
- **Risks**: Literal-path hard error is a behavioral tightening (C-006). Must handle the legitimate planned-new-file case (zero-match valid by annotation). Re-validate at lane-compute time to catch phantoms that enter `lanes.json`.

### IC-07 — Stale-Assertion Message-Content Classifier

- **Purpose**: Classify the containment target of each stale-assertion finding; suppress or demote findings where the literal appears inside a message-capture expression (`str(exc)`, `excinfo.value`, `.message`/`.stderr`/`.stdout`, capsys captures).
- **Relevant requirements**: FR-009
- **Affected surfaces**: `src/specify_cli/stale_assertions.py:350` (`_literal_findings_for_assertion`); `src/specify_cli/merge/executor.py:2570-2571` (merge summary confidence threshold)
- **Sequencing/depends-on**: none (independent)
- **Risks**: The identifier channel (stale_assertions.py:440-479) has the same flaw at higher confidence — medium/high findings may also be affected. The `changed_literals` dict is last-wins, dropping multi-site removal reports; fix this alongside the classifier.

### IC-08 — Terminus Retrospective Triggering + Content

- **Purpose**: Ensure the terminus retrospective fires on ALL mission completion paths (not only `spec-kitty next` terminal-decision branch); ingest mission-local artifact files as generator inputs.
- **Relevant requirements**: FR-007, FR-008
- **Affected surfaces**: `src/specify_cli/post_merge/retrospective_terminus.py` (`_record_path_str`, `run_terminus`); `src/specify_cli/post_merge/retrospective/generator.py:684,844-846` ("helped only by contrast" rule; stale docstring); `src/specify_cli/merge/executor.py` (merge completion postcondition); `src/specify_cli/cli/commands/merge.py`
- **Sequencing/depends-on**: IC-01 (path resolution for coord topology); triggering half can start once IC-01 exists; content half (generator ingestors) is independent
- **Risks**: `run_terminus` is dead lifecycle code (retrospective.skipped events unreachable in production). Do not duplicate — consolidate with `_run_retrospective_learning_capture`. The "helped only by contrast" generator rule guarantees `ran_no_findings` on clean missions; revisit the rule, not just the ingestor.

## Sequencing

```
IC-01 (read primitive) ─────────────────────────────────────────────────┐
                                                                         ▼
IC-02 (worktrees writer) ─────────────────────────────────────────────► IC-02 cleanup PR
                                                                         ▲
IC-03 (accept gate) ──────────────────── depends on IC-01 ─────────────┤
                                                                         ▼
IC-04 (ff-merge treadmill) ──── depends on IC-01, IC-03 ──────────────►
                                                                         
IC-05 (next fail-closed) ─── independent ──────────────────────────────►
IC-06 (ownership routing) ── independent ──────────────────────────────►
IC-07 (stale-assertion)  ─── independent ──────────────────────────────►
IC-08 (retrospective) ─────── triggering half after IC-01; content independent
```

Suggested dispatch order: IC-01 → IC-02 (writer, parallel with IC-01 late) → IC-03 → IC-05, IC-06, IC-07 (parallel) → IC-04 → IC-08.
