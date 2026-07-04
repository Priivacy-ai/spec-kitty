# Issue Matrix — Org-Charter Activations Runtime Wiring

Mission: `org-charter-activations-runtime-wiring-01KWPS9E` · Branch: `design/org-charter-activations-2365`

| Issue | Title | Disposition | Closes on merge? | Notes |
|-------|-------|-------------|------------------|-------|
| [#2365](https://github.com/Priivacy-ai/spec-kitty/issues/2365) | org-charter.yaml activations parsed/merged but never wired into runtime charter context | **PRIMARY** | ✅ Yes | P0. FR-001–FR-005 close it. Claimed 2026-07-04. |
| [#1799](https://github.com/Priivacy-ai/spec-kitty/issues/1799) | Epic: Charter & Doctrine — governance configuration | **PARENT EPIC** | ❌ No | Functional home; stays open. |

## Related — cited, not folded

| Issue | Relationship | Why not folded |
|-------|-------------|----------------|
| [#1465](https://github.com/Priivacy-ai/spec-kitty/issues/1465) | Same defect *class* (`required_<kind>` merged-but-not-rendered) | Already fixed/closed. Cited as precedent; FR-005 generalizes the guard. |
| [#1242](https://github.com/Priivacy-ai/spec-kitty/issues/1242) | Same class (org charter present-but-not-surfaced) | Already fixed/closed. Second precedent behind FR-005. |
| [#1894](https://github.com/Priivacy-ai/spec-kitty/issues/1894) | Refactored `_fold_policies` (the fold site this mission reads) | Closed. Awareness only — current call shape is `_fold_policies(policies, *, strict_schema_version=False)`. |
| `charter-mediated-doctrine-selection-01KRTZCA` | Origin mission (FR-008 propagation dropped) | Root-cause lineage; no reopen. |

## Ruled out (verified by pre-spec squad)

- **#2196** (Doctrine Catfooding) — CLOSED; wrong fit.
- **#2216** (governance override/immutability tiers) — orthogonal (who-may-override, not source-propagation).

## Origin binding

`origin_binding.attempted: false` at scaffold. To be bound at spec-commit / plan time so the mission ↔ #2365 link is machine-tracked.
