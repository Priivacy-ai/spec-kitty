# Tasks: Canonical Baseline and Repository Boundary

**Mission**: 081-canonical-baseline-and-repository-boundary
**Date**: 2026-04-10
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)

## Subtask Index

| ID | Description | WP | Parallel |
|----|------------|----|---------| 
| T001 | Audit existing glossary entries for conflicts with canonical terms | WP01 | | [D] |
| T002 | Update `orchestration.md` — fix `Project` definition, add `Repository` and `Build` | WP01 | | [D] |
| T003 | Add domain terms to glossary seed file (project, repository, build) | WP01 | | [D] |
| T004 | Update `spec_kitty_core.yaml` — deprecate `project root checkout`, add `repository root checkout` | WP01 | | [D] |
| T005 | Add identity field terms to seed file (repository_uuid, repository_label, project_uuid, repo_slug, build_id, node_id) | WP01 | | [D] |
| T006 | Create `glossary/contexts/identity-fields.md` — identity layer reference | WP01 | | [D] |
| T007 | Update `glossary/contexts/configuration-project-structure.md` — align with canonical terminology | WP02 | [P] |
| T008 | Create `docs/reference/terminology.md` — human-readable terminology reference | WP02 | [P] |
| T009 | Validate no glossary conflicts and run existing glossary tests | WP02 | |

## Work Packages

### WP01: Glossary Canonical Terms and Identity Fields

**Priority**: P0 (foundational — all other artifacts reference these definitions)
**Dependencies**: None
**Prompt**: [tasks/WP01-glossary-canonical-terms.md](tasks/WP01-glossary-canonical-terms.md)
**Estimated size**: ~350 lines

**Summary**: Add the canonical 3-tier terminology (project, repository, build) and 6 identity field definitions to the glossary system. Fix the existing `Project` definition in orchestration context, deprecate `project root checkout` in favor of `repository root checkout`, and create an identity-fields reference document.

**Included subtasks**:

- [x] T001 Audit existing glossary entries for conflicts with canonical terms (WP01)
- [x] T002 Update `orchestration.md` — fix `Project` definition, add `Repository` and `Build` (WP01)
- [x] T003 Add domain terms to glossary seed file (project, repository, build) (WP01)
- [x] T004 Update `spec_kitty_core.yaml` — deprecate `project root checkout`, add `repository root checkout` (WP01)
- [x] T005 Add identity field terms to seed file (repository_uuid, repository_label, project_uuid, repo_slug, build_id, node_id) (WP01)
- [x] T006 Create `glossary/contexts/identity-fields.md` — identity layer reference (WP01)

**Implementation sketch**:
1. Read all existing glossary seed files and context docs to identify conflicts
2. Update `orchestration.md` with corrected `Project` definition and new `Repository`, `Build` entries
3. Add domain terms and identity field terms to `spec_kitty_core.yaml` seed file
4. Deprecate `project root checkout`, add `repository root checkout` in seed file
5. Create `identity-fields.md` context document for all 6 identity fields

**Parallel opportunities**: T003-T005 can be done in sequence within the seed file; T002 and T006 touch different files and could be done in parallel.

**Risks**: The existing `Project` definition in `orchestration.md` is canonical — changing it requires careful wording that makes clear the old definition is superseded by the new canonical model introduced by mission 081.

---

### WP02: Documentation Reference and Validation

**Priority**: P1 (depends on WP01 glossary entries being in place)
**Dependencies**: WP01
**Prompt**: [tasks/WP02-docs-reference-and-validation.md](tasks/WP02-docs-reference-and-validation.md)
**Estimated size**: ~300 lines

**Summary**: Create a human-readable terminology reference document in `docs/reference/`, update the configuration-project-structure glossary context to align with canonical terminology, and validate all glossary entries are conflict-free and well-formed.

**Included subtasks**:

- [ ] T007 Update `glossary/contexts/configuration-project-structure.md` — align with canonical terminology (WP02)
- [ ] T008 Create `docs/reference/terminology.md` — human-readable terminology reference (WP02)
- [ ] T009 Validate no glossary conflicts and run existing glossary tests (WP02)

**Implementation sketch**:
1. Update `configuration-project-structure.md` to use "repository" instead of "project" where the Git resource is meant
2. Create `docs/reference/terminology.md` based on the canonical definitions from spec.md and quickstart.md
3. Run `spec-kitty glossary conflicts --json` to check for unresolved semantic conflicts
4. Run `pytest tests/ -k glossary` to verify all glossary entries are well-formed

**Parallel opportunities**: T007 and T008 touch different files and can be done in parallel. T009 must run last.

**Risks**: The configuration-project-structure context uses "project" throughout in ways that match the old meaning; updating it needs care to avoid breaking cross-references to `orchestration.md`.
