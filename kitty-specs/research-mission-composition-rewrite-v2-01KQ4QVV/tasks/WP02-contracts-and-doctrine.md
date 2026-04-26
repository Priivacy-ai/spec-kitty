---
work_package_id: WP02
title: 5 Step Contracts + 10 Action Doctrine Bundles
dependencies: []
requirement_refs:
- FR-006
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
agent: "claude:opus-4.7:reviewer-renata:reviewer"
shell_pid: "36279"
history:
- timestamp: '2026-04-26T11:46:43Z'
  actor: claude
  note: Created during /spec-kitty.tasks for mission research-mission-composition-rewrite-v2-01KQ4QVV
authoritative_surface: src/doctrine/missions/research/actions/
execution_mode: code_change
mission_id: 01KQ4QVVZ4DC6CXA1XCZZAQ8AG
mission_slug: research-mission-composition-rewrite-v2-01KQ4QVV
owned_files:
- src/doctrine/mission_step_contracts/shipped/research-scoping.step-contract.yaml
- src/doctrine/mission_step_contracts/shipped/research-methodology.step-contract.yaml
- src/doctrine/mission_step_contracts/shipped/research-gathering.step-contract.yaml
- src/doctrine/mission_step_contracts/shipped/research-synthesis.step-contract.yaml
- src/doctrine/mission_step_contracts/shipped/research-output.step-contract.yaml
- src/doctrine/missions/research/actions/scoping/index.yaml
- src/doctrine/missions/research/actions/scoping/guidelines.md
- src/doctrine/missions/research/actions/methodology/index.yaml
- src/doctrine/missions/research/actions/methodology/guidelines.md
- src/doctrine/missions/research/actions/gathering/index.yaml
- src/doctrine/missions/research/actions/gathering/guidelines.md
- src/doctrine/missions/research/actions/synthesis/index.yaml
- src/doctrine/missions/research/actions/synthesis/guidelines.md
- src/doctrine/missions/research/actions/output/index.yaml
- src/doctrine/missions/research/actions/output/guidelines.md
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

# WP02 — 5 Step Contracts + 10 Action Doctrine Bundles

## Objective

Re-author the contracts and doctrine bundles that the v1 attempt got right. The shipped step contracts under `src/doctrine/mission_step_contracts/shipped/research-*.step-contract.yaml` and the action doctrine bundles under `src/doctrine/missions/research/actions/<action>/` are correct in shape and content. Reference the v1 tag `attempt/research-composition-mission-100-broken` for source content; do NOT merge from the tag (clean history).

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Execution worktree: lane-based, allocated by `spec-kitty implement WP02`.

## Implementation Command

```bash
spec-kitty agent action implement WP02 --agent <name>
```

## Authoritative References

- `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/plan.md` — D5 (re-author from scratch)
- v1 tag: `git show attempt/research-composition-mission-100-broken:src/doctrine/mission_step_contracts/shipped/research-scoping.step-contract.yaml` (and the other 4 contracts; and the 10 doctrine bundle files)
- Software-dev contracts at `src/doctrine/mission_step_contracts/shipped/{specify,plan,tasks,implement,review}.step-contract.yaml` (schema reference)
- Software-dev action doctrine at `src/doctrine/missions/software-dev/actions/<action>/{index.yaml,guidelines.md}` (bundle reference)

## Subtask T006 — Reference v1 tag artifacts

**Purpose**: Pull the verbatim content the v1 attempt produced (which was correct in shape) into your worktree as a starting point. You are re-authoring, not merging.

**Steps**:
1. From the worktree, list the v1 artifact paths:
   ```bash
   git show attempt/research-composition-mission-100-broken --stat | grep -E "research-.*step-contract\\.yaml|missions/research/actions"
   ```
2. For each path, extract the v1 content:
   ```bash
   git show attempt/research-composition-mission-100-broken:src/doctrine/mission_step_contracts/shipped/research-scoping.step-contract.yaml > /tmp/v1-research-scoping.yaml
   ```
   …and similarly for the other 14 files (4 contracts + 10 bundle files).
3. Read each. Note the schema fields used: contracts have `schema_version`, `id`, `action`, `mission`, `steps[]` (each step with `id`, `description`, optional `command`, `delegates_to`, `guidance`, `inputs`); bundles have `index.yaml` with `action`, `directives`, `tactics`, `styleguides`, `toolguides`, `procedures` and `guidelines.md` as plain markdown.
4. Importantly: the v1 `output/guidelines.md` already includes the literal `gate_passed("publication_approved")` token (cycle-2 fix). Preserve it.

**Files**: read-only.

## Subtask T007 — Author 5 step contract YAMLs

