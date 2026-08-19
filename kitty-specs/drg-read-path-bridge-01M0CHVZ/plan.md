# Implementation Plan: DRG Read-Path Bridge

**Branch**: `mission/drg-read-path-bridge-01M0CHVZ` | **Date**: 2026-08-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/drg-read-path-bridge-01M0CHVZ/spec.md`

**Branch contract**: Planning/base branch and merge target are both
`mission/drg-read-path-bridge-01M0CHVZ` (single_branch topology, freshly cut off
`upstream/main`). The completed mission lands on this branch, which is later
opened as a PR to `main` — never pushed to `origin/main` directly.

## Summary

An org pack can author `requires`/`suggests` dependency edges in its canonical
`drg/fragment.yaml` (the `OrgDRGFragment` shape from #3387). Those edges are read
**only** by the diagnostic three-layer merge (`doctor doctrine` / `charter list`
/ lint / status) and are **never** bridged into the graph that charter cascade
walks — `charter/_drg_helpers.py::load_validated_graph` folds only root-level
`*.graph.yaml` via `merge_layers`. So activating an artifact silently cascades
nothing for org-authored fragment dependencies. The companion validator
`_check_drg_root_graph_missing` globs `*.graph.yaml` and reasons about
`drg/ fragments` in a blanket claim that inverts the moment the runtime starts
reading fragments.

**Technical approach**: route the org layer through the **existing**
`doctrine/drg/merge.merge_three_layers(built_in, org_fragments, project)` from
inside `load_validated_graph` when a new `org_fragments` argument is supplied;
reuse its endpoint-resolution (`_resolve_edge_endpoint`) and cross-fragment
edge-identity/dedup (`_OrgEdgeCollector`) — no second canonicalisation path
(C-002). Runtime cascade callers populate `org_fragments` via
`charter.drg.load_org_drg(repo_root, strict=False)`; build-time callers pass
nothing and stay byte-identical (FR-003). Re-scope the D-005 graphless warning
so it fires only when a root ships **neither** a root graph **nor** a
`drg/fragment.yaml` (FR-004). Flip the pinning regression test (FR-005) and
reconcile the validator (FR-006) in the **same change** so `pack validate` and
the runtime never tell contradictory stories (C-001 / NFR-003).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic (DRG models), pyyaml (fragment parse), typer +
`typer.testing.CliRunner` (CLI integration tests) — all already in-tree; **no new
dependencies** (supply-chain review N/A).
**Storage**: N/A — this is a pure in-memory graph-merge read path. No persistent
schema, migration, or serialized-format change.
**Testing**: pytest. ATDD-first (C-011): the flipped `test_org_cascade_chain.py`
integration test is the executable red→green contract; unit coverage for the new
`load_validated_graph(org_fragments=…)` composition, the `load_org_drg(strict=…)`
branch, and the re-scoped validator finding.
**Target Platform**: cross-platform CLI (Linux/macOS/Windows).
**Project Type**: single project (`src/` + `tests/`).
**Performance Goals**: no regression; the fragment merge already runs on the
diagnostic path — the bridge adds one `merge_three_layers` call on the cascade
path, bounded by configured org-pack count (typically 0–2). CLI stays < 2 s.
**Constraints**:
- **Layer boundary (C-005)**: `src/charter/` must not import `src/specify_cli/`.
  The runtime caller (in `specify_cli`) resolves and supplies the fragments; the
  charter-layer bridge only accepts them as a parameter. Enforced by
  `tests/architectural/test_layer_rules.py` /
  `test_runtime_charter_doctrine_boundary.py`.
- **Zero new suppressions (C-005)**: new code passes `ruff` + `mypy --strict`
  with zero `# noqa` / `# type: ignore`.
- **Diagnostic path byte-identical (NFR-001)**: the four diagnostic callers of
  `merge_three_layers` (`lint.py`, `_status_collectors.py`, `_doctrine_collect.py`,
  `_profile_health_render.py`) are **not touched**. The bridge ADDS a consumer.
