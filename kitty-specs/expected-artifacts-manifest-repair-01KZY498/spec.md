# Mission Specification: Expected Artifacts Manifest Repair

**Mission Branch**: `expected-artifacts-manifest-repair-01KZY498`
**Created**: 2026-08-13
**Status**: Draft
**Target Branch**: `main`
**Mission Type**: software-dev
**Input**: GitHub issue [#3388](https://github.com/Priivacy-ai/spec-kitty/issues/3388) — "`expected-artifacts.yaml` is unreliable: 'plan' manifest missing, blocking entries contradict every observed mission, schema drops typos silently"

## Clarifications

Two decisions were made by the operator before planning began. Both are binding; they are
recorded here (not only in session memory) so the review squad evaluates the spec against
the decisions actually made, not against the raw ambiguity that prompted them.

### Session 2026-08-13

- **Q: How should the new `plan` mission-type manifest be authored, given
  `runtime_bridge_cores.py` has no `plan`-family guard branch at all (verified: `evaluate_guards()`
  dispatches only `research` and `documentation` to their own tables; everything else, including
  `plan`, falls to `_evaluate_software_dev_guards`, whose vocabulary — `specify`/`plan`/
  `tasks_outline`/`tasks_packages`/`tasks_finalize`/`tasks` (composed)/`implement`/`review`, 8 ids
  in total — matches none of `plan` mission type's own state names **except one: `review`**, which
  lexically collides with software-dev's own `review` step id. Compounding this, the actual
  invocation path for every mission type, `plan` included, is `_check_cli_guards`
  (`src/runtime/next/runtime_bridge.py:680-698`), which hardcodes `mission_family="software-dev"`
  regardless of the mission's real type — the mission-family-aware composed-action path
  (`_dn_composition_dispatch`) is reachable only when `mission == "software-dev"`. So a `plan`
  mission's `review` step is evaluated by `_evaluate_software_dev_guards`'s `if step_id in
  ("implement", "review")` branch (`runtime_bridge_cores.py:564-565`), which calls
  `_evaluate_wp_iteration_guard("review", snapshot)` — not the bare `return []` fallback every
  OTHER `plan`-type step id (`goals`/`research`/`structure`/`draft`/`done`) reaches. Today this
  coincidentally still returns `[]`, because `wp_advance_ready` defaults `True` when a plan
  mission's directory has no `tasks/` subdirectory (`_should_advance_wp_step`,
  `runtime_bridge.py:618-630`) — but it is a real, reachable, mission-blind branch: if a plan
  mission's directory ever contained a `tasks/WP*.md` set, its `review` step would be spuriously
  blocked with a nonsensical software-dev WP-status message)?**
  **A: Author it honestly, and file the guard gap separately.** `plan/expected-artifacts.yaml` is
  keyed on `plan` mission type's own step vocabulary and real artifacts (`goals.md`, `research.md`,
  `plan.md`, per `packs/built-in/missions/plan/mission.yaml`'s `goals → research → structure →
  draft → review → done` state machine and its `transitions[].conditions` — not on
  `software-dev`'s vocabulary, which `plan`-type steps are evaluated against today (mostly a no-op,
  except for the `review`-step vocabulary collision and hardcoded-`mission_family` mechanism
  described above, which carries a latent spurious-block risk) but which does not describe what a
  `plan` mission actually produces). It is documentation-only content, consistent
  with this mission's "content + schema only" scope — it explicitly does not claim
  `runtime_bridge_cores.py`'s CLI-guard table enforces it. A separate upstream issue is filed
  (FR-011) naming the real defect this investigation surfaced — the hardcoded
  `mission_family="software-dev"` in `_check_cli_guards` combined with the accidental `review`-step
  vocabulary collision (latent spurious-block risk), not merely "no branch recognizes plan step
  ids" — as its own, independently real defect, discovered during this investigation but not
  named in #3388, and not fixed here.
  **Rejected alternatives:** mirroring `software-dev`'s manifest 1:1 (produces a manifest that
  reads as authoritative but describes a step vocabulary `plan` missions don't use and an
  artifact set they don't produce — reproducing #3388's own "unreliable, unsafe to gate on"
  failure mode inside its own remedy); dropping the `plan` manifest from this mission's scope
  entirely (under-delivers against the issue's explicit claim 1 without flagging why).

- **Q: Should `manifest_version` be bumped when manifest content is reconciled, given
  `resolve_manifest_version()` (`src/specify_cli/sync/namespace.py:90-101`) feeds it into
  `NamespaceRef`'s 5-field identity tuple for hosted-SaaS sync body uploads
  (`namespace.py:35,63`, consumed at `sync/dossier_pipeline.py:344,351`)?**
  **A: Do not bump it — keep `manifest_version: "1"` on all four manifests.** Nothing in this
  repository branches on the value beyond string equality inside the namespace tuple. Bumping
  would change the sync namespace key for every already-synced artifact body of that mission
  type, and this repository has no visibility into `spec-kitty-saas` to verify there is a
  migration path for orphaned/duplicated synced bodies that a key change would produce. This
  mission treats the reconciliation as a **corrective patch to the existing version**, not a new
  version — the manifest's *content* becomes accurate, but its *identity* for sync purposes does
  not change. The rationale is recorded inline as a YAML comment in each of the four manifest
  files (not only here), so a future reader who reasons "content changed, so version should bump"
  sees why that instinct was deliberately overridden.
  **Rejected alternative:** bumping `manifest_version` to `"2"` on the manifests whose
  `required_by_step` shape materially changes (documentation, software-dev). Semantically more
  honest but changes a live sync identity key in a system (`spec-kitty-saas`) this PUBLIC repo
  cannot verify the blast radius of — an uninvestigated cross-repo side effect, not a content
  fix.

## Overview

### Motivation

`expected-artifacts.yaml` is the per-mission-type manifest declaring which artifacts are
expected at each step of a mission's lifecycle — read by the dossier indexer for completeness
reporting, by `resolve_manifest_version()` for hosted-sync namespace identity, and by
`mission_type_profiles._resolve_expected_artifacts_slot()` for the
`ResolvedMissionType.expected_artifacts` slot (a real consumer exists for this slot — see
"Non-Gate Consumer Notes" below). As shipped, the manifest is **not reliable enough
to ever become a gate authority** (a direction its own `blocking:` field hints at, and which the
issue explicitly names as its future purpose):

1. Three of the four built-in mission types ship a manifest; `plan` does not.
2. The `blocking: true` entries on the `research` manifest (`findings.md`, `report.md`)
   contradict every one of the 13 non-software-dev missions in this repo's own `kitty-specs/`
   history — all 13 produced `spec.md`/`plan.md`/`tasks.md`; **zero** produced `findings.md` or
   `report.md`. Wiring a gate to the manifest as shipped would retroactively block every future
   research/documentation mission on files no such mission has ever created.
3. `ExpectedArtifactSpec` — **and, verified during this investigation, its outer container
   `ExpectedArtifactManifest` as well** — has no `model_config`, so Pydantic's default
   `extra="ignore"` behavior silently drops a misspelled key at either the per-artifact level
   *or* the top-level manifest level (e.g. a typo'd `required_alwyas:` block is parsed as if it
   were absent, not rejected).
4. Reconciled against `runtime_bridge_cores.py`'s guard tables (the CLI next-loop's own
   independent source of truth for what actually blocks step advancement), the three shipped
   manifests disagree with the guards on 8 steps — under-specifying, over-specifying, omitting
   entirely, or checking an artifact the guard never checks. Each is a named, independently
   verified bug (FR-001 through FR-008, below).
5. `tasks/WP*.md` appears in **zero** manifest entries despite **four** call sites in
   `runtime_bridge_cores.py` checking for it (`_evaluate_tasks_packages_guard`,
   `_evaluate_tasks_finalize_guard`, `_evaluate_composed_tasks_packages_guard`,
   `_evaluate_composed_tasks_terminal_guard` — verified by direct read; the issue said two call
   sites, the real number is four).
6. The `artifact_key` vocabulary used by these manifests (`"input.spec.main"` style, a dotted
   string) is structurally disjoint from `step.yaml`'s `template.artifact_key`
   (`IDENTIFIER_PATTERN`-constrained bare identifier, e.g. `spec`) — the two surfaces that should
   agree on artifact identity cannot be joined mechanically. **Out of scope for this mission**;
   see "Out of Scope" below.

### Corrected risk framing — the issue's "zero-risk" claim does not hold as written

The issue states: *"today no gate consumes the manifest ... which is precisely why fixing it now
is zero-risk: content and schema hardening only, no consumer changes."* Verified against this
checkout, that framing is **too strong** and this spec does not repeat it:

- **Schema hardening (`extra="forbid"`) is genuinely low-risk.** Grepped the tree for any writer
  that constructs a manifest dict with extra keys — none found. Adding `extra="forbid"` to both
  `ExpectedArtifactSpec` and `ExpectedArtifactManifest` changes no current runtime behavior.
- **Content reconciliation is not risk-free**, because there are **three** live readers of the
  manifest, not the "the dossier indexer" the issue names as the sole consumer:
  1. **`specify_cli.dossier.indexer.Indexer`** — 4 call sites (`rebaseline.py`, the `reconcile`
     CLI command, `sync/dossier_pipeline.py`), all downstream of the same reader. The
     acknowledged consumer; content changes are visible here by design (that is the fix).
  2. **`sync.namespace.resolve_manifest_version()`** — a second, independent
     `ManifestRegistry.load_manifest()` caller feeding `NamespaceRef.manifest_version`, one of 5
     fields keying hosted-SaaS sync body uploads (`namespace.py:63`,
     `f"|{self.mission_type}|{self.manifest_version}"`). Load-bearing for sync identity. This is
     precisely why Decision 2 (manifest_version non-bump) exists: content reconciliation alone,
     with `manifest_version` held at `"1"`, keeps this reader's output identical before and
     after this mission.
  3. **`charter.mission_type_profiles._resolve_expected_artifacts_slot()`** — a third,
     independent reader that bypasses `ManifestRegistry`/Pydantic entirely: it reads via
     `MissionTemplateRepository.get_expected_artifacts()` directly and checks only
     `isinstance(parsed, Mapping)`. The resulting property lives on
     `ResolvedMissionType.expected_artifacts`, a `@cached_property`
     (`src/charter/mission_type_profiles.py:404-409`) — **not** on `MissionTypeProfile`, a
     separate `pydantic.BaseModel` with no such attribute. A real consumer exists:
     `tests/charter/test_resolved_mission_type_context.py:160-162` asserts directly on
     `bundle.expected_artifacts`'s presence, type, and `mission_type` key for `software-dev` — the
     exact mission type whose manifest content this mission materially changes (FR-006/FR-007/
     FR-008). So "no gate consumes it" is narrower than it first appears: no *gate* consumes it,
     but a *contract test* does, and this mission's reconciliation must still satisfy that test's
     three assertions (folded into NFR-003/FR-015, below). This path bypasses the Pydantic schema
     entirely (the `extra="forbid"` fix, FR-009, is invisible to it) while still being sensitive
     to *content* changes. See "Non-Gate Consumer Notes" below for what this mission does to keep
     both of these readers correct going forward.
  4. **`tests/dossier/test_manifest.py:404`** pins the current, wrong,
     `plan`+`tasks.md`-conflated behavior as expected (`assert all(s.blocking for s in plan_md +
     tasks_md)`, asserted against the software-dev manifest's `plan` step). Reconciling FR-006
     requires changing this test — a real, planned test-file change (FR-013), not a zero-diff
     side effect.

### A second-order finding: the `.kittify/overrides/` mirror copies are not consumed at all

The issue's blast radius (and the readiness investigation that preceded this spec) named
`.kittify/overrides/missions/{research,documentation,software-dev}/expected-artifacts.yaml` as
mirror copies of `packs/built-in/missions/.../expected-artifacts.yaml` requiring reconciliation
"or the drift compounds." Verified directly against `src/doctrine/missions/repository.py`:

- `ManifestRegistry.load_manifest()` (the dossier indexer's path) and
  `mission_type_profiles._resolve_expected_artifacts_slot()` (the third reader above) both go
  through `MissionTemplateRepository.get_expected_artifacts()`, whose private path method
  `_expected_artifacts_path()` (`repository.py:476-490`) composes
  `self._root / mission / "expected-artifacts.yaml"` with **no override tier at all** — unlike
  the sibling resolvers for `templates/`/`command-templates/` and `mission.yaml`, which *do*
  check `.kittify/overrides/missions/{mission}/...` first. These are two separate checks in two
  separate functions, not one unified location: the templates/command-templates override check is
  in `_resolve_asset()` (`src/doctrine/resolver.py:172-183`); the `mission.yaml` override check is
  in a separate function, `resolve_mission()` (`src/doctrine/resolver.py:331-334`).
  `self._root` resolves through `MissionTemplateRepository.default_missions_root()` →
  `doctrine.pack_paths.built_in_missions_root()` — the shipped **built-in pack only**.
- Practical consequence: `packs/built-in/missions/*/expected-artifacts.yaml` is the **sole
  consumed copy** for every reader identified in this repository. The
  `.kittify/overrides/missions/*/expected-artifacts.yaml` files are present on disk but are
  currently dead from a consumption standpoint for this specific artifact type.
- This is worse for reliability than "mirrors that could drift," not better: a maintainer editing
  `.kittify/overrides/` believing it takes precedence (as it does for every other doctrine asset
  type in this same directory tree) would silently produce no effect. Direct diff also confirms
  the copies have **already drifted materially**, not just on one optional entry as previously
  reported:
  - `research`: override is missing the `runtime.charter-lint.decay` optional entry present in
    built-in (previously known).
  - `documentation`: override is additionally missing the entire `accept:` step block (present
    in built-in, empty list) and the `runtime.charter-lint.decay` optional entry.
  - `software-dev`: override's `implement:` step is **already `[]`** (i.e., it does *not* have
    the FR-008 `analysis-report.md` over-specification bug that built-in has), but it is also
    missing the `NOTE on occurrence_map.yaml` documentation comment and the
    `runtime.charter-lint.decay` optional entry that built-in carries.
- FR-014 addresses this — but not by refreshing the dead copies' content. **Editorial call**
  (Decision 4, `tracer-design-decisions.md`): keeping a confirmed-dead second copy "in sync" as
  "drift hygiene" is the literal shape of the parity-with-a-dead-quirk pattern the charter's
  DIRECTIVE_044 names as the anti-pattern to avoid ("chase unification, not parity with a dead
  quirk") — refreshing it would restate the same single-canonical-authority problem this section
  just diagnosed, dressed up as maintenance, rather than resolving it. Instead, FR-014 marks each
  override copy as explicitly deprecated/inert via a header comment, so a maintainer who finds it
  (believing, correctly for every *other* doctrine asset type, that `.kittify/overrides/` takes
  precedence) is told directly why editing it here has no effect, rather than being invited to
  keep investing in content that can never be read. Full deletion was considered and rejected:
  deleting removes the historical starting point a future override-tier-wiring mission would want,
  and a present-but-marked-dead file is discoverable in a way a deleted one is not (a future
  reader would need git archaeology to learn it ever existed). No new override file is created for
  `plan` (FR-010 note): since no `.kittify/overrides/missions/plan/` directory exists today and
  the override tier is inert for this file type, creating a brand-new unconsumed file would add
  confusion, not consistency. Wiring the override tier to actually cover
  `expected-artifacts.yaml` (so `.kittify/overrides/` behaves consistently with every sibling
  doctrine asset type) is a distinct runtime/resolver behavior change and is explicitly out of
  this mission's "content + schema only" scope; it is named as a follow-up candidate, not filed
  as a mandatory deliverable of this mission — the deprecation comment points at that follow-up
  directly.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manifest content matches guard-enforced reality (Priority: P1)

As a future engineer wiring `expected-artifacts.yaml` to an actual completeness gate, I need the
three shipped manifests (`research`, `documentation`, `software-dev`) to describe exactly what
`runtime_bridge_cores.py`'s guard tables already check — no more, no less — so that turning the
manifest into a gate does not retroactively block missions on artifacts no guard has ever
required and no observed mission has ever produced.

**Why this priority**: This is the reliability defect the issue exists to fix; every other
change in this mission is secondary to it.

**Independent Test**: For each of the 8 named divergences (FR-001–FR-008), read the corresponding
manifest key before and after the change and confirm it now matches the guard branch's actual
artifact check (or is explicitly commented as non-filesystem-expressible, e.g. a count threshold
or WP-status check the `ExpectedArtifactSpec` schema has no field for).

**Acceptance Scenarios**:

1. **Given** the reconciled `research/expected-artifacts.yaml`, **When** `ManifestRegistry
   .get_required_artifacts(manifest, "gathering")` is queried, **Then** it returns a spec for
   `source-register.csv` (blocking), matching `_evaluate_gathering_guard`'s filesystem check —
   the `source_documented_count >= 3` half of the guard is documented as a non-expressible
   runtime check via an inline YAML comment, not silently omitted.
2. **Given** the reconciled `documentation/expected-artifacts.yaml`, **When** `required_by_step`
   is inspected for `audit` and `design`, **Then** `audit` requires only `gap-analysis.md`
   blocking and `design` requires only `plan.md` blocking — the previously-required `plan.md`/
   `tasks.md` entries that `_evaluate_documentation_guards` never checks at those steps are
   removed.
3. **Given** the reconciled `documentation/expected-artifacts.yaml`, **When** `required_by_step`
   is inspected for `validate` and `publish`, **Then** `validate` requires `audit-report.md`
   blocking and `publish` requires `release.md` blocking, matching
   `_evaluate_documentation_guards`'s checks at those steps (both previously empty).
4. **Given** the reconciled `software-dev/expected-artifacts.yaml`, **When** `required_by_step`
   is inspected for `plan`, **Then** it requires only `plan.md` blocking (the `tasks.md`
   requirement is removed, matching `_evaluate_software_dev_guards`'s `plan` branch, which checks
   only `plan.md`).
5. **Given** the reconciled `software-dev/expected-artifacts.yaml`, **When** `required_by_step`
   is inspected for `tasks_outline`, `tasks_packages`, and `tasks_finalize`, **Then** each of the
   three CLI-native task steps (previously entirely absent) has an entry matching its guard: 
   `tasks_outline` → `tasks.md` blocking; `tasks_packages` and `tasks_finalize` → a `tasks/WP*.md`
   glob entry blocking, satisfying both claim 5 (the missing glob) and FR-007 in the same edit.
6. **Given** the reconciled `software-dev/expected-artifacts.yaml`, **When** `required_by_step`
   is inspected for `implement`, **Then** it is empty (`analysis-report.md` is no longer required
   — the actual `implement` guard, `_evaluate_wp_iteration_guard`, checks only WP lane status,
   never filesystem artifacts).
7. **Given** the fully reconciled manifest set, **When** every `required_by_step` key across all
   three manifests is cross-checked against `runtime_bridge_cores.py`'s guard-table branches,
   **Then** every key either matches a real guard branch's check or carries an inline comment
   explaining why it cannot be schema-expressed (e.g. the occurrence-gate / dependency-frontmatter
   checks at `tasks_finalize`) — this is the acceptance bar the issue itself sets: *"reconciled
   against observed artifacts, not merely schema-valid."*

---

### User Story 2 - `plan` mission type ships a manifest, honestly scoped (Priority: P1)

As a doctrine maintainer or a downstream mission-type author extending the manifest mechanism, I
need the `plan` mission type to ship an `expected-artifacts.yaml` like its three siblings, so
there is one consistent per-type place to look up artifact expectations — without that manifest
falsely implying a guard enforces it when none currently does.

**Why this priority**: Directly named as claim 1 in the issue; the missing manifest is the most
visible asymmetry among the four built-in mission types.

**Independent Test**: Load `plan/expected-artifacts.yaml` via `ManifestRegistry
.load_manifest("plan")`, confirm it parses, confirm its `required_by_step` keys match
`plan/mission.yaml`'s own state names (`goals`, `research`, `structure`, `draft`, `review`,
`done`) rather than `software-dev`'s CLI vocabulary, and confirm the follow-up guard-gap issue
required by Decision 1 exists on the tracker.

**Acceptance Scenarios**:

1. **Given** `packs/built-in/missions/plan/expected-artifacts.yaml` (new file), **When** it is
   loaded and validated against `ExpectedArtifactManifest`, **Then** it parses without error and
   `mission_type: "plan"`, `manifest_version: "1"`.
2. **Given** the new manifest, **When** `required_by_step` is inspected, **Then** its keys are
   `goals`, `research`, `structure`, `draft`, `review`, `done` — matching `plan/mission.yaml`'s
   state list, not `software-dev`'s `specify`/`plan`/`tasks_outline`/... vocabulary that `plan`
   type steps happen to fall through to today.
3. **Given** the new manifest, **When** `goals`, `research`, and `draft` are inspected, **Then**
   they require `goals.md`, `research.md`, and `plan.md` respectively (matching
   `plan/mission.yaml`'s own `transitions[].conditions: ['artifact_exists("...")']` — the state
   machine's own gate, a mechanism distinct from `runtime_bridge_cores.py`'s guard table).
   `structure`, `review`, and `done` have no filesystem-artifact requirement in the new manifest,
   matching `mission.yaml`'s transitions for those states — but the two remaining transitions are
   not gated the same way: `structure→draft` carries no `conditions:` key at all (unconditional),
   while `review→done` gates on `gate_passed("plan_approved")`
   (`packs/built-in/missions/plan/mission.yaml:40-42,48-52`).
4. **Given** the new manifest, **When** its header comment is read, **Then** it states explicitly
   that `plan` mission type's step ids are not enforced by a dedicated `plan`-family guard branch:
   `goals`/`research`/`structure`/`draft`/`done` fall to `_evaluate_software_dev_guards`'s bare
   `return []`, and `review` — because `_check_cli_guards` hardcodes `mission_family="software-dev"`
   for every mission type — lexically collides with software-dev's own `review` step id and is
   evaluated by `_evaluate_wp_iteration_guard`, today returning `[]` only because
   `wp_advance_ready` defaults `True` with no `tasks/` directory present (a latent spurious-block
   risk, not a second no-op fallback). So this manifest is descriptive of `plan`'s own
   state-machine contract, not proven cross-consistent with a second, CLI-native enforcement
   mechanism that today is mission-blind by accident, not by design.
5. **Given** the mission's completion, **When** the tracker is checked, **Then** a new GitHub
   issue exists (filed as FR-011) naming the real defect — `_check_cli_guards`'s hardcoded
   `mission_family="software-dev"` combined with `plan/mission.yaml`'s accidental `review`-step-id
   vocabulary collision (latent spurious-block risk) — as an independent defect, distinct from
   #3388, not resolved by this mission.

---

### User Story 3 - A misspelled manifest key fails loudly (Priority: P2)

As a doctrine author hand-editing `expected-artifacts.yaml`, I need a typo'd field name (at
either the per-artifact or the top-level manifest level) to raise a validation error immediately,
so a broken manifest is caught at author-time instead of silently parsing as if the typo'd data
were simply absent.

This guarantee must reach every real caller of the manifest, not merely direct model
construction. **Editorial call** (recorded as Decision 3 in `tracer-design-decisions.md`, scope
corrected during the second fix round — see the "corrected blast radius" note there):
`ManifestRegistry.load_manifest()` (`src/specify_cli/dossier/manifest.py:207-215`) is the sole
production loading path for every real consumer (the dossier indexer, `resolve_manifest_version()`),
and its current bare `except Exception as e: logger.error(...); return None` converts a schema
`ValidationError` into the same `None` result as "manifest not found" — silently dropping the very
typo this user story exists to catch. Completing the fix so it reaches production (FR-016, below)
is judged in scope, but its blast radius is stated precisely rather than as "it touches only
`manifest.py`" (that claim, present in an earlier draft, is false against FR-016's own text and
was flagged by fresh-eyes review SPEC-FRESH-001): reading the actual call graph of every real
`load_manifest()` caller shows the change is **manifest.py** (the raise) **plus one narrow,
output-preserving defensive catch inside `sync/namespace.py`'s `resolve_manifest_version()`** —
and, having read that call graph, explicitly **not** `dossier/indexer.py`, whose own callers
(`reconcile.py`, `rebaseline.py`, the sync-dossier pipeline) already fail closed on any exception
today, so they need no new code to "handle a raised `ValidationError` explicitly." No guard logic
in `runtime_bridge_cores.py`/`runtime_bridge_composition.py`/`runtime_bridge_io.py` is touched
(C-001 remains untouched). FR-016 below states the caller-side scope precisely, file by file.

**Why this priority**: Directly named as claim 3; lower priority than User Stories 1–2 because it
is a preventive fix for a class of future mistake, not a repair of a currently-wrong value.

**Independent Test**: Construct `ExpectedArtifactSpec` and `ExpectedArtifactManifest` with an
extra, misspelled keyword argument each and confirm both raise a Pydantic `ValidationError`
rather than silently discarding the field. Additionally, load a deliberately typo'd real YAML
fixture through `ManifestRegistry.load_manifest()` and confirm the failure surfaces to the caller
(FR-016) rather than being swallowed to `None`.

**Acceptance Scenarios**:

1. **Given** `ExpectedArtifactSpec(artifact_key="x", artifact_class="input",
   path_pattern="x.md", blocking=True, blockign=True)` (typo'd extra field), **When**
   constructed, **Then** it raises `pydantic.ValidationError` (currently: silently succeeds,
   discarding `blockign`).
2. **Given** `ExpectedArtifactManifest(mission_type="x", required_alwyas=[])` (typo'd top-level
   key), **When** constructed, **Then** it raises `pydantic.ValidationError` (currently: silently
   succeeds, discarding `required_alwyas`, leaving `required_always` at its empty default with no
   signal that the author's intent was lost).
3. **Given** the four shipped `expected-artifacts.yaml` files (three reconciled + the new
   `plan` manifest) after FR-009's schema hardening lands, **When** each is loaded via
   `ManifestRegistry.load_manifest()`, **Then** all four still load successfully — the hardening
   introduces no false positive against real shipped content.
4. **Given** a real `expected-artifacts.yaml` fixture with a typo'd top-level key (e.g.
   `required_alwyas:`), **When** it is loaded via `ManifestRegistry.load_manifest()`, **Then**
   the `ValidationError` propagates to the caller instead of being caught by the bare `except
   Exception` and converted to `None` (FR-016) — the loud-failure guarantee reaches the one path
   every real consumer uses, not merely direct Pydantic construction in a test.
5. **Given** the same typo'd fixture wired as a mission's manifest, **When** a dossier is rebuilt
   through either real indexer-side entry point — `reconcile.py`'s reconciliation flow or
   `rebaseline.py`'s backlog sweep, both calling `Indexer(ManifestRegistry()).index_feature(...)`
   — **Then** the propagated `ValidationError` is caught by that call site's own pre-existing
   fail-closed `except Exception` (no new exception handling added to `indexer.py` itself) and
   surfaces as a structured, visible failure: `ReconciliationResult(status=ERROR, error=...)`
   naming the underlying error for `reconcile`, or a `RebaselineOutcome(error="reindex_failed:
   ...")` skip (not an aborted sweep) for `rebaseline`.
6. **Given** the same typo'd fixture, **When** `sync.namespace.resolve_manifest_version(mission_type)`
   is called directly, **Then** it still returns `"1"` — it does not raise — because FR-016 adds a
   dedicated `except pydantic.ValidationError` fallback inside `resolve_manifest_version()` itself.
   This confirms `NamespaceRef`'s sync-identity tuple stays byte-identical to pre-mission behavior
   for a malformed manifest, matching Decision 2/C-002, rather than relying on the unrelated outer
   catch in `trigger_feature_dossier_sync_if_enabled`.

### Edge Cases

- What happens when a manifest's `required_by_step` key names a step id that no longer exists in
  the mission type's current `mission.yaml`/guard vocabulary (e.g. a future rename)? Out of scope
  for this mission — `ManifestRegistry.validate_manifest()` already checks path-pattern shape but
  not step-id/guard-vocabulary cross-consistency; FR-012 adds a one-time reconciliation audit for
  the current state, not an ongoing structural gate. A structural (test-time) parity check between
  manifest step keys and guard-table branches, so this class of drift cannot silently recur, is
  named as a natural follow-up but is not itself required by this mission's acceptance bar.
- How does a project running an already-in-flight mission (planned but not yet at `implement`)
  see this change? The manifest is read fresh on each `ManifestRegistry.load_manifest()` call
  (subject to the process-lifetime `_cache`); no gate currently blocks on it, so an in-flight
  mission's runtime behavior is unaffected — the dossier indexer simply reports against the
  corrected artifact set the next time it runs.
- What happens to `manifest_version` string comparisons for a mission whose artifact body was
  already synced under `manifest_version: "1"` before this change? Per Decision 2, nothing —
  the version string is unchanged, so `NamespaceRef`'s identity tuple is byte-identical before and
  after this mission for every mission type.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Reconcile `research/gathering`: add `source-register.csv` blocking requirement; document the non-expressible `source_documented_count >= 3` guard check inline | US1 | High | Open |
| FR-002 | Reconcile `documentation/audit`: remove the `plan.md`/`tasks.md` blocking entries the guard never checks there; keep only `gap-analysis.md` blocking | US1 | High | Open |
| FR-003 | Reconcile `documentation/design`: remove the `tasks.md` blocking entry the guard never checks there; keep only `plan.md` blocking | US1 | High | Open |
| FR-004 | Reconcile `documentation/validate`: add `audit-report.md` blocking requirement (previously `[]`) | US1 | High | Open |
| FR-005 | Reconcile `documentation/publish`: add `release.md` blocking requirement (previously `[]`) | US1 | High | Open |
| FR-006 | Reconcile `software-dev/plan`: remove the `tasks.md` entry (the guard checks only `plan.md` at this step; `tasks.md` belongs to the CLI-native `tasks*` steps, per FR-007) | US1 | High | Open |
| FR-007 | Add `software-dev/tasks_outline`, `tasks_packages`, `tasks_finalize` `required_by_step` entries matching `_evaluate_cli_tasks_guard`'s three branches — `tasks_outline` requires `tasks.md`; `tasks_packages` and `tasks_finalize` each require a `tasks/WP*.md` glob (this satisfies the standalone `tasks/WP*.md` glob addition named by the issue's claim 5 in the same edit). The `tasks_packages` entry additionally carries an inline YAML comment documenting that `_evaluate_tasks_packages_guard` (`runtime_bridge_cores.py:484-489`) also enforces `requirement_mapping_failures` — a second, non-filesystem-expressible check on the same guard branch — mirroring the inline-comment treatment already required for `tasks_finalize`'s occurrence-gate/dependency-frontmatter checks (AS7/SC-001) | US1 | High | Open |
| FR-008 | Reconcile `software-dev/implement`: remove the `analysis-report.md` blocking entry the guard (`_evaluate_wp_iteration_guard`, WP-lane-status only) never checks | US1 | High | Open |
| FR-009 | Add `model_config = ConfigDict(extra="forbid")` to **both** `ExpectedArtifactSpec` and `ExpectedArtifactManifest` in `src/specify_cli/dossier/manifest.py` | US3 | High | Open |
| FR-010 | Author `packs/built-in/missions/plan/expected-artifacts.yaml` (new), keyed on `plan` mission type's own state machine (`goals`/`research`/`structure`/`draft`/`review`/`done`) and real artifacts (`goals.md`, `research.md`, `plan.md`), per Decision 1. Do not create a `.kittify/overrides/missions/plan/` mirror (no such override existed before; the override tier is inert for this file type — see "A second-order finding" above) | US2 | High | Open |
| FR-011 | File a new upstream GitHub issue naming the real defect this investigation surfaced: `_check_cli_guards` (`runtime_bridge.py:680-698`) hardcodes `mission_family="software-dev"` for every mission type rather than resolving the mission's actual type, so `plan`-type missions are always evaluated against `_evaluate_software_dev_guards`'s vocabulary; combined with `plan/mission.yaml`'s `review` state accidentally lexically colliding with software-dev's own `review` step id, this produces a mission-blind branch with a latent spurious-block risk — not merely "no branch recognizes plan step ids." Per Decision 1. Record the issue URL in the PR body and in `tracer-design-decisions.md` | US2 | High | Open |
| FR-012 | Reconcile `tests/dossier/test_manifest.py:395-404` (`test_software_dev_manifest_plan_step_has_plan_and_tasks`): update the assertion to match FR-006/FR-007's corrected shape (`plan` step requires only `plan.md`; `tasks.md` requirement moves to a new `tasks_outline`-scoped assertion). Add new tests for FR-001–FR-005, FR-008 divergence fixes, FR-009's `extra="forbid"` rejection (both classes), FR-010's `plan` manifest, FR-016's `load_manifest()` loud-failure behavior, its propagation through `reconcile.py`'s reconciliation flow and `rebaseline.py`'s backlog sweep (AS5), and `resolve_manifest_version()`'s dedicated `except pydantic.ValidationError` fallback (AS6) | US1, US2, US3 | High | Open |
| FR-013 | Keep `manifest_version: "1"` unchanged on all four manifests (three reconciled + `plan`, new); record Decision 2's rationale — `manifest_version` is a sync-namespace identity key, not a content-freshness counter, and bumping it would rekey `NamespaceRef`'s identity tuple for every already-synced artifact body with no verified `spec-kitty-saas` migration path — as an inline YAML comment in each of the four files, not only in this spec | — | High | Open |
| FR-014 | Mark `.kittify/overrides/missions/{research,documentation,software-dev}/expected-artifacts.yaml` as explicitly deprecated/inert via a header comment, rather than refreshing their content to parity with the reconciled `packs/built-in` copies — per Decision 4 (editorial call, `tracer-design-decisions.md`): "refresh to keep in sync" is parity with a dead quirk (charter DIRECTIVE_044), the exact anti-pattern this mission's own second-order finding names. The header comment states the file is not consumed by any resolver for this asset type (see "A second-order finding" above) and points at the override-tier-wiring follow-up issue as where a future correction belongs | — | Medium | Open |
| FR-015 | Audit and, if needed, update `tests/runtime/test_bridge_cores.py`, `tests/integration/test_research_runtime_walk.py`, `tests/integration/test_documentation_runtime_walk.py`, `tests/doctrine/missions/test_repository.py`, and `tests/charter/test_resolved_mission_type_context.py` (the last one a confirmed real consumer, per "Non-Gate Consumer Notes" — its three assertions on `bundle.expected_artifacts` for `software-dev` must still pass after FR-006/FR-007/FR-008's content reconciliation) for assertions that depend on the pre-reconciliation manifest content | US1 | Medium | Open |
| FR-016 | Change `ManifestRegistry.load_manifest()`'s exception handling (`src/specify_cli/dossier/manifest.py:207-215`) to distinguish `pydantic.ValidationError` from genuine manifest absence: let `ValidationError` propagate to the caller instead of being caught by the bare `except Exception`; the earlier `config is None` branch (line 202) is unchanged and continues to return `None` for a genuinely absent manifest. **Caller-side scope, stated per file (verified against the live call graph, not assumed):** (a) `src/specify_cli/dossier/indexer.py`'s four `load_manifest()` call sites (lines 123, 176, 355, 407) need **no code change**. Every production entry point into `Indexer.index_feature()` already wraps the call in its own dedicated, fail-closed `except Exception`: the `reconcile` CLI command (`cli/commands/reconcile.py:151-160`, comment "fail-closed: any rebuild failure is an ERROR"), the rebaseline backlog sweep (`dossier/rebaseline.py:162-170`, comment "one bad mission must not abort the backlog sweep"), and `sync/dossier_pipeline.py`'s `sync_feature_dossier()` (its own dedicated `except Exception` at lines 243-250 around the `Indexer.index_feature()` call at line 245, independent of that function's outer catch). A raised `ValidationError` therefore already surfaces as a visible `ReconciliationResult(status=ERROR, error=...)` from `reconcile`, and a per-mission `error="reindex_failed: ..."` skip from the rebaseline sweep — both genuinely human-facing, using pre-existing code, not a new handler (AS5 pins this). `sync/dossier_pipeline.py`'s `sync_feature_dossier()` also fail-closes internally on the same raised exception, producing a `DossierSyncResult(dossier=None, errors=[str(e)])` rather than propagating it — this prevents an unhandled-exception crash, but it does **not** reach an operator: `sync_feature_dossier()` is itself wrapped by `trigger_feature_dossier_sync_if_enabled`, and every real production caller of that wrapping function (verified against the live call graph: `merge/executor.py`, `cli/commands/research.py`, `cli/commands/agent/tasks_mark_status.py`, `sync/__init__.py`'s default event handler, and several further fire-and-forget call sites under `cli/commands/agent/`) discards the returned `DossierSyncResult` without reading `.errors`. So a typo routed through the sync-pipeline path alone produces the same operator-visible outcome before and after FR-016: nothing observable — a different internal mechanism (a structured result vs. an uncaught exception), identical external silence. This is a known, named residual gap, not claimed as fixed here: see Decision 5 in `tracer-design-decisions.md` for why this mission does not widen scope to close it. (b) `src/specify_cli/sync/namespace.py`'s `resolve_manifest_version()` (lines 90-101) is the one real caller with **no dedicated catch of its own** — its only protection today is the unrelated outer `except Exception` at `dossier_pipeline.py:368` inside its sole caller, `trigger_feature_dossier_sync_if_enabled` — and its own docstring commits to returning "the manifest_version from the registry if available, otherwise ... '1'" for every input. FR-016 therefore adds one narrow, explicit change here: wrap its `load_manifest()` call in `except pydantic.ValidationError: return "1"`, falling back exactly as it already does for a genuinely-absent manifest. This keeps its return value for a malformed manifest byte-identical to today (`"1"`), so `NamespaceRef`'s sync-identity tuple is unaffected and Decision 2/C-002's sync-pipeline-untouched boundary holds without depending on an unrelated caller's blanket catch as an accidental safety net. Editorial call recording why this scope was chosen: see User Story 3 motivation above and Decisions 3 and 5 in `tracer-design-decisions.md` | US3 | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No runtime consumer behavior change | `runtime_bridge_cores.py`'s guard tables (`evaluate_guards()` and every function it dispatches to) are not modified by this mission — reconciliation direction is manifest-to-match-guard, never the reverse, per the readiness investigation's resolved-not-open determination | Correctness | High | Open |
| NFR-002 | Type/lint cleanliness | `mypy --strict` and `ruff check .` pass with zero new issues on every changed file (`manifest.py`, `sync/namespace.py` — FR-016's narrow `resolve_manifest_version()` fallback, the four `expected-artifacts.yaml` files, changed test files). `dossier/indexer.py` is explicitly **not** in this list: FR-016 requires no change there — see FR-016's caller-side scope breakdown | Quality | High | Open |
| NFR-003 | Scoped test surface | Validation targets `tests/dossier/`, `tests/doctrine/missions/`, `tests/runtime/`, and `tests/charter/test_resolved_mission_type_context.py` (plus any files identified by FR-015) rather than the full ~17k-test suite, per the charter's Testing Requirements guidance for scoped changes | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Content + schema only | No changes to `src/runtime/next/runtime_bridge_cores.py`, `runtime_bridge_composition.py`, or `runtime_bridge_io.py` — guard-side bugs surfaced during reconciliation (e.g. FR-008's `implement`-step over-specification looking like the guard is the one that's "wrong") are filed as separate follow-up issues, never fixed in this mission | Technical | High | Open |
| C-002 | `manifest_version` stability | `manifest_version` remains `"1"` on all four manifests, per Decision 2 — bumping it would rekey `NamespaceRef`'s 5-field sync-namespace identity tuple for every already-synced artifact body of that mission type, a blast radius this repo cannot verify a migration path for in `spec-kitty-saas`; no change to `resolve_manifest_version()`'s **return value** for any input, and no change to `NamespaceRef`'s identity-tuple construction. (FR-016 does add one narrow line of exception-handling *code* inside `resolve_manifest_version()` — an `except pydantic.ValidationError: return "1"` guarding the new failure mode FR-016 itself introduces in `load_manifest()` — but that line is output-preserving by construction: the function returns `"1"` for a malformed manifest exactly as it already did for an absent one, so this constraint's substance, byte-identical sync-identity values, holds) | Technical | High | Open |
| C-003 | `artifact_key` vocabulary unification is out of scope | Claim 6 (the `artifact_key` vocabulary clash between manifests and `step.yaml`) is not addressed by this mission; see "Out of Scope" below | Technical | High | Open |
| C-004 | No new override-resolution wiring | This mission does not add an override tier to `_expected_artifacts_path()` / `get_expected_artifacts()`, even though the second-order finding above shows `.kittify/overrides/` is currently inert for this file type — that is a resolver behavior change, out of "content + schema only" scope | Technical | Medium | Open |

