# Issue matrix — gate-read-surface-completion-01KVW9B0

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.
WP10 closeout (T034): every referenced issue carries a TERMINAL verdict (no `in-mission`),
with behavioral evidence, not "code looks fixed".

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2107 | setup-plan + accept gate reads on protected-primary/coord topology (driver) | fixed | WP02 `setup_plan` reads PRIMARY for spec (test_setup_plan_read_surface.py) + WP03 accept-gate planning split (2b63b7559) + WP00 write foundation (3a16473a2). Behavioral two-surface net green: `test_two_surface_seam_across_commands` + `test_accept_gate_reads_primary_planning_and_coord_status` (tests/missions/test_gate_read_two_surface_behavioral.py) — RED-first proven (reverting the seam to the topology resolver turns both the net AND the real accept entry point RED). |
| #2085 | acceptance-matrix gate / accept facet (finalize-tasks COMMIT misresolves protected primary) | fixed | WP00 (3a16473a2): resolve_placement_only / get_feature_target_branch / resolve_target_branch re-pointed onto primary_feature_dir_for_mission; coord-topology RED→GREEN (test_write_surface_resolver_foundation.py, test_finalize_tasks_commit_surface.py). Cross-command write-twin asserted on the two-surface fixture: `test_write_twin_resolves_target_branch_not_main` + anti-mutant `test_write_twin_anchors_on_primary_not_candidate`. |
| #2102 | record-analysis dirty-tree allowlist + bookkeeping commit-home | fixed | WP05 (c8ee1bd9f): self-bookkeeping allowlist (FR-003), DISJOINT from coord-residue. G-5 invariant: preflight does NOT block on meta.json/provenance but STILL blocks on stale primary spec.md — `test_record_analysis_allowlist_and_g5_dirt` (behavioral net) + test_self_bookkeeping_allowlist.py. WP04 double-resolution collapse fenced by AST dedup guard (test_record_analysis_double_resolution.py) + WP06 ratchet. |
| #2091 | `next` malformed coord branch (empty mid8) — lock the fix with a scenario-driving guard | verified-already-fixed | WP07 (06f682935 spec fold + regression-guard tests): FR-006 product guard; reverting the guard turns the new guard RED (per contracts/gate-read-seam.md anti-mutant arm). |
| #2088 | ownership-overlap validator dependency-exemption — lock the fix with a guard | verified-already-fixed | WP08 (06f682935 + guard tests): FR-007 dependency-exemption guard; reverting the product guard turns the new guard RED. |
| #2074 | CT3 test-factory drift — `test_mid8_direct_routing` instance (FR-008) | fixed | WP09 (42b956e40): the `test_mid8_direct_routing` instance fixed via a production-shaped `meta.json` fixture; broader factory-delegation work stays with #2074. |
| #2100 | residual inline meta-reader sweep (in-mission scope only) | deferred-with-followup | WP05 in-mission meta-reader sweep (FR-005, c8ee1bd9f + test_meta_reader_sweep.py) — touched modules only. The broader 62-site backlog is OUT OF SCOPE and remains deferred under the #2100 follow-up; this mission swept only the modules it touched. |
| #2106 | FR-008 protected-primary guard (preserved, not the bug) | verified-already-fixed | The protected-primary guard is preserved byte-for-byte by WP00 (3a16473a2 re-points the write-branch RESOLUTION, never the guard). The mission fixes the RESOLUTION-to-main bug, not the guard. |
| #2109 | gate-read-surface mission spec/intake reference | fixed | Mission scoped + delivered (this mission). Closeout net green; no residual. |
| #1716 | epic — coordination topology coherence (write-surface coherence) | deferred-with-followup | Read seam (resolve_planning_read_dir kind-aware split, WP01 cbeb9ed48) + write twin (WP00) adopted across all gate commands; closeout two-surface net pins both partitions. Epic carries forward (remaining write-path sites tracked by #1716 cluster). |
| #1718 | C-005 KEEP transient — coord create-window | deferred-with-followup | Preserved unchanged by the read seam: STATUS-partition reads keep candidate_feature_dir_for_mission and ALL C-005 transients (resolve_planning_read_dir docstring; test_gate_read_chokepoint.py). No regression; epic carries forward. Follow-up: #1716. |
| #1848 | C-005 KEEP transient — coord-deleted | deferred-with-followup | Same as #1718: the STATUS read path retains the #1848 coord-deleted transient; the mission only re-partitioned PRIMARY-kind reads. Epic carries forward. |
| #1868 | epic — canonical seams / mission identity (mid8 routing facet: FR-006/FR-008) | deferred-with-followup | WP07/WP08/WP09 (FR-006/FR-007/FR-008) lock the mid8-routing facet with regression guards; production-shaped `<slug>-<mid8>` ULID fixtures throughout. Epic carries forward. Follow-up: #1868. |
| #1878 | umbrella — coordination placement/identity strangler | deferred-with-followup | The gate-read read+write seam is another strangler increment onto the single primary/status partition authority (mission_runtime.artifacts). Umbrella carries forward. Follow-up: #1878. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `relates / instance-fixed`, `partial / deferred-with-followup`, `regression-guarded`, `advances` (epic/umbrella increment — terminal for this mission's contribution). `in-mission` is NOT a terminal verdict and must NOT appear at mission `done`.

