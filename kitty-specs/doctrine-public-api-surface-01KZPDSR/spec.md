# Mission Specification: Doctrine Public API Surface

**Mission Branch**: `feat/doctrine-public-api-surface`
**Created**: 2026-08-10
**Status**: Draft
**Input**: User description: "Doctrine public API surface (#3179): define a curated public surface for the doctrine module, grow the charter facades to front it, migrate the ~29 lazy-import runtime files onto charter facades, fix the raw-DoctrineService sole-door bypasses, and land a lazy-import architectural ratchet — the unblocked precondition to the #3101 kernel→doctrine→charter wheel cutover."

> Scope grounding: this spec is extracted from the settled scoping brief at
> [`docs/plans/doctrine/3179-public-api-surface-scoping.md`](../../docs/plans/doctrine/3179-public-api-surface-scoping.md)
> and the pre-spec research at
> [`docs/plans/doctrine/next-slice-wheel-mission-types-public-api-research.md`](../../docs/plans/doctrine/next-slice-wheel-mission-types-public-api-research.md).
> Governing ADR: [`2026-08-02-1-charter-wheel-assessment`](../../docs/adr/3.x/2026-08-02-1-charter-wheel-assessment.md).
> Hardened after a post-spec adversarial squad (2026-08-10): the INTERNAL-vs-migrate
> reconciliation (FR-002/FR-007), the exempt-subpackage re-export laundering closure
> (FR-004/C-005), the regression-delta gate (NFR-001), and the FR-010 isolation/governance
> all trace to convergent squad findings.

> **Census note (anti-drift):** the counts below (26 reached paths, 29 lazy-import files,
> 5 raw-service sites, 6 true gaps, 45 CRITICAL Sonar smells) are the snapshot from
> `upstream/main @ 4ce2e7097` / SonarCloud project `Priivacy-ai_spec-kitty` as analyzed
> 2026-08-10. They are **expected magnitudes**, not frozen acceptance literals. Plan MUST
> re-run the census at plan-start (an AST sweep for direct `doctrine.*` reach-through and a
> fresh Sonar pull); acceptance is defined against that re-run, not these numbers.

## User Scenarios & Testing *(mandatory)*

Actors are internal: the **doctrine/charter maintainer** who must eventually ship
`src/doctrine/` as an installable wheel, and the **runtime consumer** code in
`src/specify_cli/` that depends on doctrine behavior. "Value" here is a credible,
enforced module boundary that unblocks the #3101 wheel cutover.

### User Story 1 - One curated, enumerable doctrine public surface (Priority: P1)

The maintainer can look in exactly one place — `doctrine/api.py` — and see the complete
set of doctrine symbols other layers are allowed to depend on, with everything else clearly
internal. The dormant `spec-kitty-doctrine` wheel then has a real contract to export.

**Why this priority**: Without a declared surface there is nothing to stabilize, version,
or export — every downstream slice depends on this classification existing.

**Independent Test**: Import `doctrine/api.py` and assert every symbol downstream
legitimately consumes is reachable through it; assert each of the 6 enumerated "true gaps"
(US1 note below) is now either PUBLIC-with-a-door or explicitly INTERNAL-with-a-recorded-disposition.

**Acceptance Scenarios**:

1. **Given** the census of doctrine paths reached from runtime (re-run at plan-start), **When** the mission completes, **Then** each is classified PUBLIC, FACADE-ONLY, or INTERNAL, and **no path reached by non-exempt runtime is left without either a charter door or an explicitly enumerated management-surface/baseline disposition** (see FR-002/FR-007).
2. **Given** the public surface `doctrine/api.py`, **When** the wheel-closure test runs, **Then** it pins the real public surface (the enumerated `__all__`), not merely the manifest shape.
3. **Given** `doctrine/api.py` declaring `__all__`, **When** `tests/architectural/test_no_dead_symbols.py` runs, **Then** every public symbol either has a charter-facade caller or is routed through that gate's documented allowlist with a tracker reference (FR-001 addresses this interaction, not leaves it to fail).

