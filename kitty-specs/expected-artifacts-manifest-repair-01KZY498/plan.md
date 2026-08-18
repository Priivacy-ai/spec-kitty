# Implementation Plan: Expected Artifacts Manifest Repair

**Branch**: `pr/expected-artifacts-manifest-repair-01KZY498` | **Date**: 2026-08-13 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `/kitty-specs/expected-artifacts-manifest-repair-01KZY498/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See
`src/doctrine/missions/mission-steps/software-dev/plan/prompt.md` for the execution workflow.

All planning questions below are answered from direct verification against this checkout
(`main` @ the commit this branch forked from) — every file:line cited was re-read while writing
this plan, not merely copied from the spec. Where the spec's own citations were re-checked and
line numbers had drifted slightly (normal churn), the mechanism and content were confirmed
unchanged; no claim in this plan rests on an unverified path.

## Summary

`expected-artifacts.yaml` is the per-mission-type manifest declaring which artifacts are
expected at each mission step. As shipped it is unreliable on four independent axes: `plan`
mission type ships no manifest at all; the three shipped manifests (`research`, `documentation`,
`software-dev`) diverge from `runtime_bridge_cores.py`'s guard tables on 8 named steps; the
Pydantic schema silently drops typo'd keys (`extra="ignore"` default); and the schema's own
loud-failure promise doesn't reach the one production loading path every real consumer uses.
The technical approach is **content + schema only, no consumer-behavior change**: reconcile
three manifests' YAML content to match guard reality, author a fourth (`plan`) manifest honestly
scoped to `plan` mission type's own state machine, harden the Pydantic schema with
`extra="forbid"`, and complete that hardening's promise through the one real loading path
(`ManifestRegistry.load_manifest()`) with one narrow, output-preserving defensive catch in the
one caller (`resolve_manifest_version()`) whose contract requires it. No runtime guard code
(`runtime_bridge_cores.py`/`_composition.py`/`_io.py`) is touched (C-001); `manifest_version`
stays `"1"` on all four manifests (C-002); the `artifact_key` vocabulary clash and the
override-resolution tier gap are named and explicitly deferred (C-003/C-004).

## Technical Context

**Language/Version**: Python 3.11+ (repo floor per charter; CI runs the pinned 3.12 interpreter
via `uv sync --frozen --all-extras`)
**Primary Dependencies**: `pydantic` v2 (`ConfigDict(extra="forbid")` — the only new API surface
this mission introduces), `ruamel.yaml` (existing manifest YAML parse path in
`ExpectedArtifactManifest.from_yaml_file` / `MissionTemplateRepository`, unchanged), `typer`/
`rich` (untouched — no CLI command surface changes)
**Storage**: N/A — YAML files under `packs/built-in/missions/` and `.kittify/overrides/missions/`,
no database/service storage involved
**Testing**: `pytest`, scoped per NFR-003 to `tests/dossier/`, `tests/doctrine/missions/`,
`tests/runtime/`, `tests/charter/test_resolved_mission_type_context.py` (plus any files FR-015's
audit adds); full `pytest tests/` is NOT run per-WP (charter Testing Requirements guidance for
scoped changes) but IS required once, read-only, before the first change lands (baseline capture
— see "Baseline Capture" below) and again post-merge per the charter's standard close-out
sequence
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows) — unaffected; no platform-specific
code touched
**Project Type**: Single project (existing `src/specify_cli`, `src/doctrine`, `src/charter`
packages) — no new package, no new top-level module
**Performance Goals**: No new perf requirement. `ManifestRegistry.load_manifest()`'s
process-lifetime `_cache` is unchanged; the new `except pydantic.ValidationError` branch in
`resolve_manifest_version()` is a single additional `except` clause on an already-cheap call, not
a new I/O path
**Constraints**: C-001 (content + schema only — no `runtime_bridge_cores.py`/
`runtime_bridge_composition.py`/`runtime_bridge_io.py` changes), C-002 (`manifest_version` stays
`"1"` on all four manifests, sync-namespace identity unchanged), C-003 (`artifact_key` vocabulary
unification out of scope), C-004 (no override-resolution tier wiring for
`expected-artifacts.yaml`)
**Scale/Scope**: 4 YAML manifest files reconciled/authored (3 edits + 1 new), 3 YAML override
mirror files annotated (header comment only), 2 Python files changed
(`src/specify_cli/dossier/manifest.py`, `src/specify_cli/sync/namespace.py`), ~6 test files
touched (1 corrected assertion + new regression coverage across FR-001–FR-016), 1 upstream GitHub
issue filed (FR-011)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority (DIRECTIVE_044).** `packs/built-in/missions/<type>/expected-artifacts.yaml`
  is confirmed the sole *consumed* copy for every reader in this repo (verified:
  `MissionTemplateRepository._expected_artifacts_path()`, `src/doctrine/missions/repository.py`,
  composes only the built-in pack root, no override tier). Decision 4 (mark-deprecated, don't
  refresh) is the DIRECTIVE_044-compliant resolution for the dead `.kittify/overrides/` mirrors —
  refreshing them would be parity-with-a-dead-quirk, the named anti-pattern. **PASS.**
- **Architectural alignment.** No new module; no CLI command reaches into kernel internals; the
  one sync↔dossier import edge this mission touches (`sync/namespace.py` → `specify_cli.dossier.manifest`)
  already exists pre-mission and is not widened — see "Seam" below. **PASS.**
  domain-appropriate rigor.
- **ATDD-first (C-011).** Each WP's red-first test is named per-FR in "Test Strategy" below and
  lands before that WP's own implementation commit: IC-01, IC-02, and IC-03 each carry their own
  new regression tests into `tests/dossier/test_manifest.py`, in distinct named sections
  (`TestSchemaHardeningAndLoudFailure` / `TestManifestReconciliation` / `TestPlanManifest` — see
  the Implementation Concern Map's "Test file ownership" note) so parallel WPs never edit the same
  section. IC-04 is fully independent of IC-01-03 (it touches only `.kittify/overrides/` files) and
  carries its own red-first test, `test_override_mirror_files_carry_deprecation_header` (in its own
  `TestOverrideMirrorDeprecation` section — see "Test file ownership" below), landing before IC-04's
  own header-comment-edit commit, same C-011 discipline as every other IC. IC-05's FR-015 audit and
  its AS7/SC-006 cross-cutting checks are the only concerns that must wait for IC-01-03's content to
  be final, and IC-05's own red-first tests (in the new `test_manifest_guard_parity.py`) land before
  IC-05's own audit/correction commit, same as every other IC. **PASS (planned, corrected structure
  — see PLAN-ARCH-001 fix in the Implementation Concern Map, covering all five ICs, IC-01 through
  IC-05).**
- **Terminology Canon.** No new user-facing prose introduces `Feature`/`feature` for the Mission
  domain object. The four manifest files' new/edited comments and this plan itself use `mission`
  consistently. **PASS.**
- **Silent-success discipline.** This mission's own FR-016 closes exactly this failure class in
  `ManifestRegistry.load_manifest()`; see "Silent Success Accounting" below for what every
  changed path now does on failure. **PASS.**
- **No violations requiring Complexity Tracking.** See that section below — empty by design.

## Project Structure

### Documentation (this mission)

```
kitty-specs/expected-artifacts-manifest-repair-01KZY498/
├── spec.md                        # R1-R6 adversarial-reviewed, gate-passed
├── plan.md                        # This file
├── tracer-approach.md             # Seeded at planning (confirmed present, not recreated)
├── tracer-design-decisions.md     # Seeded at planning (confirmed present, not recreated)
├── tracer-tooling-friction.md     # Seeded at planning (confirmed present, not recreated)
├── checklists/                    # empty — no checklist artifacts required by this mission type
├── research/                      # empty — spec.md's own investigation IS this mission's research;
│                                   #   no separate Phase 0 research.md is needed (see Phase 0 below)
└── tasks.md                       # Phase 2 output (/spec-kitty.tasks — NOT created by this plan)
```

No `research.md`, `data-model.md`, or `quickstart.md` are produced by this plan. Phase 0
("Outline & Research") is a no-op here: the spec's own "Overview", "Non-Gate Consumer Notes",
and the two seeded tracer files already carry every unknown-resolution this mission needed —
re-deriving them into a separate `research.md` would duplicate content, not add it. `data-model.md`
does not apply: this mission edits an existing Pydantic model's `model_config` and YAML content;
it introduces no new entity. `quickstart.md` does not apply: there is no new user-facing workflow
to onboard to — the manifest's consumers are internal Python call sites, not a CLI surface a
person runs by hand.

### Source Code (repository root)

This mission touches an **existing, narrow file set** — no new package, module, or directory.
Every path below was verified to exist on this checkout before being named here.

```
packs/built-in/missions/
├── research/expected-artifacts.yaml        # FR-001 (edit)
├── documentation/expected-artifacts.yaml   # FR-002-FR-005 (edit)
├── software-dev/expected-artifacts.yaml    # FR-006-FR-008 (edit)
└── plan/expected-artifacts.yaml            # FR-010 (NEW FILE)

