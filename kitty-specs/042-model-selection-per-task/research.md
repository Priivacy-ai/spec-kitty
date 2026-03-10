# Research: Model Selection per Task

**Feature**: 042-model-selection-per-task
**Date**: 2026-03-09

## Findings

### 1. Global Config Location

**Decision**: `~/.spec-kitty/config.yaml`

**Evidence**: The existing spec-kitty codebase already uses `~/.spec-kitty/` as its global state directory:
- `~/.spec-kitty/missions/<id>/session.json` — collaboration session state (`collaboration/session.py`)
- `~/.spec-kitty/queues/` — event queue storage (`events/store.py`)
- `~/.spec-kitty/events/lamport_clock.json` — Lamport clock (`events/lamport.py`)

**Rationale**: Placing the global user config at `~/.spec-kitty/config.yaml` is consistent with existing conventions and requires no new path to document.

**Alternatives considered**:
- `~/.config/spec-kitty/config.yaml` (XDG Base Dir spec) — more portable on Linux, but inconsistent with existing usage
- `~/.spec-kitty.yaml` — flat file, simpler, but deviates from the directory-based pattern

---

### 2. Frontmatter Injection Mechanism

**Decision**: Use existing `FrontmatterManager` from `src/specify_cli/frontmatter.py`

**Evidence**: The `frontmatter.py` module has an explicit project-wide rule: "LLMs and scripts should NEVER manually edit YAML frontmatter." All existing migrations that touch frontmatter (`m_0_9_1_complete_lane_migration.py`) import and use `normalize_file` / `FrontmatterManager`.

**Rationale**: Consistency, safety, and correct handling of edge cases (no frontmatter, quoted vs unquoted values, preserving existing fields).

---

### 3. `model:` Frontmatter Support in Agents

**Decision**: Apply `model:` injection to all configured agent command files.

**Evidence**: Claude Code officially supports `model:` in command/skill frontmatter (per Claude Code docs, skills open standard). Other agents following the same frontmatter convention will also benefit. Agents that don't support `model:` will silently ignore the field — it is safe to inject universally.

**Rationale**: Writing to all agents is simpler (no per-agent capability matrix to maintain) and future-proof (agents that adopt the field later will benefit automatically).

---

### 4. Command Name → File Mapping

**Decision**: Command name extracted from filename as `spec-kitty.<cmd>.md` → `<cmd>`

**Known commands**: `specify`, `plan`, `tasks`, `implement`, `review`, `accept`, `merge`, `clarify`, `status`, `checklist`, `analyze`, `research`

**Evidence**: All agent command files follow the `spec-kitty.*.md` naming convention (confirmed by `m_2_0_1_fix_generated_command_templates.py` which uses `FILE_GLOBS = ["spec-kitty.*.md", "spec-kitty.*.toml"]`).

---

### 5. Migration Version

**Decision**: `m_2_0_4_model_injection.py`, `target_version = "2.0.4"`

**Evidence**: Latest migration is `m_2_0_1_fix_generated_command_templates.py`. This is a minor additive migration, appropriate for a patch-level bump.

---

### 6. Stale Model Removal

**Decision**: Remove `model:` from frontmatter when command is not in the user's mapping.

**Rationale**: Config is the source of truth. If a user removes a command from their config, the corresponding `model:` field should be cleaned up on the next upgrade. This keeps command files in sync with config.
