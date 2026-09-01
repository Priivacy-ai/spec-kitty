# Mission Specification: Tidy the charter/doctrine cutover surface

**Mission Branch**: `spec/tidy-charter-cutover-surface`
**Created**: 2026-08-30
**Status**: Draft
**Input**: User description: "Tidy the charter/doctrine cutover surface before the remaining retire-doctrine-term waves" — enabler mission #3820, bundling #3818, #3819, #3808, #3810.

## Context

The `retire-doctrine-term` program still has cutover waves ahead (domain-vocabulary retirement #3732 and successors) that will keep **moving code under `src/charter/**` and re-synthesizing charter output**. Four independent defects on that exact surface were surfaced by the #3806 and #3807 landing squads. Fixing them **first** — as one tidy-first enabler — means every later wave lands on a smaller, guard-railed, less-noisy surface instead of paying the same tax as a mid-flight landing fold (as #3800/#3806/#3807 each did).

Each user story is a self-contained lane (independent surface, independent test) — the mission runs `lanes` topology, PR-bound onto `upstream/main`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Guardrail: fail on stale moved-module path literals (Priority: P1)

**Issue**: #3818 (parent seam epic #1868).

A relocation of a `src/charter/**` module leaves stale *string* references to its old path that the import-rewrite never sees — arch-gate path-literal allowlists (`(path, line)` tuples), mock-target strings (`patch("charter.<old>...")`), and markdown doc links (`[..](../../src/charter/<old>.py)`). Today these only surface as a red CI shard *after* the move lands, then a manual landing fold.

**Why this priority**: It is the keystone guardrail — building it *before* the next relocation wave means later waves catch their own stragglers at construction time. It also protects the other three lanes' edits.

**Independent Test**: A new architectural gate flags a synthetic tree that names an old `src/charter/<moved>.py` path in a string literal or doc link, and passes on the real (clean) tree. Fully testable in isolation via `tests/architectural/`.

**Acceptance Scenarios**:

1. **Given** a module physically under `src/charter/activation/`, **When** any `src/`, `tests/`, or live `docs/` file names its old top-level `charter/<name>.py` path as a string literal or relative-link, **Then** the gate fails naming the file, line, and stale token.
2. **Given** the current merged tree (post-M2b), **When** the gate runs, **Then** it passes (0 findings) — historical archives (`kitty-specs/**`, `docs/adr/**`, `docs/plans/**`) are excluded.
3. **Given** the new test file, **When** the completeness baselines run, **Then** it is joined to `tests/_arch_shard_map.py` and passes `test_ci_collection_completeness.py` with the marker convention satisfied.

---

### User Story 2 - Reliability: activation allowlist must not strand squad lenses (Priority: P1)

**Issue**: #3810 (near-term half of profile-load epic #3809).

The charter `activated_agent_profiles` allowlist omits `doctrine-daphne` and `randy-reducer` — the exact two lenses the `adversarial-squad` skill hardcodes. The FR-014 activation gate returns `EXIT 1 "is not activated"`, and the skill's raw-YAML fallback is sanctioned only for CLI-less harnesses, so a compliant delegate has **no sanctioned recovery and dispatches unprofiled, silently**.

**Why this priority**: Those squads gate every remaining cutover wave (and this mission's own reviews). They must run profiled before the program leans on them further.

**Independent Test**: With the allowlist corrected, `spec-kitty profiles` (or the activation resolver) reports both profiles activated, and a squad dispatch of each resolves its profile rather than erroring.

**Acceptance Scenarios**:

1. **Given** the shipped `src/charter/activation/packs/default.yaml` and the project charter, **When** the activation allowlist is read, **Then** `doctrine-daphne` and `randy-reducer` are activated (25 source profiles → 25 activated, or the intended set with these two included).
2. **Given** the `adversarial-squad` skill's hardcoded lenses, **When** a delegate resolves each profile through the CLI, **Then** neither returns `EXIT 1 "is not activated"`.

---

### User Story 3 - Simplify: one shared DRG load + one fail-closed wrapper for the consistency gates (Priority: P2)

**Issue**: #3808.

`charter/activation/consistency_check.py` runs three always-on gates (`_check_enforcement_lattice`, `_check_decision_documentation_on_implement`, `_check_unreconciled_tensions`) that each independently call `load_validated_graph(repo_root)` (and two also build a `DoctrineService`), loading the graph 3× per `run_consistency_check`, behind three near-identical `try/except → (errors, suggestions)` shapes.

**Why this priority**: Behavior-preserving cleanup of the module the cutover keeps editing; valuable but not blocking, so it rides below the two P1 lanes.

**Independent Test**: The three gates produce byte-identical verdicts on the shipped corpus before/after; the graph is loaded once per run (assertable via a call-count spy).

**Acceptance Scenarios**:

1. **Given** `run_consistency_check`, **When** it runs, **Then** the DRG is loaded once and one `DoctrineService` is built, shared across the three gates.
2. **Given** the enforcement-lattice, decision-documentation-on-implement, and unreconciled-tensions gates, **When** exercised on their pass and fail arms, **Then** each produces the same verdict as before the refactor (focused per-gate tests added).

---

### User Story 4 - Declutter: stop the charter-sync doubled-path double-write (Priority: P2)

**Issue**: #3819.

A charter-sync / synthesis writer emits byte-identical duplicates at a doubled-leaf path (`.kittify/charter/provenance/provenance/<file>`, `.kittify/doctrine/styleguide/styleguide/<file>`) — a path-join that appends a leaf onto a base that already ends in it. The output is also not gitignored, so PRs keep accreting stray generated files (#3807 stripped 23).

**Why this priority**: Removes recurring clutter, but no correctness impact on shipped behavior, so it is the lowest lane.

**Independent Test**: A red-first test reproduces the doubled path from a sync/synthesis run; after the fix, one write per artifact at the single correct path; a safe `.gitignore` entry prevents re-committing the generated output without swallowing tracked files.

**Acceptance Scenarios**:

1. **Given** a charter sync / synthesis run, **When** provenance/styleguide artifacts are written, **Then** each is written exactly once at its single canonical path — no `provenance/provenance/` or `styleguide/styleguide/` duplicate.
2. **Given** `.gitignore`, **When** the generated synthesis output is produced, **Then** it is ignored, while tracked files (e.g. `.kittify/doctrine/directive/DIRECTIVE_*.md`, `.provenance/*.yaml`) remain tracked.

### Edge Cases

- US1: a module name that is a *substring* of another (e.g. `context` vs `context_state`) must not false-positive; same-name-different-package (`specify_cli.cli.commands.charter.*`) must not be flagged.
- US2: a project that has *intentionally* de-activated a profile must still be honored — the fix corrects the shipped default, not a user's deliberate opt-out.
- US4: a `.gitignore` pattern must not ignore the tracked `DIRECTIVE_*.md` / `.provenance/*.yaml` under the same doctrine directories.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Stale-path-literal arch gate | As a maintainer, I want a gate that fails on stale `src/charter/<moved>.py` string/link references so relocations catch stragglers at construction time. | High | Open |
| FR-002 | Gate excludes historical archives | As a maintainer, I want the gate to skip `kitty-specs/**`, `docs/adr/**`, `docs/plans/**` so immutable snapshots are not flagged. | High | Open |
| FR-003 | Activate doctrine-daphne + randy-reducer | As a squad orchestrator, I want both hardcoded lenses in the shipped activation allowlist so delegates dispatch profiled. | High | Open |
| FR-004 | Single shared DRG load + wrapper | As a maintainer, I want one graph load and one fail-closed wrapper backing the three consistency gates. | Medium | Open |
| FR-005 | Behavior-preserving consistency verdicts | As a maintainer, I want byte-identical gate verdicts before/after the dedup, proven by focused tests. | High | Open |
| FR-006 | Fix doubled-path synthesis write | As a maintainer, I want synthesis artifacts written once at their canonical path, no doubled-leaf duplicate. | Medium | Open |
| FR-007 | Gitignore generated synthesis output | **Superseded by KD-2.** `test_charter_synthesis_artifacts_are_trackable` requires `.kittify/charter/synthesis-manifest.yaml` + `.kittify/charter/provenance/**` to stay **tracked** (commit-ready by design), so no safe ignore exists; #3819 is closed via the WP04 detection guard instead, not a gitignore. | Medium | Dropped |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No behavior drift (US3) | Consistency-gate verdicts identical on the shipped corpus before/after (0 diff). | Reliability | High | Open |
| NFR-002 | Gate performance (US1) | The new arch gate completes within the existing `tests/architectural/` shard budget (no new >5s outlier). | Performance | Medium | Open |
| NFR-003 | Lint/type clean | All new/changed code passes `ruff` and `mypy` with zero new findings; no new suppressions. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Bugfix lanes are red-first | US2 (#3810) and US4 (#3819) land a failing test first, then the fix. | Technical | High | Open |
| C-002 | New test files join baselines | Any new `tests/**` file declares its `pytestmark` and joins `_arch_shard_map.py` / marker + golden-count baselines. | Technical | High | Open |
| C-003 | Precede, don't perform, the vocabulary waves | This mission is the enabler; it must not begin the `retire-doctrine-term` domain-vocabulary retirement (#3732 etc.). | Business | High | Open |
| C-004 | PR-bound onto upstream/main | The mission merges via a pull request onto `upstream/main`, not a direct push. | Technical | High | Open |

### Key Entities

- **Moved-module set**: the modules physically under `src/charter/activation/` (the FR-001 gate's scan input).
- **Activation allowlist**: `activated_agent_profiles` in `src/charter/activation/packs/default.yaml` + project charter config (FR-003).
- **Consistency gates**: the three always-on checks in `charter/activation/consistency_check.py` (FR-004/005).
- **Synthesis provenance writer**: the charter-sync path-join that emits `.kittify/charter/provenance/**` (FR-006/007).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The FR-001 gate fails a seeded synthetic stale-path fixture and passes on the merged tree (0 findings), and is green in CI on the `tests/architectural/` shard.
- **SC-002**: `doctrine-daphne` and `randy-reducer` resolve through the activation gate with no `EXIT 1`; a squad dispatch of each runs profiled.
- **SC-003**: `run_consistency_check` loads the DRG exactly once (down from 3×) with byte-identical verdicts across all three gates' pass/fail arms.
- **SC-004**: A charter sync / synthesis run produces zero doubled-path (`*/provenance/provenance/*`, `*/styleguide/styleguide/*`) artifacts, and a clean `git status` afterward (generated output ignored, tracked files intact).
- **SC-005**: The four lanes land via one PR onto `upstream/main`, green modulo honest inherited reds, closing #3818, #3819, #3808, #3810.
