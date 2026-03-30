---
work_package_id: WP02
title: Model Local Support Declarations and Generated References
lane: "done"
dependencies:
- WP01
base_branch: 054-constitution-interview-compiler-and-bootstrap-WP01
base_commit: 485bf523d0e68f2d3403c70bce1a9e92f517cd03
created_at: '2026-03-09T16:35:41.722897+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
phase: Phase 1 - Compiler and Reference Model
assignee: claude
agent: claude
shell_pid: '410671'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-03-09T14:23:30Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-004
- FR-017
- FR-018
- NFR-001
---

# Work Package Prompt: WP02 - Model Local Support Declarations and Generated References

## ⚠️ IMPORTANT: Review Feedback Status

- If `review_status` is `has_feedback`, treat the feedback section below as blocking implementation work.
- Update the activity log as you complete material changes.

---

## Review Feedback

*[Empty initially.]*  

---

## Markdown Formatting

Wrap literal tags in backticks. Use fenced code blocks with language identifiers.

## Objectives & Success Criteria

- `ConstitutionInterview` can persist and reload explicit `local_supporting_files` declarations.
- Local support declarations accept only explicit file paths, with optional `action`, `target_kind`, and `target_id`.
- `compile_constitution()` produces `references.yaml` entries and `library_files` output metadata for local support files without copying them into a generated library directory.
- Conflict cases emit additive warnings instead of overriding shipped doctrine.
- Shipped-only runs remain deterministic and report `library_files: []`.

## Context & Constraints

- Primary files:
  - `src/specify_cli/constitution/interview.py`
  - `src/specify_cli/constitution/compiler.py`
  - `src/specify_cli/cli/commands/constitution.py`
