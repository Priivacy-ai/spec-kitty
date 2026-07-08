# Implementation Plan: Read-Surface SSOT Completion & #1716 Closeout

**Branch**: `design/read-surface-ssot-closeout` | **Date**: 2026-07-08 | **Spec**: `kitty-specs/read-surface-ssot-closeout-01KWZV91/spec.md`
**Input**: Feature specification (spec v2, commit `ebc2660`, post pre-spec-squad + post-spec 3-lens squad)

## Summary

Complete the read-side SSOT strangle (read counterpart to the #2462 write-side placement lock) and close
epic #1716. Four threads: (A) route the remaining kind-blind `resolve_feature_dir_for_mission` reads onto the
`PlacementSeam.read_dir(kind)` authority + drain the `coord_authority` ratchet 7→2; (B) route the remaining
inline `meta.json` reads onto the canonical `load_meta` authority + establish a non-vacuous tightening ratchet;
(C) **close the #2404 wrong-kind-commit defect class at its seam** — make `commit_for_mission` per-file
partition-aware so coordination artifacts stop landing on the primary branch (fixing `spec_commit_cmd` and
`mission_finalize` by construction), then route `accept.py` through it and reconcile its dirty-detection
surface; (D) close #2088 (already fixed) and epic #1716. The technical spine is *extract → route → enforce*
behind ratchets, with the C-006 seam fix as the foundation of Thread C.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `mission_runtime` (`PlacementSeam.read_dir/write_target`, `resolve_action_context`, the `_PRIMARY_/_PLACEMENT_ARTIFACT_KINDS` partition, `kind_for_mission_file`) — all from PR #2462; `specify_cli.mission_metadata` (`load_meta`/`load_meta_strict`/`load_meta_or_empty`); `coordination/commit_router` (`commit_for_mission`); typer, ruamel.yaml
**Storage**: git (coord + primary branches / worktrees), `meta.json`, `status.events.jsonl`
**Testing**: pytest — red-first unit tests for new guards/routing (C-005); per-cluster characterization/regression for behaviour-preservation (NFR-001); two architectural ratchet gates (`coord_authority` shrink + new meta-read gate); coord-topology integration for #2404
**Target Platform**: Linux/macOS CLI
**Project Type**: single (CLI toolkit)
**Performance Goals**: N/A — correctness/SSOT mission
**Constraints**: `ruff` + `mypy` zero issues; per-function complexity ≤15; behaviour-preserving routing (no surface/contract change); **no kind→partition change** (C-002); **depends on PR #2462 merging** for Threads A/C (C-003, rebase-before-implement); `transaction.py:751-771` untouched (C-004); red-first (C-005); #2404 class closed at the seam not per-caller (C-006)
**Scale/Scope**: ~36 `resolve_feature_dir_for_mission`/`_slug` production sites + ~50 inline `meta.json` reads across ~75 files; **15–17 WPs**; 9 files touched by both Thread A and Thread B (cross-thread linearization)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| **Single canonical authority** | **Central to this mission.** Every routed read goes through exactly one authority (`read_dir` / `load_meta`); the #2404 fix consolidates write-routing *at the seam* (C-006) rather than spreading per-caller patches. PASS — this mission strengthens the principle. Honesty caveat recorded (C-001): the gate covers the gated resolver, not every direct primitive call. |
| **Architectural alignment** | Extends the existing SSOT surfaces (seam, `load_meta`, `commit_for_mission`); introduces no parallel authority. C-002 forbids the partition flip (verified sound). PASS. |
| **DDD + tiered rigour** | Core coordination/placement surfaces get the higher rigour (red-first, characterization, ratchets); doc/tracker closeout is glue-tier. PASS. |
| **ATDD-first / red-first** | C-005 mandates red-first for every new guard/routing/fix (FR-004, FR-007, FR-008). PASS. |
| **Terminology adherence** | Mission canon; no `feature*` reintroduction; run the terminology guard on any prose/doctrine touch. PASS. |

**No charter violations.** Complexity Tracking not required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/read-surface-ssot-closeout-01KWZV91/
├── plan.md              # This file
├── research.md          # Phase 0 — squad decisions D1..Dn + the C-007 census/children gate results
├── data-model.md        # Phase 1 — the partition-aware commit batch + the meta-read ratchet entities
├── quickstart.md        # Phase 1 — validation walkthrough (coord-topology accept round-trip)
├── contracts/
│   ├── partition-aware-commit-seam.md   # commit_for_mission per-file partition contract (C-006)
│   └── meta-read-ratchet.md             # the non-vacuous ratchet contract (FR-006/NFR-002)
├── traces/              # Mission tracer files (seeded at planning; APPEND during implement)
│   ├── design-decisions.md   # per-site kind decisions, read/write divergences, routing rationale
│   ├── approach.md           # approach shifts (WP re-slices, re-scopes)
│   └── tooling-friction.md   # gate/command friction in-the-moment (feeds #2095)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

**Mission tracer files (binding on every WP).** The three `traces/*.md` files are seeded (this
mission seeds at planning, not late) and pre-loaded with the settled design decisions + the
#2462-landing findings. `/spec-kitty.tasks` MUST add to every WP prompt an explicit instruction:
*"append to the relevant `kitty-specs/read-surface-ssot-closeout-01KWZV91/traces/*.md` tracer the
moment you make a per-site kind decision (→ design-decisions), shift approach (→ approach), or hit
gate/tooling friction (→ tooling-friction) — in-the-moment, 1–3 sentences, never reconstruct at
close."* At mission close the tracers are assessed into the retrospective and any friction is filed
(`mission-tracer-files` procedure).

### Source Code (repository root)

```
src/
├── mission_runtime/
│   ├── resolution.py            # PlacementSeam.read_dir/write_target (consumed, from #2462)
│   └── artifacts.py             # _PRIMARY_/_PLACEMENT_ARTIFACT_KINDS partition + kind_for_mission_file (read-only; C-002)
├── specify_cli/
│   ├── mission_metadata.py      # load_meta authority (consumed; internals NOT routed)
│   ├── coordination/
│   │   ├── commit_router.py     # IC-01: make commit_for_mission per-file partition-aware (C-006)
│   │   └── transaction.py       # IC-05: route meta reads OUTSIDE 751-771 (C-004 guard)
│   ├── cli/commands/
│   │   ├── accept.py            # IC-02: route residual commit + reconcile dirty-detection surface (M2)
│   │   ├── spec_commit_cmd.py   # fixed-by-construction via IC-01
│   │   ├── implement.py         # IC-04 read routing + FR-004 area (cross-thread collision w/ IC-05)
│   │   ├── agent/
│   │   │   ├── workflow.py           # IC-04: @2710 read→read_dir, @2747 write→write_target
│   │   │   ├── mission_finalize.py   # fixed-by-construction via IC-01 (the 3rd #2404 site)
│   │   │   └── agent_tasks_ports.py  # IC-04 FR-003: feature_write_dir reclassify-as-write
│   │   └── _identity_audit.py   # IC-04/IC-05 collision file
│   ├── orchestrator_api/commands.py  # IC-04: FR-004 fail-closed @1451 (collision file)
│   ├── acceptance/__init__.py        # IC-02: write_acceptance_matrix surface (M2)
│   ├── lanes/recovery.py             # IC-04 FR-003 status-write reclassify (NEVER route); + IC-05 collision
│   ├── context/resolver.py, decisions/service.py, doctrine_synthesizer/apply.py,
│   │   missions/plan/{plan_interview,specify_interview}.py   # IC-04/IC-05 collision files
│   └── runtime/next/ ...             # IC-05: shared-package-boundary-gated meta reads
tests/
├── architectural/
│   ├── test_resolution_authority_gates.py + resolution_gate_allowlist.yaml  # IC-04: coord_authority 7→2
│   └── <new> test_inline_meta_read_gate.py                                  # IC-06: the new ratchet
├── integration/  # IC-03: coord-topology #2404 round-trip
└── unit/         # red-first per FR
```

**Structure Decision**: Single-project CLI toolkit. All changes are routing/consolidation on existing
surfaces plus two architectural gates; no new top-level packages.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are architectural areas, not WPs. `/spec-kitty.tasks` translates them into 15–17 executable WPs.
> **Cross-thread linearization (binding):** IC-04 (feature_dir) and IC-05 (meta) both touch the 9 files named
> in spec.md's "Cross-Thread Linearization" section — `/tasks` MUST co-own each such file's A-edit and B-edit
> in one WP, or sequence them same-lane (the pattern #2088's dependency-aware overlap validator enables).
> Never split a collision file across two lanes with overlapping `owned_files`.
> **Re-grounding correction (inventory lens, 2026-07-08): 8 of the 9 named files are genuine A+B
> collisions; `orchestrator_api/commands.py` is NOT** — on the merged tree it carries only the
> Thread-A construct (the FR-004 fail-closed fallback @~1452) and zero inline-meta reads (its one
> `json.loads` parses `--evidence-json`). It joins the FR-004-only IC-04 set, not the strict
> collision set. This LOOSENS the constraint (the WP owning it for FR-004 need not co-own a B-edit).
> The other 8 are confirmed genuine — co-own/same-lane binding.

> **Post-#2462-landing deltas (2026-07-08, from the merged-PR impact review — fold at `/tasks`):**
> #2462 landed exactly as this plan assumed (seam `read_dir` present, allowlist floor = 7,
> drain-to-2 valid, **no ADR redirect, no kind flipped** — C-001/C-002/C-006 all reinforced). No
> spec revisit. Apply these plan edits before `/tasks`:
> 1. **IC-04 coord_authority census is UNCHANGED — re-verified green on the rebased base:**
>    `scan_coord_authority_call_sites(src) = 32 live / 7 allowlisted / 25 to-route`, gate 45/45 green,
>    drain 7→2 valid. **Do NOT subtract sites.** (The PR-review flagged two "pre-routed" READ sites —
>    `acceptance/__init__.py::_planning_read_dir`, `orchestrator_api/commands.py::_planning_read_dir` —
>    but those are the SEPARATE `resolve_planning_read_dir` helper class, NOT the `resolve_feature_dir_for_mission`
>    census Thread A's 25-count targets. #2462 converted those two helpers' *internals* to call
>    `placement_seam(...).read_dir(...)`; that is a refinement within the already-canonical read-delegate
>    class and does not reduce the 25. Conflating the two classes would under-count Thread A.)
> 2. **Census counts by TOKEN, not line.** The landed `resolution_gate_allowlist.yaml` pins the
>    `workflow.py` review write sites at STALE locators (2633/2670, token-authoritative only). The
>    C-007 re-run and every WP scan MUST match constructs/tokens, not frozen line numbers.
> 3. **IC-01 rename.** `_planning_commit_worktree` was renamed → `_resolve_commit_worktree_for_kind`
>    (backward alias kept). Refer to the new name.
> 4. **Thread A (#2453) folds ONE reviewer item** the #2462 reviewer assigned to it: paula's
>    fail-open-fallback finding (Thread A / FR-004, red-first). Renata's `contextlib.suppress` NOTE
>    at `mission_creation.py:469` was VERIFIED OUT of IC-04's footprint (it wraps a create-time
>    *write* `_commit_feature_file`; the file has 0 `resolve_feature_dir_for_mission` sites) —
>    per DIRECTIVE_025 it is NOT folded; deferred as an explicitly-recorded campsite NOTE
>    (create-time commit-hygiene, out of the read-side routing domain).
> 5. **Thread B (#2100) inherits a BREAKING base:** legacy meta-less missions now hard-fail
>    (#2091 guard). Routing inline reads onto `load_meta*` must NOT re-add a fallback-on-missing-meta
>    path. Full legacy-bridge removal is **#2463** — a separate mission, do NOT fold.
> 6. **CI caveat #2475:** the arch marker gate is vacuous under `.worktrees/`; verify this mission's
>    own ratchet tests from the primary checkout, not a green marker run inside an execution worktree.

### IC-01 — Partition-aware commit seam (#2404 class-closure)

- **Purpose**: Make `commit_for_mission` classify each file in a batch by partition (`kind_for_mission_file`) and commit each partition-group to its own ref — or guard-reject a mixed-partition batch — so coordination artifacts never land on the primary branch. This is the root fix; it closes `spec_commit_cmd.py` (`kind=SPEC`) and `mission_finalize.py:1320` (`kind=TASKS_INDEX`) by construction.
- **Relevant requirements**: FR-007; C-006 (Directive-043); C-002.
- **Affected surfaces**: `coordination/commit_router.py` (`commit_for_mission`, `resolve_placement_only` call at :152 — line will have drifted post-#2462, match by token; note `_planning_commit_worktree` was renamed by #2462 → `_resolve_commit_worktree_for_kind`, alias kept); read-only against `mission_runtime.artifacts` partition.
- **Sequencing/depends-on**: needs #2462's partition-aware commit context merged (C-003). Foundation for IC-02/IC-03.
- **Risks**: batch materialize-then-retry semantics per partition group; keep single-partition batches on the fast path; red-first proving a mixed batch currently misroutes.

### IC-02 — Accept-path residual routing + dirty-surface reconciliation

- **Purpose**: Route `accept.py::_commit_residual_acceptance_artifacts` through the (now partition-aware) seam instead of raw `git commit`, and reconcile its dirty-detection surface — detect coord-worktree dirt where `write_acceptance_matrix` writes (coord `feature_dir`), not only primary `git status` (M2).
- **Relevant requirements**: FR-008.
- **Affected surfaces**: `cli/commands/accept.py` (`_commit_residual_acceptance_artifacts`, `_spec_artifact_dirty_paths`), `acceptance/__init__.py` (`write_acceptance_matrix` surface).
- **Sequencing/depends-on**: IC-01.
- **Risks**: the primary-vs-coord dirty-detection surface (the subtle M2 gap); do not regress PRIMARY-kind residuals.

### IC-03 — #2404 coord-topology characterization

- **Purpose**: End-to-end regression that `acceptance-matrix.json` written via `spec-commit`, `finalize`, AND `accept` lands on coord and is read back by `accept` — the class stays closed.
- **Relevant requirements**: FR-009; SC-003.
- **Affected surfaces**: `tests/integration/` (coord-topology fixture — **build on #2462's landed `tests/integration/test_placement_partition_golden_path.py` rather than duplicate it**; sequencing lens reuse note).
- **Sequencing/depends-on**: IC-01, IC-02.
- **Risks**: fixture realism (coord topology + a valid mid8 — see the #2462 CI fixture lesson; the landed `tests/lane_test_utils.py` now mints production-shaped mission_id/mid8, reuse it).

### IC-04 — feature_dir read routing + coord_authority drain (#2453)

- **Purpose**: Route the 25 READ `resolve_feature_dir_for_mission` sites + 4 `_slug` sites onto `read_dir(kind)`; drain `coord_authority` 7→2; reclassify the two status-write false-negatives; fix the FR-004 fail-closed fallback. **Census re-verified UNCHANGED post-#2462 (32 live / 7 allowlisted / 25 to-route, gate green) — do NOT subtract; the two `_planning_read_dir` helpers #2462 touched are the separate `resolve_planning_read_dir` class, not this census.** Also folds ONE #2462-reviewer item assigned to #2453: paula's fail-open-fallback finding (FR-004, red-first). (Renata's `contextlib.suppress`@`mission_creation.py:469` verified OUT of footprint — deferred NOTE, not folded.) Route via `read_dir(kind)` per-kind (NOT one delegate for all kinds — `RETROSPECTIVE` routes to `resolve_retrospective_home`, H-1).
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004.
- **Affected surfaces**: the 25+4 read sites (~30 files); `workflow.py` (@2710 read, @2747 write), `implement.py`, `orchestrator_api/commands.py` (@1451), `agent_tasks_ports.py`, `lanes/recovery.py`; `tests/architectural/test_resolution_authority_gates.py` + `resolution_gate_allowlist.yaml`.
- **Sequencing/depends-on**: #2462 seam (C-003). **Internal ordering: FR-003 (predicate-widen) precedes FR-002 (floor re-pin)** — the predicate change moves the live write count (C-007). Cross-thread collision with IC-05 on 9 files.
- **Risks**: per-site read/write adjudication (never trust the gate's function-level `is_write`); `recovery.py:755` + `agent_tasks_ports.py:322` are reclassify-as-write, **never route**; the 9-file collision with IC-05.

### IC-05 — inline meta.json read routing (#2100)

- **Purpose**: Route the ~50 inline `json.loads(<meta_path>)` reads onto `load_meta`/`load_meta_strict`/`load_meta_or_empty` with the matching `allow_missing`/`on_malformed` contract.
- **Relevant requirements**: FR-005.
- **Affected surfaces**: census-directional ~50–63 sites across ~43 files (inventory lens re-derived 63 sites / 43 files incl. `json.load(f)` variants; the plan's own 50-vs-60 figures predate this and disagree — treat all three as directional and let the IC-06 scanner be the authoritative tie-breaker; do NOT gate WP sizing precision on the prose figure). Spread: status/*, coordination/transaction.py [outside 751-771], retrospective/*, cli/commands/*, runtime/next/* [boundary-gated], missions/plan/*, etc.
- **Sequencing/depends-on**: independent of #2462 EXCEPT the 9 collision files co-owned with IC-04. Precedes IC-06 (drain before ratchet).
- **Risks**: `transaction.py` half-in/half-out (C-004 byte-unchanged guard on 751-771); `runtime/next` shared-package boundary; `mission_metadata.py` internals + `task_utils` adapter excluded; per-site contract correctness (strict vs allow-missing vs empty).

### IC-06 — meta-read tightening ratchet (establish, non-vacuous)

- **Purpose**: Stand up the first architectural gate for inline meta reads so the drained class cannot regrow.
- **Relevant requirements**: FR-006, NFR-002.
- **Affected surfaces**: `tests/architectural/` (new gate mirroring `test_resolution_authority_gates.py`: scanner + integer floor + margin + **routed-count floor** + composite-key allow-list with stale-entry detection).
- **Sequencing/depends-on**: IC-05 (routing drains the count before the floor is pinned). Dedicated concern (not folded into routing) per the vacuity finding.
- **Risks**: vacuity — the allow-list must not swallow the census; each deferred `m_0_13_*` site is an allow-list entry with rationale + a filed follow-up issue.

### IC-07 — #1716 / #2088 closeout + tracker

- **Purpose**: Verify `69dd1fa46` on base; close #2088 early; close epic #1716 gated on #2462 merged + a children-enumeration check.
- **Relevant requirements**: FR-010; SC-004.
- **Affected surfaces**: tracker (issue-matrix, GitHub); no code (verify-only for #2088).
- **Sequencing/depends-on**: #2088-close independent; epic-#1716-close gated on #2462 merged to `upstream/main`.
- **Risks**: closing-keyword parsing discipline; confirm #1716 has no open children beyond #2088/#2100 before closing.
