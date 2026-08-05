# Decision Moment `01KZ77CBY9G8SE9PPJEKCV01KN`

- **Mission:** `review-cycle-verdict-seam-rebuild-01KZ2W7W`
- **Origin flow:** `plan`
- **Slot key:** `t062_coord_wins_voided`
- **Input key:** `t062_coord_wins_voided`
- **Status:** `resolved`
- **Created:** `2026-08-04T20:27:59.817360+00:00`
- **Resolved:** `2026-08-04T20:28:18.613205+00:00`
- **Resolved by:** `Stijn Dejongh (operator)`
- **Opened by:** `claude-opus-5`
- **Other answer:** `false`

## Question

T062 asks for a COORD-wins conflict rule and a flip of the read-side merge-gate resolution to REVIEW_CYCLE. WP13 declined, with two reproductions independently verified: flipping the writer default breaks the green unowned test test_analysis_report_rehome; flipping only the gate desyncs writer and reader, returning 0 findings for a rejection just recorded (a new C-001-class fail-open). Root cause: review-cycle files already reach COORD via path-based commit routing, so the directory resolver must stay unified at WORK_PACKAGE_TASK and a two-sided disagreement never arises. Gate coord-topology behaviour is delivered and tested with a tripwire. Void or force?

## Options

- void-T062-COORD-wins-rule-by-construction
- force-the-REVIEW_CYCLE-flip

## Final answer

void-T062-COORD-wins-rule-by-construction

## Rationale

OPERATOR-CONFIRMED. Voided by the same reasoning that voided C-001 at planning time: the premise does not obtain once FR-001's event authority and WP04's path-based partition routing both hold. Review-cycle artifacts reach the COORD ref by path (is_coord_residue_churn), independent of the kind argument, so writer and every reader must resolve the SAME directory via WORK_PACKAGE_TASK; flipping the read-side to REVIEW_CYCLE points at a different directory and manufactures a fresh fail-open (reproduced: gate returns 0 findings for a just-recorded rejection). No two-sided PRIMARY-vs-COORD read-time disagreement exists for a COORD-wins rule to adjudicate. The behavioural substance IS delivered and tested -- the gate catches a genuine coord-topology rejection and ignores a stray coord husk -- and a tripwire (test_c001_merge_gate_agrees_with_real_writer_under_coord_topology) reds if the asymmetry returns. The revert compensator is the one legitimate exception and IS migrated because it bypasses path routing via a direct safe_commit. WP17 must report T062 as VOIDED (premise does not arise), not as satisfied, and must not claim a COORD-wins mechanism exists. Fifth structural finding where the planning-time spec prescribed a mechanism the post-rebuild code makes wrong or unnecessary (C-001 voided; FR-008 amended; three ownership deadlocks) -- consistent with a spec authored against pre-rebuild assumptions.

## Change log

- `2026-08-04T20:27:59.817360+00:00` — opened
- `2026-08-04T20:28:18.613205+00:00` — resolved (final_answer="void-T062-COORD-wins-rule-by-construction")
