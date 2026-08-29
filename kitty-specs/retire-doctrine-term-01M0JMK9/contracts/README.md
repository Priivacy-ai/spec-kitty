# Planning contracts

| Contract | Output | Governs |
|---|---|---|
| `adr-content-contract.md` | Accepted ADR | operator override, Charter authority, complete scope, zero gate |
| `inventory-schema.md` | `inventory-hits.tsv` (ephemeral, hash-pinned), `inventory.md` | forced-text/NUL-safe set-equal inventory with the four fixed exclusion roots, no other exemptions |
| `operator-surface-map-schema.md` | M2 topology + CLI maps | all internal/public executable/code topology and collision closure |
| `stacked-plan-schema.md` | `stacked-plan.md` | exact M1–M6 ownership, dependencies, gates, rollback |

Cross-contract invariants:

1. Every current-tree content/path hit outside the four fixed exclusion roots is work; X1/X2/X3
   and current-tree historical/internal/test exemptions beyond those roots are invalid. `kitty-specs/`,
   `.kittify/migrations/mission-state/quarantine/`, `kitty-ops/`, and `.kittify/missions/` are the four
   immutable historical-record roots (`DM-01M0NMS9WPH33EPFCJQRTQVNSA`, amended by
   `DM-01M0P6C8C7Q6SPBT412V39RPN0`): no pre-existing slug/directory/file under any of them is renamed or
   edited, and both audits exclude all four by independent fixed pathspecs.
2. `stacked-plan.md` assigns every hit exactly once to M1–M6; current-repository deferral is forbidden.
3. M1 updates the complete Charter authority and atomically parity-joins docs context,
   `.kittify/glossaries/spec_kitty_core.yaml`, the built-in glossary pack, and active referrers; it records
   the explicit terminology-extinction override through owning workflows. Activation is engine-owned,
   and existing interview answers use a sanctioned lossless migration before interactive ownership resumes.
4. M2 owns all old executable/code topology, including private modules/symbols/tests/build hooks.
5. M3/M4 preserve data at canonical destinations but cannot complete with old-named roots/assets.
6. M5 rewrites current-tree ADR/docs/archive/history/evidence bytes and filenames outside the four fixed
   exclusion roots; Git object history and those four roots remain (runtime may keep appending new records
   to the three non-archive roots). Archive referrers are recited by `mission_id`/mid8 or a token-free path.
7. M6 removes every compatibility/control/fixture/baseline and passes checked content/path audits at zero
   (the four fixed exclusion roots only), through the mandatory token-literal-free entrypoint/check marker,
   bound externally to the final commit/tree and rerun by CI/release after any tree change. Negative tests
   encode the token numerically. `inventory-hits.tsv` is ephemeral, untracked evidence pinned by SHA-256 in
   `inventory.md` (`DM-01M0NMSD60JYG7K7V5MJCKJ3P8`).
8. These are planning contracts only. No runtime managed-path ledger/state architecture is introduced.