.kittify/overrides/missions/
├── research/expected-artifacts.yaml        # FR-014 (header comment only; content otherwise untouched)
├── documentation/expected-artifacts.yaml   # FR-014 (header comment only)
└── software-dev/expected-artifacts.yaml    # FR-014 (header comment only)
# No .kittify/overrides/missions/plan/expected-artifacts.yaml is created (FR-010 note). The
# .kittify/overrides/missions/plan/ directory itself already exists (mission.yaml,
# mission-runtime.yaml, README.md, templates/, command-templates/ — present since 2026-04-17)
# but has no expected-artifacts.yaml file; none is added here — the override tier is inert
# for this asset type (C-004), so adding one would create an unconsumed file, not restore
# consistency.

src/specify_cli/dossier/
└── manifest.py                             # FR-009 (model_config extra="forbid" on both
                                             #   ExpectedArtifactSpec and ExpectedArtifactManifest);
                                             #   FR-016 (load_manifest() exception handling —
                                             #   let pydantic.ValidationError propagate instead of
                                             #   the bare `except Exception`)

src/specify_cli/sync/
└── namespace.py                            # FR-016 narrow addition only: one
                                             #   `except pydantic.ValidationError: return "1"`
                                             #   wrapped around resolve_manifest_version()'s
                                             #   existing load_manifest() call — output-preserving,
                                             #   no change to NamespaceRef construction

tests/dossier/
└── test_manifest.py                        # FR-012: correct the FR-006/FR-007-stale
                                             #   test_software_dev_manifest_plan_step_has_plan_and_tasks
                                             #   assertion; add new regression tests for
                                             #   FR-001-FR-005, FR-008-FR-010, FR-016 (both
                                             #   load_manifest() and resolve_manifest_version()
                                             #   fallback behavior)

tests/dossier/... (new fixture(s))          # FR-016: a deliberately typo'd expected-artifacts.yaml
                                             #   fixture, used by the load_manifest()/reconcile/
                                             #   rebaseline regression tests (AS4-AS6)

tests/{reconcile,rebaseline}/ or the         # FR-016 AS5: propagation tests through
  existing coverage for                     #   reconcile.py's ReconciliationResult(status=ERROR)
  cli/commands/reconcile.py,                #   and rebaseline.py's RebaselineOutcome
  dossier/rebaseline.py                     #   (error="reindex_failed: ...") skip path — exact
                                             #   file TBD at /spec-kitty.tasks (existing test files
                                             #   for these two call sites are the natural home;
                                             #   no new test directory needed)

tests/doctrine/missions/test_repository.py  # FR-015 audit: confirm no assertion pins
                                             #   pre-reconciliation manifest content
tests/runtime/test_bridge_cores.py          # FR-015 audit: same
tests/integration/test_research_runtime_walk.py        # FR-015 audit: same
tests/integration/test_documentation_runtime_walk.py   # FR-015 audit: same
tests/charter/test_resolved_mission_type_context.py     # FR-015: this one IS a confirmed real
                                             #   consumer (bundle.expected_artifacts assertions at
                                             #   lines ~160-162 for software-dev) — must still pass
                                             #   after FR-006/FR-007/FR-008 land, not merely audited
