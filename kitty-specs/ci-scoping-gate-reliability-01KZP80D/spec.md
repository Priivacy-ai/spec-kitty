# Mission Specification: CI Scoping Gate Reliability

**Mission Branch**: `fix/ci-scoping-gate-reliability`
**Created**: 2026-08-10
**Status**: Draft
**Input**: Make two blocking CI gates reflect the PR's own changes — #3008 (data-only PRs skip corpus suites) and #3147 (docs dead-link gate over-fires whole-tree).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A corpus regression on a data-only PR is caught by CI (Priority: P1)

A contributor opens a PR that changes only non-source **corpus data** — e.g. `packs/built-in/**` doctrine, or a mission's planning artifacts under `kitty-specs/**`. Today the quality workflow's `pull_request.paths` allowlist omits those trees, so the workflow **never triggers at all**, and every corpus-reading suite (≈60 tests under `tests/doctrine/**`, plus charter/missions/architectural readers) is skipped — pre-merge AND post-merge (the `push` allowlist has the same gap). A regression in shipped doctrine data ships invisibly. This story makes such a PR run the corpus suites, and makes that run **blocking**.

**Why this priority**: This is a correctness/reliability hole in the release gate itself — CI currently cannot tell "no corpus regression" from "corpus suites never ran". P1 per the issue (reliability, tech-debt).

**Independent Test**: Open (or simulate via the path-filter tests) a PR touching only `packs/built-in/**`; confirm the workflow triggers, the corpus job runs the corpus-reading suites, and a corpus regression fails the merge gate.

**Acceptance Scenarios**:

1. **Given** a PR whose diff is confined to `packs/built-in/**`, **When** CI runs, **Then** the quality workflow triggers and the corpus-reading suites execute as a blocking gate.
2. **Given** a PR touching only a mission's `kitty-specs/<m>/spec.md` (or `plan.md`/`tasks/**`/`contracts/**`), **When** CI runs, **Then** the corpus suites that read those artifacts execute.
3. **Given** a corpus regression on such a PR, **When** the corpus job runs, **Then** the quality-gate decision is failure (merge blocked).

---

### User Story 2 - A data-only PR is not spuriously slowed by corpus churn (Priority: P1)

Nearly every mission PR touches `kitty-specs/**` — especially the append-only `status.events.jsonl` and notes/trace files that change on every status transition. If the corpus trigger globbed the whole `kitty-specs/**` tree, the heavy corpus suite would fire on almost every PR. This story keeps the trigger **narrow**: only the corpus artifacts tests actually read, never the lifecycle churn.

**Why this priority**: A false-trigger explosion would make the P1 fix a net negative (every PR pays the corpus cost). The narrow scope is what makes US1 shippable.

**Independent Test**: A PR changing only `kitty-specs/<m>/status.events.jsonl` (or `notes.md`/`trace/**`) does NOT select the corpus group.

**Acceptance Scenarios**:

1. **Given** a PR touching only `kitty-specs/**/status.events.jsonl`, **When** the path filter evaluates, **Then** the corpus group is NOT selected.
2. **Given** a PR touching `docs/**` or `src/doctrine/**` (already-covered corpus), **When** CI runs, **Then** those suites are not double-run by the new corpus group.

---

### User Story 3 - A docs PR is not blocked by pre-existing broken links it never touched (Priority: P2)

A contributor edits one documentation page. Today the blocking `fast-tests-docs` / docs-freshness dead-link gate scans the **whole tree** and fails their PR for rotted links in unrelated files. This story scopes the **blocking** dead-link check to the PR's own diff, while keeping a whole-tree scan running as a **non-blocking** signal on a schedule/full-run so genuine rot is still surfaced.

**Why this priority**: A real per-PR friction/false-failure, but lower stakes than the corpus blind spot; docs rot is still caught by the retained whole-tree scan. P2 per the issue.

**Independent Test**: A docs PR whose own diff has no broken links passes the blocking gate even when an unrelated file in the tree has a broken link; the whole-tree scan still reports that broken link on its scheduled/full run.

**Acceptance Scenarios**:

1. **Given** a docs PR whose changed files contain no broken links, **When** the blocking dead-link gate runs, **Then** it passes even if an untouched file elsewhere has a broken link.
2. **Given** the same repo state, **When** the whole-tree scan runs (scheduled/full-run), **Then** it still reports the untouched broken link.

