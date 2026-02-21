# Quickstart: Constitution Parser and Structured Config

**Feature**: 045-constitution-doctrine-config-sync

## What This Feature Does

Converts the constitution narrative markdown into machine-readable YAML config files that the governance system (Feature 044) can evaluate at lifecycle hooks.

## After Implementation

### Sync constitution to structured config

```bash
# Explicit sync (parses constitution.md → YAML files)
spec-kitty constitution sync

# Check sync status (stale detection)
spec-kitty constitution status
```

### Output files

```
.kittify/constitution/
├── constitution.md          # Human-readable (moved from .kittify/memory/)
├── governance.yaml          # Testing, quality, performance rules
├── agents.yaml              # Agent profiles and selection config
├── directives.yaml          # Numbered cross-cutting constraints
└── metadata.yaml            # Extraction metadata + content hash
```

### Automatic sync

After `/spec-kitty.constitution` or `/spec-kitty.bootstrap`, extraction runs automatically via a post-save hook. For manual edits, run `spec-kitty constitution sync` or configure CI to trigger on constitution changes.

### Staleness detection

```bash
$ spec-kitty constitution status
Constitution: .kittify/constitution/constitution.md
Status: STALE (modified since last sync)
Last sync: 2026-02-15T21:00:00+00:00
Hash mismatch: expected sha256:abc123... got sha256:def456...
Run: spec-kitty constitution sync
```

### Governance integration (Feature 044)

Governance hooks load structured YAML directly — no AI invocation at hook time:

```python
from specify_cli.constitution import load_governance_config

config = load_governance_config(repo_root)
# config.testing.min_coverage → 90
# config.testing.tdd_required → True
# config.quality.pr_approvals → 1
```

## Migration from Previous Versions

Run `spec-kitty upgrade` to automatically:
1. Move `constitution.md` to `.kittify/constitution/`
2. Run initial extraction
3. Update dashboard API path
