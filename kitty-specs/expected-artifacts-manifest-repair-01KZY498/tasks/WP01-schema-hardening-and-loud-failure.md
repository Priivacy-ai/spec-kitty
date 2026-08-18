---
work_package_id: WP01
title: Schema hardening + loud-failure propagation
dependencies: []
requirement_refs:
- FR-009
- FR-012
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: pr/expected-artifacts-manifest-repair-01KZY498
base_commit: aad6041b1f3a19bf96a9f78f5bf886897cfe0748
created_at: '2026-08-14T03:14:03.065627+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Schema + loud failure (lands first)
assignee: ''
agent: claude
history:
- timestamp: '2026-08-14T00:00:00Z'
  agent: claude
  action: Prompt generated via manual /spec-kitty.tasks-outline + /spec-kitty.tasks-packages equivalent (tasks-authoring agent)
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/dossier/manifest.py
create_intent:
- tests/dossier/fixtures/expected_artifacts_typo.yaml
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/dossier/manifest.py
- src/specify_cli/sync/namespace.py
- tests/dossier/test_manifest.py
- tests/cli/commands/test_reconcile.py
- tests/dossier/test_rebaseline.py
- tests/sync/test_namespace.py
- tests/dossier/fixtures/expected_artifacts_typo.yaml
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – Schema hardening + loud-failure propagation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Make a typo'd `expected-artifacts.yaml` key fail loudly at every real layer: direct
Pydantic construction (`ExpectedArtifactSpec`/`ExpectedArtifactManifest`, FR-009) and
the one production loading path plus its one unprotected caller
(`ManifestRegistry.load_manifest()` and `sync.namespace.resolve_manifest_version()`,
FR-016). This is **Implementation Concern IC-01** from `plan.md` — it carries no
dependency on any other WP and is recommended to land **first**, so IC-02/IC-03's
content edits (WP02/WP03) are authored and validated against the hardened schema
from the moment they're written, not retrofitted against it later.

This WP also carries the mission's **Baseline Capture** step (see Subtask T001
below) — required by `plan.md`'s "Baseline Capture" section to run **before any
functional change lands**, and the recorded confirmation that this mission's
**Campsite-Clean Scope is empty** (see "Campsite-Clean Confirmation" below) — both
belong here because WP01 is the first WP scheduled to execute.

## Context

**Why this WP exists**: User Story 3 (spec.md) requires a typo'd manifest key to
raise immediately, not just at direct model construction but through the one real
production loading path every consumer uses. `ManifestRegistry.load_manifest()`
(`src/specify_cli/dossier/manifest.py:207-215`) currently wraps `model_validate` in
a bare `except Exception as e: logger.error(...); return None` — indistinguishable
from "manifest not found." See `tracer-design-decisions.md` Decision 3 for the full
rationale and the corrected, file-by-file blast radius (this is the canonical
account — do not re-derive it from scratch).

**What depends on this WP**: WP02 and WP03 both depend on WP01 landing first (same
reasoning: validate new/edited manifest content against the hardened schema as it's
authored). WP05 also depends on WP01 (transitively, via WP02/WP03).

**Key design decisions this WP must honor** (from `tracer-design-decisions.md`):
- **Decision 3**: the blast radius is `manifest.py` (the raise) **and**, narrowly,
  `sync/namespace.py` (one output-preserving defensive `except` clause). It is
  **not** `dossier/indexer.py` — every real caller of `Indexer.index_feature()`
  (`reconcile.py`, `rebaseline.py`, `sync/dossier_pipeline.py`'s
  `sync_feature_dossier()`) already fail-closes on any exception one layer up. Do
  **not** add redundant `except` blocks inside `indexer.py` itself — this would
  duplicate existing handling for no behavior change, the opposite of
  `change-apply-smallest-viable-diff`.
