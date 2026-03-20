---
work_package_id: WP06
title: Constitution Git Policy Enforcement
lane: planned
dependencies: []
subtasks:
- T023
- T024
- T025
- T026
phase: Phase 2 - Policy
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-20T13:39:48Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-017
- FR-018
- FR-019
- NFR-004
---

# Work Package Prompt: WP06 – Constitution Git Policy Enforcement

## Objectives & Success Criteria

- `.kittify/constitution/references.yaml` is gitignored (local machine state, merge-conflict-prone).
- `.kittify/constitution/interview/answers.yaml` and `library/*.md` are tracked (shared team knowledge).
- `state_contract.py` classifications match the enforced `.gitignore` reality.
- Tests validate the alignment.

## Context & Constraints

- **User decision**: Constitution itself is committed (project way of working). Only `references.yaml` is ignored (local machine-specific, causes merge conflicts).
- **Plan reference**: Design decision D3 in plan.md.
- **Data model**: See `data-model.md` → ".gitignore Changes" and "Constitution Surfaces (reclassified)".
- **Constraint C-005**: No force-removal from Git history.
- **Current state**: `references.yaml` is classified as `DERIVED` / `INSIDE_REPO_NOT_IGNORED` with a "deferred" note.

## Implementation Command

```bash
spec-kitty implement WP06
```

## Subtasks & Detailed Guidance

### Subtask T023 – Add `references.yaml` to .gitignore

**Purpose**: Prevent `references.yaml` (local machine-specific state) from being tracked.

**Steps**:

1. In `.gitignore` at the repo root, find the constitution section (around lines 57-60):
   ```
   .kittify/constitution/context-state.json
   .kittify/constitution/directives.yaml
   .kittify/constitution/governance.yaml
   .kittify/constitution/metadata.yaml
   ```

2. Add below this block:
   ```
   .kittify/constitution/references.yaml
   ```

3. **Scope tightly**: Use the exact path `.kittify/constitution/references.yaml` — NOT a wildcard like `references.*` or `*.yaml` that could catch other files.

4. Do NOT add `answers.yaml` or `library/*.md` — those must remain tracked.

**Files**: `.gitignore` (MODIFY)

**Validation**:
```bash
git check-ignore .kittify/constitution/references.yaml
# Should output: .kittify/constitution/references.yaml

git check-ignore .kittify/constitution/interview/answers.yaml
# Should output nothing (not ignored)

git check-ignore .kittify/constitution/library/example.md
# Should output nothing (not ignored)
```

### Subtask T024 – Update state_contract.py constitution entries

**Purpose**: Align state contract classifications with the enforced Git policy.

**Steps**:

1. In `src/specify_cli/state_contract.py`, find the constitution surfaces (section B, around lines 237-311).

2. Update `constitution_references`:
   - Change `authority` from `AuthorityClass.DERIVED` to `AuthorityClass.LOCAL_RUNTIME`
   - Change `git_class` from `GitClass.INSIDE_REPO_NOT_IGNORED` to `GitClass.IGNORED`

3. Update `constitution_library`:
   - Change `authority` from `AuthorityClass.DERIVED` to `AuthorityClass.AUTHORITATIVE`
   - Change `git_class` from `GitClass.INSIDE_REPO_NOT_IGNORED` to `GitClass.TRACKED`

4. Update `constitution_interview_answers`:
   - Change `git_class` from `GitClass.INSIDE_REPO_NOT_IGNORED` to `GitClass.TRACKED`
   - Keep `authority` as `AuthorityClass.AUTHORITATIVE` (already correct)

**Files**: `src/specify_cli/state_contract.py` (MODIFY)

### Subtask T025 – Remove "deferred" notes from state contract

**Purpose**: The "Git boundary decision deferred to constitution cleanup sprint" notes are now resolved.

**Steps**:

1. In `src/specify_cli/state_contract.py`, find the `notes=` fields on the constitution entries that contain "deferred" language.

2. Replace with a note referencing this feature:
   - `notes="Policy enforced in feature 054: commit answers + library, ignore references"`
   - Or simply remove the deferred note if the entry is self-explanatory.

**Files**: `src/specify_cli/state_contract.py` (MODIFY — same file as T024)

### Subtask T026 – Test new constitution classifications

**Purpose**: Validate that state contract, `.gitignore`, and Git reality are aligned.

**Steps**:

1. In `tests/specify_cli/test_state_contract.py`, add or update tests:

   - **test_constitution_references_is_ignored**: Assert `constitution_references` has `authority=LOCAL_RUNTIME` and `git_class=IGNORED`.
   - **test_constitution_library_is_authoritative**: Assert `constitution_library` has `authority=AUTHORITATIVE` and `git_class=TRACKED`.
   - **test_constitution_answers_is_authoritative**: Assert `constitution_interview_answers` has `authority=AUTHORITATIVE` and `git_class=TRACKED`.
   - **test_no_deferred_notes_remain**: Assert no state surface `notes` field contains the word "deferred".

2. If there's an existing test that validates `.gitignore` alignment with state contract, update it to include the new `references.yaml` ignore rule.

**Files**: `tests/specify_cli/test_state_contract.py` (MODIFY)

**Validation**:
```bash
pytest tests/specify_cli/test_state_contract.py -v
```

## Risks & Mitigations

- **Already-tracked `references.yaml`**: If `references.yaml` is already in Git history, adding to `.gitignore` stops future tracking but doesn't remove from history. This is intentional (C-005).
- **Other constitution surfaces**: Only `references.yaml` gets ignored. `governance.yaml`, `directives.yaml`, etc. are already correctly ignored. `constitution.md`, `answers.yaml`, `library/*.md` must stay tracked.

## Review Guidance

- Verify `.gitignore` entry is scoped to exactly `.kittify/constitution/references.yaml`.
- Verify `answers.yaml` and `library/*.md` are NOT in `.gitignore`.
- Verify state contract changes match the data-model.md table.
- Verify no "deferred" notes remain in state contract.

## Activity Log

- 2026-03-20T13:39:48Z – system – lane=planned – Prompt created.
