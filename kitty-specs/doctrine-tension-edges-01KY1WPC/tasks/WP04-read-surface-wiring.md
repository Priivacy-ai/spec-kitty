---
work_package_id: WP04
title: Read-surface wiring — validator + activation filter
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-014
planning_base_branch: doctrine/drg-missing-links-analysis
merge_target_branch: doctrine/drg-missing-links-analysis
branch_strategy: Planning artifacts for this mission were generated on doctrine/drg-missing-links-analysis. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/drg-missing-links-analysis unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
phase: Phase 2 - Read surface
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "91207"
shell_pid_created_at: "1784643626.615457"
history:
- at: '2026-07-21T11:08:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/validator.py
create_intent:
- tests/doctrine/drg/test_validator.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/drg.py
- src/charter/activations.py
- src/charter/pack_context.py
- src/doctrine/drg/validator.py
- tests/doctrine/drg/test_validator.py
- tests/charter/test_drg_filtering.py
- tests/charter/test_activation_filtered_drg.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Read-surface wiring — validator + activation filter

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: src/doctrine/drg/validator.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting if this WP was returned from review. Address all feedback; update the Activity Log as you go.

---

## Objectives & Success Criteria

Wire `NodeKind.ANTI_PATTERN` through the activation filter's kind-gating machinery, and add the `rejects`-target validation rule. This WP is scoped tightly to reading/validating existing structure — it does not add new consistency-check findings (WP05) or lint fixes (WP06).

