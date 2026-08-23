# Work Packages: Complete Terminology-Extinction Research Plan

**Inputs**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`
**Execution**: planning artifacts only; WP01→WP02→WP03→WP04→WP05
**Terminal program rule**: zero case-insensitive current-`HEAD` content and tracked pathname occurrences
outside the four fixed exclusion roots (`kitty-specs/`, `.kittify/migrations/mission-state/quarantine/`,
`kitty-ops/`, `.kittify/missions/`); the fixed exclusions are Git object history outside `HEAD` and those
four immutable historical-record roots (`DM-01M0NMS9WPH33EPFCJQRTQVNSA` as amended by
`DM-01M0P6C8C7Q6SPBT412V39RPN0`).

## Path conventions

- Mission outputs: `implementation-baseline.json`, `inventory.md`, `inventory-hits.tsv` (ephemeral,
  untracked via mission-local `.gitignore`, hash-pinned in `inventory.md` — `DM-01M0NMSD60JYG7K7V5MJCKJ3P8`),
  `methodology.md`, `stacked-plan.md`, `verification-report.md`.
- ADR: new file + prior ADR status/pointer + generated index/page inventory.
- Contracts/data/research/quickstart are read-only WP inputs.
- No product source/Charter/test/skill/migration edit belongs to this planning mission.

## WP01 — ADR Authoring and Registration (P0)

**Goal**: create/register a self-sufficient ADR recording complete current-tree extinction, the operator's
narrow no-data-loss override, M1 Charter authority update, M2 all-code topology convergence, M3/M4
old-path-extinguishing migration, M5 current-tree history rewrite outside the immutable `kitty-specs/`
archive, and M6 exact zero gate with that one fixed exclusion.
**Prompt**: `tasks/WP01-adr-authoring-registration.md`
**Requirements**: FR-001..FR-005, FR-011, NFR-002, C-001..C-005

T001 Fetch/ancestry-check `origin/main`; atomically persist exact target + implementation base; author ADR
from template with all `contracts/adr-content-contract.md` items.
T002 Update prior ADR status/pointer; state that M5 later rewrites/renames all current-tree historical ADR
content outside `kitty-specs/` under the override while Git history and the archive preserve prior bytes.
T003 Register through `python -m scripts.docs.freshen_adr_inventory`; run `--check`.
T004 Independently precheck full-current-tree-outside-`kitty-specs/` scope, the contract's exact
per-artifact Charter owner/no-op
map, exact seven-ID mappings, atomic three-authority glossary parity/#2727 join, exact fail-closed audits,
activation-engine-only activation, lossless answers migration/serializer round trip, and no
internal/history/X/runtime-ledger exception beyond the fixed archive root.

**Gate**: reviewer derives M1–M6 and exact I6 from ADR alone; M1 needs zero decisions.

## WP02 — Exhaustive Occurrence Inventory (P0)

**Goal**: set-equal per-hit manifest for all forced-text content and matching tracked pathnames outside
`kitty-specs/`; no exempt classification; TSV ephemeral and hash-pinned in `inventory.md`.
**Prompt**: `tasks/WP02-occurrence-inventory.md`
**Requirements**: FR-006, FR-007, NFR-001, C-003, C-005

T005 Load frozen target; run exact no-pipeline Python subprocess wrappers for `git grep -a` (fixed
`:(exclude)kitty-specs/`) and NUL-safe `git ls-tree -z` (drop `kitty-specs/` after rc check); preserve raw
return codes and fail on grep rc >1 or any ls-tree nonzero rc; record excluded-root orientation counts.
T006 Create deterministic, untracked `inventory-hits.tsv`; every row has OC + S1–S10. Include internal
source/tests/build, history/ADR/docs, fixtures/controls, metadata/generated, Charter, installed/pathname
surfaces.
T007 Prove set equality, canonical domain-tag/LP/big-endian `match_sha256` for both row kinds,
byte-identical independent reproduction, stable IDs, and no duplicate/unclassified/X/exempt rows; record
TSV SHA-256, row count, and reproduction command in `inventory.md`.
T008 Derive inventory/OC sets and disjoint CR candidates; split classes wherever M1–M6 owner differs.

**Gate**: regenerated manifest union exactly equals audit outputs and matches the recorded hash;
current-repository deferral impossible.

## WP03 — Ordering and Methodology (P1)

**Goal**: author deterministic M1→M6 sequence, I0→I6, verifiers, safe migrations, guards, and rollback.
**Prompt**: `tasks/WP03-ordering-methodology.md`
**Requirements**: FR-008, C-004

T009 Define strict invariants: M1 full authority/override; M2 all code topology; M3 no old project root;
M4 no old installed path; M5 no remaining current-tree prose/history outside `kitty-specs/` and archive
byte-identical; M6 exact zero with the one fixed exclusion.
T010 Define transition fingerprints/CR lifecycle through M5 and mandatory deletion of all controls,
fixtures, baselines, allowlists at M6.
T011 Assign one verifier per S1–S10, including Charter owner workflow, M2 topology collision closure,
M3/M4 backup/conflict/rollback, M5 referrers, and M6 numeric-byte zero tests.
T012 Define wave-local snapshots, prefix/suffix rollback, and exact evidence outputs; explicitly reject
runtime managed-path ledger/state architecture.

**Gate**: every transition has a risk, verifier, failure state, and rollback; no policy gap.

## WP04 — Stacked Mission Plan (P1)

**Goal**: create schema-complete M1–M6 program with exact ownership cardinality and executable inputs/
outputs/gates.
**Prompt**: `tasks/WP04-stacked-mission-plan.md`
**Requirements**: FR-009, FR-010, NFR-003

T013 Write all six entries from `contracts/stacked-plan-schema.md`; every wave `bulk_edit` with fresh audit.
T014 Assign every OC/hit exactly once across M1–M6; distinguish each CR's frozen-base source ownership
from later-created M6 product/control cleanup; prove disjoint union/cardinality and no current-repo
deferral. Load and discharge #2727 from canonical `issue-matrix.json` through atomic glossary parity.
T015 Dry-run M1 with zero questions and M2 map with every old-source/executable collision row frozen before
editing; record gates/rollback/evidence.

**Gate**: complete manifest membership equals wave-owner union; M6 has no exception mechanism.

## WP05 — Verification and Closeout (P0)

**Goal**: independently verify SC-001..SC-004; report defects to owning WP.
**Prompt**: `tasks/WP05-verification-closeout.md`

T016 Verify frozen ancestry, planning-only scope, ADR registration/self-sufficiency/override.
T017 Rerun frozen audits; regenerate the TSV and match the recorded SHA-256/counts; verify
raw-return-code handling, git-failure mutations, manifest set equality, the fixed `kitty-specs/`
exclusion, and no X/exempt rows.
T018 Verify ordering/I-levels, complete Charter/glossary parity graph, all-code M2, safe/no-old-path M3/M4,
all-history-outside-`kitty-specs/` M5 with archive immutability, and exact-zero M6 bound/rerun on final
commit/tree through the mandatory audit entrypoint and required external check marker.
T019 Verify owner/CR arithmetic, M1 zero-decision, M2 bounded pre-edit map, dependencies/gates/rollback.
T020 Run workflow/static checks and record commands/hashes/answers/timestamps/pass-fail.

**Gate**: all evidence present and consistent; any user-visible-only/internal/history exception beyond the
fixed `kitty-specs/` root, any edit/rename under that root, managed-ledger overdesign, ownerless hit,
old-path-complete state, or otherwise narrowed terminal audit fails.
