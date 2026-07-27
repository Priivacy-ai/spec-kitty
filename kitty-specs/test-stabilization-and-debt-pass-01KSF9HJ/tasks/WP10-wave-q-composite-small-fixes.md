---
work_package_id: WP10
title: 'Wave Q composite: retro mining + tracker_refs field + bulk-edit-gate docs (FR-010, FR-011, FR-012)'
dependencies: []
requirement_refs:
- FR-010
- FR-011
- FR-012
planning_base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
merge_target_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
base_commit: 639079588508030800eba0a13baa736bc7417120
created_at: '2026-05-25T14:54:07.146219+00:00'
subtasks:
- T039
- T040
- T041
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "2021235"
history:
- by: claude
  at: '2026-05-25T14:00:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
execution_mode: code_change
mission_id: 01KSF9HJBFKRBC617JVHKZXNE2
mission_slug: test-stabilization-and-debt-pass-01KSF9HJ
owned_files:
- src/specify_cli/retrospect/generator.py
- src/specify_cli/tasks/metadata.py
- src/specify_cli/cli/commands/tasks_move.py
- docs/reference/bulk-edit-gate.md
- .kittify/doctrine/skills/spec-kitty-bulk-edit-classification/SKILL.md
- tests/specify_cli/retrospect/test_event_log_mining.py
- tests/specify_cli/tasks/test_tracker_refs_field.py
priority: P2
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `python-pedro` before reading further. Three small, independent fixes bundled in one WP because each is <100 LOC.

## Objective

Three independent quality follow-ups from the 01KSAF14 engineering notes:

- **T039 / FR-010 (F-04)**: extend `spec-kitty retrospect create` generator to mine `status.events.jsonl` for `--force` transitions, arbiter overrides, and rejection cycles. Each becomes a `helped`/`not_helpful`/`gaps` entry instead of the empty `ran_no_findings` payload that the post-mission-122 audit observed.
- **T040 / FR-011 (F-10)**: add optional `tracker_refs: list[str]` field to `WPMetadata` Pydantic model. `map-requirements` and `move-task` commands accept the field. The orchestrator can then record HiC-assigned tracker issues per DIR-012 without polluting the WP body prose.
- **T041 / FR-012 (F-01)**: author `docs/reference/bulk-edit-gate.md` documenting the 4-value action enum (`do_not_change`, `manual_review`, `rename`, `rename_if_user_visible`) and the required top-level `target:` block. Update the `spec-kitty-bulk-edit-classification` skill prose to link there.

## Branch strategy

- Planning base branch: mission lane branch
- Merge target branch: `main`
- Execution: lane workspace allocated by `finalize-tasks`.

## Context

- [`spec.md`](../spec.md) FR-010, FR-011, FR-012.
- [`docs/engineering_notes/finding/2026-05-24-mission-01KSAF14-orchestration-findings.md`](../../../docs/engineering_notes/finding/2026-05-24-mission-01KSAF14-orchestration-findings.md) F-04, F-10, F-01 (the inbound findings).
- Existing source for T039: `src/specify_cli/retrospect/generator.py` (or wherever `retrospect create` lives — verify via `grep -rn "retrospect.*create\|create.*retrospective" src/specify_cli/`).
- Existing source for T040: `src/specify_cli/tasks/metadata.py` (`WPMetadata` Pydantic model — also verify location).
- Existing source for T041: `.kittify/doctrine/skills/spec-kitty-bulk-edit-classification/SKILL.md` (skill prose to update).

## Subtask details

### T039 — Retrospective event-log mining [P]

In `src/specify_cli/retrospect/generator.py` (or equivalent), extend the generator to read `status.events.jsonl` from the mission directory and emit findings entries.

Heuristics to mine:

| Event pattern | Maps to retrospective field |
|---|---|
| `move-task ... --force` AND `from=approved AND to=planned` | `not_helpful`: "Review cycle <N> required for WP<NN>" |
| `move-task ... --force` AND arbiter-mode `--note` containing "arbiter" | `gaps`: "Arbiter override needed for WP<NN>" |
| Multiple `from=planned AND to=in_progress` events for same WP | `not_helpful`: "WP<NN> needed N implementation cycles" |
| `move-task ... --to done --force` (chore cleanup) | `helped` or no entry (clean merge fallback) |

Add at least 2-3 mining functions and unit-test each. Place tests at `tests/specify_cli/retrospect/test_event_log_mining.py`.

Critical: the existing empty-output behaviour must remain stable for missions whose event log has none of these patterns. The mining ADDS entries; it doesn't change existing empty-output semantics.

### T040 — `tracker_refs` field on `WPMetadata` [P]

In `src/specify_cli/tasks/metadata.py` (or equivalent — find the Pydantic model):

