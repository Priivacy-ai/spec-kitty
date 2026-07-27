# Contracts — Mission-Type Doctrine Authority

Internal (in-process) contracts, not network APIs. Each is a behavioural contract a
test asserts. Signatures are indicative; the WPs finalize them against live code.

## C1 — `resolve_mission_type_context` (the seam)

```
resolve_mission_type_context(repo_root, *, mission_type=None, feature_dir=None) -> ResolvedMissionType
```

**Behaviour**
- Resolves the type key: explicit `mission_type` → `feature_dir/meta.json` → error.
- **Unknown *typed* mission** (type present, unrecognised, no resolvable override) → raises a clear, remediable error (`UnknownMissionTypeError`-class). Never returns software-dev. (FR-003)
- **Typeless / no `feature_dir` and no `mission_type`** → neutral/degrade result, never software-dev. (FR-003a)
- **Known type, empty grain for a step** → empty resolved set for that step, no error. (FR-004)
- Governance slot = type-grain ∪ action-grain, ordered, URN-deconflicted; double-declaration across grains → error. (FR-013, NFR-007)
- Preserves the two distinct hard-fail policies (action-sequence strict; governance tolerant when a project override exists) as explicit branches.
- Complexity ≤ 15 via extracted helpers.

**Consumers converge**: `prompt_builder` (Surface B) and the action-doctrine path both call this; no second resolution path remains.

## C2 — Action-doctrine path (leak closure)

- `build_charter_context(...)` and `build_charter_context_json(...)` accept the mission type (threaded from `scope_router`/`feature_dir`); `_load_action_doctrine_bundle` keys off it, never `template_set or "software-dev-default"`.
- Per-entry contract: prompt path has `feature_dir`; planning-from-root requires explicit `--mission-type`; mission-less callers (`executor.py`, `workflow.py`) degrade neutrally.
- Dead `_render_action_scoped` / `_append_action_doctrine_lines` removed.
- `template_set` retained only for template-file selection.

## C3 — Per-type override overlay

- Project profile at `.kittify/doctrine/mission_types/<type>/governance-profile.yaml` resolves through `doctrine/base.py`: builtin → org → project, field-merge, collision warning.
- A project override of a field wins; absent fields fall through; a collision is reported (not silent).

## C4 — Dossier gate reader (detachable swap)

- `ManifestRegistry.load_manifest(type)` reads the **doctrine** tree via `repository.get_expected_artifacts` through a `ConfigResult → ExpectedArtifactManifest` adapter (cache preserved).
- Ordering contract: reconcile doctrine upward → transitional parity green → flip → delete copies. Never delete before parity is green. Non-blocking for enforcement; final flip deferrable on deep drift (deferral recorded, not silent).

## C5 — Enforcement (enduring, behavioural)

- **Non-leakage**: for each of documentation/research/plan, the resolved (type ⊕ action) URN set is **disjoint** from a curated, URN-normalized software-dev-only denylist.
- **Non-vacuity twin**: the same denylist **is** resolved by `software-dev`, exercised through an action name **shared** across types (so it cannot pass vacuously).
- **Determinism**: two resolutions of identical inputs are byte-identical.
- **Hard-error**: unknown typed mission errors on every governance path; typeless caller degrades.
- All enduring tests are doctrine-module or integration; **no transitional parity scaffold survives merge**; no code kept solely to avoid test churn.
