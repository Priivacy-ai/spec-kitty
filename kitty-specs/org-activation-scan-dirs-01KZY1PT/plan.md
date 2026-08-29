# Implementation Plan: `_org_scan_dirs` must scan the real org-pack layout, not a phantom one

**Branch**: `pr/org-activation-scan-dirs` | **Date**: 2026-08-13 | **Spec**: [kitty-specs/org-activation-scan-dirs-01KZY1PT/spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/org-activation-scan-dirs-01KZY1PT/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See
`.kittify/overrides/missions/software-dev/command-templates/plan.md` for the execution
workflow (the source template lives under `src/doctrine/missions/software-dev/`; there is no
separate `plan-template.md` for this mission type — `plan.md` is scaffolded directly from the
command template referenced above, same as `spec.md` was scaffolded empty at the specify phase).

The planner will not begin until all planning questions have been answered — capture those
answers in this document before progressing to later phases. This is a small, surgical,
one-work-package mission; the planning questions below are answered directly from the spec
rather than through an interactive interview, per the command template's own scope-proportionality
rule (§ "Scope proportionality (CRITICAL)" — trivial/simple changes get a light pass, not a full
platform-level interrogation).

## Summary

`charter.activation.kind_vocabulary._org_scan_dirs` (`src/charter/activation/kind_vocabulary.py:200-209`) scans only
`<org_root>/<plural>/built-in/` — a layout no real org pack uses — so `resolve_artifact_urn`
can never find an org pack's own artifacts, and every `charter activate` call silently drops
them from the filtered DRG (FR-001's defect). The fix adds a second, ordered-first scan entry
for the flat `<root>/<plural>` layout (`recursive=False`, matching the live loader,
`doctrine.service.DoctrineService._org_dirs` / `BaseDoctrineRepository`) while keeping the
existing `<root>/<plural>/built-in` entry (`recursive=True`) for backward compatibility — an
additive fix, not a layout swap. The technical approach is exactly what the spec already
specifies (FR-001's ~5 LOC body, FR-002's activation-filter-level regression test, FR-003's
unit-level extension); this plan's job is to fix the seam, the gate set, the sequencing, and the
test placement around that already-decided fix — not to re-derive the fix itself.

## Technical Context

**Language/Version**: Python 3.11+ (repo-wide baseline; no version-specific feature used by
this change).
**Primary Dependencies**: None added or changed. The fix uses only `pathlib.Path` (already
imported in `src/charter/activation/kind_vocabulary.py`) — no new import, no new third-party dependency.
**Storage**: N/A — the function reads directory existence off the local filesystem
(`Path.is_dir()`); no database, no persisted state format changes.
**Testing**: `pytest`, using the repo's existing fixture idioms (`tmp_path`, `monkeypatch`)
already in use throughout `tests/charter/`. No new test infrastructure, no new fixture
libraries.
**Target Platform**: Linux/macOS/Windows CLI host, same as the rest of the CLI — this change
does not introduce or remove any platform-specific behavior (the existing `_org_scan_dirs`
and its new sibling entry are pure `pathlib` directory checks, portable as-is).
**Project Type**: Single project (this repository, `spec-kitty` itself) — not web/mobile.
**Performance Goals**: Not applicable at mission scale — the added scan entry is one extra
`Path.is_dir()` check per configured org root per kind, negligible against the CLI's existing
`<2s` typical-operation budget (charter § Performance and Scale).
**Constraints**: The constraints that matter here are the spec's own C-001 through C-005
(bounded file set, no D1 code, no neighboring-helper refactor, red-first, no new suppressions)
— see the Gate Set and Campsite-Clean sections below, not a runtime performance constraint.
**Scale/Scope**: One function's behavior changed (`_org_scan_dirs`), ~5 LOC, in one file
(`src/charter/activation/kind_vocabulary.py`) — plus a docstring-only update to that function's caller
(`_scan_roots`, see Campsite-Clean Scope) in the same file — plus test changes in exactly two
test files (one extended, one new) — see Test Placement Decision below. One work package, one
PR.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** — the fix brings `_org_scan_dirs` into agreement with the one
  already-canonical org-layer layout (`DoctrineService._org_dirs` / `BaseDoctrineRepository`);
  it does not introduce a second, competing definition of "where org artifacts live." Pass.
- **Architectural alignment** — the change stays entirely inside the charter layer's existing
  scan-root abstraction (`_scan_roots` → `(Path, bool)` list → `_iter_artifact_paths` /
  `resolve_artifact_urn`); no new seam, no new module boundary. Pass.
- **Domain-driven splits + tiered rigour** — `_org_scan_dirs` is core resolution logic (not
  glue/IO), so full rigour (red-first test, full precedence coverage) applies, matching FR-002
  and FR-003. Pass.
- **ATDD-first** — FR-002's acceptance scenario (Acceptance Scenario 1) is the contract the
  regression test drives outside-in, at the `filter_graph_by_activation` level, not a
  unit-level shortcut. Pass.
- **`RECONCILE_CHANGE_SCOPE_TENSIONS`** (smallest-viable-diff → Boy Scout → Locality of Change)
  — already resolved in the spec's own Clarifications: the file set is
  `src/charter/activation/kind_vocabulary.py` plus the two test files named below; `_built_in_scan_dir`
  and `_layer_scan_dirs` (C-003) are deliberately not touched. This plan does not relitigate
  that resolution — see Campsite-Clean Scope below. Pass, by inheritance from the spec.
- **Standing Order #9 (red-main discipline)** — this mission does not touch or depend on any
  currently-red test; it adds new tests and fixes an independent defect. The pre-existing red
  baseline (#3284, #3283) is accounted for separately so it is never misattributed to this
  change — see Known-Red Baseline below. Pass.

No charter violation requires justification; Complexity Tracking below is empty by design.

## Related, Not Fixed

"Single canonical authority" above is scoped to what this mission actually touches, not to the
whole "charter activation subsystem." Live-code verification surfaces two adjacent, still-open
divergences this mission's C-001 file set does not close — named here so a reader of this plan
alone knows they remain open, not silently missed:

- **The `layer_roots`/`_layer_scan_dirs` cascade path.** `_layer_scan_dirs`
  (`src/charter/activation/kind_vocabulary.py:219-228`, via `_layer_candidate_dir`, `:212-216`) resolves an
  org layer to a **third** directory shape, `<root>/doctrine/<plural>/org` — distinct from both
  this mission's flat `<root>/<plural>` fix and the legacy `<root>/<plural>/built-in` shape
  `_org_scan_dirs` already scans. It is reached only via `layer_roots`, never `org_roots`:
  `charter.drg._resolve_activated_urns_for_kind` (`src/charter/drg.py:333-381`) calls
  `resolve_artifact_urn` with `org_roots` only (the call at `:374-377`; `org_roots` is built from
  `pack_context.org_roots` alone at `:397`, never `layer_roots`), while
  `src/specify_cli/cli/commands/charter/activate.py`'s `_source_urn` (`:87-119`, invoked at `:466`
  on every `charter activate` call — with or without `--cascade` — to decide between rendering the
  no-cascade warning and actually cascading) calls `resolve_artifact_urn` with `layer_roots` only,
  never `org_roots`. This mission's fix corrects
  the DRG activation-filter path (what `filter_graph_by_activation` uses and what the spec's
  Acceptance Scenarios test); it does not touch, and does not close, the cascade-warning/DRG-id
  path's independent `layer_roots`-only resolution of the `<root>/doctrine/<plural>/org` shape.
- **`CharterPackManager._resolve_org_layer_dir`'s FR-013 precedent.**
  `src/charter/activation/pack_manager.py:238-253` already reconciles flat vs. legacy for a related seam:
  its docstring states outright that "FR-013 unifies the charter activation subsystem with
  runtime... Flat is therefore the canonical, preferred layout. The legacy nested
  `<pack>/doctrine/<plural>/org/` layout is kept as a fallback." Concretely, it checks the flat
  `root / kind.plural` directory first and falls back to `root / "doctrine" / kind.plural /
  "org"` (the same shape `_layer_scan_dirs` builds via `_layer_candidate_dir`) only when flat is
  absent — a **mutually-exclusive precedence** choice (one directory wins outright). This
  mission's chosen fix is a *different* reconciliation shape for a *different* flat-vs-legacy
  pair: it scans **both** the flat `<plural>` and the legacy `<plural>/built-in` directories
  additively whenever each exists, with flat winning only on a same-stem file collision (FR-001),
  never dropping the legacy directory's other contents. Both are defensible answers to the
  charter's "single canonical authority" tension, reached from different call sites, but this
  plan does not cite FR-013's precedent or reconcile the two shapes — that reconciliation is out
  of this mission's bounded scope (C-001); it is recorded here, not silently missed.

## The Seam

This change lands entirely in the charter layer, in one pure function and its tests:

- **Production surface**: `src/charter/activation/kind_vocabulary.py`, function `_org_scan_dirs`
  (`:200-209`) is the sole *behavioral* edit. Its caller's (`_scan_roots`, `:142-181`) own
  call-chain logic, and *its* caller's (`resolve_artifact_urn`, `:253+`), are unchanged — both
  already consume whatever `_org_scan_dirs` returns via the established `(Path, bool)` list
  contract, so the fix needs no logic change above or below it in the call chain.
  `_scan_roots`'s docstring is also edited, though: the sentence at `:158-160` describing what
  `org_roots` contributes goes stale the moment the fix lands, so the implementing WP updates it
  as part of the fix commit — see Campsite-Clean Scope below for the full rationale.
- **No CLI surface.** `charter activate` itself (`src/charter/activation/pack_manager.py`) is unchanged;
  the fix is entirely inside the resolution helper it calls transitively. No Typer command,
  option, or JSON output shape changes.
- **No doctrine schema.** Nothing under `src/doctrine/*.models` or the generated JSON Schemas
  changes; the fix does not add, remove, or reshape any doctrine artifact type.
- **No kernel, no mission-loader.** `src/charter/activation/kind_vocabulary.py` is outside both
  `src/kernel/**` and `src/specify_cli/mission_loader/**` — see Gate Set below for why their
  dedicated 90% coverage jobs are structurally inapplicable, not merely "not run this time."
- **`resolve_artifact_urn`'s real consumer set is wider than the drg.py path this spec's
  Acceptance Scenarios exercise, and two of those consumers observe a real behavior change.**
  `resolve_artifact_urn` (`:253+`) is called from `charter.activation.compiler._resolve_config_activated_ids`
  (`src/charter/activation/compiler.py:112-149`), threaded `org_roots` by
  `_resolve_config_activated_roots` (`:187`, `list(pack_context.pack_roots[1:])`) for every
  activated kind on the `charter synthesize` path, and from
  `charter.activation.consistency_check`'s config↔graph parity guard (`_check_reference_id_parity`,
  `:744-748`; `_resolve_graph_kind_parity_stem`, `:815-819`) — both pass real `org_roots` today.
  `compiler.py`'s call site has **no** `try`/`except`: its own docstring (`:135-140`) states a
  stem that cannot resolve "raises `UnknownArtifactIdError` ... rather than being silently
  dropped," so for a flat-layout org pack that activates its own stem, `charter synthesize`
  **crashes today** — a second, more severe symptom of this same root cause, not merely a silent
  drop. `consistency_check.py`'s two call sites both narrowly catch `UnknownArtifactIdError`, but
  only one reports directly: `_resolve_graph_kind_parity_stem` (`:815-819`) appends to
  `verification_errors`/`suggestions` from within its own `except` block, while the forward-parity
  call site (`:744-748`) does a bare `continue` and relies on the separate
  `_check_unknown_references` check to report that stem. After the fix, resolution succeeds for
  the fixture's stem at both call sites instead of raising. Neither consumer is on the
  `filter_graph_by_activation` path FR-002's regression test
  exercises, and neither is covered by FR-003's `_org_scan_dirs`/`resolve_artifact_urn`
  unit-level cases. See "Nothing Generated, No Contract Movement" below for what this plan does
  about that gap.

## Nothing Generated, No Contract Movement

Explicit, not silently omitted or assumed: this mission regenerates none of the following, and
none of the following contract-shaped surfaces move.

- **Doctrine schema** — `scripts/generate_schemas.py`'s sources are `doctrine.*.models`
  (`:140-545`); nothing in `src/charter/activation/kind_vocabulary.py` is a schema source, so the freshness
  check (below) passes trivially without any regeneration step being run by this WP, and no
  schema contract moves.
- **Contextive glossary** — the glossary generator (`scripts/generate_contextive_glossaries.py`)
  reacts to new/changed domain terms, not to a scan-directory bugfix. This mission introduces no
  new glossary term; no `generate_contextive_glossaries.py` regeneration is needed even though
  the freshness *check* runs (see Gate Set).
- **Agent-command copies** — no `.kittify/overrides/missions/**/command-templates/*` or any
  agent-facing command doc changes; this is a pure library-code fix with no CLI/command surface
  touched (see The Seam above).
- **Mission step contracts, action indices, `orchestrator-api`, `spec-kitty-events`** — all
  untouched; none sit on the call path between `charter activate` arming `activated_directives`
  and `_org_scan_dirs` finding (or failing to find) an org-pack directory, so none are cited in
  the spec's Key Entities or Requirements. The defect and its fix remain contained to one
  resolution helper and its direct callers — **except** for the two additional
  `resolve_artifact_urn` consumers (`compiler.py`, `consistency_check.py`) named in The Seam
  above, whose *behavior* (not their contract shape) changes as a side effect of the fix.

**Test-coverage decision for those two consumers** (resolving the gap The Seam names, sized
proportionally to a one-WP, ~5 LOC mission rather than deferred wholesale): coverage for **both**
`compiler.py`'s and `consistency_check.py`'s behavior change is **deliberately deferred**, not
added, because neither is authorized by this mission's bound test scope. spec.md's C-001 confines
test changes to "one new or extended test module for the activation-filter-level regression
(FR-002)" — tied to FR-002's own text, which scopes the new module to the full `activate()` →
`filter_graph_by_activation()` round trip. Neither FR-002 nor any other FR/C in spec.md names
`compiler.py`, `_resolve_config_activated_ids`, or `consistency_check.py`'s parity guards; C-001's
file-level authorization for one new test module is not the same thing as content-level
authorization to assert an unrelated consumer's behavior inside it. Extending FR-002's scope (or
adding a companion FR/C) in spec.md to formally close this gap is a legitimate future option, but
amending spec.md's FR/C list is out of scope for a plan-phase fix pass — this plan narrows back to
what spec.md already authorizes rather than growing it unilaterally.

For `compiler.py`: its call site has no `try`/`except`, so a flat-layout org pack that activates
its own stem crashes `charter synthesize` today (`UnknownArtifactIdError`, per the call site's own
docstring at `:135-140`) — the more severe of the two symptoms The Seam names above. Post-fix,
that same call succeeds instead of crashing. That flip is real and is recorded here for a future
reader, but this mission's tests do **not** assert it — it is an explicitly deferred gap, not
silently assumed covered, and not part of FR-002/C-001's authorized scope.

For `consistency_check.py`: coverage is deferred for the same authorization reason above, and
additionally because its post-fix effect is a lower-severity shift (an already-reported
"unresolved" stem starts resolving cleanly, not a crash), asserting it correctly would require
driving `consistency_check.py`'s own multi-argument internal helpers rather than reusing the
FR-002 fixture directly, and `test_this_project_charter_pack_is_coherent` does not incidentally
cover it for this repository (this repo's own `.kittify/config.yaml` has no org pack configured at
all). Both gaps are recorded here as known, lower-priority follow-ups rather than silently
assumed covered.

## Gate Set

Verified against `.github/workflows/ci-quality.yml` and `pyproject.toml` directly (not assumed)
for this specific diff shape (`src/charter/activation/kind_vocabulary.py` + `tests/charter/*`):

| Gate | Applies? | Why |
| --- | --- | --- |
| Kernel coverage ≥90% (`kernel-tests`) | No | Path-scoped to `src/kernel/**` only; this diff touches neither `src/kernel` nor any file that job's `changes` filter selects on. |
| Mission-loader coverage ≥90% (`mission-loader-coverage`) | No | Path-scoped to `src/specify_cli/mission_loader/**`; not touched by this diff. |
| `fast-tests-charter` pytest shard | **Yes — the relevant shard.** | Runs `tests/charter tests/specify_cli/charter_freshness tests/specify_cli/charter_lint tests/specify_cli/charter_preflight` with `-m "fast and not windows_ci and not timing"`, `--cov=charter --cov-fail-under=55` (module-level floor). Every file this mission touches or adds lives under `tests/charter/`, and `tests/charter/conftest.py`'s `pytest_collection_modifyitems` auto-marks every collected test `fast`, so no test in this mission needs an explicit `@pytest.mark.fast` to be picked up here. |
| `ruff check` (repo-wide zero-issue) | Advisory, not blocking | `.github/workflows/ci-quality.yml`'s ruff step runs `continue-on-error: true` and only feeds a PR-comment job (`lint-feedback`) — it does not fail CI. CLAUDE.md's "zero issues" is a house rule this mission still honors (no ruff findings expected on a ~5 LOC pure-function change plus straightforward test additions), but it is not what makes the build red or green. |
| `mypy --strict` (repo-wide zero-issue) | Advisory, not blocking | Same shape as ruff above — `continue-on-error: true`, PR-comment only. Honored anyway: the fix's new tuple entry is the same `(Path, bool)` type the function already returns, so no new annotation burden. |
| TID251 banned-API (`ruff check src tests --select TID251`) | Applies, expected clean | Enforced (no `continue-on-error`). Bans raw `hashlib.sha256` and catching `click.exceptions.*` directly (`pyproject.toml`). Neither appears anywhere near a directory-existence check or its tests. |
| Commitlint | Applies (advisory, not blocking) | `.github/workflows/ci-quality.yml`'s "[ENFORCED] Run commit message linting" step (`:672-675`) carries `continue-on-error: true`, the same shape as the ruff/mypy rows below; its `has_failures` output feeds only the PR-comment `lint-feedback` job (`:987-990`), and the outcome-check step that turns a `continue-on-error` failure into a real job failure (`:976-985`) names only `bandit` and `pip_audit` — never `commitlint`. This is a house rule (per CLAUDE.md), not a CI-blocking gate: the `spec-kitty safe-commit` commit for this plan (and later, the WP's own commits) still must carry a conventional-commit-shaped subject, but a malformed one would not fail CI. |
| Markdown lint | No | `kitty-specs/**` is in the ignore list; this plan and the spec it extends are never scanned by the markdown-lint step. |
| Doctrine schema freshness | Applies, passes trivially | Runs unconditionally in the `lint` job, but its sources are `doctrine.*.models`; nothing in this diff is a schema source, so `generate_schemas.py --check` has nothing new to find stale. |
| Contextive glossary freshness | Applies (in scope, not triggered) | The check-scope glob includes `src/charter/**`, so touching `kind_vocabulary.py` puts this diff in scope for the check to *run* — but the fix introduces no new domain term, so `generate_contextive_glossaries.py check` passes without any regeneration. |
| Typer JSON error-surface gate | No | Gates a specific CLI command-group test (`tests/agent/test_json_group_typer_surface.py`); this diff touches no CLI surface. |
| `patch()` target validation (`scripts/check_patch_targets.py`) | Applies only if triggered | Regex-matches `@patch(...)` / `patch("...")` call strings. FR-002/FR-003's tests are expected to use `tmp_path` fixtures and, where needed, `monkeypatch.setattr` (the idiom already used by the sibling `TestBuiltInScanDirHelper` tests in `tests/charter/test_kind_vocabulary_scan_roots.py`) rather than `unittest.mock.patch` — if that idiom is followed, this gate has nothing to validate. |
| Bandit (security static analysis) | Applies, enforced | Runs on every PR over all of `src/` with no path filter; the job fails if the step's outcome isn't `success` (checked explicitly downstream, independent of the step's own `continue-on-error`). A directory-existence check and list-append introduce no plausible medium+ finding. |
| pip-audit (dependency CVEs) | Applies, unaffected by this diff | Same enforced-via-outcome-check shape as Bandit; this diff adds no dependency, so any result is pre-existing and independent of this change. |
| `uv.lock` freshness (`uv lock --check`) | Applies, passes trivially | Runs on every PR; this diff makes no `pyproject.toml`/dependency change, so the lockfile cannot drift because of it. |
| SonarCloud Quality Gate | No | Job condition is schedule/`workflow_dispatch` only (`if: ... github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'`) — PRs skip Sonar entirely per the workflow's own comment (pending #825); it is not a per-PR gate for this or any mission today. |
| **`diff-coverage` (90% floor on changed lines, critical-path allowlist)** | **Yes — the binding coverage floor for this diff.** | `src/charter/*` is explicitly in the critical-path allowlist the `diff-coverage` job enforces. This — not the 55% module-level `fast-tests-charter` floor, and not the kernel/mission-loader 90% floors — is the coverage bar this mission's changed lines in `kind_vocabulary.py` must clear. FR-002 (activation-filter-level) and FR-003 (5 new unit cases) together are sized to cover every changed branch of the ~5 LOC fix (flat-present, legacy-present, both-present, neither-present, same-stem-precedence) specifically so this floor is met without padding. |

## Known-Red Baseline

`main` currently carries two known, tracked-elsewhere red/capacity signals that must not be
misattributed to this mission's diff:

- **#3284** — the full suite has ~23 untracked failures and 2 errors after bootstrap prewarm on
  `main`. Not caused by, and not fixed by, this mission.
- **#3283** — the shared test-venv lock can time out under concurrent sessions; a capacity
  signal, not a flake, and independent of this mission's test additions.

Because of this, the work package's own sequencing (see Red-First Discipline below) baselines
the touched surface **before** any code change: the existing
`tests/charter/test_kind_vocabulary_scan_roots.py` was run in this checkout, pre-fix, scoped to
the same marker expression the `fast-tests-charter` CI shard uses
(`-m "fast and not windows_ci and not timing"`), and is fully green today — 14 passed, no
failures, no errors, confirming the pre-existing unit coverage of `_org_scan_dirs` carries none
of #3284's noise. The WP repeats this scoped baseline (the same file, plus the new FR-002 module
once it exists) immediately before authoring the fix, so any red the WP sees afterward is
attributable to the fix itself, never confused with #3284/#3283. Running the full `fast-tests-charter`
shard (all four directories) is reserved for the WP's own pre-PR validation pass, per the
charter's own directory-scoped testing guidance ("run only the affected test packages... whenever
the change is scoped to a known surface") — not for this planning-phase spot check.

