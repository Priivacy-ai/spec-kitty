# Contract: Empty-charter dispatch fallback (US1 / FR-002…FR-006)

## Seam
`invocation/executor.py` auto-route branch (`:255-259`, the *only* auto-route entry point — verified) calls
`invocation/empty_charter.py::resolve_generic_fallback(repo_root, request_text) -> RouterDecision | None`.

## Predicate (composite — ALL charter-activatable dimensions)
```
pc = PackContext.from_config(repo_root)
is_empty = (charter_activated_urns(repo_root) == set())     # 6 URN kinds
           and pc.activated_agent_profiles is None
           and pc.activated_mission_step_contracts is None
           and pc.activated_glossary_packs is None
           and pc.org_roots == ()                           # no org/project packs
# anti_pattern is NOT charter-activatable → excluded.
```

### Predicate truth table (all MUST be tested)
| Charter state | is_empty |
|---|---|
| nothing activated, no org packs | **True** → fallback |
| any URN kind activated | False |
| `activated_agent_profiles` non-None (incl. `[]`) | False |
| `activated_mission_step_contracts` non-None | False |
| `activated_glossary_packs` non-None | False |
| org/project pack present (`org_roots != ()`) | False |

## Routing behaviour
| Given | When | Then |
|---|---|---|
| `is_empty`, no `--profile` hint | dispatch auto-routes | `RouterDecision(profile_id="generic-agent", action=<derived from verb>, confidence="generic_fallback")`; `InvocationPayload.empty_charter_fallback = True` |
| `is_empty`, explicit `--profile architect-alphonso` | dispatch | specialist resolves normally (fallback returns `None`) |
| any activation present | dispatch | `resolve_generic_fallback` returns `None`; existing routing unchanged |
| `is_empty` | `software-dev` mission type requested | still available (always-on) — **assert explicitly** |

## Governance-context agreement (NOT free — US1 scope)
Under an empty charter, `render_compact_view` (`compact.py:216-230`) merges `resolver_directives` from `resolve_project_governance`, and `_resolve_directives_selection` (`resolver.py:233-260`) **catalog-falls-back to ALL built-in `DIR-###`** when nothing is selected. So the generic-agent dispatch would leak the full directive canon.
- **Requirement**: on the `empty_charter_fallback` path, the governance block must NOT merge the project catalog-fallback directives (preferred: `build_charter_context(..., suppress_project_resolver=True)` or a scoped minimal-governance render for the fallback; do NOT globally change `_resolve_directives_selection`).
- **Red-first agreement test**: dispatch under a wholly-empty charter; assert `payload.profile_id == "generic-agent"`, the governance `Directive IDs:` block is empty (or exactly generic-agent's own cited directives), no specialist marker, `empty_charter_fallback is True`. RED before the scoping lands.

## Warning surface
`cli/commands/dispatch.py::_render_rich_payload` (lines 59-91), gated on `getattr(payload, "empty_charter_fallback", False)` (payload uses dynamic `__init__` — read defensively; always thread the kwarg at the single construction site). One yellow panel; `--json` exposes the boolean.

## Default charter asset (FR-005)
Ship `src/doctrine/assets/built-in/charter_scaffold_minimal.yml` + `.asset.yaml` (`id: common-charter-scaffold-minimal`, `mime: application/yaml`). Resolve via `spec-kitty doctrine asset path common-charter-scaffold-minimal`. Done-line: (a) resolves; (b) `pack_validator` mime guard test; (c) **activatability test** — activate the scaffold in a temp repo, assert the resulting charter validates, no user charter touched.

## Untouched (regression proof — MUST stay green, NOT owned)
`test_doctrine_service_factory.py::*`, `test_registry_builtin_activation_parity.py::{test_excluded_builtin_absent_from_routing_and_context, test_no_activation_key_admits_all_builtins_in_routing}`, `tests/charter/test_activation_authority.py::*`.

## New coverage (owned)
`tests/specify_cli/invocation/test_empty_charter_fallback.py` (predicate truth table, decision shape, action-derivation preserved, RouterDecision Literal), `tests/specify_cli/invocation/cli/test_dispatch.py` (auto-route→generic-agent + warning + **governance-agreement (Directive IDs empty)** + `--json` flag + explicit-profile bypass + software-dev availability), plus the asset activatability + mime tests.
