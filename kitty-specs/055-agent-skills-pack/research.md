# Research: Agent Skills Pack

**Feature**: 055-agent-skills-pack
**Date**: 2026-03-21

## R-1: Existing Skill Infrastructure on 2.x

**Decision**: Minimal skill infrastructure exists. Only `.claude/skills/release/SKILL.md` found as a manual artifact. No automated skill distribution, discovery, or manifest tracking.

**Rationale**: The codebase has full wrapper generation infrastructure (`generate_agent_assets()`, `AGENT_COMMAND_CONFIG`) but no parallel system for skills. This confirms the feature is greenfield for the distribution layer while leveraging existing patterns for architecture consistency.

**Alternatives considered**: Extending `FileManifest` (source-driven, wrong semantics) or `ExpectedArtifactManifest` (step-aware validation, wrong domain). Both rejected per user decision.

## R-2: Packaging and Distribution Path

**Decision**: `src/doctrine/` is already bundled via `also_copy` in `pyproject.toml`. No additional packaging configuration needed for skills placed under `src/doctrine/skills/`.

**Rationale**: The existing `also_copy = ["src/doctrine/"]` directive recursively copies the entire doctrine tree into the wheel. Skills placed under `src/doctrine/skills/` will be automatically included.

**Verification**: Confirmed by reading `pyproject.toml` line 301: `"src/doctrine/"`.

## R-3: Managed-File Manifest vs Existing Systems

**Decision**: Create a new dedicated `ManagedSkillManifest` in `src/specify_cli/skills/manifest.py`. Separate from:
- `FileManifest` (`src/specify_cli/manifest.py`) — source-driven file checking, no hash tracking
- `ExpectedArtifactManifest` (`src/specify_cli/dossier/manifest.py`) — mission step artifact validation
- `ProjectMetadata` (`src/specify_cli/upgrade/metadata.py`) — migration tracking only

**Rationale**: None of these systems track installed-file ownership with content hashes. The managed manifest needs: installed path, source hash, agent key, installation class, and timestamp. This is a different concern (installer ownership) from artifact validation (mission step requirements).

## R-4: Init Integration Strategy

**Decision**: Add skill installation as a new step after wrapper generation in the init flow, inside the existing `Live` progress tracker. Each agent's skill installation runs within the per-agent loop.

**Rationale**: The init flow processes agents sequentially in a loop (init.py ~693). Adding skill installation alongside wrapper generation keeps the flow simple and allows per-agent progress tracking. The manifest is written once after all agents are processed.

**Alternatives considered**: Separate post-init command (rejected — PRD requires init to distribute skills). Parallel installation (rejected — unnecessary complexity for < 2s budget).

## R-5: Content Hash Strategy

**Decision**: Use SHA-256 of file content for drift detection. Hash is computed at installation time and stored in the manifest.

**Rationale**: SHA-256 is sufficient for integrity checking, available in Python stdlib (`hashlib`), and deterministic across platforms. No need for more complex schemes (git object hashes, content-addressable storage).

## R-6: Shared Root Deduplication

**Decision**: For shared-root-capable agents, skills are installed once to `.agents/skills/` (the shared root). Vendor-native roots (e.g., `.gemini/skills/`) are not populated in the first slice to avoid duplication.

**Rationale**: The PRD states "use `.agents/skills/` when shared-root support is officially available" (section 9.2). Installing to both shared and native roots would create duplicate content. The shared root is the canonical location for shared-root-capable agents. Native roots can be added later if specific agents require it.

**Impact**: The capability matrix config stores all possible roots, but the installer uses only the first root (`.agents/skills/`) for shared-root-capable agents.