## Campsite-Clean Scope

`src/charter/activation/kind_vocabulary.py` also contains `_built_in_scan_dir` and `_layer_scan_dirs` —
structurally similar, similarly terse helpers sitting right next to `_org_scan_dirs` in the
touched file. Standing Order #2 (campsite cleaning) and the Boy Scout Rule (`DIRECTIVE_025`)
would, on their own, license folding in a tidy-up of those neighbors since the file is already
open. This plan does **not** do that, deliberately: the spec's own Clarifications already ran
`RECONCILE_CHANGE_SCOPE_TENSIONS` on exactly this question (C-003) and Locality of Change wins
as the brake — `_built_in_scan_dir` and `_layer_scan_dirs` are not broken and are not the cited
defect, so touching them would not be a proportional tidy-up of the surface this mission is
fixing, it would be scope creep into two unrelated functions that happen to share a file. There
is no campsite-clean tidy-up of `_built_in_scan_dir` or `_layer_scan_dirs` beyond the
`_org_scan_dirs` fix itself. This is not re-litigated here — it is inherited from the spec as a
settled decision. (A distinct, mandatory docstring edit on `_org_scan_dirs`'s own caller
follows below — not a campsite tidy-up of a neighboring helper, but adjacent debt the fix
itself causes.)

One piece of adjacent debt *was* found, and it is directly caused by the change rather than a
neighboring helper: `_scan_roots`'s own docstring (`src/charter/activation/kind_vocabulary.py:158-160`,
`_org_scan_dirs`'s immediate caller) states, present-tense, that "``org_roots`` preserves the
legacy package-shaped root contract where each root contributes ``<root>/<plural>/built-in`` --
this nested layout is still live for org packs." Once FR-001 lands, `org_roots` also
contributes the flat `<root>/<plural>` layout — this sentence goes stale the moment the fix
merges, in the very function the plan already touches. Because this is the same file and the
same caller's docstring (not `_built_in_scan_dir`/`_layer_scan_dirs`, which stay untouched per
C-003), updating it is not scope creep: **the implementing WP must update this docstring
sentence** as part of the fix commit, so it accurately describes both the flat and legacy
entries `org_roots` now contributes.

