# Phase 0 Research: Org-Tier Doctrine Reaches Its Consumers

The spec's own Decisions Log (D-000 through D-005) already resolves every open technical question
that would normally drive Phase 0 research — there are zero `NEEDS CLARIFICATION` markers in this
mission's spec. This document instead records the **plan-level** research this planning pass
performed by reading the actual call sites, which the spec's Decisions Log does not itself specify
(module placement, layer-import legality, cache semantics). Each entry below is a decision this
plan's Implementation Concern Map depends on.

## R-01: Where does the shared `org_dirs` helper (FR-003) live?

**Decision**: `src/doctrine/drg/org_pack_config.py`, as a new function sibling to the existing
`resolve_org_roots(repo_root: Path) -> list[Path]` (verified at lines ~404-412 of that file).

**Rationale**: The four/five consumers span three layers:
- `charter/mission_type_profiles.py` (charter layer, FR-004)
- `specify_cli/mission_step_contracts/executor.py`,
  `specify_cli/review/gate_bindings.py`, `specify_cli/mission_loader/command.py` (specify_cli
  layer, FR-001/FR-005/FR-006a)
- `runtime/next/runtime_bridge_composition.py` (runtime package, FR-006)

`doctrine` sits below all three (`kernel <- doctrine <- charter <- specify_cli`), and `runtime`
already imports directly from `doctrine.missions.step_contracts` in this exact file
(`runtime_bridge_composition.py`'s existing `_resolve_runtime_contract_for_step` already does
`from doctrine.missions.step_contracts import MissionStepContractRepository`). Placing the shared
helper in `doctrine` is therefore the only location reachable from all five call sites without
introducing a new cross-layer import direction.

**Alternatives considered**: A new module in `charter` (e.g. `charter/org_dirs_resolution.py`) —
rejected because `runtime.next.runtime_bridge_composition` would then need a new
`runtime -> charter` import; verified no such import exists today in that file (it imports
`doctrine.missions.step_contracts` and, locally, `runtime.next.runtime_bridge`, never `charter.*`).
Introducing a new import direction is a heavier verification burden than adding one function to an
already-imported `doctrine` module.

## R-02: FR-002's single-path `org_root` — inline or shared helper?

**Decision**: Inline in `executor.py`'s `execute()` method, following the exact first-match pattern
D-000(2) names: iterate `charter.activation.org_pack_discovery._enumerate_org_pack_paths(repo_root)`, take the
first `candidate.exists()`.

**Rationale**: The spec's FR-003 only mandates a shared helper for the **list**-shaped `org_dirs`
argument ("written once and reused by FR-001, FR-004, FR-005, FR-006" — the single-path shape is
not named). The only existing caller of this pattern,
`charter/action_doctrine_bundle.py:_resolve_action_bundle` (lines ~90-97), does not itself go
through a shared helper either — it inlines the same loop. Following that precedent exactly (rather
than inventing a new shared abstraction the spec does not ask for) keeps FR-002 minimal and
auditable against its cited reference implementation.

**Verified**: `_enumerate_org_pack_paths` is exported (present in `org_pack_discovery.py`'s
`__all__`, line 31) despite its underscore prefix, and is already imported cross-module by
`action_doctrine_bundle.py` (`from charter.activation.org_pack_discovery import (_enumerate_org_pack_paths,)`).
Cross-module import of this specific private-named-but-public-exported function is established
precedent, not a new pattern this mission introduces.

## R-03: FR-004's org-tier artifact-kind subdirectory name

**Decision**: `"mission_types"` — **not** an `ArtifactKind` enum member.

