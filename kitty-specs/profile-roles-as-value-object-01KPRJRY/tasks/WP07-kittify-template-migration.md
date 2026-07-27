---
work_package_id: WP07
title: .kittify Template Migration for Profile Handoff
dependencies:
- WP06
requirement_refs:
- NFR-003
planning_base_branch: doctrine/profile_reinforcement
merge_target_branch: doctrine/profile_reinforcement
branch_strategy: Planning artifacts for this feature were generated on doctrine/profile_reinforcement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/profile_reinforcement unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-profile-roles-as-value-object-01KPRJRY
base_commit: 29ee6cc8b992bffa0b494892802d2e53af3810fc
created_at: '2026-04-22T06:39:47.183700+00:00'
subtasks:
- T036
- T037
- T038
agent: claude
shell_pid: '460662'
history:
- at: '2026-04-21T21:30:00Z'
  event: created
agent_profile: reviewer-renata
authoritative_surface: src/specify_cli/upgrade/migrations/
execution_mode: code_change
mission_slug: profile-roles-as-value-object-01KPRJRY
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/upgrade/migrations/m_*_kittify_profile_handoff*.py
- tests/specify_cli/test_migrations/test_kittify_profile_handoff_migration.py
role: reviewer
tags: []
---

# WP07 — .kittify Template Migration for Profile Handoff

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Write a spec-kitty upgrade migration that propagates the profile-load and handoff
guidance changes (introduced by WP06 to the SOURCE templates) into **all** installed
copies in client projects:

1. `.kittify/missions/software-dev/command-templates/implement.md` and `review.md`
2. `.kittify/overrides/missions/software-dev/templates/task-prompt-template.md`
3. `.agents/skills/spec-kitty.implement/SKILL.md`
4. `.agents/skills/spec-kitty.review/SKILL.md`

This WP depends on WP06: the source templates must be updated before a migration
can diff against them to know what to insert.

## Implementation Command

```bash
spec-kitty agent action implement WP07 --agent python-pedro
```

## Branch Strategy

- **Plan base**: `doctrine/profile_reinforcement`
- **Depends on**: WP06 (source template updates must land first)
- **Merge target**: `doctrine/profile_reinforcement`

---

## Context

When a client project runs `spec-kitty upgrade`, spec-kitty applies any new
migration modules found under `src/specify_cli/upgrade/migrations/`. The
migration introduced by this WP should update **four artifact paths**:

**`.kittify/missions/software-dev/command-templates/implement.md`**:
1. Fix stale field names: `profile` → `agent_profile`, `tool` → `agent`, add `model` entry
2. Fix Section 2a fallback: `If \`profile\` is empty` → `If \`agent_profile\` is empty`
3. Insert Section 6 "Prepare for Review Hand-off" before `## Output`

**`.kittify/missions/software-dev/command-templates/review.md`**:
1. Insert Section 2a "Load Agent Profile" after the Section 2 parse list
2. Expand the Output section with "On Approval" and "On Rejection" blocks

**`.kittify/overrides/missions/software-dev/templates/task-prompt-template.md`**:
1. Ensure the `agent_profile` and `role` fields are present in the frontmatter block
2. Ensure the `⚡ Do This First: Load Agent Profile` section is present after the title

**`.agents/skills/spec-kitty.implement/SKILL.md`** and **`.agents/skills/spec-kitty.review/SKILL.md`**:
1. Apply the same insertions as the `.kittify` command-template copies above

The migration must be idempotent: running it twice should not duplicate content.
Use sentinel strings (e.g., `"Prepare for Review Hand-off"`, `"Load Agent Profile"`)
to detect whether each block is already present before inserting.

---

## Subtask Guidance

### T036 — Write migration module

**File**: `src/specify_cli/upgrade/migrations/m_X_Y_Z_kittify_profile_handoff.py`

(Replace X_Y_Z with the next available migration version number — check existing
filenames to determine the correct version prefix.)

Migration class structure:

```python
from pathlib import Path
from .base import BaseMigration  # or whatever base class existing migrations use


IMPLEMENT_HANDOFF_SECTION = """
### 6. Prepare for Review Hand-off

Before moving this WP to `for_review`, update the `agent_profile` field in the WP
prompt frontmatter to a reviewer profile so the reviewing agent loads the correct
persona automatically.

1. Identify the appropriate reviewer profile:
   ```bash
   spec-kitty agent profile list --json | grep reviewer
   ```
   The default reviewer profile is `reviewer-renata`. Use it unless the mission or
   charter specifies a different reviewer.

2. Update the WP frontmatter:
   ```yaml
   agent_profile: "reviewer-renata"
   role: "reviewer"
   ```

3. Commit the updated frontmatter together with your implementation changes **before**
   running `spec-kitty agent tasks move-task WPxx --to for_review`.

The reviewer will then use `/ad-hoc-profile-load` with the reviewer profile and apply
its self-review gates automatically.
"""

REVIEW_PROFILE_LOAD_SECTION = """
### 2a. Load Agent Profile

Before proceeding with the review, load the agent profile from the WP frontmatter
using the `/ad-hoc-profile-load` skill (or `spec-kitty agent profile list` to browse
available profiles). Apply the profile's reviewer guidance and self-review gates for
the rest of this review session.

The WP frontmatter should already have `agent_profile` set to a reviewer profile
(e.g., `reviewer-renata`) by the implementing agent before it moved the WP to
`for_review`. If `agent_profile` is still set to an implementer profile, load the
implementer profile anyway and note the oversight in your review comments.
"""
```

