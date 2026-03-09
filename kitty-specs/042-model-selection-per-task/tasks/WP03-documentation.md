---
work_package_id: WP03
title: Documentation
lane: "done"
dependencies: [WP01]
base_branch: 042-model-selection-per-task-WP01
base_commit: e1eb8bb8122403f0c764b9c202b183bf5306a441
created_at: '2026-03-09T11:47:48.255571+00:00'
subtasks:
- T007
phase: Phase 2 - Validation
assignee: ''
agent: "claude-sonnet-4-6"
shell_pid: "41835"
review_status: "approved"
reviewed_by: "Zohar Stolar"
history:
- timestamp: '2026-03-09T11:13:06Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-009
---

# Work Package Prompt: WP03 – Documentation

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status` above. If `has_feedback`, read the Review Feedback section first.
- **Mark as acknowledged**: Set `review_status: acknowledged` when you start addressing feedback.

---

## Review Feedback

*[Empty — reviewers will populate if work is returned.]*

---

## Objectives & Success Criteria

Document the model-selection-per-task feature so users can configure it without reading source code.

**Done when**:
- There is a clear, findable docs section covering: config file location, full YAML schema, all 12 known command names, and upgrade behaviour
- A user following the docs can configure their model mapping correctly on the first try

## Context & Constraints

- **Implement command** (depends on WP01): `spec-kitty implement WP03 --base WP01`
- Run parallel with WP02 after WP01 is merged
- Check `docs/` for existing configuration docs to extend before creating new files

## Subtasks & Detailed Guidance

### Subtask T007 – Add model-selection docs

**Purpose**: Give users a clear reference for configuring model selection.

**Steps**:

1. Check `docs/` for existing configuration documentation:
   ```bash
   ls docs/
   grep -rl "config\|configuration\|settings" docs/ 2>/dev/null | head -10
   ```

2. **If a relevant config doc exists** (e.g., `docs/configuration.md`): add a `## Model Selection` section to it.

   **If no relevant doc exists**: create `docs/model-selection.md`.

3. The documentation must include:

   **Section title**: `Model Selection per Task` (or similar)

   **Content**:

   ```markdown
   ## Model Selection per Task

   Spec-kitty can use different AI models for different tasks — for example, a more
   capable model for planning and a faster model for implementation.

   ### Configuration

   Create (or edit) `~/.spec-kitty/config.yaml`:

   ```yaml
   models:
     specify: claude-opus-4-6
     plan: claude-opus-4-6
     tasks: claude-sonnet-4-6
     implement: claude-sonnet-4-6
     review: claude-sonnet-4-6
     accept: claude-sonnet-4-6
     merge: claude-haiku-4-5
     clarify: claude-sonnet-4-6
     status: claude-haiku-4-5
     checklist: claude-haiku-4-5
     analyze: claude-sonnet-4-6
     research: claude-opus-4-6
   ```

   You don't need to list all commands — only the ones you want to configure.
   Commands not listed will use the default model for your agent.

   ### Applying the configuration

   Run `spec-kitty upgrade` in any project to apply your model mapping.
   The `model:` field is injected into each agent's command files automatically.

   ```bash
   spec-kitty upgrade
   ```

   ### Supported commands

   | Command key | Slash command |
   |-------------|--------------|
   | `specify`   | `/spec-kitty.specify` |
   | `plan`      | `/spec-kitty.plan` |
   | `tasks`     | `/spec-kitty.tasks` |
   | `implement` | `/spec-kitty.implement` |
   | `review`    | `/spec-kitty.review` |
   | `accept`    | `/spec-kitty.accept` |
   | `merge`     | `/spec-kitty.merge` |
   | `clarify`   | `/spec-kitty.clarify` |
   | `status`    | `/spec-kitty.status` |
   | `checklist` | `/spec-kitty.checklist` |
   | `analyze`   | `/spec-kitty.analyze` |
   | `research`  | `/spec-kitty.research` |

   ### Notes

   - **Model names are not validated** — use names valid for your agent and subscription.
   - **Unknown command keys** produce a warning during upgrade (not an error).
   - **Removing a command** from `models:` will remove its `model:` field on the next `spec-kitty upgrade`.
   - The configuration is global — it applies to all projects on your machine.
   ```

4. If a `docs/README.md` or `docs/index.md` links to configuration docs, add a reference to the new section.

**Files**:
- `docs/model-selection.md` (new) OR `docs/<existing-config-doc>.md` (extended)
- `docs/README.md` or index (updated reference, if applicable)

---

## Risks & Mitigations

- Docs may become stale if command names change — keep the table in sync with `KNOWN_COMMANDS` in `global_config.py`

## Review Guidance

Reviewers should verify:
- [ ] Config file location is clearly stated (`~/.spec-kitty/config.yaml`)
- [ ] All 12 command keys are listed
- [ ] Example shows partial config (not all keys required)
- [ ] Upgrade step is documented
- [ ] Note about model names not being validated is present

## Activity Log

- 2026-03-09T11:13:06Z – system – lane=planned – Prompt created.
- 2026-03-09T11:47:48Z – claude-sonnet-4-6 – shell_pid=41835 – lane=doing – Assigned agent via workflow command
- 2026-03-09T11:59:10Z – claude-sonnet-4-6 – shell_pid=41835 – lane=for_review – Added docs/how-to/configure-model-selection.md and extended reference/configuration.md with global config schema
- 2026-03-09T12:15:06Z – claude-sonnet-4-6 – shell_pid=41835 – lane=done – Documentation complete: how-to guide, reference config section, index link, TOC entry.