---

## WP10 closeout — full `tests/architectural/` arch-gate sweep (T033)

Sweep run on the consolidated lane state (`feat/gate-read-surface-completion`,
mission base `ea7dc75c5`): **`pytest tests/architectural/ -q` → 489 passed, 0 failed**
after remediation (initial run: 486 passed, 3 failed — all three adjudicated
MISSION-INTRODUCED and fixed in-mission; verified by base-compare). The FR-010
literal-ban ratchet (WP06, `test_gate_read_literal_ban.py`) and the terminology
guard (`test_no_legacy_terminology.py`) are BOTH green.

### Per-failure adjudication (post-merge cumulative gate debt)

Three architectural-gate failures surfaced on the merged state; all three adjudicated
**MISSION-INTRODUCED** via base-compare (each PASSES on mission base `ea7dc75c5`, FAILS on
feat) and fixed conservatively in-mission:

- **`test_mission_runtime_surface.py::test_public_surface_matches_contract`** —
  MISSION-INTRODUCED. WP05 added `is_self_bookkeeping_path` to `mission_runtime.__all__`
  (a legitimate package-root public predicate, FR-003). Remediation: updated the surface
  contract baseline `_PUBLIC_SURFACE` to include it.
- **`test_untrusted_path_containment.py::test_audit_passes_on_fixed_tree`** —
  MISSION-INTRODUCED (benign line drift). WP00's finalize-tasks re-point extracted
  `_collect_finalize_artifacts`, drifting the existing dossier sink `mission.py:317→318`
  (same `mission_slug` join, same `.kittify/dossiers/<slug>/snapshot-latest.json`, same
  `routed-through-seam (TODO)` disposition). Remediation: updated the inventory.md locator
  + drift provenance.
- **`test_untrusted_path_containment.py::test_all_discovered_rows_appear_in_inventory`** —
  MISSION-INTRODUCED (same `:317→:318` drift). The undercount tripwire required the moved
  locator. Remediation: the same inventory.md update.

No GENUINELY pre-existing arch-gate debt surfaced; no burn-down ticket required.
All three were this mission's own diff (exported-API addition + line drift of an
already-dispositioned sink), fixed conservatively in-mission per the post-merge
arch-gate adjudication standing memory.

---

## Process finding — lane-merge data-loss (closeout lesson)

The lane-d integration merge `32eb6df89`
("integrate WP01+WP02+WP03 code from lane-d") **silently dropped WP02's product
fix** during the cross-lane merge. The loss was NOT caught by per-WP review (which
ran on the lane in isolation) — it was caught by the **WP06 FR-010 literal-ban
ratchet** when the consolidated state was checked, and the WP02 product fix was
restored.

Lesson (folds into the existing post-merge arch-gate / lane-merge-data-loss
memory): a cross-lane integration merge can silently drop a previously-approved
product fix; the per-WP approval gate does NOT protect against it. The defenses
that DID work were the architectural ratchet (WP06) and this WP10 consolidated
two-surface net — both run on the MERGED state, not per-lane. Standing
recommendation: always run the full architectural sweep + a consolidated
cross-command behavioral net on the integrated lane before PR, and treat any
ratchet trip during integration as a candidate data-loss signal, not just a line
drift.
