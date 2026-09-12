# Contract: Org-Tier Resolution Surfaces

This mission has no HTTP/API surface. The "contracts" below are the internal function/log-record
shapes that multiple work packages depend on staying stable, so an implementer of one IC does not
need to read another IC's source to conform to it.

## C-1: `resolve_org_dirs` (IC-01 → consumed by IC-02, IC-03, IC-04)

```python
def resolve_org_dirs(repo_root: Path, subdir: str) -> list[Path]:
    """Existing-path-filtered, declaration-ordered org directories for *subdir*."""
```

- **Location**: `src/doctrine/drg/org_pack_config.py`.
- **Guarantee**: Return value is `[]` when no org packs are configured, or when configured packs'
  roots do not exist on disk (never raises for a missing/stale config entry — Edge Cases,
  NFR-002).
- **Guarantee**: Declaration order preserved; later-configured packs appear later in the list
  (callers/downstream repositories interpret "later overrides earlier" — NFR-003, unchanged
  merge semantic).
- **Non-guarantee**: Does not check whether `<root>/<subdir>` itself exists — only the org
  **root** is existence-filtered before joining. A caller passing this list into a
  `BaseDoctrineRepository` subclass relies on that repository's own load-time missing-directory
  tolerance (existing behavior, unchanged).
- **Consumers and their `subdir` value**:
  - FR-001 (`executor.py`), FR-005 (`gate_bindings.py`), FR-006 (`runtime_bridge_composition.py`),
    FR-006a (`mission_loader/command.py`): `subdir="mission_step_contracts"`.
  - FR-004 (`mission_type_profiles.py`): `subdir="mission_types"`.

## C-2: FR-002's single-path `org_root` resolution (IC-02, inline — not a shared function)

```python
effective_org_root: Path | None = None
for _name, candidate in _enumerate_org_pack_paths(context.repo_root):
    if candidate.exists():
        effective_org_root = candidate
        break
```

- **Location**: inlined in `executor.py`'s `execute()`, immediately before the
  `load_validated_graph(context.repo_root)` call, which becomes
  `load_validated_graph(context.repo_root, org_root=effective_org_root)`.
- **Guarantee**: First-match semantics — if more than one org pack is configured, only the first
  whose path exists on disk contributes to the DRG. This is the pre-existing, out-of-scope
  limitation named in spec C-004; this mission does not change it, only threads the existing
  pattern through this one call site.
- **Reference implementation this mirrors exactly**: `charter/action_doctrine_bundle.py`'s
  `_resolve_action_bundle`, lines ~90-97.

## C-3: FR-007's WARNING log record (IC-03)

Emitted from `_dispatch_via_composition` (`runtime/next/runtime_bridge_composition.py`), one
record per step with 1+ unresolved delegation candidates, placed immediately after the existing
`logger.info("composed %s/%s emitted %d invocation(s): %s", ...)` block:

```python
for step in result.steps:
    if not step.unresolved_candidates:
        continue
    logger.warning(
        "step %s (contract %s) has unresolved delegation candidate(s): %s",
        step.step_id,
        result.contract_id,
        ", ".join(unresolved),
    )
```

- **Level**: `WARNING`, never `ERROR` — non-blocking (D-005: a correctly-cited-but-activation-filtered
  candidate is a valid, if inert, state, not necessarily an authoring mistake).
- **Cardinality**: Exactly one WARNING per step with 1+ unresolved candidates — not one per
  candidate, not one per contract (SC-004: "exactly one WARNING-level log record naming the step id
  and candidate" per the offending step).
- **Negative case**: Zero WARNING records when every candidate resolves — must be asserted in the
  same test as the positive case (SC-004), not a separate test, so a future change cannot make the
  positive case pass while silently breaking the negative one.
- **Fields named in the message**: step id, contract id, unresolved candidate string(s) — all
  three, per FR-007's explicit requirement ("naming the step id, contract id, and the candidate
  string(s)").

## C-4: FR-008's org-file precedence (IC-05)

```python
def resolve_org_expected_artifacts(
    org_roots: list[Path], mission_type: str
) -> Mapping[str, object] | None:
    """<org_root>/<mission_type>/expected-artifacts.yaml, later org_roots override earlier."""
```

- **Location**: `src/charter/org_expected_artifacts.py` (new module).
- **Input contract**: `org_roots` is the caller's own existence-filtered list of org roots (see
  `data-model.md` — this is **not** `resolve_org_dirs`'s subdir-joined output; the caller passes
  raw org roots and this function does the per-root `<mission_type>` join itself, since
  `mission_type` varies per call and cannot be baked into a fixed `subdir` string).
- **Precedence within `org_roots`**: last-existing-match wins (same declared-order-override
  contract as every other org-tier consumer in this mission, NFR-003) — not first-match (unlike
  C-2's DRG single-root resolution, which is deliberately first-match per the inherited C-004
  limitation). FR-008 is a **new** surface with no pre-existing first-match precedent to inherit,
  so it follows the more common `org_dirs`-style later-wins convention instead.
- **Precedence vs. built-in**: whole-file replacement, not field-merge. When an org file resolves,
  the built-in `<missions_root>/<mission_type>/expected-artifacts.yaml` is not read at all for that
  mission type (SC-005 Given #3).
- **No built-in baseline required**: a wholly org-defined custom mission type (no built-in
  `expected-artifacts.yaml` at all) is valid — the org file is authoritative with no fallback
  needed (Edge Cases, last bullet).
- **Callers**: `charter/mission_type_profiles.py:_resolve_expected_artifacts_slot` and
  `specify_cli/dossier/manifest.py:ManifestRegistry.load_manifest` both call this function and
  fall back to their existing `MissionTemplateRepository`-based built-in read only when it returns
  `None`.
