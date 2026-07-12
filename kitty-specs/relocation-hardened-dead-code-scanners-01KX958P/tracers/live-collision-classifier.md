# Tracer: Live Collision Classifier

**Concern**: IC-KEY (FR-005) + IC-RATCHET (DoD i) — the runtime-recomputed collision
detection that keeps T004 robust against corpus growth.

**Seed hypotheses (planning):**
- The collision set is re-derived every run (not frozen); today it == the ArtifactKind trio.
- A content key resolving to ≥2 live locations is escalated/fail-closed — this is the
  Defect-1 fix (a frozen split would silently re-blind a future byte-identical pair).
- The regression guard (DoD i) plants a NEW byte-identical same-name pair (the
  `GateDecision`-collapse vector) and proves the gate still catches the unsanctioned sibling.
- Perf: one `(bare_name → [locations])` index per run, not per-entry.

**Append during implement:** (actual collision-set members found beyond ArtifactKind?
index build cost? any ≥2-resolution surprises among the 394? escalation-vs-fail-close
decisions per case)

**Assess at close:** is the classifier genuinely live (re-run proves it)? Does the
GateDecision-collapse fixture red through the production path? Any perf regression on
the full arch suite runtime?
