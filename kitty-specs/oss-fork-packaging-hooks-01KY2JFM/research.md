# Research: OSS Fork Packaging Hooks

## Decision: Shared `specify_cli.distribution` package owns resolvers

**Rationale**: Session-presence, `version_utils`, compat planner/remediation, and the version banner all need the same package-name and provider resolution. Owning resolvers under `session_presence/` (as sibling WIP does) creates an inverted dependency (compat → session_presence) and duplicates homes when Phase 2 lands.

**Alternatives considered**:
- Keep resolvers in `session_presence/upgrade_provider.py` — rejected (layering).
- Put resolvers in `compat/` — rejected (`version_utils` / banner would import compat for identity).

## Decision: Reuse `LatestVersionProvider` protocol; do not invent a second one

**Rationale**: Spec FR assumes zero-arg constructible providers with non-raising `get_latest`. Existing protocol + `LatestVersionResult` already encode this; stock `PyPIProvider` remains the fallback.

**Alternatives considered**:
- New async provider API — rejected (call sites are sync).
- Callable-only entry points without protocol — rejected (harder to test/type).

## Decision: `LatestVersionResult.source` gains `"simple_index"` (or equivalent)

**Rationale**: Mapping private-index success to `"pypi"` would mislabel telemetry/debug. Extending the Literal is a narrow, testable change. Error tokens stay the fixed vocabulary.

**Alternatives considered**:
- Keep `source="pypi"` for all successful HTTP lookups — rejected (dishonest for private index).
- Separate result type for simple index — rejected (call-site churn).

## Decision: Multi-provider selection — env disambiguation, else deterministic first

**Rationale**: Align with sibling WIP: `SPEC_KITTY_UPGRADE_PROVIDER=<name>` when multiple registered; else sorted-by-name first; never invent unregistered names; load failures fall back to `PyPIProvider`.

**Alternatives considered**:
- Fail hard if multiple and env unset — rejected (breaks accidental dual registration in editable+wheel).
- Require exactly one always — rejected (FR-004 allows multi + env).

## Decision: CHK028 length → 512 (shared constant)

**Rationale**: Index URL flags push remediation strings past 128. Spec allows 512 or dynamic length; fixed 512 is simpler and keeps character class unchanged (`[A-Za-z0-9 .\-+_/=:]`).

**Alternatives considered**:
- Dynamic max(len(composed), 128) — more complex, little security gain.
- Allow `?&=` in character class — broader attack surface for display strings; avoid unless required.

## Decision: Supersede sibling mission `pluggable-upgrade-check-provider-01KXZDMC` for this scope

**Rationale**: Coord worktree already contains a working `resolve_upgrade_provider` prototype. Port the resolution algorithm into `distribution/upgrade_provider.py`, wire call sites here, and treat the sibling as abandoned/superseded rather than landing two overlapping features.

**Alternatives considered**:
- Finish sibling first then add profile mission — rejected (user asked for all three phases in one mission).
- Duplicate code temporarily — rejected (canonical-source principle).

## Decision: Profile resolution precedence

**Rationale**:
1. If `spec_kitty.distribution_profile` registers a profile object → use it.
2. Else synthesize a minimal profile from `cli_package` + `upgrade_provider` resolvers (Phase 1 aliases).
3. Else stock defaults (`package_name="spec-kitty-cli"`, public PyPI provider, notifier enabled, no index URLs, default freshness).

**Alternatives considered**:
- Profile-only (drop Phase 1 groups) — rejected (FR-017).
- Merge all groups into one required profile — rejected (raises packager bar for session-presence-only forks).

## Open questions resolved by operator signal

User requested automatic progression with confirmed Intent Summary covering all three phases and feature-branch PR path — no remaining product NEEDS CLARIFICATION markers.
