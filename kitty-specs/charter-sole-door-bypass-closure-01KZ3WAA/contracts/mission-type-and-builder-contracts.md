# Contracts: `mission-type` activation gating and the unified builder

## `resolve_mission_type_context()` activation contract (FR-006)

Distinct from the three-state contract used by the other 9 kinds, because `PackContext.
activated_mission_types` is never `None`:

| `PackContext.activated_mission_types` | Meaning | Post-mission behaviour |
|---|---|---|
| Equals `builtin_mission_type_id_set()` (the collapse default) | No selection was authored | Return the full built-in mission-type set |
| A proper, non-default subset | A selection was authored | Return only the named mission-types |

**The gating point is `charter.activation.mission_type_profiles.resolve_mission_type_context()` ONLY** — NOT
`charter.activation.mission_type_profile_repository.MissionTypeProfileRepository`'s own file (post-tasks squad
correction: that file is WP06's exclusive ownership for an unrelated change; implementing filtering there
too would create a real ownership overlap), and NOT `charter.activation.resolver.DoctrineService` (see the sibling
contract file's "Explicitly NOT on this class" section). A bare project (no `mission-type` key
authored) must still resolve every built-in mission-type — proven by a dedicated regression test asserting
**set-equality against `builtin_mission_type_id_set()`**, not a fakeable subset check (post-plan squad
correction: "`research`, `software-dev`, `documentation`, `plan`, at minimum" is satisfied even if a fifth
built-in type silently drops out; the non-fakeable comparand already exists and must be used directly),
since the default-collapse already happened before this repository ever sees the value and a filtering bug
here has no three-state safety net to fall back on.

## Unified builder contract (FR-008)

One function, replacing both `specify_cli.doctrine_service_factory.build_activation_aware_doctrine_service`
and `charter.activation.doctrine_service_builder._build_activation_aware_doctrine_service`:

```
build_activation_aware_doctrine_service(repo_root: Path) -> charter.activation.resolver.DoctrineService
```

Behavioural contract (both former call sites' inputs must produce identical output):

- `active_languages` is always computed via `infer_repo_languages(repo_root)` and passed to the inner
  `doctrine.service.DoctrineService` construction (the `charter` builder's fuller behaviour wins).
- `org_roots` is always self-resolved via `resolve_org_roots` (the `specify_cli` builder's fuller behaviour
  wins) — no caller can silently lose the org layer by omitting an argument.

Regression proof: construct the unified builder with the same `repo_root` twice, once exercising each former
call site's original argument shape, and assert byte-identical (or structurally-identical, if a `__eq__` is
impractical) resulting catalogs across all 9 gated properties.

Both `src/specify_cli/doctrine_service_factory.py::build_activation_aware_doctrine_service` and
`src/charter/activation/doctrine_service_builder.py::_build_activation_aware_doctrine_service` become either the same
function (one deleted, callers repointed) or one thin re-export of the other — never two independent
implementations after this mission (C-001).
