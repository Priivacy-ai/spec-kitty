---
work_package_id: WP02
title: Charter-authoritative language-scope resolution
dependencies: []
requirement_refs:
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- NFR-002
tracker_refs: []
planning_base_branch: issue/2437-env-var-pack-paths
merge_target_branch: issue/2437-env-var-pack-paths
branch_strategy: Planning artifacts for this mission were generated on issue/2437-env-var-pack-paths. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue/2437-env-var-pack-paths unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
phase: Phase 1 - Core fixes
assignee: ''
agent: "cursor:composer-2.5-fast:reviewer-renata:reviewer"
shell_pid: "25692"
history:
- at: '2026-07-07T12:08:11Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/charter/language_scope.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/charter/compiler.py
- src/charter/language_scope.py
- src/charter/context.py
- src/charter/compact.py
- tests/charter/test_language_scope.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Charter-authoritative language-scope resolution

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: (assign at dispatch time)

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: src/charter/language_scope.py`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Objectives & Success Criteria

Eliminate the DIRECTIVE_044 split-brain where doctrine language-scope inference runs the same extractor at both compile time (canonical, over interview answers) and runtime (re-derivation from the raw transcript, currently *preferred* over the compiled charter). Persist a structured, canonical language set on the compiled charter at compile time; make runtime resolution read that value; keep interview-transcript extraction as a creation-time-only fallback for the narrow pre-first-compile window.

Done when:
- `charter generate`/`charter sync` persists a structured language set derived from interview answers at compile time.
- Runtime language resolution (`infer_repo_languages` or its replacement) reads that structured value as the canonical source once it exists — even when it disagrees with what the interview transcript would independently produce.
- Projects whose compiled charter predates this change (no structured field yet) still resolve correctly via the existing interview-then-charter-prose fallback.
- The existing test that encodes the old (buggy) interview-preferred precedence is corrected — not deleted — to assert the new charter-authoritative behavior, after first confirming it is currently green against unfixed code (red-first discipline).
- `context.py`'s `active_languages` and `compact.py`'s display consumer both continue to work correctly against the corrected resolution with no separate precedence logic of their own.

## Context & Constraints

This WP implements FR-008 through FR-012, NFR-002, C-005 from `kitty-specs/pack-path-env-indirection-01KWY79W/spec.md`. Read `kitty-specs/pack-path-env-indirection-01KWY79W/plan.md` (Technical Context, IC-02), `research.md` (WP2 section), and `data-model.md` (compiled charter language set entity + state transition diagram) before writing any code.

**Why the deeper fix, not a minimal branch-flip**: the upstream issue's own suggested direction is a minimal precedence flip inside `infer_repo_languages` (interview vs. charter.md, just swap which wins). That would fix the reported symptom but leave the split-brain in place — `extract_declared_languages()` would still be invoked canonically at compile time (`src/charter/compiler.py:99`) *and* separately at runtime (`src/charter/language_scope.py`), meaning a future third caller could reintroduce its own precedence bug. This mission explicitly chose (locked decision, `deep_unify`) to persist a structured field at compile time instead, per DIRECTIVE_044 (canonical sources and unification — "unification not parity").

**Read before changing anything**:
- `src/charter/compiler.py:99` — the existing canonical invocation of `extract_declared_languages()` over interview answers at compile time. This is where the structured field should be computed and persisted.
- `src/charter/language_scope.py:18-54` — `extract_declared_languages()` (keyword-regex extractor, reuse as-is) and `infer_repo_languages()` (the function whose resolution precedence changes).
- `src/charter/context.py:1320,1326` — `active_languages` population, and `~2188-2207` — `_diagnose_catalog_miss`/`classify_scope_filtered_miss`, the scope-filtering consumer.
- `src/charter/compact.py:195-199` — display-only consumer, wrapped in a defensive exception handler; low risk but must still work correctly.
- `tests/charter/test_language_scope.py:21-36` — `test_infer_repo_languages_prefers_interview_answers`, the existing test that currently pins the buggy precedence as its contract.

**Exact field name/location is your implementation choice** — `data-model.md` deliberately leaves this open ("exact name/location TBD by implementer within `compiler.py`'s existing output shape"). Choose whatever fits the existing compiled-charter output structure most naturally (e.g. a YAML frontmatter key, a sidecar structured file, or an in-memory field on whatever object `compiler.py` already returns/persists) — just ensure it round-trips through a real compile→read cycle, not only in-memory during a single process.

## Branch Strategy

- **Strategy**: single-branch mission (`topology: coord`, no per-WP lanes required for this mission's size — confirm via `lanes.json` if present at implement time).
- **Planning base branch**: `issue/2437-env-var-pack-paths`
- **Merge target branch**: `issue/2437-env-var-pack-paths`

> These fields are populated automatically by `spec-kitty agent mission tasks`. Do NOT change them manually unless you are certain the branch topology has changed. If `spec-kitty agent action implement WP02` reports a different lane/worktree path, trust that command's output over this static text.

## Subtasks & Detailed Guidance

### Subtask T008 – Persist structured `languages` field at compile time

- **Purpose**: Give runtime a canonical value to read instead of re-deriving from the raw transcript.
- **Steps**:
  1. Read `src/charter/compiler.py` around line 99 and its surrounding function fully — understand what triggers this extraction today and what output structure the compiler already produces/persists.
  2. Add a structured `languages` (or equivalently named) field to that output, computed via the existing `extract_declared_languages()` call over interview answers, persisted so it survives to disk (not just held in memory for the current compile call) and is readable independently by `language_scope.py` afterward.
  3. Ensure this only runs at `charter generate`/`charter sync` time — not on every read.
- **Files**: `src/charter/compiler.py`.
- **Parallel?**: No — foundation for T009.
- **Notes**: Reuse `extract_declared_languages()` as-is; do not fork or duplicate its regex logic.

### Subtask T009 – Update runtime resolution precedence

- **Purpose**: Make `infer_repo_languages` (or its replacement, keeping existing call signatures for callers) read the compiled structured field as the canonical source.
- **Steps**:
  1. Update `src/charter/language_scope.py` so resolution checks for T008's structured field first.
  2. If present, return it directly — do **not** also consult the interview transcript in this branch, even if the transcript would produce a different answer. The compiled value wins unconditionally once it exists (this is the exact behavior that flips the bug: today, `answers.yaml` wins if it has any match at all).
  3. If absent (pre-existing charter, not yet recompiled under this change), fall back to today's existing logic unchanged: interview transcript first, then `charter.md` free-text extraction, then empty.
  4. Keep the function name/signature stable if at all reasonably possible — `context.py` and `compact.py` should not need call-site changes beyond what T010 verifies.
- **Files**: `src/charter/language_scope.py`.
- **Parallel?**: No — depends on T008's field existing.
- **Notes**: This is the FR-008/FR-010 core logic. Re-read `data-model.md`'s state-transition diagram before implementing — it specifies the exact two-branch precedence.

### Subtask T010 – Verify consumers

- **Purpose**: Confirm `active_languages` and the `compact.py` display path work correctly through the corrected resolution with zero consumer-side precedence logic of their own.
- **Steps**:
  1. Read `context.py:1320,1326` and the `_diagnose_catalog_miss`/`classify_scope_filtered_miss` chain (`~2188-2207`) — confirm they simply consume whatever `infer_repo_languages` returns, with no independent interview/charter branching duplicated there. If you find such duplication, that's a pre-existing DIRECTIVE_044 violation worth flagging in the Activity Log (fix only if trivially in-scope; otherwise note it for a follow-up).
  2. Read `compact.py:195-199` — confirm the defensive `except Exception` wrapper still makes sense post-change (it should; this subtask is verification, not a rewrite).
  3. Add or update tests exercising the full path from a compiled structured field through to `active_languages` and the scope-filtering consumer, not just `infer_repo_languages` in isolation.
- **Files**: `src/charter/context.py`, `src/charter/compact.py` (read/verify only — avoid changes unless something is actually broken), `tests/charter/test_context.py` if you add coverage there.
- **Parallel?**: [P] — can proceed alongside T011/T012 once T009 lands.
- **Notes**: `tests/charter/test_context.py:851` already monkeypatches `infer_repo_languages` directly in some tests — that isolation is fine and doesn't need to change, but don't rely on it as your only coverage; add at least one test that exercises the real resolution path end-to-end.

### Subtask T011 – Correct the pinning test (red-first) + add disagreement/structured-field cases

- **Purpose**: The existing test `test_infer_repo_languages_prefers_interview_answers` (`tests/charter/test_language_scope.py:21-36`) currently asserts the buggy interview-preferred precedence as its contract. Per DIRECTIVE_034/041 and the standing test-remediation/red-first discipline, this must be corrected with an explicit red-first confirmation, not silently rewritten.
- **Steps**:
  1. Before making any code change from T008/T009, run `pytest tests/charter/test_language_scope.py::test_infer_repo_languages_prefers_interview_answers -v` against the **unfixed** code and confirm it passes (green) — this is your proof that it currently encodes the bug. Record this in the Activity Log.
  2. After T008/T009 land, re-run the same test — it should now fail (red), because the fixed code returns the charter-authoritative answer, not the interview-preferred one.
  3. Invert the test's assertion to match the new, correct behavior (interview says one language, `charter.md`/the compiled structured field says a different one → assert the compiled/charter answer wins). Do **not** delete the test.
  4. Add a new test case explicitly named for the disagreement scenario if the inverted test doesn't already make this obvious from its name/docstring (e.g. `test_infer_repo_languages_prefers_compiled_charter_over_stale_interview`).
  5. Add a new test exercising T008's structured field directly (construct a compiled-charter fixture with the structured field present, assert it's returned without consulting the interview transcript at all).
- **Files**: `tests/charter/test_language_scope.py`.
- **Parallel?**: No — this is the primary regression-proof subtask; sequence it right after T009.
- **Notes**: Record both the "confirmed red on old code" and "confirmed green on new code" steps explicitly in the Activity Log — this is the auditable proof of the red-first discipline for this fix.

### Subtask T012 – Backward-compatibility test

- **Purpose**: Prove FR-010's fallback path — pre-existing compiled charters without the structured field must still resolve correctly via today's existing logic.
- **Steps**:
  1. Construct a test fixture representing a charter compiled *before* this change (no structured field present).
  2. Assert resolution falls back to interview-transcript extraction, then `charter.md` free-text extraction, exactly as it does today for that fixture shape.
  3. Confirm this test would have passed on the pre-change code too (it's a regression guard, not a new-behavior proof).
- **Files**: `tests/charter/test_language_scope.py`.
- **Parallel?**: [P] — independent of T011, can be written alongside it.
- **Notes**: This is what makes the deep-unification choice safe for existing projects without forcing a mandatory recompile.

### Subtask T013 – Documentation

- **Purpose**: Record the compiled-charter authority model where operators/future maintainers will find it.
- **Steps**:
  1. Find or create the relevant explanation doc for charter/language-scope behavior (check `docs/architecture/` and `docs/guides/` for an existing home; if none exists, a short addition to the charter guide is sufficient — do not create a large new document for this).
  2. Document: languages are resolved from the compiled charter (canonical, once present); the interview transcript is a creation-time-only input, consulted only before the first compile under this change.
- **Files**: Existing charter-related doc under `docs/` (identify at implementation time; keep the addition proportionate).
- **Parallel?**: [P] — independent of code subtasks.
- **Notes**: Keep this addition short — a paragraph, not a new architecture document.

### Subtask T014 – Quality gate

- **Purpose**: Confirm the WP is mergeable.
- **Steps**:
  1. Run `pytest tests/charter/ -v` — all green, including the inverted T011 test and the new T012 backward-compatibility test, no unexplained regressions elsewhere in the charter test suite.
  2. Run `ruff check src/charter/compiler.py src/charter/language_scope.py src/charter/context.py src/charter/compact.py` and `mypy` on the same files — zero issues.
  3. If any documentation or prose under `src/doctrine/` was touched by T013, run `pytest tests/architectural/test_no_legacy_terminology.py` (terminology guard, ~0.1s) per the repo-wide pre-push rule.
- **Files**: N/A (verification only).
- **Parallel?**: No — final gate.
- **Notes**: If mypy flags the new field/structure, fix the types — don't suppress.

## Test Strategy

- Unit tests: `tests/charter/test_language_scope.py`.
- Integration/consumer tests: `tests/charter/test_context.py` (add end-to-end coverage per T010; existing monkeypatch-based tests stay as-is).
- Run: `pytest tests/charter/test_language_scope.py tests/charter/test_context.py -v`
- Full charter suite for regression safety: `pytest tests/charter/ -v`

## Risks & Mitigations

- **Risk**: Silently deleting or weakening the pinning test instead of inverting it with red-first proof. **Mitigation**: T011's explicit red→green sequence, recorded in the Activity Log, is the non-negotiable audit trail.
- **Risk**: Breaking backward compatibility for un-recompiled projects. **Mitigation**: T012's dedicated fallback test.
- **Risk**: Duplicating precedence logic in `context.py`/`compact.py` instead of keeping it centralized in `language_scope.py`. **Mitigation**: T010's explicit check for consumer-side duplication.

## Review Guidance

- Confirm the Activity Log documents the red-first confirmation for `test_infer_repo_languages_prefers_interview_answers` (T011) — this is the key non-fakeable proof point for this WP.
- Confirm the structured field genuinely persists to disk across a compile→read cycle in a fresh process, not just within one Python session.
- Confirm `#2213` was not incidentally touched — it is explicitly out of scope (C-002).
- Confirm no new `except Exception: pass` or bare suppressions were introduced.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-07-07T12:08:11Z – system – Prompt created.
- 2026-07-07T12:37:20Z – cursor:composer-2.5-fast:implementer-ivan:implementer – shell_pid=5151 – Assigned agent via action command
- 2026-07-07T12:56:54Z – cursor:composer-2.5-fast:implementer-ivan:implementer – shell_pid=5151 – Ready for review: persisted structured languages field on references.yaml at compile time (compiler.py); infer_repo_languages now reads it as canonical, falling back to interview/charter.md only when absent (language_scope.py). Red-first confirmed: pinning test passed (green) against unfixed code, proving the interview-preferred bug; inverted to assert charter-authoritative precedence, added disagreement + structured-field + backward-compat tests. Verified context.py/compact.py have zero duplicated precedence logic; added end-to-end test through _build_doctrine_service and a real compile-write-read round-trip test. ruff+mypy zero issues on changed files.
- 2026-07-07T12:57:32Z – cursor:composer-2.5-fast:reviewer-renata:reviewer – shell_pid=25692 – Started review via action command
