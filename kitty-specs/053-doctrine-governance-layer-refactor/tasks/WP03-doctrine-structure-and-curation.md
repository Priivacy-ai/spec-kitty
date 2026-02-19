---
work_package_id: WP03
title: Doctrine Structure and Curation Scaffold
lane: "done"
dependencies:
- WP01
base_branch: develop
base_commit: dcf00102135c80e12c2d185e7ce534f6e835d22b
created_at: '2026-02-17T15:44:57.246956+00:00'
subtasks:
- T016
- T017
- T018
- T019
- T020
phase: Phase 2 - Doctrine Structure
assignee: ''
agent: "codex_nonKitty"
shell_pid: '170105'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-17T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Doctrine Structure and Curation Scaffold

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

Depends on WP01 for schema constraints.

## Objectives & Success Criteria

1. Doctrine structure includes the agreed governance directories, including `schemas` and `agent-profiles`.
2. `curation/README.md` explains pull-based assimilation intent and process.
3. Import-candidate artifact template/sample captures provenance, mapping, adaptation, and status.
4. Tests verify curation traceability requirements.

## Context & Constraints

- Proposed structure source: `work/ideas/2026-02-17-doctrine-v2-final-proposal.md`
- User journey reference: `architecture/journeys/004-curating-external-practice-into-governance.md`
- Glossary authority: `glossary/contexts/governance.md`

Maintain backward compatibility for existing mission files under `src/doctrine/missions`.

## Subtasks & Guidance

### T016: Scaffold directories

- Add the agreed governance structure and ensure naming consistency with glossary terms.

### T017: Add curation README

- Document curation intent, scope, and process.
- Include the ZOMBIES TDD example flow.

### T018: Add import-candidate sample

- Provide canonical sample with source metadata, target classification, adaptation notes, and lifecycle status.

### T019-T020: Add validation and traceability tests

- Validate curation sample against schema.
- Assert links to resulting doctrine artifacts are required at adoption state.

## Risks & Mitigations

- Risk: structure diverges from architecture proposal.
  Mitigation: assert expected paths in tests.
- Risk: curation assets drift from terminology.
  Mitigation: cross-check against glossary canonical terms.

## Activity Log

- 2026-02-17T15:44:57Z – codex_nonKitty – shell_pid=170105 – lane=doing – Assigned agent via workflow command
- 2026-02-17T15:47:40Z – codex_nonKitty – shell_pid=170105 – lane=for_review – Ready for review: doctrine structure scaffold + curation README + import candidate validation
- 2026-02-17T15:51:32Z – codex_nonKitty – shell_pid=170105 – lane=doing – Started review via workflow command
- 2026-02-17T15:51:48Z – codex_nonKitty – shell_pid=170105 – lane=done – Review passed: doctrine structure scaffold, curation process docs, import candidate validation rules
