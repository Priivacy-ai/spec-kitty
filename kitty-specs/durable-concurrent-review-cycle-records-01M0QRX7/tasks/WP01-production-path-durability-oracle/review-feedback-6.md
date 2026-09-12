# WP01 Review Feedback — Cycle 8

## Verdict

Rejected by the independent correction reviewer. The oracle validates the
ownership refusal without parsing prose and independently checks both
authorities, but it currently treats missing `evidence_ref` and
`destination_ref` keys as equivalent to explicit null values.

## Required correction

Require both keys to be present and exactly null in an `ownership_refusal`
envelope. Add negative cases proving that omission of either or both keys is
rejected as unproven.

Preserve all existing lane, agent, durability, event-id, and independent
authority-absence checks.

## Evidence already accepted

The lane/agent assertions, false-durability requirement, absence of `event_id`,
and event/working-tree/governed-ref absence proof are otherwise adequate.
