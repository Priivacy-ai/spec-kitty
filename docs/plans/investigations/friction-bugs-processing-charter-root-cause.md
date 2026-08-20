---
title: 'Processing & charter friction bugs: shared root causes and mission scope'
description: 'Five-lens squad root-cause analysis of a 7-issue friction defect class (#3605, #3604, #3598, #3596, #3590, #3578, #3571), code-verified against main, with a scoped mission seed and the open decisions specify must resolve.'
doc_status: draft
updated: '2026-08-20'
related:
- kitty-specs/kind-complete-cascade-orphan-wiring-01M0FQCD/research.md
- docs/plans/doctrine/delivery-reachability-wiring-table.md
- docs/architecture/mission-type-resolution.md
- docs/architecture/execution-lanes.md
- docs/adr/3.x/2026-08-20-1-cascade-kind-complete-relation-set.md
---

# Processing & charter friction bugs: shared root causes and mission scope

Pre-mission investigation for a planned **"fix the last known friction bugs in
processing and charter"** mission. Seven open issues were run through five
profile-loaded research lenses (pattern-scout, architecture, root-cause /
five-paradigm, semantic, synthesis) working read-only and independently. Every
file:line claim below was re-verified against `main` (HEAD `b28c5a9bf2`). The
five lenses converged on the same cluster split, the same two consolidations,
and the same dominant meta-pattern.

Scope of inputs: **#3605, #3604, #3598, #3596, #3590, #3578, #3571**.

## 0. The one-paragraph answer

Six-and-a-half of the seven issues are the same disease: a decision point
**defaults, drops, or short-circuits silently** instead of failing loud or
surfacing the delta. A single discipline — *"fail loud / surface the delta at
the decision point"* — would have caught #3605, #3604, #3596, #3598, #3571,
#3578, and the authoring-time half of #3590. #3571 (P0) is the most dangerous
instance: it prints a **fabricated success line** while discarding the operator's
intent. The remaining structure is two clusters — a **charter/doctrine
DRG-reach** family and a **processing/workflow** family — with two pairs that
should be planned as one unit each.

## 1. The missing shared contract

The semantic lens names what every issue gestures at: an **operator-signal
contract** — *a state change or a dropped input must emit an operator-visible
signal (diff, console line, warning, or error), or be a documented deliberate
silence.* It spans two bounded contexts that must **not** be merged into one fix:

- **B1 — silent input-drop (doctrine/charter projection):** #3605, #3604, #3596, #3598.
- **B2 — silent mutation/allocation (operator CLI):** #3578, #3571, #3590.

Unify the *vocabulary*; keep the *fixes* context-separated.

## 2. Cluster A — charter/doctrine DRG-reach

### 2.1 Whack-a-carrier at the DRG extract/emit seam — #3605 + #3604

The `{type, id, when?, reason?}` reference loop is hand-copied **five times in
two styles** in `src/doctrine/drg/migration/extractor.py`; only the *relation
resolver* actually varies.

- **#3605** — the Procedures branch (`extractor.py:~900`) mints a **bare**
  `DRGEdge(source, target, relation)`, bypassing `_reference_edge_kwargs`
  (`:542`) that the directive/tactic/paradigm branches use (`:768/:802/:823/:875`).
  Shipped procedures author `reason:` → it is **silently dropped**.
- **#3604** — the extractor **never reads `governance-profile.yaml`** (zero hits
  under `src/doctrine/drg/`; all readers are charter-side). So no mission type's
  *type-wide* governance enters the DRG at all; `plan` cascades empty only
  because it authors *only* type-wide governance.

**Missed generalization:** one `_emit_reference_edges(...)` helper owning the
whole loop (node-ensure + `_reference_edge_kwargs` spread + skip-empty),
parameterized only by the relation resolver, for the **five `{type, id, when?,
reason?}`-shaped reference branches** (directive, tactic top + step, paradigm,
procedure), with a **structural test** asserting no such branch emits a bare edge
where the source authored metadata. This subsumes #3605.