- **Decision 5**: the sync-pipeline path (`sync_feature_dossier()` →
  `trigger_feature_dossier_sync_if_enabled`) does **not** gain operator-visible
  failure from this WP — every real caller of the wrapping function discards its
  return value. This is a **known, named residual gap**, not something this WP
  should try to close. Do not add logging/visibility there; it is out of scope
  (see Decision 5's rejected alternative for why).
- **C-001**: no changes to `src/runtime/next/runtime_bridge_cores.py`,
  `runtime_bridge_composition.py`, or `runtime_bridge_io.py`.
- **C-002**: `resolve_manifest_version()`'s **return value** for every input,
  including a malformed manifest, stays `"1"` — the new `except
  pydantic.ValidationError: return "1"` branch is output-preserving by
  construction, not a behavior change to `NamespaceRef`'s identity tuple.

### Baseline Capture (mission-level pre-requisite — read this before T001)

Per `plan.md`'s "Baseline Capture" section: `main` carries 23 known-red test
failures and 2 errors (#3284). Before this WP's own implementation commit lands,
capture the scoped-surface baseline (see Subtask T001) and record the pass/fail
counts verbatim in this WP's PR-body evidence / the mission's `reviews/` trail. Any
red found here is pre-existing and is carried forward as the explicit baseline for
every subsequent WP's "zero new failures" claim (SC-002) — never silently
attributed to this mission's own changes, and never "fixed" opportunistically. If a
baseline red is discovered that isn't already tracked by #3284, the charter's
Pre-existing Failure Reporting Rule requires filing a GitHub issue for it before
continuing, with the exact command run and why it's judged pre-existing.

### Campsite-Clean Confirmation (mission-level, not a new task)

`plan.md`'s "Campsite-Clean Scope" section already concluded: **no domain-matched
debt was found beyond what the mission's own FRs already prescribe.** The three
`packs/built-in/missions/{research,documentation,software-dev}/expected-artifacts.yaml`
files carry no unrelated lint/type/test debt (plain YAML data). `manifest.py` and
`namespace.py` were read in full while writing the plan; neither carries an open
TODO, a Sonar-flagged complexity violation, or a failing test in this mission's
scope that isn't already one of the FRs. A live Terminology Canon violation —
`software-dev/templates/plan-template.md:4` reads `**Input**: Feature specification
from ...` where the canon requires "Mission" — was observed first-hand and
explicitly evaluated, then ruled **out of this mission's campsite-clean opening
commit**: it is a different file belonging to a different mission type's template,
and its own fix is a distinct, independently-reviewable behavior change to a
doctrine template that ships to every consumer repo (see `plan.md`'s
"Campsite-Clean Scope" section for the full two-part rationale and evidence).
**This WP does not need to fold in any debt** — record this confirmation in the
WP's own commit message / PR-body evidence rather than silently omitting the step.

### ⚠️ Chokepoint note: `tests/dossier/test_manifest.py`

This WP is the **sole owner** of `tests/dossier/test_manifest.py` in `owned_files`
(it is the first WP to touch the file and establishes the new
per-IC-named-section convention plan.md defines: IC-01 → `TestSchemaHardeningAndLoudFailure`,
IC-02 → `TestManifestReconciliation`, IC-03 → `TestPlanManifest`, IC-04 →
`TestOverrideMirrorDeprecation`). WP02, WP03, and WP04 will each append their own
named class to this same file as a documented, small, well-justified **out-of-map
edit** (per the ownership rules in `tasks-packages/prompt.md`) — they do not
declare this file in their own `owned_files`. Because WP02, WP03, and WP04 all
depend only on WP01 and sit together in `lanes.json`'s `parallel_group: 1`
(nominally parallel with each other, with no dependency edge among the three of
them), **all three editing the same file concurrently is a real git-merge risk**
even though their sections are disjoint (independent diffs each appending a new
class near the end of the same file). See tracer-approach.md's "Chokepoints &
execution sequencing" addendum for the orchestrator-level recommendation (sequence
WP02/WP03/WP04's actual execution against this file even though the dependency
graph permits parallelism). This WP's own commit against `test_manifest.py` should
land cleanly since nothing else has touched the file yet.

## Subtask T001: Baseline Capture

**Purpose**: Capture the pre-change pass/fail state of this mission's scoped
validation surface, per `plan.md`'s "Baseline Capture" section, before any
FR-009/FR-016 edit lands.

**Steps**:
1. From the repository root checkout, on this mission's PR branch
   (`pr/expected-artifacts-manifest-repair-01KZY498`), run:
   ```bash
   uv sync --frozen --all-extras
   uv run python -m pytest tests/dossier/ tests/doctrine/missions/ tests/runtime/ \
     tests/charter/test_resolved_mission_type_context.py -q --tb=short
   ```
2. Record the verbatim pass/fail/error counts and any failing test names in this
   WP's PR-body evidence and/or the mission's `reviews/` trail.
3. Classify every red found: if it is already covered by #3284 (or is plainly
   outside this mission's four target directories, matching the plan's expectation
   that this narrower surface should be fast and largely clean), note that and move
   on. If a red is found that is **not** already tracked, file a GitHub issue for it
   per the charter's Pre-existing Failure Reporting Rule (command run + why judged
   pre-existing) **before** continuing to T002.
