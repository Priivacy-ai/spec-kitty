# Implementation Plan: Org-Tier `expected-artifacts.yaml` Resolver Anchor Fix

**Branch**: `fix/org-tier-expected-artifacts-3703` | **Date**: 2026-08-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/org-tier-expected-artifacts-unreachable-01M0RMBG/spec.md`
**Planning base branch HEAD**: `c76ce3473` (verified via `git log -1`)

## Summary

`resolve_org_expected_artifacts` (`src/charter/org_expected_artifacts.py:82`) joins
`org_root / mission_type / "expected-artifacts.yaml"`, but every sibling org-tier
resolver in `src/specify_cli/runtime/resolver.py` (`_resolve_asset`, `_resolve_mission_config`)
and the built-in layout it mirrors anchor at `org_root / "missions" / mission_type / ...`.
An org-pack author who lays out their pack the only way the codebase demonstrates gets a
silently-ignored override. The fix is a one-line path-join correction plus a docstring
correction (FR-001/FR-002), with five test files corrected in step so the anchor move does
not regress currently-GREEN coverage to RED (FR-003/FR-004/FR-005). No sibling-fallback to
the old path (C-002, operator-decided). No validator gate (C-003, operator-decided). Exactly
six files touched (C-001).

## Technical Context

**Language/Version**: Python 3.11+ (repo standard; no version change here)
**Primary Dependencies**: `ruamel.yaml` (already imported in the touched module for YAML parsing) — no new dependency
**Storage**: N/A — filesystem path resolution only, no persistence layer touched
**Testing**: pytest, existing `tests/charter/` and `tests/dossier/` suites (unit + a few integration/`git_repo`-marked tests in the dossier files)
**Target Platform**: Linux/macOS/Windows CLI (no platform-specific code touched)
**Project Type**: Single project — this is an internal fix inside spec-kitty's own charter/dossier doctrine-resolution machinery, no new source tree
**Performance Goals**: N/A — no hot-path behavior change beyond correcting which path is checked (same number of filesystem stats per org root)
**Constraints**: C-001 (exactly six files), C-002 (no sibling-fallback), C-003 (no validator gate), C-004 (terminology canon — no practical effect), NFR-001 (ATDD-first for FR-001/002/003's new case), NFR-002 (no new silent-failure mode)
**Scale/Scope**: Six files: 1 production module + 5 test files (3 of which each hold a locally-duplicated fixture helper)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority**: this fix does not introduce a second resolver for org-tier
  `expected-artifacts.yaml` — it corrects the one free-function resolver
  (`resolve_org_expected_artifacts`) to match the anchor every sibling org-tier resolver in
  `resolver.py` already uses. PASS.
- **Architectural alignment**: no CLI command, no new module boundary, no shared-package
  boundary crossed. PASS (see Seam section below).
- **ATDD-first (C-011)**: FR-001/FR-002 and FR-003's new regression case are RED-first per
  NFR-001; FR-003/FR-004/FR-005's fixture-helper corrections are maintenance-only, explicitly
  excluded from RED-first by NFR-001's own text. PASS — see ATDD-First Discipline section.
- **Campsite cleaning**: evaluated below (Campsite-Clean Scope section) — verdict: no
  campsite-clean commit needed, stated explicitly rather than skipped silently.
- No constitution violations requiring Complexity Tracking. That section is left empty below.

## Project Structure

### Documentation (this mission)

```
kitty-specs/org-tier-expected-artifacts-unreachable-01M0RMBG/
├── spec.md                      # Complete, passed, binding (input to this plan)
├── plan.md                      # This file
├── tracer-approach.md           # Seeded this phase
├── tracer-design-decisions.md   # Seeded this phase
├── tracer-tooling-friction.md   # Pre-existing, untouched by this phase
└── tasks.md                     # Phase 2 output (/spec-kitty.tasks — not created here)
```

No `research.md`, `data-model.md`, `quickstart.md`, or `contracts/` are needed: this is a
single-function path-join defect fix with no new data model, no new user-facing entity, and
no new external contract. The one existing "contract" document that names this resolver
(`kitty-specs/up-org-doctrine-consumers-01M05YAB/contracts/org-tier-resolution-contract.md`,
spec.md C-007) is a deliberately frozen historical artifact from a different, already-merged
mission — this mission does not touch it and does not author a new contract file in its own
`contracts/` directory.

### Source Code (repository root)

This is a single-project Python CLI/library repo (`src/`, `tests/`) — no web/mobile split
applies. The concrete files this mission touches, all verified to exist on this checkout:

```
src/charter/
└── org_expected_artifacts.py         # FR-001 (path join), FR-002 (docstring)

