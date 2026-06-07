---
work_package_id: WP05
title: Phase 2 Writers and Registry Population
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- C-005
- FR-010
- FR-011
- FR-012
- FR-013
- FR-016
- FR-017
tracker_refs: []
planning_base_branch: pr/session-presence-multi-harness
merge_target_branch: pr/session-presence-multi-harness
branch_strategy: Planning artifacts for this mission were generated on pr/session-presence-multi-harness. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/session-presence-multi-harness unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
agent: "claude:sonnet:implementer:implementer"
shell_pid: "60922"
history:
- date: '2026-06-07'
  status: planned
  note: Initial WP creation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/session_presence/writers/
execution_mode: code_change
owned_files:
- src/specify_cli/session_presence/writers/agents_md.py
- src/specify_cli/session_presence/writers/skills_preamble.py
- src/specify_cli/session_presence/writers/registry.py
- tests/specify_cli/session_presence/test_agents_md_writer.py
- tests/specify_cli/session_presence/test_skills_preamble_writer.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Implement the Phase 2 writers (`AgentsMdWriter`, `SkillsPreambleWriter`), populate the `WRITER_REGISTRY` with all 18 non-Claude harness entries (Pattern B/C/D/E), and write the test suite for the new writers. This completes the full harness coverage planned in Phase 2 of the spec.

## Context

**C-001 constraint**: Phase 1 (WP01–WP04) must be fully merged before this WP starts. All Phase 1 classes (`MarkdownRulesWriter`, `Writer` protocol, `NullWriter`, `SessionPresenceContent`, registry skeleton) are already in the codebase.

**Open research notes**: `architecture/3.x/research/session-presence-harness-gaps.md` documents open questions for Pi, Vibe, Letta, and the 4 Pattern E harnesses. The resolution for this mission is:
- Pattern D (Pi, Vibe, Letta): use `SkillsPreambleWriter` defaulting to `AGENTS.md` injection (research.md section 3)
- Pattern E (Qwen, Kilocode, Auggie, Q): `NullWriter` — no orientation written, no error

**MarkdownRulesWriter refinement needed**: The Phase 1 `can_write()` implementation checks `(project_root / rules_path).parent.exists()`. For Pattern B harnesses with nested rules dirs (e.g., `.cursor/rules/spec-kitty.mdc`), this would fail if `.cursor/rules/` doesn't exist yet, even though `.cursor/` does. This WP adds a `check_dir` optional field to `MarkdownRulesWriter` to allow checking the harness root directory instead. This is a backward-compatible additive change.

**References**:
- Spec: FR-010, FR-011, FR-012, FR-013, FR-016, FR-017, C-005
- `kitty-specs/session-presence-multi-harness-01KTH57W/data-model.md` (writer registry shape table)
- `kitty-specs/session-presence-multi-harness-01KTH57W/spec.md` Scenario 7 (multi-harness init paths)
- `architecture/3.x/research/session-presence-harness-gaps.md` (Pattern E/D research status)

**Implementation command**:
```bash
spec-kitty agent action implement WP05 --agent claude
```

---

## Branch Strategy

- **Planning base**: `pr/session-presence-multi-harness`
- **Merge target**: `pr/session-presence-multi-harness`
- WP01–WP04 must be merged. This WP's worktree branches from the already-merged Phase 1 codebase.

---

## Subtask T023 — AgentsMdWriter

**Purpose**: Pattern C writer for Codex, OpenCode, and Google Antigravity. All three share `AGENTS.md` at the project root as their orientation target.

**File**: `src/specify_cli/session_presence/writers/agents_md.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from .markdown_rules import MarkdownRulesWriter


@dataclass
class AgentsMdWriter(MarkdownRulesWriter):
    """Pattern C: orientation injected into AGENTS.md at project root.

    Used by Codex, OpenCode, and Google Antigravity — all three resolve context
    from AGENTS.md alongside their own config directories.
    """
    harness_key: str = field(default="")       # overridden per instance
    rules_path: str = field(default="AGENTS.md")
    append_mode: bool = field(default=True)
    check_dir: str | None = field(default=None)

    def can_write(self, project_root: Path) -> bool:
        """Always writable — AGENTS.md lives at project root which always exists."""
        return True

    __all__ = ["AgentsMdWriter"]
```

