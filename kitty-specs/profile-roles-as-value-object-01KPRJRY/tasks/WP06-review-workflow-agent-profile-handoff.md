---
work_package_id: WP06
title: Review Workflow Agent Profile Handoff
dependencies: []
requirement_refs:
- NFR-003
planning_base_branch: doctrine/profile_reinforcement
merge_target_branch: doctrine/profile_reinforcement
branch_strategy: Planning artifacts for this feature were generated on doctrine/profile_reinforcement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/profile_reinforcement unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
agent: claude
history:
- at: '2026-04-21T18:24:37Z'
  event: created
agent_profile: reviewer-renata
authoritative_surface: src/specify_cli/missions/software-dev/command-templates/
execution_mode: planning_artifact
mission_slug: profile-roles-as-value-object-01KPRJRY
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/missions/software-dev/command-templates/implement.md
- src/specify_cli/missions/software-dev/command-templates/review.md
role: reviewer
tags: []
---

# WP06 — Review Workflow Agent Profile Handoff

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `curator`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Fix two command template files in the spec-kitty source so that the implement/review
hand-off loop is profile-aware:

1. **`implement.md`**: Correct two stale field names left over from before `WPMetadata`
   was introduced, and add explicit guidance at the Submit step to update `agent_profile`
   in WP frontmatter to a reviewer profile before moving the WP to `for_review`.

2. **`review.md`**: Add a "Load Agent Profile" step so reviewing agents load their
   reviewer profile before proceeding, and add guidance at the Reject step to update
   `agent_profile` back to an implementer profile before rejecting.

These are **source templates** under `src/specify_cli/missions/software-dev/command-templates/`.
Do **not** edit the generated copies under `.claude/commands/` or any other agent directory.

## Implementation Command

```bash
spec-kitty agent action implement WP06 --agent curator-carla
```

## Branch Strategy

- **Plan base**: `doctrine/profile_reinforcement`
- **Depends on**: nothing (independent of WP01–WP05)
- **Parallelizes with**: all other WPs (touches only command templates)
- **Merge target**: `doctrine/profile_reinforcement`

---

## Context

After the `AgentProfile.roles` change lands, profiles carry character-named IDs (e.g.,
`implementer-ivan`, `reviewer-renata`). The implement/review workflow should use these
IDs to signal which agent persona should work on the WP next — otherwise the `agent_profile`
frontmatter stagnates at the initial implementer value throughout the entire lifecycle.

The current templates have two problems:

**Problem 1 — stale field names in `implement.md` Section 2:**
```markdown
- `profile` -- agent profile identifier to load
- `role` -- human-readable role for this WP
- `tool` -- primary tool or skill focus
```
`profile` was never a valid `WPMetadata` field (the correct name is `agent_profile`).
`tool` was never a valid `WPMetadata` field (the correct name is `agent`).
Section 2a compounds this: "If `profile` is empty, select the best available profile...".

**Problem 2 — no handoff guidance:**
Neither `implement.md` nor `review.md` instructs the agent to update `agent_profile`
when the WP changes hands. This means reviewers work with a frontmatter that still
says `agent_profile: "python-pedro"` (an implementer), which is confusing and prevents
automatic profile-loading from working correctly in the review phase.

---

## Subtask Guidance

### T034 — Fix `implement.md`

**File**: `src/specify_cli/missions/software-dev/command-templates/implement.md`

#### Part A — Fix stale field names in Section 2

Find this block (around line 58–67):

```markdown
- `profile` -- agent profile identifier to load
- `role` -- human-readable role for this WP
- `tool` -- primary tool or skill focus
```

Replace with:

```markdown
- `agent_profile` -- agent profile identifier to load (e.g., `implementer-ivan`)
- `role` -- role within the profile (e.g., `implementer`)
- `agent` -- CLI agent/tool identifier (e.g., `claude`, `codex`)
- `model` -- optional model override (e.g., `claude-sonnet-4-6`)
```

Find the stale reference in Section 2a:

```markdown
If `profile` is empty, select the best available profile for the WP's `task_type`.
```

Replace with:

```markdown
If `agent_profile` is empty, run `spec-kitty agent profile list` and select the best
available profile for the WP's `task_type` and `authoritative_surface`.
```

#### Part B — Add profile-handoff guidance at the Submit step

Find the "## Output" or "## Next step" section at the end of `implement.md`. Insert a new
section **before** the final "Next step" line:

```markdown
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
```

**Files**: `src/specify_cli/missions/software-dev/command-templates/implement.md`

**Validation**:
```bash
grep -n "agent_profile" src/specify_cli/missions/software-dev/command-templates/implement.md
# Should return at least 2 hits (Section 2 parse list + Section 2a fallback)
grep -n "reviewer-renata\|for_review" src/specify_cli/missions/software-dev/command-templates/implement.md
# Should return the new hand-off section
grep -n '"profile"' src/specify_cli/missions/software-dev/command-templates/implement.md
# Should return zero hits (stale name removed)
grep -n '"tool"' src/specify_cli/missions/software-dev/command-templates/implement.md
# Should return zero hits (stale name removed)
```

