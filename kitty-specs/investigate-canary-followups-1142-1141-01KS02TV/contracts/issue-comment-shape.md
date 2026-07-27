# Contract: GitHub Issue Comment Shape (#1142 / #1141)

**Mission**: `investigate-canary-followups-1142-1141-01KS02TV`
**Satisfies**: FR-002, FR-003, FR-006, NFR-003
**Posted via**: `gh issue comment <n> --body "$(cat …)"` (against `Priivacy-ai/spec-kitty`)

A "substantive comment" per NFR-003 must contain **all** of the four headings below. A reviewer must be able to reproduce the test inside 15 minutes from the comment alone — that is the binding acceptance criterion.

---

## Required headings (in order)

```
### Hypothesis tested
<label per spec.md — e.g., "H1 (stale canary venv)" or "H4+H3 (fixture state error ruled out, sequencing race ruled out)">

### Commands run
```
<exact commands, multi-line code block, no abbreviation>
```

### Evidence
<log excerpt, ≥ ~20 lines around the assertion or failure point; or a gist/Permalink URL if logs exceed 4 KB>

### Conclusion
<one of: CONFIRMED — H<n> explains the failure
         RULED_OUT — H<n> does not explain the failure; advancing to H<n+1>
         INCONCLUSIVE_IN_WINDOW — H<n> evidence inconclusive; documented for next operator>

[for #1141 only]
### Recommendation
<one of: A — open new mission; B — patch canary; C — small fix already in place>
```

---

## Closing behaviour (FR-003 specific to #1142)

When `Conclusion == CONFIRMED` and the confirmed hypothesis is the H1 "stale canary venv" operator trap, the comment that closes #1142 MUST additionally contain:

```
### Fix-pattern (closing comment)
Future canary operators: rebuild the canary venv from scratch between runs.
Do NOT `pip install --force-reinstall --no-deps` into a previously-used venv —
the spec-kitty package layout's namespace edges leave stale `.pth`/dist-info
artifacts that mask new code paths.

Reproduction recipe: see "Commands run" above.
```

The fix-pattern paragraph is mandatory for the closing comment so that operators searching `Priivacy-ai/spec-kitty` for "canary" find the trap named exactly once.

---

## Non-requirements (explicit)

- The comment does **not** need to enumerate hypotheses not yet tested.
- The comment does **not** need to attach test failure JUnit XML — log excerpt is sufficient.
- The comment does **not** need to cross-link to PR #1143 (orthogonal context).