**Key design**: `can_write()` always returns `True` because `AGENTS.md` is at the project root, which always exists. The `append_mode=True` ensures orientation is appended (or replaced in-place) rather than overwriting any existing AGENTS.md content from other tools.

**`__all__`** in `writers/__init__.py` should include `AgentsMdWriter` after this is created.

---

## Subtask T024 — SkillsPreambleWriter

**Purpose**: Pattern D writer for Pi, Vibe, and Letta. Currently defaults to AGENTS.md injection (same behavior as AgentsMdWriter) while the harness-gap research is open. The class is a distinct type so it can be subclassed/redirected per harness when research resolves.

**File**: `src/specify_cli/session_presence/writers/skills_preamble.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from .agents_md import AgentsMdWriter


@dataclass
class SkillsPreambleWriter(AgentsMdWriter):
    """Pattern D: orientation injected via skills preamble or AGENTS.md fallback.

    Defaults to AGENTS.md injection (same as Pattern C) while harness-specific
    research is open. See architecture/3.x/research/session-presence-harness-gaps.md.
    When a harness-specific preamble path is confirmed, subclass and override
    rules_path and can_write() accordingly.
    """
    harness_key: str = field(default="")       # overridden per instance

    __all__ = ["SkillsPreambleWriter"]
```

**Key design**: `SkillsPreambleWriter` is a subclass of `AgentsMdWriter` (not `MarkdownRulesWriter` directly) so the inheritance makes the current behavior obvious. Once research resolves that, say, Pi has a dedicated `.pi/instructions.md`, a `PiWriter` subclass of `SkillsPreambleWriter` can be registered without changing the base class.

---

## Subtask T025 — MarkdownRulesWriter Refinement + Pattern B Registry Entries

**Purpose**: Add `check_dir` to `MarkdownRulesWriter` and wire all 6 Pattern B harnesses into `WRITER_REGISTRY`.

**> Note on file ownership**: `markdown_rules.py` is owned by WP02, but this subtask modifies it to add the `check_dir` field. This is safe and expected — WP02 is fully merged into `pr/session-presence-multi-harness` before WP05 executes (WP05 depends on WP04 which depends on WP02). Sequential execution guarantees no conflict. Do not hesitate to make this targeted addition to the WP02-owned file.**

**`markdown_rules.py` change**: Add an optional `check_dir: str | None = None` field. Update `can_write()`:

```python
@dataclass
class MarkdownRulesWriter:
    harness_key: str
    rules_path: str
    append_mode: bool
    check_dir: str | None = None   # ← ADD THIS FIELD

    def can_write(self, project_root: Path) -> bool:
        check_path = project_root / (self.check_dir if self.check_dir else str(Path(self.rules_path).parent))
        return check_path.exists()
```

**Rationale**: For `.cursor/rules/spec-kitty.mdc`, `(project_root / ".cursor/rules/").exists()` would fail if the rules subdir hasn't been created yet. `check_dir=".cursor"` makes `can_write()` check whether the harness root directory exists — which is the correct signal for "is this harness installed?".

**Pattern B registry entries** (add to `writers/registry.py`):

| Agent key | `rules_path` | `append_mode` | `check_dir` | Rationale |
|-----------|-------------|----------------|-------------|-----------|
| `cursor` | `.cursor/rules/spec-kitty.mdc` | `False` | `.cursor` | Cursor uses `.cursor/rules/*.mdc`; own-file mode; check harness root |
| `windsurf` | `.windsurf/rules/spec-kitty.md` | `False` | `.windsurf` | Windsurf IDE rules file; own-file mode |
| `copilot` | `.github/copilot-instructions.md` | `True` | `.github` | GitHub Copilot reads this file; append section |
| `roo` | `.roo/rules/spec-kitty.md` | `False` | `.roo` | Roo Cline rules directory |
| `kiro` | `.kiro/steering/spec-kitty.md` | `False` | `.kiro` | Kiro uses `.kiro/steering/` for persistent instructions |
| `gemini` | `GEMINI.md` | `True` | `.gemini` | Gemini CLI reads `GEMINI.md`; append section |

**`registry.py` update** (add after the `claude` entry from WP02):

