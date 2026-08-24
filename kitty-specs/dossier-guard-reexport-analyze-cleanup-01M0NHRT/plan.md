# Implementation Plan: Close four defects — dossier guard widening, CLI re-export trim, analyze commitlint cleanup, and SK-63 path-relativization

**Branch**: `fix/dossier-guard-reexport-analyze-cleanup-3676` | **Date**: 2026-08-22 | **Spec**: `kitty-specs/dossier-guard-reexport-analyze-cleanup-01M0NHRT/spec.md`
**Input**: Feature specification from `kitty-specs/dossier-guard-reexport-analyze-cleanup-01M0NHRT/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `packs/built-in/missions/mission-steps/software-dev/plan/prompt.md` for the execution workflow.

## Branch contract (stated per plan prompt.md's mandatory repeat rule)

- **Current branch at plan start**: `fix/dossier-guard-reexport-analyze-cleanup-3676`
- **Planning/base branch**: `fix/dossier-guard-reexport-analyze-cleanup-3676`
- **Merge target for completed changes**: `fix/dossier-guard-reexport-analyze-cleanup-3676`
- `branch_matches_target`: `true` (confirmed by `spec-kitty plan --mission dossier-guard-reexport-analyze-cleanup-01M0NHRT --json` scaffold output)
- Per spec.md D2, this branch descends from `refactor/dossier-emitters-canonical-only-1058` (PR #3672, open against `main`), and this mission's own eventual PR targets `main` and merges after #3672. Topology is `single_branch`, fixed at scaffold time — not re-litigated here.

## Summary

Four already-diagnosed, disjoint defects in spec-kitty's own tooling, closed in one mission because
three of the four share a call path or file (SK-63's path fix and #3678's commit-subject fix both
live in the `record-analysis` write path) and the fourth (the dossier guard widening) is small and
self-contained. No new modules; seven existing files edited in place:

1. `tests/architectural/test_dossier_emitter_positional_guard.py` — widen `_call_target_name` (and
   the docstring) to also flag attribute-chain (`dossier.emit_x(...)`) and aliased-import
   (`ei(...)` where `ei` aliases `emit_x`) positional calls to the four guarded dossier emitters
   (#3676, FR-001–FR-004).
2. `src/specify_cli/dossier/__init__.py` — remove seven `spec_kitty_events` type re-exports
   (`ArtifactIdentity`, `ContentHashRef`, `LocalNamespaceTuple`, the four `MissionDossier*Payload`
   types) from the `from .events import (...)` statement and `__all__`, leaving the four `emit_*`
   function re-exports untouched (#3677, FR-005).
3. `src/specify_cli/cli/commands/agent/mission_record_analysis.py` — change the `record-analysis`
   commit's `message=` string from `f"Add analysis report for mission {slug}"` to a conventional-
   commit `docs(<scope>): <subject>` shape (#3678, FR-006).
4. `src/specify_cli/analysis_report.py` — relativize `input_artifacts["path"]` values against their
   governing root (`repo_root` for `spec.md`/`plan.md`/`tasks.md`, `canonical_root` for `charter`)
   instead of writing an absolute `str(path)`, raising/reporting on relativization failure while
   preserving `check_analysis_report_current`'s established never-raises contract (SK-63, FR-007,
   NFR-002).
5. `tests/specify_cli/test_analysis_report.py` and
6. `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py` — update the five existing
   `hashes["charter"]["path"]` / `input_artifacts["charter"]["path"]` assertions from an absolute
   resolved path to the new `canonical_root`-relative value (Grounding Correction 3).
7. `tests/specify_cli/cli/commands/agent/test_mission_record_analysis.py` — add a RED-first
   fixture (T010) proving the CURRENT non-conforming `record-analysis` commit subject fails
   commitlint before the fix lands; the sole existing test module for
   `mission_record_analysis.py`, disjoint from items 5/6 above (added post-tasks,
   TASKS-DECOMP-001, per spec.md §106).

`commitlint.config.cjs` is explicitly **not** touched (Grounding Correction 4 / C-004): the fix is
a conforming commit subject, not an ignore-list widening.

No `[NEEDS CLARIFICATION]` markers were opened during planning — every decision this plan needs is
already settled in spec.md's binding Clarifications/Decision-Record section (D1–D3, §486, §106,
§581, Grounding Corrections 1–4). This plan restates and applies those decisions to concrete
work-package sequencing; it does not re-derive or re-litigate any of them. Phase 0
(`research.md`) and Phase 1 design artifacts (`data-model.md`, `contracts/`, `quickstart.md`) are
therefore not generated — see "Phase 0/1 artifacts" below for the explicit disposition.

## Technical Context

**Language/Version**: Python 3.11+ (existing CLI codebase; no version change).
**Primary Dependencies**: none added or upgraded — all four fixes edit existing stdlib (`ast`,
`pathlib`) and in-repo call sites; `spec_kitty_events` (the vendored/external contract package) is
read but not modified (item 2 removes a *re-export*, not a use of the package itself).
**Storage**: N/A — no persistence-layer change; `analysis-report.md` is an existing committed
markdown artifact whose `input_artifacts.path` *string values* change shape, not its file format.
**Testing**: `pytest` (existing suite conventions); target the seven touched files' own test modules
plus the two architectural gates named in the baseline command below — not the full `tests/`
suite, per the charter's Testing Requirements note on running only the affected test packages.
**Target Platform**: Linux/macOS/Windows CLI tooling (spec-kitty's own supported platforms) — no
platform-specific behavior introduced.
**Project Type**: Single project — this is spec-kitty's own CLI package (`src/specify_cli/`) plus
its test suite (`tests/`). No web/mobile axis applies.
**Performance Goals**: N/A — no perf-sensitive path touched (an AST-walk guard already runs
per-file at test time; the guard widening adds one more `ast.Call` shape check, not a new full
pass; `record-analysis`'s path-relativization is a one-time string operation per input artifact).
**Constraints**: No absolute local filesystem path (a path containing `$HOME` or an OS username)
may appear in any artifact this mission commits, including its own spec/plan/tasks artifacts
(C-001) — the same defect class NFR-001/FR-007 exist to close in the product must not be
reintroduced in this plan.md.
**Scale/Scope**: Four defects, seven files (per spec.md/plan.md's §106 table — see below), zero
new modules, zero contract-surface moves. Smallest
of spec-kitty's own recent bugfix-class missions in scope terms (contrast with a mission-type-seam
or architectural-gate mission).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter loaded from `.kittify/charter/charter.md` (v1.4.0). Gate-by-gate:

- **Single canonical authority** — PASS. #3677's fix is the canonical-authority fix itself: it
  removes the second import path to the seven `spec_kitty_events` types, leaving exactly one
  (directly from `spec_kitty_events`, the charter's declared external contract package).
- **Architectural alignment (shared-package boundaries)** — PASS. `spec_kitty_events` remains an
  external contract package, untouched at the source; `specify_cli/dossier/__init__.py` is CLI-
  owned internal-runtime glue, and trimming its re-export list does not blur the boundary — it
  sharpens it. No kernel, doctrine-schema, or orchestrator-api surface touched (verified: none of
  the seven files live under `src/kernel/` or `src/specify_cli/mission_loader/`).
- **DDD + tiered rigour** — PASS (advisory). This is glue/tooling code (a CLI command's commit
  message, a test-scanning AST guard, a hash-recording helper), not core domain logic; tiered
  rigour licenses a lighter touch than, say, `src/kernel/`. Applied: still ATDD-first per below,
  still evidence-grounded, but no new bounded-context modeling is warranted for a fix this shape.
- **ATDD-first (§591, C-011, binding)** — PASS, by construction of the WP sequencing below: a
  RED-first commit adds the two new positive-control fixtures to
  `test_dossier_emitter_positional_guard.py`, run and confirmed RED against the CURRENT
  (pre-widening) `_call_target_name`, committed as its own commit *before* any implementation
  commit. A GREEN implementation commit then widens `_call_target_name` (or the surrounding scan
  logic) plus the docstring (FR-003/SC-008), re-running the same two tests to confirm GREEN, plus
  the four pre-existing tests still green (NFR-003). A reviewer must be able to verify **RED on
  `planning_base_branch` and GREEN on final** — i.e. checking out the commit immediately before
  the GREEN implementation commit and re-running the two new tests must reproduce RED; checking
  out final must reproduce GREEN — this is the exact, literal check the review squad will run.
- **Glossary & terminology** — PASS. No `Feature`/`feature*` aliasing introduced; "mission" is used
  throughout new/changed strings (e.g. the `record-analysis` commit subject and its scope token).

### Quality & Tech-Debt Standing Orders — applied

1. **Adversarial squad cadence** — advisory; deferred to the post-plan review squad this planning
   artifact hands off to. Not re-litigated here.
2. **Campsite cleaning** — explicit call, not silently skipped: **not warranted** as a distinct
   preceding commit for this mission. None of the seven touched files is a "god-surface" needing a
   tidy-first pass: `dossier/__init__.py` is a flat re-export list (the FR-005 edit *is* the tidy —
   shrinking the list is the whole change); `analysis_report.py` is 544 lines total. Of the four
   touched functions, `_artifact_hash_entry` (179–185), `_charter_path` (188–214), and
   `collect_input_artifact_hashes` (217–226) are each small (5–30 lines) and already focused.
   `check_analysis_report_current` (458–544) is the one FR-007-load-bearing exception to that
   bucket — it is 87 lines, not 5–30 — but it is a flat, unnested sequence of independent
   early-return guard clauses (no branch nesting), so it is not in need of decomposition to make
   the FR-007 edit safe either; adding one more guard clause (the relativization-failure catch) to
   an already-linear chain does not raise its complexity in the way it would in a nested function.
   `mission_record_analysis.py`'s touched surface is a single `message=` string inside an
   already-isolated `contextlib.suppress(...)` block;
   `test_dossier_emitter_positional_guard.py`'s `_call_target_name` is 5 lines. Widening it is the
   functional change itself, not a debt-clearing prerequisite to it.
   `tests/specify_cli/cli/commands/agent/test_mission_record_analysis.py` (the 7th file, added
   post-tasks per TASKS-DECOMP-001) is a new-fixture addition to an existing test module, not a
   god-surface either — no decomposition or tidy-first pass is warranted there. No Sonar findings,
   over-long functions, or stale patterns were identified on any of the seven surfaces during
   grounding. If a reviewer's own Sonar pass on these seven files surfaces something this plan
   missed, fold it per the standard §106 reconciliation (below), not as a retroactive
   justification for a campsite commit that was skipped here.
3. **Mission tracer files** — this plan seeds `tracer-approach.md` and `tracer-design-decisions.md`
   alongside this document (F-01/F-02 already recorded in `tracer-tooling-friction.md`).
4. **Test remediation & bug-fix discipline** — the RED-first sequencing above satisfies this for
   the guard widening; the five updated charter-path assertions are judged VALID (not stale, not
   stubs) and are being *changed* because the product's own contract changed (FR-007), which is
   the "fix the product, update the test to match the new correct contract" branch of this rule,
   not a "test was wrong all along" branch.
5. **Architectural gate discipline** — the widened guard remains a non-vacuous, concrete-floor gate
   (still scans real `src/` with a real clean-tree assertion, `test_src_tree_has_no_positional_dossier_emitter_calls`,
   NFR-003); no shrink-only ratchet or baseline-freeze applies here (this is a widening of
   detection surface, not a debt ratchet).
6. **Canonical sources & unification** — this plan and its WPs use the canonical `spec-kitty plan`
   scaffold and the resolved software-dev plan template; no ad hoc structure copied from another
   mission's `kitty-specs/` artifact.
7. **Git & workflow discipline** — PR-only, operator merges; addressed under "PR shape" below.
8. **Mission hygiene** — reviewer ≠ implementer enforced by the mission's implement/review loop
   (out of this plan's scope to re-describe; it is a runtime-loop property, not a plan artifact).
9. **Red-main & release discipline** — addressed under "Baseline" below; §486 now binds absolutely
   per spec.md's corrected precedence ruling (charter > operator standing orders > CLAUDE.md).

### Reconciling change-scope tensions (RECONCILE_CHANGE_SCOPE_TENSIONS)

Smallest-viable-diff picks the seven-file set (spec.md §106, restated in "§106 change-scope
reconciliation" below — this is a restatement/confirmation, not a fresh derivation). Boy Scout Rule
then governs cleanup strictly inside that set: the docstring rewrite in
`test_dossier_emitter_positional_guard.py` (FR-003) is exactly this — proportional tidy-up of a
file already being touched for the functional change, not a new file added to the set. Locality of
Change is the brake: nothing beyond the seven files is touched — `commitlint.config.cjs` was
considered (Grounding Correction 4) and deliberately rejected as an addition to the file set in
favor of the smaller, more-correct fix confined to `mission_record_analysis.py`.

### Doctrine drift noted

`~/.hermes/skills/sk/references/review-overlay.md`'s Plan `verify` row still lists "SonarCloud
Quality Gate" among gates to state for a PR. This is stale doctrine for this repo's current CI:
verified directly against `.github/workflows/ci-quality.yml` this session, the `sonarcloud` job
(`if: always() && (github.event_name == 'schedule' || github.event_name == 'workflow_dispatch')`)
does not run on `pull_request` events at all, and no other workflow runs Sonar on a PR. A
missing/absent Sonar check on this mission's PR is therefore **expected, not a gap** — recorded
here so it survives into the review trail rather than being silently re-flagged downstream.

## Project Structure

### Documentation (this mission)

```
kitty-specs/dossier-guard-reexport-analyze-cleanup-01M0NHRT/
├── plan.md                       # This file
├── tracer-tooling-friction.md    # Seeded pre-plan (F-01, F-02)
├── tracer-approach.md            # Seeded this planning pass
├── tracer-design-decisions.md    # Seeded this planning pass
└── tasks.md                      # Phase 2 output (/spec-kitty.tasks — NOT created by this plan)
```

No `research.md`, `data-model.md`, `contracts/`, or `quickstart.md` are generated — see "Phase 0/1
artifacts" below.

### Source Code (repository root)

This mission edits seven existing files in place; no new source directories or modules.

```
src/specify_cli/
├── dossier/
│   └── __init__.py                              # FR-005: remove 7 type re-exports
├── analysis_report.py                            # FR-007/NFR-002: governing-root-relative paths
└── cli/commands/agent/
    └── mission_record_analysis.py                # FR-006: conforming commit subject

