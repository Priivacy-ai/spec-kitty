# Implementation Plan: Research and Plan Complete Terminology Extinction

**Mission**: `retire-doctrine-term-01M0JMK9`
**Branch**: `feat/retire-doctrine-term`
**Scope**: planning/docs artifacts only; no downstream product rename

## Summary

Produce five sequential deliverables: accepted ADR, exhaustive all-tree occurrence inventory, ordering/
methodology, executable M1–M6 stacked plan, and independent verification. The operator's 2026-08-22
override replaces earlier internal/history exemptions: completed M6 must have zero case-insensitive
content occurrences and zero tracked pathname occurrences across current `HEAD` outside the single fixed
exclusion root `kitty-specs/`. The two fixed exclusions are Git object history outside `HEAD` and the
immutable `kitty-specs/` historical-archive root (`DM-01M0NMS9WPH33EPFCJQRTQVNSA`); `inventory-hits.tsv`
is ephemeral, hash-pinned evidence (`DM-01M0NMSD60JYG7K7V5MJCKJ3P8`).

## Technical context

- Python 3.11+, Git required, Linux/macOS/Windows supported.
- Inventory uses forced-text `git grep -a` plus NUL-safe `git ls-tree -z` at a frozen target through
  checked Python subprocesses, never a shell pipeline; raw git errors fail before zero interpretation.
- ADR registration uses `python -m scripts.docs.freshen_adr_inventory`.
- Planning mission outputs Markdown/TSV/JSON evidence only; the TSV manifest is generated, hash-pinned in
  `inventory.md`, and untracked (mission-local `.gitignore`).
- Downstream work is six strict `bulk_edit` missions with wave-local audit maps.
- No runtime managed-path ledger/state architecture is planned.

## Charter check and explicit override

The current Charter ordinarily protects user customization and historical/current-tree evidence. The user
has explicitly overridden those rules for this program's terminology extinction. WP01's ADR must record
the narrow exception; M1 must add it to the Charter through correct owning workflows before other product
waves. It preserves data at canonical locations and blocks divergent conflicts, but completed migration
cannot preserve the retired pathname. Current-tree ADR/docs/archive/history files outside `kitty-specs/`
are M5 work; Git object history and the immutable `kitty-specs/` archive remain unchanged — no mission
slug, directory, or file under it is renamed or edited.

Planning continues to follow single authority, ATDD-first evidence, cross-platform behavior, exact
ownership, and smallest coherent diffs.

## Planning artifact graph

| Package | Deliverable | Depends on | Exit |
|---|---|---|---|
| WP01 / IC-01 | Accepted ADR + registration + `implementation-baseline.json` | none | self-sufficient override/authority/zero contract |
| WP02 / IC-02 | `inventory-hits.tsv` (ephemeral, hash-pinned), `inventory.md` | WP01 | set-equal all-blob/path inventory outside `kitty-specs/`; no X/exempt rows |
| WP03 / IC-03 | `methodology.md` | WP02 | exact M1→M6 sequence, I0→I6, guards/migrations/rollback |
| WP04 / IC-04 | `stacked-plan.md` | WP03 | every hit assigned once; M1 zero-decision; M2 bounded map |
| WP05 / IC-05 | `verification-report.md` | WP01–WP04 | independent evidence for SC-001..SC-004 |

Single stream. Each artifact consumes the previous authority/evidence; no safe parallel authoring lane
exists.

## IC-01 — ADR authoring and registration

**Inputs**: `spec.md`, `research.md`, ADR template, Charter dependency graph, all contracts.
**Outputs**: new Accepted ADR, prior ADR status/pointer, freshened index/lockfile, frozen baseline.
**Required content**:

- full-current-tree scope outside the fixed `kitty-specs/` exclusion root and exact I6 audit;
- explicit operator override/effectiveness at M1/I1;
- complete M1 Charter/glossary owner workflow: direct governance/directives/overrides, activation only
  through activate/deactivate + shared engine, lossless answers migration/serializer hardening,
  generate-only catalog/metadata, context cache,
  synthesis manifest, zero-consumer deletion of obsolete `graph.yml`,
  and atomic parity across docs context, project glossary YAML, built-in glossary pack, and referrers;
- M2 all-internal/public source topology convergence;
- M3/M4 data-preserving but old-path-eliminating migrations;
- M5 current-tree history rewrite outside `kitty-specs/` (archive referrers recited by `mission_id`/mid8
  or token-free path); M6 compatibility/control/fixture extinction;
- 3.x warning-only compatibility and numeric-byte post-M6 negative tests.

**Risk/gate**: old ADR resolution mechanics remain semantically valid, but its body/title/path and all other
current-tree history outside `kitty-specs/` are explicitly M5 work. No wording may imply permanent
immutability of those surfaces; only the `kitty-specs/` archive is immutable.

## IC-02 — Exhaustive inventory

**Inputs**: accepted ADR, frozen `target_tip`, inventory/data-model contracts.
**Outputs**: one-row-per-hit TSV (ephemeral, untracked, SHA-256 + counts pinned in `inventory.md`) and
derived `inventory.md`.
**Method**:

1. load frozen target; no refetch/repoint;
2. run forced-text case-insensitive all-blob audit with the fixed `:(exclude)kitty-specs/` pathspec
   through the contract's checked subprocess and preserve the distinction between valid grep rc 1 and
   audit rc >1;
3. run NUL-safe tracked-path audit through the checked subprocess, dropping `kitty-specs/` paths after
   the rc check; any `ls-tree` failure blocks; record excluded-root counts as orientation;
