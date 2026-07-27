# Implementation Plan: Coord-Authority Gate Hardening

**Branch**: `feat/coord-authority-gate-hardening` | **Date**: 2026-06-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/coord-authority-gate-hardening-01KW4T2F/spec.md`

**Mission**: coord-authority-gate-hardening-01KW4T2F | **Epic**: #2160 (umbrella, stays open) | **Closes**: #2197, #2198, #2199, #2214

The design is SETTLED: a post-spec adversarial squad (alphonso/renata/debbie/paula, 2026-06-27) resolved the FR set before planning. This plan carries that design faithfully; it does not re-open the FRs.

## Summary

The #2160 coord-topology authority unification is functionally complete, but the #2212 pre-merge squad found the **static call-shape gate** (`callshape_violations`) is intra-procedural: it flags a coord-aware dir bound to a kind-read *within the same function* but is blind to a coord-aware dir bound **one hop up** and passed in as a parameter or attribute. Two real residuals escaped statically (caught only behaviorally), and a third routing residual (#2197) sits in `src/runtime/next/`, which the arm does not scan at all.

This mission **hardens the gate surface** without re-architecting it:

- **Arm hardening (#2214)** — add one-hop cross-function parameter detection (FR-001), attribute-discipline (FR-008), scope-unify the identity arm to `merge/`+`lanes/`+`core/worktree_topology.py` (FR-002), and a named shrink-only census with sanctioned exclusions (FR-003).
- **Routing + co-landed unmask (#2197)** — re-point the `spec-kitty next` claimable-preview read in `runtime_bridge.py` onto the kind-aware leg-split (FR-004, caller-only) and extend the live scan to `src/runtime/next/` with a read-site floor (FR-005).
- **Partition + husk coverage (#2198 / #2199)** — add a machine-read per-kind rationale map cross-checked against the live frozensets (FR-006, net-new only) and a production-shaped STATUS-only husk no-op test for `check_pre30_layout` (FR-007).

Everything is built to CT7/#2077 test-hygiene doctrine (composite-key anchors, non-vacuous, self-mutation-tested) so the hardening **reduces, not adds**, test-suite friction (#2071, NFR-005).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest, `ast` (stdlib), ruff, mypy
**Storage**: N/A (test-gate hardening; no new persisted state)
**Testing**: pytest architectural gates (`tests/architectural/`) + integration behavioral proof (the divergent coord-topology fixture, `tests/integration/coord_topology_fixture.py`)
**Target Platform**: Linux/macOS developer + CI runners
**Project Type**: single repo — static-gate + test-coverage hardening plus ONE runtime read-routing change (`runtime_bridge.py`)
**Performance Goals**: N/A (AST scans over a bounded module set; no runtime hot path)
**Constraints**: zero new `file.py:NNN` ratchet anchors (CT7/NFR-001); zero false positives on the current tree (NFR-004); net test-suite-friction non-positive (NFR-005); no STATUS leg moved to PRIMARY (C-001)
**Scale/Scope**: ~5 architectural test modules touched/extended + 1 production caller (`runtime_bridge.py`) + 1 shared fixture extended once

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **Test-hygiene doctrine (CT7 / #2077)**: every new/extended gate is content-anchored via `_ratchet_keys.composite_key` (qualname/token-line), non-vacuous (anti-vacuity floor), and self-mutation-tested (synthetic offender → RED, revert → GREEN). The mission introduces zero `file:line` anchors and no new allowlist/denylist maintenance surface beyond the reused auto-discovery pattern. **#2198 stands as CT7's content-anchored, allowlist-free exemplar (C-004).** Conformant — no charter conflict.
- **No-direct-push / PR policy**: all changes land via PR to `origin/main`; `spec-kitty merge` targets local main only. The FR-005 scan-scope un-mask is paired with a pre-merge verbatim full-`tests/architectural/` dry-run (NFR-003, gate-unmask-cannot-self-validate). Conformant — no charter conflict.
- **Terminology Canon**: artifacts use "Mission"/"WP"; no `feature*` aliases introduced. Conformant.

No charter violations → Complexity Tracking section omitted.

## Project Structure

### Documentation (this mission)

```
kitty-specs/coord-authority-gate-hardening-01KW4T2F/
├── plan.md              # This file
├── research.md          # Phase 0 — settled design decisions
├── data-model.md        # Phase 1 — gate entities
├── quickstart.md        # Phase 1 — how to validate
├── contracts/
│   └── gate-hardening-contracts.md   # Phase 1 — the four gate contracts
├── spec.md              # Mission spec (FR-001..008, NFR-001..005, C-001..007, SC-001..006)
├── issue-matrix.md
└── tasks.md             # Phase 2 — /spec-kitty.tasks (NOT created here)
```

### Source surfaces (repository root)

```
tests/architectural/
├── test_gate_read_literal_ban.py        # callshape_violations (the AST arm), _IDENTITY/_LANES_READ_FUNCS,
│                                         #   _COORD_AWARE_CALLSHAPE_RESOLVERS, _PRIMARY_FOLD_CALLSHAPE_FUNCS,
│                                         #   _names_bound_from — IC-A2 (one-hop + resolver-vocab widen) + IC-A1 (ast.Attribute branch)
├── test_coord_read_residuals_closeout.py # _CALLSHAPE_KNOWN_RESIDUALS, _IDENTITY/_LANES_SCAN_DIRS,
│                                         #   floor+self-mutation pattern, _STATUS_BEARING_MODULES (C-007 guard)
│                                         #   — IC-A1 scope-unify; IC-A3 census + per-arm stale-pin split; IC-B runtime/next floor
├── test_write_surface_placement_guard.py # test_full_partition_resolves_per_membership — IC-C anchors FR-006 map
└── _ratchet_keys.py                     # composite_key — CT7 content-anchor (consumed, not edited)

