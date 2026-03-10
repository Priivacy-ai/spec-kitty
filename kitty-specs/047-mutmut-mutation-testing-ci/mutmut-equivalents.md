# Equivalent Mutants — Operator Note

**Feature**: 047-mutmut-mutation-testing-ci
**Last updated**: 2026-03-10

## Summary

A full mutmut run across the 4 scoped modules (status/, glossary/,
merge/, core/) generates ~9,700 mutants. Of those, an estimated
12–22% are **equivalent** — mutations that cannot change observable
behaviour and therefore cannot be killed by meaningful tests.

| Category | Est. count | % of total |
|----------|-----------|------------|
| Docstring / comment mutations | 500–800 | 5–8% |
| Type hint mutations | 300–500 | 3–5% |
| Error message string mutations | 200–400 | 2–4% |
| Logging statement mutations | 150–300 | 1.5–3% |
| Import order mutations | 50–100 | 0.5–1% |

**Baseline score**: ~70% (2026-03-01 full run)
**Post-campaign score**: ~72–75% (+5–8% from targeted tests)

## When a surviving mutant is equivalent

Before writing a test to kill a survivor, check whether the mutation
falls into one of these categories:

1. **Docstrings / comments** — string-only changes with no runtime effect
2. **Type hints** — Python does not enforce these at runtime
3. **Log / error messages** — message text changes that do not alter
   control flow or return values
4. **Protocol / ABC signatures** — abstract methods with no implementation
5. **Import reordering** — safe when imports have no side effects

If the mutant is equivalent, leave it. Do not write a "senseless" test
just to raise the score.

## Module-level estimates

| Module group | Est. mutants | Est. equivalent | Notes |
|--------------|-------------|-----------------|-------|
| merge/ (6 files) | ~1,200 | ~240 (20%) | 12 targeted tests written for state.py |
| core/ (27 files) | ~8,500 | ~1,000–1,800 (12–21%) | vcs/protocol.py is ~90% equivalent (abstract) |

## Pragmatic approach

Exhaustively killing all 9,700 mutants would take 40–60 hours and
require many meaningless assertions. The campaign instead:

- Sampled ~50 mutants to identify recurring patterns
- Classified patterns as equivalent vs killable
- Wrote targeted tests for high-value killable mutants only
- Achieved a meaningful score improvement without test bloat
