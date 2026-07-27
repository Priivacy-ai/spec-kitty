# Issue matrix — wp-runtime-state-eviction-01KXWN13

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2684 | Evict runtime-mutable WP state into the event log (mission execution vehicle) | fixed | Event infra + dual-write behind `_phase1_dual_write_enabled` (default OFF) landed across WP01–WP10; FR-001/002/003 proven (WP01 de458f935, regression red test green for the reduced-snapshot mechanism). Dual-write end-state; corpus cutover deferred to follow-up **#2816** (tasks.md deferred note / WP10 RE-SCOPE banner). |
| #2093 | Authority ruling that #2684 executes | fixed | FR-013 arch invariant enforced at flag ON: `tests/architectural/test_2093_authority_invariant.py` (WP10 228950996) asserts no dynamic frontmatter field is read as authority and no field is dual-homed, with `_phase1_dual_write_enabled` as the SOLE tolerated migration gate. Flag-ON scope; the unconditional (empty tolerated set / post-cutover) form is deferred with the corpus cutover (**#2816**). |
| #2736 | Operator friction / force-provenance context (catfooding) | fixed | FR-015 landed + tested: `tests/regression/test_2684_force_provenance.py` (WP02 2ae3720fc) asserts persisted `StatusEvent.force` falsy for the five evidence-gated edges. |
| #2810 | Confirmed force-provenance corruption bug (PR) | fixed | FR-015 fix carried and proven: persisted-force regression green + genuine-force positive control truthy (WP02 2ae3720fc, WP06 two in_review edges). |
| #2647 | Off-axis emit site must not resolve its write target from Path.cwd() | fixed | SC-008 destination_ref invariant proven: `tests/integration/test_sc008_topology_resolution.py` (WP08 781e6d151) — genuine worktree fixture, emit destination derives from stored topology, red against a Path.cwd()-derived resolution. |
| #2160 | implement.py shell_pid-writer restructuring (external writer work) | deferred-with-followup | spec.md FR-014 / C-006: #2160's writer work is pr:deferred and yields; rebases onto this mission |
| #1619 | Static-model authority election | deferred-with-followup | spec.md C-005: out of scope, deferred / gated on this landing. Follow-up: #1619 |
| #2686 | Semantic-only content-hash slice | deferred-with-followup | spec.md C-005: out of scope. Follow-up: #2686 |
| #2641 | Deferred PR yielding to this mission | deferred-with-followup | spec.md C-006: yields to and rebases onto this mission. Follow-up: #2641 |
| #2766 | Deferred PR (merge-ordering rebase note) | deferred-with-followup | spec.md C-006 / §243: writer-cutover WP carries rebase note against PR #2766. Follow-up: #2766 |
| #2612 | Deferred PR yielding to this mission | deferred-with-followup | spec.md C-006: yields to and rebases onto this mission. Follow-up: #2612 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
