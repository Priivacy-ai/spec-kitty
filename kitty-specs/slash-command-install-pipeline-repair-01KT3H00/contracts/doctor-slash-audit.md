# Contract: Doctor Slash-Command Audit

**Module**: `src/specify_cli/cli/commands/doctor.py`  
**Subcommand**: `doctor skills`

## Scope

Operates on: `set(config.available) ∩ set(AGENT_COMMAND_CONFIG.keys())`  
Explicitly excludes: agents in `SUPPORTED_AGENTS` (codex/vibe/pi/letta) — those are handled by the existing Agent Skills audit path.

## Read-only check output

For each agent in scope:
- Call `get_global_command_dir(agent_key)` to get the install directory
- For each command in `PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS`:
  - Compute expected filename via `_compute_output_filename(command, agent_key)`
  - Report `missing` if file absent
  - Report `stale` if version marker in file head does not match current CLI version
  - Report `ok` otherwise
- Aggregate into a `SlashCommandAuditResult` dataclass

## Healthy condition

`doctor skills` reports overall healthy only when:
1. Existing Agent Skills audit passes (unchanged behaviour), AND
2. All configured slash-command agents have all canonical commands present and current

## `--fix` behaviour

1. Call `ensure_global_agent_commands()` with `agent_keys=<configured slash-command agents>`
2. Re-run read-only check
3. Report repaired files

## Scope guard (non-negotiable)

- Never create directories for agents not in `config.available`
- Never install files for agents not in `AGENT_COMMAND_CONFIG`
- Never delete files outside the canonical `spec-kitty.*` filename pattern

## Idempotency

Running `doctor skills --fix` twice must produce identical filesystem state. No file is written if the existing content matches what would be written.
