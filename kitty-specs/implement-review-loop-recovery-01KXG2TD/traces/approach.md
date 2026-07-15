# Approach Evolution

> Track how your approach changed as the Mission progressed.

## Entries

- 2026-07-14 — The initial program grouped four issue clusters into one Mission. Post-spec code-truth review narrowed delivery to #2573's live synchronous/non-streaming default gate path; fixed or unproven facets moved out.
- 2026-07-14 — Planning selected managed observation around the existing blocking gate instead of streaming pytest output or introducing a universal progress subsystem.
- 2026-07-14 — Post-plan review rejected CLI-owned background observation: timeout was collapsed into `no_coverage`, the child could not be cancelled, and deliverable auto-commit already preceded the gate. The design shifted to a typed polling runner inside the canonical gate authority plus pre-gate mutation reordering.
- 2026-07-14 — Post-tasks review retained one atomic WP because the exact-entry RED test requires both runner and CLI seams to become green; three internal review checkpoints bound the risk. The sync requirement was corrected from impossible enabled/disabled verdict equivalence to truthful pre-I/O skip behavior.