tests/
├── architectural/
│   └── test_dossier_emitter_positional_guard.py  # FR-001–FR-004: widen guard + RED-first fixtures
└── specify_cli/
    ├── test_analysis_report.py                   # Update 2 of 5 charter-path assertions
    ├── test_analysis_report_charter_yaml_staleness.py  # Update 3 of 5 charter-path assertions
    └── cli/commands/agent/
        └── test_mission_record_analysis.py       # FR-006: RED-first commit-subject fixture (T010)
```

**Structure Decision**: Option 1 (single project) — this is spec-kitty's own existing
`src/specify_cli/` + `tests/` layout; no new top-level directory, no web/mobile split applies.

### Seam (explicit, per plan content requirements)

This mission is entirely within the `specify_cli` CLI-tooling layer:
`src/specify_cli/dossier/`, `src/specify_cli/analysis_report.py`,
`src/specify_cli/cli/commands/agent/`, plus `tests/`. No kernel (`src/kernel/`), no doctrine schema
(`src/doctrine/`, `packs/built-in/`), no orchestrator-api surface (`src/specify_cli/orchestrator/`
or equivalent) is touched. No new modules — all seven edits are in-place to existing files, named
verbatim in spec.md's §106 section:

1. `tests/architectural/test_dossier_emitter_positional_guard.py`
2. `src/specify_cli/dossier/__init__.py`
3. `src/specify_cli/cli/commands/agent/mission_record_analysis.py`
4. `src/specify_cli/analysis_report.py`
5. `tests/specify_cli/test_analysis_report.py`
6. `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py`
7. `tests/specify_cli/cli/commands/agent/test_mission_record_analysis.py`

### Generated artifacts

None of the seven touched files are generated (no codegen, no template-rendered output, no
doctrine-schema-derived file). The CI step "Verify generated doctrine schemas are up to date" is
enforced but trivially unaffected here — nothing schema-shaped changes in this mission.

### Contracts

The `spec_kitty_events` vendored/external package itself is untouched by this mission — FR-005
removes a *re-export* inside `specify_cli/dossier/__init__.py`, not any type or function in
`spec_kitty_events` itself. Zero external callers of the removed re-export path were verified (spec
SC-003: `grep -rn "from specify_cli.dossier import"` filtered to the seven names, zero matches
before and after). No version bump is needed anywhere — no contract moves.

### Upgrade/migration chain

Not touched. No migration file, no `AGENT_DIRS`/agent-directory change, no config-schema change.
One line, as required: this mission has zero interaction with `src/specify_cli/upgrade/`.

## Phase 0/1 artifacts — explicit disposition

Per the plan step's own commit-boundary and phase framing: Phase 0 (`research.md`) exists to
resolve `[NEEDS CLARIFICATION]` markers, and Phase 1 (`data-model.md`/`contracts/`/`quickstart.md`)
exists to extract new entities, invariants, state transitions, and API contracts. This mission
opened zero `[NEEDS CLARIFICATION]` markers (spec.md's Clarifications/Decision-Record section
settles every open question via D1–D3, §486, §106, §581, and Grounding Corrections 1–4), introduces
no new persistent entity (`AnalysisReportResult.input_artifacts`, `PositionalCallViolation`, and
`specify_cli.dossier.__all__` are all pre-existing, per spec.md's Key Entities section — this
mission changes field *semantics*, not shape), and adds no API/contract surface. Generating
`research.md`/`data-model.md`/`contracts/`/`quickstart.md` here would therefore either restate
spec.md's own Grounding Corrections under a different filename or fabricate content for a design
question this mission does not have. This section states that disposition explicitly rather than
silently omitting the artifacts.

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified*

No violations. No new project, no repository-pattern-style indirection, no fourth "project" added
— all seven edits stay inside the existing single-project structure.

## Gate set for this mission (verified against `.github/workflows/ci-quality.yml` this session)

**Enforced, in the `lint` job (all steps `if: always()`, i.e. run regardless of earlier failures):**

- `[ENFORCED] Run commit message linting` (commitlint) — directly exercised by FR-006/SC-005; this
  is the gate #3678 currently fails and this mission fixes.
- `[ENFORCED] Run markdown style linting on changed files` — applies to this mission's own
  planning artifacts (plan.md, the two new tracer files) if they match the changed-markdown filter.
- `[ENFORCED] Run architecture/docs consistency tests on changed markdown` — same scope note.
- `[ENFORCED] Run template/compat regression tests on matching changes` — not expected to trigger;
  no template file is touched.
- `[ENFORCED] Check Contextive glossary files are up-to-date` — not expected to trigger; no new
  domain term is introduced by this mission's seven-file diff.
- `[ENFORCED] banned-API lint gate (TID251)` — applies generically to all Python changes; no banned
  import is introduced by any of the four fixes.
- `[ENFORCED] Typer 0.26 JSON error surface` — applies generically; no CLI command signature or
  error-surface shape changes in this mission.
- `[ENFORCED] Run Bandit security scan` — applies generically; no new subprocess/eval/pickle-style
  surface introduced (the FR-006 change only changes a string literal; FR-007 only changes how a
  `Path` is stringified).
- `[ENFORCED] Run pip-audit CVE scan` — applies generically; no dependency added or upgraded (see
  Technical Context).
- `[ENFORCED] Validate patch() target strings (closes #394)` — applies if any test uses
  `unittest.mock.patch`; test-file edits here are assertion updates, not new patch targets.
- `[ENFORCED] Verify generated doctrine schemas are up to date` — trivially unaffected (see
  "Generated artifacts" above).

**Enforced, separate jobs:**

- `uv-lock-check` (uv.lock/pyproject.toml sync) — not expected to trigger; no dependency change.
- `deferral-consistency-check` (FR-016, ci-quality.yml:602-611) — unconditional on every PR (no
  `changes`-filter gate at all) and a `quality-gate.needs` member; not expected to trigger a
  failure here since this mission has no `acceptance-matrix.json` with a
  `deferred_to_consolidation` invariant to leave dangling.

**Advisory / INFO (run but do not gate, despite running):**

- `[INFO] Run ruff report (advisory)`
- `[INFO] Run mypy report (advisory)`

(SC-007 nonetheless commits to zero *new* ruff/mypy issues on the seven touched files as a mission
success criterion, even though the CI gate itself is advisory — a stricter self-imposed bar than
CI requires.)

**Not gating this mission (explicit reasoning, not silent omission):**

- `kernel-tests` (90% coverage floor, `module-kernel.yml`) — does not gate. `kernel-tests`
  triggers solely on the `kernel` filter group (`src/kernel/**`/`tests/kernel/**`); none of the
  seven touched files live under `src/kernel/`, and the module-coverage shard's path filter never
  activates for this diff.
- `sonarcloud` — does not gate any PR (see "Doctrine drift noted" above); its absence on this
  mission's PR is expected CI behavior, not a missing check to chase.

**Runs and gates this mission, but its floor is not at risk (corrected — verified against
`.github/workflows/ci-quality.yml` this session):**

- `mission-loader-coverage` (90% coverage floor via `--cov-fail-under=90`, ci-quality.yml:1437) —
  the job **WILL run** on this PR: its `if:` condition is a three-way OR
  (`next || core_misc || platform`, ci-quality.yml:1441-1442), and `core_misc` — one of the seven
  touched files' own filter group — is tripped by
  `tests/architectural/test_dossier_emitter_positional_guard.py` matching `core_misc`'s
  `tests/architectural/**` glob (ci-quality.yml:353). It is also a `quality-gate.needs` member
  (ci-quality.yml:4275), i.e. a genuinely blocking check, not merely informational. The 90% floor
  itself is nonetheless **not at risk**: none of the seven touched files live under
  `src/specify_cli/mission_loader/`, so the job's own coverage measurement is unaffected by this
  diff — the job runs and gates, but is expected to pass trivially.

## Coverage floors

- `kernel-tests` (90% floor) is held **N/A for this mission** — its path-filter surface
  (`src/kernel/`) does not intersect any of the seven files this mission changes, and (per "Gate
  set" above) the job does not even trigger for this diff.
- `mission-loader-coverage` (90% floor) DOES trigger and gate this PR (see "Gate set" above), but
  is likewise **not at risk**: its path-filter surface (`src/specify_cli/mission_loader/`) does
  not intersect any of the seven files this mission changes, so the floor is exercised (the job
  runs) without being raised or put at risk by this diff.

## Baseline (charter Standing Order #9, §486 corrected precedence — binding)

Baseline capture command, to be run by the implementing WP(s) **before the first change lands**:

```bash
pytest tests/architectural/test_dossier_emitter_positional_guard.py \
       tests/dossier/test_events.py \
       tests/architectural/test_no_dead_symbols.py \
       tests/specify_cli/test_analysis_report.py \
       tests/specify_cli/test_analysis_report_charter_yaml_staleness.py -q
```

Record the pass/fail result of this exact invocation (or a more precise variant the implementing
WP finds, noted as a deviation with reason) in the tasks/WP trail before the first implementation
commit, so no pre-existing red is later mistakenly attributed to this mission.

**Disposition rule**: `main` carries ~23 known-red tests + 2 errors under issue #3284 (confirmed
OPEN). §486 now binds absolutely for this mission (spec.md's corrected precedence: charter >
operator standing orders > CLAUDE.md):

- Any red found in this baseline run that is genuinely inside #3284's already-reported set →
  cite #3284, file nothing new.
- Any red found in this mission's touched-test-surface that is **not** inside #3284's set → file a
  new GitHub issue, charter-compelled (not an operator-escalation candidate), including: the exact
  command run, the failure summary, and the reasoning for believing it is pre-existing rather than
  introduced by this mission.
- Zero such out-of-set failures were found during spec authoring (spec.md's own re-verification,
  round 3) — the baseline run above is the WP's own independent confirmation, not a rubber stamp
  of that earlier finding.

## §591 ATDD-First sequencing (C-011, binding)

1. **RED-first commit** — add the two new positive-control fixtures (attribute-chain call,
   aliased-import call) to `test_dossier_emitter_positional_guard.py`, following the exact fixture
   idiom `test_detector_flags_planted_positional_call` already uses. Run them against the CURRENT
   (pre-widening) `_call_target_name` (lines 92–96, matches only `ast.Name`) and confirm RED. Commit
   this as its own commit, **before** any implementation commit.
2. **GREEN implementation commit** — widen `_call_target_name` (or the surrounding scan logic in
   `_violations_in_tree`/`_find_positional_emitter_calls`) to resolve attribute-chain final names
   and single-level import aliases, plus update the docstring (FR-003/SC-008: the exact phrases
   `explicitly deferred` and `` none exist in ``src/`` today `` must no longer appear). Re-run the
   same two tests to confirm GREEN, plus the four pre-existing tests
   (`test_src_tree_has_no_positional_dossier_emitter_calls`,
   `test_detector_flags_planted_positional_call`, `test_detector_does_not_flag_keyword_only_call`,
   `test_detector_ignores_unrelated_same_name_free_function`) still green (NFR-003).

A reviewer must be able to verify **RED on `planning_base_branch` and GREEN on final** — i.e.
checking out the commit immediately before the GREEN implementation commit and re-running the two
new tests must reproduce RED; checking out final must reproduce GREEN. This is stated using that
exact framing so the review squad can mechanically re-run it.

## §106 change-scope reconciliation (restatement, not fresh derivation)

Citing spec.md's own §106 section directly — this plan restates and confirms it, it does not
re-derive it:

| File | One-line rationale |
|---|---|
| `tests/architectural/test_dossier_emitter_positional_guard.py` | #3676's own named defect; the guard's docstring itself documents the two gaps this mission closes. |
| `src/specify_cli/dossier/__init__.py` | #3677's own named defect; the sole surface with the duplicate import path. |
| `src/specify_cli/cli/commands/agent/mission_record_analysis.py` | #3678's own named defect; the sole call site constructing the non-conforming commit message. |
| `src/specify_cli/analysis_report.py` | SK-63's path-relativization half (D3-folded); the actual four absolute-path write sites the mission brief mis-attributed to `mission_record_analysis.py`. |
| `tests/specify_cli/test_analysis_report.py` | Direct, necessary consequence of FR-007 — 2 of the 5 affected charter-path assertions live here. |
| `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py` | Direct, necessary consequence of FR-007 — 3 of the 5 affected charter-path assertions live here. |
| `tests/specify_cli/cli/commands/agent/test_mission_record_analysis.py` | FR-006's RED-first fixture (T010) needs a landing spot for `mission_record_analysis.py`'s commit-message construction; this is the sole existing test module for that command, disjoint from WP01's two `test_analysis_report*.py` files (added post-tasks, TASKS-DECOMP-001). |

Tracker references: #3676, #3677, #3678, ledger SK-63, ledger SK-64 (Grounding Correction 4 — the
first-hand SK-64 investigation that established the `docs(...)`-subject fix direction this mission
adopts).