4. Do not "fix" any baseline red opportunistically as part of this mission's diff.

**Files**: None changed — this is a read-only evidence-capture step.
**Validation**: The baseline counts are recorded in writing (PR body / `reviews/`)
before T002's red-first tests are authored.

## Subtask T002: Red-first tests — FR-009 schema hardening + FR-016 `load_manifest()` loud failure

**Purpose**: Land the failing-first tests for FR-009 and FR-016's `manifest.py`
half, before any implementation commit (C-011).

**Steps**:
1. In `tests/dossier/test_manifest.py`, add a new test class
   `TestSchemaHardeningAndLoudFailure` (a new, dedicated section — do not add these
   tests into any existing class such as `TestExpectedArtifactSpec`/
   `TestExpectedArtifactManifest`/`TestManifestRegistry`).
2. Add `test_expected_artifact_spec_rejects_extra_keyword`: construct
   `ExpectedArtifactSpec(artifact_key="x", artifact_class="input",
   path_pattern="x.md", blocking=True, blockign=True)` (typo'd extra field) inside
   `pytest.raises(pydantic.ValidationError)`.
3. Add `test_expected_artifact_manifest_rejects_extra_keyword`: construct
   `ExpectedArtifactManifest(mission_type="x", required_alwyas=[])` (typo'd
   top-level key) inside `pytest.raises(pydantic.ValidationError)`.
4. Add `test_all_shipped_manifests_load_after_hardening`: load the three shipped
   `expected-artifacts.yaml` files this WP can actually make pass —
   `research`, `documentation`, `software-dev` — via `ManifestRegistry.load_manifest()`
   and assert each returns non-`None`. **Do not assert on `plan` here** — the
   `plan` manifest is authored in WP03, a separate WP that WP01 has no dependency
   on, so a `plan` assertion in this test would be structurally unable to pass at
   WP01's own completion. Add a code comment noting that `plan`'s loadability is
   covered separately by WP03's `TestPlanManifest.test_plan_manifest_loads_and_matches_state_machine`,
   which is the sole place `plan`'s loadability is asserted (not a supplement to
   this test).
5. Create the new fixture directory/file `tests/dossier/fixtures/` (new dir) and
   `tests/dossier/fixtures/expected_artifacts_typo.yaml` (new file) — a real,
   deliberately typo'd manifest (e.g. a top-level `required_alwyas:` key,
   mirroring AS2's example) used by this test and by T003/T004 below.
6. Add `test_load_manifest_raises_on_malformed_yaml`: load the typo'd fixture
   through `ManifestRegistry.load_manifest()` (you will likely need to route the
   fixture through the same `get_expected_artifacts`/doctrine-repository path the
   real loader uses, or monkeypatch `_doctrine_repository()`'s
   `get_expected_artifacts` to return a `ConfigResult` whose `.parsed` is the
   typo'd fixture's parsed YAML — confirm the exact seam by reading
   `manifest.py:200` (`_doctrine_repository().get_expected_artifacts(mission_type)`)
   before choosing the monkeypatch target) and assert it raises
   `pydantic.ValidationError`, not returning `None`.

**Files**: `tests/dossier/test_manifest.py` (new section, ~80-120 lines),
`tests/dossier/fixtures/expected_artifacts_typo.yaml` (new, ~10 lines).
**Validation**: All four new tests are RED against the current (pre-FR-009/FR-016)
code — confirm by running
`uv run python -m pytest tests/dossier/test_manifest.py::TestSchemaHardeningAndLoudFailure -q`
before T005/T006 land.

