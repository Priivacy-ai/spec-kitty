---
title: 'ADR: Retire the doctrine term — Charter is the canonical vocabulary'
description: 'Retires the `doctrine` term for `charter` across the repo outside the immutable kitty-specs archive and in installations; M1 makes it effective, M2–M5 execute, M6 proves zero.'
status: Accepted
date: '2026-08-22'
---

# ADR: Retire the doctrine term — Charter is the canonical vocabulary

**Status:** Accepted

**Date:** 2026-08-22

**Deciders:** Operator (Robert Douglass); planning mission `retire-doctrine-term-01M0JMK9`
(mission_id `01M0JMK90CFFDKA4RCCTQK9675`)

**Technical Story:** decision ledger `DM-01M0NDJ33GCKATG3H4BK4PAMNG` (full current-tree extinction),
`DM-01M0NMS9WPH33EPFCJQRTQVNSA` (`kitty-specs/` archive is immutable),
`DM-01M0NMSD60JYG7K7V5MJCKJ3P8` (ephemeral inventory manifest); issue #2727 (glossary authority); the
planning contracts under `kitty-specs/retire-doctrine-term-01M0JMK9/contracts/`.

---

## Context and Problem Statement

Spec Kitty names its governance layer two ways. `charter` is the operator-facing word for the governed
state of a project; `doctrine` names the offer side (packs, the `src/doctrine/` package, `.kittify/doctrine/`,
`spk-doctrine-*` skills, the `doctrine` CLI group, tracker `doctrine_mode`, `governance.doctrine`). The split
is not a distinction users need, it leaks into CLI, config, skills, profiles, docs and code topology, and it
contradicts the single-canonical-authority principle. On the frozen target `origin/main`
(`2621a56d06b9ae4e7da07ee206879c30a4d8b363`, 2026-08-22) the forced-text audit reports 48,328 case-insensitive
content matches and 722 tracked pathnames outside `kitty-specs/`.

This ADR records the decision, the vocabulary, the operator override it requires, the complete scope and
wave ownership, and the exact terminal audit. It is the sole authority downstream waves derive their work
from; it must be readable without chat context.

## Decision Drivers

* Single canonical authority: one term for the governance layer and its state.
* Exactness over support labels: completion is proven by an audit, not by a list of exemptions.
* Data safety: no user customisation or project data is lost while retired pathnames disappear.
* Historical integrity: the `kitty-specs/` mission archive is never rewritten.
* Bounded compatibility: a 3.x warning window, a hard 4.0 boundary.

## Considered Options

* **A. Rename user-facing language only**, keep `src/doctrine/`, internal IDs and history as they are.
* **B. Complete current-tree extinction outside the immutable `kitty-specs/` archive**, data-safe, with
  3.x warning aliases and an exact zero audit at 4.0.
* **C. Hard break now**, no aliases, no migration.

## Decision Outcome

**Chosen option: B.** `charter` replaces `doctrine` throughout the repository outside the immutable
`kitty-specs/` historical archive and in completed installations/projects. Acceptance of this ADR records
intent; **M1/I1 makes it effective** by updating the Charter/glossary authority graph. During 3.x only
registered, hidden or warning aliases may remain; **M6/4.0 removes them and requires zero case-insensitive
content occurrences and zero matching tracked pathnames in current `HEAD` outside the single fixed exclusion
root `kitty-specs/`.**

The two fixed exclusions are: (1) Git object history outside `HEAD`; (2) the immutable `kitty-specs/`
historical-archive root (`DM-01M0NMS9WPH33EPFCJQRTQVNSA`) — no mission slug, directory, or file under it is
renamed or edited by any wave. The root is an operator-fixed audit boundary applied identically to the
inventory and terminal audits; it is not an occurrence class, allowlist, baseline, or X-classification, and
any other narrowing fails closed.

### Canonical vocabulary

* **Charter Bundle** — the per-project materialised governance file set under `.kittify/charter/`.
* **Charter Pack** — the offer-side versioned, distributable catalogue of governance artefacts from the
  built-in, organisation, or project-overlay layer; it is not the materialised Charter Bundle.
* **Active Charter** — a governance artefact activated/wired for a project.
* **Inactive Charter** — an artefact available from a Charter Pack but not activated.
* The existing kind labels (`directive`, `tactic`, `styleguide`, `toolguide`, `paradigm`, `procedure`,
  agent profile, glossary pack, mission step contract) retain their roles.

