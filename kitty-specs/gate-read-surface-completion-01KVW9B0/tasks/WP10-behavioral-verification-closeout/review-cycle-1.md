---
affected_files: []
cycle_number: 1
mission_slug: gate-read-surface-completion-01KVW9B0
reproduction_command:
reviewed_at: '2026-06-24T17:20:38Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP10
review_artifact_override_at: "2026-06-24T17:25:44Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP10"
review_artifact_override_reason: "Arbiter approve: substance validated cycle-1; format+verdict-vocabulary+follow-up-handles fixed"
---

# WP10 Review — REJECT (single blocker: issue-matrix fails the mission's own format gate)

## Summary

Substantively the WP is excellent: the behavioral two-surface net is genuinely
non-vacuous (I reverted a production read site myself and it went RED, including
the real accept entry point — see below), the flattened regression is real, the
full arch-gate sweep re-runs green at 489/0, both fixture updates are
mission-introduced-and-correct, and the issue-matrix verdicts are all terminal
with strong evidence.

**ONE blocker prevents `approved`:** the `issue-matrix.md` artifact fails the
mission's OWN accept-gate validator. `spec-kitty agent tasks move-task ... --to
approved` rejects with:

```
ERROR: issue-matrix.md has unresolved entries. Fill in verdicts before approving.
- issue-matrix.md contains 2 Markdown tables; exactly one is allowed.
```

The verdicts are NOT actually unresolved — the validator's "unresolved" message
is a downstream symptom of it parsing the WRONG (second) table. The root cause is
the **second Markdown pipe-table** you added for the per-failure arch-gate
adjudication (the `| Failing test | Verdict | Base-compare evidence |
Remediation |` table at ~line 39). The FR-037 gate enforces **exactly one**
Markdown table in `issue-matrix.md` (the issue table). The closeout WP must pass
the mission's own gate, so this is DoD-blocking.

## Required fix (do NOT change any verdict)

Keep the single issue table (rows #2107…#1878) exactly as-is. Re-render the
**per-failure arch-gate adjudication** section as something that is NOT a second
Markdown pipe-table — e.g. a bullet list (one bullet per failing test:
`- test_… — MISSION-INTRODUCED — base-compare: passes on ea7dc75c5, fails on
feat — remediation: …`) or prose. Do the same for the lane-merge data-loss
"Process finding" section if it parses as a table. Re-run the move-task; it must
succeed.

Do NOT soften the gate, add a suppression, or delete the adjudication content —
the adjudication is valuable and must stay; only its TABLE format must change to
satisfy the single-table contract.

## Verification I performed (everything except the gate passed)

1. **Behavioral two-surface net — non-vacuity PROVEN by my own production
   revert.** I reverted the PRIMARY-partition leg of
   `resolve_planning_read_dir` (`src/specify_cli/missions/_read_path_resolver.py`)
   from `primary_feature_dir_for_mission` back to the pre-mission
   `candidate_feature_dir_for_mission`. Result: **3 failed, 8 passed** —
   `test_two_surface_seam_across_commands`, `test_planning_seam_red_when_routed_to_coord`,
   AND the real entry-point `test_accept_gate_reads_primary_planning_and_coord_status`
   all went RED. Restored the one-line change (working tree clean, empty diff);
   net back to **7 passed**. The net is wired through the pre-existing entry point
   and is non-vacuous. The `record_analysis` cell is correctly the STATUS/allowlist
   G-5 assertion (no vacuous planning cell).

2. **Flattened regression real.** Both partitions resolve `target_branch` on the
   single-branch fixture; 11/11 across both new files green.

3. **Arch-gate sweep re-run by me: `python -m pytest tests/architectural/ -q` →
   489 passed, 0 failed** (matches the WP claim). Both fixture updates verified
   mission-introduced-and-correct:
   - `test_mission_runtime_surface.py`: `is_self_bookkeeping_path` confirmed in
     `mission_runtime.__all__` (WP05 FR-003 export) — legit baseline update.
   - `untrusted_path_audit/inventory.md`: dossier sink `mission.py:317→318` is a
     real line drift from WP00's `_collect_finalize_artifacts` extraction (helper
     confirmed present at mission.py:305; sink at line 318 is the same
     `mission_slug`-join `.kittify/dossiers/<slug>/snapshot-latest.json`, same
     `routed-through-seam (TODO)` disposition). NOT a new untrusted sink.

4. **Issue-matrix verdicts terminal.** 0 `in-mission` verdict cells. (The three
   textual mentions are the header note, #2100's issue title, and the legend — not
   verdicts.) Verdicts plausibly evidenced.

5. **ruff + mypy clean** on both new test files (no suppressions).

Fix the single-table format and re-submit; this is a one-section reformat, no
content or verdict changes.