> **The 6 "true gaps"** (paths even charter has no door for today): `model_task_routing.*`
> (`evaluator`/`loader`/`RoutingRecommendation`), `assets.*` (`AssetRepository` +
> `AssetManifest`), `missions.repository.MissionsRootNotFound`, `drg.override_policy`,
> `drg.migration.hand_authored_overlay.write_reference_graph_with_overlay`, and the raw
> `doctrine.service.DoctrineService` construction bypass. Gap #6 is resolved by
> construction-routing (US4), **not** by an identity re-export.

---

### User Story 2 - Every runtime doctrine access goes through a sanctioned door (Priority: P1)

Runtime reaches doctrine **only** through a `charter.*` facade — never a direct `doctrine.*`
import (module-level or lazy) and never by consuming a first-party module that re-exports a
doctrine object. The charter facades are grown to front the PUBLIC/FACADE-ONLY paths.

**Why this priority**: The enforced layering is `runtime → charter → doctrine`. Direct
reach-through — and its subtler cousin, laundering a doctrine object through a first-party
re-export — is exactly what blocks a credible wheel boundary.

**Independent Test**: For each new/widened facade, assert `facade.SYMBOL is doctrine.SYMBOL`
and `SYMBOL in facade.__all__`; assert no non-exempt runtime module imports a doctrine object
either directly or via a first-party re-export conduit.

**Acceptance Scenarios**:

1. **Given** a doctrine symbol runtime needs (e.g. `RoutingRecommendation`, `MissionTemplateRepository`, `AssetRepository`, `GlossaryPack`, `apply_spdd_blocks_for_project`), **When** runtime imports it, **Then** it comes from a `charter.*` facade that re-exports the **specific symbol** (not a whole submodule) by object identity.
2. **Given** the widened `charter.drg` / `charter.mission_steps` and the new `charter.missions` / `charter.model_routing` / `charter.assets` (and doors for `glossary_packs` / `spdd_reasons` / `pack_paths` — see FR-003), **When** the facade-identity test runs, **Then** all re-exports pass `facade.X is doctrine.X` and are listed in `__all__`.
3. **Given** the census of lazy-import runtime files, **When** migration completes, **Then** none imports `doctrine.*` directly (module-level or lazy) and none consumes a doctrine object via a first-party re-export (e.g. `from specify_cli.doctrine.config import resolve_org_roots`).

---

### User Story 3 - The boundary cannot silently regrow (Priority: P1)

An automated architectural guard fails CI the moment any code reintroduces a direct
`doctrine.*` import from runtime — including in-function/lazy imports the current ratchet
cannot see — and the first-party re-export laundering path is closed too.

**Why this priority**: A migrated-but-unguarded surface regrows. The existing ratchet's own
docstring names this "follow-up ratchet" as the missing piece; this FR is also the runtime→doctrine
half of the function-local-import blind spot tracked as **#2986**.

**Independent Test**: Add a throwaway lazy `from doctrine.x import y` inside a runtime
function → the architectural suite goes red naming the file; remove it → green. Add a
first-party re-export of a doctrine object consumed by non-exempt runtime → red.

**Acceptance Scenarios**:

1. **Given** the new lazy-import ratchet, **When** a new direct `doctrine.*` import is added to a runtime function body, **Then** the architectural test fails naming the offending file.
2. **Given** a `TYPE_CHECKING`-guarded doctrine import, **When** the ratchet runs, **Then** it is not flagged (type-only imports are out of scope).
3. **Given** a file legitimately blocked on a not-yet-built facade, **When** it sits on the shrinking baseline allowlist and its facade later lands, **Then** the stale-entry check forces its removal.
4. **Given** the exempt/management surface re-exporting a doctrine object, **When** a non-exempt runtime module consumes that re-export, **Then** the guard treats it as a boundary violation (closing the laundering conduit).

---

### User Story 4 - The DoctrineService sole door is not bypassed (Priority: P2)

Every construction of the doctrine service flows through the activation-aware charter sole
door, so activation filtering is never silently skipped. The raw-construction sites are
routed through the sanctioned builder.

**Why this priority**: A raw-service bypass is a governance leak (unfiltered activation), not
just style — but it is a bounded, well-identified fix riding on the same work.

