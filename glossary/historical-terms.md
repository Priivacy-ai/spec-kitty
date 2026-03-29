# Historical Terms and Mappings

| Historical term | Current term | Applicable to | Notes |
|---|---|---|---|
| AI agent tooling (runtime executable) | Tool | `1.x`, `2.x` | Use "tool" for concrete products such as Claude Code/Codex/opencode. |
| Agent identity/profile language | Agent | `1.x`, `2.x` | Use "agent" for logical collaborator identity and role. |
| Feature as runtime primary identity | Mission | `1.x`, `2.x` | All user-facing surfaces now use "Mission." Backward-compat shims (`--feature`, `SPECIFY_FEATURE`, `agent feature` alias) removed in 2.x. |
| Ad-hoc term definitions in prompts | Canonical glossary entries + append-only events | `1.x`, `2.x` | Preserve decisions and replay history. |
| `--feature` (CLI flag) | `--mission` | `2.x` | Removed. The `--feature` flag and `SPECIFY_FEATURE` env var no longer exist. Use `--mission` and `SPECIFY_MISSION`. |
