---
work_package_id: WP01
title: Harden Interview and Generate CLI Contracts
lane: "done"
dependencies: []
base_branch: feature/agent-profile-implementation
base_commit: e7293b63e41289ff14d231d703e7b63c740fa262
created_at: '2026-03-09T16:28:04.504859+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - CLI Contracts
assignee: claude
agent: claude
shell_pid: '405597'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-03-09T14:23:30Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-001
- FR-002
- FR-010
- FR-011
---

# Work Package Prompt: WP01 - Harden Interview and Generate CLI Contracts

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task.**

- If `review_status` is `has_feedback`, handle every item in **Review Feedback** before returning this WP to review.
- When you start addressing returned feedback, update `review_status` to `acknowledged` and append an Activity Log entry.

---

## Review Feedback

*[Empty initially. Reviewers populate this section if changes are required.]*  

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``  
Use language identifiers in fenced code blocks.

## Objectives & Success Criteria

- `spec-kitty constitution interview --defaults --json` returns `{"result": "success", "answers_file": "<path>"}` and still writes `.kittify/constitution/interview/answers.yaml`.
- `spec-kitty constitution generate` and `spec-kitty constitution generate-for-agent` fail fast when `--from-interview` is active and `answers.yaml` is missing.
- Human and JSON error payloads name the expected answers path and tell the user to run `spec-kitty constitution interview`.
- `--force` semantics are deterministic across every file produced by generation, including downstream sync outputs.
- Existing explicit default-generation paths (`--no-from-interview`) continue to work.

## Context & Constraints

