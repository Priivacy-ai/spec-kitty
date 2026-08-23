# Contract: Terminology-Extinction ADR Content

**Produces**: one Accepted ADR under `docs/adr/3.x/`
**Requirements**: FR-001..FR-005, FR-011, NFR-002, C-001..C-005

The ADR is self-sufficient only if it contains all items below.

## 1. Decision and effectiveness

- `charter` replaces `doctrine` throughout the repository outside the immutable `kitty-specs/` historical
  archive, and in completed installations/projects.
- ADR acceptance records intent; M1/I1 makes it effective by updating the Charter/glossary authority graph.
- 3.x permits only registered hidden/warning aliases. M6/4.0 removes them and requires zero current-tree
  content/pathname hits outside the single fixed exclusion root `kitty-specs/`.
- The two fixed exclusions are Git object history outside `HEAD` and the immutable `kitty-specs/`
  historical-archive root (`DM-01M0NMS9WPH33EPFCJQRTQVNSA`): no mission slug, directory, or file under it is
  renamed or edited by any wave. The root is an audit boundary, not a class, allowlist, or baseline.

## 2. Canonical vocabulary

- **Charter Bundle**: per-project materialized governance file set under `.kittify/charter/`.
- **Charter Pack**: offer-side versioned distributable catalogue of governance artifacts from the built-in,
  organization, or project-overlay layer; it is not the materialized Charter Bundle.
- **Active Charter**: governance artefact activated/wired for a project.
- **Inactive Charter**: artefact available from a Charter Pack but not activated.
- Existing kind labels (`directive`, `tactic`, `styleguide`, `toolguide`, `paradigm`, `procedure`, agent
  profile, glossary pack, mission step contract) retain their roles.

## 3. Explicit operator override

The ADR records this narrow exception, effective at I1:

> For program `retire-doctrine-term-01M0JMK9`, complete current-tree terminology extinction supersedes
> User Customization Preservation only to the extent necessary to eliminate the retired pathname after
> preserving its content at the canonical destination, and supersedes historical-current-tree
> immutability for ADRs, docs archives, evidence, fixtures, and filenames outside `kitty-specs/`. Divergent
> destination content blocks before destructive action; the operator resolves it. Git object history and
> the `kitty-specs/` archive are unchanged.

This exception authorizes no data loss, silent overwrite, audit narrowing beyond the fixed `kitty-specs/`
root, non-terminology cleanup, or any edit/rename under `kitty-specs/`.

## 4. Complete scope and owners

