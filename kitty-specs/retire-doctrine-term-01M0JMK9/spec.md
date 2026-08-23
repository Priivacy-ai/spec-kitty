# Mission Specification: Retire the Doctrine Term

**Mission Branch**: `feat/retire-doctrine-term`
**Created**: 2026-08-21
**Status**: Implemented (planning complete; program pending M1–M6)
**Mission type**: research and planning only

## Authoritative operator override

The operator's 2026-08-22 terminal decision (`DM-01M0NDJ33GCKATG3H4BK4PAMNG`) supersedes the earlier
discovery scope decision and every conflicting planning statement, as amended by
`DM-01M0NMS9WPH33EPFCJQRTQVNSA` (the `kitty-specs/` historical archive is immutable) and
`DM-01M0NMSD60JYG7K7V5MJCKJ3P8` (`inventory-hits.tsv` is ephemeral evidence). This mission plans complete
extinction of the case-insensitive token `doctrine` from the repository's current tree outside the single
fixed, enumerated exclusion root `kitty-specs/`. At M6/I6:

- forced-text content audit over `HEAD` with the fixed pathspec `:(exclude)kitty-specs/` returns zero
  occurrences;
- NUL-safe tracked-path audit over `HEAD`, after dropping paths under `kitty-specs/`, returns zero
  matching pathnames;
- no X1/X2/X3, internal, historical, fixture, control, metadata, generated, test, or current-tree ADR
  exception remains anywhere outside that root;
- the two fixed exclusions are Git object history outside `HEAD` and the immutable `kitty-specs/`
  historical-archive root. The root is an operator-fixed audit boundary, not an occurrence class,
  allowlist, baseline, or X-classification; no wave renames a mission slug or directory or edits/renames
  any file under it, and any narrowing beyond that one root fails closed.

The program may retain registered warning aliases during 3.x, but completed 4.0 cannot contain the token
anywhere in audited current `HEAD` or in a completed migrated installation/project. Post-M6 negative tests build
the forbidden byte sequence from numeric code points and never store it literally.

## User scenarios and acceptance

### US1 — Canonical ADR and Charter authority (P1)

The operator needs one accepted ADR and the project Charter itself to authorize and define the extinction
program.

1. The ADR follows `docs/architecture/adr-template.md`, is registered by
   `python -m scripts.docs.freshen_adr_inventory`, records the operator override, and makes it effective
   at M1/I1.
2. The ADR defines Charter Pack, Charter Bundle, Active Charter, Inactive Charter, and surviving kind vocabulary.
3. The ADR states the narrow override: for this program only, current-tree terminology extinction
   supersedes User Customization Preservation where an old-named path must disappear and supersedes
   historical-current-tree immutability outside `kitty-specs/`. It never authorizes data loss: content is
   preserved at a canonical destination and conflicts block migration until resolved. Git object history
   and the `kitty-specs/` archive remain untouched.
4. M1 executes the closed owner map in `contracts/adr-content-contract.md`: curate `charter.md` and only
   the human-owned `charter.yaml` governance/directives/overrides partitions directly; route every flat
   `activated_*`/`activated_kinds`/`mission_type_activations` change through `charter activate` or
   `charter deactivate` and the shared activation engine; migrate existing `interview/answers.yaml` with
   the contract's backup-backed coordinate-exact helper and harden serializer round trips before allowing
   `charter interview` ownership;
   use `charter generate` only for `charter.yaml` catalog/metadata after source updates; use `charter
   context` only for a necessary `context-state.json` refresh; use `charter synthesize`/`resynthesize`
   only for a necessary `synthesis-manifest.yaml` refresh; and, after repeating its zero-consumer proof,
   delete the obsolete writerless `.kittify/charter/graph.yml`. Every no-hit artifact records a verified
   no-op. `charter sync` is not treated as a writer.
5. M1 updates all glossary authorities and active referrers atomically, then arms the transition guard.

**Independent test**: a reviewer can derive the full M1 authority update and the terminal zero-current-tree
rule from the ADR alone, with no operator decision left open.

### US2 — Exhaustive all-tree inventory (P1)

Every case-insensitive content occurrence and tracked pathname at the frozen base outside `kitty-specs/`
is a work item.

1. WP02 runs the forced-text all-blob and NUL-safe pathname audits from `contracts/inventory-schema.md`,
   both applying the fixed `kitty-specs/` exclusion.
2. `inventory-hits.tsv` contains one deterministic row per content coordinate and one per matching path.
   It is ephemeral evidence: generated, hash-pinned in committed `inventory.md`, reproducible from the
   frozen base, and not committed.
3. Every row receives one occurrence class and later exactly one M1–M6 owner. There are no classified-out
   rows, allowlists, sampling, baselines-as-exemptions, or ownerless deferrals.
