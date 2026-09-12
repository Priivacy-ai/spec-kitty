# Operator ruling — plan phase HALT, `up-mission-type-seam`

**Date**: 2026-08-13
**HALT context**: R4/R5 round 2's fresh sweep (`reviews/plan-fresh.yaml`, round 2) returned three
findings — `PLAN-FRESH2-001` (severity 4), `PLAN-FRESH2-002` (severity 3), `PLAN-FRESH2-003`
(severity 3). Per `~/.hermes/skills/tk/references/review-protocol.md` §R6, the early-stop rule
tripped first (the severity-≥3 finding count did not fall between round 1's fresh sweep, 3, and
round 2's fresh sweep, 3 — a non-falling blocking count), so no round-3 fix/verify was attempted
automatically. A finding above severity 3 (`PLAN-FRESH2-001`, severity 4) survived when the loop
stopped, which mandates HALT under the "Anything > #3 → HALT" rule. The phase agent reported HALT
with all three findings verbatim and severities, and waited for the operator per protocol.

## Ruling

**Fix all three findings, then gate.** This ruling REPLACES the acceptance bar for these three
findings for the remainder of this loop, per the protocol's "Re-entering after a HALT ruling"
clause:

- **PLAN-FRESH2-001** (severity 4): IC-07 must name ALL THREE hardcoded
  `"source_layer": "built-in"` sites in `show_mission_type`
  (`src/specify_cli/cli/commands/mission_type.py`), including the human-readable Panel branch at
  line 1543 — the default, non-`--json` path that User Story 1 AC3 exercises. The fixer verifies
  the site count against the live file rather than trusting the finding's cited count or line
  numbers.
- **PLAN-FRESH2-002** (severity 3): correct IC-01's dependency sentence to match IC-03's and
  IC-06's own Sequencing bullets — only IC-02 depends on IC-01; IC-03 and IC-06 are independently
  sequenced, and IC-06 precedes IC-01 as the mission's first (campsite-clean) commit. Make every
  sequencing statement that touches this dependency graph mutually consistent, not just the one
  cited sentence.
- **PLAN-FRESH2-003** (severity 3): add real Implementation Concern + test coverage for spec.md's
  mandatory malformed-YAML Edge Case (fail loudly, name the offending file) — this is a binding
  spec requirement with zero plan coverage; it needs a red-first test and an owning IC, not a
  patched sentence.

**Process directed by the operator**: one R4 fix round with a FRESH fixer subagent (findings
quoted verbatim, no prior review context), then a single R5a anchored-verification pass with a
FRESH verifier subagent, checking these three findings ONLY. **Per the already-tripped early-stop
rule, do NOT run another full fresh sweep** — this mirrors the ruling made on the sibling
`pack-skeleton` mission's own HALT. If all three verify `resolved`, the phase gates **PASSED** and
the whole trail (plan.md + `reviews/` + this ruling) commits with plain `git commit` on
`pr/up-mission-type-seam`. If any of the three verifies `unresolved`, HALT persists and returns to
the operator — no further fresh sweep, no further rounds beyond this one.

**Authorization scope**: this ruling authorizes exactly one more R4→R5a cycle over exactly these
three findings. It does not reopen `PLAN-GOV-001`, `PLAN-ARCH-001/002/003`, `PLAN-VERIFY-001/002/004`,
or `PLAN-FRESH-001..004` (all already resolved and verified in rounds 1–2), and it does not
authorize a general re-review of `plan.md`.
