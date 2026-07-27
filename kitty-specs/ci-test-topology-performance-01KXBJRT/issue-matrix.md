# Issue matrix — ci-test-topology-performance-01KXBJRT

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

This mission's OWN tracking ticket is **#2585** (native sub-issue of the #1931 epic), created after spec authoring and therefore not a matrix row. The rows below are the issues *referenced* in spec.md — none are closed *by* this mission: #2579 is an already-merged prerequisite cited as evidence, #1931 is the parent epic, and #2071 / #2475 / #2476 / #2534 are explicitly Out of Scope (sibling missions).

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1931 | Epic: Test quality & suite hygiene (parent) | deferred-with-followup | Parent epic; stays open. This mission is native sub-issue #2585 — one contribution, not an epic closure. |
| #2579 | security: remediate 19 code-scanning alerts + unblock Dependabot | verified-already-fixed | MERGED (PR #2579) before this mission; cited only as the Sonar `new_security_rating` / coverage evidence in spec.md §Evidence. Not modified here. |
| #2071 | Epic: Tests as scaffold, not friction (CT-friction sibling) | deferred-with-followup | Explicitly Out of Scope (spec.md §Out of Scope) — the sibling test-quality mission owns it; #2071 remains open as its own tracker. |
| #2475 | Arch marker-correctness gate vacuous under `.worktrees/` | deferred-with-followup | Out of Scope (arch-gate fidelity); its own mission. #2475 remains open. |
| #2476 | Local pre-PR parity for the architectural pole | deferred-with-followup | Out of Scope (arch-gate fidelity); its own mission. #2476 remains open. |
| #2534 | Pre-review regression gate fails in consumer repos | deferred-with-followup | Out of Scope (arch-gate fidelity / consumer-repo parity); its own mission. #2534 remains open. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
