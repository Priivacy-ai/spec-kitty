# Issue matrix — glossary-seed-file-schema-validation-01KSN752

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1322 | Validate glossary seed files at creation, edit, load, and CI boundaries | fixed | Pydantic models in `seed_schema.py`, validation in `seed_validation.py`, runtime in `scope.py`, CLI `glossary validate`, dashboard error surfacing. 120 tests. |
| #1321 | Keep acceptance separate from merge completion | verified-already-fixed | PR #1321 merged prior. Bad data (`Sonar quality gate`) fixed in WP01 T001. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`.