- Supporting references:
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/data-model.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/research.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/quickstart.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/contracts/constitution-cli-contract.md`
- Implementation command: `spec-kitty implement WP02 --base WP01`
- Constraints:
  - explicit file paths only
  - local files may be free-form markdown
  - shipped artifacts remain primary on overlap
  - no generated `.kittify/constitution/library/`

## Subtasks & Detailed Guidance

### Subtask T006 - Extend the interview data model for local supporting files

- **Purpose**: Introduce a typed place for project-local doctrine declarations without overloading the shipped-selection fields.
- **Steps**:
  1. Read the existing `ConstitutionInterview` dataclass and serialization helpers in `src/specify_cli/constitution/interview.py`.
  2. Add the `local_supporting_files` field using a shape that can survive YAML round-trips cleanly.
  3. Update `to_dict()`, `from_dict()`, and any normalization helpers so missing declarations still serialize deterministically.
  4. Keep backward compatibility for existing answers files that do not contain the new field.
- **Files**:
  - `src/specify_cli/constitution/interview.py`
- **Parallel?**: No
- **Notes**: If you introduce a new dataclass for one declaration, keep it lightweight and serialization-friendly.

### Subtask T007 - Validate and normalize explicit local declaration shapes

- **Purpose**: Enforce the user-confirmed declaration rules before these files reach runtime context assembly.
- **Steps**:
  1. Reject directory paths and glob-like patterns (`*`, `?`, `[` / `]`, `**`) at normalization or compiler-entry time.
  2. Normalize optional `action` values to the known action set (`specify`, `plan`, `implement`, `review`) or `None`.
  3. Preserve optional `target_kind` and `target_id` without inventing shipped-schema requirements for free-form markdown files.
  4. Decide whether validation errors belong in `interview.py`, `compiler.py`, or a dedicated helper, and keep that decision consistent across generate paths.
- **Files**:
  - `src/specify_cli/constitution/interview.py`
  - `src/specify_cli/constitution/compiler.py`
- **Parallel?**: Yes
- **Notes**: The constraint is explicit path declarations, not path existence at interview-write time. Existence checks may happen later if generation actually uses the file.

### Subtask T008 - Build additive local support references and overlap warnings

- **Purpose**: Record local support files in the compiled bundle without letting them displace shipped doctrine.
- **Steps**:
  1. Read how `ConstitutionReference` is built today in `src/specify_cli/constitution/compiler.py`.
  2. Add a representation for local support entries in the compiled reference list.
  3. When `target_kind` and `target_id` overlap a shipped artifact, emit a warning that the local file is additive and shipped doctrine remains primary.
  4. Keep shipped doctrine references concise; do not inline full local markdown content into `constitution.md`.
- **Files**:
  - `src/specify_cli/constitution/compiler.py`
- **Parallel?**: No
- **Notes**: The warning should be precise enough for users to understand the conflict without being blocked from proceeding.

### Subtask T009 - Emit the generated output manifest correctly

- **Purpose**: Align success payloads and bundle metadata with the feature contract.
- **Steps**:
  1. Update generation bookkeeping so success payloads expose:
     - `constitution_file`
     - `references_file`
     - `generated_files`
     - `library_files`
  2. Treat `library_files` as the list of explicit project-local support files actually used, not generated artifacts.
  3. Keep `generated_files` to files the command wrote itself.
  4. Ensure shipped-only runs produce an empty `library_files` list.
- **Files**:
  - `src/specify_cli/cli/commands/constitution.py`
  - `src/specify_cli/constitution/compiler.py`
- **Parallel?**: No
- **Notes**: This WP owns the `generate --json` success shape; avoid leaving legacy `constitution_path` / `files_written`-only behavior behind.

### Subtask T010 - Remove generated library materialization

- **Purpose**: Make the constitution bundle a selection/configuration layer instead of a copied doctrine cache.
- **Steps**:
  1. Remove the logic in `write_compiled_constitution()` that creates `.kittify/constitution/library/` and writes reference content into it.
  2. Remove any stale-library cleanup code that assumes those files still exist.
  3. Update status/output code paths that count or report generated library docs.
  4. Keep the rest of bundle writing deterministic and force-aware.
- **Files**:
  - `src/specify_cli/constitution/compiler.py`
  - `src/specify_cli/cli/commands/constitution.py`
  - any tests that still count `library/*.md`
- **Parallel?**: No
- **Notes**: Runtime context retrieval will read shipped doctrine and local support files live; this WP should not reintroduce another cached-copy mechanism.

### Subtask T011 - Add compiler and CLI tests for local support declarations

- **Purpose**: Protect the new declaration model and manifest contract from regressions.
- **Steps**:
  1. Add compiler-level tests for:
     - serialization round-trip of `local_supporting_files`
     - explicit path acceptance
     - directory/glob rejection
     - conflict warning generation
     - absence of generated `library/`
  2. Add CLI tests for `generate --json` `library_files` behavior.
  3. Update any existing tests in `tests/specify_cli/constitution/test_compiler.py`, `tests/integration/`, or CLI suites that assume generated library markdown exists.
- **Files**:
  - `tests/specify_cli/constitution/test_compiler.py`
  - `tests/specify_cli/cli/commands/test_constitution_cli.py`
  - related integration tests as needed
- **Parallel?**: No
- **Notes**: Keep test fixtures small; one declared plan-scoped support file and one shipped-only fixture are enough to validate the contract.

## Test Strategy

- Run:
  - `pytest -q tests/specify_cli/constitution/test_compiler.py`
  - `pytest -q tests/specify_cli/cli/commands/test_constitution_cli.py`
- Add one fixture that exercises additive overlap warnings and one that proves shipped-only output keeps `library_files` empty.

## Risks & Mitigations

- The compiler currently treats references as content-bearing objects. Remove only the persistence behavior that materializes copied content, not the metadata needed for runtime resolution.
- Local path validation can become overly strict. Reject only the risky declaration classes the user ruled out; do not reject free-form markdown solely for lacking shipped doctrine schema fields.

## Review Guidance

- Confirm there is no generated `.kittify/constitution/library/` directory in the success path.
- Confirm `generate --json` now distinguishes between files written by the command and existing local support files it used.
- Confirm overlap warnings never imply that shipped doctrine was replaced.

## Activity Log

- 2026-03-09T14:23:30Z - system - lane=planned - Prompt created.
- 2026-03-09T16:50:00Z – claude – shell_pid=410671 – lane=for_review – LocalSupportDeclaration added, library/ removed, generate --json payload updated; 55 tests pass
- 2026-03-09T16:51:47Z – claude – shell_pid=410671 – lane=done – Reviewed and approved. Merged into feature branch.