Done means:
- `rejects` edges to a target lacking `kind == NodeKind.ANTI_PATTERN` raise a validation error (INV-004).
- `anti_pattern` nodes are gated by the activation filter using the same mechanism as every other kind (config-gated, not relying on the filter's default-allow-for-unknown-kind fallback).
- A single stored `in_tension_with` edge is queryable from either endpoint URN (INV-001).

## Context & Constraints

- **Read this before touching any file**: `src/charter/cascade.py::_kind_of` resolves `ArtifactKind(prefix)` generically — it requires **no code change** once WP01's `ArtifactKind.ANTI_PATTERN` member exists. Do not edit `src/charter/cascade.py` in this WP; doing so would create an unnecessary ownership conflict with WP06, which also touches cascade-adjacent test coverage.
- `src/charter/drg.py::_node_is_activated` has a documented default-allow for kinds absent from `_SINGULAR_TO_PLURAL` ("An unknown kind... is allowed through so the filter never silently swallows new artifact kinds"). This is real, existing behavior — but FR-004 explicitly requires wiring `anti_pattern` through `_SINGULAR_TO_PLURAL`/`_SINGULAR_TO_PER_KIND_FIELD` anyway, so it is config-gated like every other kind rather than silently defaulting to always-visible. Implement the explicit wiring; do not rely on the default-allow fallback even though it would technically "work" for a different reason.
- There are (at least) two near-duplicate singular→plural maps: `_SINGULAR_TO_PLURAL`/`_SINGULAR_TO_PER_KIND_FIELD` in `src/charter/drg.py`, and `_SINGULAR_TO_PLURAL_KIND` in `src/charter/activations.py`. Both must gain the `anti_pattern` entry or activation/CLI parsing diverges — search for any other call site using `grep -rn "_SINGULAR_TO_PLURAL" src/` before considering this done, in case a third copy exists that this prompt's research missed.
- `PackContext` (`src/charter/pack_context.py`) needs the new `activated_anti_patterns` field, following the exact pattern of the existing per-kind fields (e.g. `activated_directives`).

## Branch Strategy

- **Strategy**: single_branch — no coordination/lanes topology; planning and merge-target branch are the same branch.
- **Planning base branch**: `doctrine/drg-missing-links-analysis`
- **Merge target branch**: `doctrine/drg-missing-links-analysis`

Implementation command: `spec-kitty agent action implement WP04 --agent <name>` (depends on WP01 only — no technical dependency on WP02/WP03, this WP's tests use synthetic constructed graphs, not the real built-in pack; runs in parallel with them).

## Subtasks & Detailed Guidance

### Subtask T019 – Wire `anti_pattern` into the singular↔plural kind maps

- **Purpose**: Makes `anti_pattern` a config-gated activatable kind, consistent with every other kind (FR-004).
- **Steps**:
  1. In `src/charter/drg.py`, add `"anti_pattern": "anti_patterns"` to `_SINGULAR_TO_PLURAL` (line ~189-198 as of plan time) and `"anti_pattern": "activated_anti_patterns"` to `_SINGULAR_TO_PER_KIND_FIELD` (line ~203-214 as of plan time) — confirm current line numbers, they may have shifted after WP01-WP03.
  2. In `src/charter/activations.py`, add the matching entry to `_SINGULAR_TO_PLURAL_KIND` (line ~177-186 as of plan time).
  3. Grep for any other `_SINGULAR_TO_PLURAL`-shaped dict in `src/` you haven't yet accounted for and update it too.
- **Files**: `src/charter/drg.py`, `src/charter/activations.py`
- **Parallel?**: Yes, relative to T021 (different files).
- **Notes**: Match the exact plural form your CLI/config layer expects — `"anti_patterns"` is the working assumption; confirm no existing convention (e.g. `"anti-patterns"` with a hyphen) is already in use elsewhere for this concept before committing to the underscore form.

### Subtask T020 – Add `activated_anti_patterns` to `PackContext`

- **Purpose**: The per-kind config field T019's `_SINGULAR_TO_PER_KIND_FIELD` entry points at.
- **Steps**: In `src/charter/pack_context.py`, add `activated_anti_patterns: frozenset[str] | None = None` (or the exact type/default used by sibling fields like `activated_directives` — match it precisely, don't invent a slightly different shape).
- **Files**: `src/charter/pack_context.py`
- **Parallel?**: Yes, relative to T021.
- **Notes**: Check whether `PackContext` construction (wherever it's built from `charter.yaml`/config) needs a corresponding read-path addition too — a field that exists on the model but is never populated from config is a partial wiring, exactly the kind of "lands on one surface but not others" defect NFR-002/the Change Surface Map warns about.

### Subtask T021 – Add `rejects`-target validation

- **Purpose**: INV-004 — a `rejects` edge whose target isn't marked `anti_pattern` is a validation error, not a silent no-op.
- **Steps**:
  1. In `src/doctrine/drg/validator.py`, add a rule: for every `DRGEdge` with `relation == Relation.REJECTS`, resolve its `target` node and assert `kind == NodeKind.ANTI_PATTERN`. If not, raise the validator's existing error type/pattern (match whatever exception/finding shape the rest of this module already uses — read a couple of existing rules first).
- **Files**: `src/doctrine/drg/validator.py`
- **Parallel?**: Yes, relative to T019/T020.
- **Notes**: This validates structure (are `rejects` edges well-formed), not activation state — it should run regardless of whether the target is currently activated.

### Subtask T022 – Symmetric-read test (INV-001)

- **Purpose**: Prove `DRGGraph.edges_from`/`edges_to` already support querying a single stored edge from either endpoint (Assumption A3 — no new graph primitive needed).
- **Steps**: Write a test that constructs a graph with one `in_tension_with` edge (`A → B`), then asserts the pair is discoverable both via a query rooted at `A` and a query rooted at `B` (using whichever of `edges_from`/`edges_to` is the correct pairing for "outgoing from A" vs "incoming to B" — read both methods' actual signatures in `src/doctrine/drg/models.py` first, don't assume which one to call from which side).
- **Files**: `tests/doctrine/drg/test_validator.py` (new — reasonable home alongside T023's validator tests) or an existing DRG graph-query test file if one is a better fit
- **Parallel?**: Yes.
- **Notes**: This is a proving test, not new production code — Assumption A3 in spec.md already asserts this works; your job is to write the test that would fail if it didn't.

### Subtask T023 – Activation-gating + validation error tests

- **Purpose**: NFR-005 coverage for T019-T021.
- **Steps**:
  1. Extend `tests/charter/test_drg_filtering.py` or `tests/charter/test_activation_filtered_drg.py` with a case proving `anti_pattern` nodes are gated exactly like other kinds (present when `activated_anti_patterns` allows the ID, absent when it doesn't — not merely "always visible").
  2. In `tests/doctrine/drg/test_validator.py` (new), add the negative case for T021: a `rejects` edge to a non-`anti_pattern`-kinded target raises the expected error.
- **Files**: `tests/charter/test_drg_filtering.py` or `tests/charter/test_activation_filtered_drg.py`, `tests/doctrine/drg/test_validator.py`
- **Parallel?**: No — run after T019-T021 land.

## Test Strategy

- `.venv/bin/pytest tests/doctrine/drg/ tests/charter/test_drg_filtering.py tests/charter/test_activation_filtered_drg.py -q`
- `.venv/bin/ruff check` + `.venv/bin/mypy` on every file in `owned_files`.

## Risks & Mitigations

- **Risk**: Missing one of the (at least two, possibly three) singular→plural maps leaves activation config partially wired — it will "mostly work" until someone hits the unmigrated path. **Mitigation**: T019 explicitly requires a repo-wide grep, not just editing the two known files.
- **Risk**: Confusing the default-allow fallback with correct behavior and skipping the explicit wiring. **Mitigation**: called out directly in Context & Constraints above.

## Review Guidance

- Confirm `src/charter/cascade.py` was NOT touched in this WP (no code change needed there — verify the reviewer understands why, per the note above, rather than requesting an unnecessary edit).
- Confirm all singular→plural maps found via a repo-wide grep were updated, not just the two named in this prompt.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-07-21T11:08:12Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP04 --to <status>` to change WP status.
- 2026-07-21T13:41:05Z – claude:sonnet:python-pedro:implementer – shell_pid=80649 – Assigned agent via action command
- 2026-07-21T13:53:10Z – claude:sonnet:python-pedro:implementer – shell_pid=80649 – Ready for review: anti_pattern wired into both singular->plural kind maps + PackContext.activated_anti_patterns (with read-path), rejects-target INV-004 validator rule added, INV-001 symmetric-read + gating/negative tests added. cascade.py untouched. Scoped tests/ruff/mypy all green.
- 2026-07-21T14:20:34Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=91207 – Started review via action command
- 2026-07-21T14:27:38Z – user – shell_pid=91207 – Review passed: T019 verified — anti_pattern added to _SINGULAR_TO_PLURAL/_SINGULAR_TO_PER_KIND_FIELD (drg.py) and _SINGULAR_TO_PLURAL_KIND (activations.py). Independently re-grepped _SINGULAR_TO_PLURAL across src/ and confirmed the 3 other near-duplicates the implementer cited (doctrine.py scaffold map, pack_validator._SINGULAR_TO_PLURAL_AUGMENTATION, artifact_kinds.ArtifactKind._PLURALS) correctly exclude/handle anti_pattern by design per artifact_kinds.py's _NON_AUGMENTATION_ELIGIBLE_KINDS docstring (anti_pattern is never hand-authored standalone, never augmentation-eligible). Also found and independently investigated a 4th candidate the implementer did not mention (_activation_render.py::_singular_kind's local hardcoded inverse dict) and confirmed it is genuinely unreachable for anti_pattern (DoctrineService has no .anti_patterns property, and activations._ALLOWED_KINDS/_KIND_TO_PROPERTY never admit it) -- correctly left unchanged. T020 verified: PackContext.activated_anti_patterns field added plus a real read-path (_read_activated_anti_patterns calling _read_list_key), matching the exact sibling pattern for every other kind -- not a dead field. T021 verified: _validate_rejects_targets added to validator.py following the exact existing rule pattern (kind_by_urn lookup, dangling-defers-elsewhere comment, matching error message shape), wired into validate_graph as check 5. T022/T023 verified: real INV-001 symmetric-read test (edges_from/edges_to cross-checked both directions) and INV-004 positive/negative/dangling-target validator tests exist in new tests/doctrine/drg/test_validator.py; activation-gating coverage added to tests/charter/test_drg_filtering.py proving anti_pattern is config-gated (kind-level + per-artifact-ID), not default-allowed. Confirmed src/charter/cascade.py untouched (0 diff hits). Ran pytest tests/doctrine/drg/test_validator.py tests/charter/test_drg_filtering.py tests/charter/test_activation_filtered_drg.py tests/charter/test_pack_context.py -q myself: 58 passed. Ran mypy on all 4 changed source files myself: Success, no issues. Ran ruff check on changed files: all checks passed. Bulk-edit gate: grepped all 4 changed source files for opposed_by/Contradiction -- zero hits; this WP is purely additive activation-filter wiring, unrelated to the opposed_by retirement's manual_review code_symbols category, not a shortcut.