## Red-First Discipline (WP Sequencing)

FR-002's regression test must be authored and shown failing against the current, unfixed
`_org_scan_dirs` body **before** the ~5 LOC fix lands (Standing Order #4, C-004). This is an
ordering constraint on the mission's single work package, not a separate review-time check:

1. Author the FR-002 activation-filter-level regression test (see Test Placement Decision)
   against the pre-fix `src/charter/activation/kind_vocabulary.py`.
2. Run it and confirm red — the expected pre-fix failure is, unconditionally, the assertion that
   the org directive's node is **absent** from `filter_graph_by_activation`'s output graph.
   FR-002 (spec.md) constrains this test to the full `activate()` → `filter_graph_by_activation()`
   round trip, never a direct `resolve_artifact_urn()` sub-assertion — and for that round-trip
   shape, a raised `UnknownArtifactIdError` can never be the observed failure:
   `_resolve_activated_urns_for_kind` (`src/charter/drg.py:371-381`) calls `resolve_artifact_urn`
   inside a `try`/`except UnknownArtifactIdError: continue` (`:379-380`) that swallows the
   exception before it can propagate out of `filter_graph_by_activation`. (A
   `resolve_artifact_urn`-raises assertion is legitimate, but only for FR-003's unit-level test,
   which per spec.md Acceptance Scenario 2 calls `resolve_artifact_urn` directly — it is not part
   of FR-002's own red-first attribution.)
3. Apply the FR-001 fix to `_org_scan_dirs` (the flat-layout scan entry, ordered first,
   `recursive=False`, alongside the retained legacy `built-in/` entry, `recursive=True`).
4. Re-run the same FR-002 test unmodified and confirm green.
5. Extend `TestOrgScanDirsHelper` with FR-003's 5 new cases (flat-only, legacy-only,
   both-present, neither-present, same-stem-precedence) without deleting existing coverage;
   confirm green.
6. Run the full gate set above (the `fast-tests-charter` shard scoped to
   `tests/charter tests/specify_cli/charter_freshness tests/specify_cli/charter_lint
   tests/specify_cli/charter_preflight`, plus ruff/mypy/TID251/Bandit/pip-audit locally where
   feasible) before opening the PR.

Both the red run and the green run are recorded by the implementing WP (SC-001) — either as
captured command output in the WP's own notes, or as two distinct commits (a red-evidencing
commit followed by the fix commit), never a single commit that adds an already-green test.