src/mission_runtime/artifacts.py          # _PRIMARY_ARTIFACT_KINDS / _PLACEMENT_ARTIFACT_KINDS over
                                          #   MissionArtifactKind — the FR-006 rationale-map cross-check target

src/runtime/next/
├── runtime_bridge.py                     # _build_finalized_override_query_decision:3078 — IC-B FR-004 caller
└── discovery.py                          # preview_claimable_wp (leg-split callee, already present)

src/specify_cli/upgrade/
├── pre30_guard.py                        # check_pre30_layout — IC-C FR-007 no-op subject
└── legacy_detector.py                    # is_legacy_format / LEGACY_LANE_DIRS — FR-007 branch coverage

tests/integration/coord_topology_fixture.py  # divergent coord fixture (status-only husk + sentinel-meta) —
                                          #   IC-C OWNS+ADDS the tasks/-present-non-legacy husk (FR-007 sole consumer);
                                          #   IC-B/SC-002 reuse the existing coord_topology_mission fixture (no contention)
```

**Structure Decision**: single-repo. The mission edits architectural test modules + one production caller (`runtime_bridge.py`) + extends one shared integration fixture. No new packages, no new persisted state, no schema. The only non-test production edit is the FR-004 caller-only wiring (C-003 scope boundary).

## Implementation Concern Map

> **Note**: Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs — one concern may become multiple WPs. Concerns are not sequenced with WP-style IDs.

> **IC-A split (post-plan, paula ADJUST-BEFORE-TASKS).** The original single IC-A was over-stuffed (FR-001/002/003/008 + four self-mutation shapes + census + scope-unify). It is split into three coherent sub-concerns: **IC-A1** (scope-unify + attribute-discipline — mechanically simpler, mutually coherent), **IC-A2** (the novel inter-procedural one-hop capability + resolver-vocab widening + module-context — isolated because it is the only arm-signature change), and **IC-A3** (the named census + per-arm stale-pin split). Sequencing: A1 → A2 (A2 builds on A1's scope-unify) ; A3 lands with A1/A2.

### IC-A1 — Identity-arm scope-unify + attribute-discipline (FR-002 + FR-008)

- **Purpose**: Close the asymmetry that let the `executor` identity residual escape and make the attribute-passed coord-read shape visible — the mechanically simpler, mutually coherent half of the arm hardening.
- **Relevant requirements**: FR-002 (identity-arm scope-unify), FR-008 (attribute-discipline). NFR-001/NFR-002/NFR-004; C-007; SC-006.
- **Affected surfaces**:
  - `tests/architectural/test_coord_read_residuals_closeout.py` — (FR-002) widen the **identity** scan dirs to also include `merge/` + `lanes/` + `core/worktree_topology.py` (today identity = `cli/commands/` + `agent_utils/status.py`; lanes already covers merge/lanes/core). Run the NFR-004 census over the **widened identity scope**, route-or-pinning anything newly surfaced.
  - `tests/architectural/test_gate_read_literal_ban.py` — (FR-008) add the missing `ast.Attribute` branch to `callshape_violations` so `read_func(run.feature_dir)` is visible — flag any coord-bearing attribute unless it is a **sanctioned primary attribute** (`.target_feature_dir` or a primary-fold-bound field; the sanctioned-attr-name allowlist).
  - **Per-shape self-mutation tests**: `_VIOLATION_ATTRIBUTE` (`resolve_mission_identity(run.feature_dir)` in executor-shape → RED; `.target_feature_dir` counterpart → GREEN) + the **SC-006 executor coverage** (an injected identity read off a coord-aware dir in `merge/executor.py`, both shapes, caught by the scope-unified arm).
- **Sequencing/depends-on**: none (foundational). IC-A2 builds on this scope-unify.
- **Risks / design constraints**:
  - **C-007 (binding):** FORBID any blind attribute flag inside `_STATUS_BEARING_MODULES` — the exclusion is **read-func-scoped to `read_events` STATUS legs only**, NOT blanket-module; identity/lanes reads in `executor.py`/`recovery.py` (incl. SC-006's `resolve_mission_identity(run.feature_dir)`) stay IN-SCOPE and flaggable.
  - **CT7 (NFR-001/NFR-002)**: anchor via `composite_key`; ship the per-shape self-mutation test; keep the anti-vacuity floor (raise the read-site census after FR-002 widens scope).

### IC-A2 — One-hop cross-function machinery + resolver-vocab widening (FR-001)

- **Purpose**: Add the novel inter-procedural one-hop capability that catches the named residual — isolated because it is the only arm **signature** change (per-function → module/caller context) and the only resolver-vocabulary change.
- **Relevant requirements**: FR-001 (one-hop caller-binding). NFR-001/NFR-002/NFR-004; C-006; SC-001.
- **Affected surfaces**:
  - `tests/architectural/test_gate_read_literal_ban.py` — extend `callshape_violations`: when the flagged call's first arg is a function **parameter**, follow ONE hop to the caller and flag only if the caller binds that arg from a coord-aware resolver **without** a primary fold (`_PRIMARY_FOLD_CALLSHAPE_FUNCS`). **Two required mechanism parts:** (1) **WIDEN `_COORD_AWARE_CALLSHAPE_RESOLVERS` to align with the read-arm's `_TOPOLOGY_ROUTED_READ_RESOLVERS` (5 names)** — catalog `_resolve_setup_plan_feature_dir` and/or `_find_feature_directory`, **without which the `_run_documentation_wiring` ← `setup_plan` binding is not recognized as coord-aware and the one-hop check fires on no live caller (FR-001 hollow → SC-001/SC-006 hollow)**; (2) **MODULE/CALLER CONTEXT** — `callshape_violations(func, *, read_funcs)` is per-function; one-hop caller-binding needs a **module-scoped caller index** (an arm-signature/harness change). Retain the existing same-function PARAM-exemption EXCEPT where the one-hop check fires; **re-pin `test_callshape_arm_identity_passes_parameter_dir`** so it stays consistent (a plain caller-supplied param with no coord-aware caller binding still passes; do not leave it contradictory with FR-001).
  - **Self-mutation**: `_VIOLATION_CROSS_FUNCTION` (param bound from coord-aware caller → RED; clean counterpart from a primary-fold caller → GREEN).
- **Sequencing/depends-on**: builds on IC-A1 (the scope-unify lands first).
- **Risks / design constraints**:
  - **Root cause — the 3-vs-5 resolver-set asymmetry (the FR-001 hollowness).** The call-shape set holds 3 names; the read-arm holds 5 (the 3 + `_find_feature_directory` + `resolve_handle_to_read_path`). The residual's binding (`setup_plan` → `_resolve_setup_plan_feature_dir` → `_find_feature_directory`) is invisible to the 3-name set. **The widening (mechanism part 1) is what converts FR-001 from hollow to genuinely catching the named residual.** Re-run the NFR-004 census across the widened resolver surface.
  - **The single real residual** the one-hop check must catch is `mission_setup_plan::_run_documentation_wiring` ← coord-aware `setup_plan` (exactly one hop). A 2–3-hop chain is NOT a current residual (full multi-hop inter-procedural tracking is the deferred fallback, C-006).
  - **False-positive boundary (NFR-004 / C-006).** A blunt parameter-discipline rule is REJECTED (debbie: ~78–89% false-positive on the 9 in-scope param-takers, incl. leaf primitive `require_lanes_json`). The one-hop check whitelists `resolve_planning_read_dir`-bound / primary-fold-bound dirs and keys on the read-func families.

### IC-A3 — Named shrink-only census + per-arm stale-pin split (FR-003)

- **Purpose**: Record every in-scope param/attribute read site as routed-or-pinned with sanctioned exclusions, precisely, with zero false positives — and split the shared census so an identity-only pin does not RED the lanes clean-scan. (May fold into IC-A1; kept distinct for the stale-pin-split rationale.)
- **Relevant requirements**: FR-003 (named shrink-only census + sanctioned exclusions). NFR-004; C-005, C-007.
- **Affected surfaces**:
  - `tests/architectural/test_coord_read_residuals_closeout.py` — add the NAMED shrink-only census mirroring `_CALLSHAPE_KNOWN_RESIDUALS` / `_DIR_READ_KNOWN_RESIDUALS`, with **sanctioned, never-flagged** exclusions: leaf primitive `require_lanes_json`, payload/builder helper `_mission_identity_payload`, and the **`read_events` STATUS-leg reads** inside `_STATUS_BEARING_MODULES` (read-func-scoped — NOT blanket-module; identity/lanes reads in those modules stay in-scope).
  - **Per-arm stale-pin split (REQUIRED).** Today `_CALLSHAPE_KNOWN_RESIDUALS` is a single frozenset consumed by **both** the identity clean-scan test (~:204) and the lanes clean-scan test (~:235), each asserting `stale_pins = _CALLSHAPE_KNOWN_RESIDUALS - flagged` is empty. Adding an **identity-only** pin would make the **lanes** test's stale-pin assertion go RED (the pin is "stale" for the lanes scan). **Remediate by splitting into per-arm census sets** (e.g. `_IDENTITY_CALLSHAPE_KNOWN_RESIDUALS` / `_LANES_CALLSHAPE_KNOWN_RESIDUALS`) **OR scoping the stale diff to `census ∩ in-scope-for-this-arm`**.
- **Sequencing/depends-on**: lands with IC-A1/IC-A2 (consumes their flagged sets).
- **Risks / design constraints**:
  - **C-005**: coordinate the shrink-only `_DIR_READ_KNOWN_RESIDUALS` #2167 pin — do not rot it (it cites #2167's separate lineage).
  - **NFR-004**: full `tests/architectural/` green; the census enumerates every in-scope param/attribute read site with a route-or-pin disposition (zero false positives).

### IC-B — #2197 routing + co-landed scan-scope un-mask

- **Purpose**: Route the out-of-loop `spec-kitty next` claimable-preview read onto the kind-aware leg-split so a coord-topology mission previews from the authoritative PRIMARY surface (not the STATUS-only coord husk), and close the `src/runtime/next/` blind spot for the identity/lanes families.
- **Relevant requirements**: FR-004 (caller-only wiring at `runtime_bridge.py`), FR-005 (extend scan to `src/runtime/next/` with a read-site floor). NFR-003; C-001, C-002, C-003; SC-002.
- **Affected surfaces**:
  - `src/runtime/next/runtime_bridge.py` — `_build_finalized_override_query_decision` (the `preview_claimable_wp(feature_dir)` call at ~:3078). Change to pass a PRIMARY `planning_dir` (via `primary_feature_dir_for_mission` / the kind-aware seam — `_primary_runtime_feature_dir` already exists) + the coord `status_dir=` (coord-aware leg), mirroring `workflow.py::_preview_claimable_wp_for_mission` which already carries the split. **Caller-only** — `discovery.preview_claimable_wp` already has the `status_dir=` leg-split signature (C-003: this is the single sanctioned production routing edit).
  - `tests/architectural/test_coord_read_residuals_closeout.py` — extend the live identity/lanes scan families to include `src/runtime/next/`, with a `runtime/next` read-site floor mirroring `_count_read_call_sites` (provably non-vacuous). **The scan is non-vacuous on the current tree:** `runtime_bridge.py` already carries **≥3 in-family identity reads** — `get_mission_type(feature_dir)` at ~:2547/:3237/:3392 — so the extended scope sees real in-family sites immediately (it does NOT "match nothing today"). Each of these 3 reads MUST get an explicit **route-or-pin disposition** via the IC-A3 / FR-003 census (route to the kind-aware seam, or record as a named shrink-only residual / sanctioned exclusion) so the scope extension lands NFR-004-green.
  - **Fixture: IC-B does NOT extend it.** SC-002 uses the **existing** `coord_topology_mission` fixture (its STATUS-only husk already lacks `tasks/`). The new `tasks/`-present-non-legacy husk variant is consumed ONLY by IC-C (FR-007), so **IC-C owns and adds it** (see IC-C). There is no fixture contention to resolve — single consumer.
- **Sequencing/depends-on**: depends on the IC-A cluster (A1/A2/A3) — the arm extensions land first so the scan-scope un-mask is exercised against a hardened arm. *(FR-004 itself is pure caller-wiring and does not strictly need the A-cluster, but IC-B stays after A so the FR-005 scan-extension and its census disposition build on the hardened arm + census.)*
- **Risks**:
  - **Decoupling (FR-005 NOTE).** The FR-004 read is a `tasks/`-dir, parameter-fed shape the call-shape arm **cannot** see — it is gated **BEHAVIORALLY** by SC-002, NOT by the call-shape arm. The FR-005 scan extension does not "gate FR-004"; it future-proofs the runtime/next identity/lanes blind spot. Do not conflate the two.
  - **SC-002 must be a behavioral revert-fails test** asserting the returned domain value `preview.wp_id` (NOT a resolved-path equality), executed against the divergent coord fixture — reverting the FR-004 routing → coord husk → wrong/empty `wp_id`.
  - **NFR-003 (gate-unmask-cannot-self-validate).** Pair the FR-005 un-mask with a pre-merge verbatim full-`tests/architectural/` dry-run recorded in the PR body, plus the runtime/next read-site floor — so FR-005 is not green merely because FR-004 already routed the one site and the scan matches nothing.
  - **C-001/C-002**: the status leg stays coord-aware; consume the `resolve_planning_read_dir` seam, do not author `_read_path_resolver` internals.

### IC-C — #2198 partition-stability + #2199 husk no-op (parallel)

- **Purpose**: Make re-homing an artifact kind across the PRIMARY/STATUS partition a conscious CI-red decision with a documented per-kind rationale, and cover the `check_pre30_layout` clean no-op against a production-shaped STATUS-only husk.
- **Relevant requirements**: FR-006 (machine-read per-kind rationale map, net-new only), FR-007 (production-shaped STATUS-only husk + tasks/-present-non-legacy no-op test). NFR-005; SC-003, SC-004.
- **Affected surfaces**:
  - `tests/architectural/test_write_surface_placement_guard.py` (alongside `test_full_partition_resolves_per_membership`) — add a **machine-read** `{MissionArtifactKind: (partition, rationale, load_bearing_consumer)}` map and assert: (a) every enum member has an entry (add a kind without one → RED); (b) the map's PRIMARY/STATUS split **equals** the live `_PRIMARY_ARTIFACT_KINDS` / `_PLACEMENT_ARTIFACT_KINDS` (re-home a kind without editing its rationale → RED); plus a **parametrized anti-mutant across all load-bearing kinds** (not just SPEC). **Net-new only** — exhaustive + disjoint + the SPEC anti-mutant already exist; do NOT add line-pins (NFR-005).
  - `tests/integration/coord_topology_fixture.py` — **IC-C owns and adds** the `tasks/`-present-non-legacy husk variant (a coord husk carrying a post-3.0 `tasks/`: WP `.md`, no `planned/doing/...` lane subdirs). It is FR-007's sole consumer, so IC-C is where it lives.
  - `tests/integration/` — a coord-topology test asserting `check_pre30_layout` is a clean no-op against (a) a production-shaped STATUS-only husk (real `status.events.jsonl` + `meta.json`, no `tasks/` — NOT an empty dir, which short-circuits identically; reuses the existing `coord_topology_mission` fixture) AND (b) the IC-C-owned `tasks/`-present-but-non-legacy variant (exercises the `LEGACY_LANE_DIRS` / `.md` branch → still no-op).
- **Sequencing/depends-on**: parallel to IC-A/IC-B. **No fixture dependency on IC-B** — IC-C owns its own husk variant (paula post-plan: single consumer, no contention). It reuses the pre-existing `coord_topology_mission` fixture read-only for FR-007(a).
- **Risks**:
  - FR-006 is **verify-and-annotate**, not greenfield — the partition gate exists and is already anti-mutant; the value is the machine-read rationale map + the all-kinds anti-mutant. Keep it allowlist-free (CT7 exemplar, C-004).
  - FR-007 must use the **production-shaped** husk (real status payload), not an empty dir — an empty dir short-circuits `is_legacy_format` identically and proves nothing.

### Sequencing summary

```
IC-A1 (FR-002 scope-unify + FR-008 attribute-discipline)
   └─> IC-A2 (FR-001 one-hop + resolver-vocab widening + module-context)
   └─> IC-A3 (FR-003 named census + per-arm stale-pin split)   [lands with A1/A2]
        └─> IC-B (#2197 routing FR-004 + scan-scope FR-005; 3 runtime/next reads route-or-pinned)
IC-C (#2198 FR-006 + #2199 FR-007)  — PARALLEL; owns its own `tasks/`-present-non-legacy husk variant
```

**Fixture ownership (no contention — paula post-plan).** SC-002 (IC-B) uses the **existing** `coord_topology_mission` fixture; the `tasks/`-present-non-legacy husk variant is FR-007's **sole** consumer, so **IC-C owns and adds it**. The earlier "extend ONCE in IC-B; IC-C consumes read-only" contention resolution is removed — with a single consumer there is nothing to deconflict.
