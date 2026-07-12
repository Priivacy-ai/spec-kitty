# Tracer — Content-Descriptor Mechanism (IC-DESCRIPTOR keystone)

Seeded at planning. Append during implement; assess at close.

**Thesis**: one shared descriptor resolver (exactly-one, key-equal, normalized
matching) serves every WS1 gate — no per-gate reinvention.

**Watch for (append findings during implement):**
- [ ] Did any WS1 gate need a resolver behaviour the shared helper doesn't
      provide (a sign the abstraction leaks)?
- [ ] Any real same-qualname/same-token collision requiring `occurrence`? (record
      the site — it validates the D-2 disambiguator was necessary, not theoretical.)
- [ ] Did a descriptor ever resolve to 0 (author wrote raw-source substring) —
      caught by the FR-013 non-vacuity self-test? (record; it proves the guard works.)
- [ ] Enclosing-rename residual actually hit? (C-003 — confirm it's a genuine
      semantic change, not pure motion.)

**Close-out assessment**: was the shared resolver the right seam, or did WS1 gates
diverge? Did the exactly-one rule catch a real sibling-offender case?
