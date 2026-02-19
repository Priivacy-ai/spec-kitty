---
description: Curate external concepts and import them into doctrine artifacts with traceable adoption records.
---
**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `src/doctrine/curation/imports/<source-id>/`). Never refer to a folder by name alone.


*Path: [templates/commands/doctrine.md](templates/commands/doctrine.md)*


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Doctrine Options

- `curate`: Use this when the user wants to add external practices by **importing into the spec kitty doctrine layer**.

## `curate` Workflow

1. Identify the external source and the concepts to import (for example ATDD, TDD, ZOMBIES).
2. Create or update `src/doctrine/curation/imports/<source-id>/manifest.yaml`.
3. Create one candidate file per concept in `src/doctrine/curation/imports/<source-id>/candidates/*.import.yaml`.
4. Populate provenance in each candidate `source` section (`title`, `type`, `publisher`, `url`/path, `accessed_on`).
5. Classify each candidate to doctrine targets (`tactic`, `directive`, etc.) with rationale.
6. Add adaptation notes translating source language into Spec Kitty doctrine terms.
7. Materialize resulting doctrine artifacts (for example `src/doctrine/tactics/*.tactic.yaml`, `src/doctrine/directives/*.directive.yaml`).
8. Update directive links (`tactic_refs`) so curated tactics are active in governance behavior.
9. Mark candidate status through review to `adopted` and ensure `resulting_artifacts` is complete.
10. Run validation:
    - `pytest -q tests/unit/test_doctrine_curation.py tests/doctrine/test_schema_validation.py`
    - optionally run focused checks on newly created artifacts and candidates.

## Output Requirements

- Report created/updated files with concrete paths.
- State how each imported concept maps to doctrine artifacts.
- Confirm directive linkage updates (for example `TEST_FIRST` references).
- Report validation results and any remaining follow-up items.
