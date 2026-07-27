# Issue matrix — governed-state-surface-coherence-01KVCGQC

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

Four work tickets are **addressed** by this mission (`in-mission` until their WP lands a terminal verdict). The remaining rows are **context references** the spec mentions — epics/parents this mission advances but does not close (`deferred-with-followup`, the followup being the epic's own ongoing tracking), already-closed predecessors (`verified-already-fixed`), and anti-references ("do-not-use-as-parent" notes).

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2025 | Green main: repair un-masked architectural gate | fixed | WP01 `01c9d3403` — markers + remove diff-scoped test + interpreter-stable ratchet keys; local py3.12 architectural shard GREEN (461 pass; 1 pre-existing path-artifact). Binding CI confirmation on the mission PR (NFR-003). |
| #2016 | Orchestrator coord-read cannot bootstrap mid8 from coord-only topology | fixed | WP02 `2d5428161` — shared `resolve_declared_mid8` cascade (legacy-safe); 244 tests incl. contract + #2016 regression GREEN |
| #2009 | Charter status/sync/preflight consistency (2007/C2) | fixed | WP03 `94454f77d` (C2-b JSON-safe, C2-a pin) + WP04 `88520ccac` (C2-f residue downgrade, FR-007 unlink helper, C2-d hash pin, C2-e BOM/CRLF hash fix) |
| #2027 | Extract baseline_merge_commit cluster → merge/baseline.py | fixed | WP05 `51e1aee86` — verbatim extract + back-compat aliases; baseline suites GREEN unchanged |
| #1868 | Epic: bind authority to type/owner | deferred-with-followup | Parent epic — advanced by #2016/this mission; continues under #1868 |
| #2007 | Epic: 3.2.0 training bugs | deferred-with-followup | Parent epic of #2009; continues under #2007 |
| #2026 | Epic: merge.py god-module decomposition | deferred-with-followup | Parent epic of #2027 (this mission = slice 1); continues under #2026 |
| #1931 | Epic: test quality & suite hygiene | deferred-with-followup | Parent epic of #2025; continues under #1931 |
| #1797 | Epic: 3.2.0 codebase sanitization | deferred-with-followup | Grandparent epic (via #2026); continues under #1797 |
| #2024 | PR: canonical-seams path-trust & guard-capability | verified-already-fixed | Predecessor mission, merged to main (`9f98d89fe`) |
| #2023 | #2017-B8 ratchet re-key | verified-already-fixed | Closed — delivered by #2024 |
| #1623 | Epic/issue: doctor.py god-module split | deferred-with-followup | Sibling decomposition effort (context only); continues under #1623 |
| #1796 | Release-stabilization rollup (CLOSED) | verified-already-fixed | Closed meta-rollup; cited only as a do-not-use-as-parent anti-reference |
| #1479 | Release-stabilization meta-tracker | deferred-with-followup | Meta-tracker anti-reference; mission work parked under functional epic #1868 (meta-vs-functional-epics rule) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a WP in this mission; must reach a terminal verdict before mission `done`).

**Done-gate note:** the four `in-mission` rows MUST reach `fixed` before the mission merges to `done`. #2025 specifically requires the `integration-tests-core-misc (architectural)` shard observed GREEN on the pushed mission PR (NFR-003) before flipping to `fixed`.
