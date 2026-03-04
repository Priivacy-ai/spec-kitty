# Internal API Contracts: Feature 048

**Feature**: Structured Agent Identity & Constitution-Profile Integration

## Contract 1: ActorIdentity Protocol

```python
"""Internal protocol for structured agent identity."""

from typing import Protocol

class ActorIdentityProtocol(Protocol):
    """Contract for ActorIdentity value object."""

    @property
    def tool(self) -> str: ...
    @property
    def model(self) -> str: ...
    @property
    def profile(self) -> str: ...
    @property
    def role(self) -> str: ...

    def to_dict(self) -> dict[str, str]: ...
    def to_compact(self) -> str: ...

    @classmethod
    def from_compact(cls, s: str) -> "ActorIdentityProtocol": ...
    @classmethod
    def from_legacy(cls, s: str) -> "ActorIdentityProtocol": ...
    @classmethod
    def from_dict(cls, d: dict[str, str]) -> "ActorIdentityProtocol": ...
```

### Serialisation Contract

**Compact string**: `"tool:model:profile:role"` — 4 colon-separated parts.

| Input | Output ActorIdentity |
|-------|---------------------|
| `"claude:opus-4:implementer:implementer"` | `(tool="claude", model="opus-4", profile="implementer", role="implementer")` |
| `"claude:opus-4"` | `(tool="claude", model="opus-4", profile="unknown", role="unknown")` |
| `"claude"` | `(tool="claude", model="unknown", profile="unknown", role="unknown")` |
| `""` | Error: empty identity not allowed |

**Dict format** (JSONL / frontmatter):
```json
{"tool": "claude", "model": "opus-4", "profile": "implementer", "role": "implementer"}
```

**Legacy string** (backwards compat): `"claude-opus"` → `from_legacy("claude-opus")` → `(tool="claude-opus", model="unknown", profile="unknown", role="unknown")`

---

## Contract 2: parse_agent_identity() CLI Parser

```python
def parse_agent_identity(
    agent: str | None,
    tool: str | None,
    model: str | None,
    profile: str | None,
    role: str | None,
) -> ActorIdentity | None:
    """Parse CLI flags into ActorIdentity.

    Preconditions:
        - `agent` and individual flags (tool/model/profile/role) are MUTUALLY EXCLUSIVE
        - If both provided: raise typer.BadParameter with actionable message

    Postconditions:
        - Returns ActorIdentity if any flag provided, None if all are None
        - All fields in returned ActorIdentity are non-empty strings
    """
```

---

## Contract 3: resolve_references_transitively()

```python
def resolve_references_transitively(
    directive_ids: list[str],
    doctrine_service: DoctrineService,
) -> ResolvedReferenceGraph:
    """Resolve directive references transitively.

    Preconditions:
        - directive_ids is a non-empty list of valid directive ID strings
        - doctrine_service is fully initialised with accessible repositories

    Postconditions:
        - All directives in directive_ids appear in result.directives
        - result.tactics contains ALL tactics referenced by any resolved directive
        - result.styleguides/toolguides contain ALL guides referenced by any tactic
        - result.unresolved contains (type, id) pairs for missing artifacts
        - No infinite loops (cycle detection via visited set)
        - Resolution order is depth-first (directive → its tactics → their guides)

    Invariant:
        - len(result.unresolved) == 0 when all references exist in repositories
    """
```

---

## Contract 4: resolve_governance_for_profile()

```python
def resolve_governance_for_profile(
    profile_id: str,
    role: str | None,
    doctrine_service: DoctrineService,
    interview: ConstitutionInterview,
) -> GovernanceResolution:
    """Compile governance resolution for a specific agent profile.

    Preconditions:
        - profile_id exists in doctrine_service.agent_profiles
        - doctrine_service is fully initialised

    Postconditions:
        - result.directives is the union of profile directives and interview.selected_directives
        - result.tactics, styleguides, toolguides are transitively resolved from directives
        - result.profile_id == profile_id
        - result.role == role (or None)
        - Profile directives appear before interview directives in result.directives

    Error handling:
        - Profile not found: raise ValueError with profile_id
        - Missing referenced directive: recorded in diagnostics, not fatal
    """
```

---

## Contract 5: StatusEvent Backwards Compatibility

**Invariant**: Any JSONL file written by spec-kitty ≤ 0.x (bare-string actor) MUST be readable by spec-kitty with this feature.

**Read contract**:
```python
# Old format (string actor)
{"actor": "claude", ...}
# → StatusEvent(actor=ActorIdentity(tool="claude", model="unknown", profile="unknown", role="unknown"))

# New format (structured actor)
{"actor": {"tool": "claude", "model": "opus-4", "profile": "impl", "role": "impl"}, ...}
# → StatusEvent(actor=ActorIdentity(tool="claude", model="opus-4", profile="impl", role="impl"))
```

**Write contract**: New events ALWAYS write structured dict format.
