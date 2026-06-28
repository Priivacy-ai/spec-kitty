# Tooling-Friction Trace — coord-authority-gate-hardening-01KW4T2F

**Purpose:** running log of spec-kitty tooling friction. Seeded at spec→plan; append during implement; assess at close.
> Format: `[date] [phase] SYMPTOM — anchor — disposition (fixed/workaround/open)`

---

## Seeded during spec (2026-06-27)

1. **[env] No separate clone needed — runs on the primary checkout.** Unlike the prior two coord-authority missions (run in parallel clones), both #2194 + #2212 are MERGED, so the primary checkout is free; this mission specced on `feat/coord-authority-gate-hardening` from main. The active `spec-kitty` is an EDITABLE install (pyenv shim → `src/specify_cli` in this working tree) → it tracks the checkout, no version skew. **No friction — recorded as the baseline.**
2. **[watch] This mission HARDENS the gates it must not let regress.** gate-unmask-cannot-self-validate applies sharply: the FR-005 scan-scope un-mask + the FR-001/003 arm extension take effect on the merged tree → pair with a pre-merge full-gate dry-run (NFR-003). **OPEN (watch — the mission's own NFR).**

<!-- append during implement: arm false positives, the scan-scope un-mask dry-run, the #2197 routing, CT7 anchor friction. -->
