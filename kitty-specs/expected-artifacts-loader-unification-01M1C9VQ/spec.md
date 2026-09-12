# Mission Specification: Unify expected-artifacts.yaml Loading + Close Org-Tier Fail-Loud Gap

**Mission Branch**: `fix/expected-artifacts-loader-unification`
**Created**: 2026-08-31
**Status**: Draft (post-spec squad folded)
**Input**: Unify all `expected-artifacts.yaml` loading on one relocated cached authority (#3770) and close the org-tier YAML-syntax fail-loud gap (#3412). Milestone 3.2.6, epic #3410 (silent-drop).

## Issue Matrix *(this mission closes two paired issues)*

Both issues live in the **same load seam** and share one intent from FR-016 —
*"absence and malformation are DISTINCT outcomes."* They are folded into one
mission deliberately: fixing #3412 without unifying the loaders would leave the
fail-loud semantics duplicated across four drifting copies, and unifying the
loaders (#3770) is the enabling move that lets the org-tier fix live in exactly
one place.

| Issue | Slice | One-line |
|-------|-------|----------|
| #3770 | Structural (loader unification) | Retire the mirror loaders; route every `expected-artifacts.yaml` load through ONE relocated cached authority. |
| #3412 | Behavioral (org-tier fail-loud) | A YAML-syntax-broken *org* manifest must fail loud and distinct from "not found", not silently degrade to a green guard. |
| #3410 | Epic parent | Charter/doctrine silent-drop — loading must fail loud, never fake-green. This mission is the runtime/manifest-resolution slice. |

## Confirmed Failure Mechanism *(anchors the behavioral requirements)*

The #3412 launder is live-reachable in production (`repo_root` is threaded to the
composed guard at `runtime_bridge_composition.py:637-638`):

> corrupt *org* custom-family manifest → `org_expected_artifacts._read_yaml_mapping`
> swallows `YAMLError`→`None` (`org_expected_artifacts.py:109-116`) →
> `_resolve_org_manifest_mapping`→`None` (`runtime_bridge_io.py:983`) →
> `_expected_artifacts_manifest_resolves`→`False` (`:998-1004`) →
> `blocking_artifact_names=None` (`:1158`) → `evaluate_guards_strict` raises
> `UnregisteredMissionFamilyError` (`runtime_bridge_cores.py:724-725`) → **caught at
> `runtime_bridge_composition.py:504` → `return []`** (silent green).

A fix at the swallow alone is insufficient: the raised signal must be a **distinct
type** the `:504` handler does not treat as "unregistered family", and that seam
must be closed by construction.

## User Scenarios & Testing *(mandatory)*

The actors are **operators** who author org-pack manifests, and the **agents and
maintainers** who run and maintain missions. "Value" is a system that tells the
truth: a broken manifest is reported as broken, and one loading rule is defined
in exactly one place so a fix cannot drift.

### User Story 1 - A corrupt org manifest fails loud, distinct from absent (Priority: P1)

An operator hand-edits their org pack's `expected-artifacts.yaml` for a custom
mission family and introduces a YAML-syntax error (bad indentation, an unclosed
structure, a duplicate key). They run a mission that gathers artifact presence.

**Why this priority**: This is the FR-016 gap the epic exists to close. Today the
broken manifest is silently laundered into a green guard for a custom family — the
operator's misconfiguration is invisible and the mission proceeds on a false
all-clear.

**Independent Test**: Point a custom mission family at an org root whose
`expected-artifacts.yaml` contains a real YAML-syntax error; run the composed
guard path; assert it surfaces `MalformedManifestError` naming the offending file
and parse failure — and that the SAME input with the file *absent* still degrades
gracefully.

**Acceptance Scenarios**:

1. **[RED-on-main]** **Given** a custom mission family whose only
   `expected-artifacts.yaml` is an org-tier file with a YAML-syntax error,
   **When** the runtime resolves that family's manifest, **Then** it raises
   `MalformedManifestError` naming the file and the parse failure, and does
   **not** return `None`/empty or a green guard.
2. **[characterization]** **Given** the same custom family with **no**
   `expected-artifacts.yaml` on any tier, **When** the runtime resolves the
   manifest, **Then** it degrades gracefully (absence semantics) — proving
   corrupt and absent stay distinct.
3. **[characterization]** **Given** a YAML-syntax-broken **built-in** manifest,
   **When** it is loaded, **Then** it fails loud via the **same**
   `MalformedManifestError` class the org tier now uses (symmetry; already shipped
   for built-in in `1763bf2ae3`, verified not regressed).
4. **[RED-on-main]** **Given** a corrupt org manifest surfaced through the
   composed-action guard path, **When** the guard is evaluated, **Then** the
   error is **not** caught and degraded to an empty allowlist by the
   unregistered-family handler (`runtime_bridge_composition.py:504`) — the
   malformed signal is a distinct type that seam does not mistake for
   "unregistered family".
5. **[RED-on-main]** **Given** an org manifest that is present but a non-mapping
   (a scalar/sequence where a mapping is required), **When** resolved, **Then**
   it fails loud (present-but-invalid), distinct from absent.

### User Story 2 - One canonical loader, no drift (Priority: P1)

A maintainer needs to change how `expected-artifacts.yaml` is resolved. They
should change it in exactly one place and have every caller pick it up.

**Why this priority**: Four parallel copies of the org-first / built-in-fallback /
`model_validate` / wrap-`ValidationError`→`ManifestSchemaError` logic have already
drifted once (inside #3729). Each drift is a latent silent-drop bug.

**Independent Test**: After consolidation, grep proves there is exactly one
implementation of the load-precedence-and-validate logic; every prior mirror
delegates to it or is deleted; the relocated authority is reachable from both
runtime callers and charter-tier callers without violating C-001; behavior
(including the cache) is byte-compatible for all pre-existing inputs.

**Acceptance Scenarios** *(all characterization — green-stays-green)*:

1. **Given** the four historical model-load sites (canonical cached loader, the
   resolver mirror, the runtime-bridge mirror, and the charter-tier raw-mapping
   loader), **When** consolidation is complete, **Then** exactly one applies the
   org→built-in precedence + schema validation, and the others delegate to it (or
   are removed).
2. **Given** the charter-tier consumer that previously returned a **raw,
   unvalidated** mapping, **When** it is re-pointed at the canonical authority,
   **Then** it gains the same schema validation and fail-loud semantics as every
   other tier — while an **absent** manifest still returns `None` there (the
   guard-table short-circuit input is unchanged).
3. **Given** a caller that imported `ManifestRegistry`, `load_manifest`, or
   `ManifestSchemaError` from `specify_cli/dossier/manifest`, **When** it runs
   after relocation, **Then** it still works via the deprecation-shim re-export
   (no consumer breakage).
4. **Given** the same mission types and inputs as before, **When** manifests are
   loaded repeatedly, **Then** results and cache behavior (`(mission_type,
   org_roots)` key, cross-root non-shadowing, declaration order) are identical to
   pre-mission behavior.

### User Story 3 - The defect class cannot silently return (Priority: P2)

A future contributor reaches for a bare `ExpectedArtifactManifest.model_validate(...)`
(or `ExpectedArtifactManifest(**yaml.load(...))`) outside the canonical helper, or
broadens the `:504` guard handler to swallow malformed manifests.

**Why this priority**: DIRECTIVE_043 (close-defect-class-by-construction). Once the
loaders are unified and the launder seam closed, non-vacuous gates keep them so —
otherwise the mirrors regrow or the launder reopens.

**Independent Test**: (a) An arch-gate forbids bare `ExpectedArtifactManifest.model_validate(`
**and** bare `ExpectedArtifactManifest(` construction outside the model's own
tests, fails on an injected negative case, exempts direct-construction model
tests, and points its allowlist at the relocated charter helper. (b) A positive
regression asserts a malformed org manifest through the composed guard propagates
and is never degraded to `[]`.

**Acceptance Scenarios**:

1. **Given** the arch-gate, **When** a new bare `model_validate(`/bare
   `ExpectedArtifactManifest(` call is added to production code outside the
   canonical helper, **Then** the gate fails.
2. **Given** the arch-gate, **When** the model's direct-construction unit tests
   run, **Then** they are exempt and the gate passes.
3. **Given** a behavior-preserving refactor of the canonical helper, **When** the
   gate runs, **Then** it still passes (refactor-stable, no false failure).
4. **Given** the `:504` handler pinned to `UnregisteredMissionFamilyError` only,
   **When** a maintainer broadens it to also catch a malformed-manifest error,
   **Then** the positive launder regression fails.

### Edge Cases

- **Corrupt org override, registered built-in family (e.g. `software-dev`).** The
  guard-table short-circuits **before** `blocking_artifact_names` is read
  (`cores.py:721-723`), so the corrupt override does not reach the guard decision
  — yet C-006 makes manifest resolution hard-raise at gather time. Decision: keep
  fail-loud (the operator authored the override expecting effect); this now
  hard-blocks the whole family on that file. Covered by an explicit acceptance
  scenario + a doc note (see FR-007 / C-006).
- **Present-but-unreadable manifest (`OSError`/`UnicodeDecodeError`) on a file that
  exists on disk.** NOT current built-in behavior — `repository.py:413-414` still
  swallows both to `None`; the shipped fix widened only `YAMLError`. Honoring
  cross-tier symmetry requires re-touching the built-in reader too — costed as
  FR-012, not hidden here.
- **Multiple org roots, last-existing-match precedence.** A broken file that would
  be the *effective* override fails loud; an earlier root's good match is not
  silently substituted for a later broken one.
- **Genuinely absent manifest** (no file on any tier): unchanged graceful
  degradation — the ONLY case that legitimately returns absence.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Canonical cached loader in charter | As a maintainer, I want ONE cached loader **function** — living in `charter` so both runtime and charter-tier callers reach it — owning org→built-in precedence, `model_validate`, and error-wrapping, carrying its own `_cache` keyed `(mission_type, org_roots)`. | High | Open |
| FR-002 | Deprecation shim at the old location | As a consumer, I want `specify_cli/dossier/manifest` to re-export `ManifestRegistry`, `load_manifest`, **and** `ManifestSchemaError` (plus `MalformedManifestError`), so relocation breaks no importer (8+ sites). | High | Open |
| FR-003 | ManifestRegistry stays as thin delegate | As a maintainer, I want `ManifestRegistry` to remain in `specify_cli` (it is a stateful class with sibling completeness methods — `get_required/blocking/optional_artifacts`, `validate_manifest`, `clear_cache` — instantiated 4×) with `ManifestRegistry.load_manifest` becoming a thin delegate to the charter authority; the completeness methods do NOT move. | High | Open |
| FR-004 | Retire the resolver mirror | As a maintainer, I want `resolver._load_expected_artifact_manifest` to delegate to the canonical authority, so its uncached duplicate is gone. | High | Open |
| FR-005 | Retire the runtime-bridge mirror | As a maintainer, I want `runtime_bridge_io._presence_filenames_for` to obtain its manifest from the canonical authority and keep only its projection step, where an **absent** manifest still projects to `frozenset()` (not `None`) and a malformed one propagates **before** the projection — no `blocking_artifact_names` tri-state mutation. | High | Open |
| FR-006 | Re-point the charter-tier loader | As a maintainer, I want `mission_type_profiles._resolve_expected_artifacts_slot` to obtain a validated manifest from the canonical authority instead of a raw mapping, gaining schema validation; **absence still returns `None`** (guard-table short-circuit input unchanged) and malformation **raises before** any guard-table/None-vs-present decision. | High | Open |
| FR-007 | Org-tier malformation fails loud (MalformedManifestError) | As an operator, I want a YAML-syntax-broken (or non-mapping) org `expected-artifacts.yaml` to raise the **charter-resident `MalformedManifestError`** naming the file/origin and failure — never silently dropped to `None`. | High | Open |
| FR-008 | Symmetric sibling-error model across tiers | As an operator, I want present-but-unparseable manifests (org OR built-in) to surface via the SAME `MalformedManifestError`, and schema/`extra=forbid` violations via `ManifestSchemaError`; the two are siblings, both fail-loud, both distinct from `None`="not found". FR-008 does NOT re-point malformation onto `ManifestSchemaError` (whose message says "schema-invalid" and which lives in specify_cli). | High | Open |
| FR-009 | No re-laundering at the guard seam | As an operator, I want the malformed-manifest error carried as a distinct type the composed-action guard's unregistered-family handler (`composition.py:504`) does NOT catch-and-green, so a broken custom-family manifest can never be laundered into an empty allowlist. | High | Open |
| FR-010 | Durability gate on the launder seam | As a maintainer, I want `composition.py:504`'s `except` pinned to `UnregisteredMissionFamilyError` **only**, plus a positive regression asserting a malformed org manifest through the composed guard propagates (never `[]`), so the #3412 launder is closed by construction (FR-010's sibling arch-gate for `model_validate` does not cover this seam). | High | Open |
| FR-011 | Arch-gate against bare construction | As a maintainer, I want a non-vacuous arch-gate forbidding bare `ExpectedArtifactManifest.model_validate(` AND bare `ExpectedArtifactManifest(` outside the canonical helper (model direct-construction tests exempted; allowlist points at the relocated charter helper), so mirrors cannot regrow. | High | Open |
| FR-012 | Present-but-unreadable fails loud, both tiers | As an operator, I want `OSError`/`UnicodeDecodeError` on a manifest that **exists on disk** to fail loud on BOTH tiers (widening the built-in reader `repository.py:413-414`, which today swallows them to `None`), so unreadable-present is distinct from absent symmetrically. | Medium | Open |
| FR-013 | Retire the orphan direct-read loader | As a maintainer, I want `ExpectedArtifactManifest.from_yaml_file` **deleted** (not merely routed — it constructs via `cls(**data)`, which the model_validate gate cannot police) and its 3 tests migrated to the canonical loader. | Medium | Open |
| FR-014 | Stale docstring / comment reconciliation | As a maintainer, I want the `load_manifest` docstring (and sibling comments) that still describe #3412 as an open built-in gap corrected to the shipped semantics. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Byte-compatible resolution | For every pre-existing (mission_type, tier, input) combination, the consolidated loader returns a manifest/None identical to today's canonical `load_manifest`; characterized by `test_configured_artifact_name` / bridge-parity suites passing unchanged. | Reliability | High | Open |
| NFR-002 | Cache semantics preserved | The relocated authority's `_cache` preserves the `(mission_type, org_roots)` key and its cross-repo-root non-shadowing + declaration-order guarantees; `TestManifestRegistryOrgTier` cache tests pass (via the delegate). | Reliability | High | Open |
| NFR-003 | Zero new lint/type debt | New and moved code passes `ruff` + `mypy` with zero new issues/suppressions; every touched function stays ≤ 15 complexity. | Maintainability | High | Open |
| NFR-004 | No extra happy-path I/O | The malformation checks reuse the single existing file read; no new I/O per load beyond what the tier already performs. | Performance | Medium | Open |
| NFR-005 | Operator-actionable error text | `MalformedManifestError`'s string form names the source file (or descriptive org-tier origin) and the underlying parse failure without requiring exception-note inspection. | Usability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Charter must not import specify_cli | The relocated loader AND every error type it raises (`MalformedManifestError` already in charter; `ManifestSchemaError` must move to charter with a specify_cli shim re-export) live so charter-tier consumers reach them WITHOUT charter importing `specify_cli`. Enforced by boundary arch-gates. | Technical | High | Open |
| C-002 | Do not touch the guard tri-state contract | The `blocking_artifact_names` None-vs-`frozenset()` tri-state (#3729) is out of scope; malformation fails at gather time (`composition.py:486`, outside the `:502-504` try) **before** the None-vs-frozenset decision — no tri-state mutation. Confirmed non-contradictory with FR-009/FR-010. | Technical | High | Open |
| C-003 | Do not touch the guard-table short-circuit | The built-in-family guard-table short-circuit (`cores.py:721-723`) is owned by #3386/#3397/#3407; FR-006 keeps its input (absence→`None`) unchanged and stays off the short-circuit itself. | Technical | High | Open |
| C-004 | Red-first, real broken YAML + honest tagging | The #3412 fix lands issue-pinned regressions that construct ACTUAL YAML-syntax errors (not typo'd keys) and are RED on current `upstream/main` through the pre-existing entry point before the fix. Only genuinely-red-on-main scenarios carry `@regression`; green-stays-green characterizations (US1-AC2/AC3, all US2) are tagged characterization — a green `@regression` test is a landing defect. | Process | High | Open |
| C-005 | ADR for the relocation | Moving the canonical loader + `ManifestSchemaError` across the charter↔specify_cli boundary is recorded in `docs/adr/3.x/` with the seam rationale and the deprecation-shim contract. | Process | High | Open |
| C-006 | Corrupt org override fails loud even with fallback | A present-but-corrupt org file fails loud rather than silently masking behind a good built-in file (operator authored it expecting effect); ONLY genuine absence falls back silently. For registered built-in families this hard-blocks the family — documented + acceptance-covered. | Technical | High | Open |

### Key Entities

- **ExpectedArtifactManifest**: The validated manifest model. The single type every load path must produce via the one canonical helper.
- **Canonical loader authority**: The one cached charter-resident function owning org→built-in precedence + `model_validate` + error-wrapping; `ManifestRegistry.load_manifest` (specify_cli) delegates to it; `specify_cli/dossier/manifest` re-exports it via a shim.
- **MalformedManifestError** (charter, `repository.py:38`): the fail-loud channel for present-but-unparseable manifests — both tiers, and the distinct type the `:504` guard seam must not catch.
- **ManifestSchemaError** (moves to charter + shim): the fail-loud channel for schema/`extra=forbid` violations — sibling of `MalformedManifestError`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Exactly **one** production implementation of the org→built-in
  precedence + `model_validate` + error-wrap logic remains; the other three
  model-load reimplementations and the orphan `from_yaml_file` are deleted or
  delegate (verified by grep + call-graph).
- **SC-002**: A YAML-syntax-broken **org** manifest for a custom family produces
  `MalformedManifestError` through the composed guard path (0 silent
  degradations), while an **absent** manifest still degrades gracefully — proven
  by a regression RED on `upstream/main` before the fix and GREEN after.
- **SC-003**: 100% of pre-existing manifest-load characterization tests
  (`test_configured_artifact_name`, bridge-parity, `TestManifestRegistryOrgTier`
  cache) pass unchanged (no functional/cache regression).
- **SC-004**: The `:504` launder seam is pinned to `UnregisteredMissionFamilyError`
  only and the positive launder regression fails if it is broadened.
- **SC-005**: The arch-gate forbidding bare `model_validate(`/bare
  `ExpectedArtifactManifest(` outside the helper fails on an injected negative
  case and passes on the model's direct-construction tests (non-vacuous).
- **SC-006**: `ruff` + `mypy` report zero new issues on all touched/moved files.

## Assumptions

- The built-in-tier **YAML-syntax** fail-loud (`MalformedManifestError`,
  `repository.py:411-412`) is shipped on `upstream/main` (`1763bf2ae3`). This
  mission extends the SAME class to the org tier (FR-007), widens the
  present-but-unreadable case on BOTH tiers (FR-012), and unifies the loaders.
- The operator chose the **relocate-into-charter** strategy (decision
  `01M1CBARZBBWVGWBTWRMHPP661`).
- The final PR targets **upstream** as a DRAFT; the operator merges.

## Non-Goals

- Changing the `blocking_artifact_names` None-vs-`frozenset()` tri-state (#3729).
- Touching the built-in-family guard-table short-circuit (#3386/#3397/#3407).
- Changing `get_mission_config` (mission.yaml) YAML handling.
- Consolidating the org-root resolver wrappers — they already delegate to the
  single `charter.drg.resolve_existing_org_roots` primitive (#3525); no dedup
  needed.
- Broadening the epic's other silent-drop slices beyond the manifest-resolution
  seam.