### Key Entities

- **`ExpectedArtifactSpec`** (`src/specify_cli/dossier/manifest.py:60-87`): a single expected
  artifact declaration — `artifact_key`, `artifact_class`, `path_pattern`, `blocking`. Gains
  `extra="forbid"` (FR-009).
- **`ExpectedArtifactManifest`** (`manifest.py:90-161`): the per-mission-type manifest container —
  `schema_version`, `mission_type`, `manifest_version`, `required_always`, `required_by_step`,
  `optional_always`. Gains `extra="forbid"` (FR-009); gains a fourth mission-type instance
  (`plan`, FR-010).
- **`ManifestRegistry`** (`manifest.py:164-310`): loader/cache/query surface over
  `ExpectedArtifactManifest`. Its `load_manifest()` method's exception handling changes under
  FR-016 (distinguishing `ValidationError` from genuine absence so a typo'd manifest fails loudly
  through the real production loading path, not just direct model construction — see User Story 3
  and Decision 3 in `tracer-design-decisions.md`); everything else about this class — caching,
  `get_required_artifacts()`, `validate_manifest()` — is unmodified. The bulk of the fix is
  otherwise in the YAML content and the Pydantic schema it validates against, not in this class.
- **The four `expected-artifacts.yaml` files** (`packs/built-in/missions/{research,documentation,
  software-dev,plan}/expected-artifacts.yaml`): the actual content being reconciled/authored.
