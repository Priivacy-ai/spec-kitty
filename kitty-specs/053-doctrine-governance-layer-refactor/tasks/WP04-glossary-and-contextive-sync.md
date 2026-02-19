---
work_package_id: WP04
title: Glossary and Contextive Sync
lane: "done"
dependencies:
- WP02
base_branch: 053-doctrine-governance-layer-refactor-WP02
base_commit: 2e21dcf7e979d67415b2f431c64fefc20fee0bc6
created_at: '2026-02-17T15:48:02.758964+00:00'
subtasks:
- T021
- T022
- T023
- T024
- T025
phase: Phase 3 - Canonicalization and Validation
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

# Work Package Prompt: WP04 – Glossary and Contextive Sync

## Implementation Command

```bash
spec-kitty implement WP04 --base WP02
```

Depends on WP02 and WP03.

## Objectives & Success Criteria

1. Canonical glossary terminology fully matches governance model decisions.
2. Research/Contracts terms are present and correctly linked semantically.
3. Contextive compilation script runs cleanly from venv.
4. Generated `.kittify/memory` glossary outputs parse without YAML errors.
5. Regression tests prevent known serialization/parsing breakage.

## Context & Constraints

- Canonical source: `glossary/`
- Compiler: `scripts/chores/glossary-compilation.py`
- Generated target: `.kittify/memory/`

Use canonical glossary as source of truth; generated files are build artifacts.

## Subtasks & Guidance

### T021-T023: Canonical term alignment

- Ensure all governance-layer terms reflect agreed definitions.
- Align feature artifacts where term names changed (`Approach` to `Paradigm`, etc.).

### T024: Compile and verify

- Activate venv and execute compiler script.
- Verify generated context files are parser-safe and structurally valid.

### T025: Add regression checks

- Add checks for known failure patterns encountered earlier:
  - non-string metadata serialization
  - malformed sequence/map structure in glossary YAML

## Risks & Mitigations

- Risk: manual edits in generated files diverge from source.
  Mitigation: treat generated files as compiler output only.
- Risk: parser compatibility regressions.
  Mitigation: run parser validation in tests/CI.

## Activity Log

- 2026-02-17T15:48:02Z – codex_nonKitty – shell_pid=170105 – lane=doing – Assigned agent via workflow command
- 2026-02-17T15:50:19Z – codex_nonKitty – shell_pid=170105 – lane=for_review – Ready for review: glossary alignment + compilation hardening + regression checks
- 2026-02-17T15:51:53Z – codex_nonKitty – shell_pid=170105 – lane=doing – Started review via workflow command
- 2026-02-17T15:52:04Z – codex_nonKitty – shell_pid=170105 – lane=done – Review passed: glossary alignment, compiler hardening, and YAML regression coverage
