# Issue matrix — single-planning-surface-authority-01KVPR00

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

Verdicts reflect the seam-first respec (scope = FR-001..FR-011). Issues actively implemented
across this mission's WPs carry `in-mission` (non-terminal — passes per-WP `approved`, MUST reach a
terminal verdict before mission `done`). Carved / epic / preserved-contract / already-shipped issues
carry their terminal verdict now.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2069 | MissionTopology SSOT seam (design driver) | fixed | WP01–WP07 (enum/predicate/classifier → store/backfill → pure resolver → adoption) |
| #2062 | Read path resolves stale coord husk (coord/primary desync) | fixed | WP04 (read-leg, structural) + WP05/WP07 terminal; live flattened repro gates close (NFR-001/C-002) |
| #2063 | Planning artifacts write/read split-brain | fixed | WP05 (single write-surface authority) |
| #2064 | map-requirements vs finalize-tasks coverage mismatch | fixed | WP06 (one WP-frontmatter read surface) |
| #2065 | Read-side surface-resolver convergence | verified-already-fixed | Shipped (PR #2065, merged); the C-006 read-side contract this mission preserves |
| #1970 | Campsite-cleaning as the default (process directive) | verified-already-fixed | DIRECTIVE_025 shipped via PR #2081 (merged 2026-06-22); active process reference (C-001) |
| #1718 | create-window transient (worktree not yet materialized) | verified-already-fixed | Preserved unchanged (C-006); retained #1718 regression test + WP07 envelope row |
| #1848 | coord-deleted transient (data-loss carve-out) | verified-already-fixed | Preserved unchanged (C-006); `CoordinationBranchDeleted` hard-fail kept intact (WP03/WP04 DoD) |
| #1716 | Single surface authority (epic facet) | deferred-with-followup | Follow-up: epic #1716 carries the remaining write-side cluster forward; this mission closes the planning-surface facet |
| #2007 | Execution-context coherence (parent epic) | deferred-with-followup | Follow-up: parent epic #2007 (this mission is one increment under it) |
| #1619 | Runtime/state overhaul (parent epic) | deferred-with-followup | Follow-up: parent epic #1619 (carries forward) |
| #2070 | Mission B — CommitTargetKind type eradication + richer-API adoption | deferred-with-followup | Follow-up: Mission B tracker #2070 (carved C-007, blocked-by this mission's landing) |
| #2008 | Command-reference guard | deferred-with-followup | Follow-up: block-C mission (C-008); carries #2008 |
| #1890 | `agent worktree repair` verb | deferred-with-followup | Follow-up: block-C mission (C-008); carries #1890 |
| #2059 | doctor coord-recovery de-godding | deferred-with-followup | Follow-up: block-C mission (C-008); carries #2059 |
| #2056 | mission.py placement/commit de-godding → commit_router | deferred-with-followup | Follow-up: block-C mission (C-008); carries #2056 |
| #2066 | coverage-mismatch FR-ID set in --json | deferred-with-followup | Follow-up: block-C mission (C-008); carries #2066 |
| #1891 | campsite fold | deferred-with-followup | Follow-up: block-C mission (C-008); carries #1891 |
| #2037 | CLI-arg untrusted-path sinks (campsite fold) | deferred-with-followup | Follow-up: block-C mission (C-008); carries #2037 |
| #2048 | campsite fold | deferred-with-followup | Follow-up: block-C mission (C-008); carries #2048 |
| #1357 | Lock redesign | deferred-with-followup | Follow-up: out of scope, remains its own effort #1357 |
| #2049 | Broad audit | deferred-with-followup | Follow-up: out of scope, remains its own effort #2049 |
| #1887 | Merge path | deferred-with-followup | Follow-up: out of scope, remains its own effort #1887 |
| #2031 | out of scope | deferred-with-followup | Follow-up: out of scope, remains its own effort #2031 |
| #2058 | out of scope | deferred-with-followup | Follow-up: out of scope, remains its own effort #2058 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
