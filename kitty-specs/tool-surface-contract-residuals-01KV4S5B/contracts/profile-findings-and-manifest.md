# Contract — Agent-Profile Finding Codes & Manifest Provenance

Pins the observable contract this mission must satisfy for #1940. Source of truth for names: `kitty-specs/tool-surface-contract-01KV2K2P/data-model.md` (canonical) — reproduced here as the acceptance contract.

## `doctor tool-surfaces --kind agent-profile --json` finding-code contract

Output shape (unchanged from #1948 `SurfaceFinding`):
```json
{ "code": "<kebab-case>", "tool_key": "<str|null>", "surface_id": "<str|null>",
  "severity": "error|warning|info", "repair_command": "<str|null>", "message": "<str>" }
```

The provider MUST be able to emit each of these (in addition to the 3 already shipped):

| code | severity | triggering condition (acceptance) |
|------|----------|-----------------------------------|
| `profile-source-invalid` | error | canonical profile YAML fails schema / `AgentProfileRepository` validation |
| `profile-name-invalid` | error | profile id/name illegal for the target native format |
| `profile-overlay-conflict` | error | overlay resolution ambiguous/unsafe across layers |
| `profile-sentinel-skipped` | info | sentinel/internal profile intentionally not projected (recorded) |

Stability: codes are append-only; the 3 existing codes (`native-agent-profile-missing`, `native-agent-profile-drift`, `profile-projection-unsupported`) are NOT renamed.

## `.kittify/agent-profiles-manifest.json` entry schema (8 fields)

```json
{
  "profile_urn": "urn:profile:architect-alphonso",
  "source_layer": "built-in",
  "tool_key": "claude",
  "output_path": ".claude/agents/architect-alphonso.md",
  "format": "claude-agent",
  "file_hash": "sha256:…",
  "source_path": "src/doctrine/agent_profiles/built-in/architect-alphonso.agent.yaml",
  "source_hash": "sha256:…",
  "projection_version": 1
}
```

Round-trip / read-compat contract (`formalized-constraint-testing`):
- `load(save(entry)) == entry` for an 8-field entry.
- `load(<6-field legacy entry>)` succeeds; the 3 new fields are absent-tolerant on read and populated on the next projection write.
- `source_hash` change vs `file_hash` change are independently detectable.

## Backward-compatibility contract (NFR-001) — unchanged surfaces

- `doctor skills --json` schema: byte/contract-identical (frozen baseline test stays green).
- `agent config list/status/sync` text + exit codes: byte-identical (`test_agent_config_compat.py`).