- **Atomic validator/runtime flip (C-001 / NFR-003)**: validator finding and
  runtime bridge land in one change; no intermediate commit where `pack validate`
  claims a fragment "will not be read" while the runtime reads it.
- **Single reviewed golden re-ledger (NFR-002)**: any cascade-reach delta from
  newly-visible fragment edges is captured in exactly one reviewed golden-count
  update, with a rationale.
**Scale/Scope**: ~5 source files touched + 1 test file flipped + focused unit
tests. Out of scope (C-004): cascade traversal completeness / relation-set /
kind-complete cascade (mission M5 / #2829). This mission only makes fragment
`requires`/`suggests` edges visible through the **existing** followed relations.

### Supply-Chain Security (planning gate)

No dependency is added, upgraded, or removed. The `supply_chain_security_check`
step is **N/A** for this mission; recorded here as examined-not-silent.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter (`.kittify/charter/charter.md`) is present. Relevant gates:

| Charter rule | Application to this mission | Status |
|--------------|-----------------------------|--------|
| **Single canonical authority** | Reuse `merge_three_layers` endpoint/dedup machinery; do NOT fork a second edge-canonicalisation path (C-002). The bridge is a new *consumer*, not a new *authority*. | ✅ Aligned |
| **Architectural alignment / layer boundary** | `charter` stays free of `specify_cli` imports; caller supplies fragments (C-005). | ✅ Aligned |
| **ATDD-first (C-011)** | Flipped `test_org_cascade_chain.py` fragment test is the red-first contract, committed before the bridge implementation. | ✅ Planned |
| **Canonical sources / terminology** | Domain object is "Mission"/DRG; no `feature*` aliases introduced. | ✅ Aligned |
| **Boy-Scout / smallest-viable-diff reconciliation** | Core diff bounded to the read-path seam + validator + test flip; opportunistic cleanup only inside touched files. | ✅ Planned |
| **`__all__` convention (C-007)** | Any new public symbol in `src/charter/` declares `__all__` and has a live caller. | ✅ Will honor |
| **Zero suppressions (C-005)** | ruff + mypy --strict clean, no new ignores. | ✅ Will honor |
| **Pre-existing failure reporting** | Known-P0 baseline reds are not this mission's to fix; if hit, file/annotate per policy. | ✅ Noted |

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this mission)

```
kitty-specs/drg-read-path-bridge-01M0CHVZ/
├── plan.md              # This file
├── research.md          # Phase 0 — design decisions (composition, validator, loader resilience)
├── data-model.md        # Phase 1 — DRG merge data flow + read-set model
├── quickstart.md        # Phase 1 — red-first repro (fragment-only pack cascades)
├── contracts/           # Phase 1 — load_validated_graph + validator finding contracts
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── charter/
│   ├── _drg_helpers.py          # BRIDGE: load_validated_graph gains org_fragments; D-005 warning re-scope (FR-001/003/004)
│   └── drg.py                   # load_org_drg gains strict= param for resilient per-pack fragment load (FR-001 support)
├── doctrine/
│   └── drg/merge.py             # REUSED unchanged: merge_three_layers, _resolve_edge_endpoint, _OrgEdgeCollector (C-002)
└── specify_cli/
    ├── cli/commands/charter/
    │   ├── activate.py          # thread org_fragments into the 2 cascade load sites (FR-001)
    │   └── deactivate.py        # thread org_fragments into the cascade load site (FR-001)
    ├── review/gate_bindings.py  # (candidate) thread org_fragments — additive consumer
    ├── mission_step_contracts/executor.py  # (candidate) thread org_fragments — additive consumer
    └── doctrine/pack_validator.py  # RECONCILE: _check_drg_root_graph_missing re-scope + re-message (FR-006)

tests/
├── specify_cli/cli/commands/charter/
│   └── test_org_cascade_chain.py  # FLIP TestGraphlessPackWithFragmentEdgeIsInvisibleToCascade (FR-005) + green-preservation of root-graph tests
├── charter/                       # unit: load_validated_graph composition + load_org_drg strict branch
└── specify_cli/doctrine/          # unit: re-scoped validator finding
```