### Explicit operator override (effective at I1)

> For program `retire-doctrine-term-01M0JMK9`, complete current-tree terminology extinction supersedes
> User Customization Preservation only to the extent necessary to eliminate the retired pathname after
> preserving its content at the canonical destination, and supersedes historical-current-tree
> immutability for ADRs, docs archives, evidence, fixtures, and filenames outside `kitty-specs/`. Divergent
> destination content blocks before destructive action; the operator resolves it. Git object history and
> the `kitty-specs/` archive are unchanged.

This exception authorises no data loss, silent overwrite, audit narrowing beyond the fixed `kitty-specs/`
root, non-terminology cleanup, or any edit/rename under `kitty-specs/`.

### Complete scope and owners

| Surface | Canonical treatment | Owner |
|---|---|---|
| `.kittify/charter/` and all owning source/graph/interview/synthesis/generated authority | rewrite through documented human/generated owner workflows; record override | M1 |
| glossary authorities and referrers | canonical Charter vocabulary/path | M1 |
| `governance.doctrine` | `governance.charter`; 3.x reader warning | M1, remove M6 |
| every public/non-public `src/doctrine/` module/path/symbol/import/test/build hook | exhaustive collision-free merge/relocation into `src/charter/` topology | M2, aliases M6 |
| CLI/serialized/API/config/workflow/distribution metadata | exhaustive internal+public topology map | M2, aliases M6 |
| `.kittify/doctrine/` project overlay root | `.kittify/charter-packs/`; preserve data, conflict blocks, old root absent on completion | M3, old reader M6 |
| skills/profiles/directives/prompts/generated/installed/shared assets | canonical IDs and paths; completed migration leaves no old path | M4, aliases M6 |
| all remaining current-tree prose/history/ADR/docs/archive/evidence and filenames/referrers outside `kitty-specs/` | rewrite/rename in the checked-out tree; a referrer citing an archive path containing the token is recited by `mission_id`/mid8 or a token-free path, never by changing the archive | M5 |
| `kitty-specs/` historical archive (all missions, including `retire-doctrine-term-01M0JMK9`) | immutable: no slug/directory/file rename or edit; excluded from both audits by the one fixed pathspec | none (fixed exclusion root) |
| all compatibility aliases/keys/paths/controls/fixtures | delete; replace negative fixtures with numeric-byte construction | M6 |

No non-public, internal, historical, intentional-test, generated, metadata, or current-tree pathname
exemption exists outside the fixed `kitty-specs/` root.

### Fixed seams and identifier mappings

* Charter Pack offer root is `.kittify/charter-packs/`; the Charter Bundle remains `.kittify/charter/`.
* `doctrine.org.packs` → `charter_packs.org.packs`.
* tracker `doctrine` / `--doctrine-mode` / `doctrine_mode` → `ownership` / `--ownership-mode` /
  `ownership_mode`; `field_owners` remains.
* `doctrine:<kind>:<id>` → `charter:<kind>:<id>`.

| 3.x ID(s) | Canonical ID |
|---|---|
| `spk-doctrine-charter`, `spec-kitty-charter-doctrine` | `spk-charter-lifecycle` |
| `spk-doctrine-glossary` | `spk-charter-glossary` |
| `spk-doctrine-spdd-reasons` | `spk-charter-spdd-reasons` |
| `spk-doctrine-profile-load` | `spk-charter-profile-load` |
| `spk-doctrine-semantic-compression` | `spk-charter-semantic-compression` |
| `spk-doctrine-bulk-edit` | `spk-charter-bulk-edit` |
| `spk-doctrine-show-me` | `spk-charter-show-me` |

Profile `doctrine-daphne` maps exactly to `charter-daphne`; directive `018-doctrine-versioning-requirement`
maps exactly to `018-charter-versioning-requirement`. Wildcard or "corresponding" ID derivation is
forbidden. M2 freezes every additional internal/public topology, facade, distribution, wheel, import,
symbol, test, build, producer and consumer row before its first edit.

### M1 — Charter authority update (per-artifact owner map)

M1 freezes and executes this map; it may not substitute `charter generate` for another writer.

