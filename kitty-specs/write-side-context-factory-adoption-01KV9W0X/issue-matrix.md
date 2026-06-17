# Issue matrix — write-side-context-factory-adoption-01KV9W0X

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.
Pre-filled from the spec Tracker table at planning time (renata B-1); `in-mission` rows MUST reach a terminal
verdict before mission `done` (driven by WP08 — see its DoD).

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1716 | coordination topology authority (write-side) | fixed | bounded root/placement/surface/target slice landed — WP02/WP04/WP05/WP06; keystone proves the flat collapse (`tests/specify_cli/coordination/test_simple_case_flat_topology.py`) + ratchet enforces no write-side re-derivation (`tests/architectural/test_no_write_side_rederivation.py`). DEFERRED residuals (C-003, NOT in this slice): the S2 write-surface-SELECTION ladder AND the `BookkeepingTransaction` legacy-override on `git symbolic-ref HEAD` (`coordination/transaction.py::_resolve_legacy_lane_destination`) — the latter only diverges from `target_branch` under topology divergence (HEAD≠target_branch), NOT in the genuine NFR-006 simple case (HEAD==base), so NFR-006 holds. Follow-up: #1716 |
| #1878 | complete coordination placement/identity strangler (post-3.2.0) | deferred-with-followup | finalize/merge ff-advance bookkeeping = later focus (spec Out of Scope); Follow-up: #1878 |
| #1619 | unify execution context / runtime-state SSOT (epic) | fixed | fragment resolvers now load-bearing via shared-resolver routing (SC-002) — WP02/03/05/06; keystone asserts every adopted fragment resolves to base in the flat case (`test_simple_case_flat_topology.py::test_flat_every_adopted_fragment_resolves_to_base`). Epic continues beyond this increment; Follow-up: #1619 |
| #2016 | orchestrator coord-read identity bootstrap | verified-already-fixed | Mission A WP09 `d4f0cf581` (`commands.py:282-311`); cross-ref, not re-fixed (D-3) |
| #1993 | extract `resolve_lanes_dir()` seam + lanes/coord adoption | fixed | seam done by Mission A (`persistence.py:23`); FR-008 lanes/coord adoption = WP06; keystone pins the flat-arm lanes-dir under the primary specs root (`test_simple_case_flat_topology.py`) + WP01 net pins the coord arm |
| #2000 | route remaining `<slug>-<mid8>` composes through canonical seam | verified-already-fixed | naming-rider #2012 (ratchet flags zero offenders); closes on #2015 merge |
| #2015 | Mission A — read-path-error-fidelity (stacked base / frozen factory seam) | verified-already-fixed | PR #2015 (green/CLEAN); this mission stacks on it (C-002) |
| #2007 | epic: 3.2.0 training bugs (architecture alignment) | deferred-with-followup | epic advanced (Robert rule #2 = this #1716/#1878 step); children tracked separately |
| #2010 | [2007/C3] read-path resolver unification (P0) | verified-already-fixed | delivered by Mission A; closes on #2015 merge (spec note) |
| #2011 | [2007/C6] submodule/root detection hardening (P0) | verified-already-fixed | delivered by Mission A; closes on #2015 merge (spec note) |
| #1832 | single-resolution adoption | verified-already-fixed | delivered by Mission A (spec #2007-alignment note) |
| #2012 | naming/identity routing rider (PR) | verified-already-fixed | merged to upstream/main; cited as recurrence/context |
| #2004 | Robert CI-hardening / architecture-alignment (PR) | verified-already-fixed | merged; pre-validates the write-side direction (spec note) |
| #1970 | Doctrine: campsite-cleaning / Fix-don't-litigate | deferred-with-followup | operationalized as C-008 (BINDING) in every WP prompt; doctrine ref, not a code fix here; Follow-up: #1970 |
| #2017 | Investigate: workflow guards lacking depth | deferred-with-followup | running guard-friction trace; meta investigation, not fixed by this mission; Follow-up: #2017 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