**Rationale**: `MissionTypeProfileRepository` is a `BaseDoctrineRepository` subclass (confirmed,
`mission_type_profile_repository.py:77`), but its project overlay directory is
`.kittify/doctrine/mission_types/<type>/governance-profile.yaml` — a mission-type-scoped tree, not
one of the nine `ArtifactKind` content-dir kinds. `DoctrineService` has no `.mission_types` property
and no `ArtifactKind.MISSION_TYPE` member exists (verified: `ArtifactKind` in
`src/doctrine/artifact_kinds.py` lists exactly 12 members, none named for mission types). The shared
helper from R-01 must therefore be genuinely parameterized by a caller-supplied subdirectory string
(mirroring what `DoctrineService._org_dirs(artifact: str)` already does), not restricted to
`ArtifactKind.plural` values — FR-004 calls it with `"mission_types"`, the other four/five call
sites call it with `"mission_step_contracts"`.

## R-04: FR-008's shared helper — new module, not a `MissionTemplateRepository` method

**Decision**: New module `src/charter/activation/org_expected_artifacts.py`, not a new method on
`MissionTemplateRepository`.

**Rationale**: C-003 is explicit: "FR-008 adds a narrow, additive org-file check alongside the
existing built-in-only reader; it does not restructure `MissionTemplateRepository`'s single-root
design ... or change any of its other methods." Read literally, this rules out adding *any* new
method to the class too (not just restructuring existing ones) — the org-file check must live
beside the class, calling `MissionTemplateRepository.default().get_expected_artifacts(mission_type)`
only as the built-in-tier fallback. `charter` is an importable layer from both of FR-008's two
callers (`charter/mission_type_profiles.py` itself, and `specify_cli/dossier/manifest.py`, which
already imports `charter.missions.MissionTemplateRepository` today — confirmed via its
`TYPE_CHECKING`-gated import at the top of `manifest.py`), so placing the shared helper in `charter`
keeps both callers' import direction unchanged (specify_cli -> charter is already established;
charter -> charter is intra-layer).

## R-05: `ManifestRegistry.load_manifest`'s cache-key correctness (self-identified, not in spec)

**Finding**: `ManifestRegistry` (`specify_cli/dossier/manifest.py`) is a
`@staticmethod`-only class with a **process-global** cache:
`_cache: dict[str, ExpectedArtifactManifest | None]`, keyed **only** on `mission_type`. Its sole
production caller, `resolve_manifest_version(mission_type: str)` in
`specify_cli/sync/namespace.py:89`, has **no `repo_root` in scope at all** — it is called from a
context (`NamespaceRef` construction for SaaS body sync) that only carries mission metadata, not a
project root.

**Implication for FR-008**: If `load_manifest` gains org-tier resolution keyed only on
`mission_type`, the very first call to resolve a given `mission_type` in a long-lived process
(e.g. a daemon or long test session touching two different projects with different org overrides)
permanently caches that project's result for every later call — a silent-scope-loss shape NFR-002
was written to forbid at the five caller-threading sites, that this plan's investigation found
recurring at FR-008's new surface too.

**Design decision** (recorded here, referenced from `plan.md`'s Stated Assumptions): give
`load_manifest` an optional `repo_root: Path | None = None` parameter; cache key becomes
`(mission_type, tuple(sorted(str(p) for p in resolved_existing_org_roots)))` — an empty tuple when
`repo_root is None` (today's call shape, unchanged behavior, satisfies SC-005 Given #2's
byte-identical requirement) or when no org pack is configured/exists. `resolve_manifest_version`
itself is **not** changed by this mission (it has no `repo_root` to pass, and passing one is out of
scope — FR-008 only requires that *a caller that has* `repo_root` can see the override; it does not
require retrofitting every existing caller with one).

## R-06: Campsite-cleaning check (charter Quality & Tech-Debt Standing Order #2)

**Finding**: None of the five in-scope call sites, nor `MissionTemplateRepository`,
`ManifestRegistry`, or `mission_type_profiles.py`'s two touched functions, are god-surfaces.
`_resolve_governance_slot` and `_resolve_expected_artifacts_slot` are each under 40 lines;
`executor.py`'s `__init__`/`execute` are already factored (delegation resolution and request-text
building are separate private methods); `gate_bindings.py`'s `_build_repository` is a two-line
function. No preceding campsite-clean step is warranted before this mission's functional changes.
