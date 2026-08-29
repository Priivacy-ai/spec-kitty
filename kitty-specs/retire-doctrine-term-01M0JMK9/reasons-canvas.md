# REASONS Canvas — Retire the Doctrine Term

> Mission: retire-doctrine-term-01M0JMK9
> Updated: 2026-08-22
> Scope: research/planning only

## Requirements

- Plan complete extinction of the case-insensitive token from current `HEAD` content and tracked pathnames
  outside the four fixed exclusion roots (`kitty-specs/`, `.kittify/migrations/mission-state/quarantine/`,
  `kitty-ops/`, `.kittify/missions/`); the fixed exclusions are Git object history outside `HEAD` and those
  four immutable historical-record roots (`DM-01M0NMS9WPH33EPFCJQRTQVNSA` as amended by `DM-01M0P6C8C7Q6SPBT412V39RPN0`).
- Record an Accepted ADR and M1-effective Charter exception that supersedes customization/path and
  current-tree historical immutability only for this terminology program, while preventing data loss.
- Inventory every hit outside `kitty-specs/`, including internal code, tests, metadata, generated assets,
  history, and fixtures. Assign every hit exactly once to M1–M6; no X/allowlist/deferral. The TSV is
  ephemeral, hash-pinned evidence.
- Terminal proof is forced-text blob count 0 plus NUL-safe pathname count 0 over `HEAD` with the fixed
  `kitty-specs/` exclusion.

## Entities

- **Charter Pack**: versioned governance catalogue, offer side.
- **Charter Bundle**: per-project materialized set under `.kittify/charter/`, consume side.
- **Active/Inactive Charter**: activation state of one governance artefact.
- **Occurrence hit/class**: exact audit coordinate and one semantic work grouping.
- **Compatibility reservation**: bounded 3.x alias budget, introduced once and removed with its controls in
  M6; never a terminal exception.

## Approach

Strict authority-first stack:

1. M1 updates ADR + complete Charter/glossary owner graph and records the override.
2. M2 freezes/applies every internal+public code topology row, merging the old source tree into a
   collision-free `src/charter/` aggregate.
3. M3 preserves project overlay data at `.kittify/charter-packs/` and removes old root on completion;
   divergence blocks.
4. M4 canonicalizes all source/generated/installed/shared agent assets and removes old paths on completed
   migration.
5. M5 rewrites/renames all remaining current-tree prose/history/ADR/docs/archive/evidence/referrers outside
   `kitty-specs/`; the archive stays byte-identical.
6. M6 removes every alias/key/path/control/fixture/baseline and proves exact zero over `HEAD` outside the
   fixed `kitty-specs/` root.

Rejected: user-facing-only scope; internal/history X classes; runtime managed-path ledger overdesign;
silent overwrite; preserving old path after completed migration; terminal supported-surface audit.

## Structure

- Planning WPs remain one stream: ADR → inventory → methodology → stacked plan → verification.
- `stacked-plan.md` owns exact OC/hit assignment across M1–M6.
- M1 has zero local decisions. M2 has one bounded pre-edit topology-map approval with every collision
  resolved. M3–M6 have no policy question.
- Every downstream wave is `bulk_edit`, captures a fresh base/audit, and has explicit merge/rollback gates.

## Operations

- Freeze `origin/main` and implementation base before WP01 edits.
- Use forced-text `git grep -a` and NUL-safe `git ls-tree -z`; derive inventory, not vice versa.
- Verify the closed Charter owner/action/no-op table and obsolete-graph deletion at M1; do not treat all
  `.kittify/charter/` artifacts as `charter generate` outputs.
- Use backup → checked canonical copy/move → verify → old-path removal for M3/M4; divergent collision keeps
  both and blocks.
- M6 numeric-byte negative tests avoid storing the forbidden token after cleanup.

## Norms and safeguards

- Planning mission edits docs/artifacts only; no product rename or lifecycle transition.
- Explicit operator override is narrow: terminology extinction only, no unrelated cleanup/data loss.
- Current-tree historical files outside `kitty-specs/` are mutable M5 work; Git object history and the
  immutable `kitty-specs/` archive remain the proof trail.
- No M6 exception, allowlist, baseline, external deferral, unreadable blob, or narrowed audit can pass.
- Rollback: revert one wave before dependents; afterward reverse suffix/forward-fix; M3/M4 restore verified
  backup; post-4.0 rollback is release-level.

## Deviations / decisions

- 2026-08-21 — Discovery decisions were recorded after mission creation because the decision protocol
  requires a mission handle.
- 2026-08-22 — Operator superseded the prior user-facing-only scope. Complete current-tree extinction now
  governs; internal/history/test/generated/metadata hits are work and only Git object history is excluded
  (later amended by `DM-01M0NMS9WPH33EPFCJQRTQVNSA`: the immutable `kitty-specs/` archive root is the second fixed exclusion).
- 2026-08-22 — Rejected managed-path runtime ledger architecture as unnecessary planning overdesign;
  M3/M4 use bounded backup/verify/conflict/rollback contracts.
- 2026-08-22 — `DM-01M0NMS9WPH33EPFCJQRTQVNSA`: `kitty-specs/` is an immutable historical archive — no
  mission slug, directory, or file under it is renamed or edited; it is the single fixed exclusion root of
  both audits. `DM-01M0NMSD60JYG7K7V5MJCKJ3P8`: `inventory-hits.tsv` is ephemeral, hash-pinned evidence,
  not a committed artifact.
- 2026-08-23 — `DM-01M0P6C8C7Q6SPBT412V39RPN0` (amends `DM-01M0NMS9WPH33EPFCJQRTQVNSA`): the fixed exclusion
  set is widened from the single `kitty-specs/` root to **four** immutable historical-record roots —
  `kitty-specs/`, `.kittify/migrations/mission-state/quarantine/`, `kitty-ops/`, `.kittify/missions/` —
  excluded by the same fixed, enumerated pathspec mechanism (not an allowlist); no wave edits/renames/deletes
  a pre-existing path under any of the four roots.