## Campsite-clean — explicit call

**Not warranted as a distinct commit.** See "Quality & Tech-Debt Standing Orders — applied", item 2
above for the full per-surface reasoning; restated in one line here per the plan content
requirement: no touched surface is a god-surface, and the functional edits on each file already
are the tidy (a shrinking re-export list, a small focused hash-recording helper, a single string
literal, a 5-line callee-name resolver).

## PR shape

**One PR for the whole mission** — the default here, and no per-WP split is warranted. Reasoning:
the total diff across all seven files is small (a docstring + one function widened; seven names
removed from two lists; one f-string; a handful of `_artifact_hash_entry`/`_charter_path`/
`collect_input_artifact_hashes`/`check_analysis_report_current` edits; five test assertions
updated; one new RED-first fixture added to the 7th file's test module), the topology is
`single_branch` (fixed at scaffold time per spec.md D2, not
re-litigated), and the four defects — while independently diagnosed as separate GitHub issues —
share enough call-path/file overlap (SK-63 and #3678 are both in the `record-analysis` write path)
that reviewing them together costs less than context-switching across four small PRs. A per-WP
split would only pay off if gating each defect's CI status independently mattered; it does not
here — commitlint (#3678) and the path leak (SK-63) must both be green in the same run anyway
since they share `mission_record_analysis.py`'s call into `analysis_report.py`.

## Write scopes / open-PR-overlap check

Checked via `gh pr list` + `gh pr diff <n> --name-only` against all seven touched files this
session: 14 open PRs total. Only PR #3672 (`refactor/dossier-emitters-canonical-only-1058`, our
own stacked parent per spec.md D2) touches one of the seven files
(`tests/architectural/test_dossier_emitter_positional_guard.py`) — expected, since it IS this
mission's base branch, not a concurrent lane. **No concurrent lane conflict exists** — no other
open PR touches any of the seven files. **Re-verified during the round-2 fix pass (2026-08-23,
TASKS-FRESH-001)** specifically for the 7th file
(`tests/specify_cli/cli/commands/agent/test_mission_record_analysis.py`), added to this mission's
scope post-tasks (TASKS-DECOMP-001) after this check was first run: re-ran `gh pr list` (still 14
open PRs) and `gh pr diff <n> --name-only | grep -i test_mission_record_analysis` against each of
the 14 PR numbers — zero matches in every case. No open PR touches the 7th file either; the
original "no concurrent lane conflict" conclusion holds for the full seven-file set, not merely
asserted to still hold.

## Test strategy per FR/AC (concrete, file:line-grounded)

| Requirement | Proving test(s) |
|---|---|
| FR-001 (attribute-chain detection) | New fixture in `test_dossier_emitter_positional_guard.py` asserting `_find_positional_emitter_calls` reports exactly one violation for `dossier.emit_artifact_indexed("m","k","c","p","h",1)` (spec US2 AC1). RED pre-widening, GREEN post. |
| FR-002 (aliased-import detection) | New fixture asserting one violation, correctly attributed to `emit_artifact_indexed`, for `from ...dossier.events import emit_artifact_indexed as ei; ei(...)` (spec US2 AC2). RED pre-widening, GREEN post. |
| FR-003 (docstring no longer frames gaps as deferred) | `grep -n 'explicitly deferred\|none exist in ``src/`` today' tests/architectural/test_dossier_emitter_positional_guard.py` returns zero matches post-change (SC-008). |
| FR-004 (RED-first fixtures exist and prove the widening) | The two new tests themselves, run against both the pre-widening and post-widening `_call_target_name` (SC-001). |
| FR-005 (7 type re-exports removed, 4 `emit_*` untouched) | `tests/dossier/test_events.py` (sole existing consumer of the 7 names, imports them directly from `spec_kitty_events`, unaffected — spec US3 AC3) re-run unmodified and green; `grep -rn "from specify_cli.dossier import"` filtered to the 7 names, zero matches before and after (SC-003); `tests/architectural/test_no_dead_symbols.py` re-run green before and after (SC-004, NFR-004); manual read-diff confirming the four `emit_*` names remain in both the import statement and `__all__`. |
| FR-006 (conforming commit subject) | `commitlint --from <parent-sha> --to <analysis-commit-sha>` on this mission's own `record-analysis` commit, reporting 0 problems, without any `commitlint.config.cjs` change (SC-005) — see "SK-63 interaction / Reflexivity" below for when this actually runs. |
| FR-007 (governing-root-relative paths, raise on failure) | The five updated assertions in `test_analysis_report.py`/`test_analysis_report_charter_yaml_staleness.py`, now asserting the `canonical_root`-relative string (each fails against the OLD absolute-path behavior — revert discipline, see below); two new, independently-reportable test functions constructing an unrelativizable-path condition — `test_write_analysis_report_raises_on_unrelativizable_path` for `write_analysis_report` (raises/reports) and `test_check_analysis_report_current_reports_relativization_failure_without_raising` for `check_analysis_report_current` (returns typed `AnalysisFreshness(ok=False, reason=...)` without raising) — these are the two NFR-002 test functions (mirrors `tasks/WP01-sk63-path-relativization.md` T002/T003/T004). |
| NFR-001 (no absolute path in committed artifact) | `grep -E '"path":\s*"(/home|/Users)/' <freshly generated analysis-report.md>` returns zero matches (SC-006) — run as part of the same integration test that exercises `write_analysis_report` end to end. |
| NFR-002 (non-raising contract preserved) | The same two NFR-002 test functions above, each independently reportable: `test_write_analysis_report_raises_on_unrelativizable_path` asserts `write_analysis_report` raises/surfaces an explicit error on an unrelativizable `spec.md`/`plan.md`/`tasks.md` path; `test_check_analysis_report_current_reports_relativization_failure_without_raising` asserts `check_analysis_report_current` returns `AnalysisFreshness(ok=False, reason=...)` — never raises — for the equivalent condition. Deliberately split into two separate `def test_...` functions (not one combined test), since a single combined function cannot report "half passing" in pytest — it would still FAIL/ERROR as a whole once only one half's behavior starts passing (`write_analysis_report` may raise per NFR-002; `check_analysis_report_current` may not — the two halves of the same contract split, proved by two independently-green functions). |

## Revert discipline

Every changed behaviour gets a test that fails when the change is reverted:

- **Two new guard fixtures** (FR-001/FR-002) — RED-first already covers this by construction: they
  are RED against the reverted (pre-widening) code path.
- **Five updated charter-path assertions** (FR-007) — these are modifications of existing tests, so
  revert discipline here means: the NEW assertion (asserting the `canonical_root`-relative value)
  fails if FR-007 is reverted (the old code would produce the absolute path again, and the new
  assertion would then compare a relative string against an absolute one and fail).
- **FR-006 commit-subject fix** — proven by actually running commitlint against a real
  `record-analysis` commit (SC-005's Independent Test framing), not a unit-level string-shape
  assertion alone; a unit test asserting the constructed `message=` string matches the
  `docs(<scope>): <subject>` shape is the fast/local proxy, but the authoritative evidence is the
  live commitlint run — both are in scope for the implementing WP.
- **NFR-002 raising/non-raising test functions (two, independently reportable)** — by
  construction: `test_write_analysis_report_raises_on_unrelativizable_path` directly asserts the
  raise in `write_analysis_report`, and
  `test_check_analysis_report_current_reports_relativization_failure_without_raising` directly
  asserts the typed non-raising result in `check_analysis_report_current`; either would silently
  regress to "write absolute path anyway" if the fix were reverted, and each function reports its
  own regression independently.

## Public-repo / NFR-001 verification (concrete command, part of test strategy)

```bash
grep -E '"path":\s*"(/home|/Users)/' <analysis-report.md path>
```

Expected: zero matches, run against a freshly generated `analysis-report.md` as part of the
integration test proving FR-007/NFR-001 (not merely restated as a requirement — this is the actual
command the implementing WP's test executes).

## SK-63 interaction (process note for the analyze phase, not a plan requirement)

When this mission's own analyze phase runs (after tasks), `tracer-tooling-friction.md`'s F-02
mitigation applies: verify the `record-analysis` commit via `git log`/`git ls-tree` on the branch,
never by trusting `{"success": true, ...}` alone, since SK-63's still-open retry/backoff half can
print success and then hang before committing. This is a process note for whoever runs the
implementing/analyze phase — it is not a plan requirement to fix SK-63's other half, which stays
explicitly out of scope for this mission per C-003/D3. (For what to do if the `record-analysis`
commit's *content* — not SK-63's hang/false-success behavior — turns out wrong, see the recovery
path in "Reflexivity" below: that half is a plan requirement.)

## Reflexivity

This mission's own `record-analysis` invocation, later in its own lifecycle, is the first
real-world exercise of the FR-006/FR-007 fix. If the fix is wrong, this mission's own analyze-phase
commit will demonstrate it live — a built-in acceptance check worth naming explicitly: a failing
commitlint run or a leaked absolute path in this mission's own `analysis-report.md` would be direct,
first-party evidence the fix did not work, discovered before the PR is even opened.

**Recovery path (binding, not left to improvisation):** if this mission's own `record-analysis`
commit fails commitlint, or its `analysis-report.md` still contains an absolute username-bearing
path after FR-006/FR-007 have supposedly landed, that is treated as FR-006/FR-007 **not yet done** —
not a pre-existing/unrelated failure to note and move past. Fix forward within this same mission
(amend IC-03's implementation) before proceeding to PR-prep. Do not open the PR with a
known-failing self-test; the analyze phase does not get marked complete on a failing self-exercise
of this mission's own deliverable.

The RED-first fixture that proves the fix-forward differs by which half failed — these are two
different code paths (FR-006's commit-subject string vs. FR-007's path-relativization logic) and
must not be collapsed into one generic instruction:

- **If the `analysis-report.md` leak is what failed (FR-007/NFR-002)**: extend the relevant one of
  the two existing NFR-002 test functions (described in "Test strategy per FR/AC" above —
  `test_write_analysis_report_raises_on_unrelativizable_path` if `write_analysis_report`'s raise
  is what's wrong, or `test_check_analysis_report_current_reports_relativization_failure_without_raising`
  if `check_analysis_report_current`'s non-raising result is what's wrong; extend both only if both
  are implicated) with a case reproducing this mission's own observed failure shape, confirm it is
  RED against the currently-landed IC-03 implementation, then amend that implementation until it
  is GREEN — the same RED-first discipline §591 applies to IC-01.
- **If the commit-subject fails commitlint (FR-006)**: this is not a case either NFR-002 test
  function touches at all. Add a RED-first fixture that runs the repo's real `commitlint` invocation against
  the actual failing subject string (per SC-005's live-commitlint acceptance method, not a
  unit-level string-shape assertion alone) BEFORE amending `mission_record_analysis.py`'s
  `message=` construction — confirm that fixture is RED against the failing subject, then amend the
  implementation until `commitlint` reports 0 problems.

## Implementation Concern Map

> Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs — one concern may become
> multiple WPs; multiple small concerns may merge into one WP.

### IC-01 — Widen the dossier-emitter positional-call guard

- **Purpose**: Close the attribute-chain and aliased-import detection gaps the guard's own
  docstring currently documents as deliberately deferred, with RED-first proof.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004; NFR-003; SC-001, SC-002, SC-008.
- **Affected surfaces**: `tests/architectural/test_dossier_emitter_positional_guard.py` only.
- **Sequencing/depends-on**: none — fully independent of IC-02/IC-03. Internally sequenced
  RED-first (fixtures) then GREEN (widening + docstring), per §591 above.
- **Risks**: A too-eager attribute-chain matcher could introduce false positives against real
  `src/` code using unrelated `.emit_x`-shaped attribute access on unrelated objects; mitigated by
  re-running `test_src_tree_has_no_positional_dossier_emitter_calls` and the negative-control test
  (`test_detector_ignores_unrelated_same_name_free_function`) after the widening (NFR-003).

### IC-02 — Trim the dossier CLI re-export surface

- **Purpose**: Remove the second import path to seven `spec_kitty_events` types, restoring single
  canonical authority.
- **Relevant requirements**: FR-005; NFR-004; SC-003, SC-004.
- **Affected surfaces**: `src/specify_cli/dossier/__init__.py` only.
- **Sequencing/depends-on**: none — fully independent of IC-01/IC-03.
- **Risks**: Low — verified zero external callers (SC-003); the dead-symbol gate's self-referential
  blind spot (Grounding Correction 2) means it gives zero signal either way and is re-run purely as
  an empirical confirmation, not because it is expected to catch anything.

### IC-03 — Fix the record-analysis commit subject and input-artifact path recording

- **Purpose**: Make the `record-analysis` commit pass commitlint without an ignore-list change, and
  stop writing absolute local filesystem paths into a committed public artifact, while preserving
  `check_analysis_report_current`'s non-raising contract and the existing #1823 cross-root charter
  behavior.
- **Relevant requirements**: FR-006, FR-007; NFR-001, NFR-002; SC-005, SC-006.
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/mission_record_analysis.py`,
  `src/specify_cli/analysis_report.py`, `tests/specify_cli/test_analysis_report.py`,
  `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py`,
  `tests/specify_cli/cli/commands/agent/test_mission_record_analysis.py` (the 7th file, added
  post-tasks per TASKS-DECOMP-001 for FR-006's RED-first commit-message-construction fixture,
  T010 — WP03 traces to this concern in `wps.yaml`).
- **Sequencing/depends-on**: none against IC-01/IC-02. Internally, the FR-007 path-relativization
  change and its five test-assertion updates are tightly coupled (the assertions cannot go green
  independently of the implementation change) and should land together; FR-006's commit-subject
  change is independent of FR-007 within this concern and could be split into its own WP if task
  planning finds that useful, since both live in the same file family but touch disjoint code
  paths (`mission_record_analysis.py`'s `message=` string vs. `analysis_report.py`'s hash-entry
  helpers).
- **Concrete shape (binding — ONE shape, restructured out of the prior ambiguous Risks paragraph
  per review finding PLAN-FRESH2-001/002; not a menu of options)**:

  1. **`_charter_path` keeps its own resolution logic verbatim; only its return shape changes.**
     `_charter_path(repo_root: Path) -> tuple[Path | None, Path]` now returns
     `(charter_path, canonical_root)` instead of bare `Path | None`. `canonical_root` is exactly
     the value the function's EXISTING body already computes at lines 204–207
     (`resolve_canonical_repo_root(repo_root)`, falling back to `canonical_root = repo_root` on
     `NotInsideRepositoryError`) — that try/except is **untouched**, so
     `test_charter_hash_falls_back_to_repo_root_outside_git`'s underlying fallback behavior is
     preserved unchanged. **Not-found case**: `(None, canonical_root)` when neither
     `canonical_root / CHARTER_YAML` nor `canonical_root / CHARTER_MD` exists. **Found case**:
     `(charter_path, canonical_root)`, where `charter_path` is the resolved `charter.yaml` or
     `charter.md` `Path`. The caller (`collect_input_artifact_hashes`) checks `if charter_path is
     not None`. This resolves PLAN-FRESH2-001: no second `resolve_canonical_repo_root` call is
     introduced anywhere in this fix, so there is no duplicated try/except to get right or wrong —
     the second-call option the prior plan text also offered is dropped entirely, per the review's
     own recommendation, because this single-call tuple shape is strictly safer and makes the
     second option unnecessary.
  2. **`collect_input_artifact_hashes` (217–226) consumes the tuple.**
     `charter_path, canonical_root = _charter_path(repo_root)`. If `charter_path is None`:
     `inputs["charter"] = {"path": None, "sha256": None}` (unchanged from today). Otherwise:
     relativize `charter_path` against `canonical_root` and record the relative string (see the
     shared helper in point 4) plus `_sha256_file(charter_path)` (unchanged — hashing still reads
     the absolute `charter_path`; only the recorded `path` string changes). In practice this
     relativization always succeeds, because `_charter_path` only ever constructs its returned
     `charter_path` as `canonical_root / CHARTER_YAML` or `canonical_root / CHARTER_MD` — never an
     unrelated path — but the shared raise-on-failure helper is used uniformly rather than
     special-cased, so a future change to `_charter_path` cannot silently reintroduce the
     absolute-path leak without the helper catching it.
  3. **`_artifact_hash_entry` (179–185) gains a `governing_root: Path` parameter**:
     `_artifact_hash_entry(path: Path, governing_root: Path) -> dict[str, str | None]`, called for
     `spec.md`/`plan.md`/`tasks.md` with `governing_root=repo_root`. When `path.exists()`:
     relativize `path` against `governing_root` via the same shared helper (point 4); a
     relativization failure raises (spec.md Acceptance Scenario 3 — the hypothetical
     symlink-escaping-`repo_root` case). When `path` does **not** exist: **unchanged from
     today** — still `{"path": str(path), "sha256": None}`, still absolute. This is a deliberate
     non-change, not an oversight: `write_analysis_report` requires all three of
     `spec.md`/`plan.md`/`tasks.md` to exist before it ever calls `collect_input_artifact_hashes`
     (lines 406–409), so this not-exists branch never fires on the path that produces the
     *committed* `analysis-report.md` NFR-001 governs; the only other caller,
     `check_analysis_report_current`, uses the result purely in-memory for staleness comparison
     and never writes it to a committed artifact, so it is outside this mission's NFR-001 scope.
  4. **One shared relativize-or-raise helper** performs `path.relative_to(governing_root)` and
     translates a `ValueError` into the raised exception (point 5) — both call sites (point 2's
     charter branch, point 3's `_artifact_hash_entry`) go through this one helper, so the
     exception type/message is defined once, not duplicated ad hoc per call site.
  5. **Exception type** (unchanged from the plan's prior text — this choice was not flagged by
     review and remains a WP-level implementation choice, not a source of ambiguity the findings
     named): reuse `AnalysisReportError` (`src/specify_cli/analysis_report.py:124`, the repo's one
     existing analysis-report-domain exception) or introduce a narrowly-scoped
     `PathRelativizationError(AnalysisReportError)` subtype — either way, `check_analysis_report_current`'s
     catch (point 6) must be specific to it, never a broad `except Exception:` (narrow catches
     only, per the charter's Sonar expectations).
  6. **Catch site — `check_analysis_report_current` must not let this propagate (NFR-002).**
     Re-verified against the live code (this is a correction to the prior plan text, which
     described this as an existing catch to preserve — it is not; it must be added):
     `check_analysis_report_current` (analysis_report.py:458–544) currently has **no** try/except
     of any kind around its own `collect_input_artifact_hashes` call (line 515). The implementing
     WP must ADD one there — `try: current = collect_input_artifact_hashes(...) except
     <exception type from point 5>: return AnalysisFreshness(ok=False, path=path, stale=True,
     missing=False, reason=<describes the relativization failure>, mismatches={})`. Without this
     addition, the relativization failure propagates out of `check_analysis_report_current` into
     `_require_current_analysis_report` (`cli/commands/agent/workflow.py`) — exactly the
     non-raising-contract regression NFR-002 forbids.
  7. **`write_analysis_report` (line 397) intentionally keeps NO try/except** around its call into
     `collect_input_artifact_hashes` (line 412) — unchanged from the prior plan text, re-verified
     accurate: this is by design, not omission, so the same relativization-failure exception
     propagates there uncaught and satisfies NFR-002 Acceptance Scenario 3 (`write_analysis_report`
     raises/reports on an unrelativizable path).

- **NFR-002 proof shape (binding, updated per round-2 review finding TASKS-FRESH-002 to match the
  tasks-phase fix)**: the NFR-002 proof is TWO independently-reportable pytest functions, not one
  combined test — `test_write_analysis_report_raises_on_unrelativizable_path` (asserts ONLY the
  raising half, point 7 above) and
  `test_check_analysis_report_current_reports_relativization_failure_without_raising` (asserts
  ONLY the non-raising typed-result half, point 6 above), mirroring
  `tasks/WP01-sk63-path-relativization.md`'s T002/T003/T004. This split exists specifically so a
  single failing half cannot mask the other's independently-reportable pytest GREEN/RED state — a
  single combined function would still FAIL/ERROR as a whole even after one half's behavior starts
  passing, which is a worse review/verification signal than two functions with independent
  outcomes. This supersedes any single-test framing implied elsewhere in this Concrete shape.

- **Test-assertion sites this shape touches (cites spec.md Grounding Correction 3; does not
  re-derive it).** Points 1–2 above change `hashes["charter"]["path"]`'s *value* from an absolute
  resolved path to a `canonical_root`-relative string. Per Grounding Correction 3, **all five**
  existing assertions comparing `hashes["charter"]["path"]` (or
  `input_artifacts["charter"]["path"]`) against an absolute path have their *assertion text*
  updated to the `canonical_root`-relative form, while each test's underlying
  resolution/fallback behavior is unchanged and continues to hold:

  - `tests/specify_cli/test_analysis_report.py:238` (`test_charter_hash_resolves_canonical_root_from_worktree`)
  - `tests/specify_cli/test_analysis_report.py:260` (`test_charter_hash_falls_back_to_repo_root_outside_git`)
  - `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py:52`
  - `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py:94`
  - `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py:137`

  This explicitly includes the `:260` fallback test PLAN-FRESH2-001 named: its assertion changes
  from `assert hashes["charter"]["path"] == str(charter_file)` to the `canonical_root`-relative
  equivalent (`canonical_root` there equals the passed `repo_root`, per the outside-git fallback
  in point 1 above, so the expected value is `str(charter_file.relative_to(repo_root))` or the
  implementation's equivalent), while its *fallback* behavior — `_charter_path` degrading to
  `canonical_root = repo_root` outside git — is byte-for-byte unchanged per point 1. Read "must
  stay green" as "the test, updated per Grounding Correction 3 to the relative-path assertion,
  must pass" — **not** as "the assertion text stays literally unchanged." All other assertions in
  each of these five tests (sha256 checks, `"charter" in hashes`, freshness/success checks) are
  unaffected and stay as-is, per Grounding Correction 3.

  **Out of scope, explicitly**: `tests/specify_cli/test_analysis_report.py:416`
  (`assert emitted["path"] == str(report_path)`, inside `test_record_analysis_command_persists_report`)
  is **not** one of the five affected sites and needs no change. Verified against the live code:
  `report_path` there is `feature_dir / ANALYSIS_REPORT_FILENAME` — the analysis-report file's OWN
  location, emitted via `AnalysisReportResult.to_dict()`'s `"path": str(self.path)`
  (`analysis_report.py:91`) through `mission_record_analysis.py`'s `payload = {..., **result.to_dict()}`
  (around `mission_record_analysis.py:388`). This is a different `path` field entirely from
  `input_artifacts[*]["path"]` — `_artifact_hash_entry`/`_charter_path` never touch it, and this
  mission's relativization change does not alter it.
