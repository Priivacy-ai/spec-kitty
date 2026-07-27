# Interface Contracts — Doctrine Governance Fidelity

The public-surface contracts established or relied upon by this mission.

## C1 — Charter-activation-aware org-profile resolver (WP02, FR-003/FR-007)

```python
# src/specify_cli/invocation/org_profiles.py
@dataclass(frozen=True)
class ResolvedOrgProfile:
    profile: AgentProfile
    source_layer: str          # always "org" for entries returned here
    source_path: Path | None

def resolve_activated_org_profiles(repo_root: Path) -> list[ResolvedOrgProfile]: ...
```

- Returns the **charter-activated** org-provenance subset, composed via
  `build_activation_aware_doctrine_service(repo_root)` (the `PackContext.activated_agent_profiles`
  three-state gate). Pure, fail-closed.
- **Contract**: `activated_agent_profiles is None` → all declared org profiles admitted;
  explicit list → only listed ids; explicit list excluding an id (or empty set) → that id
  is ABSENT. Never returns a profile the charter has de-activated.

## C2 — Org overlay reaches consumers only through the activation filter (C-008, WP03/WP04)

- `ProfileRegistry` (dispatch routing), the dispatch governance-context path
  (`charter/context.py`), and agent-profile projection (`tool_surface/profiles/projection.py`)
  merge the C1 activated subset **onto their existing project layer** — they MUST NOT
  splice raw `org_dirs=` / `resolve_org_roots(...)` into an `AgentProfileRepository`.
- Enforced by the architectural gate `tests/architectural/test_org_activation_seam.py` (WP05, FR-008):
  absence-of-raw-splice at the 3 org-honouring surfaces, integer floor = 3, self-mutation teeth.

## C3 — Charter directive interpolation (WP01, FR-001/FR-002)

- `charter generate --from-interview` renders the `documentation_policy` answer verbatim
  into the `charter.md` Project Directives section (mirroring `risk_boundaries`); absent answer → no line.

## C4 — Pack layout (WP06, FR-013)

- Canonical org-pack layout is flat `<pack>/agent_profiles/<id>.agent.yaml`. The charter
  activation subsystem resolves layout-tolerantly (flat preferred, nested
  `<pack>/doctrine/<plural>/org/` fallback) so `charter activate agent-profile <id>` works
  against runtime-resolvable packs.

## C5 — doctor doctrine override diagnostics (WP07/WP08/WP09, FR-009..FR-012)

```python
# doctrine.drg.override_policy public API (post-WP09 __all__):
load_replaceable_builtins(repo_root) -> ReplaceableBuiltinsPolicy
find_overridden_builtin_urns(merged, built_in_urns) -> set[str]
find_unsanctioned_overrides(targets, policy) -> list[UnsanctionedOverride]   # by-value type
```

- `spec-kitty doctor doctrine --json` reports an `unsanctioned_overrides` finding and flips
  `healthy=false` (RC=1) when an org pack overrides a built-in DRG node without a
  `.kittify/doctrine/replaceable-builtins.yaml` sanction. Project-tier overrides are
  intentionally ungoverned (FR-012). No org packs → unchanged (NFR-001).
