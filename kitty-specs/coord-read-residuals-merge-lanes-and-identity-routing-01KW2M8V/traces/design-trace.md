# Design Trace — coord-read-residuals-merge-lanes-and-identity-routing-01KW2M8V

**Purpose:** a running log of the design decisions and their rationale — the "what the fix
looks like and why" record. Seeded at spec→plan; **append during implement**; assessed at close.

> Format per entry: `[date] [phase] DECISION — rationale — evidence/constraint`

---

## Seeded during spec → plan (2026-06-26)

1. **[spec] Route by the REAL artifact-kind partition, not the issue labels.** The fix re-points
   each site to `resolve_planning_read_dir(kind=<real kind>)`. The issues mislabel 6 of 10 Lane A
   sites — `merge/resolve.py:98`, `cli/commands/merge.py:269`, `lanes/worktree_allocator.py:360`
   read `meta.json` (PRIMARY_METADATA) not LANE_STATE; `lanes/recovery.py:611` reads `lanes.json`
   (LANE_STATE) not `tasks/`. Evidence: debugger lens verified each against `is_primary_artifact_kind`.

2. **[spec] Per-leg split for mixed PRIMARY+STATUS sites; STATUS stays coord-aware (C-001).**
   `merge/executor.py` (`feature_dir`→`run.feature_dir`→`status_feature_dir` at `:503`/`:560`),
   `merge/done_bookkeeping.py:237` (WP-path leg only; status-transactional legs stay on the
   meta-bearing primary dir), `lanes/recovery.py:356` (lanes/tasks → PRIMARY; events leg coord-aware).
   Rationale: collapsing both legs onto PRIMARY would break status semantics. Constraint: NFR-001.

3. **[spec] Lane B builds a NET-NEW command-layer identity-read scan arm — not a pin drain.**
   The existing scanner matches only `resolver / "tasks"|"lanes.json"|"*.md"` dir-joins and is
   structurally blind to `resolve_mission_identity(dir)` / `get_mission_type(dir)` function-call
   reads. So #2186 has no inherited pin; the detector + remediation co-land here, validated by a
   committed synthetic-AST non-vacuity self-test + a pre-merge full-gate dry run (gate-can't-
   self-validate). Arm scoped to `cli/commands/` to avoid red-CI on out-of-scope strangers
   (~41 identity sites repo-wide; sync/acceptance/policy/orchestrator_api are follow-on).

