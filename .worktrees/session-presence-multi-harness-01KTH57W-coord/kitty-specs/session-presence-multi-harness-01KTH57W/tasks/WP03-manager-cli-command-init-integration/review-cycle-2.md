---
affected_files: []
cycle_number: 2
mission_slug: session-presence-multi-harness-01KTH57W
reproduction_command:
reviewed_at: '2026-06-07T15:32:59Z'
reviewer_agent: unknown
verdict: approved
wp_id: WP03
review_artifact_override_at: "2026-06-07T15:39:54Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP03"
review_artifact_override_reason: "Review cycle 2 passed: load_agent_config fix confirmed (not AgentConfig.load), unused type-ignore removed from manager.py, mypy+ruff clean. Tests deferred to WP04 per mission plan. All anti-pattern checks pass."
---

**Issue 1 — CRITICAL: `AgentConfig.load()` does not exist (runtime AttributeError)**

Both new files call `AgentConfig.load(project_path)`, but `AgentConfig` is a plain `@dataclass` with no `.load()` classmethod. The correct API is the free function `load_agent_config(project_path)`.

Affected files:
- `src/specify_cli/cli/commands/session_start.py` line 53
- `src/specify_cli/upgrade/migrations/m_3_3_0_session_presence_claude_code.py` line 57

Fix — in both files, change the import and call:

```python
# WRONG (current)
from specify_cli.core.agent_config import AgentConfig
agent_config = AgentConfig.load(project_path)

# CORRECT
from specify_cli.core.agent_config import load_agent_config
agent_config = load_agent_config(project_path)
```

This is a confirmed runtime bug: `AgentConfig` has no `.load()` classmethod (grepped across the entire src tree — only `load_agent_config()` free function exists). The spec's Risks section acknowledged this ambiguity but the wrong pattern was used.

**Issue 2 — mypy: unused `type: ignore[arg-type]` on manager.py line 92**

`manager.py` line 92 carries `# type: ignore[arg-type]` on the `SessionPresenceContent(current, slug, health, avail)` return. Mypy reports this as `[unused-ignore]` — meaning the type checker is happy with the call without the suppression. The definition of done requires zero mypy issues. Remove the comment:

```python
# Before
return SessionPresenceContent(current, slug, health, avail)  # type: ignore[arg-type]

# After
return SessionPresenceContent(current, slug, health, avail)
```

**Note — pre-existing baseline (not a WP03 regression)**

The `Class cannot subclass "BaseMigration" (has type "Any") [misc]` mypy error in the new migration file is identical to the same error in existing migrations (e.g. `m_3_2_0rc35_spk_skill_pack.py`). This is a pre-existing codebase issue — WP03 did not introduce it and need not fix it. The DoD criterion "zero mypy --strict issues" should be interpreted relative to issues introduced by this WP; the baseline already carries this error. If the team decides to fix the baseline, it belongs in a separate task.

**Summary**

- Ruff: clean (no issues)
- Mypy: 2 issues — 1 genuine unused-ignore (fixable in 1 line), 1 pre-existing baseline
- Runtime correctness: `AgentConfig.load()` will raise `AttributeError` at runtime in both `session-start` and the migration's `apply()` path

Please fix both Issue 1 and Issue 2 before re-submitting.