## Test Placement Decision

- **FR-003 (unit-level)**: extends the existing `TestOrgScanDirsHelper` class in
  `tests/charter/test_kind_vocabulary_scan_roots.py` (currently 3 methods at `:125-135`) with 5
  new test methods, without deleting `test_none_org_roots_returns_empty_list`,
  `test_missing_org_built_in_dir_skipped`, or `test_existing_org_built_in_dir_returned`. The
  file already carries module-level `pytestmark = [pytest.mark.unit, pytest.mark.fast]`
  (`:35`) — new methods inherit both markers automatically; no per-method marker is needed.
- **FR-002 (activation-filter-level)**: a **new** module,
  `tests/charter/test_org_scan_dirs_activation_regression.py`. Considered and rejected as
  extension targets: `test_activation_filtered_drg.py` (hermetic, in-memory `PackContext`
  construction only — no on-disk org-pack fixture, and its own scope is mission-step-contract
  activation, not org-pack directory layout), `test_drg_filtering.py` and
  `test_drg_activation_gate.py` (each already document a distinct, separately-numbered past
  defect — WP08's per-artifact-ID gate and WP01's stem/canonical mismatch, respectively — and
  folding an unrelated org-scan-dirs regression into either would blur their own documented
  scope), and `test_org_activations_resolution.py` /
  `test_org_activations_reach_context.py` (both scoped to `activations:` stanza rendering in
  `charter.activation.context`, a different consumer of org packs entirely, not `resolve_artifact_urn` /
  `filter_graph_by_activation`). A new file is explicitly permitted by C-001 ("plus one new or
  extended test module") and is the better fit here: it gets its own on-disk fixture (a flat
  `<org_root>/directives/<stem>.directive.yaml` plus a root-level `<org_root>/<stem>.graph.yaml`
  DRG-node fixture per FR-002's fixture-construction note) and its own RED/GREEN attribution
  narrative, mirroring the precedent already set by `test_drg_activation_gate.py`'s own
  RED-on-merge-base / GREEN-after-fix documentation style, without inheriting any other file's
  unrelated history. No new marker is needed here either: any test collected under
  `tests/charter/` is auto-marked `fast` by `tests/charter/conftest.py`'s
  `pytest_collection_modifyitems` hook, so the new module is picked up by the
  `fast-tests-charter` shard's `-m "fast and not windows_ci and not timing"` selection without
  any explicit `pytestmark`. An explicit `pytestmark = pytest.mark.fast` is added anyway, to
  match the visible convention in sibling org-pack fixture files
  (`test_org_activations_resolution.py:37`, `test_org_activations_reach_context.py:35`) rather
  than relying on the conftest hook silently. This module does **not** carry a
  `compiler._resolve_config_activated_ids` assertion — see "Nothing Generated, No Contract
  Movement" above for why that consumer's coverage is deliberately deferred, not added here.

## PR Shape

One PR, per the `sk-implement` default ("default PR shape is one PR per mission"), adapted from
its general form: this is a spec-kitty **design-phase mission targeting `main` directly**
(topology `single_branch`, no lane branch minted — see spec header), not a
`spec-kitty-saas`-style mission with a per-work-package-PR rule. There is exactly one work
package (FR-001 + FR-002 + FR-003 together — see Project Structure below), so one PR is not a
simplification of a larger default, it is the only shape that makes sense at this mission's
size. `tasks.md`, the next phase, formalizes this WP; this plan does not propose any WP
breakdown structure.

## Tracer Files

`tracer-tooling-friction.md`, `tracer-approach.md`, and `tracer-design-decisions.md` already
exist in this mission directory, seeded at the specify phase. This planning pass:

- Appends **one** new dated entry to `tracer-tooling-friction.md` (below) recording that
  `spec-kitty plan --mission org-activation-scan-dirs-01KZY1PT --json` scaffolded `plan.md`
  cleanly on the first call, with a `blocked` result whose `blocked_reason` was the expected
  "Technical Context is still placeholder text" gate, not a tooling defect.
- Does **not** add a new entry to `tracer-approach.md` or `tracer-design-decisions.md` — the
  approach (additive fix, flat-layout entry ordered first, `recursive=False`) and the design
  decisions (D1/D2 separation, no neighboring-helper refactor, additive-not-replacing fix,
  recursive-flag parity) were already fully recorded at the specify phase and this plan makes no
  decision beyond executing them. Duplicating that content here would be redundant, not
  additive.
- Cross-reference: this mission already hit and resolved two tooling defects at the specify
  phase — SK-09 (protected-`main` branch refusal) and SK-11 (missing git identity swallowed by
  `safe-commit`) — see `tracer-tooling-friction.md`'s own "Commit blocked" / "Resolution" entries
  for the full, self-contained account (this mission directory's tracer file, not any
  repository-external tracking surface).

## Project Structure

### Documentation (this mission)

```
kitty-specs/org-activation-scan-dirs-01KZY1PT/
├── spec.md               # Mission specification (already complete)
├── plan.md               # This file
└── tasks.md              # Phase 2 output (/spec-kitty.tasks command — NOT created by /spec-kitty.plan)
```

`research.md`, `data-model.md`, `contracts/`, and `quickstart.md` are **not produced** by this
plan. This is a proportionality decision, not an omission: the change has no unresolved
`NEEDS CLARIFICATION` (the spec already pins the recursive-flag choice, the precedence rule,
and the fixture-construction approach), no new entity or data model (a `(Path, bool)` tuple list
is the entire "data model," and it already exists), and no API/contract surface (no endpoint, no
webhook, no CLI option). Generating those four files for a ~5 LOC pure-function fix would be
template-filling for its own sake, not planning proportional to the mission — the command
template's own scope-proportionality rule for trivial/simple changes applies.

### Source Code (repository root)

```
src/
└── charter/
    └── kind_vocabulary.py           # _org_scan_dirs (:200-209) fix, plus the _scan_roots
                                      # docstring update at :158-160 (see Campsite-Clean Scope)

tests/
└── charter/
    ├── test_kind_vocabulary_scan_roots.py            # extended: TestOrgScanDirsHelper +5 (FR-003)
    └── test_org_scan_dirs_activation_regression.py   # new: activation-filter-level red-first test (FR-002)
```

**Structure Decision**: Single project (this repository). No new directory, no new package —
one function's behavior edited in place (`_org_scan_dirs`), plus a docstring update on its
caller (`_scan_roots`); two test files (one extended, one new) in the directory the function's
tests already live in. See Test Placement Decision above for the FR-002 module's name and the
reasoning for a new file over extending an existing one.

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified*

None. Charter Check above found no violation requiring justification.

## Implementation Concern Map

Omitted. This section exists to decompose architectural intent into IC-## concerns when a
mission has multiple distinct architectural areas informing task decomposition
(`/spec-kitty.tasks` then translates those concerns into work packages). This mission has one
concern — the `_org_scan_dirs` fix plus its two-file test coverage — which is already exactly
one work package by construction; introducing IC-## labels for a single-concern, single-WP
mission would create decomposition structure with nothing to decompose. `tasks.md` will
formalize the one WP directly.