- **`resolve_manifest_version()`** (`src/specify_cli/sync/namespace.py:90-101`): the sync-namespace
  version resolver, and the one real `load_manifest()` caller with no dedicated exception handling
  of its own. Under FR-016 it gains a narrow `except pydantic.ValidationError: return "1"` branch
  around its `ManifestRegistry.load_manifest()` call — preserving its own "always a string"
  docstring contract and Decision 2/C-002's sync-pipeline-untouched boundary, since its return
  value is unchanged for every input, including a malformed manifest.
- **`Indexer`** (`src/specify_cli/dossier/indexer.py`): explicitly considered and found to need
  **no change** under FR-016. Its four `load_manifest()` call sites (lines 123, 176, 355, 407) all
  run inside `index_feature()`'s call graph, and every real caller of `index_feature()`
  (`reconcile.py`, `rebaseline.py`, `sync/dossier_pipeline.py`'s `sync_feature_dossier()`) already
  wraps that call in its own dedicated, fail-closed `except Exception` — so a raised
  `ValidationError` already surfaces as a structured, visible error through existing code. Named
  here so a future reader does not have to re-derive this from the call graph.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every `required_by_step` key across the reconciled `research`, `documentation`, and
  `software-dev` manifests either matches a real branch in `runtime_bridge_cores.py`'s guard
  tables (verified by direct cross-read, key by key) or carries an inline YAML comment naming the
  specific non-filesystem-expressible check it corresponds to (count thresholds, WP-status,
  dependency frontmatter, occurrence-gate). Zero unexplained divergences remain — this is the
  acceptance bar the issue itself sets ("reconciled against observed artifacts, not merely
  schema-valid"), not merely "manifest parses."
- **SC-002**: `pytest tests/dossier/ tests/doctrine/missions/ tests/runtime/
  tests/charter/test_resolved_mission_type_context.py` (plus any files updated per FR-015) passes
  with zero new failures relative to the pre-change baseline on this branch.
- **SC-003**: `ExpectedArtifactSpec(...)` and `ExpectedArtifactManifest(...)` each raise
  `pydantic.ValidationError` when constructed with an unrecognized keyword argument (new
  regression tests, both green); all four shipped `expected-artifacts.yaml` files still load
  successfully through `ManifestRegistry.load_manifest()` after the hardening lands; a
  deliberately typo'd real YAML fixture loaded through `ManifestRegistry.load_manifest()` raises
  rather than silently returning `None` (FR-016, new regression test, green); the same typo'd
  fixture, routed through `reconcile.py`'s reconciliation flow and `rebaseline.py`'s backlog
  sweep, surfaces as a structured `ReconciliationResult(status=ERROR, error=...)` /
  `RebaselineOutcome(error="reindex_failed: ...")` respectively — no new exception handling added
  to `indexer.py` itself (AS5, new regression tests, both green); and
  `sync.namespace.resolve_manifest_version()` called directly against the same fixture still
  returns `"1"` via its new dedicated `except pydantic.ValidationError` fallback (AS6, new
  regression test, green).
- **SC-004**: `ManifestRegistry.load_manifest("plan")` returns a non-`None`
  `ExpectedArtifactManifest` whose `get_step_ids()` returns exactly `["goals", "research",
  "structure", "draft", "review", "done"]` (order matching `plan/mission.yaml`'s `states` list).
- **SC-005**: A new GitHub issue (distinct from #3388) exists on the tracker, naming the real
  defect surfaced during this investigation — `_check_cli_guards`'s hardcoded
  `mission_family="software-dev"` combined with `plan/mission.yaml`'s accidental `review`-step-id
  vocabulary collision (latent spurious-block risk), per FR-011/Decision 1; its URL is recorded in
  `tracer-design-decisions.md` and the mission's PR body.
- **SC-006**: `grep manifest_version packs/built-in/missions/*/expected-artifacts.yaml` shows
  `"1"` for all four files, both before this mission starts (three files) and after it lands
  (four files) — no value changes.
- **SC-007**: `mypy --strict` and `ruff check .` report zero new issues on every file this mission
  changes.

## Out of Scope

- **Claim 6 — `artifact_key` vocabulary unification.** The manifest's dotted `artifact_key`
  style (`"input.spec.main"`) and `step.yaml`'s `IDENTIFIER_PATTERN`-constrained bare-identifier
  `template.artifact_key` (`spec`) are confirmed structurally disjoint value spaces sharing one
  field name across two independently-versioned surfaces. Reconciling them is a contract change,
  not a content fix, and per the charter's "single canonical authority" governing principle
  ("prefer require-canonical + migration over no-canonical-field fallback branches... chase
  unification, not parity with a dead quirk"), it needs its own scoped mission with explicit
  versioning of whichever surface changes. A follow-up issue documenting this specific gap should
  be filed separately from this mission (distinct from FR-011's plan-guard-gap issue).
- **Fixing `runtime_bridge_cores.py` guard-side bugs.** Several of the 8 divergences (most
  visibly FR-008: `implement` requiring `analysis-report.md` that no guard checks) could
  plausibly be read as "the guard is wrong, not the manifest." This mission does not take that
  reading — per the resolved reconciliation direction, the manifest is corrected to match current
  guard behavior; guard-side bugs are filed as independent follow-up issues, never fixed here.
- **Wiring an override-resolution tier for `expected-artifacts.yaml`.** The second-order finding
  that `.kittify/overrides/` is currently inert for this file type (see Overview) is a real gap
  relative to how every sibling doctrine asset type resolves, but closing it is a resolver
  behavior change outside "content + schema only" scope (C-004). Named as a follow-up candidate
  only.
- **Turning the manifest into an actual completeness gate.** This mission makes the manifest
  *reliable enough* to eventually become one (per the issue's own framing); it does not wire any
  new gate, CLI check, or blocking behavior to the manifest's content.
- **A structural test that permanently prevents manifest/guard drift from recurring.** FR-012
  adds targeted regression tests for the current reconciliation; a general parity gate between
  manifest step keys and guard-table branches (so this class of divergence cannot silently
  reappear on a future guard change) is named as a natural follow-up in the Edge Cases section but
  is not required by this mission's acceptance bar.

## Non-Gate Consumer Notes

Concrete answer to "what does 'safe for the two live non-gate readers' mean here":

- **`sync.namespace.resolve_manifest_version()`**: safety comes entirely from Decision 2
  (C-002/FR-013). Because `manifest_version` stays `"1"` on every manifest this mission touches,
  this function's return value — and therefore `NamespaceRef`'s 5-field identity tuple used to
  key hosted-SaaS sync body uploads — is byte-identical before and after this mission for every
  mission type, including `plan`. `resolve_manifest_version("plan")` already returned `"1"`
  *before* this mission, via the function's own `None`-fallback branch (`if manifest is not None:
  return str(manifest.manifest_version); return "1"`, `src/specify_cli/sync/namespace.py:90-101`)
  — because `ManifestRegistry.load_manifest("plan")` returned `None` with no manifest present.
  After FR-010 lands, it continues to return `"1"`, now sourced from the real manifest's
  `manifest_version` field rather than the fallback. The sync-identity value for `plan` was, and
  remains, `"1"` throughout — this is a mechanism change (fallback → real field), not a value
  change, and certainly not a new value appearing where none existed before. FR-016 (User Story 3)
  adds one more fallback branch to this same function — `except pydantic.ValidationError: return
  "1"` — for the malformed-manifest case FR-016 itself introduces upstream in `load_manifest()`.
  This is a defensive addition, not a new risk: it fires only on a hand-editing mistake this
  mission is designed to catch (none of the four shipped manifests can trigger it after FR-009/
  FR-012's regression coverage), and its output is the same `"1"` the function already returns for
  the absence case. "Safety comes entirely from Decision 2" above remains true — this branch does
  not depend on Decision 2 to be safe, but it does not weaken it either.
- **`charter.mission_type_profiles._resolve_expected_artifacts_slot()`**: this reader bypasses
  the Pydantic schema entirely (`isinstance(parsed, Mapping)` only), so FR-009's schema hardening
  is invisible to it — it will accept a manifest dict with a typo'd key exactly as before, because
  it never invokes `ExpectedArtifactSpec`/`ExpectedArtifactManifest` at all. What it *is* sensitive
  to is content: it reads the raw YAML for whichever mission type is requested, including the new
  `plan` type (FR-010) for the first time. This reader feeds
  `ResolvedMissionType.expected_artifacts` (`src/charter/mission_type_profiles.py:404-409`, a
  `@cached_property` — **not** `MissionTypeProfile`, a separate `pydantic.BaseModel` with no such
  attribute). A real consumer exists: `tests/charter/test_resolved_mission_type_context.py:160-162`
  asserts on `bundle.expected_artifacts`'s presence, type, and `mission_type` key for
  `software-dev` — one of the three mission types whose manifest content this mission reconciles.
  This mission's software-dev content changes (FR-006/FR-007/FR-008) must still satisfy that
  test's three assertions; FR-015/NFR-003/SC-002 add `tests/charter/test_resolved_mission_type_
  context.py` to the validation surface specifically to confirm this. This mission keeps the
  reader's own shape identical (still returns whatever `isinstance(parsed, Mapping)` accepts)
  rather than changing its contract — only the underlying YAML content changes.

## Assumptions

- The 13-mission tally (7 research, 6 documentation) cited from the readiness investigation as
  evidence for the `blocking: true` contradiction (issue claim 2) reflects this checkout's
  `kitty-specs/` history at the time of writing and is cited as corroborating evidence for a
  problem statement already established by direct guard-table reconciliation (FR-001–FR-008);
  it is not itself re-verified artifact-by-artifact as part of this mission's acceptance bar.
- `plan/mission.yaml`'s `artifacts.optional: [research.md, data/]` block (a v0-compatibility
  field, separate from the `transitions[].conditions` state-machine gate) is read as informational
  context, not as a second authority for what FR-010's manifest should mark blocking — the
  transition conditions (`artifact_exists("research.md")` gating `research→structure`) are the
  operative check `plan/expected-artifacts.yaml` documents.

## Dependencies

- None outside this repository. No PR overlap found among the 19 open PRs at investigation time
  (PR #3378, "declarative transition gates," is thematically adjacent but touches no file in this
  mission's blast radius — worth a plan-time skim, not a blocker).
