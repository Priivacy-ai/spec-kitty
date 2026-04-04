# Historical Terms and Mappings

| Historical term | Current term | Applicable to | Notes |
|---|---|---|---|
| AI agent tooling (runtime executable) | Tool | `1.x`, `2.x` | Use "tool" for concrete products such as Claude Code/Codex/opencode. |
| Agent identity/profile language | Agent | `1.x`, `2.x` | Use "agent" for logical collaborator identity and role. |
| Mission as reusable blueprint | Mission Type | `1.x`, `2.x` | Plain `mission` is no longer canonical for the reusable blueprint layer. |
| Feature as generic tracked-item noun | Mission | `1.x`, `2.x` | `Feature` remains a software-dev compatibility alias only. |
| Feature as runtime primary identity | Mission Run (runtime), Mission (tracked item), Feature (compatibility alias) | `1.x`, `2.x` | `mission_run_id` is reserved for runtime/session identity; tracked-item identity moves toward `mission_slug`. |
| Workflow as primary domain object | Mission Type / Mission Action / Procedure | `1.x`, `2.x` | Keep `workflow` as umbrella prose only. |
| Ad-hoc term definitions in prompts | Canonical glossary entries + append-only events | `1.x`, `2.x` | Preserve decisions and replay history. |
