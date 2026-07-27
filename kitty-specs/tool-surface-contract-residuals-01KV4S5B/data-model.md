# Data Model — ToolSurfaceContract Residual Closeout

Deltas only; the canonical baseline lives in `kitty-specs/tool-surface-contract-01KV2K2P/data-model.md`. This mission implements the parts of that baseline that did not land in PR #1948.

## Finding codes (additions to `src/specify_cli/tool_surface/findings.py`)

The agent-profile provider currently emits 3 of the 7 canonical profile codes. Add the 4 missing ones (stable, kebab-case, append-only — do **not** rename existing codes):

| Code | Severity | Emit condition |
|------|----------|----------------|
| `profile-source-invalid` | error | Canonical profile YAML fails schema or `AgentProfileRepository` validation |
| `profile-name-invalid` | error | Profile ID/name is invalid for the target native format (e.g. illegal chars for a Claude `.claude/agents/<id>.md` filename) |
| `profile-overlay-conflict` | error | Org/project overlay profile resolution is ambiguous or unsafe (two layers claim the same id incompatibly) |
| `profile-sentinel-skipped` | info | A sentinel/internal profile is intentionally not projected (recorded, never silently dropped) |

Existing (unchanged): `native-agent-profile-missing`, `native-agent-profile-drift`, `profile-projection-unsupported`.

## ProfileManifest entry — provenance fields (`src/specify_cli/tool_surface/profiles/manifest.py`)

Extend the entry from 6 → 8 fields:

| Field | Status | Meaning |
|-------|--------|---------|
| `profile_urn` | existing | Canonical profile identity |
| `source_layer` | existing | Resolution layer (built-in / org / project) |
| `tool_key` | existing | Target tool |
| `output_path` | existing | Projected native file path |
| `format` | existing | Native format (`claude-agent`, `copilot-agent`, …) |
| `file_hash` | existing | Hash of the projected output |
| **`source_path`** | **NEW** | Path to the canonical source YAML the projection derives from |
| **`source_hash`** | **NEW** | Hash of the canonical source YAML (detects upstream profile change) |
| **`projection_version`** | **NEW** | Projection-format version (enables future re-projection migrations) |

**Invariants**:
- A projected native file is traceable to its canonical source via (`source_path`, `source_hash`).
- `source_hash` drift (source changed) is distinct from `file_hash` drift (output edited) — both feed `native-agent-profile-drift` but the manifest records which.
- **Backward read-compat**: loader MUST accept pre-existing 6-field entries (the 3 new fields default/optional on read; populated on next projection). No crash on an old `.kittify/agent-profiles-manifest.json`.

## Registry-backed agent sets (`src/specify_cli/cli/commands/agent/config.py`)

| Symbol | Before | After |
|--------|--------|-------|
| `SKILL_ONLY_AGENTS` | hardcoded `{"codex","vibe","pi","letta"}` | derived from `command_installer.SUPPORTED_AGENTS` (single source) |
| `VALID_AGENTS` | `set(AGENT_DIR_TO_KEY.values()) \| SKILL_ONLY_AGENTS` | unchanged shape, now transitively registry-backed |

**Invariant**: the *set of accepted/rejected tool keys* is byte-identical before/after (pinned by `test_agent_config_compat.py`).

## `locate_project_root` resolution (`src/specify_cli/core/paths.py`)

| Input | Before | After |
|-------|--------|-------|
| `SPECIFY_REPO_ROOT` set, path exists, has `.kittify/` | returns it (Tier 1) | returns it (unchanged) |
| `SPECIFY_REPO_ROOT` set, path exists, **no** `.kittify/` | **falls through** → ambient discovery (the #1965 leak) | **returns it** (override authoritative) |
| `SPECIFY_REPO_ROOT` set, path does **not** exist | falls through | falls through (unchanged — `env_path.exists()` guard kept) |
| `SPECIFY_REPO_ROOT` unset | Tier-2 walk-up / `.kittify` search | unchanged |

**Invariant (C-003)**: real `.kittify/` projects are unaffected (same Tier-1 branch). Only an explicitly-set, existing, non-`.kittify` path changes from silently-ignored to honored.