- Primary file: `src/specify_cli/cli/commands/constitution.py`
- Supporting files likely touched: `src/specify_cli/constitution/compiler.py`, `tests/specify_cli/cli/commands/test_constitution_cli.py`
- Planning references:
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/spec.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/plan.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/contracts/constitution-cli-contract.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/tasks.md`
- Keep repo conventions intact: Python 3.11+, no new dependencies, JSON failures use `{"error": ...}`.
- Implementation command: `spec-kitty implement WP01`

## Subtasks & Detailed Guidance

### Subtask T001 - Audit the current interview/generate command flows

- **Purpose**: Establish the exact control-flow branches before changing error and overwrite behavior.
- **Steps**:
  1. Read `interview()`, `generate()`, and `generate_for_agent()` in `src/specify_cli/cli/commands/constitution.py`.
  2. Note the current JSON payload keys and the success/failure split for each command.
  3. Trace where `default_interview()` is used today and separate valid fallback usage from the silent generate-time fallback that must be removed.
  4. Note where `write_compiled_constitution()` and `sync_constitution()` are invoked so overwrite checks stay consistent.
- **Files**: `src/specify_cli/cli/commands/constitution.py`
- **Parallel?**: No
- **Notes**: This is an analysis step, but record the specific branches you intend to replace so the diff stays surgical.

### Subtask T002 - Normalize interview JSON and failure payloads

- **Purpose**: Align the CLI surface to the spec contract before changing deeper behavior.
- **Steps**:
  1. Update `interview --json` to emit `result: "success"` and `answers_file`, rather than the current `success` / `interview_path` shape.
  2. Standardize JSON failures to emit `{"error": "<message>"}` on stdout before exiting non-zero.
  3. Keep human-readable console output for non-JSON mode unchanged except where the message text must become more actionable.
  4. Avoid introducing helper abstractions that obscure the branch logic unless they clearly remove duplication across both generation commands.
- **Files**:
  - `src/specify_cli/cli/commands/constitution.py`
  - `tests/specify_cli/cli/commands/test_constitution_cli.py`
- **Parallel?**: No
- **Notes**: Preserve current success exit codes and Typer error handling patterns.

### Subtask T003 - Remove the silent missing-interview fallback

- **Purpose**: Enforce the strict `interview -> generate` workflow.
- **Steps**:
  1. In both `generate()` and `generate_for_agent()`, keep loading answers via `_interview_path(repo_root)` when `from_interview` is true.
  2. If `answers.yaml` is absent or unreadable in that mode, emit the required error with the absolute or repo-relative path and exit 1.
  3. Keep the explicit `--no-from-interview` and `--interview-profile` paths working by using deterministic defaults only when the caller chose to bypass interview answers.
  4. Ensure `interview_source` still reports a truthful value for success payloads.
- **Files**:
  - `src/specify_cli/cli/commands/constitution.py`
  - any shared helper extracted nearby in the same module
- **Parallel?**: No
- **Notes**: Do not remove the `default_interview()` import globally; `interview()` and the explicit fallback paths still need it.

### Subtask T004 - Enforce overwrite checks across all generated outputs

- **Purpose**: Make `--force` / interactive-confirmation behavior consistent with the feature contract.
- **Steps**:
  1. Audit `write_compiled_constitution()` and the surrounding generate flow to see which files can already exist before generation starts.
  2. When any output file exists and `--force` is not set: collect all conflicting paths, warn the user listing every conflict, and prompt interactively for confirmation. Write nothing until the user confirms; abort cleanly on rejection.
  3. Treat at least these files as the generated set: `constitution.md`, `references.yaml`, `governance.yaml`, `directives.yaml`, `metadata.yaml`.
  4. Keep `--force` as the non-interactive opt-in that skips the prompt and overwrites the full bundle without asking.
- **Files**:
  - `src/specify_cli/cli/commands/constitution.py`
  - `src/specify_cli/constitution/compiler.py`
  - `src/specify_cli/constitution/sync.py` if output bookkeeping needs adjustment
- **Parallel?**: No
- **Notes**: This WP should define the contract; later WPs can expand the file set details but should not redefine force/prompt behavior.

### Subtask T005 - Add CLI regression tests for the hardened contract

- **Purpose**: Lock the user-facing command behavior before other work packages build on it.
- **Steps**:
  1. Add/update tests for:
     - `interview --defaults --json`
     - `generate` without answers
     - `generate --json` failure shape
     - `generate --force` overwrite behavior
     - `generate-for-agent` missing-answers behavior when `--from-interview` is active
  2. Keep fixtures minimal and prefer Typer `CliRunner` coverage in `tests/specify_cli/cli/commands/test_constitution_cli.py`.
  3. Assert on exact payload keys, exit codes, and the presence of the expected answers path.
- **Files**:
  - `tests/specify_cli/cli/commands/test_constitution_cli.py`
- **Parallel?**: No
- **Notes**: Avoid coupling these tests to later local-support-file or context-depth changes; those belong to later work packages.

## Test Strategy

- Run: `pytest -q tests/specify_cli/cli/commands/test_constitution_cli.py`
- If compiler-level overwrite behavior changes, also run: `pytest -q tests/specify_cli/constitution/test_compiler.py`
- Verify at least one JSON failure case and one human-readable failure case.

## Risks & Mitigations

- `generate` and `generate-for-agent` share logic but are not fully unified. If you patch one branch without the other, the contract will drift immediately.
- Overwrite checks can become brittle if they are spread across CLI and compiler layers. Keep one authoritative definition of the generated bundle file set.

## Review Guidance

- Confirm both generation commands reject missing answers only when `--from-interview` is in effect.
- Confirm JSON payloads use `result` / `error` instead of legacy `success`-style keys.
- Confirm `--force` gating is evaluated before generation mutates output files.

## Activity Log

> **CRITICAL**: Activity log entries MUST be appended in chronological order.

- 2026-03-09T14:23:30Z - system - lane=planned - Prompt created.
- 2026-03-09T16:35:21Z – unknown – shell_pid=405597 – lane=for_review – Hardened CLI contracts: interview JSON (result/answers_file), missing-answers hard-fail, interactive overwrite prompt, JSON error shape
- 2026-03-09T16:42:56Z – claude – shell_pid=405597 – lane=done – Reviewed and approved. Merged into feature branch.