| Surface | Canonical treatment | Owner |
|---|---|---|
| `.kittify/charter/` and all owning source/graph/interview/synthesis/generated authority | rewrite through documented human/generated owner workflows; record override | M1 |
| glossary authorities and referrers | canonical Charter vocabulary/path | M1 |
| `governance.doctrine` | `governance.charter`; 3.x reader warning | M1, remove M6 |
| every public/non-public `src/doctrine/` module/path/symbol/import/test/build hook | exhaustive collision-free convergence into **one named offer-side sub-package inside `src/charter/`** (name fixed by M2's map gate), preserving the one-way consumer→offer import rule and the live boundary gates rewritten to the new names; facade and implementation never merged into one module; skills tree relocated (pathnames) by M2, skill IDs by M4; `.kittify/doctrine` code literals + dual-root reader (CR-07) by M2 | M2, aliases M6 |
| CLI/serialized/API/config/workflow/distribution metadata | exhaustive internal+public topology map | M2, aliases M6 |
| `.kittify/doctrine/` project overlay root | `.kittify/charter-packs/`; preserve data, conflict blocks, old root absent on completion | M3, old reader M6 |
| skills/profiles/directives/prompts/generated/installed/shared assets | canonical IDs and paths; completed migration leaves no old path | M4, aliases M6 |
| all remaining current-tree prose/history/ADR/docs/archive/evidence and filenames/referrers outside `kitty-specs/` | rewrite/rename in checked-out tree; a referrer citing an archive path containing the token is recited by `mission_id`/mid8 or a token-free path, never by changing the archive | M5 |
| `kitty-specs/` historical archive (all missions, including this one) | immutable: no slug/directory/file rename or edit; excluded from both audits by the one fixed pathspec | none (fixed exclusion root) |
| all compatibility aliases/keys/paths/controls/fixtures | delete, replace negative fixtures with numeric-byte construction | M6 |

No non-public, internal, historical, intentional-test, generated, metadata, or current-tree pathname
exemption exists outside the fixed `kitty-specs/` root.

## 5. Fixed seams

- Charter Pack offer root is `.kittify/charter-packs/`; Charter Bundle remains `.kittify/charter/`.
- `doctrine.org.packs` → `charter_packs.org.packs`.
- tracker `doctrine` / `--doctrine-mode` / `doctrine_mode` → `ownership` /
  `--ownership-mode` / `ownership_mode`; `field_owners` remains.
- `doctrine:<kind>:<id>` → `charter:<kind>:<id>`.
| 3.x ID(s) | Canonical ID |
|---|---|
| `spk-doctrine-charter`, `spec-kitty-charter-doctrine` | `spk-charter-lifecycle` |
| `spk-doctrine-glossary` | `spk-charter-glossary` |
| `spk-doctrine-spdd-reasons` | `spk-charter-spdd-reasons` |
| `spk-doctrine-profile-load` | `spk-charter-profile-load` |
| `spk-doctrine-semantic-compression` | `spk-charter-semantic-compression` |
| `spk-doctrine-bulk-edit` | `spk-charter-bulk-edit` |
| `spk-doctrine-show-me` | `spk-charter-show-me` |

Profile `doctrine-daphne` maps exactly to `charter-daphne`; directive
`018-doctrine-versioning-requirement` maps exactly to `018-charter-versioning-requirement`. Wildcard or
“corresponding” ID derivation is forbidden.
- M2 freezes all additional internal/public topology, facade, distribution, wheel, import, symbol, test,
  build, producer, and consumer rows before its first edit.

## 6. Charter authority update

M1 freezes and executes this per-artifact owner map; it may not substitute `charter generate` for another
writer:

| Artifact/partition | Authoritative owner/action |
|---|---|
| `.kittify/charter/charter.md` | human/agent Charter conversation edits the existing file directly; `charter generate` never overwrites it |
| `.kittify/charter/charter.yaml` `governance`, `directives`, and `overrides` | human/agent Charter conversation owns these authorable policy partitions, using the `charter_yaml_io` round-trip section contract; never edit activation as policy prose |
| `.kittify/charter/charter.yaml` flat `activated_*`, `activated_kinds`, and `mission_type_activations` activation partition | `charter.activation_engine`/`CharterPackManager` through `spec-kitty charter activate` or `spec-kitty charter deactivate`; interview promotion and absent-key seeding delegate to the same activation writer. Derive the complete key set from `ACTIVATION_YAML_KEYS`; direct edits and `charter generate` are forbidden |
| `.kittify/charter/charter.yaml` `catalog` and `metadata` | update their owning pack/profile/directive sources, then run `spec-kitty charter generate`; verify every direct partition is byte-stable |
| `.kittify/charter/interview/answers.yaml` | current `charter interview` serialization is unsafe here: it starts from defaults and drops extra/selected/template fields. M1 backs up exact bytes outside the audited tree, freezes every target coordinate/replacement, applies only those replacements to the original bytes through planned `scripts/migrate_charter_interview_answers.py`, parses before/after, and atomically replaces only after semantic-preservation checks. M1 also makes the normal serializer round-trip the complete mapping; only then may `charter interview` resume ownership |
| `.kittify/charter/context-state.json` | runtime-local cache written only by `spec-kitty charter context` (`context_state.py`); it is not tracked Charter authority. Audit it when present; if no hit, record a no-op. If an owning serializer change makes refresh necessary, rerun each registered action through `charter context --action <action> --mark-loaded`; never use `charter generate` or a direct edit |
| `.kittify/charter/synthesis-manifest.yaml` | `spec-kitty charter synthesize`/`resynthesize` writes it manifest-last from synthesis inputs. If neither inputs nor manifest contain an M1 hit, verify and record no-op; otherwise update inputs and run that owner, never hand-edit or use `charter generate` |
| `.kittify/charter/graph.yml` | tracked legacy activation snapshot with no current supported writer/consumer; before edits, repeat the exact consumer audit. On the frozen target's zero-consumer result, delete it and all referrers as an obsolete snapshot. Any newly found consumer invalidates the dry run and must be added to the fixed M1 map before execution |

The M1 glossary transaction updates `docs/context/doctrine.md` → `docs/context/charter.md`,
`.kittify/glossaries/spec_kitty_core.yaml`, and
`packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml` atomically with all active referrers.
The three authorities must encode the same Charter Pack/Bundle/active/inactive meanings; any parity or
link audit failure rolls back all three. WP01 records the obligation; WP04 consumes canonical
`issue-matrix.json` #2727 and binds it into the M1 contract; downstream M1 consumes that stack output and
cannot split/defer one authority to the issue.

`charter sync` is not a writer. `charter synthesize` owns `.kittify/doctrine/graph.yaml`; it does not own
`.kittify/charter/graph.yml`. M1 acceptance requires every tracked Charter authority/output and every
present runtime-local cache to have its mapped action or an explicit verified no-op, and no ordinary
authority hit may remain outside registered 3.x compatibility owned for M6.

The answers migration preserves every unknown key, all answers, comments, ordering, quoting,
`selected_styleguides`, `selected_toolguides`, `selected_procedures`, `selected_tactics`, `template_set`,
and every selected asset byte-for-byte except frozen target replacements. It writes temp + fsync + atomic
rename, retains the preimage backup/hash until M1 merge, and restores it on parse/parity/write failure.
Named tests: `test_answers_migration_preserves_unknown_keys_and_all_answers`,
`test_answers_migration_preserves_selected_assets_and_template_set`,
`test_answers_migration_changes_only_frozen_target_bytes`, and
`test_answers_migration_failure_restores_preimage`, and
`test_interview_serializer_round_trips_extended_answers`. A deletion/default-reset/empty-
`selected_tactics` mutation must fail. Direct ad hoc YAML editing and the current lossy CLI are forbidden.

## 7. Relationship to prior ADRs and current-tree history

The new ADR supersedes the terminology portion of
`2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md`; resolution mechanics survive.
WP01 may update status/pointer first. M5 later rewrites/renames this ADR, all other matching ADRs, docs
archives, evidence, and referrers in current `HEAD` outside `kitty-specs/` under the explicit override.
Their old bytes remain only in Git history. Nothing in the current tree outside the fixed `kitty-specs/`
archive root is protected from the M5/M6 zero gate; that root is byte-identical across all waves.

## 8. Guard and exact terminal audit

M1 may arm shrink-only ordinary fingerprints and bounded CR reservations for M1–M5 transition safety.
Every base hit receives one M1–M6 owner. M6 deletes every CR control/product/tombstone and the transition
baseline/allowlist machinery, then constructs the token from numeric bytes and runs:

- at the repository toplevel only (`git rev-parse --show-prefix` empty, else audit error): forced-text
  case-insensitive `git grep` over all `HEAD` blobs with the `:(top)`-anchored pathspec
  `':(top)' ':(top,exclude)kitty-specs/'`: count 0;
- NUL-safe case-insensitive `git ls-tree -r -z --full-tree --name-only HEAD`, dropping `kitty-specs/`
  paths after the rc check: pathname count 0;
- every `120000` (symlink) entry: target string read via `git cat-file blob` and audited: count 0
  (`test_symlink_target_audited`);
- a second content pass over text blobs after NFKC normalisation and stripping Unicode `Cf`/soft-hyphen/
  zero-width characters: count 0 (`test_no_homoglyph_or_format_char_evasion`).

Negative tests construct the same numeric byte sequence without storing the token. Any hit, exception,
deferral, missing Charter file, omitted archive exclusion, any other narrowed root, non-toplevel cwd, or
audit error blocks 4.0 (`mutation_subdir_cwd_cannot_pass_zero` is a named mutation).

M6 must create/use the mandatory tracked, token-literal-free entrypoint
`scripts/audit_retired_term_zero.py`; command identity is
`python scripts/audit_retired_term_zero.py --commit <final-commit-oid> --mode terminal --json -`, and the
required CI/release check marker is `terminology-zero-current-tree`. Exit `0` means both zero audits,
`1` means hits, and `2` means audit/input/git error. JSON goes only to stdout and external CI/release
attestation storage; it contains object format, the resolved toplevel, exact lowercase **commit** OID
(`git rev-parse --verify <ref>^{commit}`) and tree OID, `git --version`, argv/raw return codes,
stdout/stderr hashes, counts, and result. It never writes into the audited tree, avoiding self-reference.
Any subsequent tree change invalidates it. CI plus release merge/publish gates rerun the entrypoint on the
final result tree; no earlier working-tree or parent-commit zero result can authorize merge/publication.

## Anti-goals

- no product rename in this planning mission;
- no runtime managed-path ledger/state architecture;
- no silent data overwrite or old-root survival after completed migration;
- no X1/X2/X3 terminal class, allowlist, or current-tree historical carve-out other than the fixed
  `kitty-specs/` archive root;
- no unresolved topology collision when M2 begins editing.
