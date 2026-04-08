# Research: Init Command Overhaul (076)

## Pre-Planning Code Investigation

All questions resolved via direct codebase inspection. No external research needed.

---

### R-001: Version Marker Format (Migration B safety invariant)

**Question:** What header marks a spec-kitty-generated command file?

**Finding:** `<!-- spec-kitty-command-version: X.Y.Z -->` is written as line 1 of every generated command file by `shims/generator.py:101`:
```python
f"<!-- spec-kitty-command-version: {version} -->\n"
```
Also used in `m_2_1_4_enforce_command_file_state.py:39` as `_VERSION_MARKER_PREFIX = "<!-- spec-kitty-command-version:"`.

**Decision:** Migration B safety check: a file is spec-kitty-generated if and only if its first line starts with `<!-- spec-kitty-command-version:`.

---

### R-002: Migration B Already Exists

**Question:** Does a migration exist to remove per-project command files?

**Finding:** `src/specify_cli/upgrade/migrations/m_3_1_2_globalize_commands.py` — already removes all `spec-kitty.*` files from per-project agent dirs. However it is **missing all four safety invariants** from FR-021 through FR-023:

1. Does NOT check global runtime is present before deleting
2. Does NOT check global agent commands are present for the specific agent
3. Does NOT verify the version marker header before deleting
4. Does NOT emit per-agent skip warnings when invariants fail

**Decision:** WP04 hardens `m_3_1_2_globalize_commands.py` in-place rather than creating a new migration. This is safer (idempotent re-run) and avoids a second migration doing overlapping work.

---

### R-003: Latest Migration Version for New Migrations

**Finding:** Latest migration file is `m_3_2_0_update_planning_templates.py`. New migrations should use version prefix `3.2.1` (Migration A: strip selection keys).

---

### R-004: `ensure_runtime()` Error Handling

**Finding:** `init.py:1107` catches all exceptions from `ensure_runtime()` and logs them as debug only — init continues silently even if global runtime bootstrap fails. This violates FR-003 which requires failure to surface explicitly.

**Decision:** The exception catch block must be replaced with explicit error surfacing (rich console error + `raise typer.Exit(1)`) for any exception from `ensure_runtime()`.

---

### R-005: `AgentSelectionConfig` Usage Across Codebase

**Finding:** `select_implementer()` and `select_reviewer()` are defined in `agent_config.py` and called **nowhere** in the codebase. `AgentSelectionConfig` is only referenced in `agent_config.py` itself and `init.py`. The `agent config` CLI command (`cli/commands/agent/config.py`) does not expose or read the `selection` fields. No migration, no runtime command, no test fixture exercises these methods.

**Decision:** `AgentSelectionConfig` dataclass, `select_implementer()`, `select_reviewer()`, and all `selection` serialization can be removed with zero runtime impact. A cleanup migration strips orphaned keys from existing `config.yaml` files.

---

### R-006: Global Command Infrastructure

**Finding:** `ensure_global_agent_commands()` (referenced in `m_3_1_2` docstring) installs commands globally at CLI startup. Global commands live in `~/.{agent}/commands/` or equivalent. The migration at 3.1.2 assumes this infrastructure is already present. Our hardening adds an explicit pre-flight check confirming global commands exist before removing local copies.

---

### R-007: Test Files to Delete or Update

| File | Action |
|------|--------|
| `tests/specify_cli/cli/commands/test_init_doctrine.py` | **Delete** — tests `_run_doctrine_stack_init`, `_run_inline_interview` |
| `tests/agent/test_agent_config_unit.py` | **Update** — remove `preferred_implementer`/`preferred_reviewer` assertions |
| `tests/agent/test_init_command.py` | **Update** — remove `--preferred-implementer`, `--script`, `--debug` etc. test cases |
| `tests/upgrade/migrations/test_m_2_0_1_tool_config_key_rename.py` | **Update** — selection key fixture data changes |
| `tests/upgrade/migrations/` (3.1.2 tests) | **Update** — add safety invariant test cases to Migration B tests |
