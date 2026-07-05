# Issue matrix — ci-topology-shrink-01KWQAVX

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2378 | CI shard-side split: `fast-tests-core-misc` matrix subdivision | fixed | spec FR-003/013; WP03 split `fast-tests-core-misc` into 2 disjoint non-empty shards (commit b4cb334e); terminal at WP06 closeout |
| #1933 | CI group-side shrink: map unmapped src dirs to named filter groups | fixed | spec FR-001/002/010 + C-006 shrink-intent; WP01 census + WP03 6 composite groups route all 32 worklist dirs; #1933-intent (fast targeted PR CI) satisfied with escape hatches + nightly `run_all` over-cover intact (FR-009); terminal at WP06 |
| #2383 | Arch un-blind (P1): architectural + adversarial guards on 100% of src | fixed | spec FR-005/013, NFR-002; WP03 always-on de-serialized `arch-adversarial` pole (needs edge dropped, if:always(), group-less) over 100% of src; terminal at WP06 |
| #1931 | Epic rollup: CI failure-isolation + topology remediation | fixed | spec header (Closes … under epic #1931); rollup terminal at WP06 closeout — #2378/#1933/#2383 all fixed |
| #2283 | Marker→job factors (b)/(c) | deferred-with-followup | spec Out-of-scope + C-004 scope fence; tracked at #2283 |
| #2077 | CT7 audit item | deferred-with-followup | spec Out-of-scope + C-004; tracked at #2077 |
| #2071 | Test-suite friction audit epic | deferred-with-followup | spec Out-of-scope + C-004; tracked at #2071 |
| #2368 | CI suite-map bind (marker→job substrate) | verified-already-fixed | spec C-001 (consume, don't rebuild); substrate merged PR #2368 |
| #2370 | Orphan-coverage bug (`m_3_2_4`, acceptance/state) | verified-already-fixed | spec Context Mode-B; already merged; un-blind (WP03) prevents recurrence class |
| #2379 | Orphan-coverage bug (migration) | verified-already-fixed | spec Context Mode-B; already merged; un-blind (WP03) prevents recurrence class |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