| Artifact/partition | Authoritative owner/action |
|---|---|
| `.kittify/charter/charter.md` | human/agent Charter conversation edits the existing file directly; `charter generate` never overwrites it |
| `.kittify/charter/charter.yaml` `governance`, `directives`, `overrides` | human/agent Charter conversation owns these authorable policy partitions through the `charter_yaml_io` round-trip section contract; never edit activation as policy prose |
| `.kittify/charter/charter.yaml` flat `activated_*`, `activated_kinds`, `mission_type_activations` | `charter.activation_engine` / `CharterPackManager` through `spec-kitty charter activate` or `spec-kitty charter deactivate`; interview promotion and absent-key seeding delegate to the same activation writer; derive the complete key set from `ACTIVATION_YAML_KEYS`; direct edits and `charter generate` are forbidden |
| `.kittify/charter/charter.yaml` `catalog`, `metadata` | update the owning pack/profile/directive sources, then run `spec-kitty charter generate`; verify every direct partition is byte-stable |
| `.kittify/charter/interview/answers.yaml` | the current `charter interview` serialisation is lossy (starts from defaults; drops extra/selected/template fields). M1 backs up exact bytes outside the audited tree, freezes every target coordinate/replacement, applies only those replacements to the original bytes through `scripts/migrate_charter_interview_answers.py`, parses before/after, and atomically replaces only after semantic-preservation checks; M1 also makes the normal serialiser round-trip the complete mapping; only then may `charter interview` resume ownership |
| `.kittify/charter/context-state.json` | runtime-local cache written only by `spec-kitty charter context` (`context_state.py`); not tracked authority. Audit when present; no hit → verified no-op; if a serialiser change requires refresh, rerun each registered action through `charter context --action <action> --mark-loaded`; never `charter generate` or a direct edit |
| `.kittify/charter/synthesis-manifest.yaml` | `spec-kitty charter synthesize` / `resynthesize` writes it manifest-last from synthesis inputs; no M1 hit in inputs or manifest → verified no-op; otherwise update inputs and run that owner, never hand-edit or `charter generate` |
| `.kittify/charter/graph.yml` | tracked legacy activation snapshot with no supported writer/consumer; before edits repeat the exact consumer audit; on the frozen target's zero-consumer result delete it and all referrers as an obsolete snapshot; a newly found consumer invalidates the dry run and must be added to the fixed map before execution |

`charter sync` is not a writer. `charter synthesize` owns `.kittify/doctrine/graph.yaml`; it does not own
`.kittify/charter/graph.yml`. M1 acceptance requires every tracked Charter authority/output and every present
runtime-local cache to have its mapped action or an explicit verified no-op; no ordinary authority hit may
remain outside registered 3.x compatibility owned for M6.

The answers migration preserves every unknown key, all answers, comments, ordering, quoting,
`selected_styleguides`, `selected_toolguides`, `selected_procedures`, `selected_tactics`, `template_set`, and
every selected asset byte-for-byte except the frozen target replacements; it writes temp + fsync + atomic
rename, retains the preimage backup/hash until M1 merge, and restores it on parse/parity/write failure.
Named tests: `test_answers_migration_preserves_unknown_keys_and_all_answers`,
`test_answers_migration_preserves_selected_assets_and_template_set`,
`test_answers_migration_changes_only_frozen_target_bytes`, `test_answers_migration_failure_restores_preimage`,
`test_interview_serializer_round_trips_extended_answers`; a deletion/default-reset/empty-`selected_tactics`
mutation must fail. Direct ad hoc YAML editing and the current lossy CLI are forbidden.

**Glossary transaction.** M1 atomically updates `docs/context/doctrine.md` → `docs/context/charter.md`,
`.kittify/glossaries/spec_kitty_core.yaml`, and `packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml`
together with all active referrers. The three authorities must encode the same Charter Pack / Charter
Bundle / active / inactive meanings; any parity or link audit failure rolls back all three. This ADR records
the obligation; the stacked plan (WP04) consumes the canonical mission `issue-matrix.json` row for #2727 and
binds it into the M1 contract; downstream M1 consumes that stack output and cannot split or defer one
authority to the issue. The parity predicate is fixed: term set, definitions and aliases keyed by term ID
must be equal across the three authorities and every referrer link must resolve. M1 also re-points the
referrers of `docs/context/doctrine.md` outside the archive (generated `docs/api/**` by re-running their
generators). M1 then arms the transition guard; its baseline store lives untracked or inside M1's own
`kitty-specs/` mission directory, never as a tracked token-bearing file elsewhere, and
`scripts/migrate_charter_interview_answers.py` builds its frozen replacements from numeric bytes, never a
stored literal. At M1's close, generated `charter.yaml` partitions whose producers are later waves (catalog
summaries emitted by `src/charter/compiler.py`, activation IDs renamed by M4) are carried forward in M1's
occurrence map, not rewritten by hand. **M1 requires zero new operator decisions.**

