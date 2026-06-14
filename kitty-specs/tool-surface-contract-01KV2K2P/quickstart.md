# Quickstart: ToolSurfaceContract -- Unified Tool Surface Registry

**Mission**: tool-surface-contract-01KV2K2P

## For implementers (Claude)

This mission is implemented as 9 sequential work packages, each corresponding to a child GitHub issue. Do not start a work package until its predecessors have merged.

### Mandatory sequence

```
WP01 (#1936) Registry skeleton        --> must merge before WP02
WP02 (#1944) Migration compat gate    --> must merge before WP03-WP09
WP03 (#1937) Command-skill provider   --> first user-visible feature
WP04 (#1938) Session-presence provider
WP05 (#1939) Doctrine-skill provider
WP06 (#1940) Native agent profile projection
WP07 (#1941) Legacy agent config refactor
WP08 (#1942) Docs contract lint
WP09 (#1943) Plugin bundle projection and validation
```

### For each work package

1. Read the child issue (#1936 etc.) for acceptance criteria.
2. Implement in `src/specify_cli/tool_surface/` (new bounded context only -- no changes to `core.config`, `agent.config`, or `doctor.py` internals).
3. Run migration compat fixtures (from WP02 onward): `pytest tests/specify_cli/tool_surface/integration/test_migration_compat.py tests/specify_cli/tool_surface/integration/test_agent_config_compat.py`
4. Run full test suite: `pytest tests/`
5. Check type safety: `.venv/bin/mypy --strict src/specify_cli/tool_surface/`
6. Check complexity: `.venv/bin/ruff check src/specify_cli/tool_surface/`
7. Submit PR for Codex review. Codex reviews for: glossary compliance, source/generated/manifest ownership, backward compatibility, stable finding codes, repair safety, focused tests.

### Key invariants to preserve

- `doctor skills --json` output must not change -- run `test_migration_compat.py` after every WP.
- `spec-kitty agent config list/status/sync` external behavior must not change.
- All new code in `src/specify_cli/tool_surface/` must pass `mypy --strict`.
- Finding codes, once introduced in any WP, are stable forever (no renames without deprecation).

### For Codex (reviewer)

Review each PR for:
- Glossary compliance: Tool vs. Agent vs. Tool Surface vs. ToolSurfaceContract naming
- Source/generated/manifest ownership: registry = policy, manifests = state
- Backward compatibility: migration compat fixtures pass
- Stable finding codes: no renamed or removed codes
- Repair safety: repair commands are runnable without manual file editing
- Focused tests: new branches and helpers have direct test coverage
- No accidental conflation of tool runtimes with agent profiles

## Using `doctor tool-surfaces` (after WP03 merges)

```bash
# Full report for all configured tools
spec-kitty doctor tool-surfaces --json

# Filter by surface kind
spec-kitty doctor tool-surfaces --kind command-skill --json

# Filter by tool
spec-kitty doctor tool-surfaces --tool codex --json

# Fix repairable findings
spec-kitty doctor tool-surfaces --fix
spec-kitty doctor tool-surfaces --kind command-skill --fix
```

## Key files

| File | Purpose |
|------|---------|
| `src/specify_cli/tool_surface/registry.py` | Policy registry -- what should exist |
| `src/specify_cli/tool_surface/plan.py` | Computes SurfacePlan for configured tools |
| `src/specify_cli/tool_surface/status.py` | Probes actual state vs. plan |
| `src/specify_cli/tool_surface/findings.py` | Stable finding codes |
| `src/specify_cli/tool_surface/repair.py` | Executes repair for a finding |
| `.kittify/command-skills-manifest.json` | Command-skill install state (not policy) |
| `.kittify/skills-manifest.json` | Doctrine-skill install state (not policy) |
| `.kittify/tool-surface-profile-manifest.json` | Native agent profile install state (new, WP06) |
| `kitty-specs/tool-surface-contract-01KV2K2P/contracts/doctor-tool-surfaces-output.schema.json` | JSON Schema for doctor output |