**Steps**:
1. Create the 5 contract files under `src/doctrine/mission_step_contracts/shipped/research-{scoping,methodology,gathering,synthesis,output}.step-contract.yaml`.
2. Use the v1 content from T006 verbatim where it was correct. If you spot any improvement opportunity, defer it to a follow-up — D5 is "re-author on corrected substrate," not "improve."
3. Each contract: `mission: research`, `action: <name>`, schema mirrors the existing software-dev contracts.
4. Validate via `MissionStepContractRepository().list_all()`:
   ```python
   from specify_cli.mission_step_contracts.repository import MissionStepContractRepository
   contracts = sorted([(c.mission, c.action) for c in MissionStepContractRepository().list_all()])
   print(contracts)
   ```
   Expect 10 entries: 5 software-dev + 5 research.

**Files**: 5 new contract YAMLs.

## Subtask T008 — Author 10 action doctrine bundle files

**Steps**:
1. Create directories: `src/doctrine/missions/research/actions/{scoping,methodology,gathering,synthesis,output}/`.
2. In each directory, author `index.yaml` and `guidelines.md` (10 files total). Pull verbatim from v1 tag content.
3. `index.yaml` fields: `action`, `directives` (list of slugs), `tactics` (list of slugs). Match v1's shape.
4. `guidelines.md`: plain markdown. The `output/guidelines.md` MUST contain the literal `gate_passed("publication_approved")` token; preserve from v1 cycle-2.
5. **Validate every slug against current shipped doctrine, not blindly preserve from v1.** For each directive/tactic slug an `index.yaml` references, verify the file exists at `src/doctrine/directives/shipped/<slug>*` or `src/doctrine/tactics/shipped/<slug>*` on the current baseline. If a v1 slug is stale (renamed/removed since the tag was created), substitute the closest current equivalent and document the substitution in the commit message. The slugs you keep here MUST also appear in WP03's per-action edge map — if a bundle references a slug WP03's graph doesn't edge to, either add the edge in WP03 or drop the slug here. Coordinate with WP03 reviewer.
6. Validate via the doctrine resolver:
   ```python
   from specify_cli.missions.repository import MissionTemplateRepository  # whatever the actual import is
   from specify_cli.next._internal_runtime.discovery import load_mission_template
   # ... load the 5 bundles
   ```

**Files**: 10 new files.

## Subtask T009 — Smoke-load both repositories

**Steps**:
1. From the worktree, run an ad-hoc Python check that confirms:
   - `MissionStepContractRepository().list_all()` returns 10 entries with the expected (mission, action) pairs.
   - `MissionTemplateRepository.get_action_guidelines("research", action)` returns non-empty content for each of 5 actions.
   - `load_action_index(...)` returns a populated `ActionIndex` for each.
2. Capture verbatim output in your commit message.
3. **NOTE**: This smoke proves loaders see the files. The DRG validation (whether composition's `resolve_context` returns non-empty `artifact_urns`) is WP03's responsibility — they are different surfaces. Don't conflate them.

**Files**: no edits in T009.

## Definition of Done

- [ ] 15 new files exist under `owned_files` (5 contracts + 10 bundle files).
- [ ] All 5 contracts load via the repository; (mission, action) pairs match expectations.
- [ ] All 5 doctrine bundles load via the resolver; non-empty content per action.
- [ ] `output/guidelines.md` contains the literal `gate_passed("publication_approved")` token.
- [ ] No edits outside `owned_files`.
- [ ] No software-dev contracts or doctrine modified.
- [ ] mypy --strict + ruff zero new findings.

## Test Strategy

WP02 does not add formal tests. T009 is a smoke check. WP04 owns the formal contract+doctrine resolution test.

## Risks

| Risk | Mitigation |
|---|---|
| v1 schema drift since the tag was created. | Cross-check with software-dev contracts before authoring. |
| Wrong file naming pattern. | Software-dev uses `<action>.step-contract.yaml`; research uses `research-<action>.step-contract.yaml` (per the existing repository's loader convention; verify by listing the shipped/ dir). |
| Doctrine resolver failures from missing referenced URNs. | T009 catches this; if a referenced directive/tactic doesn't exist, fix the index.yaml ref. |

## Reviewer Guidance

- Confirm 15 new files in the diff.
- Confirm software-dev contracts and doctrine are byte-identical to baseline.
- Spot-check `output/guidelines.md` for the `gate_passed("publication_approved")` literal.

## Activity Log

- 2026-04-26T12:16:40Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=22421 – Started implementation via action command
- 2026-04-26T12:21:52Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=22421 – WP02: 15 files (5 contracts + 10 bundles) authored from v1 substrate; T009 smoke validates 10 contracts, 5 guidelines, 5 indices; gate token preserved
- 2026-04-26T12:23:51Z – claude:opus-4.7:reviewer-renata:reviewer – shell_pid=36279 – Started review via action command
