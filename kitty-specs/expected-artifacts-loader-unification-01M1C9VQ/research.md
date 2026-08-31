# Phase 0 Research — expected-artifacts-loader-unification

Consolidated from two research scouts + a two-lens post-spec adversarial squad.
Every decision below is anchored to file:line evidence.

## D1 — Home for the relocated authority: `charter/activation/manifest_loader.py`

- **Decision**: Put the cached loader *function* in `charter/activation/`, and
  DEFINE `ManifestSchemaError` beside it in `charter/activation/manifest_loader.py`
  (as shipped — NOT `repository.py`, which would force an `offering→activation`
  import). The sibling `MalformedManifestError` stays charter-resident in
  `charter/offering/missions/repository.py:38`; both are re-exported via the shim.
- **Rationale**: The loader needs `resolve_org_expected_artifacts`
  (`charter/activation/org_expected_artifacts.py:54`), `resolve_existing_org_roots`
  (`charter/offering/drg/org_pack_config.py:571`), `MissionTemplateRepository`
  (`charter/offering/missions/repository.py:145`), and the model
  (`.../expected_artifact_manifest.py:87`). Activation may import offering — proven
  by `mission_type_profiles.py:975,1120,1130`. Offering must NOT import activation
  (only a `TYPE_CHECKING` mention exists, `mission_step_repository.py:44`), so the
  loader cannot live in offering/missions. Activation is the correct layer.
- **Alternatives**: (a) offering/missions home — rejected, would need
  offering→activation for org resolution. (b) A dedicated top-level
  `charter/manifest/` — rejected as premature; activation already owns the
  org-precedence collaborators.

## D2 — Sibling error model (the load-bearing post-spec correction)

- **Decision**: `MalformedManifestError` (charter, `repository.py:38`) is the
  fail-loud channel for **present-but-unparseable** manifests (YAML-syntax,
  non-mapping, and present-but-unreadable) on BOTH tiers. `ManifestSchemaError`
  is the sibling for **schema/`extra="forbid"`** violations. Both are distinct
  from `None`="not found". The malformation channel is NOT canonicalized on
  `ManifestSchemaError`.
- **Rationale**: Three independent forces converge (both squad lenses found this):
  1. **C-001** — a charter-resident loader cannot raise a `specify_cli`-resident
     `ManifestSchemaError` (`specify_cli/dossier/manifest.py:104`) without charter
     importing specify_cli. `MalformedManifestError` is already in charter.
  2. **Symmetry** — the built-in tier already raises `MalformedManifestError` for
     YAML-syntax (`repository.py:411-412`, `1763bf2ae3`); the org tier must match.
  3. **Message correctness** — `ManifestSchemaError.__str__` says "schema-invalid"
     (`manifest.py:149-155`), actively misleading for a parse fault; its own
     docstring (`manifest.py:106-108`) *excludes* YAML-syntax.
- **Consequence**: `ManifestSchemaError` still moves to charter (the loader raises
  it for the schema case), re-exported via the shim.
- **Adversarial disposition**: **changed** — the spec originally canonicalized on
  `ManifestSchemaError` (FR-008 v1); corrected to the sibling model.

## D3 — `ManifestRegistry` stays; charter owns a loader *function*

- **Decision**: `ManifestRegistry` remains in `specify_cli/dossier/manifest.py`
  as a thin delegate; the charter authority is a *function* carrying its own
  `_cache`. `ManifestRegistry`'s sibling completeness methods
  (`get_required/blocking/optional_artifacts`, `validate_manifest`, `clear_cache`)
  do NOT move.
- **Rationale**: `ManifestRegistry` is a stateful class instantiated 4× in
  specify_cli (`dossier_pipeline.py:361`, `reconcile.py:158`, `rebaseline.py:346`,
  + doc) as `Indexer(ManifestRegistry())`; moving it wholesale would drag
  specify_cli-owned completeness logic into charter. Only the load+cache concern
  relocates.
- **Alternative**: move the whole class — rejected (charter would host
  dossier-completeness logic; larger blast radius).
- **Adversarial disposition**: **accepted** (scope lens SEV-3).

## D4 — Shim re-export surface

