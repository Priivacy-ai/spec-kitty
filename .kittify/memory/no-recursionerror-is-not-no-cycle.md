# "No RecursionError" Is Not Evidence of "No Cycle"

**Why it's here:** a "no cycle" / no-infinite-recursion requirement is easy to
"verify" by running the code and observing no crash — but a green run only proves the
recursion *terminated*, not that the call graph is acyclic. This gap has already
produced one closed cycle that shipped past both an implementer's own check and a
173-test-green orchestrator verification; it was only found by an independent reviewer
tracing the call graph.

## The fact

When a delegation makes a leaf re-enter the seam it sits under, termination can be a
property of a **hard-coded constant or short-circuit** rather than of the call graph
being acyclic. The cycle is real; it stays silent until something changes that
constant or removes the short-circuit that happened to break it.

A seam with kind/type-specific short-circuits (a chokepoint that bypasses the normal
composition root for certain inputs) is a common source: those short-circuited call
sites sit *beneath* the seam and must call the target leaf directly — routing them
*through* the seam instead reintroduces the cycle the short-circuit was accidentally
hiding.

## How to apply

- For any "no cycle" / no-infinite-recursion requirement, demand a **structural**
  check, not a runtime one: trace every input variant through the entry point and
  assert **zero** entries into the symbol that must not be re-entered (e.g. via
  `sys.setprofile` on the target's code object, which catches all module bindings, not
  just one import site).
- Treat "no crash" and "tests green" as **absence of evidence**, never evidence of
  absence, for this class of requirement.
- Before delegating work that touches a seam with known short-circuits, enumerate the
  short-circuits first — each one marks a call site that must bypass the seam by
  design, not a bug to "fix" by routing it through.
