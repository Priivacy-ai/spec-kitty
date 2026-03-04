# Historical Terms and Mappings

| Historical term | Current term | Applicable to | Notes |
|---|---|---|---|
| AI agent tooling (runtime executable) | Tool | `1.x`, `2.x` | Use "tool" for concrete products such as Claude Code/Codex/opencode. |
| Agent identity/profile language | Agent | `1.x`, `2.x` | Use "agent" for logical collaborator identity and role. |
| Feature as runtime primary identity | Mission Run (target), Feature (2.x compatibility) | `1.x`, `2.x` | 2.x still uses feature slugs heavily in artifacts; runtime identity work moves toward mission-run scoping. |
| Ad-hoc term definitions in prompts | Canonical glossary entries + append-only events | `1.x`, `2.x` | Preserve decisions and replay history. |
| `--feature` (CLI flag) | `--mission` | `2.x` | Deprecated in 2.2.0. Emits a deprecation warning when used. Removal planned in 3.0.0. See `glossary/contexts/orchestration.md#Feature`. |
