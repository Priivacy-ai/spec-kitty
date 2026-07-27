# Decision Moment `01KWC36SFC7XVDVA9QQTN1NAK8`

- **Mission:** `sync-daemon-orphan-cleanup-01KWC2A3`
- **Origin flow:** `plan`
- **Slot key:** `plan.scope.issue-1071-reconfirmation-method`
- **Input key:** `issue_1071_method`
- **Status:** `resolved`
- **Created:** `2026-06-30T11:04:09.452804+00:00`
- **Resolved:** `2026-06-30T11:05:15.519731+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How should issue #1071 (same-$HOME singleton leak) be live-reconfirmed for FR-012/SC-006?

## Options

- Automated regression test in the live-subprocess harness
- Manual reconfirmation plus documentation in the ADR/PR
- Other

## Final answer

Automated regression test in the live-subprocess harness reproducing the same-HOME singleton scenario; close #1071 with durable test evidence.

## Rationale

_(none)_

## Change log

- `2026-06-30T11:04:09.452804+00:00` — opened
- `2026-06-30T11:05:15.519731+00:00` — resolved (final_answer="Automated regression test in the live-subprocess harness reproducing the same-HOME singleton scenario; close #1071 with durable test evidence.")