## Subtask T003: Red-first tests — FR-016 propagation through `reconcile.py` and `rebaseline.py` (AS5)

**Purpose**: Prove the raised `ValidationError` surfaces as a structured, visible
failure through the two genuinely human-facing call sites, using their own
pre-existing fail-closed `except Exception` handlers (no new exception handling
added to `indexer.py` itself — Decision 3).

**Steps**:
1. In `tests/cli/commands/test_reconcile.py`, add
   `test_reconcile_reports_error_on_malformed_manifest` (fits alongside the
   existing `TestLibraryApi`/`TestCli` classes at lines 79/131 — follow their
   existing `tmp_path`/`monkeypatch` fixture pattern for constructing a feature dir
   whose mission type resolves to a manifest that will fail validation, e.g. by
   monkeypatching `ManifestRegistry`/the doctrine repository to serve the typo'd
   fixture from T002 for the mission type under test). Assert the reconciliation
   flow returns `ReconciliationResult(status=ERROR, error=...)` naming the
   underlying `ValidationError`, exercising `cli/commands/reconcile.py:151-160`'s
   own pre-existing `except Exception` (comment: "fail-closed: any rebuild failure
   is an ERROR") — do not add new exception handling to `reconcile.py` itself.
2. In `tests/dossier/test_rebaseline.py`, add
   `test_rebaseline_skips_one_mission_on_malformed_manifest` inside (or alongside)
   the existing `TestRebaselineErrorBranches` class (line 324) — this class already
   houses the error-path tests this new test belongs with. Assert the backlog
   sweep returns a per-mission `RebaselineOutcome(error="reindex_failed: ...")` for
   the one bad mission and **continues** past it for every other mission in the
   sweep (not an aborted sweep), exercising `dossier/rebaseline.py:168-170`'s
   own pre-existing `except Exception` (comment: "one bad mission must not abort
   the backlog sweep") — do not add new exception handling to `rebaseline.py`
   itself.

**Files**: `tests/cli/commands/test_reconcile.py` (~40-60 new lines),
`tests/dossier/test_rebaseline.py` (~30-50 new lines, inside
`TestRebaselineErrorBranches`).
**Validation**: Both tests are RED against current code (the exception never
propagates this far before FR-016 lands, so neither structured-error branch is
exercised).

## Subtask T004: Red-first test — `resolve_manifest_version()` fallback (AS6)

**Purpose**: Prove `sync.namespace.resolve_manifest_version()` keeps its own
"always a string" contract for a malformed manifest, via its own new dedicated
`except pydantic.ValidationError` (not an accident of an unrelated caller's
blanket catch).

**Steps**:
1. In `tests/sync/test_namespace.py`, add
   `test_resolve_manifest_version_returns_one_on_malformed_manifest`. Follow the
   file's existing `unittest.mock.patch`/`MagicMock` pattern (see the module's
   existing imports) to make `ManifestRegistry.load_manifest(mission_type)` raise
   `pydantic.ValidationError` for a chosen mission type (reuse the T002 fixture's
   typo'd content, or construct the error directly via a mocked
   `model_validate` call — either is acceptable; prefer whichever keeps the test
   closest to the real call path).
2. Call `resolve_manifest_version(mission_type)` directly (not through
   `trigger_feature_dossier_sync_if_enabled` or any sync-pipeline wrapper) and
   assert it returns `"1"` — it must not raise.

**Files**: `tests/sync/test_namespace.py` (~20-30 new lines).
**Validation**: RED against current code (today `resolve_manifest_version()` has
no dedicated catch of its own; a raised `ValidationError` would propagate out of
this direct call).

## Subtask T005: Implement FR-009 — `extra="forbid"` on both models

**Purpose**: Make a typo'd keyword argument raise at direct construction.

**Steps**:
1. In `src/specify_cli/dossier/manifest.py`, add `from pydantic import BaseModel,
   ConfigDict, Field` (extend the existing `pydantic` import at the top of the
   file to include `ConfigDict`).
2. Add `model_config = ConfigDict(extra="forbid")` as the first line of the class
   body in `ExpectedArtifactSpec` (currently starting at line 60).
3. Add the same `model_config = ConfigDict(extra="forbid")` as the first line of
   the class body in `ExpectedArtifactManifest` (currently starting at line 90).
4. Do not change any field definition, default, or the `from_yaml_file`/
   `get_step_ids` methods — this is additive `model_config` only.

**Files**: `src/specify_cli/dossier/manifest.py` (~4 new lines).
**Validation**: T002's two `_rejects_extra_keyword` tests go GREEN. Re-run
`test_all_shipped_manifests_load_after_hardening` to confirm no false positive
against the three real shipped manifests it now asserts on
(`research`/`documentation`/`software-dev` — SC-003's "no false positive" bar);
this test is fully GREEN at WP01's own completion, with no carve-out needed since
it no longer asserts on `plan`.

## Subtask T006: Implement FR-016 — `load_manifest()` lets `ValidationError` propagate

**Purpose**: Complete FR-009's promise so it reaches the one production loading
path every real consumer uses.

**Steps**:
1. In `src/specify_cli/dossier/manifest.py`'s `ManifestRegistry.load_manifest()`
   (currently lines 179-215), change the `try/except` block (lines 207-215):
   - Keep `manifest = ExpectedArtifactManifest.model_validate(config.parsed)` and
     the success path (cache + return) unchanged.
   - **Remove the `except Exception as e: logger.error(...); return None` clause's
     handling of `ValidationError` entirely.** The intended code shape has NO
     catch of `pydantic.ValidationError` in `load_manifest()` at all — do not add
     an `except pydantic.ValidationError` block around the `model_validate` call
     either; a raised `ValidationError` must propagate to the caller unhandled by
     this function. If some other, genuinely different exception type still needs
     a bare `except Exception` here, keep only that (none is expected per
     Decision 3).
   - Do **not** change the earlier `if config is None:` branch (line 202) — genuine
     absence still returns `None`.
2. Add `import pydantic` (or `from pydantic import ValidationError` — match the
   file's existing import style; prefer the qualified `pydantic.ValidationError`
   form to match the plan's own citations) near the top of the file.
3. Double-check no other exception type is silently now uncaught that used to be
   caught by the old bare `except Exception` — per Decision 3, the only exception
   type this loading path realistically raises from `model_validate` is
   `pydantic.ValidationError`; if `config.parsed` can itself be malformed in a way
   that raises something else (e.g. a `TypeError` from `model_validate` on a
   non-mapping), leave that uncaught too per FR-016's letter (it changes the
   loud-failure guarantee's scope only for `ValidationError`, matching User
   Story 3's acceptance scenarios exactly — do not broaden or narrow this scope
   without flagging the deviation).

**Files**: `src/specify_cli/dossier/manifest.py` (~5-10 changed lines).
**Validation**: T002's `test_load_manifest_raises_on_malformed_yaml` and T003's two
propagation tests go GREEN. Re-run the full `TestSchemaHardeningAndLoudFailure`
section plus `TestManifestRegistry`/`TestManifestIntegration`/`TestManifestValidation`
(the pre-existing classes) to confirm zero new failures from this narrowing.

## Subtask T007: Implement FR-016 — `resolve_manifest_version()` defensive fallback

**Purpose**: Keep `resolve_manifest_version()`'s own "always a string" docstring
promise, without depending on an unrelated caller's blanket catch (Decision 3,
Option C rejected).

**Steps**:
1. In `src/specify_cli/sync/namespace.py`'s `resolve_manifest_version()` (lines
   90-101), wrap the existing `manifest = ManifestRegistry.load_manifest(mission_type)`
   call in a `try/except pydantic.ValidationError: return "1"` — falling back
   exactly as the function already does for a genuinely-absent manifest (the
   existing `if manifest is not None: return str(manifest.manifest_version)`
   branch and the trailing `return "1"` for `None` are otherwise unchanged).