4. Scope includes non-public code, `src/doctrine/`, internal symbols/imports/files, tests, fixtures,
   build hooks, public metadata, Charter sources, generated assets, installed assets, ADRs, docs archives,
   event/history prose, and filenames/referrers. `kitty-specs/` content and pathnames are recorded only
   as non-contractual orientation counts.

**Independent test**: regenerated manifest rows are set-equal to both audit outputs (matching the recorded
SHA-256 and counts) and the stacked plan assigns every row exactly once.

### US3 — Deterministic ordering and transition method (P2)

The program executes M1→M6 without split authority or a false terminal pass.

1. M1 changes Charter/glossary authority and records the explicit exception.
2. M2 freezes an exhaustive internal+public topology map, then merges/relocates `src/doctrine/` into a
   collision-free `src/charter/` topology and renames all code/files/symbols/imports/tests/build hooks.
   It cannot close while any live executable/code hit or pathname remains.
3. M3 moves `.kittify/doctrine/` to `.kittify/charter-packs/`. Migration copies/moves all data to the
   canonical destination, verifies it, and removes the old root; collisions hard-fail before destructive
   action and block upgrade until the operator resolves them. A completed migration never retains the old
   root.
4. M4 renames every source, generated, installed, shared, and override skill/profile/directive/prompt/
   agent asset. Old aliases warn only through 3.x; a completed migration has no old-named installed path.
5. M5 rewrites/renames every remaining current-tree prose/history surface outside `kitty-specs/`,
   including ADRs, docs archives, evidence, filenames, and all referrers; a referrer that cites an
   immutable archive path containing the token is rewritten to cite the mission by `mission_id`/mid8 or a
   token-free path. Git object history and `kitty-specs/` are untouched.
6. M6 removes every compatibility alias/key/path/control/fixture and proves both exact zero audits.

**Independent test**: each level I1–I6 has a named verifier and failure/rollback rule; I6 is equivalent to
the two zero audit results, not a curated exception set.

### US4 — Executable stacked mission plan (P2)

1. Each M1–M6 entry names inputs, outputs, dependencies, exact owned occurrence classes/hits, tests,
   merge gate, rollback, and invariant.
2. Every hit is assigned exactly once across M1–M6. Compatibility reservations have one introduction
   owner and M6 removal owner without duplicating primary ownership.
3. M1 requires zero new operator decisions. M2's sole bounded design gate is the exhaustive
   internal+public topology map; every collision is resolved and frozen before its first edit.
4. M6 has no exception/allowlist/baseline/deferral escape hatch.

## Edge cases and fixed resolutions

- **Existing `src/charter/` package**: M2 maps every old module/symbol/path to a collision-free destination,
  records merge vs relocation for each collision, updates every importer/build/test consumer, and freezes
  the map before editing. It may not leave `src/doctrine/` as an internal implementation refuge.
- **Current-tree history**: M5 rewrites historical prose/files outside `kitty-specs/` in the checked-out
  tree under the explicit override. Prior bytes remain available only from Git object history.
- **Historical missions**: `kitty-specs/` is an immutable archive. No slug, directory, or file under it is
  renamed or edited by any wave; both audits exclude it by the one fixed pathspec.
- **Charter ownership**: M1 edits human-owned content directly and invokes owning generators for generated
  surfaces; it verifies the complete Charter dependency graph and regenerated hashes.
- **User project data**: M3/M4 preserve content, not the retired pathname. Absent destination → verified
  move/copy; identical destination → verify then remove source; divergent destination → hard fail with
  both sides intact until manual resolution. No completed upgrade may keep an old-named path.
- **Compatibility tests**: 3.x aliases have behavioral/warning tests. M6 deletes alias/control fixtures and
  replaces negative tests with numeric-byte construction so the literal token is absent.
- **External consumers**: coordination may name owners/milestones, but no current-repository hit may be
  deferred. External work cannot weaken the current-tree M6 gate.

## Functional requirements

| ID | Requirement |
|---|---|
| FR-001 | Accepted ADR records the terminology decision, operator override, I1 effectiveness, and exact I6 audits. |
| FR-002 | ADR defines Charter Pack, Charter Bundle, Active Charter, Inactive Charter, and surviving kind labels. |
| FR-003 | M1 atomically updates docs context, `.kittify/glossaries/spec_kitty_core.yaml`, the built-in glossary pack, active referrers, and the complete Charter authority graph through owning workflows. |
| FR-004 | Every current-tree content/path hit outside the fixed `kitty-specs/` exclusion root is in scope, including non-public/internal/history/test/generated/metadata surfaces. |
| FR-005 | 3.x warning aliases are temporary; completed 4.0 and completed migrations contain zero token occurrences/pathnames. |
| FR-006 | Inventory manifest is set-equal to the forced-text content and NUL-safe tracked-path audits (both excluding `kitty-specs/`), proven by deterministic regeneration against the recorded hash. |
| FR-007 | Every manifest hit has exactly one M1–M6 primary owner; no X classification or terminal exemption exists. |
| FR-008 | Methodology defines M1→M6 ordering, I0→I6, transition guards, rollback, and exact zero gate. |
| FR-009 | Stacked plan names deterministic inputs/outputs/dependencies/ownership/tests/gates/rollback for M1–M6. |
| FR-010 | M1 is spec-ready with zero new operator decisions; M2 has only the bounded topology-map gate. |
| FR-011 | Fixed vocabulary, serialized seams, skill/profile/directive mappings, root destination, and zero-audit method are recorded. |

## Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-001 | Frozen-base inventory is reproducible, byte-safe, per-hit, and set-equal to checked audit outputs; terminal evidence binds one final commit/tree and is rerun after any tree change. |
| NFR-002 | ADR is self-sufficient: authority, override, complete scope, migration safety, compatibility window, and zero gate require no chat context. |
| NFR-003 | 100% of hits have one owner; 100% of missions have complete contracts; zero unresolved cross-wave inputs at closeout. |

## Constraints

| ID | Constraint |
|---|---|
| C-001 | This mission changes planning/docs artifacts only. Product renames happen in downstream M1–M6 missions. |
| C-002 | ADR registration uses the canonical template/freshen workflow; no hand-maintained index drift. |
| C-003 | Terminology-extinction override: current-tree ADR/docs/archive/history bytes and filenames outside `kitty-specs/` are mutable retirement work; the two fixed exclusions are Git object history outside `HEAD` and the immutable `kitty-specs/` root (DM-01M0NMS9WPH33EPFCJQRTQVNSA). |
| C-004 | Transition fingerprints/reservations may exist through M5, but M6 deletes every compatibility control/product record and switches the guard to exact zero mode. No baseline/allowlist survives I6. |
| C-005 | Non-public executable topology is in scope. M2 removes/merges the old source package and every internal symbol/file/import/test/build-hook hit. |

## Exact terminal audit contract

The M6 gate constructs the token without storing it in post-M6 source:

The terminal gate runs the checked no-pipeline Python subprocess procedures in
`contracts/inventory-schema.md` with `--commit <final-commit-oid>` and `mode=terminal`, **at the repository
toplevel only** (`git rev-parse --show-prefix` must be empty; the pathspec is `:(top)`-anchored and
`ls-tree` uses `--full-tree`, so a subdirectory run can never report zero), both applying the fixed
`kitty-specs/` exclusion. Content succeeds only for raw `git grep` rc 1 plus empty stdout; pathname
succeeds only for raw `git ls-tree` rc 0 plus zero matching NUL records after the archive-root drop;
symlink targets (`120000` entries) are read and audited; a normalised (NFKC, format/zero-width characters
stripped) content pass must also be zero. Git errors and return-code/output inconsistencies fail closed.

M6 plans/creates token-literal-free `scripts/audit_retired_term_zero.py`; CI/release invokes its
contract-defined terminal command and requires check marker `terminology-zero-current-tree`. Its external
stdout attestation binds the resolved final **commit** OID and tree OID without modifying the audited tree.

The raw content git process must return rc 1 with empty stdout and the raw pathname git process rc 0 with
zero matches, after which the wrapper exits **0**; exit **1** means hits remain; exit **2** means audit,
input, or git error (including a non-toplevel cwd). Any hit, audit error, unreadable blob/path, allowlist,
omitted archive exclusion, or any other narrowed root blocks I6. Evidence records the resolved commit
and tree; any tree change invalidates it, and CI/release reruns on the final merge/publish tree; no earlier
working-tree or parent-commit zero result authorizes merge or publication. Charter files are ordinary
audited `HEAD` content. The same byte construction is used in post-M6 negative tests.

## Success criteria

- **SC-001**: independent reviewer confirms ADR self-sufficiency and explicit operator override.
- **SC-002**: regenerated inventory is set-equal to frozen content/path audits and matches the recorded
  hash; no unclassified or excluded rows outside the fixed `kitty-specs/` root.
- **SC-003**: stacked plan assigns every hit exactly once to M1–M6 and every compatibility reservation to
  one introduction plus M6 removal.
- **SC-004**: M1 dry run needs zero decisions; M2 topology gate is bounded and pre-edit; I6 requires both
  exact final commit/tree audits at zero and no surviving exception machinery.

## Assumptions

- Git history outside `HEAD` remains accessible; it and the immutable `kitty-specs/` root are the two
  fixed exclusions.
- 3.x is the only compatibility window; M6/4.0 is a coordinated breaking cutover.
- Operators resolve divergent project/install destination collisions before upgrade completion.
- Each downstream wave captures a fresh target snapshot and performs its own complete occurrence audit.
