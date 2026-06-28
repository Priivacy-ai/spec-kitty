# Research — Coord-Authority Gate Hardening (01KW4T2F)

Phase 0. The design is SETTLED by the post-spec adversarial squad (alphonso/renata/debbie/paula, 2026-06-27). This document consolidates the decisions that tightened the spec before planning, each as Decision / Rationale / Alternatives-rejected. There are no open NEEDS-CLARIFICATION items.

---

## Decision 1 — One-hop caller-binding for cross-function parameter detection (FR-001)

**Decision**: When a kind-read (`read_lanes_json`/`require_lanes_json`/`resolve_mission_identity`/`get_mission_type`) takes a first arg that is a **function parameter**, the arm follows ONE hop to the caller's binding and flags **only** when the caller binds that arg from a coord-aware resolver (`_COORD_AWARE_CALLSHAPE_RESOLVERS`) **without** a primary fold (`_PRIMARY_FOLD_CALLSHAPE_FUNCS`). A parameter whose caller-binding is primary/seam-bound (`resolve_planning_read_dir`, `primary_feature_dir_for_mission(_canonicalize_…)`) is not flagged.

**Rationale**: The static arm is intra-procedural today (`callshape_violations` only flags a coord-aware dir bound in the SAME function). Two real residuals — `lanes/lifecycle_sync.py` and `merge/executor.py::baseline_mission_id` — bound the coord-aware dir one hop up and passed it in, so they escaped the static gate and were caught only behaviorally. The single remaining one-hop residual class in production is `mission_setup_plan::_run_documentation_wiring` ← coord-aware `setup_plan`, which a one-hop caller check catches precisely.

**Root cause — the 3-vs-5 resolver-set asymmetry (the FR-001 hollowness, paula post-plan).** The named residual `_run_documentation_wiring(feature_dir)` reads `get_mission_type(feature_dir)`; its caller `setup_plan` binds `feature_dir` from `_resolve_setup_plan_feature_dir` → `_find_feature_directory`. But the call-shape arm's `_COORD_AWARE_CALLSHAPE_RESOLVERS` holds only **3** names (`resolve_feature_dir_for_mission`/`candidate_feature_dir_for_mission`/`resolve_feature_dir_for_slug`), whereas the read-arm's `_TOPOLOGY_ROUTED_READ_RESOLVERS` holds **5** (the 3 plus `_find_feature_directory` and `resolve_handle_to_read_path`). So even with a one-hop caller index in place, the binding behind the residual is bound from a resolver the call-shape arm **does not recognize as coord-aware** → the one-hop check fires on no live caller → catches no offender → SC-001/SC-006 hollow.

**Mechanism (both parts required):** (1) **Widen `_COORD_AWARE_CALLSHAPE_RESOLVERS` to align with `_TOPOLOGY_ROUTED_READ_RESOLVERS`** — catalog `_resolve_setup_plan_feature_dir` and/or `_find_feature_directory` so the `_run_documentation_wiring` binding is seen as coord-aware. (2) **Give the arm module/caller context** — `callshape_violations(func, *, read_funcs)` is per-function; one-hop caller-binding requires a **module-scoped caller index** (an arm-signature/harness change), not a single-function AST. After widening, **re-run the NFR-004 census across the widened resolver surface** (route-or-pin anything newly surfaced). This converts FR-001 from hollow to genuinely catching the named residual.

