# Issue matrix — do-dispatch-open-op-lifecycle-01KTSJ2H

One row per issue referenced in spec.md. Filled at WP01 review (schema v2 split); rows
for issues owned by later WPs carry deferred-with-followup verdicts and will be upgraded
as those WPs land.

| Issue | Verdict | Evidence ref |
|-------|---------|--------------|
| #1810 | deferred-with-followup | #1810 — WP01 (commit b1f8634cf) fixes the "unreadable record" portion: OpCompletedEvent requires outcome/closed_by, blank-default records unrepresentable. The do→dispatch rename is explicitly out of scope per spec.md C-002; follow-up remains #1810. |
| #1229 | deferred-with-followup | Follow-up: #1229 — closed by WP02 (do open-Op dispatch) / WP03 (close surface, closing actor) in this mission; not in WP01 scope. |
| #1688 | deferred-with-followup | Follow-up: #1688 — closed by WP04 (doctor stale sweep) in this mission; closed_by=doctor_sweep discriminator introduced in WP01. |
| #1781 | deferred-with-followup | Follow-up: #1781 — closed by WP05 (legacy record migration via spec-kitty upgrade) in this mission; WP01 provides LegacyRecordError + warn-and-skip readers. |
| #701 | deferred-with-followup | Follow-up: #701 — closed by WP06 (session presence contract prose) in this mission. |
