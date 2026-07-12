# Tracer — WS2 Relocation-Proof Symbol Key (IC-WS2-KEY, tripwire)

Seeded at planning. Append during implement; assess at close.

**Thesis**: the dead-symbol allow-list can be re-keyed onto a relocation-proof
symbol identity WITHOUT re-blinding T004 (no bare-name-alone) — this is the
mission's design-risk concentration and the tripwire subject (C-004).

**Watch for (append findings during implement):**
- [ ] Design spike outcome: is the key stable under formatting/whitespace? (body-hash
      instability → **TRIPWIRE**: carve WS2 to standalone #2546.)
- [ ] WP count for the key + migration: >2 impl WPs → **TRIPWIRE**.
- [ ] T004 self-tests green with the same-name fixtures (`ArtifactKind`×3,
      `GateDecision`×2, `ResolutionResult`/`ResolutionTier`×2)? (must stay green —
      record; this is the no-false-negative proof.)
- [ ] FR-008 auto-derivation: does exempting only the *registered* symbol still
      catch a dead helper in an `m_*.py`? (plant one — record.)
- [ ] Did WS2 ever threaten to gate WS1/WS3 merge? (must not — C-004.)
- [ ] Any fight with #2293's category_b burn-down? (record + coordinate.)

**Close-out assessment**: did the tripwire fire (carved to #2546) or hold (shipped
in-mission)? Was the relocation key genuinely relocation-proof (move a symbol →
green, no edit) while preserving T004 bite?
