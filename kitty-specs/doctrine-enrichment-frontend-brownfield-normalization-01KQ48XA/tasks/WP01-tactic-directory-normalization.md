---
work_package_id: WP01
title: Tactic Directory Normalization
dependencies: []
requirement_refs:
- FR-004
planning_base_branch: feature/doctrine-enrichment-bdd-profiles
merge_target_branch: feature/doctrine-enrichment-bdd-profiles
branch_strategy: Planning artifacts for this feature were generated on feature/doctrine-enrichment-bdd-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/doctrine-enrichment-bdd-profiles unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-enrichment-frontend-brownfield-normalization-01KQ48XA
base_commit: 6bcf2d94a7fee98c225cf7a3988c6240f380863a
created_at: '2026-04-26T11:42:41.874891+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "80879"
history:
- timestamp: '2026-04-26T08:49:24Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: src/doctrine/tactics/shipped/communication/
execution_mode: code_change
owned_files:
- src/doctrine/tactics/shipped/communication/adr-drafting-workflow.tactic.yaml
- src/doctrine/tactics/shipped/communication/decision-marker-capture.tactic.yaml
- src/doctrine/tactics/shipped/communication/documentation-curation-audit.tactic.yaml
- src/doctrine/tactics/shipped/communication/glossary-curation-interview.tactic.yaml
- src/doctrine/tactics/shipped/communication/stakeholder-alignment.tactic.yaml
- src/doctrine/tactics/shipped/communication/traceable-decisions.tactic.yaml
- src/doctrine/tactics/shipped/communication/usage-examples-sync.tactic.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, initialize the Curator Carla profile:

```
/ad-hoc-profile-load curator-carla
```

This profile governs doctrine curation work — consistency, completeness, and schema conformance are the primary success criteria.

---

## Objective

Move 7 communication-discipline `.tactic.yaml` files from the flat `src/doctrine/tactics/shipped/` root into `shipped/communication/`. This WP handles the `communication/` category only.

**Scope note**: The `analysis/`, `architecture/`, and `testing/` category moves are handled by WP02, WP03, and WP04 respectively, each alongside their new-file creation work. This division gives each category-owning WP full control of its directory.

**Constraint (C-001)**: Do not touch any Python loader code. The existing `rglob("*.tactic.yaml")` in `src/doctrine/base.py:119` handles subdirectories automatically.

**Constraint (C-002)**: The `id` field inside each YAML file is the canonical identity. Do not change it.

---

## Context

- Loader: `src/doctrine/base.py` line 119 uses `self._shipped_dir.rglob(self._glob)` — subdirectories are already supported
- Reference implementation: `src/doctrine/tactics/shipped/refactoring/` (already categorized)
- Pre-move tactic count (canonical baseline): establish this at WP01 start with `python3 -c "import sys; sys.path.insert(0,'src'); from doctrine.tactics.repository import TacticRepository; r = TacticRepository(); print(len(r.load_all()))"`. Record the number — WP02/03/04 use this as the NFR-003 reference count.
- Test command: `pytest -m doctrine -q` — must be green before AND after

---

## Subtask T001 — Create `testing/` and move testing tactics

**Purpose**: Group all testing-discipline tactics under `shipped/testing/`.

**Files to move** (15 tactics):
```
acceptance-test-first.tactic.yaml
atdd-adversarial-acceptance.tactic.yaml
black-box-integration-testing.tactic.yaml
formalized-constraint-testing.tactic.yaml
function-over-form-testing.tactic.yaml
mutation-testing-workflow.tactic.yaml
no-parallel-duplicate-test-runs.tactic.yaml
quality-gate-verification.tactic.yaml
tdd-red-green-refactor.tactic.yaml
test-boundaries-by-responsibility.tactic.yaml
testing-select-appropriate-level.tactic.yaml
test-minimisation.tactic.yaml
test-pyramid-progression.tactic.yaml
test-to-system-reconstruction.tactic.yaml
zombies-tdd.tactic.yaml
```

**Steps**:
1. `mkdir src/doctrine/tactics/shipped/testing/`
2. Move each file: `mv src/doctrine/tactics/shipped/<name>.tactic.yaml src/doctrine/tactics/shipped/testing/`
3. Do NOT modify any YAML content — only the filesystem path changes

**Validation**: `ls src/doctrine/tactics/shipped/testing/ | wc -l` should show 15.

---

## Subtask T002 — Create `analysis/` and move analysis tactics

**Purpose**: Group analysis and discovery tactics under `shipped/analysis/`.

**Files to move** (13 tactics):
```
ammerse-impact-analysis.tactic.yaml
analysis-extract-before-interpret.tactic.yaml
bounded-context-canvas-fill.tactic.yaml
bounded-context-identification.tactic.yaml
connascence-analysis.tactic.yaml
context-boundary-inference.tactic.yaml
context-mapping-classification.tactic.yaml
entity-value-object-classification.tactic.yaml
premortem-risk-identification.tactic.yaml
requirements-validation-workflow.tactic.yaml
reverse-speccing.tactic.yaml
safe-to-fail-experiment.tactic.yaml
strategic-domain-classification.tactic.yaml
```

