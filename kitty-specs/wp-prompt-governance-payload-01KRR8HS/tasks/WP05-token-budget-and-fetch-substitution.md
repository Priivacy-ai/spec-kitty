---
work_package_id: WP05
title: Token budget enforcement and fetch substitution mechanism
dependencies:
- WP04
requirement_refs:
- NFR-001
- NFR-002
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
agent: claude
agent_profile: python-pedro
authoritative_surface: src/charter/context_renderers/
execution_mode: code_change
owned_files:
- src/charter/context_renderers/token_budget.py
- src/charter/context_renderers/fetch_stanza.py
- tests/charter/test_context_token_budget.py
- scripts/measure-wp-prompt.py
role: implementer
history: []
tags: []
---

## Objective

Enforce NFR-001: the augmented WP prompt MUST stay under 32 000 characters total
(proxy for ~8 000 tokens). When the rendered governance payload exceeds the budget,
auto-substitute the longest sections with `fetch + when-doing` stanzas until the
budget is met. Emit a single warning line summarising the substitutions.

This WP also delivers the baseline measurement that NFR-002 (latency ≤ 1.5× of
pre-mission baseline) is asserted against, run against
`layered-doctrine-org-layer-01KRNPEE` WP01–WP10 prompts per C-004.

---

## Module organisation note

To keep ownership boundaries clean between WP03, WP04, and WP05, the helpers introduced
here MUST live in `src/charter/context_renderers/`:

- `src/charter/context_renderers/token_budget.py` — `_apply_token_budget` (T019)
- `src/charter/context_renderers/fetch_stanza.py` — `_fetch_stanza` (T020)

`src/charter/context.py` imports from this submodule. WP03 + WP04 renderers refactor
their inline stanza construction to call `_fetch_stanza` from the new submodule.

---

## Context

WP03 + WP04 inline a lot of new content into `CharterContextResult.text`: profile-cited
directive bodies, profile-cited tactic bodies, action-critical section bodies. On a
project with rich charter prose and a chatty profile, the rendered text can easily
break the 32 k character budget the plan pins as NFR-001.

The substitution rule is deterministic and reversible: each section's body is replaced
by the canonical fetch stanza (`Run: spec-kitty charter context --include <selector>`)
plus the when-doing conditional sentence the renderer already knows how to emit (from
WP03 + WP04). The executing agent can recover the body on demand.

This WP also delivers the only non-test ATDD-adjacent surface: the aggregate
`test_implement_prompt_self_sufficiency` test fails any time the rendered payload is
either too sparse OR too bloated; the token budget is the bloat-side gate.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Worktree**: allocated by `finalize-tasks`
- **Implement command**: `spec-kitty agent action implement WP05 --agent claude`

---

## Subtask T019 — Implement `_apply_token_budget(text, budget=32_000)`

**File**: `src/charter/context.py`

```python
_BUDGET_DEFAULT = 32_000  # NFR-001 — ~8000 tokens at 4 chars/token


def _apply_token_budget(
    rendered_sections: list[tuple[str, str, str]],  # (section_id, header, body)
    budget: int = _BUDGET_DEFAULT,
) -> tuple[str, list[str]]:
    """Combine sections into a single text under the character budget.

    Substitution algorithm:
      1. Render the join of all sections; if len <= budget, return as-is.
      2. Sort sections by body length (longest first).
      3. Pop the longest; replace its body with the canonical fetch stanza
         derived from section_id (selector ``directive:`` / ``tactic:`` /
         ``section:``).
      4. Re-render; if still over budget, repeat.
      5. When all bodies have been substituted, emit a single trailing line:
         ``# Governance payload: <N> sections substituted with fetch commands (budget=<B>).``

    Returns (joined_text, list_of_substituted_section_ids).
    """
```

The renderer chain in `_render_bootstrap_text` should be refactored to build the
section list (header + body) as tuples and only call `_apply_token_budget` once at the
end, rather than each `_render_*` helper performing its own substitution.

---

## Subtask T020 — Fetch + when-doing stanza formatter

**File**: `src/charter/context.py`

Centralise the stanza shape so every renderer (WP03 profile-cited, WP04 section bodies,
WP05 budget substitution) emits the same bytes:

```python
def _fetch_stanza(
    selector: str,           # "directive:DIRECTIVE_010" | "tactic:lang-driven-design" | "section:terminology-canon"
    when_doing_clause: str,  # "apply a code change" | "perform a terminology cutover" | ...
) -> str:
    return (
        f"Run: spec-kitty charter context --include {selector}\n"
        f"When you {when_doing_clause}, run this command and apply the returned rule."
    )
```

WP03 and WP04 helpers refactor their inline stanza construction to call this helper
(if they did not already). The token-budget substitution uses the same helper.

Selector derivation:
- Profile-cited directive → `directive:<id>` (e.g. `directive:DIRECTIVE_010`)
- Profile-cited tactic → `tactic:<id>`
- Action-critical section → `section:<kebab-slug>`

When-doing clause derivation:
- Directive — derived from the directive's `applies-when` field (or `apply a code change` fallback)
- Tactic — derived from the tactic's `when` field (or `apply a code change` fallback)
- Charter section — keyword map (see WP04 T015 table)

---

## Subtask T021 — Baseline measurement (C-004)

**File**: `scripts/measure-wp-prompt.py` (new, dev-only utility)