```python
class WPMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", ...)
    # ... existing fields
    tracker_refs: list[str] = Field(default_factory=list, description="External tracker issue references (e.g., '#1298', 'JIRA-123').")
```

Update `map-requirements` and `move-task` to accept `--tracker-ref` CLI flag(s) and write them into the WP frontmatter. Mirror the existing `requirement_refs` flow.

Add regression test at `tests/specify_cli/tasks/test_tracker_refs_field.py`:
- WP with no `tracker_refs` → loads (backward compatibility).
- WP with `tracker_refs: ['#1298']` → loads, field accessible.
- `map-requirements --tracker-ref '#1298' --wp WP01` → persists.

### T041 — Bulk-edit-gate documentation [P]

Create `docs/reference/bulk-edit-gate.md`:

```markdown
# Bulk-edit gate reference

When a mission's `meta.json` declares `change_mode: bulk_edit`, the planning
phase MUST author `kitty-specs/<slug>/occurrence_map.yaml`. The bulk-edit
gate validates that file before `/spec-kitty.implement` can claim the first
WP workspace.

## Required schema

```yaml
schema_version: "1.0"
mission: <mission-slug>

target:
  term: "<the literal string being renamed>"
  operation: <rename | remove>
  replacement: "<the new literal string, or null if operation=remove>"

categories:
  code_symbols:
    action: <do_not_change | manual_review | rename | rename_if_user_visible>
    # optional per-category fields...
  import_paths:
    action: ...
  filesystem_paths:
    action: ...
  serialized_keys:
    action: ...
  cli_commands:
    action: ...
  user_facing_strings:
    action: ...
  tests_fixtures:
    action: ...
  logs_telemetry:
    action: ...
```

## Allowed `action` values

| Action | Meaning |
|---|---|
| `do_not_change` | Preserve as-is (historical text, dead-code-after-rename, etc.) |
| `manual_review` | Implementer must inspect per-occurrence (e.g., dead-code that should be deleted, not renamed) |
| `rename` | Mechanical s/old/new/ across the matched files |
| `rename_if_user_visible` | Rename only on public CLI surfaces / JSON keys / docs; preserve in internal text |

## See also

- The skill `spec-kitty-bulk-edit-classification` (loaded automatically when meta.json declares `change_mode: bulk_edit`).
- Existing missions that exercised this gate: `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/occurrence_map.yaml`, `kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/occurrence_map.yaml`.
```

Then update `.kittify/doctrine/skills/spec-kitty-bulk-edit-classification/SKILL.md` to link to this reference doc (add a "Schema" or "Reference" section).

## Definition of Done

- [ ] T039: retrospective generator emits ≥1 finding entry on missions with `--force` / arbiter events in `status.events.jsonl`.
- [ ] T039: tests at `test_event_log_mining.py` cover 3 patterns; all pass.
- [ ] T040: `WPMetadata` accepts `tracker_refs` field; backward-compatible (existing WPs without the field still load).
- [ ] T040: `map-requirements` and `move-task` accept `--tracker-ref`; regression test passes.
- [ ] T041: `docs/reference/bulk-edit-gate.md` exists and is linked from `cli-commands.md` index.
- [ ] T041: skill `SKILL.md` includes a link to the new reference doc.
- [ ] `ruff check` clean on touched files.
- [ ] `mypy --strict` clean on touched files.

## Risks

- **Retrospective generator location drift**: the actual implementation may be under a different module path than `retrospect/generator.py`. Adjust per `grep -rn 'def.*create.*retrospective\|retrospect.*create' src/`.
- **WPMetadata Pydantic class location**: similar. The field addition is small but the locator may need updating.
- **Skill file location**: `.kittify/doctrine/skills/spec-kitty-bulk-edit-classification/SKILL.md` is the canonical path, but the rendered/installed-to-tool copies (in `.claude/skills/`, etc.) are GENERATED. Only edit the source file under `.kittify/doctrine/`; do NOT edit the generated copies.

## Reviewer guidance

1. For T039: verify the generator runs cleanly on a mission with NO `--force` events (no regression).
2. For T040: verify the field is `Optional` / has a default, so existing serialised WPs still load.
3. For T041: verify the skill file edit is in the SOURCE under `.kittify/doctrine/`, not in a generated copy.

## Activity Log

- 2026-05-25T14:54:07Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1947302 – Assigned agent via action command
- 2026-05-25T15:05:58Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1947302 – 3 small fixes landed: F-04 retro mining + F-10 tracker_refs + F-01 bulk-edit-gate docs
- 2026-05-25T15:06:35Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2021235 – Started review via action command
- 2026-05-25T15:09:03Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2021235 – Review passed: 3 sub-fixes (F-04 retro-mining + F-10 tracker_refs + F-01 bulk-edit-gate docs); 66 tests green