**Correction (code-inspection squad):** #3604 does **not** route through that
helper. `governance-profile.yaml` is a `selected_<kind>: [id, …]` bare-id list
(the `extract_action_edges` shape), not a `{type, id}` reference — so #3604 is a
**separate new extractor pass** (`extract_governance_profile_edges`), not a sixth
route through `_emit_reference_edges`. The two agent-profile reference branches
(bare-string list; `rationale` key, no `when`) also do not fit the helper — leave
them on `_add_ref_edge`.

**Load-bearing sequencing:** both move golden `*.graph.yaml` counts. The
fragments are disjoint (`procedure.graph.yaml` vs `mission_type.graph.yaml`) but
the guard tests are whole-graph → land both extractor edits, then **regenerate
the goldens once**. This is exactly the "re-ledger once" constraint that mission
M5 (PR #3600) cited when it deferred both.

### 2.2 Coarse-proxy predicate — a fail-open gate in front of a finer capability — #3596 + #3598

The same anti-pattern in two adjacent charter files: a precise per-entity
question is answered by a broad boolean proxy that is true in the common case.

- **#3596** — `BOOTSTRAP_ACTIONS = frozenset({specify, plan, implement, review})`
  (`src/charter/context.py:115`) short-circuits every other action to `compact`
  at `:255`/`:484` **before** a bundle is built. `tasks`, `retrospect`, all
  `research`/`documentation` actions have a non-empty `index.yaml` and deliver
  nothing. The downstream traversal already honours any DRG-declared node
  (verified in code: the action name is opaque to `resolve_context`; an
  undeclared node returns empty, a declared node delivers). **Fix:** carry a
  grain iff the merged DRG declares the node; keep the 4-token fast path. The
  graph is loaded *inside* the action bundle (`bundle.merged`), so "thread the
  already-loaded graph" means **resolve the bundle first, then decide mode from
  node-membership** — do not add a second pre-gate load.

  **Correction (code-inspection squad):** the "all four built-ins stay
  byte-identical" claim is **false as stated** — the built-in `tasks` and
  `retrospect` action indexes are non-empty, so the fix (correctly) flips them
  `compact → bootstrap` and they start delivering. The real self-limiting
  property is narrower: an **undeclared** action node stays compact (pinned by
  `test_non_bootstrap_action_returns_compact`). A naïve "diff all built-ins vs
  `main`" acceptance test would fail and must not be written; pin instead: (a)
  bootstrap actions unchanged, (b) undeclared action stays compact, (c)
  tasks/retrospect now deliver their index grain. Note the issue also conflates
  two timing tests (import-time I/O vs per-call latency); neither breaks, but add
  a per-call pin for a declared non-bootstrap action.
- **#3598 (P1)** — `_resolve_governance_slot` hard-fails only
  `if not is_registered and not has_override` (`mission_type_profiles.py:804`);
  `has_override` = `_project_has_doctrine_overrides` (`:1235`) is **project-wide**
  (true for essentially every real charter), so a **typo'd type resolves
  silently** with a fabricated `provenance="project"` (`:809`). **Fix:** per-type
  probe — tolerate only when `.kittify/doctrine/mission_types/<type>/governance-profile.yaml`
  exists.

**Shared ADR:** *"gate on the declared entity, not a coarse set."* Two
independent diffs, different files/entities. Both flip an existing test that
documents the current behaviour as intentional **red by design** (#3598:
`tests/charter/test_mission_type_profiles.py`) → ship an ADR line; do not "fix
the test back."

### 2.3 N-disagreeing readers of `meta.json` mission-type (bonus)

#3598's "second inconsistency" is bigger than it states: there are **4+
hand-rolled parsers with different defaults** (`mission_type_profiles.py:748`
reads only `mission_type`; `mission_metadata.py:255` defaults `software-dev`;
`context/resolver.py:94` → `None`; `dashboard/handlers/features.py:68` reads only
legacy `mission`), while a blessed canonical reader
**`mission.py:_canonical_meta_mission_type` (`:542`)** already exists. Widening
#3598 to adopt it project-wide changes legacy `{"mission": …}` resolution → an
**explicit spec decision, not a drive-by**.

## 3. Cluster B — processing/workflow

Independent of Cluster A; no DRG/golden entanglement.

- **#3571 (P0) — `--base` silently ignored; lane inherits unrelated ancestry.**
  Two disjoint allocation routes: `--base` patches **only**
  `lanes_manifest.mission_branch` (`implement.py:1412`) and prints success
  (`:1411`), but `allocate_lane_worktree` (`worktree_allocator.py`) branches
  coord-topology missions (the modern default, including the repro mission) from
  `coordination_branch` (`:260-264`) and reads `mission_branch` **only** in the
  legacy `else` (`:272-276`). So `--base` is a no-op on the dominant path and the
  lane inherits the coord branch's original ancestry (the "unrelated branch
  became an ancestor" symptom). Reuse (`:191`) and crash-recovery (`:235`)
  early-returns honour it either. **This is a regression / topology gap, not a
  missing feature** (`--base` was wired for the legacy route by #1684) → start
  from a **red-first repro**, thread `base` into the allocator so the override
  binds the field the dominant path reads, and **fail loud** if a topology cannot
  honour it.
- **#3578 (P2) — rollback reset became invisible.** `_mt_rollback_subtasks_reset`
  (`tasks_move_task.py:2102`) resets the roster as an off-axis `InnerStateChanged`
  delta (`:2186`); `tasks.md` stays byte-stable and nothing prints. The reset is
  sanctioned (#2513); the defect is the lost signal. Secondary: the roster now
  **encodes review-state but is read as work-state**. **Fix:** one
  operator-visible line on the rejection/rollback path + test. *Product decision:*
  implicit-with-refusal-message vs an explicit signal; separate work/review state?
- **#3590 (P1) — `tasks` can author a WP with no honest terminal state.**
  Action-shaped WPs produce no diff; the `for_review` gate is diff-defined
  (`for_review_gate.py:160`); `done` demands checked subtasks;
  `_ACCEPTED_READY_LANES` excludes `canceled` (`gates_core.py:52`) so `accept`
  rejects a canceled WP (#2945); `merge` does not gate the accept record (the
  de-facto escape hatch). `ExecutionMode` has only `code_change` /
  `planning_artifact` — no action/non-diff mode — and there are **two** enums
  (`ownership/models.py:21` and `mission_runtime/context.py:42`). **Largest blast
  radius.** **Recommend scoping this mission to the interim only:** `tasks` warns
  at authoring time when a WP's acceptance criteria are observable only
  post-integration; route the deep terminal-state fix to the open epic
  **#3550 / #3432 / #2945 / #2745**.

## 4. Consolidation & dedup verdict

| Issues | Verdict |
|--------|---------|
| **#3605 + #3604** | Not duplicates, but **one re-ledger unit** — co-locate, unify the emit helper, regen goldens once. #3604 additionally needs an ADR. |
| **#3596 + #3598** | Same anti-pattern, one shared ADR, two independent diffs. Plan together. |
| **#3598 reader-convergence** | Widen to canonical `_canonical_meta_mission_type` — but it changes legacy resolution → own decision, flag in spec. |
| **#3578 + #3590** | Share the operator-signal / state-model theme but are **not** duplicates — different depth. Separate WPs. |
| **#3571** | Standalone P0; same meta-pattern as A (input must reach its consumer via one seam, not a mutated proxy), different subsystem. |
| **#3590 vs #3550 / #3432 / #2945 / #2745** | Distinct trigger (authored-as-action, nothing absorbed); take only the interim here, route the deep fix to that open epic. |

## 5. Proposed mission shape & order

Cluster B runs fully parallel to Cluster A.

- **WP-A0 (tidy-first, optional):** extract the single `_emit_reference_edges`
  helper and collapse the five duplicated branches **before** A1/A2 land on top.
- **WP-B1 — #3571 (P0), first.** Red-first repro proving the lane descends from
  `--base` alone; thread base through both allocation routes; fail loud on
  unhonorable topology.
- **WP-A1 — #3605.** Route procedures through `_reference_edge_kwargs`; `reason`
  round-trip test. No regen yet.
- **WP-A2 — #3604.** ADR (relation + source node) + extractor reads
  `governance-profile.yaml`; red-first cascade coverage; **then regen goldens
  once covering A1+A2.**
- **WP-A3 — #3598.** Per-type hatch replaces the project-wide probe;
  policy-reversal ADR line; flag the meta-reader convergence as an explicit
  decision.
- **WP-A4 — #3596.** Replace the two `BOOTSTRAP_ACTIONS` gates with "grain iff
  the DRG declares the node"; thread the loaded graph; document the pack-root
  `*.graph.yaml` carrier. **Also fold the third copy of the 4-token list —
  `_KNOWN_ACTIONS` (`charter/interview.py:34`)** — so retiring `BOOTSTRAP_ACTIONS`
  does not leave a divergent sibling. (A3 and A4 are **independent diffs** — zero
  file overlap, no ordering constraint; the "adjacent files" note earlier
  overstated it.)
- **WP-B2 — #3578.** One operator-visible signal line + test (early harm-reduction).
- **WP-B3 — #3590.** Authoring-time warning only; explicitly defer the
  terminal-state fix to #3550 / #3432.

## 6. Decisions the spec must resolve

1. **#3604 ADR** — relation (`requires` vs `scope` vs new) and source node
   (`mission_type` vs each `action`); how it composes with action-grain `scope`
   (FR-004/FR-013 keep the two grains disjoint). **Code-inspection input:** `scope`
   is the lower-blast-radius relation — cascade already follows it and the two
   `mission_type` edge-count/sequence tests (`test_total_mission_type_edge_count_is_twenty_one`,
   `test_every_mission_type_edge_matches_its_action_sequence`) are `REQUIRES`-filtered,
   so they stay green; choosing `requires` forces rewriting both.
2. **#3598 reader-convergence** — adopt `_canonical_meta_mission_type` across the
   4+ readers? It changes legacy `{"mission": …}` resolution.
3. **#3590 scope boundary** — authoring-time warning only (recommended) vs the
   deep terminal-state fix (→ #3550 / #3432).
4. **#3578 shape** — implicit-with-refusal-message vs an explicit signal line;
   separate work-state from review-state?
5. **#3571** — does `--base` override coord-branch parentage, or only the branch
   the coord branch is minted from? Interaction with an already-existing coord branch.
6. **Golden re-ledger owner** — one canonical regen command, assigned to WP-A2.

## 7. Risks / blast-radius

- **Golden double-churn** — batch #3605 + #3604 into one regen (guards are whole-graph).
- **Byte-identity** — #3596 must keep all four built-ins byte-identical (its acceptance test).
- **Import-time budget** — #3596 must reuse the already-loaded graph (`test_charter_import_time_io`, ~100 ms).
- **Legacy backward-compat** — #3598 (meta-reader convergence) and #3571 (keep the legacy `mission_branch` route working) both touch legacy resolution.
- **Three `ExecutionMode` enums** (code-inspection correction, not two) — `ownership.models` (`code_change`/`planning_artifact`, the WP-authoring enum #3590 would extend), `mission_runtime.context` (effectively **dead** — no member consumers), and the external `spec_kitty_events.status` (live at `tasks_transition_core.py:229`). Narrower authoring blast radius than "two enums" implied, but the shared `code_change` token across three enums is a latent hazard → route consolidation to the open enum ticket **#3416**. #3590's interim warning needs a **net-new prose detector** (`infer_execution_mode` misclassifies action-WPs as `code_change`; hook exists at `mission_finalize.py:1253`).

## 8. Terminology to pin in the spec

`base` (WP/lane-level, not `target_branch`) · `terminal` (state-machine-terminal
vs accept-tolerable) · `mission_type` vs legacy `mission` · `scope` **edge** (DRG
relation) · `carrier` (DRG carrier / authoring surface) · `grain` (type-grain vs
action-grain). Candidate new glossary terms (curator-owned): **operator-signal
contract**, **delivery-reachability**, **DRG carrier**.

## 9. Prior-art status

Mission M5 (PR #3600) closed #2829 + #3009; **#3605 and #3604 are its
deliberately-deferred residue** (still open, genuinely unfixed). #3397 and #3386
(dependencies of #3598) are **closed**. #2945 / #3432 / #3550 / #2745 (the
terminal-state epic behind #3590) are **open** — keep #3590 scoped to its interim
so the friction mission stays bounded.

## 10. Implementation-readiness (code-inspection squad)

Three implementation-readiness audits (one per cluster) verified every fix site
against `main` and returned go/no-go plus the exact red-by-design test surfaces.

**Go/no-go:**

- **#3605 (procedure edge metadata) — GO.** 1-line fix: add
  `**_reference_edge_kwargs(ref)` to the bare `DRGEdge(...)` at `extractor.py:~900`.
  Live drop confirmed: `procedure.graph.yaml` carries 0 `reason:`/`when:` while 16
  shipped procedures author `reason:`. New test: `test_procedure_reference_reason_roundtrips`.
- **`_emit_reference_edges` (5→1 helper) — GO** for the five reference branches;
  agent-profile branches and #3604 stay separate (see §2.1 correction).
- **#3604 (governance projection) — GO** as a new `extract_action_edges`-shaped
  pass emitting `mission_type:<type> --<rel>--> <kind>:<id>`; lands in
  `mission_type.graph.yaml` only (disjoint from #3605's `procedure.graph.yaml`).
  Relation: prefer **`scope`** (zero test churn; see decision #1). Red-first driver:
  add `mission_type:plan` to `_GOVERNANCE_BEARING_MISSION_TYPE_URNS`
  (`test_cascade.py:406`); `test_plan_cascade_is_empty_…` (`:449`) flips by design.
- **Re-ledger once — mechanically TRUE.** `spec-kitty doctrine regenerate-graph`
  rewrites *all* fragments in one pass and `--check` compares the whole set, so a
  partial regen is impossible: land both extractor edits, then regen once.
- **#3596 — GO** with the byte-identity reframing in §2.2. Red-by-design:
  `test_json_non_bootstrap_action_is_explicitly_ruled_out` (`test_every_load_delivery.py:197`),
  `test_non_bootstrap_action_carries_stamped_version` (`test_context_schema_version_ledger.py:95`).
- **#3598 — GO, no blocker.** Single production caller of the project-wide probe;
  per-type filesystem probe is strictly safe. Red-by-design:
  `test_project_with_overrides_does_not_hard_fail_for_unknown_type`
  (`test_mission_type_profiles.py:260`).
- **#3596 & #3598 are independent diffs** (zero file overlap) — plan under one ADR,
  land in any order.
- **#3571 (P0) — GO.** Minimal fix: thread an explicit `base` param into
  `allocate_lane_worktree` (stop smuggling via `mission_branch`); fail loud on the
  reuse/recovery early-returns that cannot re-parent. Red-first repro harness
  already exists (`test_worktree_allocator_coord.py`) — add a divergent
  `explicit-base` branch and assert the lane descends from it alone. One architect
  decision (coord-descent vs `--base` override = decision #5). Dep-tip merge composes
  cleanly; the stale docstring at `worktree_allocator.py:450-453` needs correcting.
- **#3578 — GO.** Signal site is `_mt_output` (`tasks_move_task.py:2354-2402`); wire a
  `subtasks_reset_count` field through `_MoveTaskState`. Two more silent mutations at
  the same rollback site (`release_runtime_claim`, review-override clear) should be
  surfaced together.
- **#3590 — GO on the interim only.** `merge` not gating the accept record is
  confirmed (the escape hatch). The authoring-warning needs a net-new prose detector
  (see §7).

## 11. Expanded scope (related-issues discovery squad)

Two discovery sweeps (broad tracker + structural-signature) found this is **not a
7-issue class but a standing repo-wide disease** with existing homes:

- **Reframe under epic #3410** *"Charter/doctrine silent-drop — must fail loud,
  never fake-green"* (the B1 umbrella; already owns the vocabulary — cite it and
  **#3549** rather than minting `operator-signal contract`). Tracking issues
  **#3530** (org-tier reach) and **#3550** (WP-retirement lifecycle) aggregate more
  siblings; mine them.
- **Low-cost FOLD candidates** (same seam/ADR, small): **#3548** (`_fail()` drops
  message, 16 sites), **#2991** (finalize-tasks drops `SC-###`), **#3407** (hardcoded
  `software-dev` guard — twin of #3598), **#3122** & **#3029** (override written to
  one field, read from another — twins of #3571), and **#2477–#2480** *iff* the
  meta-reader convergence (decision #2) is taken.
- **New UNTICKETED latent defects** (found in code, no tracker entry):
  - **`_KNOWN_ACTIONS` (`charter/interview.py:34`)** — a *third* copy of the 4-token
    action allowlist; silently globalizes `tasks`/`research`/`documentation`-scoped
    supporting files → **fold into #3596** (§5).
  - **`_DRG_NODE_KINDS` (`charter/synthesizer/topic_resolver.py:37`)** — a
    hand-copied `NodeKind` list that has **already drifted** (9 of 16 kinds; missing
    `mission_type`, `glossary_pack`, …), silently failing DRG-URN resolution for
    those selectors. Separate one-line fix (derive from `NodeKind` + drift guard).
  - **Agent-profile `context-sources.tactics` unprojected** in the extractor —
    latent (currently masked by a subset relation to `tactic-references`).
- **FOLLOW-ON, plan-adjacent:** **#3599/#3597** (closed-set artifact gate — pair with
  #3596), **#3488** (3-of-5 profile selector kinds deliver nothing — the delivery-seam
  twin of #3605; plan alongside the emit-helper or they re-diverge), **#2992/#3412/#3261**
  (charter B1), **#3061** (`action:plan/*` zero artefacts), **#2901** (WP-frontmatter
  N-reader — pairs with #3598 convergence), **#3016** (accept hardcodes `src/`),
  **#3460/#3462/#3536** (the coord two-route seam — the architectural home for #3571's
  recurrence-prevention, epic-sized, cite don't fold).
- **Meta.json mission-type reader census is ~10–12**, not "4+": four silent
  `software-dev` defaults plus a legacy-`mission`-only dashboard reader. Converging on
  `mission.py:_canonical_meta_mission_type` changes legacy `{"mission": …}` resolution
  across dashboard/retrospective/interview — do it in **explicit, per-reader,
  test-pinned steps**, never a blanket sweep.
- **Do NOT fold — sequence to #3550:** the terminal-state family
  **#3432/#3433/#2745** (consistent with the #3590-interim call in §3).

## See also

- [Investigations home](index.md)
- [Delivery-reachability wiring table](../doctrine/delivery-reachability-wiring-table.md)
- [Mission-type resolution](../../architecture/mission-type-resolution.md)
- [Execution lanes](../../architecture/execution-lanes.md)
