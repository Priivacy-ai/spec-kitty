# Contract — Doctrine-Service Builder Overlay Seam (WP-B, #3176)

## C-B1 Optional overlay param, default byte-identical
- `agent_profile_overlay_dir: Path | None = None` is threaded through:
  `build_activation_aware_doctrine_service` → `_build_activation_aware_doctrine_service` → `_build_doctrine_service` → `doctrine.service.DoctrineService`.
- When unset (`None`): kwargs and constructed service are byte-identical to pre-mission; every existing caller is unaffected (NFR-002).

## C-B2 Overlay honoured for agent profiles only
- `DoctrineService.agent_profiles` uses `agent_profile_overlay_dir` as the project overlay dir when set, else `self._project_dir("agent_profiles")`.
- No other repository's project dir is affected (overlay is agent-profile-scoped).

## C-B3 Project-overlay profiles found
- `default_profile_repository(project_root)` builds via the factory with `agent_profile_overlay_dir = project_root / ".kittify/agent_profiles"`.
- A profile authored at `.kittify/agent_profiles/<id>.agent.yaml` is visible through the returned repository with `project` provenance.
- The three carved-out tests pass and the C-002 carve-out docstring/skip is deleted:
  `test_projection.py`, `test_projection_collision_precedence.py`, `test_projection_org_visibility.py`.

## C-B4 Invariants preserved
- Single-wrapper-body (C-006): only `_build_activation_aware_doctrine_service` constructs the activation-aware wrapper; the public builder stays a thin delegate; the service is always wrapped (R5).
- C-008: `default_profile_repository` still merges activation-admitted org profiles via `resolve_activated_org_profiles` (the activation gate), NOT a raw `org_dirs` splice.
- C-001: `charter` does not import `specify_cli`; the overlay authority lives in `charter`/`doctrine`, consumed by `specify_cli`.
