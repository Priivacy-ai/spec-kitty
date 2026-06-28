# Spec: Coord-Authority Gate Hardening

**Mission**: coord-authority-gate-hardening-01KW4T2F
**Epic**: #2160 (coord-topology artifact authority — umbrella, stays open)
**Closes**: #2197, #2198, #2199, #2214

## Overview / Context

The #2160 coord-topology authority unification is **functionally complete**: writers, validators, and committers now agree on one canonical PRIMARY/STATUS authority path across the write side (#2154/#2155), the implement/review loop (#2115/#2140/#2183), and the merge/lanes/identity cluster (#2185/#2186/#2187).

But the #2212 pre-merge adversarial squad surfaced a structural weakness in the **static gate** that protects this authority: the call-shape arm (`callshape_violations`) is **intra-procedural** — it flags a coord-aware dir bound to a kind-specific read *within the same function*, but is blind to a coord-aware dir **bound one function up and passed in as a parameter or attribute**. Two real residuals (`lanes/lifecycle_sync.py`, `merge/executor.py:baseline_mission_id`) escaped the static gate and were caught only behaviorally. A related residual (`runtime_bridge` next-query preview, #2197) sits in `src/runtime/next/`, which the arm does not scan at all.

This mission **hardens the gate surface** so coord-read residuals are caught statically, the PRIMARY/STATUS partition is regression-proofed, and the one remaining out-of-loop routing residual (#2197) is both routed and gated — all built to the test-hygiene (CT7/#2077) standard so the hardening **reduces, not adds**, test-suite friction (#2071).

## User Scenarios & Testing

**Primary actor**: a spec-kitty contributor (or the merging agent) introducing or reviewing a coord-aware read; and CI, which must catch a regression before merge.

**Primary scenario (the gate catches what it previously missed):** A contributor adds a function in `merge/`/`lanes/`/`core/` that takes a `feature_dir` parameter and passes it into `read_lanes_json()` / `resolve_mission_identity()`. The caller binds that dir from a coord-aware resolver. Today this passes the static gate (the binding is one hop up) and only fails if a behavioral coord-topology test happens to exercise it. **After this mission**, the static gate flags it at CI time as a **one-hop cross-function violation** — the arm follows the parameter one hop to the caller's binding, and the binding's coord-aware resolver (now in the call-shape vocabulary, aligned with the read-arm) trips the flag. Anything not statically routable is dispositioned in the **named shrink-only census** (FR-003) rather than caught by a blunt self-resolve rule (rejected per C-006).

**Exception / edge path (no false positives):** A function legitimately receives a dir parameter that is *not* a coord-aware read target (e.g. a STATUS leg, or a dir already primary-folded by the caller). The hardened gate must NOT flag these — the extension is bounded so behavior-neutral param-passing stays green (otherwise a correct change goes red and gets reverted instead of the gate being fixed — the #2071 anti-pattern).

**Partition-stability scenario:** A contributor moves an artifact kind across the PRIMARY/STATUS partition (a "one-line move" that silently re-homes every routed read). CI must turn this into a conscious red decision with a documented per-kind rationale.

**Routing scenario (#2197):** On a coordination-topology mission, `spec-kitty next`'s finalized-override claimable-preview must report the claimable WP from the authoritative (primary) surface, not the STATUS-only coord husk.

**Rule that must always hold:** No STATUS read or write is ever routed to the PRIMARY surface (C-001 / #2155). The hardening adds gates and one read-routing; it must not move a status leg.

## Functional Requirements

| ID | Description | Issue | Priority | Status |
|----|-------------|-------|----------|--------|
| FR-001 | **One-hop cross-function (parameter) detection.** For an in-scope kind-read (`read_lanes_json`/`require_lanes_json`/`resolve_mission_identity`/`get_mission_type`) whose dir arg is a **function parameter**, follow one hop to the caller's binding: flag **only** when the caller binds that arg from a coord-aware resolver **without a primary fold**. A parameter whose caller-binding is primary/seam-bound (`resolve_planning_read_dir`, `primary_feature_dir_for_mission(_canonicalize_…)`) is NOT flagged. **Mechanism (two parts — both required for the named residual to be reachable):** (1) **Widen the call-shape coord-aware resolver set to align with the read-arm's `_TOPOLOGY_ROUTED_READ_RESOLVERS` (5 names).** Today `_COORD_AWARE_CALLSHAPE_RESOLVERS` holds only 3 (`resolve_feature_dir_for_mission`/`candidate_feature_dir_for_mission`/`resolve_feature_dir_for_slug`); it must also catalog `_find_feature_directory` and/or `resolve_handle_to_read_path` so the `setup_plan` → `_resolve_setup_plan_feature_dir` → `_find_feature_directory` binding behind the `_run_documentation_wiring` residual is recognized as coord-aware. **Without this widening the one-hop check fires on no live caller and the residual is never caught (SC-001/SC-006 hollow).** (2) **Give the arm module/caller context.** `callshape_violations(func, *, read_funcs)` is per-function today; one-hop caller-binding needs a **module-scoped caller index** (an arm-signature/harness change), not a single-function AST. Re-run the NFR-004 census across the widened resolver surface (route-or-pin anything newly surfaced). (Precisely catches the one real residual — `mission_setup_plan::_run_documentation_wiring` ← coord-aware `setup_plan` — without false-flagging the legit param-takers. The existing same-function PARAM-exemption is retained EXCEPT where this one-hop caller check fires; the precision-guard test is re-pinned, not left contradictory.) | #2214 | MUST | Draft |
| FR-002 | The **identity** arm's scan scope is unified to also cover `merge/` + `lanes/` + `core/worktree_topology.py` (closing the asymmetry that let the `executor` identity residual escape — the lanes.json arm already covers these). | #2214 | MUST | Draft |
| FR-003 | **Named shrink-only census + sanctioned exclusions** (NOT a blunt param-discipline flag — which would false-flag ~78–89% of in-scope param-takers). Every in-scope param-/attribute-fed kind-read is either routed or recorded in a named shrink-only census (mirroring `_DIR_READ_KNOWN_RESIDUALS`/`_CALLSHAPE_KNOWN_RESIDUALS`). **Sanctioned, never-flagged**: leaf primitives that must take a dir (`require_lanes_json`), payload/builder helpers (`_mission_identity_payload`), and the **`read_events` STATUS-leg reads** inside `_STATUS_BEARING_MODULES` (`lanes/recovery.py`, `merge/executor.py`). The exclusion is **read-func-scoped to the STATUS leg (`_STATUS_READ_FUNCS = {"read_events"}`), NOT a blanket module exclusion** — identity/lanes reads in `executor.py`/`recovery.py` (e.g. an injected `resolve_mission_identity(run.feature_dir)` off a coord-aware dir, incl. SC-006's executor case) remain **in-scope and flaggable**. Excluding the whole module would let the SC-006 / FR-008 executor residual escape. | #2214 | MUST | Draft |
| FR-004 | The `spec-kitty next` claimable-preview read in `src/runtime/next/runtime_bridge.py` (the `preview_claimable_wp` caller) is routed onto the kind-aware seam — a **caller-only** wiring change passing a PRIMARY `planning_dir` + the coord `status_dir=` (the `discovery.preview_claimable_wp` callee already carries the leg-split signature). | #2197 | MUST | Draft |
| FR-005 | Extend the live arm's scan scope to `src/runtime/next/` to **future-proof identity/lanes reads there**, with a read-site floor (mirroring `_count_read_call_sites`) so the extended scan is provably non-vacuous. **The scan is NON-vacuous on the current tree:** `runtime_bridge.py` already carries **≥3 in-family identity reads** — `get_mission_type(feature_dir)` at ~lines 2547/3237/3392 — so the extended scope immediately sees real in-family sites (it does NOT "match nothing today"). Each of these 3 reads MUST receive an explicit **route-or-pin disposition** under the FR-003 census (route to the kind-aware seam, or record as a named shrink-only residual / sanctioned exclusion) so the scope extension lands NFR-004-green. **NOTE:** the FR-004 read is a `tasks/`-dir, parameter-fed shape the call-shape arm cannot see — it is gated **behaviorally** by SC-002, NOT statically by this scan. The scan extension does not "gate FR-004"; it closes the runtime/next blind spot for the identity/lanes families. | #2197 | MUST | Draft |
| FR-006 | **Net-new only** (exhaustive + disjoint + a SPEC anti-mutant already exist in `test_full_partition_resolves_per_membership`). Add a **machine-read** per-kind rationale map `{MissionArtifactKind: (partition, rationale, load_bearing_consumer)}` and assert: (a) every enum member has an entry (add a kind without one → RED); (b) the map's PRIMARY/STATUS split **equals** the live `_PRIMARY_ARTIFACT_KINDS`/`_PLACEMENT_ARTIFACT_KINDS` (re-home a kind without editing its rationale → RED); plus a **parametrized anti-mutant across all load-bearing kinds** (not just SPEC). | #2198 | MUST | Draft |
| FR-007 | A coord-topology test asserts `check_pre30_layout` is a clean **no-op** against (a) a **production-shaped STATUS-only husk** (real `status.events.jsonl`+`meta.json`, no `tasks/` — via the divergent coord-topology fixture, NOT an empty dir which short-circuits identically) AND (b) a `tasks/`-present-but-non-legacy variant (exercises the `LEGACY_LANE_DIRS`/`.md` branch → still no-op). | #2199 | SHOULD | Draft |
| FR-008 | **Attribute-discipline** (the executor-shape escape the scanner has no `ast.Attribute` branch for). An in-scope kind-read whose first arg is an attribute (e.g. `run.feature_dir`) must be a **sanctioned primary attribute** (`.target_feature_dir` or a primary-fold-bound field); any other coord-bearing attribute is flagged. Self-mutation: reintroducing `resolve_mission_identity(run.feature_dir)` in `executor` → RED. In-scope (NOT a fallback). | #2214 | MUST | Draft |

## Non-Functional Requirements

| ID | Description | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | CT7 conformance: every new/extended gate is **content-anchored** via `_ratchet_keys.composite_key` (qualname/symbol), never a `file:line` ratchet. | Zero new `file.py:NNN` ratchet keys introduced (grep-verifiable). | Draft |
| NFR-002 | Every new/extended gate is **non-vacuous + self-mutation-tested** (a synthetic offender → RED; revert → GREEN), reusing the existing closeout floor+MARGIN+self-mutation pattern. | Each new gate ships a self-mutation test; anti-vacuity floor present. | Draft |
| NFR-003 | The scan-scope un-mask (FR-005) is validated by a **pre-merge verbatim full-gate dry-run** AND a **runtime/next read-site floor** so FR-005 is provably non-vacuous (not green merely because FR-004 already routed the one site and the scan matches nothing). | PR body carries the verbatim full-`tests/architectural/` dry-run; FR-005 ships a `runtime/next` read-site count floor. | Draft |
| NFR-004 | The FR-001/FR-008 extension produces **zero false positives** on the current tree, verified via the FR-003 named shrink-only census (every in-scope flagged site is either routed or an individually-justified pinned exception). | Full `tests/architectural/` green; the census enumerates every in-scope param/attribute read site with a route-or-pin disposition. | Draft |
| NFR-005 | Net test-suite-friction impact is **non-positive** (reduce-or-neutral). | No new allowlist/manual-denylist maintenance surface beyond the reused auto-discovery pattern; #2198 adds no line-pins. | Draft |

## Constraints

| ID | Description |
|----|-------------|
| C-001 | STATUS reads/writes stay coord-aware — no #2155 re-opener. The arm extensions and the #2197 routing must not move a status leg to PRIMARY. |
| C-002 | Consume the resolver seam (`resolve_planning_read_dir`); do not author `_read_path_resolver` internals. |
| C-003 | Scope boundary: static-gate + test-coverage hardening **plus the single #2197 production read-routing change** (explicitly NOT purely behavior-neutral). No other production routing edits. |
| C-004 | CT7-binding: build to #2077/CT7 doctrine (composite-key anchors, non-vacuous, self-mutation-tested); cross-cite #2077, and let #2198 stand as CT7's content-anchored, allowlist-free exemplar. |
| C-005 | Coordinate the shrink-only `_DIR_READ_KNOWN_RESIDUALS` #2167 pin: do not rot it (it cites #2167's separate lineage). |
| C-006 | The primary plan is the auto-discovery arms (FR-001 one-hop caller-binding + FR-002 scope-unify + FR-008 attribute-discipline + FR-005 scan extension), all low/neutral-friction. A **blunt** parameter-discipline rule is explicitly rejected (it false-flags ~78–89% of legit param-takers incl. the leaf primitive). Full **multi-hop** inter-procedural tracking is the only deferred fallback (a 2–3-hop chain is not a current residual). |
| C-007 | Do NOT apply any param/attribute flag blindly inside `_STATUS_BEARING_MODULES` (`recovery.py` etc.): a mechanical "self-resolve → PRIMARY" remediation there could drive a status→PRIMARY move (C-001). Such sites are sanctioned exclusions in the FR-003 census. |

## Success Criteria

- **SC-001**: A coord-aware dir passed **cross-function (one-hop, parameter)** into an in-scope kind-read is caught by CI's static gate — proven by an **automated synthetic-AST self-mutation test** (a `_VIOLATION_CROSS_FUNCTION` snippet asserted RED + its clean counterpart GREEN; NFR-002), not a one-time manual inject.
- **SC-002**: On coord topology, `spec-kitty next`'s claimable-preview resolves from the **primary** surface — proven by an **executed** revert-fails test asserting the returned domain value `preview.wp_id` (NOT a resolved-path equality); reverting the FR-004 routing → coord husk → wrong/empty `wp_id`.
- **SC-003**: Re-homing any load-bearing artifact kind across the PRIMARY/STATUS partition is a **conscious CI-red decision** — the machine-read rationale map's split must equal the live frozensets (move-a-kind-without-rationale → RED), enforced by a parametrized anti-mutant across all load-bearing kinds.
- **SC-004**: `check_pre30_layout` is a verified clean no-op against a **production-shaped** STATUS-only coord husk (real status payload, not an empty dir) and a `tasks/`-present-non-legacy variant.
- **SC-005**: The mission introduces **zero new `file:line` ratchet anchors**, and every new/extended gate is non-vacuous + self-mutation-tested (CT7).
- **SC-006**: An injected identity read off a coord-aware dir in `merge/executor.py` — both the **parameter** shape (FR-002 scope-unify) and the **attribute** `run.feature_dir` shape (FR-008) — is caught by the scope-unified arm post-mission (today `merge/` is outside the identity arm's scope and attribute args are invisible — this is net-new, measurable coverage).

## Key Entities

- **Call-shape arm** (`tests/architectural/test_gate_read_literal_ban.py::callshape_violations`) — the AST scanner this mission extends (cross-function + scope-unify + param-discipline).
- **PRIMARY/STATUS partition** (`src/mission_runtime/artifacts.py`: `_PRIMARY_ARTIFACT_KINDS` / `_PLACEMENT_ARTIFACT_KINDS` over `MissionArtifactKind`) — the invariant #2198 protects.
- **Kind-aware seam** (`resolve_planning_read_dir`) — the routing target; **coord-aware resolvers** (`candidate_/resolve_feature_dir_for_mission`, `resolve_feature_dir_for_slug`) — the things a coord-read must not bind a PRIMARY read from.
- **Composite-key anchor** (`tests/architectural/_ratchet_keys.py::composite_key`) — the CT7 content-anchor (replaces `file:line`).
- **Divergent coord-topology fixture** (`tests/integration/coord_topology_fixture.py`, sentinel-meta variant) — the behavioral backstop reused for SC-001/SC-002/FR-007.

## Assumptions

- Both prior coord-authority missions (#2194, #2212) are merged; this mission branches from `main` with the primary checkout free.
- The partition-stability gate (#2198) mostly exists already (`test_full_partition_resolves_per_membership`) — #2198 is verify-and-annotate, not greenfield.
- `check_pre30_layout`/`is_legacy_format` already returns False when `tasks/` is absent — FR-007 is coverage of the realistic husk shape, not a behavior change.
- The auto-discovery arms (FR-001 one-hop caller-binding + FR-002 scope-unify + FR-008 attribute-discipline + FR-005 scan extension) suffice for the known residual classes; only a 2–3-hop chain (not a current residual) would need full multi-hop inter-procedural tracking (deferred fallback). A **blunt** parameter-discipline rule is rejected (post-spec squad: ~78–89% false-positive rate, C-001 risk).
- Post-spec adversarial squad (alphonso/renata/debbie/paula, 2026-06-27) tightened this spec before plan: FR-001 sharpened to one-hop caller-binding, FR-003 reframed to a census, FR-005 decoupled from the static-gate claim, FR-006 re-scoped to net-new, FR-007 to a production husk, FR-008 added for the attribute case, SC-006 added for FR-002.

## Dependencies & References (do NOT fold)

- **#2071 / #2077 (CT7)** — the test-suite-friction epic + its gate-hygiene doctrine child. This mission conforms to and cross-cites #2077; it does not absorb the broader CT1/CT7 remediation.
- **#2167** — separate pre-3.0 `scripts/tasks/` legacy-reader cleanup; coordinate the shared shrink-only pin (C-005).
- **#2017** — guard-friction umbrella; the tracer's tooling-friction items belong here / under #2160, not in #2071.
- **#2160** — parent epic (umbrella, stays open); this mission is its gate/test-coverage track.