**Independent Test**: The sole-door architectural test reports zero unwrapped raw
`doctrine.service.DoctrineService` constructions outside the charter door.

**Acceptance Scenarios**:

1. **Given** the raw-construction sites (census: 5, e.g. `_doctrine_asset.py:93`, `_doctrine_collect.py:209/314/468/920`), **When** the mission completes, **Then** each obtains its service via `charter.doctrine_service_builder.build_activation_aware_doctrine_service` (or the `charter.resolver.DoctrineService` wrapper). This is construction-routing, **not** an identity re-export — `charter.resolver.DoctrineService` is a deliberate activation-aware wrapper and must never be added to the facade identity table.

---

### User Story 5 - Doctrine maintainability debt cleared (Priority: P3, separately sequenced)

The doctrine tree's open SonarCloud debt is cleared: duplicate DRG-URN literals hoisted to
constants, the malformed suppression fixed, and the high-complexity functions reduced to the
charter's ≤15 ceiling — **without changing doctrine's observable behavior**.

**Why this priority / provenance**: The campsite items (FR-009 duplicate literals, FR-011
suppression) sit on files this mission already classifies/touches, so they ride along. The
**complexity refactor (FR-010) is a conscious in-scope override of the scoping brief**, which
marked it "out-of-scope … do NOT blur it into this boundary mission" — the operator elected
on 2026-08-10 to include it. Because it is the mission's highest-risk, most-fakeable slice and
does **not** share a file-touch with the boundary work, it is isolated as the **last-sequenced,
independently-revertable work package** and method-governed by the disciplined-refactoring /
semantic-compression doctrine (see C-007-mission).

**Independent Test**: SonarCloud shows zero open CRITICAL code smells in `src/doctrine/`;
`ruff`/Sonar report every doctrine function at cognitive complexity ≤ 15; and the DRG
`regenerate-graph` canonical output is byte-identical to a golden snapshot captured on the
base commit **before** the refactor.

**Acceptance Scenarios**:

1. **Given** `src/doctrine/drg/migration/hand_authored_overlay.py`'s duplicate DRG-URN literals, **When** hoisted to named constants, **Then** `S1192` on the file is zero **and** the round-trip catches any accidental over-DRY (two coincidentally-equal-but-independent URNs collapsed into one constant would change edge endpoints and fail byte-identity).
2. **Given** `src/doctrine/drg/migration/extractor.py:545` (cognitive complexity 183) and the 7 other `S3776` breaches, **When** refactored, **Then** every affected function is ≤ 15, **the regenerate-graph output is byte-identical to the pre-captured golden snapshot**, and every extracted helper carries its own focused test (no complexity-shuffling into untested no-op helpers).
3. **Given** the malformed suppression at `src/doctrine/artifact_kinds.py:118` (`S7632`), **When** fixed, **Then** `S7632` is resolved with no behavior change.

### Edge Cases

