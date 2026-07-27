---
work_package_id: WP11
title: New Tactics & Supporting Artifacts
lane: "done"
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP07
- WP08
- WP09
base_branch: feature/agent-profile-implementation
base_commit: 1a7bcb7f34aa6169aba1725a434fe60f467978f3
created_at: '2026-03-04T05:12:22.979944+00:00'
subtasks:
- T064
- T065
- T066
- T067
- T068
phase: Phase 2 - Content
assignee: ''
agent: "claude-sonnet-4-6"
shell_pid: "46406"
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-26T04:36:22Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP11 – New Tactics & Supporting Artifacts

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Audit all enriched and new directives for `tactic-refs` that point to non-existent tactics
- Create new tactic YAML files for every unresolved reference
- Create new styleguide/toolguide YAML files if referenced by directives or tactics
- Every `tactic-ref` in every shipped directive resolves to a tactic file in `shipped/`
- All new artifacts validate against their respective schemas
- Only create artifacts that are actually referenced — no speculative creation

## Context & Constraints

- **Depends on WP02-04**: Repositories must exist for validation
- **Depends on WP07-09**: Enriched directives must be finalized to know which refs are needed
- **Reference material**: `src/doctrine/doctrine_ref/tactics/` for tactic content
- **Minimum viable tactic**: `schema-version`, `id`, `name`, `steps` (at least 1 step)

## Subtasks & Detailed Guidance

### Subtask T064 – Audit directives for unresolved tactic_refs

- **Purpose**: Build a complete list of tactic IDs referenced but not yet existing.
- **Steps**:
  1. Load all shipped directives via `DirectiveRepository().list_all()`
  2. Collect all unique `tactic_refs` values across all directives
  3. For each tactic ref, check if `TacticRepository().get(ref)` returns a result
  4. Build list of unresolved refs (tactic ID + which directive(s) reference it)
  5. Document the audit results as a comment in the implementation
  6. Also check `TacticReference` objects in shipped tactics — any references to non-existent artifacts?
- **Files**: No file changes — this is an audit step
- **Notes**: The output of this audit drives T065-T067. If no unresolved refs exist, T065-T067 may be no-ops.

### Subtask T065 – Create new tactic YAML files

- **Purpose**: Create tactic files for every unresolved tactic-ref.
- **Steps**:
  1. For each unresolved tactic ref from T064:
     - Check `src/doctrine/doctrine_ref/tactics/` for reference content
     - Create `src/doctrine/tactics/shipped/{tactic-id}.tactic.yaml`
     - Follow existing tactic schema structure:
       ```yaml
       schema-version: "1.0"
       id: {tactic-id}
       name: "{Human Readable Name}"
       purpose: |
         Description of what this tactic achieves.
       steps:
         - title: "Step 1 Name"
           description: |
             Detailed description of step 1.
         - title: "Step 2 Name"
           description: |
             Detailed description of step 2.
       ```
     - Minimum 2-3 steps per tactic (meaningful, not filler)
  2. Validate each new tactic against `tactic.schema.yaml`
  3. Verify `TacticRepository().get(tactic_id)` returns the new tactic
- **Files**: `src/doctrine/tactics/shipped/*.tactic.yaml` (new files, count depends on audit)
- **Parallel?**: Yes — each tactic file is independent
- **Notes**: Likely new tactics include those referenced by the new directives (020-026). Check the enriched directives (WP07-08) too for newly wired tactic-refs.

### Subtask T066 – Create new styleguide YAML files

- **Purpose**: Create styleguide files if any directives or tactics reference non-existent styleguides.
- **Steps**:
  1. Check all `TacticReference` objects where `type == "styleguide"`
  2. Verify each referenced styleguide exists in `StyleguideRepository`
  3. Create any missing styleguide files in `src/doctrine/styleguides/shipped/`
  4. Follow existing styleguide schema structure
  5. Validate against `styleguide.schema.yaml`
- **Files**: `src/doctrine/styleguides/shipped/*.styleguide.yaml` (new files if needed)
- **Notes**: May be a no-op if all styleguide references already resolve

### Subtask T067 – Create new toolguide YAML files

- **Purpose**: Create toolguide files if any references point to non-existent toolguides.
- **Steps**: Same pattern as T066 but for toolguides
- **Files**: `src/doctrine/toolguides/shipped/*.toolguide.yaml` (new files if needed)
- **Notes**: May be a no-op

### Subtask T068 – Validate all new artifacts against schemas

