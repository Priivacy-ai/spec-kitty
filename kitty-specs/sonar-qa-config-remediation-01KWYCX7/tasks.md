# Tasks: SonarCloud QA config — projectVersion + coverage-scope + review tool

**Mission**: `sonar-qa-config-remediation-01KWYCX7` | **Branch**: `feat/sonar-qa-config-remediation`

3 work packages. WP01 (projectVersion) and WP02 (the tool) are independent; WP03 (coverage doc) depends on WP02 because the investigation runs *through* the tool.

## Subtask Index
| ID | Description | WP | Parallel |
| --- | --- | --- | --- |
| T001 | Wire `sonar.projectVersion` from `pyproject.toml` into the `sonarcloud` job | WP01 | |
| T002 | Static config-assertion test: projectVersion is wired (SC-001a) | WP01 | |
| T003 | Author `scripts/ci/sonarcloud_branch_review.sh` (read-only, 5 subcommands) | WP02 | [P] |
| T004 | Token-free, fixture-backed smoke test + shellcheck (SC-003) | WP02 | [P] |
| T005 | Investigate Sonar-vs-internal coverage scope via the tool (FR-003) | WP03 | |
| T006 | Write + link `docs/guides/coverage-signals.md` reconciliation note (FR-003/004) | WP03 | |

## WP01 — projectVersion wiring (IC-01) — P1
Goal: `sonar.projectVersion` reads from `pyproject.toml` into the `sonarcloud` job so the new-code baseline resets per cycle. FR-001, FR-002, SC-001a.
- [x] T001 Wire projectVersion from `pyproject.toml` into ci-quality.yml's `sonarcloud` job (Materialize step and/or scanner args) (WP01)
- [x] T002 Static YAML-parse config-assertion that the wiring is present (SC-001a) (WP01)
**Independent test**: the config-assertion passes; the effective properties carry the real version.

## WP02 — the read-only review tool + smoke test (IC-03) — P2
Goal: author `scripts/ci/sonarcloud_branch_review.sh` (read-only) + a token-free smoke test. FR-005, FR-006, NFR-001, SC-003.
- [x] T003 Author the script: read-only subcommands — quality-gate status, coverage metrics, per-file uncovered lines, issues-by-rule/file, project-version/analyses; arg-parsing + error handling; no mutation (WP02)
- [x] T004 Fixture-backed smoke test (no `SONAR_TOKEN`, no network) + shellcheck-clean (WP02)
**Independent test**: `pytest tests/ci/test_sonarcloud_branch_review.py` passes with no token; shellcheck clean.

## WP03 — coverage-scope reconciliation doc (IC-02) — P2 (depends on WP02)
Goal: use the tool to determine whether Sonar's `coverage` file-set differs from the internal `diff-coverage` set, then document it. FR-003, FR-004, C-002.
- [ ] T005 Investigate scope via the tool + unauthenticated API (file-set diff vs threshold-philosophy diff) (WP03)
- [ ] T006 Write `docs/guides/coverage-signals.md` + reference it from the coverage/quality-gate context (WP03)
**Independent test**: the note lets a reader classify a Sonar-vs-internal discrepancy correctly; it accurately states whether file-sets or only philosophy differ.

**MVP**: WP01 (the P1 projectVersion fix). **Dependencies**: WP03 → WP02.