---

### T035 — Update `review.md`

**File**: `src/specify_cli/missions/software-dev/command-templates/review.md`

#### Part A — Add profile-load step as Section 2a

Find Section 2 "Load Work Package Prompt". Directly after the parse list (the bulleted
list ending with `- \`dependencies\``), insert a new subsection:

```markdown
### 2a. Load Agent Profile

Before proceeding with the review, load the agent profile from the WP frontmatter
using the `/ad-hoc-profile-load` skill (or `spec-kitty agent profile list` to browse
available profiles). Apply the profile's reviewer guidance and self-review gates for
the rest of this review session.

The WP frontmatter should already have `agent_profile` set to a reviewer profile
(e.g., `reviewer-renata`) by the implementing agent before it moved the WP to
`for_review`. If `agent_profile` is still set to an implementer profile, load the
implementer profile anyway and note the oversight in your review comments.
```

#### Part B — Add reject profile-handoff guidance to the Output section

Find the Output section at the end of `review.md`:

```markdown
## Output

After completing review:
- Approve or reject each subtask with clear reasoning
- If rejecting, provide specific feedback on what needs to change
- Commit any review notes or annotations
```

Replace with:

```markdown
## Output

After completing review:
- Approve or reject each subtask with clear reasoning
- If rejecting, provide specific feedback on what needs to change
- Commit any review notes or annotations

### On Approval

Move the WP forward:
```bash
spec-kitty agent tasks move-task WPxx --to approved
```

### On Rejection

Before rejecting, update `agent_profile` in the WP frontmatter back to the
implementer profile so the next implementation cycle starts with the right context:

1. Identify the implementer profile that worked on this WP (check the history field
   or `status.events.jsonl` to find the last `in_progress` actor).
   Alternatively, use the default: `implementer-ivan` (or `python-pedro`/`java-jenny`
   for language-specific work).

2. Update the WP frontmatter:
   ```yaml
   agent_profile: "implementer-ivan"
   role: "implementer"
   ```

3. Commit the updated frontmatter together with your review notes **before** running:
   ```bash
   spec-kitty agent tasks move-task WPxx --to in_progress
   ```

The implementing agent will then load the correct profile via `/ad-hoc-profile-load`
and resume work with the proper persona and self-review gates.
```

**Files**: `src/specify_cli/missions/software-dev/command-templates/review.md`

**Validation**:
```bash
grep -n "2a\|agent_profile\|ad-hoc-profile-load" src/specify_cli/missions/software-dev/command-templates/review.md
# Should return the new Section 2a block
grep -n "On Rejection\|implementer-ivan" src/specify_cli/missions/software-dev/command-templates/review.md
# Should return the new rejection guidance
```

---

## Definition of Done

- [ ] `implement.md`: `profile` → `agent_profile` in Section 2 parse list
- [ ] `implement.md`: `tool` → `agent` in Section 2 parse list; `model` entry added
- [ ] `implement.md`: Section 2a: `profile` → `agent_profile` in fallback sentence
- [ ] `implement.md`: Section 6 "Prepare for Review Hand-off" added with frontmatter update and commit guidance
- [ ] `review.md`: Section 2a "Load Agent Profile" added after Section 2 parse list
- [ ] `review.md`: Output section expanded with "On Approval" and "On Rejection" blocks
- [ ] `review.md`: Rejection block includes `agent_profile` frontmatter update + commit step
- [ ] `grep '"profile"' implement.md` → zero hits
- [ ] `grep '"tool"' implement.md` → zero hits (or only in bulk-edit classification table which is unrelated)

## Risks

- **Generated copies**: The real templates live in `src/specify_cli/missions/software-dev/command-templates/`. Do NOT edit `.claude/commands/`, `.amazonq/prompts/`, or any other agent directory — those are generated copies that will be overwritten on the next `spec-kitty upgrade`.
- **Bulk-edit classification table**: `implement.md` contains a table with `dict_key`, `config_value`, etc. Searching for `"tool"` may hit the `| \`config_value\` | ...` column header. Confirm that only the field-name bullets in Section 2 are changed, not the classification table.

## Reviewer Guidance

- Confirm Section 2 parse list in `implement.md` uses `agent_profile`, `role`, `agent`, `model` (4 items, no `profile`, no `tool`).
- Confirm Section 2a in `implement.md` references `agent_profile` not `profile`.
- Confirm Section 6 in `implement.md` includes a concrete profile update example with `reviewer-renata` and a commit-before-move instruction.
- Confirm Section 2a in `review.md` instructs the reviewing agent to load the profile via `/ad-hoc-profile-load`.
- Confirm the Output section in `review.md` distinguishes approve vs. reject and the rejection path updates `agent_profile` back to an implementer.