### M2–M6 — execution summary

* **M2 `charter-code-topology`** freezes one exhaustive internal+public topology map (every package,
  module, file, symbol, import, test, fixture, build hook, CLI route incl. nested subgroups and the
  `charter mission-type` collision, serialized/API/event/workflow/distribution/wheel/metadata producer and
  consumer); every collision with the existing `src/charter/` package is `merge-existing` or exact
  `relocate` before the first edit; it then converges the whole `src/doctrine/` tree into **one named
  offer-side sub-package inside `src/charter/`** (name fixed by the map approval) — the offer→activate→
  consume boundary of ADR 2026-07-15-1 is preserved, not dissolved: the one-way consumer→offer import rule
  and the live boundary gates are rewritten to the new package names, and facade and implementation are
  never merged into one module. M2 also relocates the skills tree (pathnames; skill IDs stay M4), renames
  every `.kittify/doctrine` code literal and introduces the dual-root reader (CR-07) ahead of M3's data
  move, retargets live architectural baselines (never deletes them), and disposes of the dormant
  `spec-kitty-doctrine` manifest by an explicit map row. Its sole bounded gate is that pre-edit map
  approval. It cannot close while any M2-owned (or earlier-wave-owned) live code/executable hit or matching
  pathname remains outside registered 3.x compatibility owned by M6; later-wave-owned rows are carried
  forward in its occurrence map.
* **M3 `charter-packs-source`** migrates `.kittify/doctrine/` to `.kittify/charter-packs/` (never into the
  Charter Bundle): preflight inventory and backup; absent destination → verified copy/move then remove old;
  identical destination → verify then remove old; divergent destination → hard-fail with both intact until the
  operator resolves; any interruption before verification → restore backup, do not mark complete. A completed
  migration never retains the old root. No runtime managed-path ledger/state architecture is introduced.
* **M4 `charter-agent-assets`** applies the same bounded preflight/backup/verify/conflict rule to every
  source, generated, installed, shared, override, profile, directive, prompt, skill and agent artefact with
  the fixed ID mappings above; completed installations have no old-named path; 3.x aliases warn only.
* **M5 `charter-current-tree-prose`** rewrites/renames every remaining current-tree prose/history
  occurrence, filename and referrer outside `kitty-specs/` — ADR bodies/titles/files (this ADR and the prior
  ADR included), docs archives, evidence, comments, READMEs — under the override. Prior bytes remain only in
  Git object history; the `kitty-specs/` archive is byte-identical across all waves.
* **M6 `charter-compatibility-extinction`** removes every compatibility alias/key/path/route/import,
  old-root reader, migrator, redirect, warning, distribution alias, test fixture, transition baseline,
  allowlist and guard record, replaces negative fixtures with numeric-byte construction, and proves the exact
  terminal audit below. M6 has no exception, allowlist, baseline, or deferral escape hatch.

Sequence is strict M1→M2→M3→M4→M5→M6; every wave is `bulk_edit` with a fresh wave-local base and exact
occurrence map; every frozen-base hit has exactly one M1–M6 primary owner; compatibility reservations have
one M1–M4 introduction owner and M6 removal; later-created product/control coordinates are distinct M6 work.
Rollback: revert the current wave before dependents land; afterwards reverse the landed suffix or
forward-fix; M3/M4 restore verified backups; after 4.0 publication rollback is release-level.

### Guard and exact terminal audit

M1 may arm shrink-only ordinary fingerprints and bounded compatibility reservations for M1–M5 transition
safety. M6 deletes every reservation control/product/tombstone and the transition baseline/allowlist
machinery, constructs the token as `bytes((100,111,99,116,114,105,110,101))`, and runs, as checked Python
subprocesses (no shell pipeline):

* precondition: the audit runs at the repository toplevel only — `git rev-parse --show-prefix` must be
  empty, otherwise audit error (a subdirectory run can never report zero); the resolved toplevel,
  `git --version` and the resolved commit OID (`git rev-parse --verify <ref>^{commit}`) are recorded;
* content: `git grep -a -i -n -o --column --full-name -z -e <token> <commit> -- ':(top)' ':(top,exclude)kitty-specs/'`
  — raw rc 1 with empty stdout means zero; rc 0 means hits; rc >1 or any rc/stdout inconsistency is an
  audit error; records are parsed structurally so pathnames containing LF are handled;
