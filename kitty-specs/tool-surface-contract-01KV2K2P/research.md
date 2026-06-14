# Research: ToolSurfaceContract -- Unified Tool Surface Registry

**Mission**: tool-surface-contract-01KV2K2P
**Date**: 2026-06-14
**Sources**: Research gist (tool-surface-contract-research.md), Architecture gist (tool-surface-contract-architecture.md), live issue cluster (#1780, #702, #1670, #1945)

## Decision 1: Registry-as-Policy Pattern

**Decision**: Introduce a `ToolSurfaceRegistry` that owns surface definitions (policy) separately from manifests (installation state). The registry answers "what should exist"; manifests answer "what is installed".

**Rationale**: The comparative market analysis (13 systems) shows that the best-practice pattern is always: define a typed contract -> generate native artifacts from that contract -> track installed files in a manifest -> expose machine-readable status. Spec Kitty currently conflates policy and state, causing impossible states after fresh clone. Spec Kit's integration registry is the closest production implementation and validates this separation.

**Alternatives considered**:
- Extending each subsystem to coordinate with the others: rejected because it perpetuates the fragmented state and requires every new subsystem to know about all others.
- Consolidating into a single flat manifest: rejected because manifests are install-state snapshots; they cannot answer "is this tool configured to have command skills?" without recomputing policy.

## Decision 2: Provider Wrapping (Not Rewriting)

**Decision**: Existing installers (`command_installer`, `skills/installer`, `skills/verifier`, `session_presence/writers`) are wrapped as `SurfaceProvider` adapters. Their core logic -- ref-counts, hash checks, shared-root safety, multi-install guards -- is preserved intact.

**Rationale**: The shared-root safety invariant in `command_installer` prevents corrupt installs when multiple tools share `.agents/skills/`. Rewriting that logic from scratch introduces regression risk. Provider wrapping is the lowest-risk path and is consistent with BMAD's installer architecture (sparse overrides over generated files).

**Alternatives considered**:
- Full rewrite of installers: rejected due to high regression risk for current users.
- Leaving installers unwrapped and calling them directly from doctor: rejected because it prevents unified status reporting and stable finding codes.

## Decision 3: Finding Code Stability Contract

**Decision**: All finding codes in `doctor tool-surfaces --json` output are stable machine-readable kebab-case strings (e.g., `"generated-surface-missing"`, `"managed-file-drift"`). They are not renamed or removed without a documented deprecation cycle (minimum one minor version warning period). Python constants in `findings.py` may use SCREAMING_SNAKE names (e.g., `GENERATED_SURFACE_MISSING`) but the string VALUES must always be kebab-case; uppercase codes must never appear in JSON output.

**Rationale**: CI pipelines gate on specific codes. Unstable codes silently break pipelines in ways that are hard to detect. The comparative analysis showed this is a common failure mode (BMAD #2442: stale manifest path breaks whole plugin load). Finding codes are a public API contract.

**Alternatives considered**:
- Human-readable-only output: rejected because it cannot be reliably machine-parsed across versions.
- Numeric error codes: rejected in favor of descriptive string constants that are self-documenting.

## Decision 4: Migration Gate Ordering

**Decision**: IC-02 (migration/compatibility) is placed immediately after IC-01 (registry skeleton), before any user-visible provider work. The migration fixtures from IC-02 act as a gate: no provider IC may merge if those fixtures fail.

**Rationale**: Introducing providers that route through the new registry risks changing `doctor skills --json` or `agent config` output. By establishing the compatibility fixtures first, any regression is caught immediately when a provider PR is opened. This is consistent with C-008 (prescribed implementation order).

**Alternatives considered**:
- Add migration fixtures at the end: rejected because it delays protection and allows regressions to accumulate across multiple PRs.
- No migration fixtures: rejected because `doctor skills --json` is consumed by documented external tooling and its schema is a backward-compatibility guarantee.

## Decision 5: Plugin Bundle Scope

**Decision**: Plugin bundle work (IC-09) is limited to projection (generating the native plugin package layout from canonical surfaces) and pre-publish validation (checking that all required surfaces are present and correctly formatted). No auto-install, no marketplace push, no project-local installation replacement.

**Rationale**: Auto-install has security implications (trust, version control, audit trail). Marketplace push is a release engineering concern separate from the contract definition. Scope is bounded to ensure this mission is completable without platform-specific distribution infrastructure. Plugin distribution is a separate future mission.

**Alternatives considered**:
- Full plugin distribution pipeline: deferred to a future mission after the contract and projection machinery is proven stable.
- No plugin bundle work: rejected because the bundle validation use case is needed to validate that the contract is complete and correctly structured.

## Decision 6: Native Agent Profile Projection

**Decision**: Spec Kitty agent profiles (built-in, org overlay, project overlay) are projected into host-native agent/subagent formats for each configured tool that supports named agents. Tools that do not support named agents natively receive a `RESEARCH_GAP` finding code rather than a hard failure.

**Rationale**: Users currently cannot select "Architect Alphonso" in Claude Code's native agent picker because no projection exists. The `AgentProfileRepository` already resolves the profile graph; this IC adds the render + manifest + doctor layer. The `RESEARCH_GAP` code prevents spurious failures for harnesses without native agent support.

**Alternatives considered**:
- Require users to manually configure native agents: rejected as poor UX and inconsistent with Spec Kitty's install-once model.
- Hard failure for tools without native agent support: rejected because it would block `doctor tool-surfaces` on tools where this feature is not applicable.

## Decision 7: Glossary Compliance

**Decision**: PR #1935 terminology is non-negotiable. `ToolSurfaceContract`, not `AgentSurfaceContract`. All new identifiers, doc sections, CLI output, and finding codes must use the glossary-compliant vocabulary (Tool, Agent, Tool Surface as distinct concepts).

**Rationale**: The existing naming drift (`agents.available`, `AGENT_DIRS`, `VALID_AGENTS`, `SUPPORTED_AGENTS`) has already caused conceptual confusion (skills vs agents, install vs profile). Introducing new identifiers with the wrong vocabulary extends the drift. IC-01 is the right moment to establish the canonical naming for the bounded context.

**Alternatives considered**:
- Use `AgentSurfaceContract` for backward-naming compatibility: rejected because it propagates the incorrect Tool/Agent conflation.
- Introduce gradual renaming over multiple ICs: rejected because inconsistent naming within one bounded context is worse than a clean break at introduction.

## Research Gaps

The following areas have open research questions that are out of scope for this mission and should be tracked in separate issues:

1. **Tool harness CLI detection**: The registry needs to know whether a tool's CLI is installed to determine which surfaces are active. The existing `check_tool_for_tracker` pattern is sufficient for now, but a unified tool-presence probe belongs in a future mission.
2. **Cross-tool skill namespace conflicts**: Multiple tools sharing `.agents/skills/` creates naming collision risk when two tools have different skill count expectations for the same path. The existing ref-count mechanism in `command_installer` handles this, but a formal conflict-detection model is deferred.
3. **AgentSkills trust/provenance**: The research found open issues in the AgentSkills standard around version locking and trust/provenance (agentskills/agentskills#418, #46). These are not in scope for this mission but should be tracked for the plugin distribution mission.