```

Explicitly **not touched**, and verified absent from every FR: `src/runtime/next/runtime_bridge_cores.py`,
`runtime_bridge_composition.py`, `runtime_bridge_io.py` (C-001); `src/doctrine/missions/repository.py`
(the loader — its behavior is unchanged, only the YAML content it reads changes);
`src/doctrine/missions/mission-steps/**` (unrelated SOURCE templates — this mission edits pack
*data*, not step-contract templates); `src/doctrine/agent_profiles/**` and
`packs/built-in/agent_profiles/**` (agent profile loader/data — no agent profile is touched by
this mission).

**Structure Decision**: Single project, existing package layout. No new directory is created
except the one new manifest file (`packs/built-in/missions/plan/expected-artifacts.yaml`) and (at
`/spec-kitty.tasks` discretion) a small test fixture for the typo'd-manifest regression case. All
work lands as edits to files that already exist on this checkout, verified above.

## Seam, Canonical Sources, and Contract Stability

### Which seam the change lands on

This mission is **entirely CLI-owned + doctrine-pack-content**, with zero kernel involvement and
zero new runtime coupling:

- **`src/specify_cli/dossier/manifest.py`** — CLI-owned service module (`specify_cli.dossier`
  package). `ExpectedArtifactSpec`/`ExpectedArtifactManifest`/`ManifestRegistry` are all defined
  here. FR-009 and FR-016 are both scoped to this one file's schema and exception-handling code.
  `manifest.py` already calls into the doctrine loader (`charter.missions.MissionTemplateRepository`,
  imported lazily inside `_doctrine_repository()`) — that import edge is pre-existing and
  unchanged by this mission.
- **`src/specify_cli/sync/namespace.py`** — CLI-owned sync-namespace-resolution module.
  `resolve_manifest_version()` already imports `specify_cli.dossier.manifest.ManifestRegistry`
  (a local import inside the function body, pre-existing). FR-016 adds one `except
  pydantic.ValidationError: return "1"` around the existing `load_manifest()` call — no new
  import, no new call target, no widened surface.
- **`packs/built-in/missions/{research,documentation,software-dev,plan}/expected-artifacts.yaml`**
  — doctrine pack *content* (data, not code), consumed via the existing, unmodified
  `MissionTemplateRepository.get_expected_artifacts()` → `_expected_artifacts_path()` chain in
  `src/doctrine/missions/repository.py`. This mission edits the data the loader reads; it does not
  touch the loader.
- **`.kittify/overrides/missions/{research,documentation,software-dev}/expected-artifacts.yaml`**
  — inert mirror copies (confirmed: `_expected_artifacts_path()` composes only the built-in pack
  root, no override tier for this file type). FR-014 adds a header comment only.

**No new module is created.** No CLI command reaches past a service into kernel internals: this
mission touches no `src/kernel/**` file at all (verified — grepped this plan's own file list
above against `src/kernel/`; zero overlap). No unguarded core-loop → sync coupling of the kind
issue **#3290** names (`runtime_bridge` hard-importing `sync.runtime_event_emitter` — an
*unguarded* new coupling in the *opposite* direction, core-loop reaching into sync) is introduced
or altered here: this mission's only sync-adjacent touch is the reverse direction (an existing,
already-present sync→dossier import inside `resolve_manifest_version()`), and it is not widened —
one narrow `except` clause added around a call that already existed. This mission neither fixes
nor worsens #3290; it is unrelated to that coupling class by direction and by file (`#3290` is
`runtime_bridge.py` ↔ `sync/runtime_event_emitter.py`; this mission never touches either file).

### What is generated, and by which command (there is none in scope)

Verified directly, not assumed: `scripts/generate_schemas.py` (the doctrine JSON-schema generator
gated by CI's "[ENFORCED] Verify generated doctrine schemas are up to date" step) contains **zero**
references to `manifest`, `expected-artifact`, or any symbol from `src/specify_cli/dossier/manifest.py`
(`grep -n "manifest\|expected.artifact" scripts/generate_schemas.py` — no hits beyond an unrelated
`"file-patterns"` doc-string literal). `scripts/generate_contextive_glossaries.py` likewise has
**zero** references to `manifest`/`expected-artifact`. Both CI gates (schema freshness, Contextive
glossary) run unconditionally or on a broad path trigger this mission's file changes will satisfy
(`src/specify_cli/**` for Contextive), but **pass as a no-op** for this mission's content — there
is nothing for either generator to regenerate from what this mission changes. **No generated file
is hand-patched by this mission; no codegen command needs to run as part of it.** This confirms
the readiness probe's finding rather than merely repeating it.

### Canonical sources — every path verified to exist on this checkout

- **Mission-step templates (SOURCE, not touched by this mission)**: `src/doctrine/missions/mission-steps/`
  — confirmed present; irrelevant to this mission's blast radius (this mission edits manifest
  *data*, not step-contract prompt templates).
- **Agent profile data (NOT touched by this mission)**: `packs/built-in/agent_profiles/` —
  confirmed present as a sibling directory to `packs/built-in/missions/` (the directory this
  mission *does* touch); no agent profile file is edited.
- **Agent profile loader (NOT touched)**: `src/doctrine/agent_profiles/` — confirmed present;
  irrelevant here (this mission's loader is `src/doctrine/missions/repository.py`, a distinct
  module).
- **This mission's own canonical source/loader split**: manifest **data** lives at
  `packs/built-in/missions/<type>/expected-artifacts.yaml` (confirmed via `ls packs/built-in/missions/`
  → `documentation`, `plan`, `research`, `software-dev`); the **loader** is
  `src/doctrine/missions/repository.py` (confirmed present, 14698 bytes, `MissionTemplateRepository`
  class, `_expected_artifacts_path()` at the cited location); the **schema** is
  `src/specify_cli/dossier/manifest.py` (confirmed present, `ExpectedArtifactSpec`/
  `ExpectedArtifactManifest`/`ManifestRegistry` all defined there, matching the spec's "Key
  Entities" section exactly). No override file exists yet for `plan` and none is created (FR-010
  note, C-004).

### Whether any contract moves

- **Doctrine schemas**: `ExpectedArtifactSpec`/`ExpectedArtifactManifest`'s Pydantic
  `model_config` gains `extra="forbid"` (FR-009). This is a **schema tightening**, not a shape
  change: no field is added, removed, or renamed. Grepped this tree for any writer that
  constructs a manifest dict with extra keys — none found (confirmed in the spec's own "Corrected
  risk framing" section and re-confirmed here by inspecting all four shipped manifests' YAML keys
  against the model's declared fields — every key present is a declared field). All four shipped
  manifests continue to load successfully after hardening (SC-003, AS3).
- **Mission step contracts / action indices**: untouched. This mission edits `expected-artifacts.yaml`
  content, never `mission.yaml` state machines, `step.yaml` contracts, or action-index files.
- **The orchestrator-api surface**: untouched — no `orchestrator-api`-facing endpoint or contract
  reads `expected-artifacts.yaml` (verified: the three live readers named in the spec —
  `dossier.indexer.Indexer`, `sync.namespace.resolve_manifest_version()`,
  `charter.mission_type_profiles._resolve_expected_artifacts_slot()` — are all internal Python
  call graphs, none of them orchestrator-api-exposed).
- **The vendored `spec-kitty-events` package**: untouched. Not imported by any file this mission
  changes.
- **`manifest_version` / sync-namespace identity (Decision 2, C-002)**: explicitly **preserved**,
  not versioned. All four manifests keep `manifest_version: "1"`. `NamespaceRef`'s 5-field
  identity tuple (`src/specify_cli/sync/namespace.py:63`,
  `f"|{self.mission_type}|{self.manifest_version}"`) is byte-identical before and after this
  mission for every mission type, including `plan` — verified in the spec's "Non-Gate Consumer
  Notes" section and not contradicted anywhere in this plan. **This plan does not undo Decision
  2.** No `spec-kitty-saas`-coordinated release is required by this mission, because no sync
  identity key changes.

## Migration / Upgrade Chain Impact

**None of this mission's changes touch a migration.** `src/specify_cli/upgrade/migrations/` is
not in this mission's file set. There is no schema-version bump requiring a migration script
(`manifest_version` stays `"1"` per C-002/Decision 2), so there is no atomicity/idempotence/
dry-run/self-recovery surface for epic #3347 to be concerned with here — this mission adds no new
migration step and does not touch an existing one.

**Reflexivity — what happens to missions mid-flight when this lands**: `ManifestRegistry.load_manifest()`
reads the manifest fresh on each process invocation (subject to its process-lifetime `_cache`, not
a persisted cache across CLI invocations). A mission already planned but not yet at a step whose
manifest content changed sees the corrected artifact set the *next* time the dossier indexer runs
against it — no gate currently blocks on the manifest's content (confirmed: no code in this repo
wires `expected-artifacts.yaml` to a blocking CLI check today; that is the state of the world both
before and after this mission, per the spec's own "Out of Scope" — "Turning the manifest into an
actual completeness gate" is explicitly not done here). So an in-flight mission's *runtime
behavior* (what advances a step) is unaffected; only the dossier indexer's *completeness report*
changes, retroactively describing a mission's history against the corrected artifact set. This is
the intended effect (SC-001's acceptance bar), not a side effect requiring mitigation.

The one place a mid-flight mission *could* newly observe different behavior: if a mission's
`expected-artifacts.yaml`-derived content were ever hand-typo'd (rare — these are shipped,
reviewed files) and had previously silently loaded as `None`/empty, FR-016 makes that now raise
through `reconcile`/`rebaseline` as a structured, visible error instead of silently degrading.
This is the intended fix (User Story 3), not a regression — a currently-broken-but-silent state
becomes a currently-broken-and-visible one. Decision 5 records, honestly, that the sync-pipeline
path (`sync_feature_dossier()` → `trigger_feature_dossier_sync_if_enabled`) does *not* gain this
visibility, because every real caller of the wrapping function discards its return value — this
plan does not claim otherwise and does not widen scope to fix it (see "Out of Scope", C-002's
sync-pipeline-untouched boundary, and Decision 5's rejected-alternative rationale).

## Silent Success Accounting

Per the charter's dominant-failure-mode framing (#3133, #3212, #3282, #3336) and this mission's
own subject matter (a manifest loader swallowing errors into `None`), every changed code path's
failure behavior is stated explicitly:

| Path | Before this mission | After this mission |
|---|---|---|
| `ExpectedArtifactSpec(**typo'd_kwargs)` (direct construction) | Silently succeeds, drops the typo'd field | **Raises** `pydantic.ValidationError` (FR-009) |
| `ExpectedArtifactManifest(**typo'd_kwargs)` (direct construction, top-level key) | Silently succeeds, drops the typo'd field | **Raises** `pydantic.ValidationError` (FR-009) |
| `ManifestRegistry.load_manifest(type)` on a malformed real YAML file | Catches `ValidationError` inside a bare `except Exception`, logs at ERROR, **returns `None`** — indistinguishable from "manifest not found" | **Raises** `pydantic.ValidationError` to the caller (FR-016); the pre-existing `config is None` branch for genuine absence is unchanged and still returns `None` |
| `reconcile.py`'s reconciliation flow, given a malformed manifest | (unreachable before FR-016 — the exception never propagated this far) | **Reports** `ReconciliationResult(status=ERROR, error=...)` via its own pre-existing fail-closed `except Exception` — no new exception handling added to `reconcile.py` itself |
| `rebaseline.py`'s backlog sweep, given a malformed manifest | (unreachable before FR-016) | **Skips** the one bad mission with `RebaselineOutcome(error="reindex_failed: ...")` via its own pre-existing fail-closed `except Exception` — sweep continues for every other mission, not aborted |
| `sync.namespace.resolve_manifest_version()`, given a malformed manifest | Docstring-promised `"1"` fallback was actually unprotected — a raised exception would have propagated to the unrelated outer catch in `trigger_feature_dossier_sync_if_enabled` | **Returns `"1"`** via its own new, dedicated `except pydantic.ValidationError` (FR-016) — the function's own promise is now actually kept by its own code, not an accident of a caller's blanket catch |
| `sync_feature_dossier()` → `trigger_feature_dossier_sync_if_enabled`, given a malformed manifest, reached via the sync-pipeline path | Silently absorbed — no crash, no operator-visible signal (10 confirmed call sites all discard the returned `DossierSyncResult`) | **Unchanged, named explicitly as a residual gap** (Decision 5) — internal fail-close prevents a crash but still does not reach an operator. This mission does not claim to fix this path and does not widen scope to do so (see Decision 5's rejected alternative) |
| `Indexer`'s four `load_manifest()` call sites | N/A — no dedicated handling | **Unchanged, deliberately** — every real caller of `index_feature()` already fail-closes one layer up (verified above); adding redundant per-call-site `except` blocks inside `indexer.py` itself would duplicate existing handling for no behavior change |

**Every changed path now does exactly one of: raise (schema construction, `load_manifest()`),
report (reconcile/rebaseline's structured error results), or explicitly refuse-to-widen-scope
with the gap named in writing (the sync-pipeline residual, Decision 5).** None silently succeeds
where it previously silently failed, except the one residual gap that is named, not claimed fixed.

## Baseline Capture

`main` carries 23 known-red test failures and 2 errors (#3284), plus a shared test-venv lock that
can time out (#3283). Concretely, **before the first functional change lands** (i.e., as the
mission's opening commit, ahead of any FR-001–FR-016 edit), the implementer runs the scoped
validation surface named in NFR-003 —

```
uv sync --frozen --all-extras
uv run python -m pytest tests/dossier/ tests/doctrine/missions/ tests/runtime/ \
  tests/charter/test_resolved_mission_type_context.py -q --tb=short
```

— against the **pre-change** tree (this mission's branch at the commit where `spec.md`/tracer
files landed, before any WP's implementation commit) and records the pass/fail counts verbatim in
that WP's PR-body evidence / the mission's `reviews/` trail. Any red found here is *pre-existing*
and is carried forward as the explicit baseline for every subsequent WP's "zero new failures"
claim (SC-002) — it is never silently attributed to this mission's own changes, and it is never
"fixed" opportunistically as part of this mission's diff (per the charter's red-main discipline:
judge the test, don't retry-to-green, and if a baseline red is discovered that isn't already
tracked by #3284, the Pre-existing Failure Reporting Rule requires filing a GitHub issue for it
before continuing, with the exact command run and why it's judged pre-existing). Because this
mission's own validation surface (`tests/dossier/`, `tests/doctrine/missions/`, `tests/runtime/`,
`tests/charter/test_resolved_mission_type_context.py`) is narrower than the full ~17k-test suite
#3284/#3283 describe, the baseline run above is expected to be fast and is **not** expected to
surface #3284's specific known-reds (those are not concentrated in this mission's four target
directories per the spec's own scoping) — but the run is still required, not assumed clean, so
that if it *does* surface something, that something is captured before, not after, this mission's
edits.

## Test Strategy Per Acceptance Criterion

Every entry below names the file, the (new or corrected) test, and what it asserts — and
confirms it fails when the corresponding change is reverted (the ATDD red-first bar, C-011).

| AC / FR | File | Test (new unless noted) | Asserts | Fails-on-revert because |
|---|---|---|---|---|
| AS1 (US1, research/gathering, FR-001) | `tests/dossier/test_manifest.py` | `test_research_manifest_gathering_requires_source_register` | `get_required_artifacts(manifest, "gathering")` returns a `source-register.csv` blocking spec; inline comment documents `source_documented_count >= 3` as non-expressible | Reverting FR-001 restores `gathering: []`, so the new spec lookup returns nothing and the test's `len(specs) > 0` / `blocking is True` assertions fail |
| AS2 (US1, documentation/audit+design, FR-002/FR-003) | `tests/dossier/test_manifest.py` | `test_documentation_manifest_audit_design_reconciled` | `audit` requires only `gap-analysis.md` blocking; `design` requires only `plan.md` blocking (no `tasks.md` at either) | Reverting restores the old `plan.md`/`tasks.md` entries at `audit` and the `tasks.md` entry at `design`, tripping an explicit "must NOT contain" assertion |
| AS3 (US1, documentation/validate+publish, FR-004/FR-005) | `tests/dossier/test_manifest.py` | `test_documentation_manifest_validate_publish_reconciled` | `validate` requires `audit-report.md` blocking; `publish` requires `release.md` blocking (both previously `[]`) | Reverting restores empty lists at both steps, failing the "returns exactly one blocking spec" assertion |
| AS4 (US1, software-dev/plan, FR-006) | `tests/dossier/test_manifest.py` | `test_software_dev_manifest_plan_step_has_plan_only` (**replaces** the reverted-shape `test_software_dev_manifest_plan_step_has_plan_and_tasks`, FR-012) | `plan` step requires only `plan.md` blocking; `tasks.md` is **absent** from this step's specs | Reverting FR-006 restores `tasks.md` at `plan`, tripping the new "not present" assertion |
| AS5 (US1, software-dev CLI-native tasks steps, FR-007) | `tests/dossier/test_manifest.py` | `test_software_dev_manifest_tasks_outline_packages_finalize` | `tasks_outline` requires `tasks.md` blocking; `tasks_packages` and `tasks_finalize` each require a `tasks/WP*.md` glob entry blocking, with the `requirement_mapping_failures` non-expressible check documented inline on `tasks_packages` | Reverting FR-007 removes these three `required_by_step` keys entirely, failing every "step present with N specs" assertion |
| AS6 (US1, software-dev/implement, FR-008) | `tests/dossier/test_manifest.py` | `test_software_dev_manifest_implement_has_no_filesystem_requirement` | `required_by_step["implement"]` is `[]` — `analysis-report.md` absent | Reverting FR-008 restores the `analysis-report.md` blocking entry, tripping the "empty list" assertion |
| AS7 (US1, cross-check, SC-001) | `tests/dossier/test_manifest.py` or a new `tests/dossier/test_manifest_guard_parity.py` | `test_all_required_by_step_keys_match_guard_or_carry_comment` | Every `required_by_step` key across `research`/`documentation`/`software-dev` either has a corresponding `runtime_bridge_cores.py` guard branch or an inline YAML comment (checked by loading the raw YAML and asserting on comment presence via `ruamel.yaml`'s round-trip `CommentedMap`) | Any un-reconciled or un-annotated divergence reintroduced by a future edit fails this parity check — this is FR-012's "cross-check" bar, not merely per-step checks |
| AS1–AS4 (US2, `plan` manifest, FR-010) | `tests/dossier/test_manifest.py` | `test_plan_manifest_loads_and_matches_state_machine` | `ManifestRegistry.load_manifest("plan")` returns non-`None`; `mission_type == "plan"`, `manifest_version == "1"`; `get_step_ids()` returns exactly `["goals","research","structure","draft","review","done"]` (order-sensitive, matching `plan/mission.yaml`'s `states` list verified above); `goals`/`research`/`draft` require `goals.md`/`research.md`/`plan.md` respectively, blocking; `structure`/`review`/`done` have no filesystem requirement | Reverting FR-010 (deleting the file) makes `load_manifest("plan")` return `None`, failing the first assertion outright |
| AS5 (US2, upstream issue, FR-011/SC-005) | N/A (tracker verification, not a pytest test) | Manual/CI-external: `gh issue view <new-issue-number>` confirms the issue exists, is distinct from #3388, and its URL is recorded in `tracer-design-decisions.md` and the PR body | The issue naming the `_check_cli_guards` hardcoded-`mission_family` + `plan`'s accidental `review`-step collision | N/A — this is a tracker-state assertion, verified once at mission close, not re-run in CI |
| FR-014 (override-mirror deprecation header) | `tests/dossier/test_manifest.py` (or `tests/doctrine/`, confirmed at `/spec-kitty.tasks`) | `test_override_mirror_files_carry_deprecation_header` | For each of `.kittify/overrides/missions/{research,documentation,software-dev}/expected-artifacts.yaml`, a file-read/grep assertion confirms the header comment names the specific inert mechanism (`_expected_artifacts_path()` has no override tier for this asset type) — not a generic "deprecated" string | Reverting FR-014 (or a future edit that strips/genericizes the header) removes the specific-mechanism wording, failing the assertion instead of only failing manual review — this is also the regression guard for PLAN-GOV-001/Decision 4: it fails if a future "drift hygiene" refresh overwrites the header back to content-parity wording |
| AS1–AS2 (US3, schema hardening, FR-009/SC-003) | `tests/dossier/test_manifest.py` | `test_expected_artifact_spec_rejects_extra_keyword` / `test_expected_artifact_manifest_rejects_extra_keyword` | Both raise `pydantic.ValidationError` on an extra kwarg (`blockign=True` / `required_alwyas=[]`) | Reverting FR-009 (dropping `extra="forbid"`) restores default `extra="ignore"`, so construction silently succeeds and the `pytest.raises(ValidationError)` context manager fails to catch anything |
| AS3 (US3, no false positive, SC-003) | `tests/dossier/test_manifest.py` | `test_all_shipped_manifests_load_after_hardening` | All four shipped `expected-artifacts.yaml` files load successfully via `ManifestRegistry.load_manifest()` post-hardening | If FR-001–FR-008/FR-010's content edits introduced any stray key not in the schema, this fails — the test is the concrete proof the hardening introduces no false positive against real shipped content |
| AS4 (US3, `load_manifest()` loud failure, FR-016) | `tests/dossier/test_manifest.py` (+ a new typo'd YAML fixture) | `test_load_manifest_raises_on_malformed_yaml` | Loading a deliberately typo'd (`required_alwyas:`) real fixture through `ManifestRegistry.load_manifest()` raises `pydantic.ValidationError`, not `None` | Reverting FR-016 restores the bare `except Exception: return None`, so the raise never reaches the caller and the `pytest.raises` block fails to catch anything (the call returns `None` instead) |
| AS5 (US3, propagation through indexer callers, FR-016/AS5) | New test(s) alongside existing coverage for `cli/commands/reconcile.py` and `dossier/rebaseline.py` (exact file confirmed at `/spec-kitty.tasks`) | `test_reconcile_reports_error_on_malformed_manifest`, `test_rebaseline_skips_one_mission_on_malformed_manifest` | `reconcile.py`'s flow returns `ReconciliationResult(status=ERROR, error=...)`; `rebaseline.py`'s sweep returns a per-mission `RebaselineOutcome(error="reindex_failed: ...")` and continues past it (not an aborted sweep) | Reverting FR-016 means `load_manifest()` never raises, so neither call site's `except Exception` branch is exercised and both structured-error assertions fail |
| AS6 (US3, `resolve_manifest_version()` fallback, FR-016/AS6) | `tests/dossier/test_manifest.py` or `tests/sync/test_namespace.py` (exact file confirmed at `/spec-kitty.tasks` — a `tests/sync/` home is more locality-appropriate than `tests/dossier/`, since the function under test lives in `sync/namespace.py`) | `test_resolve_manifest_version_returns_one_on_malformed_manifest` | `resolve_manifest_version(mission_type)` called directly against the typo'd fixture still returns `"1"`, not raising | Reverting FR-016's `sync/namespace.py` addition leaves the raised `ValidationError` uncaught inside `resolve_manifest_version()`, so the direct call raises instead of returning `"1"`, failing the assertion |
| FR-013 (manifest_version-stability rationale comment, all four manifests) | `tests/dossier/test_manifest_guard_parity.py` | `test_manifest_version_rationale_comment_present` | For each of the four `packs/built-in/missions/{research,documentation,software-dev,plan}/expected-artifacts.yaml` files, loading the raw YAML via `ruamel.yaml`'s round-trip `CommentedMap` and inspecting `.ca.items` finds a comment attached at/near the `manifest_version: "1"` key whose text contains a recognizable Decision-2 rationale marker (e.g. references `manifest_version` being a sync-namespace identity key rather than a content-freshness counter) — a content check on the comment itself, not merely on the version value | Reverting FR-013 (dropping the inline comment from one or more files while leaving `manifest_version: "1"` unchanged) leaves SC-006's value-only check passing but makes this test's comment-content assertion find no matching comment at that key, failing outright |
| SC-006 (manifest_version stability) | `tests/dossier/test_manifest.py` | `test_manifest_version_unchanged_on_all_four_files` (or a shell-level `grep` assertion folded into an existing test) | `grep manifest_version packs/built-in/missions/*/expected-artifacts.yaml` shows `"1"` for all four files | A future edit that bumps any manifest's version trips this — the concrete regression guard for Decision 2/C-002 |
| FR-015 audit (non-regression) | `tests/doctrine/missions/test_repository.py`, `tests/runtime/test_bridge_cores.py`, `tests/integration/test_research_runtime_walk.py`, `tests/integration/test_documentation_runtime_walk.py`, `tests/charter/test_resolved_mission_type_context.py` | (existing tests, audited — corrected only if found to assert on pre-reconciliation content) | Each file's pre-existing assertions still pass against the reconciled manifest content; `test_resolved_mission_type_context.py`'s three `bundle.expected_artifacts` assertions for `software-dev` specifically confirmed | If any of these pinned old content, it fails against the reconciled manifest and must be corrected as part of the same WP that reconciles that content (not silently left red) |

**Addendum (tasks-phase adversarial review fix, round 1 — recorded here in round 2, TASKS-FRESH1-003):**
the AS3 (US3, no false positive, SC-003) row above still names a single test,
`test_all_shipped_manifests_load_after_hardening`, as covering "all four shipped
`expected-artifacts.yaml` files." During the tasks phase's own adversarial-review fix pass, that
test (in WP01) was narrowed to assert on only three of the four manifests (`research`,
`documentation`, `software-dev`); the fourth (`plan`) is independently covered by WP03's own
`test_plan_manifest_loads_and_matches_state_machine` (already listed above in the "AS1–AS4 (US2,
`plan` manifest, FR-010)" row, whose first assertion — `load_manifest("plan")` returns non-`None` —
is exactly the "loads successfully post-hardening" check for that fourth manifest). The AS3/SC-003
bar ("no false positive on any of the four shipped manifests") is therefore still met **in
aggregate**, just split across two tests in two different WPs rather than proven by one single
test as this table's AS3 row literally describes. This is a documentation-only correction — plan.md
is not itself re-gated by this mission's own review process — recorded here per the charter's
documentation-accuracy doctrine rather than left silently stale now that the disagreement is known.

**Addendum (tasks-phase adversarial review fix, round 4 — recorded here in round 5,
TASKS-FRESH4-001):** the AS1–AS4 (US2, `plan` manifest, FR-010) row above bundles all four
acceptance scenarios under `test_plan_manifest_loads_and_matches_state_machine` as if that one test
covered all four — but the "Asserts" column's actual list (load-success, `mission_type`,
`manifest_version`, `get_step_ids()` ordering, per-step required-artifact specs) never touched AS4's
header-comment-content requirement (spec.md's Acceptance Scenario 4: the header must state,
precisely, the hardcoded-`mission_family="software-dev"` + `review`-step lexical-collision mechanism
from Decision 1, not a vaguer "no guard exists yet" statement). AS4 was covered only by a one-time
manual reviewer read (WP03's own Risks/Reviewer Guidance sections), unlike this same table's FR-014
row, which carries a dedicated content-substring regression test
(`test_override_mirror_files_carry_deprecation_header`) for the structurally parallel case. WP03's
T015 now adds a second, dedicated test in the same `TestPlanManifest` class,
`test_plan_manifest_header_names_guard_gap_mechanism`, mirroring that FR-014 pattern: it reads the
raw text of `packs/built-in/missions/plan/expected-artifacts.yaml` and asserts the header comment
contains the specific-mechanism markers from Decision 1 (`mission_family="software-dev"`,
`_check_cli_guards`, the named `review`-step collision) and does **not** contain the rejected vaguer
framing. AS4 is therefore now covered by its own explicit assertion — structurally mirroring the
FR-014 row's treatment — rather than bundled prose alongside AS1-AS3's structural checks. This is a
documentation-only correction to this table's row description, matching round 1's own precedent
above (TASKS-FRESH1-003); the row's "Test" cell (`test_plan_manifest_loads_and_matches_state_machine`)
is unchanged because that test still covers AS1-AS3 exactly as described — AS4's coverage now lives
in the sibling test named in this addendum, not by renaming or expanding the original row's test.

## Enforced Gate Set For This Mission

Chosen from the full gate catalog in `docs/development/how-to/review-gates.md` and
`.github/workflows/ci-quality.yml`, based on this mission's actual changed-file set (verified
against the CI workflow's own `paths-filter` groups, not assumed):

**Applies (verified via path-filter match against this mission's file list above):**

- `make lint` / the CI `lint` job — always-on, all enforced sub-steps apply: commitlint,
  markdown-style lint (this mission's tracer/spec/plan `.md` files), Contextive glossary
  freshness (`src/specify_cli/**` changes trigger it — verified no-op per "What is generated"
  above, but the check itself still runs), generated-doctrine-schema freshness (verified no-op,
  same reason, check still runs and passes trivially), TID251 banned-API gate, Typer 0.26 JSON
  error surface, Bandit, pip-audit, `patch()` target validation — ruff/mypy run as **advisory**
  reports in this job (not release-blocking in CI today) but this mission holds itself to the
  charter's stricter local bar: zero new ruff/mypy issues on every changed file (NFR-002), checked
  locally before each WP's commit.
- `fast-tests-doctrine` / `integration-tests-doctrine` — `tests/doctrine/**` and `src/doctrine/**`
  are in this mission's validation surface and this mission's `manifest_version`/schema content
  is doctrine-adjacent; the `doctrine` path-filter group matches `tests/doctrine/missions/test_repository.py`.
- `fast-tests-core-misc` / `integration-tests-core-misc` (misc shard) — `tests/dossier/**` is
  explicitly listed in the `core_misc` path-filter group (verified at
  `.github/workflows/ci-quality.yml:376`); `src/specify_cli/dossier/**` is in the **separate**
  `agent_surface` composite group (`.github/workflows/ci-quality.yml:495`), not `core_misc`. Both
  independently gate `fast-tests-core-misc`/`integration-tests-core-misc`, whose own `if:` ORs
  across `core_misc`, `agent_surface`, and 9 other groups (`.github/workflows/ci-quality.yml:1704`),
  so the "applies" conclusion is unaffected — but the two paths trip two distinct named groups, not
  one. The `misc` shard's path list (line ~2063) explicitly includes `tests/dossier`.
- `fast-tests-corpus` — `packs/**` is routed exclusively to the `corpus` filter group (verified:
  `packs/**` appears only under `corpus`, not under `missions`/`doctrine`/`core_misc`); this
  mission's three edited + one new `expected-artifacts.yaml` file under `packs/built-in/missions/`
  triggers it.
- `fast-tests-sync` / `integration-tests-sync` / `integration-tests-sync-real-port` —
  `src/specify_cli/sync/**` (this mission's `namespace.py` change) is in the `sync` filter group.
  The real-port/daemon variant is included because the filter group is undifferentiated by file
  within `sync/**` — it will run even though this mission's change is far from the daemon/port
  surfaces; accepted as the cost of a narrow, correctly-scoped path filter rather than a special
  case.
- `fast-tests-charter` / `integration-tests-charter` — `tests/charter/test_resolved_mission_type_context.py`
  is in the `charter` filter group's `tests/charter/**` glob.
- `fast-tests-next` / `integration-tests-next` / `mission-loader-coverage` — `tests/runtime/**`
  (FR-015's `test_bridge_cores.py` audit target) is in the `next` filter group's
  `tests/runtime/**` glob; `mission-loader-coverage` gates on the `next` OR `core_misc` group
  being true, both of which this mission trips.
- `mission-loader-coverage` (≥90%, see above) — applies via the `next`/`core_misc` trigger; this
  mission does not touch `src/specify_cli/mission_loader/` directly, so no new coverage burden is
  introduced, but the gate still runs and must stay green.
- `arch-adversarial` — always-on pole per its own job description; applies regardless of path.
- `unit-contract-residual` — always-on, path-independent CI residual selection; applies.
- `regression tests (blocking)` — always-on, path-independent (`-m regression`); applies.
- `commitlint`, `markdown lint`, `architecture/docs consistency` (no-op — no `docs/**/*.md`
  changed), `template/compat regression` (no-op — no `src/specify_cli/template|compat|migration/**`
  changed) — both consistency checks are **path-gated to zero relevant changes** and will report
  "skipping" rather than running substantive assertions; listed here for completeness of "what was
  considered", not because they do meaningful work on this diff.
- `Contextive glossary` — runs (per `src/specify_cli/**` trigger) but is a **pass-through**: no
  glossary term is added/changed by this mission (verified: zero `manifest`/`expected-artifact`
  references in `scripts/generate_contextive_glossaries.py`).
- `generated doctrine schema freshness` — runs but is a **pass-through** for the same reason
  (verified: zero references in `scripts/generate_schemas.py`).
- `TID251 banned-API lint gate` — applies to every Python file changed; no banned import is
  introduced by this mission (no new `click`, no banned pattern).
- `Typer 0.26 JSON error surface` — applies repo-wide; this mission adds no new CLI command or
  error surface, so it is a pass-through.
- `patch() target validation` — applies to any new/changed `mock.patch()` call in new tests; the
  new regression tests in this mission's file list do not mock `dossier.manifest` internals with
  string-target patches where a direct import is available, per this gate's own intent — verified
  at test-authoring time, not assumed clean in advance.
- `Bandit`, `pip-audit`, `uv.lock` freshness — always-on; this mission adds no new dependency, so
  `uv.lock` is untouched and these gates are pass-throughs.
- `clean-install-verification` — always-on (`needs: [build-wheel]`, no path filter visible on the
  job itself); applies. No shared-package-boundary change (no new dependency, no
  `spec-kitty-events`/`spec-kitty-tracker` touch), so expected to pass unchanged.

**Explicitly NOT included, with reason for each:**

- `fast-tests-missions` / the `missions` path-filter group — **does not trigger.** `missions`'s
  glob list (`src/specify_cli/mission.py`, `mission_metadata.py`, `src/specify_cli/missions/**`,
  `src/doctrine/missions/**`, `tests/fixtures/missions/**`, `tests/missions/**`,
  `tests/specify_cli/missions/**`) does **not** include `packs/built-in/missions/**` — verified by
  direct read of the filter block. This mission's manifest edits are pack *data*, routed instead
  to `corpus` (already included above). Reason for exclusion: the CI path-filter itself does not
  select this job for this file set; including it would be simulating a trigger this mission does
  not actually have.
- `e2e-cross-cutting`, `integration-tests-agent`, `fast-tests-agent`, `fast-tests-lanes`,
  `fast-tests-dashboard`, `fast-tests-upgrade`, `fast-tests-cli`, `fast-tests-merge`,
  `fast-tests-status`, `fast-tests-review`, `fast-tests-release`, `fast-tests-post-merge`,
  `fast-tests-docs`, and their integration counterparts — **do not trigger.** None of this
  mission's changed files fall under `src/specify_cli/{agent_utils,lanes,dashboard,upgrade,cli,
  merge,status,review,release,post_merge}/**`, `tests/{agent,lanes,dashboard,upgrade,cli,merge,
  status,review,release,post_merge,docs}/**`, or `docs/**`. Reason: no path-filter match.
- `stress-tests-serial`, `timing-nfr-serial`, `slow-tests`, `restart-daemon-nfr-timing`,
  `quarantine-visibility` — these gate marked-`@pytest.mark.stress`/`timing`/`slow` tests or
  daemon-lifecycle behavior; this mission adds no such marker to any new test (all new tests are
  plain unit-level manifest/schema assertions) and touches no daemon code. Reason: no marker
  overlap, no path overlap.
- `deferral-consistency-check` — gates `deferred_to_consolidation` invariants; this mission
  introduces no such marker. Reason: no relevant content.
- `kernel-tests` (kernel coverage ≥90%) — **does not run on this mission's PR.** The job's `if:`
  gate (`.github/workflows/ci-quality.yml:1077-1082`, two lines below its `needs: [changes]` line)
  is `always() && (needs.changes.outputs.kernel == 'true' || github.event_name == 'push')`. This
  mission touches zero `src/kernel/**`/`tests/kernel/**` files and is a `pull_request` event, so
  neither disjunct is satisfied — the job does not execute for this PR at all (not "runs and passes
  trivially"). The coverage-floor conclusion still holds, but because the job doesn't run, not
  because it runs and passes.
- `SonarCloud Quality Gate` — **does not run on this mission's PR.** The `sonarcloud` job's `if:`
  (`.github/workflows/ci-quality.yml:3625`) is
  `always() && (github.event_name == 'schedule' || github.event_name == 'workflow_dispatch')` — a
  `pull_request` event never satisfies it, and the job's own header comment
  (`.github/workflows/ci-quality.yml:3562-3566`) confirms this is deliberate ("PRs skip Sonar
  entirely to keep review latency low"). SonarCloud evaluates `main` on the next scheduled/manual
  run, post-merge, not this PR directly. Kept as good practice, not gate compliance: new code (the
  `except` branches in `manifest.py`/`namespace.py`, the new tests) should still carry
  Sonar-acceptable coverage per the charter's Sonar Expectations — the test strategy above is
  deliberately narrow-and-direct (one test per new branch) — but this does not satisfy a gate that
  runs on this PR.
- `mutation-testing` — **permanently disabled, does not apply.** The job has `if: false`
  (`.github/workflows/ci-quality.yml:3557`) and its sole step is `run: echo "Mutation testing is
  disabled."` — it never executes, for any diff, on any event. No test-strategy justification is
  needed for it.
- `diff-coverage` (both critical-path and full-diff variants) — genuinely always-on per the
  workflow (unlike `mutation-testing`, above) and will execute against whatever diff-coverage this
  mission's tests provide, which the Test Strategy table above is designed to satisfy. Listed here
  rather than in "Applies" only because it has no path gate to reason about separately — it is not
  excluded, it simply isn't gated on this mission's specific file set the way the path-filtered
  jobs above are.
- `consumer-compatibility` (SaaS consumer compatibility) — **has a path gate; this mission does not
  trip it.** The job (`.github/workflows/ci-quality.yml:4216-4220`) runs only when
  `if: always() && needs.changes.outputs.release == 'true' && needs.build-wheel.result ==
  'success'` — gated on the `release` path-filter group (`src/specify_cli/release/**`,
  `pyproject.toml`, `uv.lock`, `CHANGELOG.md`, etc.) plus a successful `build-wheel`. This mission
  touches none of the `release` group's paths, so the job does not run on this PR — the plan's
  conclusion (effectively excluded) is correct, but "no path gate" was wrong; it has one and this
  mission simply doesn't trip it.
- **`markdown lint`** on `kitty-specs/**/*.md` is explicitly folded into the always-on `lint` job
  above, not listed as a separate exclusion — this mission's own `plan.md`/tracer files ARE the
  markdown being linted.

## PR Shape

**One PR per mission**, confirmed by `tracer-approach.md`'s already-recorded decision ("Default:
one PR per mission" — this plan does not re-litigate it, only confirms it holds for the phasing
below). The mission's `accept` → `merge` machinery assumes one mission, one branch, one PR;
splitting would fragment a single, already-narrow "content + schema only" change across multiple
review cycles for no isolation benefit — every FR here is small, and several (FR-013's
`manifest_version` comments) are line-items *inside* the same files FR-001–FR-010 already touch.
The two follow-up issues (FR-011's plan-guard-gap; the out-of-scope `artifact_key` unification
candidate) are filed as **tracker issues, not separate PRs**, since neither is implemented here.

## Implementation Concern Map

*Concerns below map to work packages at `/spec-kitty.tasks`; sequencing notes are recommendations,
not commitments — the tasks phase makes the final WP slicing decision.*

**Test file ownership (`tests/dossier/test_manifest.py`) — PLAN-ARCH-001/PLAN-FRESH-001 fix.**
IC-01, IC-02, IC-03, and IC-04 each carry their own red-first regression test(s), landing before
that IC's own implementation commit (C-011) — the earlier draft deferred all of IC-01/02/03's tests
into a single IC-05 that depended on IC-01/IC-02/IC-03, which either violated C-011 (if IC-01-03
truly carried no test of their own) or left an unaddressed collision risk (if they did, silently).
A later fresh-eyes sweep (PLAN-FRESH-001) found that same restructuring had missed IC-04 — it is
now included here, closing the same gap for the one IC the first fix round left out. The Test
Strategy table above already fully specifies every assertion these tests need, so there is no
technical reason to defer any of them — only the FR-015 audit and the cross-cutting AS7/SC-006
checks (moved to IC-05 below) genuinely need IC-01-03's content to be final. To avoid merge
collisions among WPs that may share `test_manifest.py`, each IC owns a distinct, named test
section:

| IC | Test section/class in `test_manifest.py` |
|---|---|
| IC-01 | `TestSchemaHardeningAndLoudFailure` |
| IC-02 | `TestManifestReconciliation` |
| IC-03 | `TestPlanManifest` |
| IC-04 | `TestOverrideMirrorDeprecation` (if housed in `test_manifest.py`; the Test Strategy table's FR-014 row leaves the exact home file — `test_manifest.py` or `tests/doctrine/` — to be confirmed at `/spec-kitty.tasks`) |

IC-04's test is a section none of the other ICs write to regardless of which home file
`/spec-kitty.tasks` picks, so it introduces no new collision risk either way.

IC-05's cross-cutting checks (AS7, SC-006) land in a **separate new file**,
`tests/dossier/test_manifest_guard_parity.py`, specifically so IC-05 never needs to touch the
other three ICs' sections. `/spec-kitty.tasks` should carry these section names into each WP's
prompt so parallel WPs do not need to coordinate live.

### IC-01 — Schema hardening + loud-failure propagation (FR-009, FR-016)

- **Purpose**: Make a typo'd manifest key fail loudly at every real layer — direct construction
  (FR-009) and the one production loading path plus its one unprotected caller (FR-016).
- **Relevant requirements**: FR-009, FR-016, FR-012 (this WP's own red-first tests below are the
  literal FR-009/FR-016 test items FR-012 enumerates — schema-rejection tests, `load_manifest()`'s
  loud-failure test, the `reconcile.py`/`rebaseline.py` propagation tests (AS5), and
  `resolve_manifest_version()`'s fallback test (AS6) — so this IC owns that slice of FR-012's
  redistributed test-remediation content, per PLAN-FRESH-002)
- **Affected surfaces**: `src/specify_cli/dossier/manifest.py` (both `model_config` additions +
  `load_manifest()`'s exception handling), `src/specify_cli/sync/namespace.py` (one narrow
  `except pydantic.ValidationError` in `resolve_manifest_version()`); `tests/dossier/test_manifest.py`
  — this WP's own red-first tests, in the `TestSchemaHardeningAndLoudFailure` section (see "Test
  file ownership" above): `test_expected_artifact_spec_rejects_extra_keyword`,
  `test_expected_artifact_manifest_rejects_extra_keyword`,
  `test_all_shipped_manifests_load_after_hardening`, `test_load_manifest_raises_on_malformed_yaml`
  (+ its new typo'd YAML fixture), `test_resolve_manifest_version_returns_one_on_malformed_manifest`
  — all committed **before** this WP's own implementation commit, per C-011; targeted test
  additions alongside `cli/commands/reconcile.py`'s and `dossier/rebaseline.py`'s existing coverage
  for `test_reconcile_reports_error_on_malformed_manifest` /
  `test_rebaseline_skips_one_mission_on_malformed_manifest` (exact file TBD at `/spec-kitty.tasks`).
- **Sequencing/depends-on**: none — self-contained; recommended to land **first** so IC-02/IC-03's
  content edits are validated against the hardened schema from the moment they're authored, not
  retrofitted against it later.
- **Risks**: None identified — pure exception-handling narrowing plus a `ConfigDict` addition,
  both additive/output-preserving for every currently-passing input (SC-003's "no false positive"
  bar is the concrete check).

### IC-02 — Reconcile research/documentation/software-dev manifests (FR-001-FR-008, FR-013)

- **Purpose**: Correct the 8 named divergences between shipped manifest content and
  `runtime_bridge_cores.py`'s guard reality; record the `manifest_version`-stability rationale
  inline in each edited file (FR-013/Decision 2) — the comment's actual presence across all four
  manifest files (this WP's three plus IC-03's new one) is checked by the FR-013 row in the Test
  Strategy Per Acceptance Criterion table (`test_manifest_version_rationale_comment_present`,
  landed by IC-05 once all four files carry their final content).
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008,
  FR-013, FR-012 (this WP's own red-first tests below are the literal FR-001-FR-005/FR-008
  divergence-fix tests plus the stale plan-step test correction FR-012 itself enumerates, so this
  IC owns that slice of FR-012's redistributed test-remediation content, per PLAN-FRESH-002)
- **Affected surfaces**: `packs/built-in/missions/research/expected-artifacts.yaml`,
  `packs/built-in/missions/documentation/expected-artifacts.yaml`,
  `packs/built-in/missions/software-dev/expected-artifacts.yaml`; `tests/dossier/test_manifest.py`
  — this WP's own red-first tests, in the `TestManifestReconciliation` section (see "Test file
  ownership" above): `test_research_manifest_gathering_requires_source_register`,
  `test_documentation_manifest_audit_design_reconciled`,
  `test_documentation_manifest_validate_publish_reconciled`,
  `test_software_dev_manifest_plan_step_has_plan_only` (which **replaces**, in this same WP,
  FR-012's stale `test_software_dev_manifest_plan_step_has_plan_and_tasks` — the correction is tied
  directly to this WP's own FR-006 edit, so it belongs here rather than in a later cross-cutting
  concern), `test_software_dev_manifest_tasks_outline_packages_finalize`,
  `test_software_dev_manifest_implement_has_no_filesystem_requirement` — all committed **before**
  this WP's own implementation commit, per C-011.
- **Sequencing/depends-on**: IC-01 (schema hardened first, so any accidental new-key typo
  introduced while editing is caught immediately rather than silently ignored)
- **Risks**: FR-008's `implement`-step removal reads, at first glance, like "the guard is wrong,
  not the manifest" — the approach explicitly rejects that reading (`tracer-approach.md`); a
  reviewer unfamiliar with that rationale may flag it as a regression. Mitigated by the inline
  YAML comment already planned and this plan's own restatement.

### IC-03 — Author `plan` manifest + file the follow-up guard-gap issue (FR-010, FR-011, FR-013)

- **Purpose**: Ship the fourth built-in mission type's manifest, honestly scoped to `plan`'s own
  state machine (Decision 1); file the independent upstream defect the investigation surfaced.
  This new file must also carry the `manifest_version`-stability rationale as an inline YAML
  comment (FR-013/Decision 2), matching IC-02's treatment of the other three manifests — this is
  the fourth of the "four manifest files" FR-013 names, and this WP is the only one that touches
  this file.
- **Relevant requirements**: FR-010, FR-011, FR-012 (this WP's own red-first test below is the
  literal FR-010 `plan`-manifest test FR-012 itself enumerates, so this IC owns that slice of
  FR-012's redistributed test-remediation content, per PLAN-FRESH-002), FR-013 (record the
  `manifest_version`-stability rationale inline in this new file — see Purpose above)
- **Affected surfaces**: `packs/built-in/missions/plan/expected-artifacts.yaml` (new file — carries
  both the AS4 header-style comment on Decision 1's guard gap and, separately, the FR-013 rationale
  comment on Decision 2's `manifest_version` stability; these are two distinct required comments
  about two distinct decisions, not one comment serving both); a new GitHub issue (tracker-side,
  not a repo file); `tests/dossier/test_manifest.py` — this WP's own red-first test, in the
  `TestPlanManifest` section (see "Test file ownership" above):
  `test_plan_manifest_loads_and_matches_state_machine`, committed **before** this WP's own
  implementation commit, per C-011. (The FR-013 rationale comment's actual presence, across this
  file and IC-02's three, is verified separately by IC-05's cross-cutting
  `test_manifest_version_rationale_comment_present`, per the Test Strategy table's FR-013 row.)
- **Sequencing/depends-on**: IC-01 (same reasoning as IC-02 — validate against the hardened
  schema from authoring time)
- **Risks**: The header-comment requirement (AS4) is easy to under-specify without care — it must
  name the exact hardcoded-`mission_family` + `review`-step-collision mechanism, not a vaguer "no
  guard exists yet" — the reviewing squad should check this comment word-for-word against Decision
  1's text, not just confirm a comment is present. Separately, and easy to drop precisely because
  AS4's comment is the more visually prominent one: the FR-013 rationale comment on
  `manifest_version` is a second, distinct comment this same file must carry (Decision 2, not
  Decision 1) — the reviewing squad should confirm both are present rather than treating one as
  satisfying the other.

### IC-04 — Deprecate the dead `.kittify/overrides/` manifest mirrors (FR-014)

- **Purpose**: Stop a future maintainer from investing in content that can never be read, per
  Decision 4's DIRECTIVE_044-driven resolution (mark-deprecated, don't refresh, don't delete).
- **Relevant requirements**: FR-014
- **Affected surfaces**: `tests/dossier/test_manifest.py` (or `tests/doctrine/`, exact file
  confirmed at `/spec-kitty.tasks` — see the Test Strategy table's FR-014 row) — this WP's own
  red-first test, in the `TestOverrideMirrorDeprecation` section (see "Test file ownership" above):
  `test_override_mirror_files_carry_deprecation_header`, committed **before** this WP's own
  header-comment-edit implementation commit, per C-011; `.kittify/overrides/missions/research/expected-artifacts.yaml`,
  `.kittify/overrides/missions/documentation/expected-artifacts.yaml`,
  `.kittify/overrides/missions/software-dev/expected-artifacts.yaml` (header comment only in each
  — content otherwise untouched, explicitly NOT refreshed to parity per Decision 4)
- **Sequencing/depends-on**: none — fully independent of IC-01-IC-03 (these three files are never
  read by any production code path, confirmed above). **Addendum (tasks-phase adversarial review
  fix, round 1 — recorded here in round 2, TASKS-FRESH1-004):** the tasks phase's own round-1 fix
  added a formal `WP04: dependencies: [WP01]` edge in `wps.yaml`/`lanes.json` for this IC's WP —
  not for a content dependency (there still is none; these files are never read by production
  code), but purely for scheduling/chokepoint safety, since this WP's own out-of-map edit to the
  shared `tests/dossier/test_manifest.py` file (owned by IC-01's WP) needs to land after IC-01's
  WP has landed. That structural edge supersedes this plan-time "fully independent" recommendation
  for scheduling purposes, per this document's own disclaimer elsewhere that these sequencing
  notes are recommendations, not commitments, and the tasks phase makes the final WP slicing
  decision.
- **Risks**: Low. The only failure mode is writing a comment vague enough that a future maintainer
  still believes the override might take effect — the comment must name the specific mechanism
  (`_expected_artifacts_path()` has no override tier for this asset type) and point at the
  follow-up-candidate issue, not just say "deprecated."

### IC-05 — Post-reconciliation audit and cross-cutting parity check (FR-015, plus AS7/SC-006/FR-013)

- **Purpose**: Audit the five files FR-015 names for any pre-reconciliation content dependency;
  run the cross-cutting checks that can only be evaluated once all four manifests carry their
  final content — AS7's guard-vs-comment parity check across `research`/`documentation`/
  `software-dev` (IC-02's output), SC-006's `manifest_version` stability check across all four
  files (IC-02's three edits + IC-03's new file), and FR-013's rationale-comment presence check
  across those same four files (the comment IC-02 and IC-03 each committed to adding, verified
  here rather than only asserted in prose). Per PLAN-ARCH-001's fix, FR-012's stale-test
  correction and the per-FR regression tests have moved into IC-01/IC-02/IC-03's own "Affected
  surfaces" above — each lands as that WP's own red-first test before that WP's own implementation
  commit; IC-05 no longer carries any of that per-FR test-authoring, only the genuinely
  cross-cutting checks that need the reconciled content to exist first.
- **Relevant requirements**: FR-015 (plus the AS7/SC-006/FR-013 Test Strategy rows, which are
  cross-cutting and not tied to a single FR — FR-013 in particular needs both IC-02's three edits
  and IC-03's new file to exist before it can be checked across all four)
- **Affected surfaces**: `tests/doctrine/missions/test_repository.py`,
  `tests/runtime/test_bridge_cores.py`, `tests/integration/test_research_runtime_walk.py`,
  `tests/integration/test_documentation_runtime_walk.py`,
  `tests/charter/test_resolved_mission_type_context.py` (audit — corrected only if a pinned
  assertion is actually found); a new `tests/dossier/test_manifest_guard_parity.py` housing
  `test_all_required_by_step_keys_match_guard_or_carry_comment` (AS7),
  `test_manifest_version_unchanged_on_all_four_files` (SC-006), and
  `test_manifest_version_rationale_comment_present` (FR-013 — reads each of the four
  `expected-artifacts.yaml` files via `ruamel.yaml`'s round-trip `CommentedMap` and asserts a
  recognizable rationale marker is attached to/near `manifest_version: "1"`, not merely that the
  value equals `"1"`) — a **separate file** from `tests/dossier/test_manifest.py`, specifically so
  IC-05 never touches IC-01/IC-02/IC-03's own test sections in that file (see "Test file
  ownership" note above).
- **Sequencing/depends-on**: IC-01, IC-02, IC-03 — genuinely required: AS7, SC-006, and FR-013 all
  read across all four manifests' final content, and the FR-015 audit checks assertions against
  the *reconciled* content those three ICs produce. This remains a real content dependency, not a
  C-011 exception: IC-05's own red-first tests (in `test_manifest_guard_parity.py`) still land
  before IC-05's own audit/correction commit, the same as every other IC.
- **Risks**: The FR-015 audit could find more than the one confirmed pinned test
  (`test_resolved_mission_type_context.py`) — budget review time for that possibility rather than
  assuming the audit is a formality.

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified*

No violations. This section is intentionally empty — the Charter Check above passed on every
axis without an exception being taken.

## Campsite-Clean Scope

Per the charter's Standing Order #2, the opening commit is a **distinct, behavior-preserving**
campsite-clean folding only *domain-matched* debt on the surfaces this mission is about to touch
— not a grab-bag.

**Domain-matched debt actually found and folded in**: none beyond what the mission's own FRs
already prescribe. The three files this mission edits for content
(`packs/built-in/missions/{research,documentation,software-dev}/expected-artifacts.yaml`) carry
no unrelated lint/type/test debt of their own — they are YAML data files with no Sonar
complexity/coverage surface. `src/specify_cli/dossier/manifest.py` and
`src/specify_cli/sync/namespace.py` were read in full while writing this plan; neither carries an
open TODO, a Sonar-flagged complexity violation, or a failing test in the scope this mission
touches that isn't already one of the FRs above.

**Note on `SPEC-KITTY-LEDGER.md`: it is not part of this repository.** `git log --all --
SPEC-KITTY-LEDGER.md` returns nothing and `git show main:SPEC-KITTY-LEDGER.md` fails with "path
does not exist" — this file has never existed anywhere in this checkout's git history, on any
branch. Nothing in this repository's own `CLAUDE.md` or `AGENTS.md` instructs any agent to read it
(`grep -n 'SPEC-KITTY-LEDGER' CLAUDE.md AGENTS.md` returns no matches, confirmed at time of
writing). `SPEC-KITTY-LEDGER.md` is an artifact of the *operator's own local workspace*, one
directory above this git checkout and outside spec-kitty entirely — a separate, parent-level
`CLAUDE.md` in that workspace (also outside this repo) is what instructs agents operating there to
read it. A prior remediation pass of this note mistakenly attributed that instruction to this
repo's own `CLAUDE.md`; that attribution was incorrect and is corrected here. Below, the substance
that matters (the SK-11 defect) is restated directly from first-hand, in-repo evidence rather than
cited from that external file, and the broader SK-01–SK-15 enumeration is named only as an
external, operator-side pointer — not as something this repository asserts or a public reader can
verify.

**What *is* independently verifiable and stands on its own evidence, with no dependency on any
external file**: while scaffolding this mission's own `plan.md` via `spec-kitty plan --json`, the
software-dev mission type's shipped plan template (`packs/built-in/missions/software-dev/templates/plan-template.md:4`)
was observed first-hand to read `**Input**: Feature specification from ...` — a live, reproducible
Terminology Canon violation ("Feature" where the canon requires "Mission"). That observed defect is
judged out of this mission's campsite-clean opening commit, for two independent reasons: (1) it is
a **different mission type's template** (`software-dev/templates/plan-template.md`) from this
mission's actual subject (`packs/built-in/missions/plan/expected-artifacts.yaml` for FR-010, and
the three *content* manifests for FR-001-FR-008) — "software-dev's plan template prose" and "the
`plan` mission type's manifest" share only the word "plan" and are otherwise unrelated files,
unrelated mission types, unrelated FRs; (2) a fix (rename one string, extend the terminology
guard's scan to `packs/built-in/**`) is itself a small but *distinct* behavior change to a doctrine
template that ships to every consumer repo — bundling it into a "content + schema only"
manifest-repair mission would blur exactly the kind of independently-reviewable, independently-timed
change this mission's own approach doc already insists on for its two *other* deferred follow-ups
(the plan-guard-gap issue, the `artifact_key` unification). **This plan's own `plan.md` does not
re-propagate the violation**: this document's own "Input" line above reads "Mission specification",
not "Feature specification" — a local, zero-risk correction inside this mission's own artifact, not
a fix to the shared template. This defect remains open and unresolved by this mission, and is not
silently worked around.

**Other claimed ledger entries ("SK-01 through SK-15")**: the operator's local
`SPEC-KITTY-LEDGER.md` — outside this repository, not something spec-kitty ships or a public
reader can open — is understood (from that external workspace) to catalog these as tooling/CLI
workflow defects (branch resolution, commit routing, retrospective FR-ID regex, dispatch routing)
not domain-matched to this mission's scope. That characterization is named here only as an
external, operator-side pointer, not a fact this repository asserts or can independently verify.
Nothing in this mission's own campsite-clean scope depends on it — the domain-matched-debt
conclusion above stands entirely on the first-hand, in-repo evidence in the preceding paragraph.

## Confirmed: Tracer Files Already Seeded

`tracer-tooling-friction.md`, `tracer-approach.md`, and `tracer-design-decisions.md` all exist in
this mission's directory (confirmed via direct `Read`, not assumed from a directory listing) and
carry substantive content from the spec-authoring phase (Decisions 1-5, the reconcile-to-guard
approach, the SK-09-matching commit-tooling friction transcript). **They are not recreated by this
plan.** Appending to them during implementation (per charter Standing Order #3) is each WP's own
responsibility going forward, not this plan's.