- **Purpose**: Final validation pass for all artifacts created in this WP.
- **Steps**:
  1. Load all new tactics via `TacticRepository` — verify no load errors
  2. Load all new styleguides/toolguides — verify no load errors
  3. Validate each against its schema using the validation utility
  4. Re-run the consistency check from T064 — all tactic-refs should now resolve
  5. Run `pytest tests/doctrine/test_consistency.py` — must pass
- **Files**: No new files — validation only
- **Notes**: This is the gate check — if consistency tests fail, new artifacts are incomplete

## Test Strategy

```bash
# Validate new artifacts load correctly
pytest tests/doctrine/ -v -k "consistency"

# Verify all tactic-refs resolve
python -c "
from doctrine.service import DoctrineService
s = DoctrineService()
unresolved = []
for d in s.directives.list_all():
    for ref in d.tactic_refs:
        if not s.tactics.get(ref):
            unresolved.append((d.id, ref))
if unresolved:
    print('UNRESOLVED:', unresolved)
else:
    print('All tactic-refs resolve!')
"
```

## Architectural Alignment

This WP produces artifacts consumed by the **Doctrine Catalog Loader** and validated by the **Schema Validation Gate** components (see `architecture/2.x/03_components/README.md`). Key invariants:

- Artifacts live in `src/doctrine/{type}/shipped/` — never in the project dir or outside the catalog
- All new files must pass their respective schema (`src/doctrine/schemas/`) before committing
- The `DoctrineService` aggregates lazily; new tactics/styleguides/toolguides are accessible via `DoctrineService().tactics.get(id)`, etc.
- No circular imports: none of the `{type}/` subpackages may import from `doctrine.service`

**Reference files:**
- Container view: `architecture/2.x/02_containers/README.md` (Doctrine Artifact Catalog)
- Component view: `architecture/2.x/03_components/README.md` (Doctrine Catalog Loader, Schema Validation Gate)
- Glossary: `glossary/contexts/doctrine.md`, `glossary/contexts/practices-principles.md`
- Doctrine reference material: `src/doctrine/doctrine_ref/tactics/`, `src/doctrine/doctrine_ref/directives/`

---

## ⚠️ Pre-Review Gate (Required Before Moving to `for_review`)

Before moving this WP to `for_review`, run the following checks on all **changed files** in this WP and fix any issues immediately:

```bash
# 1. Ruff lint (must be clean)
ruff check src/doctrine/tactics/shipped/ src/doctrine/styleguides/shipped/ src/doctrine/toolguides/shipped/

# 2. Mypy strict (must be clean on Python sources)
python -m mypy src/doctrine/tactics/ src/doctrine/styleguides/ src/doctrine/toolguides/ --strict --ignore-missing-imports

# 3. Tests (must pass)
pytest tests/doctrine/ -v -k "consistency or tactic or styleguide or toolguide"
```

Note: YAML files are not Python — ruff/mypy apply only to `.py` files. Schema validation is the gate for YAML artifacts (see T068).

---

## Risks & Mitigations

- **doctrine_ref tactics may be incomplete**: Some tactic references from enriched directives may not have corresponding doctrine_ref material — create minimal but meaningful tactic content
- **Cascade of missing artifacts**: One missing tactic may reference another missing styleguide — audit deeply before creating

## Review Guidance

- Verify every previously-unresolved tactic-ref now resolves
- Verify new tactics have meaningful content (not placeholder/filler)
- Verify no speculative artifacts created (only those actually referenced)
- Verify `test_consistency.py` passes

## Activity Log

- 2026-02-26T04:36:22Z – system – lane=planned – Prompt created.

---

### Implementation Command

All dependencies (WP01–WP09) are merged into `feature/agent-profile-implementation`. Branch directly from the feature branch:
```bash
spec-kitty implement WP11
```
No additional merges needed — the feature branch is the base.
- 2026-03-04T05:37:08Z – unknown – shell_pid=1539597 – lane=for_review – T064-T068 complete: 8 tactics, 14 directives wired, paradigm/directive/tactic schemas extended with tactic_refs+opposed_by, opposed_by wired on 024/025 and change-apply-smallest-viable-diff, DAG cycle detection test, 40 doctrine tests pass, architecture README updated with Doctrine Stack mermaid diagram.
- 2026-03-08T07:37:03Z – claude-sonnet-4-6 – shell_pid=46406 – lane=doing – Started review via workflow command
- 2026-03-08T08:15:40Z – claude-sonnet-4-6 – shell_pid=46406 – lane=done – Review passed: 13 tactics, 18 directives wired, all refs resolve, 521 tests pass. Fixed test-first directive naming: TEST_FIRST → DIRECTIVE_027 (027-test-first-development.directive.yaml).