- **Non-exempt consumers of "INTERNAL" paths (the reconciliation).** Several paths the scoping brief called INTERNAL are, in fact, imported by **non-exempt** runtime today: `pack_paths.built_in_dir/built_in_root` (`tool_surface/bundles/claude.py:434`, `cli/commands/doctrine.py:205`), `drg.override_policy` (`_doctrine_collect.py:726`), `drg.migration.hand_authored_overlay` (`cli/commands/doctrine.py:249`), `missions.mission_step_repository` + `missions.step_projection` (`cli/commands/mission_type.py:1508/1511`). A pure-INTERNAL classification with "no door, no exemption" is unsatisfiable for these — there is no legal target to migrate them to, and a permanent baseline resident violates the stale-entry check. FR-002/FR-007 resolve each by exactly one of: (a) a narrow charter door (→ FACADE-ONLY), (b) explicit enumeration of the consuming module into the management-surface carve-out with a rationale, or (c) a ticketed, documented permanent baseline exception.
- **First-party re-export laundering.** `src/specify_cli/doctrine/config.py` re-exports doctrine objects (`resolve_org_roots`, `load_pack_registry`, …) that ~10 non-exempt runtime sites consume as `from specify_cli.doctrine.config import …`. Neither string-ratchet sees this (it matches `doctrine.*`, not `specify_cli.doctrine.*`). C-005/FR-004 close it: the exemption is **inbound-only**.
- **A genuinely load-bearing lazy import** (circular-import avoidance, optional dependency, `try/except` graceful degradation): keep the lazy shape but retarget it to `charter.*` — the ratchet forbids `doctrine.*`, not laziness.
- **Facade-blocked files** (e.g. `invocation/executor.py` needs a symbol-level `charter.model_routing` before it migrates): remain on the shrinking baseline until their door lands; hoisting to module level is forbidden (trips the sibling module-level ratchet).
- **Whole-module vs symbol facades.** Some consumers use doctrine submodules as modules (e.g. `invocation/executor.py:75-88` calls `loader.load()` / `evaluator.evaluate()`). Re-exporting a whole module passes identity but defeats curation — FR-003 requires **symbol-level** re-exports and migrating those call sites to symbol imports.
- **The `import doctrine` bare/introspection form** (`tool_surface/bundles/codex.py:267/299` reads package metadata via `importlib`, not a symbol): FR-006 must state whether bare `import doctrine` for metadata is in or out of scope, and handle aliased imports.

## Requirements *(mandatory)*

> **Sequencing (binding for /plan):** FR-003 (grow doors) must precede FR-004 (migrate) for
> every facade-blocked file. FR-010 is last and independently revertable. The FR table's
> "Depends on" column encodes this so `finalize-tasks` derives correct lane order rather than
> inferring it from prose.

### Functional Requirements

