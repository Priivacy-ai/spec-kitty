# Research: Agent Skills Installer Infrastructure

**Feature**: 042-agent-skills-installer-infrastructure
**Date**: 2026-03-20

## Research Questions

### RQ1: Current call-site footprint for AGENT_COMMAND_CONFIG and AGENT_DIRS

**Decision**: Use derived compatibility views (option C) — compute old structures from the new canonical source.

**Rationale**:
- `AGENT_COMMAND_CONFIG` has exactly 1 direct consumer in production code: `asset_generator.py` line 12/67. Tests also reference it.
- `AGENT_DIRS` has 15+ migration file consumers, all importing via `get_agent_dirs_for_project` from `m_0_9_1` or `directories.py`.
- `AGENT_DIR_TO_KEY` is consumed by `directories.py` internally and by `m_0_14_0`.
- Making old names derived views (computed at module load time) means zero call-site changes for migrations.
- Only `asset_generator.py` gets a direct update to use `get_agent_surface()` for cleaner access.

**Alternatives considered**:
- (A) Unify into single structure, rewrite all call sites: Too invasive for Phase 0, 15+ migration files touched.
- (B) Keep AGENT_DIRS as-is, only replace AGENT_COMMAND_CONFIG: Leaves two hand-maintained registries, defeats the purpose of unification.

### RQ2: Distribution class assignment accuracy

**Decision**: PRD section 8.1 matrix is the source of truth. All 12 agents verified against cited official documentation.

**Rationale**:
- 8 agents are shared-root-capable: Copilot, Gemini, Cursor, OpenCode, Windsurf, Codex, Augment, Roo — all officially document `.agents/skills/` support.
- 3 agents are native-root-required: Claude (`.claude/skills/`), Qwen (`.qwen/skills/`), Kilo Code (`.kilocode/skills/`) — do not document `.agents/skills/`.
- 1 agent is wrapper-only: Amazon Q — no first-class `SKILL.md` surface in current docs.
- Kiro explicitly excluded from Phase 0 per constraints.

**Alternatives considered**:
- Treating Claude as shared-root-capable (`.claude/skills/` could coexist with `.agents/skills/`): Rejected because Claude docs do not list `.agents/skills/` as a scanned root.

### RQ3: Manifest storage format and location

**Decision**: YAML at `.kittify/agent-surfaces/skills-manifest.yaml`.

**Rationale**:
- YAML is already the standard for Spec Kitty config files (`config.yaml`, `metadata.yaml`).
- `ruamel.yaml` is already a project dependency.
- `.kittify/agent-surfaces/` is a new subdirectory that cleanly namespaces skill/surface metadata.
- JSON was considered but YAML is more readable for human inspection and consistent with project conventions.

**Alternatives considered**:
- JSON at `.kittify/skills-manifest.json`: Inconsistent with project's YAML-first convention.
- Inside `config.yaml`: Would overload an already-used file with different lifecycle semantics (config is user-editable; manifest is tool-managed).

### RQ4: Hash algorithm for managed file tracking

**Decision**: SHA-256 via Python stdlib `hashlib.sha256`.

**Rationale**:
- No new dependencies.
- SHA-256 is collision-resistant for file integrity verification.
- Hash is used for drift detection (is this wrapper file still the one we generated?), not security, so SHA-256 is more than sufficient.
- Consistent with common manifest/lockfile practices (npm, pip, cargo).

### RQ5: .gitkeep vs alternative skill root markers

**Decision**: Use `.gitkeep` files in empty skill root directories.

**Rationale**:
- Git does not track empty directories. Without a marker, skill roots would vanish on clone.
- `.gitkeep` is a widely understood convention.
- The manifest tracks `.gitkeep` files as managed content, so sync can repair them.
- Alternative: `README.md` in each root — rejected because it adds noise and is not a managed Spec Kitty artifact.

### RQ6: Migration version numbering

**Decision**: `m_2_1_0_agent_surface_manifest.py` targeting version 2.1.0.

**Rationale**:
- Current CLI version is 2.0.9 (from `metadata.yaml`).
- This feature introduces new infrastructure worthy of a minor version bump.
- Follows existing migration naming convention: `m_{version}_{description}.py`.
- Version 2.1.0 leaves room for patch releases on 2.0.x if needed before this ships.
