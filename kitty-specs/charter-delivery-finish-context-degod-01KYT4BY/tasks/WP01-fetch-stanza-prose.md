---
work_package_id: WP01
title: 'US2: fetch-stanza when-clause prose (#3082)'
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: feat/charter-delivery-finish-context-degod
merge_target_branch: feat/charter-delivery-finish-context-degod
branch_strategy: Planning artifacts for this mission were generated on feat/charter-delivery-finish-context-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-delivery-finish-context-degod unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-delivery-finish-context-degod-01KYT4BY
base_commit: a1e6cbb8730e89462c4db6b00b1acd6867610eda
created_at: '2026-07-30T19:56:19.644762+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- at: '2026-07-30'
  actor: planner-priti
  note: WP authored from plan IC-01 + post-plan squad.
agent_profile: python-pedro
authoritative_surface: src/charter/context_renderers/
create_intent:
- tests/charter/test_fetch_stanza_normalization.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/charter/activation/context_renderers/fetch_stanza.py
- tests/specify_cli/next/test_wp_prompt_governance_contract.py
- tests/charter/test_fetch_stanza_normalization.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Apply the resolved initialization, boundaries, directives, and tactics. Confirm which you applied in one line, then proceed.

## Objective

Fix issue **#3082**: the generated `When you …` disclosure line in the fetch stanza is ungrammatical for many clause shapes (e.g. `When you designing or reviewing …`, `When you Fetch when this artefact's guidance applies …., run this command`). Normalize the authored `when` clause so every emitted stanza is grammatical **and** still satisfies the pinned prompt-governance contract — asserted **per stanza**.

Design authority: [`../spec.md`](../spec.md) (US2, FR-001, NFR-003), [`../contracts/fetch-stanza-normalization.md`](../contracts/fetch-stanza-normalization.md).

## Critical context (verified against code)

- The single composition choke-point is `src/charter/activation/context_renderers/fetch_stanza.py`, function `fetch_stanza_lines` (~line 133): `f"{indent}When you {clause}, run this command and apply the returned rule."`.
- **`_WHEN_DOING_RE` is a CLOSED 6-verb set** (`tests/specify_cli/next/test_wp_prompt_governance_contract.py:221`):
  `when you (are about to | need to | encounter | introduce | rename | review)`.
  So a grammatical-but-non-matching rewrite (e.g. `When you are designing…`) **silently breaks the contract**. Your normalization MUST land the clause inside this closed set. The safe default anchor is the existing `DEFAULT_WHEN_CLAUSE = "are about to apply a code change"`.
- The contract test today applies `_WHEN_DOING_RE.search(prompt)` over the **whole prompt** — one matching line anywhere passes. You must add a **per-stanza** grammaticality assertion so the guarantee is real.
- `_FETCH_CMD_RE` (the `Run: spec-kitty charter context --include …` line) must also keep matching.

## Subtasks

### T001 — Red-first per-stanza grammaticality test
Create `tests/charter/test_fetch_stanza_normalization.py`. For each representative clause shape, render via `fetch_stanza_lines` and assert the second line is grammatical **and** matches `_WHEN_DOING_RE` (import the real regex from the contract test module or re-declare the same pattern):
- leading gerund: `"designing or reviewing significant code changes"`
- full sentence w/ trailing period: the `STATED_DEFAULT_WHEN` value (import it)
- already well-formed: `"are about to apply a code change"` → assert byte-unchanged output
- a `need to …` / `review …`-style clause
This test is **RED** before T002. Use realistic clause strings (production-shaped), not `foo`.

### T002 — Normalize the clause in `fetch_stanza_lines`
Add a normalization helper (pure, in `fetch_stanza.py`) that maps an arbitrary authored clause into a form headed by one of the closed 6 lead-ins:
- if the clause already begins with one of the 6 lead-ins → pass through unchanged (no regression on the good path);
- if it is a full sentence / ends in a period → strip the trailing period and re-anchor to `are about to …` (or another lead-in that reads correctly);
- if it begins with a gerund → re-anchor (e.g. prefix the safe default) so the result reads naturally and matches the set;
- keep complexity ≤ 15; add focused unit tests for the helper itself.
Do NOT widen `_WHEN_DOING_RE` — that is a documented contract change reserved for a clause that genuinely cannot be mapped (out of scope here; if you hit one, stop and flag it).

### T003 — Fold the thin `_render_fetch_stanza` wrapper (campsite)
`context.py::_render_fetch_stanza` is a one-line wrapper delegating to `fetch_stanza_lines`. Move the public renderer form into `fetch_stanza.py` (e.g. expose `render_fetch_stanza(selector, when_clause)`); update the single call site in `context.py` to import it. This is a **small, declared out-of-map edit** to `context.py` (owned by WP06) — record the one-line rationale. Do not restructure anything else in `context.py`.

### T004 — Per-stanza assertion helper in the contract test
In `tests/specify_cli/next/test_wp_prompt_governance_contract.py`, add a helper that splits the rendered prompt into stanzas and asserts **each** `When you …` line individually matches `_WHEN_DOING_RE`. Keep the existing whole-prompt checks; the new per-stanza check is the SC-003 authority. Do not weaken existing assertions.

### T005 — Byte-unchanged good path + gates
Assert the already-well-formed clause path is byte-identical to today. Run:
```
uv run pytest tests/charter/test_fetch_stanza_normalization.py tests/specify_cli/next/test_wp_prompt_governance_contract.py -q
uv run ruff check src/charter/activation/context_renderers/fetch_stanza.py && uv run mypy src/charter/activation/context_renderers/fetch_stanza.py
```

## Branch strategy
Planning base `feat/charter-delivery-finish-context-degod`; final merge target `main` (via PR). The execution worktree is allocated per computed lane from `lanes.json` after `finalize-tasks`; enter the resolved workspace via `spec-kitty agent action implement WP01 --agent claude`. Do not reconstruct the path by hand.

## Definition of Done
- [ ] T001 red-first test committed before the fix (RED → GREEN).
- [ ] Every emitted stanza grammatical across all 4 clause shapes AND per-stanza `_WHEN_DOING_RE`/`_FETCH_CMD_RE` match.
- [ ] Already-well-formed clause is byte-unchanged.
- [ ] `_render_fetch_stanza` folded; single call site updated (out-of-map rationale recorded).
- [ ] ruff + mypy --strict clean; no new suppressions.

## Risks
- Over-eager normalization changing the good path (guard with the byte-unchanged test).
- Producing grammatical-but-non-matching output (the closed 6-verb set is the trap — test per stanza).

## Reviewer guidance
Confirm RED→GREEN on T001; grep the diff for any `# noqa`/`# type: ignore`; verify no widening of `_WHEN_DOING_RE`; verify the whole-prompt search was augmented (not replaced) and the per-stanza helper is the real guarantee.