**Steps**: Same as T001 — mkdir + mv each file.

**Validation**: `ls src/doctrine/tactics/shipped/analysis/ | wc -l` should show 13 (more will be added by WP02, but this is the baseline).

---

## Subtask T003 — Create `communication/` and move communication tactics

**Purpose**: Group documentation, decision, and stakeholder communication tactics under `shipped/communication/`.

**Files to move** (7 tactics):
```
adr-drafting-workflow.tactic.yaml
decision-marker-capture.tactic.yaml
documentation-curation-audit.tactic.yaml
glossary-curation-interview.tactic.yaml
stakeholder-alignment.tactic.yaml
traceable-decisions.tactic.yaml
usage-examples-sync.tactic.yaml
```

**Steps**: Same pattern — mkdir + mv.

**Validation**: `ls src/doctrine/tactics/shipped/communication/ | wc -l` should show 7.

---

## Subtask T004 — Create `architecture/` and move architecture tactics

**Purpose**: Group structural and design tactics under `shipped/architecture/`.

**Files to move** (12 tactics):
```
aggregate-boundary-design.tactic.yaml
anti-corruption-layer.tactic.yaml
architecture-diagram-review-checklist.tactic.yaml
atomic-design-review-checklist.tactic.yaml
atomic-state-ownership.tactic.yaml
c4-zoom-in-architecture-documentation.tactic.yaml
compositional-stream-boundaries.tactic.yaml
cross-cutting-state-via-store.tactic.yaml
dependency-hygiene.tactic.yaml
domain-event-capture.tactic.yaml
language-driven-design.tactic.yaml
problem-decomposition.tactic.yaml
```

**Steps**: Same pattern — mkdir + mv.

**Validation**: `ls src/doctrine/tactics/shipped/architecture/ | wc -l` should show 12 (more will be added by WP03, but this is the baseline).

**Tactics remaining in `shipped/` root** (do NOT move these):
`avoid-gold-plating`, `autonomous-operation-protocol`, `behavior-driven-development`, `change-apply-smallest-viable-diff`, `code-review-incremental`, `easy-to-change`, `eisenhower-prioritisation`, `input-validation-fail-fast`, `locality-of-change`, `occurrence-classification-workflow`, `review-intent-and-risk-first`, `secure-design-checklist`, `stopping-conditions`, `work-package-completion-validation`

---

## Subtask T005 — Verify with doctrine test suite

**Purpose**: Confirm no tactics were lost and schema validation is clean.

**Steps**:
1. Capture post-move count:
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'src')
   from doctrine.tactics.repository import TacticRepository
   r = TacticRepository()
   all_tactics = r.load_all()
   print(f'Tactic count: {len(all_tactics)}')
   "
   ```
2. Assert count equals pre-move baseline (from context above)
3. Run `pytest -m doctrine -q` — must be fully green

**Validation checklist**:
- [ ] `testing/` has exactly 15 files
- [ ] `analysis/` has exactly 13 files
- [ ] `communication/` has exactly 7 files
- [ ] `architecture/` has exactly 12 files
- [ ] Tactic count after == tactic count before
- [ ] `pytest -m doctrine -q` exits 0

---

## Branch Strategy

Worktree allocated to lane computed from `lanes.json`. All changes commit to and merge into `feature/doctrine-enrichment-bdd-profiles`. Do not push to `main` directly.

Implementation command:
```bash
spec-kitty agent action implement WP01 --agent claude
```

---

## Definition of Done

- All 47 tactics (T001–T004 total) are in their target subdirectories
- No YAML content was modified — only filesystem paths changed
- `pytest -m doctrine -q` is fully green
- Post-move tactic count equals pre-move count
- No tactics were accidentally left in their source location

## Reviewer Guidance

- Diff should show only file renames (git tracks these as `R` — renamed)
- Spot-check 3 random moved files: open each and confirm YAML `id` field is unchanged
- Run `pytest -m doctrine -q` independently to verify
- Confirm 14 tactics remain in `shipped/` root (the cross-cutting ones listed in T004)

## Activity Log

- 2026-04-26T11:47:18Z – claude – shell_pid=76018 – 7 communication tactics moved to shipped/communication/; baseline=80, post-move=80; doctrine tests green
- 2026-04-26T12:10:55Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=80879 – Started review via action command
- 2026-04-26T12:13:07Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=80879 – Review passed: 7 communication tactics renamed to shipped/communication/ with 100% similarity (pure renames, no content changes). IDs intact. 7/7 files verified. Doctrine tests green.
- 2026-04-26T13:10:13Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=80879 – Done override: Feature merged to feature/doctrine-enrichment-bdd-profiles (squash merge commit 7383936b2)
