---
work_package_id: WP03
title: New Bare-Prose Predicate — find_bare_prose_requirement_ids
dependencies:
- WP01
requirement_refs: []
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 1 - Foundation (parallel with WP02, WP04)
history:
- at: '2026-08-14T02:50:21Z'
  actor: system
  action: Prompt authored during tasks-authoring pass (not run via /spec-kitty.tasks)
agent_profile: ''
authoritative_surface: src/specify_cli/requirement_mapping.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/requirement_mapping.py
- tests/specify_cli/test_requirement_mapping.py
role: ''
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – New Bare-Prose Predicate — `find_bare_prose_requirement_ids`

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load`, or select via `spec-kitty agent profile list` for an
`implement`-typed WP on `src/specify_cli/requirement_mapping.py`.

---

## Objectives & Success Criteria

Implement IC-01 (plan.md): the new, per-token, per-line, document-scoped blocking
predicate `find_bare_prose_requirement_ids`. This is the foundation every other WP in
this mission wires into — nothing else can start until this lands.

Success: Story 1's exact repro (declared `NFR-001` table row + bare-prose
`FR-001`/`FR-002` under a "Functional Requirements" heading) is correctly flagged;
Story 2 AC3's description-column-in-a-declared-row case is correctly NOT flagged;
Story 5's fault-injection case surfaces an explicit failure, never `[]`.

## Context & Constraints

- Read plan.md's "Architecture" section (`### FR-001 — the new per-token, per-line,
  document-scoped bare-prose predicate`) in full — it specifies the exact three-step
  algorithm this WP must implement literally, not re-derive.
- Read spec.md's Story 1, Story 2 (especially AC3), Story 4, Story 5, C-001, C-006,
  C-008 before starting.
- **C-001 binding**: do NOT widen `_DECLARED_ID_PATTERNS` or touch what counts as
  "declared." This predicate is additive, reusing `_declared_ids` and
  `_requirement_named_sections` verbatim.
- **C-008 binding, already decided by plan.md (option (b))**: do NOT broaden
  `_is_requirement_heading` to also match "constraint." `C-XXX` bare-prose under a
  `### Constraints` heading is explicitly out of scope for this mission — WP07 records
  the disclosure side of that decision, this WP does not reopen it.
- **C-006 binding**: the declared-id set the predicate checks against is
  **document-scoped** (`_declared_ids(spec_content)`, the whole document), never
  section-scoped. Measured 15x difference (2.45% vs. 37.77%) — document-scoped is the
  only correct reading.
- **Environment trap**: `requirement_mapping.py` is pure stdlib. A standalone probe/test
  importing it outside the full CLI package must use
  `importlib.util.spec_from_file_location`, not the package `__init__` (which needs
  `typer`).

## Branch Strategy

- **Strategy**: Planning artifacts were generated on `pr/bare-prose-requirements-uncounted`;
  completed changes must merge back into `pr/bare-prose-requirements-uncounted`
  (base `op/3394-requirement-citation-scope` @ `ab15225ea`).
- **Planning base branch**: `pr/bare-prose-requirements-uncounted` (mission topology).
- **Merge target branch**: `pr/bare-prose-requirements-uncounted`.

> **ATDD RED verification uses a DIFFERENT ref than the branch-topology fields above.**
> This mission's real `planning_base_branch` for RED verification is **`ab15225ea`**
> (tip of `origin/op/3394-requirement-citation-scope`) — NOT `main`, and NOT the branch
> named in the "Branch Strategy" fields above (which describe where planning artifacts
> and completed work *land*, a separate concept). On `main`, the declared-shape
> machinery this predicate reuses (`_declared_ids`, `_requirement_named_sections`,
> `_DECLARED_ID_PATTERNS`) does not exist at all — a RED run there would be an
> `ImportError`/`AttributeError`, a category error, not a meaningful RED. See plan.md's
> "ATDD-First" section.

## Subtasks & Detailed Guidance

### Subtask T013 [P] – ATDD RED-first commit

- **Purpose**: Charter C-011 binding — a failing test as a separate commit before any
  implementation commit.