2. Add the needed `import pydantic` (or `from pydantic import ValidationError`) to
   this file — it currently has no top-level `pydantic` import (check the file's
   import block before adding, to avoid a duplicate).
3. Do not touch `NamespaceRef` construction or any other function in this file.

**Files**: `src/specify_cli/sync/namespace.py` (~4-6 changed lines).
**Validation**: T004's `test_resolve_manifest_version_returns_one_on_malformed_manifest`
goes GREEN. Confirm `NamespaceRef`'s identity-tuple construction (line ~63) is
byte-for-byte unchanged (C-002) — no test should need to change here.

## Definition of Done

- [ ] T001's baseline counts are recorded in writing (PR body / `reviews/`) before
      any of T002-T007 land.
- [ ] `TestSchemaHardeningAndLoudFailure` section exists in
      `tests/dossier/test_manifest.py` with all 4 new tests, committed **before**
      the T005-T007 implementation commit (C-011 red-first).
- [ ] `tests/cli/commands/test_reconcile.py` and `tests/dossier/test_rebaseline.py`
      each carry their new AS5 propagation test, committed before implementation.
- [ ] `tests/sync/test_namespace.py` carries the AS6 fallback test, committed
      before implementation.
- [ ] `ExpectedArtifactSpec` and `ExpectedArtifactManifest` both carry
      `model_config = ConfigDict(extra="forbid")`.
