# Issue matrix — tool-surface-contract-01KV2K2P

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1945 | ToolSurfaceContract: Unified Tool Surface Registry (parent epic) | fixed | All 9 WPs (WP01–WP09) implemented + independently approved |
| #1935 | Glossary pre-formalization (prerequisite) | verified-already-fixed | Glossary terminology is established by the separate prerequisite PR #1935, not this mission. C-009 compliance verified across all 9 WP reviews: `ToolSurfaceContract`/`Tool`/`Agent`/`Tool Surface` naming throughout, zero `feature*` aliases, terminology guard green. |
| #1944 | Migration and Compatibility Gate | fixed | WP02 approved (26 compat baselines) |
| #1936 | Registry Skeleton and Glossary-Compliant Naming | fixed | WP01 approved |
| #1937 | Command-Skill Provider and `doctor tool-surfaces` | fixed | WP03 approved (live-wired, schema-conformant) |
| #1938 | Session-Presence Provider | fixed | WP04 approved (no-stub `--fix` verified) |
| #1939 | Managed Doctrine Skill Provider | fixed | WP05 approved (cycle 1; `--fix` crash fixed + regression test) |
| #1940 | Native Agent Profile Projection | fixed | WP06 approved (16 profiles projected, manifest) |
| #1941 | Legacy Agent Config Refactor | fixed | WP07 approved (frozen interface preserved, zero-mismatch) |
| #1942 | Docs Contract Lint | fixed | WP08 approved (drift-catch verified, CI-collected) |
| #1943 | Plugin Bundle Projection and Validation | fixed | WP09 approved (FR-016/C-006 prohibition guard verified) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