| ID | Title | User Story | Priority | Depends on | Status |
|----|-------|------------|----------|-----------|--------|
| FR-001 | Curated doctrine public surface (`doctrine/api.py`) | As a maintainer, I want one enumerable public surface — `doctrine/api.py` with an explicit `__all__` — as the single manifest the wheel exports, and I want its interaction with `test_no_dead_symbols.py` resolved (facade caller or documented allowlist entry per public symbol). | High | — | Open |
| FR-002 | Reclassify + disposition every reached path | As a maintainer, I want each reached doctrine path (census re-run at plan-start) classified PUBLIC / FACADE-ONLY / INTERNAL, with an explicit disposition for every path a non-exempt consumer touches so none is left unsatisfiable. Explicitly disposition `glossary_packs`, `spdd_reasons`, `pack_paths`, `drg.override_policy`, `missions.mission_step_repository`, `missions.step_projection`. | High | — | Open |
| FR-003 | Grow charter facades (symbol-level) | As a consumer, I want the charter facades widened (`charter.drg`, `charter.mission_steps`) and new facades added (`charter.missions`, `charter.model_routing`, `charter.assets`, plus doors for `glossary_packs`, `spdd_reasons`, and the FACADE-ONLY `pack_paths` symbols) — all **symbol-level** object-identity re-exports listed in `__all__` — so every PUBLIC/FACADE-ONLY doctrine symbol has a sanctioned door. | High | FR-002 | Open |
| FR-004 | Migrate runtime off direct + laundered imports | As a maintainer, I want all lazy-import runtime files migrated to consume doctrine only via `charter.*` facades — zero direct `doctrine.*` imports (module-level or lazy) and zero first-party re-export laundering — outside the enumerated management surface. | High | FR-003 | Open |
| FR-005 | Fix DoctrineService sole-door bypasses | As a maintainer, I want the raw `doctrine.service.DoctrineService` construction sites routed through the charter sole door (construction-routing, not re-export) so activation filtering is never skipped. | High | FR-003 | Open |
| FR-006 | Lazy-import architectural ratchet | As a maintainer, I want a sibling architectural guard walking full ASTs — matching **absolute** `doctrine`/`doctrine.*` with `ImportFrom.level == 0`, excluding `TYPE_CHECKING` and the enumerated management surface, with an only-shrink baseline — that fails CI on any new/relocated direct `doctrine.*` import, plus a rule closing first-party re-export laundering. Closes the runtime→doctrine half of #2986. FR-006 must state the disposition of bare `import doctrine` (metadata) and aliased imports. | High | FR-002 | Open |
| FR-007 | Keep truly-internal paths hidden, reconciled | As a maintainer, I want paths with **no** non-exempt consumer kept unexposed (no facade, not in `doctrine/api.py __all__`), with a **negative** acceptance test asserting their absence from both the public surface and every facade; paths with a non-exempt consumer are dispositioned under FR-002, not left as pure INTERNAL. | Medium | FR-002 | Open |
| FR-008 | Wheel-closure pins real surface | As a maintainer, I want `test_doctrine_wheel_closure.py` to pin the actual `doctrine/api.py` public surface (not just the manifest shape) so the eventual cutover exports a real contract. | Medium | FR-001 | Open |
| FR-009 | Clear duplicate-literal debt (campsite) | As a maintainer, I want the duplicate DRG-URN literals in `src/doctrine/drg/migration/hand_authored_overlay.py` hoisted to named constants so `S1192` on the file reaches zero, guarded by the byte-identical round-trip against over-DRY. | Medium | — | Open |
| FR-010 | Reduce doctrine complexity (isolated, governed) | As a maintainer, I want `src/doctrine/drg/migration/extractor.py:545` (cc 183) and the 7 other `S3776` breaches refactored to ≤ 15 **without changing regenerate-graph output** — as the last-sequenced, independently-revertable WP, governed by the disciplined-refactoring/semantic-compression doctrine, with a golden DRG snapshot captured on the base commit and per-helper tests. | Medium | FR-001..FR-009 | Open |
| FR-011 | Fix malformed suppression (campsite) | As a maintainer, I want the malformed suppression at `src/doctrine/artifact_kinds.py:118` (`S7632`) fixed with no behavior change. | Low | — | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Regression-delta gate (not "all green") | No test that is green on the merge-base goes red on this branch. Pre-existing reds (known-P0, CI-env, stale-install) are classified and reported per the charter's Pre-existing Failure Reporting Rule / DIR-013 — never green-washed, never used to excuse a new regression. The FR-010 refactor additionally holds regenerate-graph output byte-identical to the pre-captured golden snapshot. | Reliability | High | Open |
| NFR-002 | Facade identity fidelity | 100% of facade re-exports satisfy `facade.SYMBOL is doctrine.SYMBOL` (symbol-level, not whole-module) and appear in the facade module's `__all__` (per `test_charter_facades_reexport_doctrine.py`). | Correctness | High | Open |
| NFR-003 | Complexity ceiling | Every function in `src/doctrine/` measures cognitive complexity ≤ 15 (ruff `C901` / Sonar `S3776`); zero open `S1192` in files touched by this mission. Extracted helpers must reduce real cognitive load and carry their own tests, not relocate complexity into untested no-ops. | Maintainability | High | Open |
| NFR-004 | Type + docs on public surface | `mypy --strict` passes on `doctrine/api.py` and all new/widened facades; every public symbol carries a docstring (DIR-006, DIR-007). | Maintainability | Medium | Open |
| NFR-005 | No new suppressions, no Sonar-UI triage | Zero new blanket `# noqa` / `# type: ignore` / Sonar suppression comments introduced to pass gates (narrow retained ones carry an inline rationale); **and** zero doctrine CRITICAL issues resolved as Won't-Fix / False-Positive in the Sonar UI during the mission window (verified against Sonar issue history). | Maintainability | High | Open |
| NFR-006 | Guard performance | The new lazy-import ratchet runs within the architectural test suite and completes in ≤ 3 s, consistent with existing boundary tests. | Performance | Low | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Layering invariant preserved | Do not legitimize runtime importing doctrine directly. The sanctioned path stays `runtime → charter facade → doctrine`; `doctrine/api.py` exists for charter and the wheel, not for direct runtime import. | Technical | High | Open |
| C-002 | Facades are pure identity re-exports | New/widened facades must be **symbol-level** object-identity re-exports (`X is doctrine.X`) listed in `__all__`, per `test_charter_facades_reexport_doctrine.py` and the **charter C-007 `__all__` convention**. | Technical | High | Open |
| C-003 | OpenAPI does not apply | The doctrine public surface is an in-process Python contract (versioned via wheel semver + `py.typed`), not an HTTP/REST schema. OpenAPI/REST conventions must not shape `doctrine/api.py`; they apply only to a future network edge that wraps doctrine, if one is ever built. | Technical | Medium | Open |
| C-004 | Precondition only — no wheel cutover | This mission stops at the public-API precondition. It must NOT build/publish the `spec-kitty-doctrine` wheel or mint `src/charter/pyproject.toml` — that is #3101, and a partial cutover is forbidden by **ADR 2026-04-25-1 C-007 (no-partial-cutover)** — a distinct rule from the charter C-007 `__all__` convention; always qualify which "C-007" is meant. | Technical | High | Open |
| C-005 | Exemption is inbound-only | `src/specify_cli/doctrine/` may **import** doctrine for its own management (inbound), but must not act as an **outbound** re-export conduit handing doctrine objects to non-exempt runtime. The management-surface carve-out is an explicit enumerated allowlist, not a directory-prefix blanket. | Technical | High | Open |
| C-006 | Behavior-preserving refactor | FR-009/FR-010/FR-011 must be strictly behavior-preserving — no change to regenerate-graph output, resolution results, or any public function's observable contract. | Technical | High | Open |
| C-007-mission | C-007 extension + refactor governance | This mission makes the per-mission scope decision to **extend** the charter C-007 `__all__` convention (today binding only `src/charter/` + `src/kernel/`) to `src/doctrine/`, and records that extension. FR-010's method is governed by the disciplined-refactoring / semantic-compression doctrine (activate the tactic for this mission if not already active). | Governance | High | Open |

