---
work_package_id: WP08
title: Relation doc-parity
dependencies:
- WP01
requirement_refs:
- FR-012
- NFR-004
planning_base_branch: doctrine/drg-missing-links-analysis
merge_target_branch: doctrine/drg-missing-links-analysis
branch_strategy: Planning artifacts for this mission were generated on doctrine/drg-missing-links-analysis. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/drg-missing-links-analysis unless the human explicitly redirects the landing branch.
subtasks:
- T038
- T039
- T040
- T041
phase: Phase 3 - Checkup surface
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "91207"
shell_pid_created_at: "1784643626.615457"
history:
- at: '2026-07-21T11:08:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: docs/architecture/doctrine-relationships.md
create_intent:
- tests/doctrine/test_relation_doc_parity.py
execution_mode: code_change
model: ''
owned_files:
- docs/architecture/doctrine-relationships.md
- tests/doctrine/test_relation_doc_parity.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP08 – Relation doc-parity

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: docs/architecture/doctrine-relationships.md`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting if this WP was returned from review. Address all feedback; update the Activity Log as you go.

---

## Objectives & Success Criteria

FR-012/NFR-004/US5: single canonical authority for relation semantics must not drift between code and docs. The parity check this WP builds **does not exist today** — it is a deliverable of this mission (Assumption A2), not a pre-existing check you're merely satisfying.

Done means:
- `docs/architecture/doctrine-relationships.md` has entries for `in_tension_with`, `reconciles_tension`, `rejects` matching WP01's `RELATION_DESCRIPTIONS` text verbatim.
- A parity check compares the two and fails (red) when they diverge, naming the specific relation that drifted.
- The check is wired into the test suite (or `charter lint`) so it runs automatically.

## Context & Constraints

- This WP is **read-only** with respect to `src/doctrine/drg/models.py` — it consumes WP01's `RELATION_DESCRIPTIONS` text, it does not edit it. If you find the registry text inadequate for a doc entry, that is WP01's file to fix, not yours; flag it rather than editing `models.py` directly (avoids an ownership conflict).
- Scope is exactly the three new relations (Assumption A2) — do not attempt to backfill parity entries for the other 12 existing relations in this WP.
- Read `docs/architecture/doctrine-relationships.md`'s current structure before adding to it — match its existing per-relation entry format exactly (headers, table columns, whatever shape it already uses for the other 12 relations).

## Branch Strategy

- **Strategy**: single_branch — no coordination/lanes topology; planning and merge-target branch are the same branch.
- **Planning base branch**: `doctrine/drg-missing-links-analysis`
- **Merge target branch**: `doctrine/drg-missing-links-analysis`

Implementation command: `spec-kitty agent action implement WP08 --agent <name>` (depends on WP01 only — can run in parallel with WP02-WP07).

## Subtasks & Detailed Guidance

### Subtask T038 – Add the 3 relation entries to the doc

- **Purpose**: The human-readable half of the parity pair.
- **Steps**: In `docs/architecture/doctrine-relationships.md`, add entries for `in_tension_with`, `reconciles_tension`, `rejects`, matching WP01's `RELATION_DESCRIPTIONS` text **verbatim** (copy the exact string, do not paraphrase) — the parity check in T039 will do a literal comparison. Follow the doc's existing formatting conventions for the other 12 relations.
- **Files**: `docs/architecture/doctrine-relationships.md`
- **Parallel?**: No — do this first so T039 has something concrete to compare against while developing.

### Subtask T039 – Build the enum↔doc parity check

- **Purpose**: NFR-004 — "a parity check enforcing it" that does not exist today.
- **Steps**: Write a check that: reads `RELATION_DESCRIPTIONS` from `src/doctrine/drg/models.py`; parses (or greps, whichever is robust enough given the doc's actual structure) the corresponding entries from `docs/architecture/doctrine-relationships.md`; asserts the text matches exactly for each of the 3 new relations; reports which specific relation(s) diverged on failure (not just "parity check failed"). Decide whether this lives as a pytest test (simplest, matches T040's red-first requirement most directly) or as a `charter lint` check (more visible to operators day-to-day) — a plain test is the lower-risk default unless the doc's structure makes lint integration clearly better.
- **Files**: new module (likely `tests/doctrine/test_relation_doc_parity.py` if implemented as a test; if implemented as a lint check, also add a thin test wrapper there)
- **Parallel?**: No — depends on T038 existing to develop against.

### Subtask T040 – Red-first test

- **Purpose**: NFR-004's explicit red-first requirement — "fails red when a description is mutated."
- **Steps**: Prove the check actually catches drift: temporarily mutate one relation's description in the doc only (not the registry), run the parity check, confirm it fails and names that specific relation; revert the mutation, confirm it passes again. Encode this as an actual test (not a manual one-off you ran and threw away) — e.g. monkeypatch or use a temp copy of the doc content with one description altered, assert the check's failure output names the correct relation.
- **Files**: `tests/doctrine/test_relation_doc_parity.py`
- **Parallel?**: No — depends on T039.
- **Notes**: A check that only verifies *presence* (both sides have *some* description) rather than content-equality would pass this red-first test trivially in the wrong way if you're not careful — make sure the mutation you test with is a small text change, not a deletion, to specifically exercise the equality comparison.

### Subtask T041 – Wire the check into the test suite

- **Purpose**: "Runs automatically, not as a manual step."
- **Steps**: Confirm the parity check (T039/T040) runs as part of the normal `pytest` collection (if implemented as a test) or is invoked by whatever CI/local gate already runs `charter lint` (if implemented there) — no separate manual invocation should be required for it to catch drift in normal CI.
- **Files**: none if already wired via normal pytest discovery; update whatever config/gate list needs it otherwise
- **Parallel?**: No — final step.

## Test Strategy

- `.venv/bin/pytest tests/doctrine/test_relation_doc_parity.py -q`
- `.venv/bin/ruff check` + `.venv/bin/mypy` on any new Python module.

## Risks & Mitigations

- **Risk**: A parity check that only checks presence, not equality — satisfies the letter of "a check exists" while missing NFR-004's actual point. **Mitigation**: T040's red-first test is specifically designed to catch this shortcut.
- **Risk**: Editing `RELATION_DESCRIPTIONS` in this WP to make the doc "fit" rather than flagging inadequate text back. **Mitigation**: called out explicitly in Context & Constraints — this WP is read-only on `models.py`.

## Review Guidance

- Actually run the red-first scenario yourself (mutate the doc, watch the check fail, revert, watch it pass) rather than trusting a green test suite alone — this is precisely the kind of check that's easy to write in a way that looks correct but doesn't test the right thing.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-07-21T11:08:12Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP08 --to <status>` to change WP status.
- 2026-07-21T13:41:24Z – claude:sonnet:python-pedro:implementer – shell_pid=80649 – Assigned agent via action command
- 2026-07-21T13:50:44Z – claude:sonnet:python-pedro:implementer – shell_pid=80649 – Ready for review
- 2026-07-21T14:20:41Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=91207 – Started review via action command
- 2026-07-21T14:27:07Z – user – shell_pid=91207 – Review passed: verified RELATION_DESCRIPTIONS text in src/doctrine/drg/models.py is byte-for-byte reproduced (after whitespace normalization) in docs/architecture/doctrine-relationships.md's new Tension vocabulary section for all 3 new relations (in_tension_with, reconciles_tension, rejects); confirmed models.py untouched by WP08's commit (git diff empty, read-only constraint respected); ran tests/doctrine/test_relation_doc_parity.py (7 passed), ruff check (clean), mypy (clean); independently mutated one word in the doc's rejects section and reran the suite -- 3 tests failed and correctly named only 'rejects' as divergent, confirming genuine content-equality comparison rather than presence-only checking; reverted the mutation via git checkout, reran -- 7 passed, git diff clean. Check is auto-collected by pytest (testpaths=tests, no exclusion), satisfying T041 wiring requirement. All anti-pattern checklist items PASS.
