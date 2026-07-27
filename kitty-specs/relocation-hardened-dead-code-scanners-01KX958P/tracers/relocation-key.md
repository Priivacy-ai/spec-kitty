# Tracer: Relocation Key

**Concern**: IC-KEY / IC-REKEY — the relocation-tolerant `SymbolKey` and the 394-entry re-key.

**Seed hypotheses (planning):**
- Content-only `(bare_name, body_hash)` gives relocation tolerance for the simple subset
  (majority of 394); the ~100+ known re-export/facade/fan-out forfeit by design.
- AnnAssign support (14 constants) is the highest-priority correctness item — the spike
  has no AnnAssign branch, so this is the re-introduced T001 bug.
- `_compute_offenders` needs a signature change to receive source/AST (`path_to_tree`).

**Append during implement:** (surprises, signature ripple, keyability edge cases, which
of the 394 refused to key, category-boundary discoveries)

**Assess at close:** did content-only cover the expected simple majority? How many
entries actually forfeited (vs the ~100+ estimate)? Did the AnnAssign branch match the
14 census constants?