4. **[spec] Divergent-husk integration fixture (the squad's CRITICAL fix).** `build_coord` as-is
   writes `meta.json` to main before the worktree add → byte-identical husk meta → identity reads
   pass regardless of routing; and it seeds no `lanes.json`/`tasks/` anywhere. FR-009 requires a
   **divergent** husk: sentinel coord `meta.json` (≠ PRIMARY) + PRIMARY-only `lanes.json`/`tasks/`
   seeded post-worktree-add, asserting the husk lacks them — so reverting a routed read to
   coord-aware observably fails. Evidence: reviewer lens, `topology_fixtures.py:199-218`.

5. **[spec] `next_cmd.py:631` is routing, not telemetry.** `get_mission_type` husk-miss returns the
   default `software-dev` (no raise) → `get_or_start_run` starts the wrong run type. Higher impact
   than the `:187`/`:253` silent lifecycle-record drops. Evidence: `mission.py:574-575`.

6. **[spec] Consume the resolver seam, never author it (C-002); guards precede fallback removal
   (C-EXCL-FALLBACK).** Every fix is a call-site swap; `_read_path_resolver` internals are untouched.
   `implement.py:1389` gets its own primary anchor so it survives the eventual removal of the
   `:1018` fallback — but this mission does NOT remove that fallback (separate follow-on).

7. **[plan/brownfield] Deferred the `primary_read_dir` shared seam — consume, don't dedup here.**
   Brownfield scan found the two-call PRIMARY idiom inlined at ~12 sites + 3 duplicate
   `_planning_read_dir` wrappers — a real dedup opportunity. Deferred to a separate follow-on
   (cousin of #2100): it tension-conflicts with C-002 (consume-not-author the resolver), straddles
   the implement-loop sibling's owned `workflow.py`/`implement.py` legs, and is broader than
   #2185/#2186. This mission consumes the existing `resolve_planning_read_dir` seam only.
   But: converge the one in-scope split-brain pair — thread `executor.py:887`'s PRIMARY dir through
   to `:976` instead of recomputing coord-aware. Guardrail: `candidate_feature_dir_for_mission` is
   the C-005 STATUS primitive — never removed/"converged away".

## Appended during implement (2026-06-27)

8. **[rescope] The #2185 "permanent ratchet vocabulary gap" was NOT permanent.** The literal-ban scanner is blind to `lanes.json`/LANE_STATE — everyone (including the original plan) treated that as immovable and leaned on the fixture alone. alphonso found the lanes.json reads are a `read_lanes_json(dir)`/`require_lanes_json(dir)` **call-shape**, identical in form to the `resolve_mission_identity(dir)` reads the identity arm already targets. Design: ONE unified call-shape arm covering BOTH shapes (identity scoped `cli/commands/`+`agent_utils/status.py`; lanes.json scoped `merge/`+`lanes/`+`core/`). Static gate > fixture-only.

9. **[rescope/fixture] `build_coord` false-green confirmed; sentinel-meta divergence is the cure.** `write_side/topology_fixtures.py::build_coord` materializes the husk via `git worktree add` off a branch that already carries the mission dir → the husk MIRRORS primary (same meta/lanes/tasks) → a broken coord-read passes silently. Cure: reuse the genuinely-divergent `tests/integration/coord_topology_fixture.py` (STATUS-only husk) + add a **sentinel-husk-meta variant** — husk `meta.json` PRESENT-but-WRONG (sentinel `mission_id` ≠ `ctx.mission_id`), so an identity regression yields a silent WRONG VALUE (matching the bug), not a raise. Hard preconditions assert the husk lacks `lanes.json`+`tasks/` and meta==sentinel. The revert-fails terminal MUST assert a RETURNED domain value; the fixture's `assert_reads_primary`/`assert_both_legs` path-equality helpers are BANNED as the terminal.

10. **[rescope/deps] Dependency inversion fixed — WP01 owns the shared fixture.** The sentinel-divergent fixture is consumed by both Lane B (identity tests) and Lane A (per-site tests); a fixture consumed before it is built is the highest-probability false-green path. Design: WP01 (deps `[]`) owns the fixture extension; WP02→WP01→…→WP04 all depend on it. One divergence definition, no inline drift.

11. **[rescope CORRECTION to entry 7] `executor.py:887`→`:976` is NOT a thread-through — they are different functions.** Re-verified on merged main: `:887 primary_feature_dir_for_mission` lives in `_run_lane_based_merge_locked` (def `:866`); `:976 candidate_…` lives in `_run_lane_based_merge` (def `:947`). The planned "thread `:887`'s PRIMARY dir to `:976`" is impossible across the function boundary. Corrected design: route `:976`'s legs DIRECTLY per-leg (`:981/:1003` resolve_mission_identity→META, `:997` require_lanes_json→LANE_STATE); keep `run.feature_dir` STATUS leg coord. Also: `lanes/recovery.py:664` is an UNCITED STATUS-write leg (feeds `emit_status_transition_transactional`) → the C-001/#2155 analog, explicit KEEP.

12. **[impl WP01] Floor census genuinely MOVED (real gain, not a re-pin).** The 7 routed identity anchors use the DIRECT `primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))` primitive (which the canonicalizer census counts), not the seam → CANONICALIZER 38→45 / ROUTED 35→42 → `CANONICALIZER_FLOOR` 38, `ROUTED_CANONICALIZER_FLOOR` 38 (live 42 − margin 4). Routing the coord-authority-censused identity sites (`implement:1283`/`review:2739`) out of coord shrank `COORD_AUTHORITY_WRITE_FLOOR` 15→13 (claimed legit — identity reads, not status writes; under C-001 review verification).

<!-- append during implement: per-site route deltas, the ROUTE/KEEP ownership table outcome,
     any kind re-classification found mid-implementation, floor recompute census. -->

## Close-out assessment (2026-06-27)

Final design realized + proven: **kind-aware read seam** (PRIMARY kinds routed topology-blind; STATUS stays coord — C-001 held across all 8 routed sites) + **dual-shape live call-shape arm** (the static ratchet that closed the literal-ban vocabulary gap for lanes.json/identity) + **divergent sentinel fixture** (the behavioral backstop, proven falsifiable). Floor honesty held (only WP01's 7 direct anchors moved the census; seam-routes didn't — stated, never re-pinned). Late lesson (entry 11 cousin): the `done_bookkeeping:428/:430` "new sinks" were **line-drift of the existing :419/:421 inventory rows** (a merge inserted 9 lines above the helper) — bisect against upstream/main before assuming a sink is new, or you double-count. The contracts/ doc (`seam-and-gate-contracts.md`) captures all four contracts for the next maintainer.
