# Issue matrix — org-charter-activations-runtime-wiring-01KWPS9E

One row per issue referenced in spec.md. Branch: `design/org-charter-activations-2365`.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2365 | org-charter.yaml activations parsed/merged but never wired into runtime charter context | in-mission | P0 primary. WP01 (FR-001–FR-006) wires the resolve-time union; reaches terminal `fixed` before mission `done`. Claimed 2026-07-04. |
| #1799 | Epic: Charter & Doctrine — governance configuration | deferred-with-followup | Parent functional epic; this mission is one slice. Epic stays open. Follow-up: #2372 (deferred JSON-structured-activations surface + compact-mode rendering, spec Deferred Items). |
| #1465 | `required_<kind>` merged-but-not-rendered | verified-already-fixed | Same defect class, fixed/closed. Cited as precedent; FR-005 generalizes the guard against a fourth recurrence. research.md §3. |
| #1242 | org charter present-but-not-surfaced | verified-already-fixed | Second precedent of the class, fixed/closed. research.md §3. |
| #1894 | Refactored `_fold_policies` (the fold site read here) | verified-already-fixed | Closed. Awareness only — current shape `_fold_policies(policies, *, strict_schema_version=False)`. research.md §3. |

**Ruled out as wrong parent (verified by pre-spec squad, not dispositioned here):** #2196 (Doctrine Catfooding — closed, wrong fit) and #2216 (governance override/immutability tiers — orthogonal: who-may-override, not source-propagation). See research.md §3.

**Origin lineage (no reopen):** `charter-mediated-doctrine-selection-01KRTZCA` — the propagation requirement (numbered 008 there) required org→consumer propagation; dropped as a cross-WP seam (WP02 wired the project path, WP06 wired the org fold, nobody wired fold→consumption).