* pathname: `git ls-tree -r -z --full-tree --name-only <commit>` — any nonzero rc or missing NUL framing is
  an audit error; after the rc check, paths under `kitty-specs/` are dropped and the remainder is matched
  case-insensitively on raw bytes; zero matches required;
* symlink targets: every `120000` entry's blob is read and audited — zero required;
* normalised content: a second pass over text blobs after NFKC normalisation and stripping `Cf`/soft-hyphen/
  zero-width characters — zero required.

The mandatory tracked, token-literal-free entrypoint is `scripts/audit_retired_term_zero.py`; command
identity is `python scripts/audit_retired_term_zero.py --commit <final-commit-oid> --mode terminal --json -`;
the required CI/release check marker is `terminology-zero-current-tree`. Exit `0` = both audits zero,
`1` = hits, `2` = audit/input/git error. Its JSON goes only to stdout and external CI/release attestation
storage and contains object format, the resolved toplevel, `git --version`, exact lowercase commit/tree OIDs,
argv/raw return codes, stdout/stderr hashes, counts and result; it never writes into the audited tree. Any
subsequent tree change invalidates the attestation; CI and release merge/publish gates rerun the entrypoint
on the final result tree; no earlier working-tree or parent-commit zero result authorizes merge or
publication. Negative tests construct the same numeric byte sequence and never store the token
(named: `test_content_audit_accepts_rc1_empty_only`, `test_content_audit_rejects_git_rc_gt1`,
`test_path_audit_propagates_ls_tree_failure`, `test_symlink_target_audited`,
`test_no_homoglyph_or_format_char_evasion`, `mutation_git_audit_failure_cannot_pass_zero`,
`mutation_subdir_cwd_cannot_pass_zero`). Any hit, exception, deferral, missing Charter file, omitted archive
exclusion, any other narrowed root, non-toplevel cwd, or audit error blocks 4.0.

The per-hit inventory manifest (`inventory-hits.tsv`) is ephemeral evidence: regenerated deterministically
from the frozen base and hash-pinned in the committed `inventory.md` (`DM-01M0NMSD60JYG7K7V5MJCKJ3P8`).

### Consequences

#### Positive

* One canonical term and one authority graph for governance; operators never meet `doctrine` again.
* Completion is an exact, reproducible audit bound to a commit/tree, not a curated exemption list.
* User data and the mission archive are preserved by construction.

#### Negative

* A multi-wave program (M1–M6) touching code topology, project roots, installed assets and docs; 4.0 is a
  coordinated breaking cutover for the 3.x aliases.
* Divergent destinations during M3/M4 block upgrade until the operator resolves them.

#### Neutral

* Git object history and the `kitty-specs/` archive keep the old bytes; the program is not a history rewrite.

### Confirmation

I1: this ADR and the full Charter/glossary authority graph record the decision and override; M1 hits gone;
guard armed. I2–I5: per-wave zero over each wave's owned occurrence set. I6: `terminology-zero-current-tree`
reports content = 0 and pathnames = 0 for the final commit/tree with the one fixed exclusion.

## Pros and Cons of the Options

### A. User-facing rename only

Pros: small diff. Cons: leaves `src/doctrine/`, IDs, config keys and docs as a second authority; the term
keeps re-entering user surfaces; violates single canonical authority. Rejected.

### B. Complete extinction outside the immutable archive (chosen)

Pros: one authority, exact audit, data-safe, history preserved. Cons: multi-wave program, 4.0 breaking
boundary for aliases.

### C. Hard break now

Pros: fastest end state. Cons: breaks installed projects and external consumers with no migration; rejected.

## More Information

* Supersedes the terminology portion of
  [ADR 2026-07-15-1](2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md); its resolution
  mechanics (offer → activate → consume) survive: the offer side becomes one named sub-package inside
  `src/charter/` with the same one-way import rule and boundary gates (renamed), not a merged module set.
* Planning contracts: `kitty-specs/retire-doctrine-term-01M0JMK9/contracts/` (ADR content, inventory
  schema, operator-surface map, stacked plan); data model and methodology in the same mission directory.
* Anti-goals: no product rename in the planning mission; no runtime managed-path ledger/state architecture;
  no silent data overwrite or old-root survival after completed migration; no X1/X2/X3 terminal class,
  allowlist, or carve-out other than the fixed `kitty-specs/` root; no unresolved topology collision when M2
  begins editing.
