# Orthogonality Matrix

Why all five paradigms — what each one catches that the others
structurally cannot.

| Paradigm | Catches | Misses without help from |
|---|---|---|
| The Falsifier | The highest-leverage hypothesis early; explicitly closes dead-end theories so they cannot be re-investigated | Trace evidence (Stenographer); structural causes (Cartographer) |
| The Five-Whys Cartographer | Terminal root cause; categorisation across Methods/Machines/Materials/Measurements/Manpower/Mother Nature; Pareto table linking incidents to root causes | When-did-this-start (Bisector); identity proofs across systems (Matrix-Maker) |
| The Bisector | Introducing commit, drift lifetime, upstream-vs-local verdict, precise timeline of contributing changes | Why the introducing commit was wrong (Cartographer); other-system view (Matrix-Maker) |
| The Matrix-Maker | Complete enumeration of divergences; dormant masks not yet observed; structural identity proofs | When (Bisector); observational confirmation (Stenographer) |
| The Stenographer | Bugs nobody is looking for; the discrepancy between what code claims and what traces show | Causal structure (Cartographer); enumeration (Matrix-Maker) |

## Convergence vs Divergence

When all five paradigms converge on the same fix, confidence is
structurally higher than any single investigator's certainty —
five independent epistemologies cannot share the same blind spot.

When paradigms diverge, the divergence is a signal. Investigate it
before discounting. A common pattern: The Stenographer disagrees
because trace data reveals a separate orthogonal bug; do not
suppress it to force convergence.

## Failure Modes Alone

- The Falsifier alone: speculation theatre.
- The Cartographer alone: linear narratives that mistake the
  loudest cause for the deepest.
- The Bisector alone: a precise timeline of a misunderstanding.
- The Matrix-Maker alone: a beautiful representation of a wrong
  assumption.
- The Stenographer alone: a haystack the size of the bug.

This is why we dispatch all five. Each is strong where another is
weak.
