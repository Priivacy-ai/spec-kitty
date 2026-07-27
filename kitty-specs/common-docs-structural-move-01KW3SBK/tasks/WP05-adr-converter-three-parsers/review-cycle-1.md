# WP05 Review — Cycle 1 (reviewer-renata)

**Verdict: Changes requested — one issue.** The production code is correct and the
WP is otherwise excellent. The single blocker is a **test-pinning gap on the
raw-byte content-invariance contract** — the very property the C-002 / NFR-001
merge-blocker exists to protect across 117 ADRs.

## What is correct (no action needed)

- Three parsers (table / bold-inline / dash-bullet) each extract title/status/date
  + body offset via a shared `_build_header` driver. ✅
- Dash-bullet **boundary rule** is correct and pinned:
  `test_dash_bullet_body_bullets_are_body_not_header` proves `- selected_paradigms`
  body bullets survive as body. ✅
- `invariant()` is a **raw-byte** `==` compare (not a re-render). ✅
- Post-image strip **reuses** `scripts.docs._inventory.parse_frontmatter`; no forked
  YAML parser (the lone `YAML()` in the module is the emitter, not a parser). ✅
- Emitter writes **bare `status`** in MADR vocab, title→status→date, never
  `doc_status`; `ruamel.yaml`; **pyproject untouched** (no new dependency). ✅
- Malformed input fails closed: status-less, non-MADR, titleless each raise a clear
  `AdrParseError`. ✅
- Tooling-only: WP05 commit touches only the 2 owned files; no ADR moved/rewritten. ✅
- 18 tests pass; ruff clean; `mypy --strict --explicit-package-bases` clean. ✅

## Issue 1 — the mutation fixture does not pin the *raw-byte* requirement (NFR-001 "not normalised")

**The crux property of this WP is that `invariant()` compares raw bytes, NOT a
normalised/re-rendered body** (spec T031: "A re-render comparison is a false-green —
assert raw bytes"). The current suite proves the assertion is *load-bearing* but does
**not** prove it is *raw-byte*, because the only mutation fixture
(`test_mutation_fixture_drives_invariance_red`) is a **word substitution**
("skill-only" → "slash-command-only"). A whitespace-normalising compare catches a word
swap just as well as a byte compare, so the fixture cannot distinguish the two.

Empirical proof (probes run during review, reverted):

- **Probe A** — force `invariant()` to `return True`: the mutation test FAILS.
  (Good — the assertion is non-vacuous.)
- **Probe B** — weaken `invariant()` to a whitespace-normalised compare
  (`body_minus_header(pre).split() == body_minus_frontmatter(post).split()`):
  **all 18 tests still pass.** A regression from raw-byte to normalised would ship
  green — exactly the false-green this merge-blocker must prevent.
- **Discriminating case** — a whitespace-only body mutation (a double space in the
  Decision body):
  - raw-byte `==` → `False` (RED, caught) ✅
  - normalised `.split()` → `True` (MISSED) ❌

So today, nothing in the suite would red-first if a future edit normalised the
comparison. That defeats the protection across the 117-ADR WP06 run.

### Required fix (small, within owned files)

Add a **whitespace-only mutation test** to `tests/docs/test_adr_converter.py` that
goes RED under the raw-byte compare and would go GREEN (i.e. fail) under a normalised
compare — locking the "not normalised" contract into the suite. For example: take
`convert(BOLD_ADR)`, introduce a single whitespace-only change in the decision body
(e.g. a doubled space or an altered code-block indent), assert the mutation landed,
and assert `not invariant(BOLD_ADR, mutated)`. Keep the existing word-substitution
test as well (it guards content edits); the new test guards the byte-vs-normalised
distinction.

This is a directive-041 fidelity fix: the test must red-first on the actual contract
it claims to guard (raw-byte invariance), not merely on gross content changes.

## Note for WP06 (NOT a WP05 blocker) — non-MADR status handling

The implementer's IC note is correct that the emitter rejects non-MADR status strings
fail-closed (`AdrParseError`), so a real ADR carrying `Active` or
`Accepted (superseded by …)` will error during the WP06 bulk run.

**Recommendation: keep fail-closed in the converter core; do NOT auto-normalise
silently.** Auto-mapping `Active`→`Accepted` or stripping `(superseded by …)`
parentheticals is a *semantic* decision a tool must not make silently under C-002.
Instead, for WP06:
1. Run a cheap census of the actual `Status:` values across all 117 real ADRs first
   to enumerate the real outliers.
2. For `Accepted (superseded by X)` the MADR-correct mapping is usually `Superseded`
   (or `Accepted` + an explicit `superseded-by` note) — a per-ADR human call.
3. Add a **small, explicit, reviewed alias table** for the handful of known real
   variants (documented, not silent) rather than blanket parenthetical-stripping.

Net: fail-closed-and-surface is the right default; pair it with a pre-run census +
an explicit reviewed alias map for the few outliers. This belongs in WP06.