**Structure Decision**: Single-project layout. The change is concentrated on the
charter-layer read-path seam (`_drg_helpers.py`), with a small resilient-loader
addition (`drg.py`), thin threading at the specify_cli cascade call sites, one
test flip, and the atomic validator reconciliation.

## Implementation Concern Map

Concerns for `/spec-kitty.tasks` to translate into work packages. Because C-001 /
NFR-003 require the validator finding and the runtime bridge to flip **atomically**
(no intermediate commit where they disagree), these concerns are **tightly
coupled and land together** on the single mission branch — they are *not* an
independent-parallel-lane decomposition.

1. **IC-1 — ATDD red-first contract (FR-005, C-011).** Flip
   `TestGraphlessPackWithFragmentEdgeIsInvisibleToCascade` to assert the
   `drg/fragment.yaml` `requires` edge **cascades** (`b-directive` activated,
   `Cascade-activated` in output) and that **no** graphless warning fires for a
   fragment-bearing pack. Committed RED first (fails on current main), before the
   bridge implementation. Rename the class/docstring away from
   "…IsInvisibleToCascade".
2. **IC-2 — Bridge (FR-001/002/003).** `load_validated_graph` accepts
   `org_fragments: list[OrgDRGFragment] | None`; when supplied, fold via
   `merge_three_layers(built_in=<built-in+root-graph merge>, org_fragments=…,
   project=…)`, reusing its endpoint/dedup machinery. Build-time callers
   (no `org_fragments`) stay byte-identical.
3. **IC-3 — Resilient fragment resolution (FR-001 support).** `load_org_drg`
   gains `strict: bool = True`; `strict=False` skips packs with no
   `drg/fragment.yaml` (so a root-graph-only or graphless pack degrades instead
   of raising `OrgPackMissingError`). Diagnostic callers keep `strict=True`
   default → NFR-001 unaffected.
4. **IC-4 — Warning re-scope (FR-004, C-003).** The D-005 branch in
   `load_validated_graph` fires only when a root ships **neither** a root-level
   `*.graph.yaml` **nor** a `drg/fragment.yaml`. Degrade posture preserved; only
   the trigger narrows.
5. **IC-5 — Thread cascade call sites (FR-001).** `activate.py` (×2),
   `deactivate.py` (×1) pass `org_fragments=load_org_drg(repo_root, strict=False)`
   alongside the `org_roots` they already resolve. `gate_bindings.py` and
   `executor.py` evaluated for the same threading (fold if low-risk & in-scope,
   else defer with rationale — see research.md D4).
6. **IC-6 — Validator reconciliation (FR-006, C-001, NFR-003).**
   `_check_drg_root_graph_missing` re-scoped + re-messaged so it never claims a
   `drg/fragment.yaml`-bearing pack's DRG "will not be read" once the runtime
   reads it. Lands in the SAME change as IC-2.
7. **IC-7 — Golden re-ledger + regression sweep (NFR-001/002).** Locate any
   golden/count assertions affected by newly-visible fragment edges; capture the
   delta in ONE reviewed update with rationale. Confirm the four diagnostic
   `merge_three_layers` callers and `doctor doctrine` / `charter list` output are
   byte-identical.

## Complexity Tracking

*No Constitution Check violations — table intentionally empty.*

## Parallel Work Analysis

**Not a parallel-lane mission.** single_branch topology; C-001 / NFR-003 force
the runtime bridge and validator reconciliation into one atomic change. Sequencing
is: **IC-1 (red)** → **IC-2 + IC-3 + IC-4 + IC-6 (green, atomic)** →
**IC-5 (threading, green)** → **IC-7 (re-ledger + sweep)**. A single implementer
owns the whole slice to preserve atomicity; the tasks phase may still cut it into
ordered WPs on one lane, but they merge as one coherent unit.
