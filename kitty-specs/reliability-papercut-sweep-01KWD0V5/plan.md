# Implementation Plan: Reliability Papercut Sweep

**Branch**: `fix/reliability-papercut-sweep` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/reliability-papercut-sweep-01KWD0V5/spec.md`

> Post-plan squad adjustments folded (2026-06-30): corrected source paths, consumer/call-site
> counts, `read_topology` purity pin, IC-01 cross-gate scope, and the IC-04/IC-06 merge. See
> research.md § "Post-plan squad findings & adjustments".

## Summary

Fix six operator-facing reliability defects in two cohesive, file-disjoint lanes, each defect
landing a red-first regression test. Lane A repairs operator coord/gate papercuts (dirty-tree
allowlist, never-created-coord classification + remediation, doctor recovery hint). Lane B
repairs identity / surface-resolution residuals (a single canonical mission-identity contract,
and target_branch silent-fallback). The approach is fixed by a pre-flight + post-plan squad:
fail-closed over silent fallback, canonical ULID identity, and — binding — keep
`classify_topology` AND `read_topology` pure (git-existence probing lives at the
surface-resolver remediation + backfill **write** boundary, never in the read/SSOT path).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console), ruamel.yaml (frontmatter), subprocess/git
**Storage**: filesystem — `meta.json`, `status.events.jsonl`, `kitty-ops/<ulid>.jsonl`, git refs/worktrees
**Testing**: pytest, red-first regression per fixed defect (fail on pre-fix code via the existing operator entry point); ruff + mypy clean; cyclomatic complexity ≤ 15 on touched functions
**Target Platform**: Linux/macOS developer CLI (spec-kitty-cli)
**Project Type**: single (Python CLI library under `src/`)
**Performance Goals**: N/A — correctness/reliability mission, no throughput target
**Constraints**: no new silent fallback (fail closed on read failure); `classify_topology` AND `read_topology` stay pure (C-001); `target_branch` reader call sites unchanged (thin adapters, C-005); intra-lane shared-file WPs sequenced (C-002)
**Scale/Scope**: 8 issues / 7 implementation concerns, ~bug-fix scale, 2 lanes, ~14–18 source/test files touched (#2274 + #2275 folded post-tasks)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter policy summary (typer / rich / ruamel.yaml / pytest / mypy) is consistent with this
mission — no new dependencies, frameworks, or architectural deviation. The mission *reinforces*
existing doctrine (fail-closed, no silent fallback, canonical-surface authority, pure SSOT).
**No charter violations; Complexity Tracking is empty.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/reliability-papercut-sweep-01KWD0V5/
├── plan.md  research.md  data-model.md  quickstart.md  contracts/   # planning artifacts
└── tasks.md                                                          # Phase 2 (/spec-kitty.tasks)
```

### Source Code (repository root) — verified paths

```
src/
├── mission_runtime/
│   ├── artifacts.py                       # IC-01: is_self_bookkeeping_path (shared dirty-tree authority)
│   └── context.py                         # IC-02: classify_topology (PURE — unchanged)
├── specify_cli/
│   ├── acceptance/__init__.py             # IC-01: _accept_dirty_gate (consume shared authority)
│   ├── coordination/
│   │   ├── surface_resolver.py            # IC-02: CoordinationBranchDeleted remediation + _coord_branch_exists
│   │   └── status_transition.py           # (read_topology consumer — must stay behavior-stable)
│   ├── migration/backfill_topology.py     # IC-02: git-probe at backfill WRITE path; read_topology stays PURE
│   ├── cli/commands/
│   │   ├── _coordination_doctor.py        # IC-02/IC-03: coord recovery hint (shared → sequence)
│   │   └── _workspace_husk_doctor.py      # IC-03: real recovery path
│   ├── events/decision_log.py             # IC-04: slug→mission_id fallback site #1 (:98)
│   ├── review/prompt_metadata.py          # IC-04: slug→mission_id fallback site #3 (:149)
│   ├── merge/preflight.py                 # IC-01: merge dirty-tree gate (consume shared authority)
│   └── core/{paths.py, git_ops.py}        # IC-05: the 3 target_branch readers
└── runtime/next/runtime_bridge.py         # IC-04: _resolve_mission_ulid (#2) + mint boundary (empty-mid8)

tests/
├── mission_runtime/test_self_bookkeeping_allowlist.py        # IC-01 extend
├── specify_cli/cli/commands/test_doctor_coordination.py      # IC-03 re-pin
├── specify_cli/cli/commands/test_doctor_cli_surface_golden.py # IC-03 re-pin
├── specify_cli/events/test_decision_log.py                   # IC-04 INVERT stale test
├── agent/test_orchestrator_merge_target.py                   # IC-05 extend
└── (new red-first regression tests per IC)
```