The migration `apply()` method should:
1. Locate `.kittify/missions/software-dev/command-templates/implement.md` relative to `project_path`
2. Read the file content
3. If `"Prepare for Review Hand-off"` is NOT in the content, insert `IMPLEMENT_HANDOFF_SECTION` before `## Next step` (or at end if not found)
4. Write back if changed
5. Repeat for `review.md` with `REVIEW_PROFILE_LOAD_SECTION`

Also fix stale field names in `implement.md` if present:
- `"- \`profile\`"` → `"- \`agent_profile\`"`
- `"- \`tool\`"` → `"- \`agent\`"` (add `model` line after if missing)
- `"If \`profile\` is empty"` → `"If \`agent_profile\` is empty"`

### T037 — Register migration in migration registry

Find the migration registry (likely `src/specify_cli/upgrade/migrations/__init__.py`
or the upgrade runner). Ensure the new migration class is included in the list of
migrations that `spec-kitty upgrade` applies.

Inspect existing migrations to determine the correct registration pattern.

### T038 — Write migration tests

**File**: `tests/specify_cli/test_migrations/test_kittify_profile_handoff_migration.py`

(Or extend an existing migration test file if the convention is a single file per
migration version.)

Tests to include:
- `test_inserts_handoff_section_in_implement_when_absent`: synthetic `implement.md`
  without the handoff section → migration inserts it
- `test_does_not_duplicate_handoff_section_when_present`: migration run twice →
  content identical on second run (idempotent)
- `test_inserts_profile_load_section_in_review_when_absent`: synthetic `review.md`
  without Section 2a → migration inserts it
- `test_fixes_stale_field_names_in_implement`: `profile` / `tool` field names →
  replaced with `agent_profile` / `agent`
- `test_updates_skill_implement_skill_md`: `.agents/skills/spec-kitty.implement/SKILL.md`
  gets same profile-load + handoff blocks inserted
- `test_updates_skill_review_skill_md`: `.agents/skills/spec-kitty.review/SKILL.md`
  gets Section 2a + On Approval/Rejection blocks inserted
- `test_updates_task_prompt_template_override`: override `task-prompt-template.md`
  gets `agent_profile`/`role` frontmatter fields and `⚡ Do This First` section
- `test_skips_if_kittify_dir_missing`: no `.kittify` dir → migration completes
  without error
- `test_skips_if_agents_skills_missing`: no `.agents/skills` dir → migration
  completes without error

---

## Definition of Done

- [ ] Migration module exists at `src/specify_cli/upgrade/migrations/m_*_kittify_profile_handoff.py`
- [ ] Migration is registered and `spec-kitty upgrade` applies it
- [ ] `.kittify/missions/software-dev/command-templates/implement.md`: Review Hand-off section inserted, stale field names corrected
- [ ] `.kittify/missions/software-dev/command-templates/review.md`: Section 2a inserted, Output expanded
- [ ] `.kittify/overrides/missions/software-dev/templates/task-prompt-template.md`: `agent_profile`/`role` fields + `⚡ Do This First` block
- [ ] `.agents/skills/spec-kitty.implement/SKILL.md`: same as `.kittify` implement updates
- [ ] `.agents/skills/spec-kitty.review/SKILL.md`: same as `.kittify` review updates
- [ ] Migration is idempotent (running twice produces no change on second run)
- [ ] Tests pass: `pytest tests/specify_cli/test_migrations/` (or equivalent)

## Risks

- **Migration version number collision**: Check existing migration filenames before
  choosing a version prefix. Use the next available number.
- **Content variation in client templates**: Client projects may have customized their
  `implement.md`/`review.md`. The insertion must be position-aware (before a known
  anchor string) not line-number-based. Use `"## Next step"` or `"## Output"` as anchors.
- **Missing .kittify**: Some projects may not have the software-dev templates installed.
  Silently skip if the file doesn't exist.

## Activity Log

- 2026-04-21T21:30:00Z – claude – Created WP07 per user instruction
