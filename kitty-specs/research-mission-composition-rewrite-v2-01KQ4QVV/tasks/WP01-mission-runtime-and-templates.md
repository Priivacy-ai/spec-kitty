---
work_package_id: WP01
title: Research mission-runtime.yaml + 6 Prompt Templates
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-research-mission-composition-rewrite-v2-01KQ4QVV
base_commit: 2daeef10ecf6a162044826aa7443a11aaa01021c
created_at: '2026-04-26T12:05:51.045578+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
shell_pid: "7384"
agent: "claude:opus-4.7:implementer-ivan:implementer"
history:
- timestamp: '2026-04-26T11:46:43Z'
  actor: claude
  note: Created during /spec-kitty.tasks for mission research-mission-composition-rewrite-v2-01KQ4QVV
authoritative_surface: src/specify_cli/missions/research/mission-runtime.yaml
execution_mode: code_change
mission_id: 01KQ4QVVZ4DC6CXA1XCZZAQ8AG
mission_slug: research-mission-composition-rewrite-v2-01KQ4QVV
owned_files:
- src/specify_cli/missions/research/mission-runtime.yaml
- src/doctrine/missions/research/mission-runtime.yaml
- src/specify_cli/missions/research/templates/scoping.md
- src/specify_cli/missions/research/templates/methodology.md
- src/specify_cli/missions/research/templates/gathering.md
- src/specify_cli/missions/research/templates/synthesis.md
- src/specify_cli/missions/research/templates/output.md
- src/specify_cli/missions/research/templates/accept.md
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the implementer profile so this work is governed by the right doctrine context:

```
/ad-hoc-profile-load implementer-ivan
```

# WP01 — Research mission-runtime.yaml + 6 Prompt Templates

## Objective

Author the missing `mission-runtime.yaml` sidecar that gives the runtime engine a `MissionTemplate` with `mission.key: research` and a populated `steps` list. Software-dev has this file at `src/specify_cli/missions/software-dev/mission-runtime.yaml`; research has nothing equivalent today, which is why `get_or_start_run('demo-research', repo, 'research')` raises `MissionRuntimeError`.

After WP01: a fresh research mission can be started via the runtime engine. WP02–WP06 build on that runnability.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Execution worktree: lane-based, allocated by `spec-kitty implement WP01`. Stay in the worktree for all edits.

## Implementation Command

```bash
spec-kitty agent action implement WP01 --agent <name>
```

## Authoritative References

- `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/plan.md` — D1 (coexistence) and D4 (PromptStep shape)
- `src/specify_cli/missions/software-dev/mission-runtime.yaml` — the canonical model to mirror (read in full)
- `src/doctrine/missions/software-dev/mission-runtime.yaml` — doctrine mirror
- `src/specify_cli/next/_internal_runtime/schema.py:401-450` — `PromptStep` and `MissionTemplate` schemas
- `src/specify_cli/next/runtime_bridge.py:905-961` — runtime template resolver (prefers `mission-runtime.yaml` sidecar)

## Subtask T001 — Audit software-dev mission-runtime.yaml structure

**Purpose**: Discover the exact schema your file must produce. Don't invent fields.

**Steps**:
1. Read `src/specify_cli/missions/software-dev/mission-runtime.yaml` in full. Note the top-level keys: `mission` (with `key`, `name`, `version`), `steps` list, optional `audit_steps`.
2. For each step, list the fields used: `id`, `title`, `description`, `agent-profile` (alias for `agent_profile`), `prompt_template`, `depends_on`, optional `contract_ref`.
3. Read the doctrine mirror at `src/doctrine/missions/software-dev/mission-runtime.yaml` and note any divergence (likely none).
4. Read `src/specify_cli/next/_internal_runtime/schema.py:401-450` to confirm field names and aliases. The YAML alias is `agent-profile` (line 415) but the Python field name is `agent_profile`.
5. Record schema findings in your commit message.

**Files**: read-only.

## Subtask T002 — Author `src/specify_cli/missions/research/mission-runtime.yaml`

**Purpose**: Make the runtime engine able to load a research `MissionTemplate`.

**Steps**:
1. Create `src/specify_cli/missions/research/mission-runtime.yaml`.
2. Set `mission.key: research`, `mission.name: Deep Research Kitty`, `mission.version: "2.0.0"`.
3. Author 6 `steps`:
   - `scoping`: title `Research Scoping`; `agent-profile: researcher-robbie`; `prompt_template: scoping.md`; description.
   - `methodology`: depends_on `[scoping]`; profile `researcher-robbie`; template `methodology.md`.
   - `gathering`: depends_on `[methodology]`; profile `researcher-robbie`; template `gathering.md`.
   - `synthesis`: depends_on `[gathering]`; profile `researcher-robbie`; template `synthesis.md`.
   - `output`: depends_on `[synthesis]`; profile `reviewer-renata`; template `output.md`.
   - `accept`: depends_on `[output]`; template `accept.md` (no agent-profile required).
