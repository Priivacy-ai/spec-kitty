# Issue matrix — sonar-qa-config-remediation-01KWYCX7

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2421 | SonarCloud never sets sonar.projectVersion (baseline frozen) | fixed | WP01 (lane-a, `319cc5c`): `scripts/ci/sonar_project_version.py` + `ci-quality.yml` sonarcloud job wires `sonar.projectVersion` from `pyproject.toml`; 14 tests red→green |
| #2422 | SonarCloud project-wide coverage vs internal diff-coverage scope mismatch | in-mission | WP03 (coverage-scope investigation + `docs/guides/coverage-signals.md`) — must reach `fixed` before mission `done` |
| #825 | Umbrella: SonarCloud quality-gate debt | deferred-with-followup | Parent umbrella; this mission delivers only the 3-part config slice (#2421+#2422+tool). Remaining sonar debt stays under #825 / epic #1928 (C-001) |
| #1928 | EPIC: Reduce ruff / mypy --strict / SonarCloud debt (3.2.x) | deferred-with-followup | Out of scope per C-001 — the ~900-issue backlog slicing + roadmap-slice fixes remain with epic #1928; this mission only fixes how the gate measures + adds the read-only tool |
| #2416 | LOC-census test brittleness | verified-already-fixed | Not this mission — landed separately (census-freshness-loc-insensitive → PR #2434). Referenced only as sibling context in Stijn's prep |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