- **Steps**: Write test(s) in `tests/specify_cli/test_requirement_mapping.py` for
  `find_bare_prose_requirement_ids` against Story 1's exact repro. Run against
  **`ab15225ea`** (reuse WP01's worktree or check out fresh) and confirm RED — the
  function does not exist yet, so this should fail with an import/attribute error at
  minimum; verify it fails for the *right* reason (missing function), not an unrelated
  syntax error in the test itself.
- **Files**: `tests/specify_cli/test_requirement_mapping.py`.
- **Notes**: This commit lands BEFORE T014's implementation commit.

### Subtask T014 – Implement the predicate

- **Purpose**: The core deliverable.
- **Steps**: Add `find_bare_prose_requirement_ids(spec_content: str) -> BareProseResult`
  (a `NamedTuple`/`TypedDict` of `{section_heading: str, ids: list[str]}` entries) to
  `src/specify_cli/requirement_mapping.py`:
  1. `document_declared = _declared_ids(spec_content)` — unmodified, whole-document.
  2. For each `(heading_text, body)` in `_requirement_named_sections(spec_content)` —
     heading-scoping reused byte-identical.
  3. For each line in `body`: if the line matches one of the four
     `_DECLARED_ID_PATTERNS`, **skip raw-token scanning of the rest of that line
     entirely** (the Story 2 AC3 load-bearing rule). Else, scan the line for
     `_REF_FIND_PATTERN` tokens; any token not in `document_declared` is a bare-prose
     candidate, recorded against that section's heading.
- **Files**: `src/specify_cli/requirement_mapping.py`.

### Subtask T015 – Document the measured rates

- **Purpose**: FR-005's binding requirement — record the false-positive measurement
  in-repo at implementation time, following `_DECLARED_ID_PATTERNS`'s existing #3395
  6%-figure docstring precedent (~lines 43-53).
- **Steps**: Add a module/function docstring recording: 9/368 = 2.45% (document-scoped,
  C-006), 139/368 = 37.77% (rejected section-scoped alternative), zero true positives,
  corpus size (368), and measurement date. Both rates MUST be recorded together.

### Subtask T016 – Story 2 AC3 regression test

- **Purpose**: Pin the description-column non-blocking case — the exact class that drove
  #3395's rejected doc-wide prototype's ~6% false-positive rate.
- **Steps**: A table row whose ID cell is properly declared but whose description
  column cites a foreign/malformed id-shaped token must produce NO candidate for that
  row.

### Subtask T017 – Story 5 fault-injection test

- **Purpose**: Pin the pure-function half of "never silently report clean." (The
  call-site wrapping — try/except → blocking failure string — is IC-04, delivered per
  call site in WP05/WP06, not here.)
- **Steps**: Force the classification logic into an unresolvable state (monkeypatched
  exception mid-computation) and assert the result is an explicit surfaced failure,
  never `[]`/`None`/silent success.

### Subtask T018 – Story 4 negative-space regression test

- **Purpose**: Confirm #3394's repro shape stays green — the two stories are
  inseparable.
- **Steps**: A spec whose own requirements are all declared correctly, citing a
  foreign id in prose outside a Requirements-named section (or not matching a declared
  shape inside one), must not produce a candidate.

## Test Strategy

- `tests/specify_cli/test_requirement_mapping.py` is the primary test file — new tests
  land here.
- Run: `PWHEADLESS=1 pytest tests/specify_cli/test_requirement_mapping.py tests/specify_cli/test_requirement_mapping_coord_surface.py -n 8 --dist loadfile -q`
  (never `-n auto`).
- Confirm `tests/specify_cli/test_requirement_mapping_coord_surface.py` stays green,
  unmodified (Story 2 AC2 / SC-002).

## Risks & Mitigations

- Getting the per-line skip rule wrong reopens #3394 (doc-wide fallback) or
  reintroduces the description-column false-positive class — mitigated by T016/T018's
  explicit negative-space pins, and later by WP08's frozen corpus ratchet as a
  permanent regression guard.

## Review Guidance

- Confirm the RED-before-GREEN commit ordering against `ab15225ea` specifically, not
  `main`.
- Confirm `_DECLARED_ID_PATTERNS`/`_is_requirement_heading` are byte-identical in the
  diff — no widening.
- Confirm the module docstring records both rates (2.45% and 37.77%), not only one.

## Activity Log

- 2026-08-14T02:50:21Z – system – Prompt created.
