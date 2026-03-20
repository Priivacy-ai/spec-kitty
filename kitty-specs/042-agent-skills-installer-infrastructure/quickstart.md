# Quickstart: Agent Skills Installer Infrastructure

**Feature**: 042-agent-skills-installer-infrastructure

## What Changed

`spec-kitty init` now creates skill root directories alongside the existing wrapper files. A managed manifest tracks everything Spec Kitty installed, enabling future sync, repair, and upgrade operations.

## New CLI Flag

```bash
spec-kitty init --ai claude,codex,opencode --skills auto
```

`--skills` controls skill distribution mode:

| Mode | Behavior |
|------|----------|
| `auto` (default) | Shared root + native roots where required + wrappers |
| `native` | Vendor-native roots for all skill-capable agents + wrappers |
| `shared` | Shared root wherever possible, native fallback + wrappers |
| `wrappers-only` | Pre-Phase-0 behavior: wrappers only, no skill roots |

## What Gets Created

For `spec-kitty init --ai claude,codex,opencode`:

```
project/
├── .agents/
│   └── skills/
│       └── .gitkeep              # Shared root (Codex + OpenCode)
├── .claude/
│   ├── commands/                  # Wrappers (unchanged)
│   │   └── spec-kitty.*.md
│   └── skills/
│       └── .gitkeep              # Native root (Claude)
├── .codex/
│   └── prompts/                   # Wrappers (unchanged)
│       └── spec-kitty.*.prompt.md
├── .opencode/
│   └── command/                   # Wrappers (unchanged)
│       └── spec-kitty.*.md
└── .kittify/
    └── agent-surfaces/
        └── skills-manifest.yaml   # Managed manifest
```

## Manifest

The manifest at `.kittify/agent-surfaces/skills-manifest.yaml` records:
- Which agents were selected
- Which skill roots were created
- Which wrapper files are managed (with content hashes)
- The skills mode used

## Verification

Init runs a post-install verification check. If anything is wrong, you see actionable errors:

```
✓ All selected agents have managed roots
✓ Skill root directories exist
✓ Wrapper counts match
✓ No duplicate skill names in overlapping roots
```

## Sync and Repair

```bash
# Repair missing skill roots and wrappers
spec-kitty agent config sync --create-missing

# Remove orphaned agent directories
spec-kitty agent config sync --remove-orphaned
```

Sync now reads the manifest to know which skill roots to repair and which are orphaned.

## Backward Compatibility

- `--skills wrappers-only` preserves exact pre-Phase-0 behavior
- All existing wrapper files are generated identically
- Projects that don't upgrade continue to work as before
- The upgrade migration adds manifest and skill roots non-destructively

## For Developers

New internal API:

```python
from specify_cli.core.agent_surface import (
    AGENT_SURFACE_CONFIG,    # Canonical registry (12 entries)
    get_agent_surface,       # Get one agent's full profile
    DistributionClass,       # Enum: shared-root-capable, native-root-required, wrapper-only
)

surface = get_agent_surface("claude")
assert surface.distribution_class == DistributionClass.NATIVE_ROOT_REQUIRED
assert surface.skill_roots == (".claude/skills/",)
assert surface.wrapper.dir == ".claude/commands"
```

Old imports still work (derived from canonical source):

```python
from specify_cli.core.config import AGENT_COMMAND_CONFIG  # still works, derived view
from specify_cli.agent_utils.directories import AGENT_DIRS  # still works, derived view
```