**Alternatives rejected**:
- **Blunt parameter-discipline rule** (flag every kind-read taking a param, requiring the callee to self-resolve by kind): rejected. debbie measured ~78–89% false-positive on the 9 in-scope param-takers, including the leaf primitive `require_lanes_json` (which MUST take a dir). It also creates a C-001 risk in `recovery.py`: a mechanical "self-resolve → PRIMARY" remediation on a STATUS leg would drive a status→PRIMARY move (#2155 re-opener). Rejected as both noisy and unsafe (C-006).
- **Full multi-hop inter-procedural tracking**: deferred fallback only. A 2–3-hop chain is not a current residual; building inter-procedural data-flow now is unjustified scope (C-006).

---

## Decision 2 — Attribute-discipline via a bounded `ast.Attribute` branch (FR-008)

**Decision**: Add the missing `ast.Attribute` branch to the scanner. A kind-read whose first arg is an attribute (e.g. `run.feature_dir`) must be a **sanctioned primary attribute** (`.target_feature_dir`, or a field bound from a primary fold); any other coord-bearing attribute is flagged. Self-mutation: reintroducing `resolve_mission_identity(run.feature_dir)` in `executor` → RED.

**Rationale**: The scanner has NO `ast.Attribute` branch — `_call_func_name`/`callshape_violations` only inspect `ast.Name` and `ast.Call` first args. The `merge/executor.py` `run.feature_dir`-shape identity read is therefore structurally invisible (this is exactly the residual that escaped). A bounded attribute rule (sanctioned-primary-attr vs coord-bearing) closes it without requiring full field-provenance inter-procedural analysis. This is in-scope, NOT a fallback.

**Alternatives rejected**:
- **Full field-provenance / inter-procedural attribute tracking**: rejected as over-engineered. The bounded sanctioned-attribute allowlist (`.target_feature_dir` + primary-fold-bound fields) covers the real shape; anything else is flagged conservatively.
- **Ignoring attribute args entirely** (status quo): rejected — it leaves the executor escape uncovered (SC-006 requires the attribute shape be caught).

---

## Decision 3 — FR-005 decoupled from "gates FR-004"; behavioral gating + scan-extension + read-site floor

**Decision**: FR-005 (extend the live arm's scan to `src/runtime/next/`) future-proofs the identity/lanes families there and ships a read-site floor (mirroring `_count_read_call_sites`) proving non-vacuity. The FR-004 read itself is gated **BEHAVIORALLY** by SC-002 (executed revert-fails on `preview.wp_id`), NOT by the call-shape arm.

**Rationale**: renata + alphonso established that the FR-004 read is a `tasks/`-dir, parameter-fed shape the call-shape arm **cannot** see (the arm's vocabulary is identity/lanes coord-aware reads, not `tasks/`-dir planning reads through `preview_claimable_wp`). Claiming the scan "gates FR-004" would be a vacuity trap. **But the scan is NOT itself vacuous (paula post-plan correction):** the earlier "matches nothing today" framing was wrong — `runtime_bridge.py` already carries **≥3 in-family identity reads**, `get_mission_type(feature_dir)` at ~lines 2547/3237/3392, so the extended scope sees real in-family sites the moment it lands. These 3 reads MUST each get an explicit **route-or-pin disposition** under the FR-003 census (route to the kind-aware seam, or record as a named shrink-only residual / sanctioned exclusion) so the FR-005 scope extension lands **NFR-004-green**. So: the FR-004 correctness is proven behaviorally; the scan extension independently closes the runtime/next blind spot for the identity/lanes families AND is provably non-vacuous against the 3 existing in-family reads.

**Alternatives rejected**:
- **Asserting FR-005's scan catches the FR-004 site**: rejected as the vacuity trap above (gate-unmask-cannot-self-validate).
- **Skipping the runtime/next scan extension** (rely on behavioral SC-002 alone): rejected — leaves identity/lanes reads in `src/runtime/next/` permanently un-scanned (a future residual class). The floor (NFR-003) keeps the extension honest.

---

## Decision 4 — FR-006 net-new only: a machine-read per-kind rationale map

**Decision**: The partition-stability gate is **verify-and-annotate**. `test_full_partition_resolves_per_membership` already proves exhaustive + disjoint + a SPEC anti-mutant. FR-006 ADDS a machine-read `{MissionArtifactKind: (partition, rationale, load_bearing_consumer)}` map asserting (a) every enum member has an entry, (b) the map's split equals the live `_PRIMARY_ARTIFACT_KINDS`/`_PLACEMENT_ARTIFACT_KINDS`, plus a parametrized anti-mutant across ALL load-bearing kinds.

**Rationale**: The "one-line move" hazard (re-homing a kind silently re-routes every routed read) is real, but the membership equality already mostly exists. The net-new value is the rationale map: re-homing a kind without editing its documented rationale → RED, turning a silent partition flip into a conscious CI-red decision with a documented per-kind reason (SC-003). Extending the anti-mutant from SPEC-only to all load-bearing kinds removes the residual "only SPEC is mutant-tested" gap.

**Alternatives rejected**:
- **Greenfield re-author of the partition gate**: rejected — the existing gate is sound; re-authoring adds risk and friction for no coverage gain.
- **Line-pins for partition membership**: rejected — violates NFR-005 (no new line-pin maintenance surface) and CT7 (content-anchored, allowlist-free). The map is keyed on enum members, not file lines.

---

## Decision 5 — FR-007 against a production-shaped STATUS-only husk, not an empty dir

**Decision**: The `check_pre30_layout` no-op test runs against (a) a production-shaped STATUS-only husk (real `status.events.jsonl` + `meta.json`, no `tasks/`, via the divergent coord-topology fixture) AND (b) a `tasks/`-present-but-non-legacy variant (exercises the `LEGACY_LANE_DIRS`/`.md` branch in `is_legacy_format` → still no-op).

**Rationale**: `is_legacy_format` short-circuits to False when `tasks/` is absent. An EMPTY dir hits the same short-circuit and proves nothing about the realistic coord-husk shape. The realistic husk carries status payload + meta but no `tasks/` (post-#2106), and the tasks/-present-non-legacy variant exercises the branch that walks `LEGACY_LANE_DIRS` and finds no lane subdirs with `.md` files. Together they cover both no-op paths against production-shaped inputs (SC-004). #1057 (the lineage that retired the pre-3.0 reader) left exactly this coord-husk no-op path untested.

**Alternatives rejected**:
- **Empty-dir fixture**: rejected — short-circuits identically; vacuous coverage.
- **A behavior change to `check_pre30_layout`**: rejected — `is_legacy_format` already returns False correctly; FR-007 is coverage of the realistic husk shape, not a behavior change.

---

## Decision 6 — CT7 conformance: composite-key anchors, non-vacuous, self-mutation-tested

**Decision**: Every new/extended gate is content-anchored via `_ratchet_keys.composite_key` (qualname + token-line), non-vacuous (anti-vacuity floor / read-site floor), and self-mutation-tested (synthetic offender → RED, revert → GREEN). Zero new `file.py:NNN` ratchet anchors. The FR-003 census mirrors the existing shrink-only `_CALLSHAPE_KNOWN_RESIDUALS` / `_DIR_READ_KNOWN_RESIDUALS` pattern.

**Rationale**: The hardening must REDUCE, not add, test-suite friction (#2071 / NFR-005). #2077/CT7 doctrine is the standard: content-anchored keys survive +1 line drift; self-mutation tests are an automated regression rather than a rotting manual mutation log (DIRECTIVE_041). #2198 becomes CT7's content-anchored, allowlist-free exemplar (C-004). No new allowlist/manual-denylist maintenance surface beyond the reused auto-discovery pattern.

**Alternatives rejected**:
- **`file:line` ratchet anchors**: rejected — they rot on any line drift and are the #2071 anti-pattern (NFR-001 forbids new ones).
- **Recorded manual mutation logs**: rejected — they cannot be re-run and rot silently (DIRECTIVE_041); self-mutation tests are mandatory (NFR-002).

---

## Cross-references (NOT folded — context/boundary/lineage)

- **#2071 / #2077 (CT7)** — the test-suite-friction epic + its gate-hygiene doctrine child; this mission conforms to and cross-cites #2077 (does not absorb broader CT1/CT7 remediation).
- **#2167** — separate pre-3.0 `scripts/tasks/` legacy-reader cleanup; coordinate the shared shrink-only `_DIR_READ_KNOWN_RESIDUALS` pin (C-005, do not rot it).
- **#2017** — guard-friction umbrella; tracer tooling-friction items land there / under #2160, not #2071.
- **#2160** — parent epic (umbrella, stays open); this mission is its gate/test-coverage track.
- **#1057** — pre-3.0 reader retirement / layout-guard lineage (verified-already-fixed); #2199 covers the untested coord-husk no-op path it left.