- [ ] `ManifestRegistry.load_manifest()` lets `pydantic.ValidationError` propagate;
      the `config is None` branch is unchanged.
- [ ] `resolve_manifest_version()` has its own dedicated
      `except pydantic.ValidationError: return "1"`.
- [ ] All 7 new/updated tests in this WP are GREEN — including
      `test_all_shipped_manifests_load_after_hardening`, which asserts only on
      the three manifests WP01 owns (`research`/`documentation`/`software-dev`);
      it does not assert on `plan` (that coverage lives in WP03's
      `TestPlanManifest.test_plan_manifest_loads_and_matches_state_machine`), so
      this bullet requires no exception carve-out.
- [ ] `mypy --strict` and `ruff check .` report zero new issues on
      `manifest.py`, `namespace.py`, and every test file this WP touches
      (NFR-002).
- [ ] No change to `runtime_bridge_cores.py`, `runtime_bridge_composition.py`, or
      `runtime_bridge_io.py` (C-001).

## Risks

- **None identified at the implementation level** — pure exception-handling
  narrowing plus a `ConfigDict` addition, both additive/output-preserving for
  every currently-passing input (per `plan.md`'s IC-01 risk assessment).
- **Chokepoint risk on `tests/dossier/test_manifest.py`** — see the "Chokepoint
  note" in Context above. This WP's own commit should land cleanly since it is
  first; the risk materializes for WP02/WP03/WP04 landing after it.
- **Fixture-seam risk in T002/T006**: the exact monkeypatch target for routing a
  typo'd fixture through `ManifestRegistry.load_manifest()` depends on
  `_doctrine_repository()`'s exact signature — read `manifest.py`'s
  `_doctrine_repository()` helper (near the top of the file) before writing T002's
  test to confirm the correct patch point, rather than guessing.

## Reviewer Guidance

- Confirm `load_manifest()` in `manifest.py` has **no** `except
  pydantic.ValidationError` (or equivalent) clause around the `model_validate`
  call at all — the raised `ValidationError` must propagate to the caller
  unhandled, per T006 step 1. A reviewer who finds any catch of
  `ValidationError` reintroduced here (narrowed or otherwise) should reject the
  change. Also confirm this removal did not silently swallow a different,
  previously-caught exception type in a way that changes other callers'
  behavior — re-run the full `tests/dossier/` and `tests/sync/test_namespace.py`
  suites, not just this WP's new tests.
- Confirm `resolve_manifest_version()`'s new `except` clause is genuinely
  output-preserving (returns the same `"1"` for absence and for malformation) —
  this is the concrete guard for C-002/Decision 2.
- Confirm no change was made to `dossier/indexer.py` — Decision 3 explicitly rules
  this out; a reviewer seeing a diff there should reject it.
- Confirm the red→green evidence: each new test was RED on `main` (or this WP's
  own pre-implementation commit) and GREEN on the WP's final commit (C-011).

Implementation command: `spec-kitty agent action implement WP01 --agent claude`