A small CLI helper that builds the prompt for a given WP and prints both:
- character count (for the NFR-001 budget assertion);
- wall-clock build time (for the NFR-002 latency assertion).

```bash
python scripts/measure-wp-prompt.py --feature layered-doctrine-org-layer-01KRNPEE --wp WP01
```

Run the helper against all 10 WPs of `layered-doctrine-org-layer-01KRNPEE` **before**
making any code change. Record the results in the WP05 activity log as a baseline:

```
WP01: 11_234 chars, 0.18s
WP02: 12_890 chars, 0.21s
...
```

Then re-run after WP03 + WP04 + WP05 changes land and assert:
- every WP's character count ≤ 32 000 (NFR-001).
- every WP's build time ≤ 1.5× baseline (NFR-002).

If a WP exceeds either threshold, the substitution algorithm needs tuning before this
WP can be marked done.

The helper does not need to ship as a `spec-kitty` subcommand; it lives under
`scripts/` as developer ergonomics.

---

## Subtask T022 — Unit tests for token budget

**File**: `tests/charter/test_context_token_budget.py` (new)

| Test | Scenario | Expectation |
|---|---|---|
| `test_under_budget_no_substitution` | three sections, total 8 000 chars, budget 32 000 | output unchanged; substituted list empty |
| `test_over_budget_substitutes_longest_first` | three sections (200, 30_000, 5_000), budget 10 000 | the 30_000-char section is replaced with a fetch stanza; other two untouched |
| `test_severely_over_budget_substitutes_all_bodies` | three sections, all 20 000 chars each, budget 10 000 | all three bodies replaced with fetch stanzas |
| `test_warning_line_emitted_when_any_substitution_happens` | any over-budget case | output ends with `# Governance payload: <N> sections substituted ...` |
| `test_warning_line_absent_when_no_substitution` | under-budget case | no warning line |
| `test_fetch_stanza_carries_when_doing_clause` | force substitution of a directive section | the emitted stanza contains both `Run: spec-kitty charter context --include directive:...` AND `When you ..., run this command and apply the returned rule.` |
| `test_aggregate_self_sufficiency_under_budget` | full bootstrap render against the `python-pedro` fixture | resulting `len(text) <= 32_000` AND the self-sufficiency test passes |

---

## Definition of Done

- [ ] `_apply_token_budget` exists and is unit-tested.
- [ ] `_fetch_stanza` exists; WP03 and WP04 renderers route through it.
- [ ] `scripts/measure-wp-prompt.py` exists; baseline + post-change measurements recorded in this WP's activity log.
- [ ] `tests/charter/test_context_token_budget.py` passes (7 tests).
- [ ] No WP01–WP10 prompt of `layered-doctrine-org-layer-01KRNPEE` exceeds 32 000 characters after this WP lands (NFR-001).
- [ ] No WP01–WP10 prompt of `layered-doctrine-org-layer-01KRNPEE` takes > 1.5× the baseline time to build (NFR-002).
- [ ] ATDD `test_implement_prompt_self_sufficiency` passes when run against a fixture mission with the `python-pedro` profile.
- [ ] `tests/architectural/test_layer_rules.py` (8 tests) still passes.
- [ ] All 14 currently-passing ATDD tests remain green.

---

## Risks

- **R-1**: The substitution algorithm picks the wrong section to substitute and produces
  a payload that no longer contains the rule body the test asserts on. **Mitigation**:
  substitute longest-first; verify each ATDD body-or-fetch test still passes (each one
  accepts either body or stanza). The aggregate self-sufficiency test catches this.
- **R-2**: NFR-002 latency regression slips through because the baseline measurement is
  taken on a fast machine. **Mitigation**: relative threshold (1.5×) rather than absolute;
  same machine for baseline and post-change measurements.
- **R-3**: A pathological charter with one enormous section that cannot be substituted
  (e.g. a single 50 k character `## Terminology Canon` block) busts the budget. The
  algorithm substitutes it (replacing with a fetch stanza), so the post-substitution
  length is small. The case is covered by `test_severely_over_budget_substitutes_all_bodies`.
- **R-4**: `scripts/measure-wp-prompt.py` itself drifts; future WPs add fields that the
  helper doesn't render. **Mitigation**: the helper invokes `_build_wp_prompt` directly,
  so it always emits the current shape.

---

## Reviewer Guidance

Check that:

1. The substitution algorithm is deterministic and order-independent — same input
   always produces same output (no `dict` iteration assumption on Python < 3.7).
2. The fetch-stanza shape exactly matches the contract:
   - line 1: `Run: spec-kitty charter context --include <selector>`
   - line 2: `When you <verb-clause>, run this command and apply the returned rule.`
   Drift here breaks the ATDD `_contains_either_body_or_fetch_with_conditional` helper.
3. The selector names use the canonical forms: `directive:`, `tactic:`, `section:`.
4. The when-doing clause for charter sections matches the keyword map in
   `contracts/charter-context-resolver.md` (Terminology Canon → "rename or introduce a
   term", Regression Vigilance → "perform a terminology cutover", Code Review Checklist
   → "prepare a WP for review").
5. The baseline + post-change measurements are recorded in the WP activity log with
   per-WP character counts and wall-clock times — not just an aggregate.
6. NFR-001 and NFR-002 numbers in the activity log are reproducible by running
   `scripts/measure-wp-prompt.py` again.
