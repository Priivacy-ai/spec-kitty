# Post-Tasks Brownfield Review Squad — findings & dispositions

**Point-cut:** post-tasks (anti-laziness / decomposition-realism / scope). **Date:** 2026-08-23.
**Squad (profile-loaded, read-only):** reviewer-renata, paula-patterns, planner-priti.
Verdicts: renata APPROVE-WITH-MINOR; paula REQUEST-CHANGES (1 structural); priti
REQUEST-CHANGES (clean-PR blockers). All findings verified against the tree.

| # | Finding (evidence) | Lens | Sev | Disposition |
|---|--------------------|------|-----|-------------|
| G1 | **WP03 org-tier raise can't live in `org_pack_loader.py`.** `merge_three_layers` (`merge.py:1185-1194`) **warns, not raises** on dangling org endpoints by design; the escalation home is `validator.validate_dangling_references`. A pre-merge single-pack guard can't see built-in targets → false positives. | paula | HIGH | **accepted** → WP03 owns `validator.py` (governance-scope escalation following the documented pattern) + `org_governance.py` (extraction); the **invocation** is post-merge at WP04's two callers. WP04 now **depends on WP03** and invokes the guard. Chain WP03→WP04→WP05. |
| G2 | WP03 T014 "mirror `_GOVERNANCE_PROFILE_SCOPE_FIELDS`" = a **new hand-copy** of an SSOT (ironic vs WP01). | paula | MED | **accepted** → **import** `_GOVERNANCE_PROFILE_SCOPE_FIELDS` from `extractor` (a read, not an edit) instead of copying; if it must stay private, add a C-009 drift-guard parity test. |
| G3 | Spec still frames #3629 p2 as "verify-and-close" while WP03 builds a **net-new** org-tier path. | priti | HIGH | **accepted** → reframe spec User Story 2 (org-tier = implement, not verify); disclose in the #3629 close comment that org-tier governance fail-loud was net-new here. |
| G4 | **Missed WP02 consumer**: `tests/doctrine/fixtures/valid-profile.agent.yaml` authors `context-sources` (loaded by `test_profile_schema_validation.py`, `test_doctor_doctrine.py`) → silent integration red after removal (violates FR-006). `tests/specify_cli/bulk_edit/test_occurrence_map_field_paths.py` uses the field-path as a literal. | priti | MED | **accepted** → add the fixture to WP02 `owned_files` + a T010 sub-bullet; verify/adjust the occurrence-map test; fold F15 doc/example hygiene into WP02. |
| G5 | **Migration filename `m_3_2_6_*` mis-ordered** — `m_3_2_7`, `m_3_2_8`, `m_3_3_0` already shipped (version `3.2.6rc3`). | priti | MED | **accepted** → rename to the next unreleased version (`m_3_3_1_context_sources_consolidation.py`) after confirming the runner's ordering/idempotency; align with the version bump. |
| G6 | **DIR-009 gap** — no CHANGELOG entry / version-bump task for a breaking schema removal. | priti | MED | **accepted** → add CHANGELOG (breaking-change + migration pointer) + version bump to WP02 DoD. |
| G7 | WP01 T002 **tautology fallback** re-introduces the F7 anti-pattern; T003 carries real acceptance. | renata | MED | **accepted** → delete the fallback; T003 (each dropped kind resolves) is the acceptance; note FR-002's literal wording is superseded by the behaviour pin. |
| G8 | WP03 T013 mischaracterized as red-first — the built-in guard already passes; it's a **characterization pin**. | renata | LOW | **accepted** → reword T013 + the tasks.md "each WP red-first" blanket. |
| G9 | Stale citations: `load_org_drg` **not** imported at `executor.py:21` (add to the `charter.drg` import ~`:23`); pedro→034 SUGGESTS edge is ~`hand_authored_overlay.py:1674`, not `:585`. | renata | LOW | **accepted** → fix both citations in WP04 / WP02. |
| G10 | WP05→WP04 correct; WP05→WP02 / WP05→WP03 **not** needed (T024 misconfigs are org-fragment faults, not governance `selected_*`; fixtures carry none). | paula, priti | INFO | **accepted (guard)** → add a WP05 note: fixtures MUST carry no governance `selected_*` (else WP03's guard raises). |
| G11 | WP02 core (model+profile+golden) is legitimately **atomic**; T007+T012 optionally sheddable — not required. | paula | INFO | **noted** → keep WP02 atomic; state "cannot split removal↔migration↔regen triad". |
| G12 | #3514/#3511/#3412 exclusions correctly held; overall scope coherent (expansions traceable to squad findings + operator decisions), not sprawl. | priti | INFO | **noted** — no action. |
| G13 | authoritative_surface nits: WP03 → `org_governance.py`; WP02's true hotspot is `extractor.py`; WP04 omits the charter caller (all prefix-valid). | paula | LOW | **accepted (partial)** → retarget WP03 authoritative_surface to `org_governance.py`; WP02/WP04 left (prefix-valid). |

## Net structural change

`WP03 → WP04 → WP05` (was: WP01–04 all parallel, WP05→WP04). WP03 gains
`validator.py`; WP04 gains a dependency on WP03 + a guard-invocation subtask; WP02
gains the missed fixture consumer + CHANGELOG/version + a corrected migration name.
No ownership overlap after the change (re-validated via finalize-tasks).
