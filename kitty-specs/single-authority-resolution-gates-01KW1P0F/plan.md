# Implementation Plan: Single-Authority Resolution Gates

**Branch**: `design/infra-logic-separation-2173` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/single-authority-resolution-gates-01KW1P0F/spec.md`
**Binding design**: ADR `architecture/3.x/adr/2026-06-26-1-single-authority-seam-and-call-site-gate.md` · investigation `docs/engineering_notes/2173-infra-logic-separation/00-SYNTHESIS.md`

> **Revision note (post-plan squad + residual hunt, 2026-06-26):** IC-02 split a/b/c (alphonso sizing); IC-04 re-scoped — #2155 is a 2-site caller fix (`tasks.py:1555` + `implement.py:1311`) via the coordination transaction, the guard is unchanged (residual hunt + #1887); factual anchors corrected; lane plan added (A serialized on `tasks.py`, B parallel).

## Summary

Phase 1 of #2173. Route the bypassing **write paths** through the *existing* kind-aware resolution authority — `mark_status`'s write leg (#2154) and the two `move_task`/`implement` mixed-partition commit bundles (#2155) — and add **two architectural call-site gates** (one machinery module, two discriminators) that make a future bypass a CI failure, closing the #2164 class by construction. No new runtime abstraction and **no guard mutation**: the kind-aware authority and the `safe_commit` guard both already exist and are sound; the work is *routing the writes to the right surface* and *gating the omission*. Phase 2's `MissionResolver` DI port is out of scope.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing only — `typer`, `ruamel.yaml`, `pytest`, `mypy`. **No new dependencies**.
**Storage**: N/A (filesystem mission-artifact paths; no datastore changes)
**Testing**: `pytest`; new architectural gates in `tests/architectural/` (fast tier, `<30 s` on full `src/`); a stub-driven convergence test (no live `kitty-specs/` fixtures); a coord-topology integration test for #2155
**Target Platform**: the spec-kitty CLI (`src/specify_cli`), Linux/macOS/Windows CI
**Project Type**: single (Python CLI + its test suite)
**Performance Goals**: each new AST gate completes `<30 s` on the full `src/` tree (NFR-004)
**Constraints**: canonicalizer guard at the seam never the primitive (C-001, FR-011 — merge-blocker); `safe_commit` guard unchanged (C-006 — merge-blocker); ambiguity → `MissionSelectorAmbiguous`, cold-miss fail-closed-loud (C-002 — merge-blocker); composite-keyed shrink-only allowlists with concrete floors (NFR-001/002/003); reuse the Idiom-B *shape*, composite-key + def-use predicate are net-new (C-005)
**Scale/Scope**: **38** `primary_feature_dir_for_mission` call sites (only ~9–11 canonical today — the seam-internal sites); the `mark_status` write leg + the two mixed-bundle callers; `resolve_feature_dir_for_mission` has a *separate* ~58-caller surface (only its write subset is in IC-03 scope); 2 gates; 2 domain-matched test-hygiene folds

## Charter Check

*GATE: must pass before Phase 0; re-checked after Phase 1.*

Charter mode: compact. No charter-principle conflict. Binding governance: **ADR 2026-06-26-1**. Gates that must hold:
- **C-001 (FR-011 recursion fence)** — canonicalization never folds into `primary_feature_dir_for_mission` (the fold *probes via* the primitive at `_read_path_resolver.py:454`; live-confirmed the primitive body calls no canonicalizer). PASS-by-design; regression-pinned.
- **C-002 (no silent fallback)** — every patched seam propagates `MissionSelectorAmbiguous`; cold-miss fails closed-loud. PASS-by-design.
- **C-006 (guard unchanged)** — the `safe_commit` `worktree_root`-foreignness discriminator is the #1887 backstop; not modified. PASS-by-design.
- **C-005 (unification not parity)** — reuse the Idiom-B shape; composite-key + def-use are net-new extensions, no parallel mechanism. PASS-by-design.
- **Terminology Canon** — "Mission" not "feature"; no "ceremony". Verified.

## Project Structure

### Documentation (this mission)

```
kitty-specs/single-authority-resolution-gates-01KW1P0F/
├── plan.md  research.md  data-model.md  quickstart.md  contracts/   # Phase 0/1
└── tasks.md  tasks/                                                  # Phase 2 (/spec-kitty.tasks)
```

### Source Code (repository root) — corrected anchors

```
src/specify_cli/
├── cli/commands/agent/tasks.py        # mark_status write (:1807) / commit (:1906) / move_task validation (:658)  [IC-04a]
│                                       # move_task mixed-bundle auto-commit (:1555)                                [IC-04b]
├── cli/commands/implement.py          # claim mixed-bundle auto-commit (:1311)                                    [IC-04b]
├── agent/workflow.py                  # _commit_workflow_change — the BookkeepingTransaction MODEL to copy        [IC-04b ref]
├── git/commit_helpers.py              # safe_commit guard (:983-991) — READ-ONLY, NOT modified (C-006)
├── missions/_read_path_resolver.py    # primary_feature_dir_for_mission (TBYD, :1212); _canonicalize_primary_read_handle (:1244, probes :454)
├── runtime/next/runtime_bridge.py     # latent bare-handle sites (:98, :177 — corrected path/lines)              [IC-02c]
├── decisions/emit.py, widen/state.py  # legitimate coord-owned writes that bypass commit_for_mission (allowlist) [IC-03]
└── (the 38 primary_feature_dir call sites: core/paths, core/git_ops, merge/*, implement.py, status/aggregate.py, mission_runtime/resolution.py, mission_type.py, …)  [IC-02b/c]

tests/architectural/
├── surface_resolution_audit/audit.py      # Idiom-B shape to extend (NOTE: keys on raw rel_path:line — composite-key is NEW)  [IC-01]
├── test_resolution_authority_gates.py      # NEW — shared module, two discriminators                              [IC-01/02a/03]
└── test_no_tmp_paths_in_tests.py            # NEW — frozen-baseline /tmp ratchet (FR-007)                          [IC-06]

tests/missions/test_*_convergence.py         # NEW — read≡write convergence, stub-driven + negative control (FR-006) [IC-05]
tests/<coord-integration>                     # NEW — #2155 coord-topology repro (no swallowed error)               [IC-04b]
```

**Structure Decision**: Single Python project. Surgical edits to `tasks.py`/`implement.py` write paths (routing, mirroring `workflow.py`'s coordination transaction), a routing/allowlist sweep across the 38 `primary_feature_dir_for_mission` sites, and new architectural-gate + convergence + coord-integration tests. The `safe_commit` guard is **read-only**. No new packages or runtime abstractions.

## Complexity Tracking

| Decision | Why Needed | Simpler Alternative Rejected Because |
|----------|------------|--------------------------------------|
| Two discriminators sharing one gate module | The canonicalizer boundary and the coord-authority boundary are structurally different AST predicates | One predicate cannot catch both; two modules duplicate the machinery |
| Scan-by-name + **def-use provenance** discriminator | The primitive composes the join internally (raw-join scan is blind); and a name-substring check is itself fakeable — the gate must prove the arg came from the fold *in this function* | Raw-join scan misses the #2164 class; name-matching auto-passes ~5 sites and lets mass-allowlisting pass vacuously |
| Composite-key `(qualname, token_line)` allowlist as **net-new** code | NFR-001 needs line-drift resilience; neither precedent implements it (frozenset of module paths / raw `rel_path:line`) | Reusing the raw-line key re-introduces the churn NFR-001 forbids |
| #2155 fix at the **two callers**, not the guard | Mutating the guard to be "kind-aware" can't distinguish a leak from a legit coord write (only `worktree_root`-relativity can) → re-opens #1887 | Guard mutation = #1887 regression for zero gain (residual hunt, 2 independent traces) |

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs. **Lane hint:** IC-02b/IC-03/IC-04a all edit `tasks.py` → one serialized **Lane A**; **Lane B** = {IC-02c non-`tasks.py` sweep, IC-05, IC-06} parallel; IC-01 is the shared foundation both lanes consume first.

### IC-01 — Shared gate machinery (Idiom-B shape + net-new composite-key)

- **Purpose**: One reusable AST-gate module: the **net-new** composite-keyed allowlist `(enclosing_qualname, token_line)`, the self-mutation test (inject→FAIL→revert→PASS, injection at a site distinct from any IC-04 fix), the **concrete-integer** discovered-row floor, and the shrink-only staleness twin-guard with a **pre-sweep baseline**. Reuses the scan/AST shape from `surface_resolution_audit/audit.py`; the composite key + the twin-guard are written fresh.
- **Relevant requirements**: FR-003/FR-004 (mechanism); NFR-001/002/003/004; C-005.
- **Affected surfaces**: `tests/architectural/surface_resolution_audit/`, new `test_resolution_authority_gates.py`.
- **Sequencing/depends-on**: none (foundation). **Lane A (shared).**
- **Risks**: the composite-key is net-new (don't under-budget as "copy"); floor must be the live census, never 0/1; the staleness twin-guard re-derives live keys.

### IC-02a — Canonicalizer discriminator (def-use)

- **Purpose**: The scan-by-name discriminator over `primary_feature_dir_for_mission` calls that judges "canonical" by **intra-function def-use provenance** (arg assigned from `_canonicalize_primary_read_handle` or a known-canonical `feature_dir.name` in the same function) — not name-substring. Floor ≥ 38.
- **Relevant requirements**: FR-004; NFR-002; C-001 (regression-pin `:454` as a sanctioned bare probe).
- **Affected surfaces**: the shared gate module.
- **Sequencing/depends-on**: IC-01. **Lane A (shared).**
- **Risks**: intra-function def-use is more than `audit.py`'s `first_arg.id` label; keyword-arg call forms (e.g. `tasks.py:1346` passes it as a kwarg) must be handled; `:454` must be allowlisted not "fixed" (else FR-011 recursion).

### IC-02b — Seam-module sweep (low-risk, mostly allowlist)

- **Purpose**: Route-or-allowlist the seam-internal / already-canonical sites (`_read_path_resolver.py`, `mission_type.py:1048`, `retrospective/writer.py`) — predominantly allowlist-with-rationale (already canonical). Touches `tasks.py`/`mission_type.py`.
- **Relevant requirements**: FR-005; NFR-003.
- **Sequencing/depends-on**: IC-02a. **Lane A** (touches `tasks.py`/`mission_type.py`).
- **Risks**: don't double-fold already-canonical sites; each allowlist entry names its already-canonical provenance.

### IC-02c — Consumer-site sweep (the judgment-heavy ~27)

- **Purpose**: Route the ~27 bare-`mission_slug` consumer sites (`merge/*`, `core/paths`, `core/git_ops`, `implement.py`, `status/aggregate.py`, `mission_runtime/resolution.py`, `runtime_bridge.py:98/:177`) through `_canonicalize_primary_read_handle` — **routing is the default**; allowlist only with an already-canonical rationale; **≥ the bare-handle census must be routed, not allowlisted**.
- **Relevant requirements**: FR-005; SC-004; C-002.
- **Affected surfaces**: the ~27 non-`tasks.py` consumer modules.
- **Sequencing/depends-on**: IC-02a. **Lane B** (disjoint from `tasks.py`).
- **Risks**: this is the WP-sized judgment workload (alphonso); ambiguity propagation; the mass-allowlist anti-pattern (routed-count floor guards it).

### IC-03 — Coord-authority discriminator

- **Purpose**: Flag a mission-artifact **write** using kind-blind `resolve_feature_dir_for_mission` where kind-aware is mandated; classify write-vs-read by an explicit documented predicate; **allowlist the legitimate coord-owned writes that bypass `commit_for_mission` by design** (`decisions/emit.py`, `widen/state.py`). Floor ≥ live write-candidate count. Produce a **read-vs-write classification artifact** separating the ~58 `resolve_feature_dir_for_mission` callers.
- **Relevant requirements**: FR-003; NFR-002.
- **Affected surfaces**: the shared gate module; the coord-authority write sites in `tasks.py`.
- **Sequencing/depends-on**: IC-01; coordinates with IC-04 (routing changes sanctioned sites). **Lane A** (touches `tasks.py`).
- **Risks**: write-vs-read is downstream data-flow (no name proxy) — the predicate must be explicit, not a one-entry tautology; must NOT false-positive on decision_log/widen (debbie).

### IC-04a — `mark_status` write-leg routing (#2154)

- **Purpose**: Route the write leg (`tasks.py:1807`) through the kind-aware authority its commit (`:1906`) and `move_task` validation (`:658`) use → primary. Intra-function. Acceptance asserts 3-leg convergence under coord AND flat topologies.
- **Relevant requirements**: FR-001; SC-001; C-002.
- **Affected surfaces**: `cli/commands/agent/tasks.py`.
- **Sequencing/depends-on**: none (runtime fix; IC-03 then ratchets). **Lane A.**
- **Risks**: the intra-function write/commit split (fix one leg, miss the other); fix only the coord leg and leave flat divergent (acceptance covers both topologies).

### IC-04b — Mixed-bundle routing (#2155, the residual)

- **Purpose**: Route the two mixed-partition auto-commit bundles — `move_task` (`tasks.py:1555`) and `implement`/claim (`implement.py:1311`) — so coord-owned status artifacts commit to coord (via the `BookkeepingTransaction` pattern `workflow.py:_commit_workflow_change` uses) and the WP file to primary, with **no swallowed `SafeCommitPathPolicyError`**. The guard is unchanged (C-006).
- **Relevant requirements**: FR-002; SC-002; C-006.
- **Affected surfaces**: `cli/commands/agent/tasks.py`, `cli/commands/implement.py` (model: `agent/workflow.py`).
- **Sequencing/depends-on**: none (runtime fix). **Lane A** (`tasks.py`) + `implement.py`.
- **Risks**: the swallow currently hides the failure — the fix must surface a genuine failure, not re-swallow; reachable only under coord-topology + unprotected branch (the integration test must set that up); do NOT touch the guard.

### IC-05 — Convergence test

- **Purpose**: Stub-driven read≡write/placement convergence for every handle form, with **distinguishable per-form stub outputs** (constant-return rejected), driving ambiguity-raise + cold-miss, plus a **red-first negative control** (a form divergent under pre-fix code).
- **Relevant requirements**: FR-006; SC-005.
- **Affected surfaces**: `tests/missions/` (new).
- **Sequencing/depends-on**: IC-02a/c (routing in place). **Lane B.**
- **Risks**: a tautological stub; missing the negative control; skipping the divergent cases.

### IC-06 — Test-hygiene folds (domain-matched)

- **Purpose**: FR-007 — frozen-baseline `/tmp` ratchet (baseline ~82, block new only, self-mutation proof); FR-008 — empirically re-derive #2034's actually-non-running set (`--collect-only` before/after diff) and co-tag only proven-excluded mission-owned files (the two originally-named files already run → likely satisfied-by-verification).
- **Relevant requirements**: FR-007, FR-008; SC-006.
- **Affected surfaces**: new `test_no_tmp_paths_in_tests.py`; (conditionally) markers on proven-excluded mission-owned test files.
- **Sequencing/depends-on**: IC-01 (for the ratchet pattern); the FR-008 verification is independent. **Lane B.**
- **Risks**: scope discipline (no #1842 sweep, no `ci-quality.yml` matrix); FR-008 must not add redundant markers to already-running files.

### IC-07 — Pre-condition verification + existing-gate reconciliation

- **Purpose**: (a) the C-003 one-step check that the #2161 read-leg fix is present on the base before building on it; (b) reconcile the **existing** surface-resolver gates' floors/allowlists after IC-04a/IC-02 move sites (the pre-existing `test_single_mission_surface_resolver.py` / `audit.py` scan the same files and may need their counts updated).
- **Relevant requirements**: C-003; NFR-002/003 (no existing gate left red by site moves).
- **Affected surfaces**: the existing `tests/architectural/` surface-resolver gates.
- **Sequencing/depends-on**: after IC-02/IC-04 land. **Lane A** (gate reconciliation tracks `tasks.py` edits).
- **Risks**: a site move silently breaking a pre-existing gate's floor; easy to miss in per-WP review (caught by the full `tests/architectural/` sweep pre-merge).