tests/charter/
├── test_org_expected_artifacts.py    # FR-003 (helper + 5 hand-built paths + 1 new test case)
└── test_mission_type_profiles.py     # FR-004 (duplicated helper, lines ~996-1010)

tests/dossier/
├── test_manifest.py                  # FR-005 (duplicated helper, lines ~516-524)
├── test_rebaseline.py                # FR-005 (duplicated helper, lines ~494-500)
└── test_indexer.py                   # FR-005 (locally-duplicated method helper, lines ~714-721)
```

No other file is touched. `src/specify_cli/runtime/resolver.py` and
`src/specify_cli/dossier/manifest.py` are read-only references (the sibling pattern FR-001
must match, and the cache whose reflexivity is analyzed below) — neither is edited by this
mission.

**Structure Decision**: Single project, existing structure. The fix lands entirely inside the
already-established `src/charter/` (charter package) and its `tests/charter/` /
`tests/dossier/` test trees — no new directories, no new modules.

## Seam

This change lands entirely inside the `charter`/`dossier` doctrine-resolution machinery —
kernel-adjacent doctrine code, not the CLI, not a sync surface. Concretely:

- The one production file touched, `src/charter/org_expected_artifacts.py`, is a
  free-function module in the `charter` package (per its own docstring: "the free-function,
  sibling-module seam that gives an org pack a way to override
  `<mission_type>/expected-artifacts.yaml`"). It exposes exactly one public symbol
  (`resolve_org_expected_artifacts`, declared in `__all__`) and has two callers:
  `charter.mission_type_profiles._resolve_expected_artifacts_slot` and
  `specify_cli.dossier.manifest.ManifestRegistry.load_manifest` — neither caller's signature,
  call site, or control flow changes; only what `resolve_org_expected_artifacts` returns for
  a correctly-laid-out pack changes (from `None` to the parsed manifest).
- No CLI command is touched: no `typer.Option`, no new/changed command in
  `src/specify_cli/cli/commands/`, no help text, no error message surface. There is no CLI
  surface change here at all, so no CLI reaching into kernel internals is even a risk to
  evaluate.
- No sync surface is touched: nothing under `src/specify_cli/sync/`, no event envelope, no
  `spec-kitty-events` payload shape.
- The five test files touched are pytest fixtures/assertions exercising the same one
  production function (directly, or transitively via `ManifestRegistry.load_manifest`,
  `rebaseline_snapshot_file`, or `Indexer.index_feature` — each of which calls into the fixed
  resolver with no mocking, per spec.md's C-001 rationale for including them).

## Generated Artifacts

Nothing touched by this mission is a generated artifact. Confirmed by inspection of all six
files:

- `src/charter/org_expected_artifacts.py` is hand-authored Python — not a doctrine schema
  (schemas live under `src/doctrine/` / `.kittify/doctrine/`, untouched here), not a
  Contextive glossary file (those are generated by
  `scripts/generate_contextive_glossaries.py` from `glossary/` + `src/specify_cli/` sources —
  this mission touches neither), and not an agent-command copy (those live under `.claude/`,
  `.amazonq/`, etc. per AGENTS.md's template-flow table — this mission touches none of them).
- The five test files are hand-authored pytest modules with hand-written fixture helpers
  (`_write_org_expected_artifacts` / `_write_org_manifest`) — none of them is rendered from a
  template or regenerated by any `spec-kitty upgrade`/`sync` pathway.

A hand-edit here is therefore correct, not a violation: there is no canonical-source rule this
mission's edits could be improvising around, because none of the six files has a canonical
generator upstream of it.

## Contracts

No doctrine schema, mission step contract, action index, orchestrator-api surface, or the
vendored `spec-kitty-events` package moves as part of this mission. `spec-kitty-events` and
`spec-kitty-tracker` are external PyPI contract packages per the charter's Architecture
section — this mission's diff touches neither.

The one existing document that names the resolver by its OLD, pre-fix path is
`kitty-specs/up-org-doctrine-consumers-01M05YAB/contracts/org-tier-resolution-contract.md`
(spec.md C-007's "Contract C-4"). That document is a deliberately frozen historical artifact
from an already-merged mission (`up-org-doctrine-consumers-01M05YAB`) — per repo convention,
mission-scoped historical artifacts under `kitty-specs/<merged-mission>/` are immutable
point-in-time records, not kept in sync with later bugfixes. This mission carries that
decision forward as-is: **that contract file is NOT part of this mission's file set and is
not touched.** (`src/charter/org_expected_artifacts.py`'s own module docstring cites that
frozen document as its "Contract C-4" reference — the docstring correction in FR-002 fixes
the *function's* stated on-disk path, not the frozen historical document's content.)

## Upgrade/Migration Chain

UNTOUCHED by this mission. No migration script under
`src/specify_cli/upgrade/migrations/` is added or modified, no upgrade shim is implicated,
and no `spec-kitty upgrade` behavior changes. This is a pure runtime path-join correction
inside a doctrine-resolution helper that is invoked fresh on every call — there is no
persisted, versioned artifact for a migration to carry forward.

## The Gate Set For This Mission

Verified against this checkout's actual CI configuration (`.github/workflows/ci-quality.yml`,
`.github/workflows/doctrine-charter-tests.yml`, `.github/workflows/module-kernel.yml`), not
assumed.

**In scope — real, path-filter-triggered gates for this diff:**

1. **`fast-tests-charter` + `integration-tests-charter`** (`ci-quality.yml`, gated on the
   `charter` dorny filter: `src/charter/**` + `tests/charter/**`, which this diff hits).
   Invocation:
   `uv run python -m pytest tests/charter tests/specify_cli/charter_freshness tests/specify_cli/charter_lint tests/specify_cli/charter_preflight -m "fast and not windows_ci and not timing" -q --tb=short --cov=charter --cov=specify_cli.charter_runtime --cov-fail-under=55 ...`
   (fast leg) plus the integration leg (`-m 'not windows_ci and (git_repo or integration)'`,
   no coverage floor). The charter package's own coverage floor here is **55%**, not 90% —
   see item 4 below for the real 90% gate that does apply.
2. **`fast-tests-core-misc` (misc shard) + `integration-tests-core-misc` (misc shard)**
   (`ci-quality.yml`) — the `misc` shard's `paths:` list explicitly includes `tests/dossier`
   (verified: `.github/workflows/ci-quality.yml` matrix, `shard: misc`). Triggered by the
   `agent_surface` dorny filter (`src/specify_cli/dossier/**` is a member) or the broad
   `core_misc`/other filters; also runs unconditionally on `push`. Invocation (fast leg):
   `uv run python -m pytest tests/dossier ... -m "fast and not windows_ci and not regression" ...`;
   integration leg swaps to `-m '... (git_repo or integration or architectural) ...'`. No
   per-package coverage floor is enforced in this job (only the aggregate `--cov=specify_cli`
   instrumentation feeding item 4).
3. **`doctrine-charter-tests.yml`** — a dedicated, path-filtered duplicate fast signal,
   triggered by the same `src/charter/**` / `tests/charter/**` paths, running
   `tests/doctrine` + `tests/charter` (+ others) under `-m "fast and not windows_ci and not
   timing"`. This is intentional, precedented overlap with item 1 (documented in the
   workflow's own header comment), not a mistake to fold away.
4. **`diff-coverage` (PR-only, ENFORCED, `--fail-under=90`)** — `src/charter/*` is explicitly
   listed in the job's `critical_paths` array (`.github/workflows/ci-quality.yml`, the
   `diff-coverage` job). **This is the real 90%-floor gate that applies to this mission**: the
   changed lines inside `src/charter/org_expected_artifacts.py` (FR-001's path join, FR-002's
   docstring) must be covered at ≥90% by the union of fast+integration coverage XMLs, via
   `diff-cover ... --compare-branch=origin/<base> --fail-under=90 --include 'src/charter/*'
   ...`. `src/specify_cli/dossier/*` is NOT in that `critical_paths` array, so the dossier
   test-file corrections carry no equivalent enforced-diff-coverage obligation of their own
   (their existing test coverage already exercises the resolver call path).
5. **`lint` job (`ci-quality.yml`)** — runs on every PR unconditionally (no path filter, only
   an `if:` gate on `pr:deferred`/`pr:skip-ci` labels), so it always fires for this PR
   regardless of file set:
   - **`mypy --strict`** (ENFORCED) — `src/charter` is in its target list
     (`uv run python -m mypy --strict src/specify_cli src/charter src/doctrine`). Applicable:
     the FR-001 path-join edit must keep typing clean.
   - **TID251 banned-API lint** (ENFORCED, `ruff check src tests --select TID251`) —
     path-independent, always runs; the six touched files use no banned API today and the fix
     adds none.
   - **`check_patch_targets.py`** (ENFORCED, `patch()` target validation) — path-independent;
     none of the six files use `unittest.mock.patch`, so this is a pass-through, not a
     meaningful check for this diff, but it still runs.
   - **Bandit security scan** (ENFORCED) and **pip-audit CVE scan** (ENFORCED) — both scan
     `src`/the dependency graph unconditionally; this diff adds no new dependency and no new
     security-relevant surface (pure path-string construction), so both are pass-through.
   - **commitlint** (ENFORCED via job outputs feeding the aggregate gate) — applies to this
     mission's own commit messages; real obligation (see Phasing section for the RED/GREEN
     commit shape it must accept).
   - **markdownlint** (ENFORCED) — applies to any `.md` files this mission's commits touch,
     including this `plan.md` and the tracer files under `kitty-specs/` (not just docs/); a
     real, if minor, obligation.
   - **Contextive glossary freshness check** — conditionally SKIPPED for this diff: it only
     runs when the commit range touches `glossary/`, `src/specify_cli/`, or
     `.kittify/traceability/` (verified in the job step's own skip-logging line); this mission
     touches only `src/charter/` and test files, so this check will report "no changes"
     and skip, not silently pass on unrelated grounds.
   - **`ruff check src tests` full report** — explicitly labeled `[INFO] ... (advisory)` in
     the workflow; **not a merge blocker** by the workflow's own annotation. Not counted as a
     required gate.

**Explicitly excluded, with reason:**

- **`make lint`** — the repo's actual lint entry point in CI is the `ruff` step inside the
  `lint` job, and that step is explicitly `[INFO] ... (advisory)` — verified directly in
  `ci-quality.yml`, not merely assumed from the mission-prompt's characterization. Excluded as
  a *required* gate for the same reason the prompt names it advisory; TID251 (a narrower ruff
  selection) is still enforced and is listed above.
- **Kernel coverage ≥90%** — NOT applicable. `module-kernel.yml`'s 90% floor is scoped to
  `src/kernel/**` only (its own path filter and its coverage step both target
  `src/kernel` exclusively) — verified by reading the workflow file directly, not assumed
  from the "kernel-adjacent doctrine code" framing in this mission's own briefing. `src/charter/`
  is a sibling package, not `src/kernel/`, and carries its own, separate 55% floor (item 1
  above) plus the real applicable 90% floor via `diff-coverage`'s critical-path list (item 4).
- **Mission-loader coverage ≥90%** — NOT applicable. That gate
  (`ci-quality.yml`, `mission-loader-coverage` job) is scoped to `src/specify_cli/mission_loader/**`
  and runs only `tests/unit/mission_loader/` + `tests/integration/test_mission_run_command.py`
  — none of this mission's six files are inside that package or those test paths.
- **SonarCloud Quality Gate** — excluded per this mission's own briefing: verified 2026-08-22
  that it does not run on `pull_request`, gated to `schedule`/`workflow_dispatch` only. Not
  re-verified independently in this planning pass (accepted as given, current knowledge).
- **Doctrine schema freshness** — no distinct gate by that name exists in this repo's CI
  beyond the `doctrine-charter-tests.yml` workflow (item 3 above), which runs `tests/doctrine`
  for DRG/overlay freshness as part of its own scope. This mission touches no file under
  `src/doctrine/` or `.kittify/doctrine/`, so no doctrine-schema-specific assertion is at risk
  from this diff; the workflow still fires (path-triggered by `src/charter/**`) but exercises
  pre-existing doctrine coverage, not new coverage from this change.
- **Typer JSON error surface** (`tests/agent/test_json_group_typer_surface.py`, run inside the
  `lint` job) — runs path-independently as part of `lint`, but this mission adds/changes no
  Typer command, so it is a pass-through with nothing new to break; listed here as excluded
  from the *meaningful* gate set rather than omitted from the report.
- **`uv.lock` freshness** — no dependency is added, removed, or version-pinned by this
  mission (confirmed: `pyproject.toml` and `uv.lock` are not in the six-file set), so the
  dedicated freshness workflows (`check-spec-kitty-events-alignment.yml`,
  `release-readiness.yml`) have nothing to react to; the `uv.lock` path trigger on those
  workflows will simply not fire.
- **"We'll run the tests"** is explicitly not a gate statement per this mission's own
  briefing — the concrete invocation commands are named per-gate above, and the same target
  set doubles as the local pre-commit verification command: `pytest tests/charter/test_org_expected_artifacts.py
  tests/charter/test_mission_type_profiles.py tests/dossier/test_manifest.py
  tests/dossier/test_rebaseline.py tests/dossier/test_indexer.py` (SC-003's own invocation).

## Baseline Discipline

`main` (and, by extension, this mission's `c76ce3473` planning-base HEAD, which sits on top of
recent `main` history) carries ~23 known-red tests and 2 errors, tracked as issue #3284
(spec.md C-006). This mission's test runs are not read against a fully-green baseline, and no
duplicate issue is opened for that pre-existing red.

**Mechanism for distinguishing pre-existing red from introduced red, applied BEFORE the first
change lands:**

1. Before any edit, run the mission's full target test surface once on `c76ce3473` (the
   current HEAD of this branch, unmodified):
   `pytest tests/charter/test_org_expected_artifacts.py tests/charter/test_mission_type_profiles.py tests/dossier/test_manifest.py tests/dossier/test_rebaseline.py tests/dossier/test_indexer.py -v`
   and record the pass/fail set by test node ID (this captures the pre-fix baseline, which
   should be entirely GREEN for these five files today — this mission does not expect #3284's
   ~23 known reds to intersect this narrow five-file surface, but the baseline run is what
   confirms that rather than assuming it).
2. After each commit (each RED-first test commit, and each implementation/maintenance
   commit), re-run the same target surface and diff the resulting pass/fail set against the
   step-1 baseline by node ID.
3. A test that is RED after a commit and was GREEN (or absent) in the step-1 baseline is
   attributable to this mission's change and must be resolved (or is the deliberately-RED
   pinning commit under NFR-001, resolved by the next commit).
4. A test that was already RED in the step-1 baseline and remains RED is pre-existing #3284
   territory — left alone, not "fixed" as a drive-by, not attributed to this mission.

**Shared test-venv lock (#3283) capacity signal**: this mission reduces lanes rather than
retrying on timeout — test invocations for this mission's WPs run sequentially against the
shared `.venv`, never launched concurrently against it. If a test invocation appears to hang
or contend on the shared venv, the response is to wait for the prior invocation to complete
(or investigate the specific lock), not to fire a second concurrent `pytest` run as a
workaround.

## Campsite-Clean Scope

Per Standing Order #2 and `RECONCILE_CHANGE_SCOPE_TENSIONS`, the campsite-clean question was
evaluated against the actual six files (all six were read in full or in the cited line ranges
before this plan was written):

- `src/charter/org_expected_artifacts.py` is 120 lines, one small module-level constant, two
  functions (`resolve_org_expected_artifacts` at 39 lines including docstring,
  `_read_yaml_mapping` at 32 lines including docstring), both well under the repo's
  complexity ceiling of 15 (Ruff `C901`/Sonar `S3776`) by inspection — no nested conditionals
  beyond a single `for`/`if`, no long parameter lists, no repeated literal needing a constant
  hoist (the one repeated literal, `_EXPECTED_ARTIFACTS_FILENAME = "expected-artifacts.yaml"`,
  is already hoisted to a module constant). No empty/effect-free exception handler — the one
  `except` clause in `_read_yaml_mapping` does real work (logs and returns `None`).
- The five test files' cited fixture-helper regions (`_write_org_expected_artifacts` /
  `_write_org_manifest`, 8-14 lines each) are equally small, single-purpose, and free of
  duplication beyond the cross-file duplication FR-003/FR-004/FR-005 already exist to correct
  in lockstep (that correction *is* the functional change, not separable Boy-Scout cleanup).

**Verdict: no campsite-clean commit is needed.** This is stated explicitly as a deliberate
finding, not a silently-skipped topic: having read all six files, there is no over-long
function, no stale Sonar finding pointed at in the touched sections, and no dead/duplicated
code inside the touched regions beyond the FR-003/004/005 duplication that the functional fix
itself resolves. No file is added to the six-file set to manufacture cleanup work.

## ATDD-First Discipline (C-011, binding)

Per NFR-001, two RED states are pinned, each as its own failing-first test commit before the
implementation commit that turns it GREEN:

1. **FR-001/FR-002 pair.** RED test: a new (or extended) test in
   `tests/charter/test_org_expected_artifacts.py` that writes a fixture at the CORRECT,
   post-fix location (`<org_root>/missions/<mission_type>/expected-artifacts.yaml`) and
   asserts `resolve_org_expected_artifacts` returns the parsed mapping (not `None`). This
   assertion is mechanically RED on `c76ce3473` today, because
   `resolve_org_expected_artifacts` still joins the old, wrong path
   (`org_root / mission_type / "expected-artifacts.yaml"`, no `missions/` segment) — the new
   test's fixture, written at the corrected location, is invisible to the current
   implementation. Mechanical RED-verification: `git stash` the implementation change (or
   simply commit the test first, before touching `org_expected_artifacts.py`), run
   `pytest tests/charter/test_org_expected_artifacts.py -k <new_test_name> -v` and confirm
   failure; then land the FR-001 path-join + FR-002 docstring commit and re-run the same
   command, confirming pass. The reviewer repeats this same two-command check against the
   WP's first and final commits to verify RED-at-base / GREEN-at-final independently.
2. **FR-003's new old-location-returns-None regression case.** RED test: write a fixture
   ONLY at the OLD, pre-fix path (`org_root / mission_type / "expected-artifacts.yaml"`, no
   `missions/` segment) and assert `resolve_org_expected_artifacts` returns `None`. This is
   RED *before* the fix (today the old path IS found, so it returns the parsed mapping, not
   `None`) and GREEN *after* the fix (the corrected resolver no longer checks the old path at
   all, per C-002's no-sibling-fallback decision). Same mechanical check: commit the test
   before the fix, confirm failure via `pytest tests/charter/test_org_expected_artifacts.py -k
   <new_case_name> -v`; confirm pass after the FR-001 commit lands.

Both RED-first commits land BEFORE the FR-001/FR-002 implementation commit in this WP's commit
sequence (see Phasing below), so a reviewer can `git log` the WP's commits in order and see
test-then-fix for each pinned behavior, exactly mirroring Mission B's 7-file ATDD contract
pattern the charter cites.

**Carried forward from spec.md's NFR-001 exclusion, verbatim in effect:** FR-003's own
helper-join-fix and its five hand-corrected malformed-file test paths (lines documented in
spec.md's FR-003 row: `test_malformed_yaml_file_treated_as_no_match`,
`test_non_mapping_yaml_content_treated_as_no_match`,
`test_malformed_yaml_file_logs_a_warning_naming_the_file`,
`test_non_mapping_yaml_content_logs_a_warning_naming_the_file`,
`test_later_malformed_root_does_not_clobber_earlier_good_match`), plus FR-004's and FR-005's
fixture-helper corrections, are maintenance-only: they must be GREEN at the WP's final commit
(no test deleted, weakened, or skipped — SC-003), but require no RED-first commit of their
own. They are tracking already-passing coverage through the anchor move, not pinning new
behavior — landing them alongside the FR-001/FR-002 implementation commit (or immediately
after, as maintenance) is acceptable; they do not need to precede it as a separate RED step.

## Reflexivity

Carried forward verbatim from spec.md's Edge Cases finding, not re-derived:
`ManifestRegistry._cache` (`src/specify_cli/dossier/manifest.py:183-190`) is a process-local,
in-memory `dict`, never persisted to disk. No currently-shipped long-lived process holds a
stale pre-fix cache entry across the fix boundary — the CLI is per-invocation (fresh process,
fresh empty cache, on every run), and neither `orchestrator_api` nor the dashboard daemon
calls `ManifestRegistry`. **No cache-invalidation step is needed for this fix.** (The five
test files' own `setup_method`/`teardown_method` calls to `ManifestRegistry.clear_cache()`,
where present, are pre-existing per-test isolation hygiene, not something this mission adds or
depends on for correctness.)

## Silent Success

Explicitly stating what the resolver does when it cannot do its job, post-fix, per NFR-002:

- **Legitimately no override exists** at the corrected anchor for a given mission type:
  `resolve_org_expected_artifacts` returns `None`. This is correct "no override" semantics,
  not a bug — a caller's fallback to the built-in manifest (or `None` for a wholly custom type
  with no built-in baseline) is the intended behavior, unchanged by this fix.
- **A malformed file DOES exist** at the corrected anchor (unparseable YAML, or parses to a
  non-mapping): `_read_yaml_mapping` (unedited by this mission — its logic is already correct,
  only the caller's path construction moves) logs `logging.warning`, naming the offending path
  and the parse failure, then falls through as "no match" for that root. This is existing,
  already-tested behavior (`TestResolveOrgExpectedArtifactsMalformedFile` in
  `test_org_expected_artifacts.py`) that must keep passing at the corrected anchor — not new
  behavior this mission builds.
- **No new silent-failure mode is introduced.** The fix moves *where* the resolver looks; it
  does not change *what happens* when what it finds is malformed, or when nothing is found.

## PR Shape

This ships as ONE PR for the whole mission — the default per spec-kitty's accept→merge
machinery, which assumes one mission branch. This is a six-file fix; the work packages below
are phased so the mission's final diff is one reviewable unit (a handful of commits: RED-first
test commits, the FR-001/FR-002 implementation commit, and the FR-003/FR-004/FR-005
maintenance commit(s), landing on the single `fix/org-tier-expected-artifacts-3703` branch).
There is no basis to split this into multiple PRs — six files, one resolver function, and its
direct fixture-helper dependents are well within one reviewable sitting; this plan does not
invoke the escape hatch to propose otherwise.

## Phasing / Work Packages

Rough WP-level shape (tasks.md does the detailed breakdown next phase):

1. **Campsite-clean commit**: NONE — see Campsite-Clean Scope verdict above (explicitly
   decided not needed, not skipped).
2. **RED-first test commit(s) for FR-001/FR-002 and FR-003's new case** (NFR-001): land the
   new/extended test in `tests/charter/test_org_expected_artifacts.py` that (a) asserts a
   fixture at the corrected `missions/<type>/` anchor is found, and (b) asserts a fixture
   ONLY at the old anchor now resolves to `None`. Confirmed RED on `c76ce3473` before
   proceeding.
3. **FR-001 + FR-002 implementation commit**: fix the path join in
   `resolve_org_expected_artifacts` (`src/charter/org_expected_artifacts.py:82`, insert the
   `"missions"` segment to match `resolver.py`'s sibling pattern) and correct the module +
   function docstrings to state the corrected on-disk location. Re-run the WP2 tests and
   confirm GREEN.
4. **FR-003/FR-004/FR-005 maintenance commit(s)** (GREEN throughout, no RED-first commit
   required per NFR-001's exclusion): update the `_write_org_expected_artifacts` /
   `_write_org_manifest` fixture helpers in all five files to write to the corrected anchor;
   hand-correct the five malformed-file test paths in
   `TestResolveOrgExpectedArtifactsMalformedFile` (test_org_expected_artifacts.py) that
   construct their target path directly instead of via the helper; correct the four
   pre-fix-path docstrings named in spec.md's Note (fix round, 2026-08-24) in step with each
   helper's path join.
5. **Gate verification**: run the full target surface
   (`pytest tests/charter/test_org_expected_artifacts.py tests/charter/test_mission_type_profiles.py tests/dossier/test_manifest.py tests/dossier/test_rebaseline.py tests/dossier/test_indexer.py`)
   against the baseline captured per Baseline Discipline above, confirm no new red beyond
   #3284's pre-existing set, then confirm mypy --strict, TID251, and the diff-coverage
   critical-path gate locally before treating the WP as CI-ready (per the named gate set
   above).

## Complexity Tracking

*No constitution violations to justify — this section intentionally left empty.*

## Parallel Work Analysis

Not applicable — this is a single-lane, six-file fix with a strict WP-ordering dependency
(RED-first tests must precede the implementation commit that turns them GREEN; the
maintenance commit for FR-003/004/005 depends on FR-001's path-join landing first, since it is
what the fixture-helper corrections are keeping GREEN through). No parallel work streams are
proposed.
