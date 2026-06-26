# Implementation Plan: Single-Authority Resolution Gates

**Branch**: `design/infra-logic-separation-2173` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/single-authority-resolution-gates-01KW1P0F/spec.md`
**Binding design**: ADR `architecture/3.x/adr/2026-06-26-1-single-authority-seam-and-call-site-gate.md` · investigation `docs/engineering_notes/2173-infra-logic-separation/00-SYNTHESIS.md`

## Summary

Phase 1 of #2173. Route the bypassing **write legs** of `mark_status`/`safe_commit` through the *existing* kind-aware resolution authority (unblocking #2154/#2155), and add **two architectural call-site gates** — sharing one Idiom-B machinery module, with two discriminators — that make a future bypass (an un-canonicalized handle reaching the topology-blind primitive; a kind-blind write where kind-aware is mandated) a CI failure, closing the #2164 class by construction. No new runtime abstraction — the kind-aware authority already exists; the work is *routing the write leg to it* and *gating the omission*. The Phase 2 `MissionResolver` DI port is explicitly out of scope.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing only — `typer`, `ruamel.yaml`, `pytest`, `mypy`. **No new dependencies** (bug-class closure + architectural-gate tests over existing modules).
**Storage**: N/A (filesystem mission-artifact paths; no datastore changes)
**Testing**: `pytest`; new architectural gates in `tests/architectural/` (fast tier, `<30 s` on full `src/`); a stub-driven convergence test (no live `kitty-specs/` fixtures)
**Target Platform**: the spec-kitty CLI (`src/specify_cli`), Linux/macOS/Windows CI
**Project Type**: single (Python CLI + its test suite)
**Performance Goals**: each new AST gate completes `<30 s` on the full `src/` tree (NFR-004)
**Constraints**: guard at the seam never the primitive (C-001, FR-011 recursion — merge-blocker); ambiguity → `MissionSelectorAmbiguous`, cold-miss fail-closed-loud (C-002 — merge-blocker); composite-keyed shrink-only allowlists (NFR-001/003); copy the existing Idiom-B machinery, no new gate mechanism (C-005)
**Scale/Scope**: ~34 `primary_feature_dir_for_mission` call sites to route-or-allowlist (only 2 canonicalize today); the `mark_status` write/commit intra-function split + the `safe_commit` `.worktrees/` guard; 2 gates; 2 domain-matched test-hygiene folds

## Charter Check

*GATE: must pass before Phase 0; re-checked after Phase 1.*

Charter mode: compact. No charter-principle conflict. The binding governance for this mission is **ADR 2026-06-26-1** (single-authority seam + call-site gate). Gates that must hold:
- **C-001 (FR-011 recursion fence)** — canonicalization never folds into `primary_feature_dir_for_mission` (it probes via the primitive at `_read_path_resolver.py:454`). PASS-by-design: all new logic lives at the seam.
- **C-002 (no silent fallback)** — every patched seam propagates `MissionSelectorAmbiguous`; cold-miss fails closed-loud. PASS-by-design.
- **C-005 (unification not parity)** — gates copy the existing Idiom-B machinery; no parallel mechanism. PASS-by-design.
- **Terminology Canon** — "Mission" not "feature"; no "ceremony". Verified in prose.

## Project Structure

### Documentation (this mission)

```
kitty-specs/single-authority-resolution-gates-01KW1P0F/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (the resolution-boundary entities)
├── quickstart.md        # Phase 1 output (the SC reproductions)
├── contracts/           # Phase 1 output (the gate + seam contracts)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── cli/commands/agent/tasks.py        # mark_status write leg (:1807), commit (:1905), move_task validation (:660)  [IC-04]
├── ...commit_helpers.py               # safe_commit SafeCommitPathPolicyError (.worktrees/ guard, :298-320)          [IC-04]
├── missions/_read_path_resolver.py    # primary_feature_dir_for_mission (TBYD, :1212), _canonicalize_primary_read_handle (:1244)
├── runtime/next/_internal_runtime/runtime_bridge.py   # latent bare-handle sites (:98/114/139/177)                   [IC-02]
├── events/decision_log.py             # :103 un-canonicalized slug                                                   [IC-02]
└── (the ~34 primary_feature_dir_for_mission call sites: core/paths, core/git_ops, merge/*, implement.py, mission_runtime/resolution.py, …)  [IC-02]

tests/architectural/
├── surface_resolution_audit/audit.py  # the Idiom-B AST machinery to extend                                          [IC-01]
├── test_resolution_authority_gates.py # NEW — the shared gate module, two discriminators                             [IC-01/02/03]
└── test_no_tmp_paths_in_tests.py       # NEW — the /tmp ratchet (FR-007)                                              [IC-06]

tests/missions/test_*_convergence.py    # NEW — read≡write seam convergence (FR-006)                                  [IC-05]
tests/contract/                          # marker co-tag on mission-owned contract files (FR-008)                      [IC-06]
```

**Structure Decision**: Single Python project. Changes are surgical edits to the existing `tasks.py`/`commit_helpers.py` write paths, a routing/allowlist sweep across the existing `primary_feature_dir_for_mission` call sites, and new architectural-gate + convergence tests modeled on the existing `surface_resolution_audit/` machinery. No new packages or runtime abstractions.

## Complexity Tracking

| Decision | Why Needed | Simpler Alternative Rejected Because |
|----------|------------|--------------------------------------|
| Two discriminators sharing one gate module | The canonicalizer boundary (un-canonicalized handle → blind primitive) and the coord-authority boundary (kind-blind write) are structurally different AST predicates and cannot be one scan | One predicate cannot catch both; two separate modules would duplicate the composite-key/self-test/floor machinery |
| Scan-by-name discriminator (not raw-join) | `primary_feature_dir_for_mission` composes `KITTY_SPECS_DIR` *internally* and is auto-blessed; the raw-join scanner is structurally blind to a bare handle reaching it | A raw-join scan (Idiom-B's first discriminator) misses the entire #2164 class — this is the precise blind-spot the second discriminator exists for |

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Shared gate machinery (Idiom-B copy)

- **Purpose**: One reusable AST-gate module providing the composite-keyed allowlist `(enclosing_qualname, token_line)`, the self-mutation test (inject→FAIL→revert→PASS), the anti-vacuous discovered-row floor, and the shrink-only staleness twin-guard — copied/adapted from `tests/architectural/surface_resolution_audit/audit.py` + `test_single_mission_surface_resolver.py`. The foundation both discriminators consume.
- **Relevant requirements**: FR-003, FR-004 (mechanism); NFR-001, NFR-002, NFR-003, NFR-004; C-005.
- **Affected surfaces**: `tests/architectural/surface_resolution_audit/`, new `tests/architectural/test_resolution_authority_gates.py`.
- **Sequencing/depends-on**: none (foundation).
- **Risks**: composite-key drift management; keeping it a copy-adapt (C-005) not a reinvention; the floor must be calibrated so the gate is non-vacuous.

### IC-02 — Canonicalizer discriminator + seam sweep + allowlist

- **Purpose**: The **scan-by-name** discriminator that flags an un-canonicalized handle reaching `primary_feature_dir_for_mission`; plus the sweep of the ~34 bare-handle call sites — each routed through `_canonicalize_primary_read_handle` OR allowlisted with a recorded rationale (incl. the latent `runtime_bridge.py:98/114/139/177`, `decision_log.py:103`). Closes the #2164 class by construction.
- **Relevant requirements**: FR-004, FR-005; C-001, C-002.
- **Affected surfaces**: `missions/_read_path_resolver.py` callers; `runtime_bridge.py`; `events/decision_log.py`; `core/paths.py`, `core/git_ops.py`, `merge/*`, `implement.py`, `mission_runtime/resolution.py`, `cli/commands/agent/tasks.py`/`mission_type.py`; the gate allowlist.
- **Sequencing/depends-on**: IC-01.
- **Risks**: the TBYD auto-bless blind-spot (must scan by name); FR-011 recursion (route at the caller/seam, never the primitive); some sites legitimately hold a pre-resolved `feature_dir.name` and must be allowlisted, not re-canonicalized (avoid double-fold); ambiguity propagation (C-002).

### IC-03 — Coord-authority discriminator

- **Purpose**: The discriminator that flags a mission-artifact **write** using the kind-blind `resolve_feature_dir_for_mission` where the kind-aware authority is mandated; with its sanctioned allowlist.
- **Relevant requirements**: FR-003.
- **Affected surfaces**: the new gate module (shared with IC-01); the coord-authority write sites (`tasks.py`, status write paths).
- **Sequencing/depends-on**: IC-01; coordinates with IC-04 (IC-04's routing changes which sites are sanctioned).
- **Risks**: distinguishing a mandated kind-aware write from a legitimate kind-blind read/probe; allowlist precision.

### IC-04 — Coord-authority write-path fix (#2154 + #2155, co-land)

- **Purpose**: Route `mark_status`'s write leg (`tasks.py:1807`) through the same kind-aware authority its commit (`:1905`) and `move_task` validation (`:660`) use (#2154, FR-001); AND make `safe_commit`'s `.worktrees/` blanket-refusal (`commit_helpers.py:298-320`) surface-aware so coord-owned status writes commit (#2155, FR-002). **These co-land** — fixing the routing alone leaves commits blocked.
- **Relevant requirements**: FR-001, FR-002; C-002.
- **Affected surfaces**: `cli/commands/agent/tasks.py`, `...commit_helpers.py`.
- **Sequencing/depends-on**: none for the runtime fix (IC-03's gate then ratchets it).
- **Risks**: the intra-function write/commit split (easy to fix one leg and miss the other); the #2155 guard-conflict must be made *surface-aware*, not simply relaxed (must still refuse genuinely-wrong-surface writes); no silent fallback.

### IC-05 — Convergence test

- **Purpose**: A parametrized, stub-driven test asserting read-seam dir == every write/placement-seam dir for every handle form (full slug, `<slug>-<mid8>`, bare mid8, ULID, numeric), with no live `kitty-specs/` fixtures.
- **Relevant requirements**: FR-006.
- **Affected surfaces**: `tests/missions/` (new convergence test).
- **Sequencing/depends-on**: IC-02 (the routing must be in place to converge).
- **Risks**: stubbing the resolver behavior faithfully (the P1–P5 cascade) without an FS fixture; covering the ambiguity-raises and cold-miss cases.

### IC-06 — Test-hygiene folds (domain-matched)

- **Purpose**: FR-007 — a `/tmp`-literal-in-tests ratchet using IC-01's pattern (partial close of #1842); FR-008 — a CI-selected co-marker on the mission-owned `contract` test files so they run (partial close of #2034).
- **Relevant requirements**: FR-007, FR-008.
- **Affected surfaces**: new `tests/architectural/test_no_tmp_paths_in_tests.py`; markers on `tests/contract/test_mark_status_input_shapes.py`, `tests/git_ops/test_mark_status_pipe_table.py`.
- **Sequencing/depends-on**: IC-01 (for the /tmp ratchet pattern); the marker co-tag is independent.
- **Risks**: scope discipline — the /tmp ratchet only (not the #1842 litter sweep); the marker co-tag on mission-owned files only (not the `ci-quality.yml` matrix).
