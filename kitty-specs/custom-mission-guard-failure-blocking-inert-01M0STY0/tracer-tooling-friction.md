# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

**Prompting questions**
- What tooling or command did you have to work around?
- What blocked you unexpectedly, and how long did it take to unblock?
- Was this a known issue or something discovered fresh?

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what happened, why it slowed you down. -->

2026-08-24 — `.venv/bin/spec-kitty plan --mission custom-mission-guard-failure-blocking-inert-01M0STY0 --json`
took >120s (backgrounded, completed under 3 min) and emitted several non-fatal warnings to
stderr before the JSON result line: `event journal capture failed: project sync store is
locked`, `Event routing failed: project sync store is locked`, `Event did not durably queue;
dropping from publication`, and `Explicit-context event capture failed: machine layout cutover
did not publish within the bounded wait`. The command still succeeded (`"result": "success"`,
`plan_file` written, `scaffold_only: true`) and the plan.md scaffold was written correctly
despite the noisy event-journal-lock warnings — did not block planning, just needed to be read
past. This is the SK-63/SK-65/SK-70 warning-signature family in SPEC-KITTY-LEDGER.md (identical
`event journal capture failed: project sync store is locked` /
`Explicit-context event capture failed: machine layout cutover did not publish within the
bounded wait` text, same command shape `spec-kitty plan --mission <slug> --json`), adjacent to
issue #3283's shared-lock-timeout class. Specifically, this occurrence matches SK-63/SK-65's
milder variant — warned but completed, JSON payload returned, `"result": "success"` — not
SK-70's full hang (partial state written, no JSON, no exit). Not re-diagnosed further here
since it did not block this mission's work; see the ledger entries for the tracked root cause
and recommended fix.

2026-08-24 — The mission brief's blast-radius list named `doctrine/missions/step_projection.py`
alongside the actually-edited files. Reading it in full (rather than assuming it needed an edit
because it was listed) was necessary to correctly conclude it should stay read-only for this
mission (see plan.md's Seam and module placement table, final row, and the closing "Design
decisions" section) — a case where the mission brief's blast-radius framing ("read to
understand") needed to be distinguished from "necessarily edited," worth flagging for a future
mission brief to state that distinction more explicitly up front.
