# Data Model & Contracts

Phase 1 design detail for `status-writepath-profile-surface-remediation-01KTB6AN`. Entities are mostly **existing**; this mission adds behavior, two CLI surfaces, one factory, and one error shape — not new persistent schema.

## Entities (existing — reused, not redefined)

| Entity | Module | Change in this mission |
|--------|--------|------------------------|
| `MissionStatus` | `specify_cli/status/aggregate.py` | Behavior only: docstring write methods; `_read_meta` fail-closed; `load()` slug guard |
| `ActiveWPStatus` | `specify_cli/status/aggregate.py` | None |
| `TransitionRequest` | `specify_cli/status/models.py` | None (reused as `transition()` input) |
| `StatusEvent` | `specify_cli/status/models.py` | None (return of `transition()`) |
| `CommitReceipt` | `specify_cli/coordination/types.py` | None (return of `save()`) |
| `charter.resolver.DoctrineService` (wrapper) | `charter/resolver.py` | None (reused via factory) |
| `PackContext` | `charter/pack_context.py` | None (3-state `activated_agent_profiles`) |
| `AgentProfile` | `doctrine/agent_profiles/profile.py` | None (rendered by `show`) |

## New surfaces

### Factory (FR-010)

```python
def build_activation_aware_doctrine_service(repo_root: Path) -> "charter.resolver.DoctrineService":
    """Construct the inner doctrine service and wrap it with charter activation filters.

    Single construction seam for all profile surfaces (profile list/show,
    charter context --include). Generalises the pattern at charter/generate.py:46-74.
    Layer rule: lives in specify_cli.*, imports charter.* (allowed direction).
    """
```

**Placement decision:** `src/specify_cli/doctrine_service_factory.py` (new, thin) — importable by both `cli/commands/profiles_cmd.py` and, if needed, charter context callers in `specify_cli`. `charter/context.py`'s own `_build_doctrine_service` is updated independently inside `charter.*` (it cannot import `specify_cli`), wrapping with `PackContext` it already constructs at `context.py:244`.

### `profile list` (FR-011/012)

| Mode | Source | Rows |
|------|--------|------|
| default | `factory(repo_root).agent_profiles` | activated only |
| `--all` | `inner.agent_profiles.list_all()` | every layer; columns add `source` + `state(activated|available)` |
| `--show-available` | `inner.agent_profiles.list_all()` | activated + available-not-activated |
| `--json` | as above | JSON array of descriptors |

Three-state preserved: absent key → all built-ins (unchanged default), empty set → none, explicit set → those.

### `profile show <id>` (FR-013/014/015)

Resolution:
1. `svc = factory(repo_root)`; `prof = svc.agent_profiles.get(id)`
2. if `prof is None` and not `--all`: emit `profile_not_activated` (exit 1)
3. else resolve full definition + lineage via inner `AgentProfileRepository.resolve_profile(id)`
4. if any traversed `specializes_from` ancestor ∉ `svc.agent_profiles`: append lineage warning
5. render (human table or `--json`)

Rendered fields: `profile_id`, `name`, `role`, `initialization_declaration`, `specialization{primary_focus, secondary_awareness, avoidance_boundary, success_definition}`, `collaboration{handoff_to, handoff_from, works_with, canonical_verbs}`, `mode_defaults[]`, `directive_references[]`, `tactic_references[]`, `source_layer`, `warnings[]`.

## Error & warning contracts (D-4 / FR-015)

`profile_not_activated` (JSON, exit 1):
```json
{
  "error": "profile_not_activated",
  "profile_id": "architect-alphonso",
  "activated_candidates": ["curator-carla", "reviewer-renata"]
}
```
`activated_candidates` sorted ascending. Mirrors the selector-disambiguation error style.

Lineage warning (FR-015), non-fatal:
```json
{ "warnings": ["resolved via non-activated parent profile(s): base-analyst — these act as abstract base profiles and are not directly selectable"] }
```
Human mode prints the same text to stderr in yellow.

## Invariants

- INV-1: `transition()` never appends an event when `validate_transition` fails (fail-closed).
- INV-2: factory is the **only** construction of the activation wrapper in `specify_cli.*` (no duplication; C-003).
- INV-3: `profile list` default output for a project with absent `activated_agent_profiles` is byte-identical to pre-mission output (NFR-001).
- INV-4: no write to `coordination/transaction.py` (NFR-002).
- INV-5: slugs reaching `MissionStatus.load()` match `^[A-Za-z0-9_-]+$` (`.isascii()` true) — DIR-010/011.
