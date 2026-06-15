# Issue matrix — tool-surface-contract-residuals-01KV4S5B

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1945 | Define and enforce ToolSurfaceContract (epic) | in-mission | operator-owned closure; SC-6 readiness note delivered at accept |
| #1948 | Residuals from over-reported closes in PR #1948 | in-mission | WP01 clears FOLD-PRE pre-clean gate; WP02–WP05 address each residual |
| #1940 | Native agent-profile projection finding codes + manifest provenance | in-mission | FR-001/FR-002 addressed by WP02 |
| #1941 | Legacy agent config hardcoded literals | in-mission | FR-003/FR-004 addressed by WP03 |
| #1942 | Docs-contract lint CI enforcement | in-mission | FR-005 addressed by WP04 |
| #1944 | Migration guide (Tool-vs-Agent upgrade guide) | in-mission | FR-006 addressed by WP05 |
| #1965 | test_doctor_skills_json_error_schema_stable environment leakage | in-mission | FR-007 addressed by WP05 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
