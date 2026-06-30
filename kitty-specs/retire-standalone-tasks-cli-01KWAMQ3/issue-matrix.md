# Issue matrix — retire-standalone-tasks-cli-01KWAMQ3

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2167 | Retire pre-3.0 readers: repo-root scripts/tasks/ duplicate still reads legacy layout | in-mission | This mission (WP04) deletes all three standalone scripts/tasks/ copies + scaffolding and sheds the ratchet entries; resolves to `fixed` at merge. |
| #1057 | Legacy cleanup: retire pre-3.0 status and task readers from active runtime | verified-already-fixed | #1057 (CLOSED) retired the shipped/active-runtime readers; this mission closes the codebase-wide loop for the non-shipped, test-only standalone copy it left behind. The canonical is_legacy_format/migration paths #1057 kept are out of scope (C-005) and untouched. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
