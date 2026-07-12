# Tracer — Standing Meta-Guard (IC-METAGUARD, FR-004)

Seeded at planning. Append during implement; assess at close.

**Thesis**: a single standing gate bans positional anchors across ALL
`tests/architectural/`, with a codified authoritative-vs-diagnostic rule — this is
the DIR-041 generalization + #2077's recurrence guard.

**Watch for (append findings during implement):**
- [ ] The authoritative-vs-diagnostic classification: was a heuristic enough, or
      did seeds need an explicit marker/typed wrapper? (record the mechanism chosen.)
- [ ] Did the guard false-positive on the two compliant YAMLs' `line:` fields or a
      count-floor baseline? (must not — record the exemption that fixed it.)
- [ ] Any OTHER positional-anchored seed the guard surfaced that the squad
      inventory missed? (record — completeness signal.)
- [ ] Did the red-first→green sequencing hold (guard only green post-WS1)?

**Close-out assessment**: does the guard actually prevent recurrence (plant a new
anchor → red)? Coordinate #2077 closure. Confirm the two deferred census
allow-lists are enumerated with a live follow-up.
