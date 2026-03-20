# Internal API Contract: Agent Surface

**Module**: `src/specify_cli/core/agent_surface.py`

## Public Functions

### `get_agent_surface(agent_key: str) -> AgentSurface`

Returns the full capability profile for one agent.

- **Input**: Agent key string (must be in `AGENT_SURFACE_CONFIG`)
- **Output**: `AgentSurface` dataclass instance
- **Raises**: `KeyError` if agent_key not found
- **Side effects**: None (pure lookup)

### `get_agent_command_config() -> dict[str, dict[str, str]]`

Returns a dict identical in shape and values to the legacy `AGENT_COMMAND_CONFIG`.

- **Output**: `{"claude": {"dir": ".claude/commands", "ext": "md", "arg_format": "$ARGUMENTS"}, ...}`
- **Invariant**: Output must be byte-identical when serialized to the old hardcoded dict for all 12 agents.

### `get_agent_dirs() -> list[tuple[str, str]]`

Returns a list identical in shape and values to the legacy `AGENT_DIRS`.

- **Output**: `[(".claude", "commands"), (".github", "prompts"), ...]`
- **Invariant**: Order must match the order entries appear in `AGENT_SURFACE_CONFIG`.

### `get_agent_dir_to_key() -> dict[str, str]`

Returns a dict identical in shape and values to the legacy `AGENT_DIR_TO_KEY`.

- **Output**: `{".claude": "claude", ".github": "copilot", ...}`

## Public Constants

### `AGENT_SURFACE_CONFIG: dict[str, AgentSurface]`

The canonical agent registry. 12 entries. Hand-maintained. All other agent metadata is derived from this.

## Module: `src/specify_cli/skills/roots.py`

### `resolve_skill_roots(selected_agents: list[str], mode: str = "auto") -> list[str]`

Returns the minimum set of project skill root directory paths to create.

- **Input**: List of agent keys, distribution mode
- **Output**: Sorted list of unique directory paths (relative to project root)
- **Modes**:
  - `"auto"`: `.agents/skills/` if any shared-root-capable + native roots for native-required
  - `"native"`: Vendor-native roots for all skill-capable agents
  - `"shared"`: `.agents/skills/` wherever possible + native fallback
  - `"wrappers-only"`: Empty list
- **Side effects**: None (pure computation)

## Module: `src/specify_cli/skills/manifest.py`

### `write_manifest(project_root: Path, manifest: SkillsManifest) -> None`

Writes manifest to `.kittify/agent-surfaces/skills-manifest.yaml`.

### `load_manifest(project_root: Path) -> SkillsManifest | None`

Loads manifest from YAML. Returns None if file does not exist or is invalid.

### `compute_file_hash(file_path: Path) -> str`

Returns SHA-256 hex digest of file contents.

## Module: `src/specify_cli/skills/verification.py`

### `verify_installation(project_root: Path, selected_agents: list[str], manifest: SkillsManifest) -> VerificationResult`

Runs all verification checks. Returns structured result with errors and warnings.