### Key Entities

- **Doctrine public surface**: `doctrine/api.py` with an explicit `__all__` — the single declared, wheel-exported set of externally-consumable doctrine symbols.
- **Charter facade**: a per-subsystem module in `src/charter/` that re-exports doctrine **symbols** (not whole submodules) by object identity; the only sanctioned path for runtime to reach doctrine.
- **Lazy-import ratchet**: an architectural test + only-shrink baseline forbidding direct `doctrine.*` imports (module-level and in-function) and first-party re-export laundering from runtime, excluding `TYPE_CHECKING` and the enumerated management surface.
- **Management surface (enumerated)**: the explicit allowlist of modules permitted inbound doctrine imports (`src/specify_cli/doctrine/` plus any modules FR-002 dispositions into it) — never an outbound re-export conduit.
- **INTERNAL doctrine paths**: subsystems with no non-exempt consumer, kept unexposed and asserted-absent by a negative test.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of runtime doctrine access flows through a `charter.*` facade — zero direct `doctrine.*` imports (module-level or lazy) and zero first-party re-export laundering remain outside the **enumerated management surface** (not merely outside the `src/specify_cli/doctrine/` directory).
- **SC-002**: `doctrine/api.py` enumerates the public surface in one place, and every path reached by runtime in the plan-start census — plus the 6 enumerated gaps — has a disposition (PUBLIC/FACADE-ONLY door, enumerated management-surface entry, or ticketed baseline exception); the raw-service bypasses are eliminated. (No "legitimately need" adjudication — coverage is defined by the census, not by opinion.)
- **SC-003**: Introducing a new direct `doctrine.*` import (module-level or lazy) — or a new first-party re-export laundering path — into runtime causes the architectural suite to fail within a single test run.
- **SC-004**: Zero open SonarCloud **CRITICAL** code smells remain in `src/doctrine/` (baseline: 45 CRITICAL of 48 total, project `Priivacy-ai_spec-kitty`, analyzed 2026-08-10), and every doctrine function measures cognitive complexity ≤ 15 — achieved by fixes, not Won't-Fix/False-Positive transitions (NFR-005).
- **SC-005**: The regression-delta gate holds (NFR-001) — no merge-base-green test goes red; all facade re-exports are object-identical to their doctrine originals; and the FR-010 refactor produces regenerate-graph output byte-identical to the pre-captured golden snapshot.