- **Decision**: `specify_cli/dossier/manifest.py` re-exports `ManifestRegistry`
  (kept), `load_manifest` (delegate), `ManifestSchemaError`, and
  `MalformedManifestError`.
- **Rationale**: `ManifestSchemaError` is imported/caught at 8+ specify_cli sites
  (`sync/namespace.py:102`, `sync/dossier_pipeline.py:363`, 6 tests). Omitting it
  from the shim breaks every catch site on import.
- **Adversarial disposition**: **accepted** (scope lens SEV-4).

## D5 — Close the launder seam by construction (not the model_validate gate)

- **Decision**: Pin `runtime_bridge_composition.py:504`'s `except` to
  `UnregisteredMissionFamilyError` **only**, plus a positive regression asserting
  a malformed org manifest through the composed guard propagates (never `[]`).
- **Rationale**: The `model_validate` arch-gate cannot police the guard seam; a
  broadened `except (UnregisteredMissionFamilyError, MalformedManifestError)`
  reopens #3412 while the string-gate stays green. The malformed raise fires at
  *gather* time (`composition.py:486`, outside the `:502-504` try) and, as a
  distinct type, is not caught there — failing BEFORE the None-vs-`frozenset`
  decision (`cores.py:724`), so C-002 (tri-state) and C-003 (guard-table) are
  untouched. Verified non-contradictory by the fail-loud lens.
- **Adversarial disposition**: **changed** — added FR-010 durability gate.

## D6 — Delete `from_yaml_file` (do not "route")

- **Decision**: Delete `ExpectedArtifactManifest.from_yaml_file`
  (`expected_artifact_manifest.py:130`) and migrate its 3 tests
  (`test_manifest.py:458/472/486`) to the canonical loader.
- **Rationale**: It constructs via `cls(**data)` (`:152`), which the
  `model_validate(` string-gate cannot police. The arch-gate is therefore
  broadened to also forbid bare `ExpectedArtifactManifest(` construction outside
  the model's own tests. No production callers exist.
- **Adversarial disposition**: **accepted** (scope lens SEV-2).

## D7 — Widen present-but-unreadable on BOTH tiers (costed, not hidden)

- **Decision**: `OSError`/`UnicodeDecodeError` on a manifest that EXISTS →
  `MalformedManifestError` on both tiers. This re-touches the built-in reader
  (`repository.py:413-414`, which today swallows both to `None`) — the shipped
  fix widened only `YAMLError`.
- **Rationale**: Symmetry (D2) demands both tiers agree; the fail-loud lens showed
  the unreadable case is NOT covered by the shipped built-in fix, so honoring
  symmetry forces this — captured as FR-012 rather than an unstated edge case.
- **Adversarial disposition**: **changed** — promoted an edge case to FR-012.

## D8 — Red-first tagging hygiene

- **Decision**: Only genuinely-RED-on-`upstream/main` scenarios carry
  `@pytest.mark.regression`: US1-AC1 (org YAML broken), US1-AC4 (launder through
  composed guard), US1-AC5 (non-mapping org), the org-unreadable case. US1-AC2
  (absent degrades), US1-AC3 (built-in YAML — already shipped), and all US2
  (consolidation/cache) are **characterization** (green-stays-green), NOT
  `regression`.
- **Rationale**: A green `@regression` test is a landing defect (charter DIRECTIVE
  034/041; the green-regression-test lesson). Transitional repros do not remain
  marked `regression`.
- **Adversarial disposition**: **accepted** (fail-loud lens SEV-2).

## D9 — Non-goal fences confirmed

- Org-root resolver "triplication" is NOT dedup work: the three wrappers already
  delegate to `charter.drg.resolve_existing_org_roots` (#3525) — 1-line wrappers.
  No WP targets them (removed from scope to prevent a manufactured dedup WP).
- `blocking_artifact_names` None-vs-`frozenset()` tri-state (#3729) and the
  guard-table short-circuit (`cores.py:721-723`, #3386/#3397/#3407) are untouched;
  malformation fails before both.

## Supply-chain / dependencies

No dependency added, upgraded, or removed. `051-supply-chain-install-safety` is
N/A for this mission. Silence here is compliance because there is no dependency
decision to examine.
