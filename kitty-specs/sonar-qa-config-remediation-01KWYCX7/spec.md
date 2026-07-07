# Mission Specification: SonarCloud QA config — projectVersion + coverage-scope + review tool

**Status**: Draft
**Issues**: Closes #2421, Closes #2422 (both parented under #825 / epic #1928)
**Provenance**: Reuses maintainer @stijn-dejongh's prep (branch `design/pr-landing-followups-and-sonar-remediation`, mission `ci-hygiene-and-sonar-debt-remediation-01KWV531`, his Concern-B projectVersion / coverage-scope / review-tool requirements + its `research.md` decisions). This mission is the **3-part sonar-config slice only**; the ~900-issue backlog slicing stays with epic #1928; the census/contract work (#2416/#2419/#2420) already landed.

## User Scenarios & Testing *(mandatory)*

**Primary actor**: a contributor or maintainer reading a PR's **SonarCloud signal**, currently misled two ways — (a) the new-code quality gate has measured ~4 months of undifferentiated drift since 2026-03-21 because no `sonar.projectVersion` is ever set (#2421), and (b) SonarCloud's whole-repo `coverage` looks alarmingly low next to the internal `diff-coverage` gate because the two measure **different scopes**, with no documented way to tell an expected scope difference from a real regression (#2422).

**Grounding** (from Stijn's `research.md`, confirmed against the live repo):
- The `sonarcloud` job (`.github/workflows/ci-quality.yml`, "Materialize effective Sonar config" step + the scanner-action `args`) and `sonar-project.properties` never set `sonar.projectVersion` → every analysis reports `"projectVersion": "not provided"`, freezing the `previous_version` new-code baseline.
- SonarCloud's public read API is reachable **without `SONAR_TOKEN`** for this public project (verified in Stijn's post-spec squad) — so the coverage-scope question is answerable from CI/locally.
- A `sonarcloud_branch_review.sh` exists **only as an untracked local file on the maintainer's machine** — `work/` is gitignored on every ref (including Stijn's `design/…` branch), so it is **not fetchable via git anywhere** (post-spec squad, architect-alphonso + reviewer-renata, independently confirmed). This mission therefore **authors a fresh, tracked, read-only tool** to the same behavioral contract rather than relocating a file git cannot see; `scripts/ci/` is the repo's convention (sibling to `scripts/ci/quality_gate_decision.py`).

