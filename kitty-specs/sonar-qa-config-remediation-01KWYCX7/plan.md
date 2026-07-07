# Implementation Plan: SonarCloud QA config — projectVersion + coverage-scope + review tool

**Branch**: `feat/sonar-qa-config-remediation` | **Mission**: `sonar-qa-config-remediation-01KWYCX7`
**Spec**: `kitty-specs/sonar-qa-config-remediation-01KWYCX7/spec.md`
**Provenance**: reuses @stijn-dejongh's Concern-B implementation concerns (his projectVersion-wiring, coverage-scope, and review-tool work) + `research.md` decisions from `ci-hygiene-and-sonar-debt-remediation-01KWV531`.

## Summary
Fix how SonarCloud *measures* and how coverage is *interpreted* for this repo — three independent, low-blast-radius surfaces, no product-code change. **Concern is CI/QA config + one read-only tool + one doc.**

## Technical Context
**Language/Version**: Python 3.11 (repo pinned) for the smoke test + config-assertion; Bash for the review tool; GitHub Actions YAML for the wiring
**Primary Dependencies**: GitHub Actions (`.github/workflows/ci-quality.yml`), `pyproject.toml` (version source, read via `tomllib`), `curl` + SonarCloud public REST API (`GET /api/measures/component_tree`, `/api/project_analyses/search` — token-free read endpoints for this public project), `pytest` (smoke test), `jq` (tool output shaping)
**Storage**: N/A — flat committed config (`ci-quality.yml`), one `docs/` note, one `scripts/ci/` script + its recorded test fixture
**Testing**: `pytest` fixture-backed smoke test for the tool (token-free, `tests/ci/`), a config-assertion for the projectVersion wiring (SC-001a), `shellcheck` on the script
**Target Platform**: GitHub Actions CI (Ubuntu) + local
**Project Type**: single project — CI/QA config + tooling (no product-code change)
**Performance Goals**: N/A — config + a read-only query tool; the smoke test uses a recorded fixture (no network in CI)
**Constraints**: no `SONAR_TOKEN` dependency (NFR-001, public read endpoints only); no suppression/ratchet/allowlist (NFR-002); research-first for #2422 (C-002); scope = 3-part slice, backlog-slicing excluded (C-001); `ruff`+`mypy` clean, commitlint-clean
**Scale/Scope**: `ci-quality.yml` (projectVersion wiring), `scripts/ci/sonarcloud_branch_review.sh` + its test (authored fresh), `docs/guides/coverage-signals.md` (reconciliation note)

## Charter Check
Read-only observability + config; no product surface, no new secret, no debt masking — aligned with the charter's honesty + no-ratchet standing orders.

## Implementation Concerns

### IC-01 — Wire `sonar.projectVersion` from `pyproject.toml` (FR-001, FR-002) — P1
- **Surface**: `.github/workflows/ci-quality.yml` — the `sonarcloud` job's "Materialize effective Sonar config" step (and/or the scanner-action `args`).
- **Approach**: read the version from `pyproject.toml` (single canonical source — no hardcode, no duplicate key in `sonar-project.properties`) and inject `-Dsonar.projectVersion=<version>` (scanner arg) OR append `sonar.projectVersion=<version>` to the materialized effective properties. Survives a version bump with zero further edits (FR-002).
- **Verify (SC-001a)**: a **static YAML-parse config-assertion** confirms the wiring is present in the `sonarcloud` job — no live analysis (the job is gated to `schedule`/`workflow_dispatch` only, not PR/push). Baseline reset (SC-001b) lands on the **next nightly cron (`17 2 * * *`) or a manual dispatch**, not on merge.

### IC-02 — Coverage-scope investigation → reconciliation doc (FR-003, FR-004) — P2, research-first
- **Approach (C-002, research-first)**: use the promoted tool (IC-03) against the unauthenticated API — `GET /api/measures/component_tree?component=Priivacy-ai_spec-kitty&metricKeys=coverage` — to enumerate the file set SonarCloud scores, and compare it against the internal `diff-coverage` gate's critical-path file list (`.github/workflows/ci-quality.yml` diff-cover step). Determine whether the **file sets** materially differ or only the **threshold philosophy** (whole-repo average vs per-PR-diff-only) differs.
- **Deliverable**: a committed `docs/` note (e.g. `docs/guides/coverage-signals.md`) explaining the two metrics, why they differ, and how to classify a discrepancy as a real regression vs an expected scope difference; referenced from the coverage/quality-gate context so a PR reviewer finds it (FR-004). **Code change only if** a genuine `sources`/`exclusions` misconfiguration is found — not for a philosophy-only difference.

### IC-03 — Author the read-only SonarCloud review tool + smoke test (FR-005, FR-006) — P2
- **Approach**: author `scripts/ci/sonarcloud_branch_review.sh` fresh (no git-fetchable predecessor exists — post-spec finding). Read-only subcommands over the public REST API: quality-gate status, coverage metrics, per-file uncovered lines, issues-by-rule/file, **and project-version/analyses (`/api/project_analyses/search` + `/api/components/show`) — the subcommand that backs SC-001b's confirmation** (closes the post-plan orphan-dependency finding). Arg-parsing + explicit error handling; **no state mutation**. Sibling to `scripts/ci/quality_gate_decision.py`; `shellcheck`-clean.
- **Smoke test (FR-006, NFR-001)**: a committed test (`pytest` driving the script, or a shell test the CI runs) exercises arg-parsing + output shape against a **recorded fixture** (so it needs no network + no `SONAR_TOKEN`), plus one optional live-read smoke against the public API. Verifies read-only behavior.

## Constraints honored
- **C-001** scope: the ~900-issue backlog slicing + issue-filing automation + roadmap-slice fixes are OUT (epic #1928). This tool is the read-only query layer only.
- **NFR-001** no new secret: every step works against public read endpoints; the smoke test uses a recorded fixture.
- **NFR-002** no masking: no suppression/ratchet/allowlist; the coverage work clarifies interpretation, it does not hide findings.

## Project Structure (files touched)
```
.github/workflows/ci-quality.yml          # IC-01: inject sonar.projectVersion from pyproject.toml
scripts/ci/sonarcloud_branch_review.sh    # IC-03: NEW read-only SonarCloud REST tool
tests/ci/test_sonarcloud_branch_review.*  # IC-03: NEW token-free smoke test (fixture-backed)
tests/ci/ or tests/architectural/         # IC-01: NEW config-assertion (projectVersion wired) for SC-001a
docs/guides/coverage-signals.md           # IC-02: NEW coverage-scope reconciliation note (FR-003/004)
```

## Key Decisions
- **projectVersion source** (Stijn DM-01KWV7EJ…): `pyproject.toml` version; resets baseline per bump; briefly reports an unreleased mid-cycle version — accepted (baseline-reset signal, not release authority).
- **Research-first coverage** (C-002): docs if only threshold philosophy differs; config change only for a genuine file-set misconfig.
- **Author-fresh tool** (post-spec finding): the predecessor script is untracked/gitignored on every ref — not fetchable; author to the behavioral contract.
- **Trigger-gate + testability** (post-plan finding): the `sonarcloud` job runs only on `schedule`/`workflow_dispatch` (not PR/push) — so SC-001a is a static YAML-parse assertion, and SC-001b lands on the next nightly cron / manual dispatch, not on merge. (The token/fork-secrets model applies to *other* jobs, not this one.)