4. Do NOT include `contract_ref` on any step — composition uses synthesis (per plan D4).
5. Mirror software-dev's prose style for `description` fields.
6. Validate the file loads via Pydantic:
   ```bash
   uv run python -c "from specify_cli.next._internal_runtime.schema import load_mission_template_file; from pathlib import Path; t = load_mission_template_file(Path('src/specify_cli/missions/research/mission-runtime.yaml')); print(t.mission.key, len(t.steps))"
   ```
   Expect: `research 6`.

**Files**: `src/specify_cli/missions/research/mission-runtime.yaml` (new).

## Subtask T003 — Author the doctrine mirror

**Purpose**: Match software-dev's pattern of having both files.

**Steps**:
1. Copy the file from T002 to `src/doctrine/missions/research/mission-runtime.yaml`. Mirror exactly.
2. Same Pydantic load validation.

**Files**: `src/doctrine/missions/research/mission-runtime.yaml` (new).

## Subtask T004 — Author 6 prompt templates

**Purpose**: Give the runtime engine real prompt content for each step.

**Steps**:
1. Create `src/specify_cli/missions/research/templates/<step>.md` for each step (6 files: scoping, methodology, gathering, synthesis, output, accept).
2. Mirror the structure of `src/specify_cli/missions/software-dev/templates/<step>.md` files (read at least 2 to see the pattern).
3. Each template should have: a brief intro framing the step, expected outputs (with explicit artifact filenames where applicable), and references to the corresponding action doctrine bundle (which WP02 authors).
4. Keep each template focused; ~30-80 lines each.
5. The `gathering.md` template MUST mention the minimum-source threshold (the `event_count("source_documented", 3)` rule from the legacy mission.yaml). The `output.md` template MUST mention the publication approval gate.

**Files**: 6 new files under `src/specify_cli/missions/research/templates/`.

## Subtask T005 — Runnability proof (CRITICAL — closes the v1 P0 finding)

**Purpose**: Prove that the work in T002-T004 made the research mission runnable.

**Steps**:
1. Set up a clean tmp repo and run:
   ```python
   from pathlib import Path
   import tempfile
   from specify_cli.next.runtime_bridge import get_or_start_run

   with tempfile.TemporaryDirectory() as td:
       tmp_repo = Path(td)
       (tmp_repo / ".kittify").mkdir()
       run = get_or_start_run('demo-research', tmp_repo, 'research')
       print("RUN_OK", run)
   ```
2. Expected: prints `RUN_OK <handle>` with no exception.
3. Before WP01 lands, the same call raises `MissionRuntimeError: Mission 'research' not found` (or "no steps"). After WP01 lands, it succeeds. This is the v1 P0 finding being closed.
4. Capture the verbatim output of this script in your commit message under a `Runnability proof:` section.

**Files**: no edits in T005; this is a proof step.

## Definition of Done

- [ ] 8 new files exist under `owned_files`.
- [ ] `mission-runtime.yaml` (both copies) load via Pydantic with `mission.key == "research"` and 6 steps.
- [ ] All 6 prompt templates exist with research-specific content.
- [ ] Runnability proof from T005 produces `RUN_OK` with no `MissionRuntimeError`.
- [ ] No edits outside `owned_files`.
- [ ] mypy --strict + ruff zero new findings on the changed paths.

## Test Strategy

WP01 does not add formal tests. T005 is a runnability smoke. WP04 (composition resolution) and WP06 (real-runtime walk) own the formal tests for SC-001/SC-002.

## Risks

| Risk | Mitigation |
|---|---|
| `mission-runtime.yaml` schema drift between software-dev's file and the schema. | Implementer reads schema.py:401-450 first and validates via `load_mission_template_file()`. |
| Prompt templates referenced by `prompt_template:` not on disk. | T004 creates all 6 files explicitly. |
| `agent-profile` YAML alias vs `agent_profile` Python field name. | Use `agent-profile` in YAML (matches software-dev). |

## Reviewer Guidance

- Diff `src/specify_cli/missions/research/mission-runtime.yaml` and `src/doctrine/missions/research/mission-runtime.yaml`. Confirm 6 steps, correct depends_on chain, profiles match D2 (researcher-robbie ×4 + reviewer-renata for output).
- Run the T005 proof script yourself from a fresh tmp dir.
- `git diff` should show only the 8 new files.

## Activity Log

- 2026-04-26T12:05:52Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=7384 – Assigned agent via action command
- 2026-04-26T12:10:04Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=7384 – Ready for review: mission-runtime sidecar + 6 templates; runnability proof captured
