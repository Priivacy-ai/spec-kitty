# Issue matrix — compat-planner-contract-ci-portable-01KWVKYH

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2419 | compat-planner.json contract-conformance test is dead in CI (hardcoded sibling-checkout path) | fixed | Both dead enforcers revived (repo-root-anchored, fail-hard, validation unconditional): `_validate_json_contract` (test_upgrade_command.py) + `_validate_against_schema` (test_messages.py); the one real drift trimmed (`UnifiedBundleMigration.description` 283→249). Reviewer-renata mutation-verified both reject-path witnesses + fail-hard branches. |
| #2339 | migration_id contract pattern fix (the defect the dead check let through) | verified-already-fixed | #2339 was fixed independently (PR #2414); this mission restores the CI guard that would catch a #2339-class recurrence — the previously-dead `compat-planner.json` conformance check now runs and fails on real drift (demonstrated: it caught the 283-char description). No #2339 code changed here. |
| #1931 | EPIC: Test quality & suite hygiene | deferred-with-followup | Follow-up: #1931 (parent epic remains open). This mission is member #2419 — one slice of suite hygiene (a green-but-vacuous dead test revived + its defect class closed). Sibling members (#572, #1008, #1634, #1842, #2071, …) remain tracked under #1931. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