4. classify every row S1–S10 + OC; no X/exempt value;
5. split classes wherever downstream ownership differs;
6. plan disjoint CR candidates for temporary 3.x compatibility;
7. prove manifest set equality and deterministic hashes; record the TSV SHA-256, row count, and exact
   reproduction command in `inventory.md`.

Internal code, old source topology, tests/build hooks, metadata, generated assets, ADRs/docs history,
fixtures/controls, and matching filenames outside `kitty-specs/` are mandatory rows. Current-repository
deferral is invalid.

## IC-03 — Ordering and methodology

**Inputs**: ADR + exact inventory.
**Output**: `methodology.md`.
**Fixed sequence**:

1. M1 establishes Charter/glossary authority and the override through owner workflows, then guard.
2. M2 freezes and applies exhaustive internal+public topology, including collision resolution with existing
   `src/charter/`.
3. M3 moves project overlay data to `.kittify/charter-packs/`; verified completion removes old root.
4. M4 moves all agent assets/IDs/installed paths; verified completion removes old paths.
5. M5 rewrites/renames every remaining current-tree prose/history artifact and referrer outside
   `kitty-specs/`.
6. M6 removes compatibility/control/fixture/baseline machinery and proves exact zero over `HEAD` outside
   the fixed `kitty-specs/` root.

Methodology names one verifier per S1–S10; transition fingerprints/CR tests; M2 topology-map set equality;
M3/M4 absent/identical/divergent/crash/rollback cases; M5 filename/referrer closure; M6 zero-audit and
numeric-byte negative tests.

## IC-04 — Stacked mission plan

**Inputs**: ADR, manifest/inventory, methodology, stack/operator-map contracts.
**Output**: `stacked-plan.md`.
**Cardinality**:

- OC/hit owner sets across M1–M6 are pairwise disjoint and union to the complete manifest;
- every CR frozen-base source OC has one M1–M4 introduction owner; later-created product/control
  coordinates are distinct M6-removal work, with no coordinate double-owned or source double-funded;
- M1 local questions = 0;
- M2 local questions = one bounded pre-edit topology-map approval, with every collision resolved;
- M3–M6 local policy questions = 0.

Each wave names fresh base capture, exact occurrence map, inputs/outputs/owned surfaces, tests, merge gate,
rollback, and I1–I6 invariant. No external deferral can own a current-repository row.

## IC-05 — Verification and closeout

WP05 verifies rather than repairs:

- baseline ancestry and planning-only committed+working-tree scope;
- ADR self-sufficiency and exact override;
- manifest set equality by regenerating the TSV from the frozen base and matching the recorded SHA-256
  and counts; absence of X/exemption classifications;
- exact owner union/cardinality and CR joins;
- M1 zero-decision dry run and M2 frozen-map pre-edit dry run;
- M3/M4 no-old-path completion semantics without runtime-ledger overdesign;
- M5 current-tree history ownership outside `kitty-specs/`, and archive immutability;
- M6 deletion of every exception/control/baseline and exact `HEAD` content/path zero gate with the one
  fixed `kitty-specs/` exclusion.

Failures route to owning WP. Independent review requires one named reviewer with evidence; missing evidence
fails.

## Downstream program contract

| Wave | Outputs | Merge gate | Rollback |
|---|---|---|---|
| M1 | ADR-effective Charter/glossary graph, override, selection migration, guard | all owner workflows regenerate consistently; M1 hit set gone | revert before M2; restore authority graph |
| M2 | topology maps, merged/relocated source tree, renamed code/tests/build/API/CLI/metadata | no live executable/code hit/path outside registered CR | dependency-slice revert; reverse suffix after M3+ |
| M3 | canonical pack/overlay root and verified migrated data | completed fixtures/projects have no old root; conflicts block | restore backup if verification fails |
| M4 | canonical source/generated/installed agent assets | completed installations have no old asset path | restore backup/aliases within 3.x |
| M5 | all remaining current-tree prose/history/files/referrers outside `kitty-specs/` canonical | M5-owned audit rows zero; no dangling renamed refs; `kitty-specs/` byte-identical | revert before M6; forward-fix after |
| M6 | no aliases/keys/paths/controls/fixtures/baselines; numeric-byte negative tests; fixed zero-audit entrypoint/check marker | checked content/path 0 externally bound to final commit/tree; CI/release rerun after tree change | prepublish Git/release rollback only |

## Risks and mitigations

- **False zero via exclusion** → exact commands/token construction and the single `kitty-specs/` exclusion
  root fixed in contract; any other narrowing, or omitting that root, fails.
- **Data loss during pathname extinction** → backup, verified canonical copy/move, divergent conflict hard
  failure, no completion marker with old path.
- **`src/charter/` collisions** → exhaustive map approval before first M2 edit; unresolved row blocks.
- **Charter regeneration drift** → map owner inputs/outputs, edit sources first, run documented generator,
  hash/behavior tests over every tracked Charter artifact plus present runtime cache, including mapped
  verified no-ops and obsolete-graph deletion.
- **Program artifacts break final gate** → mission artifacts live in the excluded `kitty-specs/` root; M5
  explicitly owns ADR/docs/evidence files and names outside it, including the program's own ADR filename.
- **Detector stores token** → M6 replaces fixtures/tests with numeric-byte construction and deletes old
  baseline/control data.

## Definition of planning complete

ADR contract, inventory contract, data model, methodology instructions, stack schema, tasks/prompts,
quickstart, checklist, and verification evidence state the same full-current-tree-outside-`kitty-specs/`
scope and exact I6 gate; no conflicting internal/history/X/managed-ledger exception remains beyond the
one fixed archive root.
