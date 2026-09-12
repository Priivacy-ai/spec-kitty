# Contract: Fetch-stanza when-clause normalization (US2 / FR-001, NFR-003)

## Site
`context_renderers/fetch_stanza.py::fetch_stanza_lines` (line ~133) — the single
composition choke-point for `When you {clause}, run this command and apply the returned rule.`

## Pinned wire contract (must keep matching, per-stanza)
- `_FETCH_CMD_RE` — the `Run: spec-kitty charter context --include <selector>` line.
- `_WHEN_DOING_RE = r"when\s+you\s+(are\s+about\s+to|need\s+to|encounter|introduce|rename|review)"` — **closed 6-verb set**.
  (`tests/specify_cli/next/test_wp_prompt_governance_contract.py:221`.)

## Behaviour
| Given clause shape | Then emitted line |
|---|---|
| leading gerund (`designing or reviewing significant code changes`) | grammatical, headed by a closed lead-in (e.g. `are about to …`), matches `_WHEN_DOING_RE` |
| full sentence w/ trailing period (`STATED_DEFAULT_WHEN` fallback) | no `When you <sentence>., …` doubling; grammatical; matches |
| already well-formed (`are about to apply a code change`) | **byte-unchanged** from today |

## Assertion upgrade
NFR-003 is asserted **per rendered stanza** via a dedicated helper, not the current
whole-prompt `_WHEN_DOING_RE.search(prompt)` (which passes if any single line matches).

## Escape hatch
If a clause genuinely cannot be mapped into the closed set, `_WHEN_DOING_RE` is widened
as a **deliberate, documented** contract change kept in sync with
`kitty-specs/wp-prompt-governance-payload-01KRR8HS/contracts/charter-context-resolver.md`.
Default is to normalize, not widen.
