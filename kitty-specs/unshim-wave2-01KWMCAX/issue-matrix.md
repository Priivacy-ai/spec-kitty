# Issue Matrix — unshim-wave2-01KWMCAX

<!-- Schema: issue | title (optional) | verdict | evidence ref (mandatory) -->
<!-- Valid verdicts: fixed | verified-already-fixed | deferred-with-followup | in-mission -->

| Issue | Title | Verdict | Evidence ref |
|---|---|---|---|
| #2291 | closes: execute registered removals (specify_cli.next + glossary) | fixed | DONE (WP01-WP04, all reviewer-verified): 3 src callers + seam re-pointed (e2ad484ef), 71-file test surface re-pointed with 163 ledgered interception proofs (1c51f6733, 5e7ddaab1), both shims deleted + registry drained to shims:[] + schema presence-asserts converted to absence pins in atomic 6cf0d4e99. PR closes. |
| #2290 | closes: charter deprecation-cycle closure | fixed | DONE (WP05-WP06, reviewer-verified): 4 src callers re-pointed incl. runner.py:36 canonical→legacy defect fix (76799e749), 20 test files + 32 ledgered proofs, 3 shim packages deleted + lock-gate retired with 6-row disposition table + test_canonical_paths_import re-homed (d435ad6a1); charter_activate settled CANONICAL (documented-excluded). PR closes. |
| #2326 | closes: dead frontmatter::update_field wrapper | fixed | DONE (WP07, reviewer-verified): wrapper + __all__ + orphaned instance method deleted with zero-external-caller evidence; :235 row drained; category_b honest re-derive 216→215 (0e3d64e60). PR closes. |
| #1868 | partial: WS1 mission_runtime layer-rule bind | deferred-with-followup | WS1 delivered via sub-issue #2327 (WP08); WS2–WS6 remain OPEN under #1868 (the follow-up). |
| #2327 | closes: WS1 mission_runtime layer-rule bind (sub-issue of #1868) | fixed | DONE (WP08, reviewer-verified): outbound LayerRule with 9-subpackage allowed-exception ledger + committed CI-selected negative test + shrink-only stale-entry guard (0f3a16877); evidence comment posted (issuecomment-4878911580). PR closes. |
| #1797 | parent epic (unshim cluster) | deferred-with-followup | Epic stays OPEN — Wave 2 is one slice; follow-up is #1797 itself (Wave 3+: #2293 burn-down, remaining shim families). Progress comment at merge: registry drained to zero legacy rows, 5+ shim surfaces deleted, honest baseline counts. |
| #612 | closed antecedent (next-extraction ticket, parent #391) | verified-already-fixed | CLOSED 2026-06-01; Wave 2 completes the deletion it registered. PR body references, never re-closes. |
| #613 | closed antecedent (glossary-extraction ticket, parent #391) | verified-already-fixed | CLOSED 2026-06-01; Wave 2 completes the deletion it registered. PR body references, never re-closes. |
| #391 | debt epic (parent of #612/#613) | deferred-with-followup | Referenced lineage only — remainder of the extraction-debt epic continues under #391; nothing in Wave 2 closes it. |
| #2072 | Obligation B boundary | deferred-with-followup | Obligation B (~10 resolver sites) is NOT in any Wave 2 surface (verified); stays open under #2072; operator note on #2293's prerequisite semantics posted at closeout (FR-010). |
| #2293 | boundary: category_b burn-down (later wave) | deferred-with-followup | Stays OPEN as the follow-up wave; needs #2072 formal closure or operator prerequisite confirmation; Wave 2 hands it honest baselines (WP07). |
| #2034 | CI marker-gate hole | deferred-with-followup | Follow-up: #2034 stays OPEN upstream; honored in-mission as the NFR-005 obligation (new/relocated tests carry CI-selected markers — proven for WP08's three new tests). |
| #2159 | reference: uv_receipt trap (closed) | verified-already-fixed | Lesson encoded as C-001 (re-point before delete); no structural constraint. |