**Structure Decision**: Single Python CLI project; surgical edits to the named modules + test homes. No new packages.

## Complexity Tracking

*No charter violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.
> Five ICs (IC-04 absorbed the former IC-06 identity-mint concern per the post-plan review).

### IC-01 — Shared dirty-tree self-bookkeeping authority (kitty-ops debris)

- **Purpose**: a `kitty-ops/<ulid>.jsonl` orphan must not block ANY dirty-tree gate, while genuine mission dirt still blocks.
- **Relevant requirements**: FR-001 (#2251)
- **Affected surfaces**: `src/mission_runtime/artifacts.py` (`is_self_bookkeeping_path` — add kitty-ops arm); route **all three** dirty-tree gates through it: record-analysis (`mission_record_analysis.py:131`, already consumes it), the accept gate (`specify_cli/acceptance/__init__.py` `_accept_dirty_gate`), and merge preflight (`merge/preflight.py`). Extend `tests/mission_runtime/test_self_bookkeeping_allowlist.py`.
- **Sequencing/depends-on**: none (Lane A, independent of IC-02/IC-03 files)
- **Risks**: keep the match tight (kitty-ops segment + ULID-`.jsonl`) so it cannot mask real dirt; preserve disjoint-set G-5. The accept/merge gates today keep *separate* allowlists — converge them on the shared authority (else split-brain partial fix). Cite #2102; reference umbrella **#1914** (no-op-stable gates) as the deeper framing.

### IC-02 — Coord topology classification & remediation for a never-created branch

- **Purpose**: a declared-but-never-created `coordination_branch` must not classify as healthy `coord`; remediation leads with "flatten".
- **Relevant requirements**: FR-002 (#2250)
- **Affected surfaces**: `src/specify_cli/coordination/surface_resolver.py` (remediation ordering + reuse `_coord_branch_exists` / `probe_coord_state`), `src/specify_cli/migration/backfill_topology.py` (git-existence probe at the **write/migrate** path `backfill_mission_topology`), `_coordination_doctor.py` (hint). **`classify_topology` (context.py) AND `read_topology` (backfill_topology.py) stay PURE.**
- **Sequencing/depends-on**: shares `_coordination_doctor.py` with IC-03 → C-002 (sequence IC-02 → IC-03).
- **Risks**: C-001 binding — do NOT git-probe inside `classify_topology` (6 consumers) NOR inside `read_topology` (consumed by Lane B's `runtime_bridge.py:173,189` + `resolution.py:764` + `status_transition.py:601` — probing there silently reclassifies for Lane B = cross-lane behavioral shift). Scope: "lead-with-flatten + stop mis-classifying", not reflog-grade never-vs-torn-down provenance. Cite #2219.

### IC-03 — Doctor coordination recovery hint + #1890 recurrence guard

- **Purpose**: every recommended recovery command exists and performs the recovery; guard the recurred #1890 dead-command class; handle a stale-behind-tip worktree.
- **Relevant requirements**: FR-003 (#2240)
- **Affected surfaces**: `_coordination_doctor.py`, `_workspace_husk_doctor.py`; re-pin `test_doctor_coordination.py` + `test_doctor_cli_surface_golden.py`.
- **Sequencing/depends-on**: **after IC-02** (shared `_coordination_doctor.py` — C-002).
- **Risks**: the literal phantom string is already gone (#1890 / `ecf45f52c`); residual is the real recovery path + a standing regression test so the class can't recur silently. Cite #1890. See-also #2017.

### IC-04 — Canonical mission-identity contract (fail-closed) [absorbs former IC-06]

- **Purpose**: `mission_id` persisted anywhere is ALWAYS a ULID; an absent ULID fails closed; the coordination-branch identity is minted once at the canonical boundary (no empty-mid8).
- **Relevant requirements**: FR-004 (#2138) + FR-006 (#2091)
- **Affected surfaces** (one owner, one contract): `src/specify_cli/events/decision_log.py:98`, `src/specify_cli/review/prompt_metadata.py:149` (third slug→mission_id site found post-plan), `src/runtime/next/runtime_bridge.py` (`_resolve_mission_ulid` + the `:224` slug-sentinel idiom + the mint boundary). **INVERT** `tests/specify_cli/events/test_decision_log.py::test_slug_fallback_when_no_mission_id` (C-003).
- **Sequencing/depends-on**: none (single self-contained identity contract).
- **Risks**: merged from IC-04+IC-06 because they are contract-coupled — the mint boundary calls `_resolve_mission_ulid`, and `runtime_bridge:224` encodes the slug-as-sentinel that this contract removes; splitting them would recreate the define-here/consume-there split. The flat path must source the ULID (meta or mint), not delete the fallback blindly (coord path already fails closed). Cite #2136.

### IC-05 — target_branch read primitive + thin adapters (fail-closed)

- **Purpose**: one canonical `target_branch` read primitive distinguishing field-absent (default) from read-failure (fail closed); the three readers become thin adapters, call sites unchanged.
- **Relevant requirements**: FR-005 (#2139)
- **Affected surfaces**: `src/specify_cli/core/paths.py` (`get_feature_target_branch`, `resolve_merge_target_branch`), `src/specify_cli/core/git_ops.py` (`resolve_target_branch`); extend `tests/agent/test_orchestrator_merge_target.py`. The 2 higher-level resolvers (`orchestrator_api/commands.py`, `merge/resolve.py`) already delegate — no separate edit.
- **Sequencing/depends-on**: none (Lane B, file-disjoint from IC-04).
- **Risks**: ~18–20 genuine call sites (raw refs ~64 incl. delegating wrappers) must stay behavior-stable (C-005, not a bulk rename); three return types (str / tuple+provenance / BranchResolution) keep their adapter shapes; the WP's test scope must prove behavior-stability across consumers. Sibling field-absent readers (`context/resolver.py`, `mission_branch_context.py`, retrospective) serve different concerns → out of scope (single-primitive follow-up). Cite #2065.

### IC-06 — Lane-hygiene guard compares by content, not commit-history (Lane A) [folded #2274]

- **Purpose**: the `kitty-specs`-on-lane guard must not false-positive on `kitty-specs/` files that are byte-identical to the planning tip after a legitimate planning-branch rebase.
- **Relevant requirements**: FR-007 (#2274)
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/tasks.py` — `_list_wp_branch_mission_specs_changes` (~:876-913) currently does `git merge-base HEAD base` then `git diff {merge_base}..HEAD -- kitty-specs/`. Add a content re-check against the planning-branch tip; drop zero-content-diff files. New test.
- **Sequencing/depends-on**: none, but **shares `tasks.py` with IC-07** → IC-07 sequenced after IC-06 (C-002-style).
- **Risks**: small/local; verify only genuine divergence still requires `--force`. Directly relevant to THIS mission's own just-rebased branch. Occurrence class A3 of #2017.

### IC-07 — Review-artifact lane-vs-coord authority (approve-over-rejected) (Lane A) [folded #2275]

- **Purpose**: `move-task --to approved` over a coord-latest `rejected` artifact must persist the approved/override artifact in the **coord** worktree (where the merge gate reads), so a genuinely-approved terminal WP is not blocked by `REJECTED_REVIEW_ARTIFACT_CONFLICT`.
- **Relevant requirements**: FR-008 (#2275)
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/tasks_materialization.py` (`_persist_review_artifact_override` → write to the coord artifact dir via the kind-aware seam), `src/specify_cli/post_merge/review_artifact_consistency.py` + `src/specify_cli/review/artifacts.py` (gate/model, verify honored), with a small **documented out-of-map edit** to the `move-task --to approved` handler in `tasks.py` (~:1120-1138). New test.
- **Sequencing/depends-on**: **depends on IC-06** (both touch `tasks.py`; sequence to avoid co-edit collision). `tasks.py` is owned by IC-06's WP; IC-07's WP makes the small approval-handler edit as a recorded out-of-map change.
- **Risks**: meatier review-artifact-authority surface (explicit sibling #1817 under epic #2160). Keep scope to the approve-over-rejected persistence path; honor the existing #1924 override mechanism. Cite #2160.