```python
from .markdown_rules import MarkdownRulesWriter
from .agents_md import AgentsMdWriter
from .skills_preamble import SkillsPreambleWriter
from .null_writer import NullWriter
from .claude_code import ClaudeCodeWriter

WRITER_REGISTRY: dict[str, "Writer"] = {
    # Pattern A — Claude Code
    "claude": ClaudeCodeWriter(),
    # Pattern B — MarkdownRulesWriter (parameterized per harness)
    "cursor":   MarkdownRulesWriter("cursor",   ".cursor/rules/spec-kitty.mdc",    append_mode=False, check_dir=".cursor"),
    "windsurf": MarkdownRulesWriter("windsurf", ".windsurf/rules/spec-kitty.md",   append_mode=False, check_dir=".windsurf"),
    "copilot":  MarkdownRulesWriter("copilot",  ".github/copilot-instructions.md", append_mode=True,  check_dir=".github"),
    "roo":      MarkdownRulesWriter("roo",      ".roo/rules/spec-kitty.md",        append_mode=False, check_dir=".roo"),
    "kiro":     MarkdownRulesWriter("kiro",     ".kiro/steering/spec-kitty.md",    append_mode=False, check_dir=".kiro"),
    "gemini":   MarkdownRulesWriter("gemini",   "GEMINI.md",                       append_mode=True,  check_dir=".gemini"),
    # Phase 2 Pattern C/D/E added in T026
}
```

**Note**: Since WP02 owns `markdown_rules.py`, and WP05 depends on WP02 being merged, adding `check_dir` to `markdown_rules.py` in WP05 is safe — it's a backward-compatible additive change (field with default `None`, existing callers unaffected).

---

## Subtask T026 — Pattern C, D, and E Registry Entries

**Purpose**: Complete the registry with all remaining 12 harness entries.

**`registry.py` — add Pattern C entries**:
```python
    # Pattern C — AgentsMdWriter (AGENTS.md at project root)
    "codex":       AgentsMdWriter("codex"),
    "opencode":    AgentsMdWriter("opencode"),
    "antigravity": AgentsMdWriter("antigravity"),
```

**`registry.py` — add Pattern D entries**:
```python
    # Pattern D — SkillsPreambleWriter (defaults to AGENTS.md; upgradeable per-harness)
    "pi":   SkillsPreambleWriter("pi"),
    "vibe": SkillsPreambleWriter("vibe"),
    "letta": SkillsPreambleWriter("letta"),
```

**`registry.py` — add Pattern E entries**:
```python
    # Pattern E — NullWriter (no known orientation mechanism; no error raised)
    # See architecture/3.x/research/session-presence-harness-gaps.md for research status.
    "qwen":     NullWriter("qwen"),
    "kilocode": NullWriter("kilocode"),
    "auggie":   NullWriter("auggie"),
    "q":        NullWriter("q"),
```

**Validation**: After all entries are added, `WRITER_REGISTRY` must have exactly 19 keys (all harnesses from `.kittify/config.yaml`). Add an assertion in tests:
```python
EXPECTED_KEYS = {"claude","cursor","windsurf","copilot","roo","kiro","gemini",
                 "codex","opencode","antigravity","pi","vibe","letta",
                 "qwen","kilocode","auggie","q"}
# Total: 17 listed. Check exact count from AI_CHOICES in src/specify_cli/__init__.py.
```

Verify the key list against `AGENT_DIRS` in `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` for completeness. There must be no silent gaps — every configured key must map to a writer.

---

## Subtask T027 — Tests for AgentsMdWriter and SkillsPreambleWriter

**Purpose**: Full test coverage for the two new writers; tests for the check_dir refinement to MarkdownRulesWriter.

**`tests/specify_cli/session_presence/test_agents_md_writer.py`** — required cases:
- `can_write()` always returns True regardless of directory state
- `has_presence()` returns False when `AGENTS.md` doesn't exist
- `has_presence()` returns False when `AGENTS.md` exists but has no section
- `has_presence()` returns True when `AGENTS.md` contains `SECTION_OPEN`
- First `write()`: creates `AGENTS.md` with orientation section
- Second `write()` (section already present): replaces section, no duplicate
- `write()` when `AGENTS.md` has existing content: appends section; existing content preserved
- `remove()`: removes section from `AGENTS.md`, leaves other content intact
- `remove()` when section not present: no-op

