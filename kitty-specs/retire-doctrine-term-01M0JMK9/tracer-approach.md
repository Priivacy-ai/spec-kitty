# Tracer: Approach — retire-doctrine-term

Seeded at planning (post-analyze, pre-implement). Append during implementation; assess at close per the
`mission-tracer-files` procedure (charter Standing Order #3).

## Scope

Planning-only mission (C-001): author the ADR, run the exhaustive occurrence inventory, write the
ordering/methodology, write the executable M1–M6 stacked plan, and independently verify — for the
program that retires the token `doctrine` in favour of `charter`. No product rename happens here.

## Approach

- Single sequential lane WP01→WP05; each WP consumes the previous WP's authority/evidence.
- Operator-fixed boundaries (decision ledger): full current-tree extinction
  (`DM-01M0NDJ33GCKATG3H4BK4PAMNG`); `kitty-specs/` is an immutable historical archive and the single
  fixed exclusion root of the audits (`DM-01M0NMS9WPH33EPFCJQRTQVNSA`); `inventory-hits.tsv` is
  ephemeral, hash-pinned evidence (`DM-01M0NMSD60JYG7K7V5MJCKJ3P8`).
- Audits are checked Python subprocesses (no shell pipelines) with frozen argv; the same argv runs
  in inventory and terminal mode. Live orientation on 2026-08-22 `origin/main`: 48,328 content records
  across audited `HEAD` (39,167 more inside the excluded root) and 722 pathnames (1,070 more inside it).
- OC assignment for tens of thousands of rows must be rule-derived (ordered path-prefix/seam predicates
  recorded in `inventory.md`), never hand-labelled (analysis finding U1).

## WP01 (2026-08-22, scribe-sally)

Froze `implementation-baseline.json` (target `origin/main` 2621a56d…, implementation base 00b7eb06…,
ancestry checked) before any edit; authored the ADR section-by-section from
`contracts/adr-content-contract.md` (decision/effectiveness, four vocabulary terms, verbatim override,
scope/owner table incl. the archive row, fixed seams + seven ID mappings, per-artifact M1 owner map,
M2–M6 summary, exact terminal audit with the fixed `kitty-specs/` exclusion); registered it with
`scripts.docs.freshen_adr_inventory` + `--check` (no hand edits to generated index/lockfile).

## WP02 — inventory (curator-carla, 2026-08-23)

- One Python procedure (embedded verbatim in `inventory.md` §8; working copy `inventory-audit.py` is gitignored)
  runs both checked subprocesses, parses NUL records without ever splitting on `:`, hashes rows with the v1 LP
  preimage, sorts/IDs deterministically, and classifies by two ordered predicate tables (content / pathname) with
  no catch-all — an unmatched path is an audit error, which is how completeness of the rule table was proven.
- Result at `2621a56d…`: 48,328 content + 722 pathname rows (49,050), 2,056 files, 45 OCs, 8 CR candidates;
  TSV `3631531b…` (9.1 MB, untracked). Excluded-root orientation: 39,167 content / 1,070 pathnames.
- Self-tests: rc-1-empty acceptance, rc>1 rejection, ls-tree failure propagation, failing-git/invalid-commit
  mutation in both modes, hostile-path fixture, two-process byte identity (fixture + real tree), and an
  independent recompute of all 49,050 hashes.

## WP03 — methodology (planner-priti, 2026-08-23)

- `methodology.md` sequences the 49,050 frozen-base rows across M1→M6 at the transition level using the WP02
  default owners (M1 304 · M2 13,259 · M3 111 · M4 647 · M5 34,729 · M6 0 base rows), restates I0–I6 verbatim,
  defines the shrink-only coordinate fingerprint guard (coordinate+hash subset rule, CR-budgeted exceptions only,
  ten named mutations), the CR state machine, one named verifier per S1–S10 plus the mandatory M1–M6 cases, an
  every-wave archive byte-identity check, per-wave inputs/outputs/tests/gates, and the rollback ladder.

## WP04 — Stacked Mission Plan

- `stacked-plan.md` writes the six wave entries with all 17 schema fields, one-row-per-OC primary ownership (44
  populated classes → M1 4, M2 20, M3 3, M4 7, M5 10; OC-05/OC-50 unused), the CR-01…CR-08 source/introduction/removal
  table, the disjoint-union arithmetic (304 + 13,259 + 111 + 647 + 34,729 + 0 = 49,050, identical to `methodology.md`
  §1.2), cross-wave joins, the M1 zero-decision dry run (per-artifact owner map → action/no-op) and the M2 pre-edit
  topology-map dry run. The archive gate is stated in executable form (no pre-existing `kitty-specs/` path edited,
  renamed, or deleted; only the wave's own new mission directory may be added), folding the WP03 reviewer's note.
- `#2727` row refreshed (analysis I3): closure deferred to the issue owner; the glossary-authority slice bound into M1.

## WP05 — verification (reviewer-renata, 2026-08-23)

- Verified rather than repaired: re-derived every claim from the artifacts and the frozen base (`2621a56d…`) —
  ancestry + planning-only diff (4 docs paths + mission dir), eight ADR questions answered from the ADR text alone,
  TSV regenerated from the `inventory.md` §8 script into scratch (SHA-256 `3631531b…` byte-identical, 48,328 + 722),
  own-code `match_sha256` recompute (2,002 content + 722 pathname rows, 0 mismatches), direct-argv set equality,
  wave arithmetic/CR joins recomputed from the regenerated TSV, workflow/docs/terminology gates green. Verdict PASS,
  no routed findings (`verification-report.md`).

### Assess at close (mission-tracer-files procedure)

The single-stream WP01→WP05 approach held: each WP consumed the previous authority/evidence and the reviewer could
reproduce every number independently. The two highest-value design choices were rule-derived OC classification
with no catch-all (made 49,050-row verification mechanical) and the ephemeral, hash-pinned manifest (regenerate-and-
match is a stronger proof than a committed TSV). Insight for the retrospective: keep "reviewer reproduces from the
contract, not from the implementer's script" as the standing check for any future inventory/audit mission.

## Whole-mission adversarial squad fold (orchestrator, 2026-08-23)

Four profile-loaded lenses (architect-alphonso, debugger-debbie, planner-priti, reviewer-renata) reviewed the merged
mission; convergent findings were folded in one commit (`squad-findings-whole-mission.md`): terminal contract hardened
(toplevel-only, `:(top)` pathspec, `--full-tree`, symlink-target + normalised-content passes, commit-OID attestation),
guard re-keyed tree-independently, archive gate restated as a merge-base-scoped test, ownership re-derived by live seam
(OC-03 and OC-41 → M2; CR-07 introduced by M2; CR-01/CR-04/CR-05 re-sourced), wave-gate semantics made carried-forward-
aware, M6 release row added. The frozen-base TSV and hash were not touched. Hand-offs that remain open for M1 adoption:
M2 sizing (one 13k-row PR vs declared slices) and the deferred operator decision `DM-01M0P6C8C7Q6SPBT412V39RPN0`
(serialized historical records) for M5. The earlier "no decision open at close" statement is superseded by this list.