### Edge Cases

- **Mixed PR** (src + corpus data): already triggers via `src/**`; the corpus group must not double-run suites already selected by an existing group.
- **New corpus path bucket added later**: the arch-invariant path-filter/collection-completeness guards must force the new bucket to be claimed, not silently uncovered.
- **A docs PR that genuinely introduces a broken link in a changed file**: the diff-scoped blocking gate MUST still fail it (the scoping narrows WHICH files are checked, not whether the check bites).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Corpus paths trigger the workflow | As a maintainer, I want `packs/**` and narrow `kitty-specs`/`.kittify` corpus paths added to the quality workflow's `pull_request.paths` AND `push.paths` so a data-only change starts CI at all (closes Gate 0). | High | Open |
| FR-002 | Corpus change-group + blocking job | As a maintainer, I want a `corpus` dorny change-group and a blocking corpus-test job (modeled on `fast-tests-docs`) wired into `quality-gate`, so corpus-reading suites run and gate merge when corpus data changes (closes Gate 1). | High | Open |
| FR-003 | Narrow corpus globs | As a maintainer, I want the `kitty-specs` corpus globs limited to `spec.md`/`plan.md`/`tasks/**`/`contracts/**`/`acceptance-matrix.json` (never `status.events.jsonl`/notes/trace), so the corpus suite does not fire on lifecycle churn. | High | Open |
| FR-004 | Diff-scoped blocking dead-link gate | As a contributor, I want the blocking docs dead-link check to evaluate only the PR's own changed files, so unrelated pre-existing broken links do not fail my PR. | Medium | Open |
| FR-005 | Retained whole-tree scan (non-blocking) | As a maintainer, I want the whole-tree dead-link scan to keep running as a non-blocking signal on a schedule/full-run (via a CI trigger/config boolean), so genuine repo-wide rot is still detected. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Corpus gate is blocking | The corpus test job feeds the `quality-gate` decision (a corpus regression → gate failure), not an advisory-only status. | Reliability | High | Open |
| NFR-002 | No false-trigger on lifecycle churn | A PR whose only `kitty-specs` change is `status.events.jsonl` (or `notes`/`trace`) does not select the `corpus` group — verified by the path-filter test. | Reliability | High | Open |
| NFR-003 | Arch invariants co-evolve, not bypassed | `tests/architectural/test_ci_quality_path_filters.py`, `test_ci_collection_completeness.py`, and `ci_topology_census.json` stay green with the new group claimed (no suite left unclaimed; no `# noqa`/skip to pass). | Maintainability | High | Open |
| NFR-004 | No double-run | Suites already covered (`docs`→`fast-tests-docs`, `src/doctrine/**`→doctrine/core_misc/missions) are NOT re-run by the corpus group. | Efficiency | Medium | Open |

## Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No wholesale kitty-specs in allowlist | Do NOT add `kitty-specs/**` wholesale or `status.events.jsonl` to any trigger allowlist; the docs-freshness allowlist arch-invariant also forbids `kitty-specs/**` there. | Technical | High | Open |
| C-002 | Whole-tree scan retained, not removed | The whole-tree dead-link scan is demoted to non-blocking (scheduled/full-run), never deleted — rot detection is preserved. | Technical | High | Open |
| C-003 | Reuse canonical CI machinery | Reuse the existing `dorny/paths-filter` groups, the `fast-tests-docs` job shape, and the `doctrine-charter-tests.yml` path-filtered prior art — do not hand-roll a parallel mechanism. | Technical | Medium | Open |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A PR changing only `packs/built-in/**` (or a narrow `kitty-specs` planning file) triggers the quality workflow and runs the corpus-reading suites as a blocking gate (from: never triggered).
- **SC-002**: A PR changing only `kitty-specs/**/status.events.jsonl` does not select the `corpus` group (no false-trigger).
- **SC-003**: A docs PR with no broken links in its own diff passes the blocking dead-link gate even when an untouched file has a broken link; the whole-tree scan still reports that link on its scheduled run.
- **SC-004**: `test_ci_quality_path_filters.py` + `test_ci_collection_completeness.py` are green with the new `corpus` group claimed.