**`tests/specify_cli/session_presence/test_skills_preamble_writer.py`** — required cases:
- Same structural tests as `AgentsMdWriter` (both write to AGENTS.md)
- `isinstance(SkillsPreambleWriter("pi"), MarkdownRulesWriter)` — confirms inheritance
- `get_writer("pi")` returns `SkillsPreambleWriter` instance
- `get_writer("vibe")` returns `SkillsPreambleWriter` instance
- `get_writer("letta")` returns `SkillsPreambleWriter` instance
- `get_writer("codex")` returns `AgentsMdWriter` instance (not SkillsPreambleWriter)

**Additional tests for registry completeness** (add to `test_agents_md_writer.py` or a separate `test_registry.py`):
- `get_writer("cursor").rules_path == ".cursor/rules/spec-kitty.mdc"`
- `get_writer("copilot").append_mode is True`
- `get_writer("gemini").rules_path == "GEMINI.md"`
- `get_writer("qwen")` returns a NullWriter instance
- `get_writer("auggie")` returns a NullWriter instance
- All 19 expected harness keys have entries in `WRITER_REGISTRY` (no silent gaps)
- `isinstance(get_writer("unknown_key"), NullWriter)` — default NullWriter for unknown keys

**MarkdownRulesWriter check_dir refinement tests** (add to `test_markdown_rules_writer.py`):
- `can_write()` with `check_dir=".cursor"`: returns True when `.cursor/` exists; False when it doesn't
- `can_write()` without `check_dir`: falls back to checking parent of `rules_path`
- `can_write()` for `.cursor/rules/spec-kitty.mdc` without `check_dir`: returns False if `.cursor/rules/` doesn't exist (regression test confirming the old behavior)
- `can_write()` for `.cursor/rules/spec-kitty.mdc` with `check_dir=".cursor"`: returns True when `.cursor/` exists even if `.cursor/rules/` doesn't

---

## Definition of Done

- [ ] `get_writer("cursor")` returns `MarkdownRulesWriter` with `rules_path=".cursor/rules/spec-kitty.mdc"` and `append_mode=False`
- [ ] `get_writer("copilot")` returns `MarkdownRulesWriter` with `rules_path=".github/copilot-instructions.md"` and `append_mode=True`
- [ ] `get_writer("gemini")` returns `MarkdownRulesWriter` with `rules_path="GEMINI.md"` and `append_mode=True`
- [ ] `get_writer("codex")` returns an `AgentsMdWriter` instance
- [ ] `get_writer("pi")` returns a `SkillsPreambleWriter` instance
- [ ] `get_writer("qwen")` returns a `NullWriter` instance (no error)
- [ ] Writing orientation for a Cursor project creates `.cursor/rules/spec-kitty.mdc` (dirs created atomically)
- [ ] Writing orientation for a Copilot project appends section to `.github/copilot-instructions.md`
- [ ] Writing orientation to `AGENTS.md` twice produces exactly one section (idempotent)
- [ ] `WRITER_REGISTRY` covers all 19 harnesses — no silent gaps
- [ ] Zero ruff issues, zero mypy --strict issues in all new/updated files
- [ ] `pytest tests/specify_cli/session_presence/test_agents_md_writer.py tests/specify_cli/session_presence/test_skills_preamble_writer.py -v` passes

## Risks

- **Dataclass inheritance field ordering**: `AgentsMdWriter` and `SkillsPreambleWriter` use `field(default=...)`. In Python 3.11+ dataclass inheritance, fields with defaults must follow fields without defaults. Verify the field order doesn't cause `TypeError: non-default argument 'harness_key' follows default argument`.
- **`check_dir` None comparison in `can_write()`**: `Path(self.rules_path).parent` returns `Path(".")` for top-level paths like `"GEMINI.md"`. `(project_root / ".").exists()` is True. Test this edge case explicitly.
- **Conflicting AGENTS.md writes**: Pattern C and D harnesses all write to the same `AGENTS.md`. If a project has both `codex` and `pi` configured, `SessionPresenceManager.install()` will call both writers. The second call will find `SECTION_OPEN` already present (from the first write) and call `_replace_section()` — not append a duplicate. This is correct behavior, but verify with a test covering two Pattern C/D harnesses on the same project.
- **Key count discrepancy**: The agent key list may differ between `AI_CHOICES` in `__init__.py` and `AGENT_DIRS` in the migration. Grep both before finalizing the registry to ensure no key is missing.

## Activity Log

- 2026-06-07T16:06:21Z – claude:sonnet:implementer:implementer – shell_pid=60922 – Assigned agent via action command