### User Story 1 — SonarCloud tracks a real code version (Priority: P1) — #2421
As a maintainer, I want each SonarCloud analysis to carry a real version identifier derived from `pyproject.toml`, so the new-code baseline resets per dev cycle instead of freezing indefinitely.
**Independent test**: after the fix, a SonarCloud analysis reports a real `projectVersion` (the CLI's `pyproject.toml` version), and the new-code baseline reflects a release boundary, not the fixed 2026-03-21 anchor.

### User Story 2 — Sonar vs internal coverage is interpretable (Priority: P2) — #2422
As anyone reading a PR's coverage signal, I want to know whether SonarCloud's `coverage`/`new_coverage` and the internal `diff-coverage` gate are comparable, so I don't mistake an expected scope difference for a regression.
**Independent test**: given the documented explanation, a reader can correctly classify an apparent Sonar-vs-internal discrepancy as either a real regression or an expected scope difference.

### User Story 3 — A tracked, read-only SonarCloud review tool exists (Priority: P2)
As a maintainer, I want a tracked, read-only SonarCloud review tool at `scripts/ci/` with a smoke test, so the projectVersion check (SC-001b) and the coverage-scope investigation (FR-003) route through one canonical, testable tool instead of ad-hoc API calls. (The maintainer's untracked local copy is a reference, not a source — the tool is authored fresh to its behavioral contract; adopt his copy as a starting point only if he hands it over, without blocking on it.)
**Independent test**: `scripts/ci/sonarcloud_branch_review.sh` runs read-only against the public API and its smoke test passes in CI with no `SONAR_TOKEN`.

### Edge Cases
- **Coverage fix is research-first, not fix-first (FR-003).** First determine, via the unauthenticated `GET /api/measures/component_tree` (scoped to `coverage`) vs the internal gate's critical-path file list, whether the **file sets** genuinely differ or only the **threshold philosophy** (whole-repo average vs per-PR-diff) differs. If only the threshold philosophy differs → the deliverable is **explanatory documentation**, not a scope-alignment code change. If the file sets are materially misconfigured → document which files/dirs differ (and, only if it is a genuine config bug, fix the Sonar `sources`/`exclusions`). Do not force a code change where docs are the honest answer.
- **projectVersion mid-cycle (Stijn's DM-01KWV7EJ…).** Deriving from `pyproject.toml` briefly reports an unreleased version mid-cycle — accepted: SonarCloud uses it only as a baseline-reset signal, not a release-authority claim.
- **Promoted script stays read-only.** The idempotent issue-*filing* layer (for the excluded backlog slicing) is NOT built here — only the read-only query tool + its smoke test.
- **No `SONAR_TOKEN` dependency.** The smoke test + FR-003 investigation must work against the public read endpoints; do not introduce a token requirement.

## Requirements *(mandatory)*

### Functional Requirements
| ID | Title | User Story | Priority | Status |
| --- | --- | --- | --- | --- |
| FR-001 | SonarCloud analysis reports a real project version | US1 — wire `sonar.projectVersion` from `pyproject.toml`'s version into the `sonarcloud` job (the "Materialize effective Sonar config" step and/or the scanner-action `args`), so every analysis carries a real version and the new-code baseline resets per cycle. | High | Open |
| FR-002 | Version source is single-sourced + non-brittle | The version is read from `pyproject.toml` (the canonical source), not hardcoded or duplicated into `sonar-project.properties`; the wiring survives a version bump with no further edits. | High | Open |
| FR-003 | Sonar-vs-internal coverage scope is investigated then reconciled-or-documented | US2 — using the unauthenticated SonarCloud API, determine whether Sonar's `coverage` file-set differs from the internal `diff-coverage` critical-path set; deliver a committed doc explaining the scope difference and how to interpret a discrepancy. Make a config change only if a genuine misconfiguration (not a philosophy difference) is found. | Medium | Open |
| FR-004 | The coverage doc is discoverable + linked from the signal | The reconciliation note lives where a PR reviewer will find it (e.g. `docs/` + referenced from the coverage/quality-gate context), not orphaned. | Medium | Open |
| FR-005 | Author a tracked, read-only SonarCloud review tool | Since no `sonarcloud_branch_review.sh` is fetchable via git (the maintainer's copy is untracked/`work/`-gitignored on every ref), **author** `scripts/ci/sonarcloud_branch_review.sh` fresh to the behavioral contract: read-only queries for quality-gate status, coverage metrics, per-file uncovered lines, issues-by-rule/file, **and project-version/analyses (`/api/project_analyses/search` + `/api/components/show`) so SC-001b is confirmable through the tool, not ad-hoc calls**, with arg-parsing + error handling; no state mutation. Adopt the maintainer's local copy as a starting point only if handed over, without blocking. | Medium | Open |
| FR-006 | The promoted tool has a smoke test that needs no token | A committed smoke test exercises the script's argument-parsing/output shape against the public API (or a recorded fixture), runs in CI, and needs no `SONAR_TOKEN`. | Medium | Open |

### Non-Functional Requirements
| ID | Title | Requirement | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | No new secret dependency | The projectVersion wiring, the FR-003 investigation, and the smoke test must not introduce a `SONAR_TOKEN` requirement where none exists; public read endpoints suffice. | Security | High | Open |
| NFR-002 | No masking of real debt | This mission changes how the gate *measures* + how coverage is *interpreted*; it must not suppress, allowlist, or ratchet away any real SonarCloud finding. | Integrity | High | Open |

### Constraints
| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | Scope: 3-part slice only | Deliver #2421 + #2422 + the read-only tool promotion. **Exclude** the ~900-issue backlog slicing, issue-filing automation, and roadmap-slice fixes (epic #1928). | Product | High | Open |
| C-002 | Research-first for #2422 | Do not write a code "scope alignment" fix unless the investigation proves a genuine file-set misconfiguration; a philosophy-only difference is discharged by documentation. | Technical | High | Open |
| C-003 | Quality gates | `ruff` + `mypy` clean on new Python (the smoke test); the promoted shell script passes `shellcheck` if the repo runs it; commit messages commitlint-clean. | Technical | High | Open |

### Key Entities
- **`.github/workflows/ci-quality.yml`** (`sonarcloud` job) — where `sonar.projectVersion` is injected (FR-001).
- **`pyproject.toml`** — the canonical version source (FR-002).
- **`scripts/ci/sonarcloud_branch_review.sh`** — the promoted read-only QA tool (FR-005/006).
- **The coverage-scope reconciliation doc** — FR-003/004 deliverable.
- **Stijn's `research.md`** (`ci-hygiene-…-01KWV531`) — the reused investigation grounding.

## Success Criteria *(mandatory)*
- **SC-001a (CI-verifiable now)**: `sonar.projectVersion` is wired into the `sonarcloud` job's "Materialize effective Sonar config" step and/or the scanner-action `args` and appears in the printed effective `sonar-project.properties` — verified by a **static YAML-parse config-assertion** in the diff/CI. (The `sonarcloud` job is gated `if: … github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'` — it runs on **neither `pull_request` nor `push`**, so no live analysis runs in any PR regardless of token; the wiring is verified statically, not by observing the job run. The token/fork model applies to *other* jobs, not this one.)
- **SC-001b (post-merge observation)**: the analysis carrying the fix is the **next scheduled nightly run** (`ci-quality.yml` cron `17 2 * * *`) or a manual `workflow_dispatch` — **merge/push does NOT trigger it**, so an operator checking immediately post-merge sees no change (up to ~24 h, or trigger a dispatch). On that run, SonarCloud reports the real `projectVersion` (matching `pyproject.toml`) and the new-code baseline is no longer anchored at 2026-03-21 — confirmed via the tool's project-version/analyses read subcommand against the public API. Labelled post-merge; not a PR-gate criterion.
- **SC-002**: The committed coverage-scope note lets a reader correctly classify a Sonar-vs-internal discrepancy as regression vs expected scope difference; it accurately states whether the file sets differ or only the threshold philosophy does (backed by the FR-003 investigation).
- **SC-003**: `scripts/ci/sonarcloud_branch_review.sh` is tracked, read-only, and its smoke test passes in CI with no `SONAR_TOKEN`.
- **SC-004**: No suppression/ratchet/allowlist introduced (NFR-002); no new token requirement (NFR-001); `ruff`+`mypy` clean.

## Out of Scope
- The ~900-issue live-backlog slicing into tracked tickets, issue-filing automation/idempotency, roadmap-slice fixes (epic #1928).
- The census-gate (#2416) + contract-conformance (#2419/#2420) work — already landed.
- Any pure-core/port extraction refactor.

## Assumptions
- SonarCloud's public read API remains reachable without a token for this public project (confirmed in Stijn's post-spec squad).
- `pyproject.toml`'s version is the intended `projectVersion` source (Stijn's DM-01KWV7EJ…).
