# Data Model: Retire the Doctrine Term

**Mission**: retire-doctrine-term-01M0JMK9 · **Phase 1 output** · **Date**: 2026-08-22

This planning mission defines six artifact entities: surface category, occurrence hit, occurrence
class, compatibility reservation, stacked mission, and stack-level invariant. No runtime/domain model
is added.

## 1. Surface category

Every in-scope hit belongs to exactly one category. Categories describe operator-visible surfaces, not file types; one file may contain hits from several categories.

| ID | Category | Complete base scope | Primary verification |
|----|----------|---------------------|----------------------|
| S1 | `cli-executable` | Human-facing command routes, subcommands, flags, help, errors, warnings, and CLI text emitted for people; excludes machine fields in S7 and the fixed tracker flag/output seam in S10 | fingerprint guard + canonical/alias CLI tests |
| S2 | `glossary-authorities` | `docs/context/doctrine.md` → `docs/context/charter.md` plus every active referrer in the same M1 wave; immutable X2 inline/path references stay byte-identical historical text with no current-HEAD link promise; plus both YAML glossary authorities | guard + parity/audit + 3.x old-path test + zero active old-ref test |
| S3 | `active-human-prose` | Current human-facing prose regardless directory: non-ADR `docs/` outside S2 and source-tree Markdown/READMEs outside S4. Root-level operator documents are exclusively S9; generated/render templates remain S7. | fingerprint guard + link/path audit |
| S4 | `prompts-skills-profiles-agent-artifacts` | Source skills/profiles/directives, `.github/prompts/`, `.kittify/overrides/`, and installed/generated agent prompts or skill copies | guard where scanned + audit + migration/upgrade smoke tests |
| S5 | `charter-bundle` | Human-authored sections of `.kittify/charter/charter.yaml`, curated `charter.md`, plus graph/interview/runtime sections routed to their owning workflows | bundle diff + `charter generate` catalog refresh + context/render validation |
| S6 | `packs-overlays` | Built-in and org packs, project overlays, and the project-overlay root migration `.kittify/doctrine/` → `.kittify/charter-packs/` (never into the Charter Bundle at `.kittify/charter/`) | audit + pack validation + dual-read/upgrade/collision tests |
| S7 | `generated-serialized-api-output` | Runtime-rendered headings/paths/context, schema-generator output, target URNs, schema aliases, enum/policy/hash values, machine JSON/event/API output, supported public Python exports/imports, and installable distribution/project/wheel metadata; includes the exact `doctrine.api.__all__` and public metadata/content inside `src/doctrine/pyproject.toml`, but not a non-emitted physical implementation pathname (X1), and excludes the fixed tracker output seam in S10 | guard/audit + frozen operator-surface map + output/API/wheel parity snapshots |
| S8 | `scripted-consumers` | Workflow filenames/content, prompt consumers, scripts, and `uses:` references | audit + same-wave CI consumer tests |
| S9 | `root-docs` | `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, and other root operator docs | audit |
| S10 | `operator-config-storage` | Three distinct seams: charter selection `governance.doctrine` → `governance.charter` (M1); org-pack config `doctrine.org.packs` → `charter_packs.org.packs` (M2); tracker ownership block/flag/output → `ownership`, `--ownership-mode`, `ownership_mode` (M2). Old readers/flags warn through 3.x; M6 removes them. | per-seam compatibility/migration/API tests + audit |

For any apparent overlap, the most specific owning surface wins in this order: S10, S2, S4, S5,
S6, S8, S9, then S1/S7/S3. S1 owns executable human CLI routes/help/errors/warnings;
S7 owns machine-serialized/generated/API output and supported public API names; S3 owns remaining
active human prose. A mention of a command inside a skill, workflow, or root document stays S4, S8,
or S9 respectively. The tracker flag/output named in S10 is always S10, never S1 or S7.

The exact audit governs counts. Orientation only at the reviewed base: 429 `src/`, 731 `tests/`, 430 total `docs/`, 103 `packs/`, and 45 `.kittify/` files contain the term case-insensitively.

### Classification-out categories

| ID | Category | Per-hit rule |
|----|----------|--------------|
| X1 | `internal-identifier` | Non-public package/module/import/symbol names and non-emitted implementation paths. Names/imports in `__all__`, package re-exports, public API/operator docs/skills, external contracts, or installable distribution/project/wheel metadata are supported public API and never X1. Operator IDs and serialized config/path names are also never X1. |
| X2 | `immutable-history` | Every merged ADR body/title, including the new Accepted terminology ADR after this planning PR merges; immutable event journals; and merged mission snapshots whether or not later archived. An unmerged/current working mission is active and never X2; merge is the lifecycle threshold. ADR status/pointer metadata remains the narrow mutable carve-out. |
| X3 | `intentional-non-user-facing-data` | Quoted test fixtures, matcher literals, and data whose purpose is to detect or document the retired string without emitting it to users. Active glossary packs, warnings, and compatibility aliases are not X3. |

## 2. Occurrence hit (`inventory-hits.tsv`)

One row represents one case-insensitive textual occurrence or one matched tracked pathname at WP01's
frozen `origin/main` target tip. Immediately before its first edit, WP01 fetches that ref, requires it
is an ancestor of `HEAD`, and atomically persists target plus implementation anchors. WP02–WP05 never
repoint that snapshot; a stale branch point or post-capture target incorporation invalidates evidence.

| Field | Type | Rule |
|-------|------|------|
| `hit_id` | `H-C-######` or `H-P-######` | Stable within a snapshot; assigned after deterministic sort |
| `kind` | `content` or `pathname` | Text occurrence vs one occurrence per matched tracked path |
| `path` | repo-relative path | Path at `base_commit` |
| `line` | positive int or empty | Empty for pathname hits |
| `column` | positive int or empty | Column reported by `git grep`; empty for paths |
| `classification_id` | `OC-##` or `X1`/`X2`/`X3` | Exactly one; never empty |
| `surface_category` | `S1`..`S10` or empty | Required for OC rows; empty for X rows |
| `compatibility_registry_id` | `CR-##` or empty | Nonempty only for an OC product-compatibility hit after introduction; always empty for X1/X2/X3, including the separately fingerprinted X3 registry control record; never changes arithmetic |

**H-I1 (exhaustive join)**: manifest row count equals content occurrences plus matched pathnames from the two canonical audit commands.

**H-I2 (deterministic)**: rows sort by `kind,path,line,column`; hit IDs derive from that order. Re-running at the same commit produces byte-identical coordinates and IDs.

## 3. Occurrence class (OC-##)

| Field | Type | Rule |
|-------|------|------|
| `id` | `OC-##` | Stable and never reused |
| `surface_category` | `S1`..`S10` | Exactly one |
| `path_patterns` | list | Descriptive scope; manifest membership is authoritative |
| `occurrence_count` | int | Number of manifest rows assigned to the class, not matching lines/files |
| `representative_examples` | at most 3 coordinates | Presentation only; cannot substitute for manifest rows |
| `operator_typed` | bool | True for commands, keys, paths, skill/profile/directive IDs |

Assignment is deliberately absent here. `stacked-plan.md` is the single owner of OC-to-mission
assignment. Every pre-M1 OC hit is ordinary primary use and receives exactly one M1–M5 owner; an OC
is never duplicated or reassigned merely because its literal later participates in compatibility.

**OC-I1**: every OC count is mechanically derived from manifest rows.

**OC-I2**: classification is per occurrence, never inferred from an entire file. Mixed files can contain both OC and X hits.

## 4. Compatibility reservation and classified occurrence fingerprint

A compatibility reservation is a budget overlay, not a second hit classification or OC assignment.
M1 creates one `CR-##` entry for each semantic legacy form/path that a declared M1–M4 introduction
wave may need to retain as 3.x compatibility. Identity is `(legacy_form, semantic_seam,
source_hit_coordinates, introduction_wave)`, not literal or mutable resolved target: the same literal may
have multiple CRs only when their exact source/product fingerprint sets are disjoint.

| Field | Rule |
|-------|------|
| `id` | Stable `CR-##`, never reused |
| `legacy_form` / `semantic_seam` | Full literal or repo-relative path plus one meaning/target seam; fragments forbidden |
| `source_oc_ids` / `source_hit_coordinates` | Existing OCs plus a disjoint exact subset of their actual pre-M1 hits; each coordinate funds at most one CR and its OC primary owner equals `introduction_wave` |
| `introduction_wave` / `removal_owner` | One of M1–M4 / always M6 |
| `disposition` | `reserved` before introduction; then `active` or, only with distribution publication/no-channel evidence, `closed-no-channel`; both records persist until M6 |
| `frozen_product_maximum` | Size of that reservation's disjoint exact source-hit set; aggregate maxima for a legacy form never exceed its unique pre-M1 hits |
| `canonical_target` | Initially either `fixed:<canonical literal/path>` or, only for M2's bounded question, `owner:M2; source_oc:<OC-##>`; M2 replaces its descriptor with the literal/map-row reference before edits without changing CR identity or ID |
| `compatibility_fingerprints` | Empty before introduction; after introduction, exact source/path fingerprints, each linked by `compatibility_registry_id` while retaining its sole OC classification |
| `control_record_path` / `control_record_fingerprint` | Fixed path `tests/architectural/legacy_terminology_compatibility_registry.yaml`; fingerprint empty in WP02 candidate, materialized by M1 as one exact X3 control record containing the full form; manifest CR column stays empty, record is excluded from product budget and deleted with CR at M6 |
| `verification` | Named enumeration and behavior/migration test; M6 absence test |

`owner:M2; source_oc:<OC-##>` is an immutable candidate ownership/reference descriptor, not `TBD` or
part of CR identity. M2 freezes the
literal canonical form and authoritative map row into both map and registry atomically before its
first source edit; until then the reservation is fail-closed and cannot gain product compatibility
fingerprints. Fixed M1/M3/M4 targets are literal from M1. For the public distribution candidate,
M2 also resolves publication evidence: published creates evidence-required compatibility within the
reservation and sets `active`; unpublished removes the ordinary hit, sets `closed-no-channel`, and
retains the exact control/evidence tombstone until M6 without inventing an alias or product fingerprint.

WP02's planning inventory records a reservation **candidate** with `observed_source_hit_coordinates`
and `observed_count` at its pinned planning base, plus the fixed target/owner descriptor and control
path. M1 reruns the canonical audit at its actual pre-M1 base, emits a fail-closed drift reconciliation,
then materializes the CR's disjoint actual `source_hit_coordinates`, `frozen_product_maximum`, and X3
control fingerprint before the final guard. A new semantic form without a planned candidate cannot
become compatibility; coordinate drift for an existing candidate must be completely classified and
reviewed, never silently absorbed.

M1 seeds the guard with **every** classified pre-M1 occurrence inside guard roots:

- ordinary `OC-##` hits owned exactly once by M1–M5 and approved X1/X2/X3 hits use exact fingerprints: `kind`, repo-relative `path`, normalized-line/path SHA-256, match ordinal, classification ID, and owner wave. M1 first materializes this complete pre-edit baseline, then removes its own source/baseline entries in the same PR before the final guard lands; the preimage, M1 scoped delta, and post-M1 baseline are review evidence;
- repository-wide, each potential 3.x compatibility identifier, command route, serialized key, project path, parser/migrator literal, redirect, or warning has a `CR-##` reservation from M1 with semantic seam, full legacy literal/path, disjoint source hit coordinates/OCs, canonical-target descriptor, introduction wave, M6 removal, frozen product maximum derived from the pre-M1 manifest, exact X3 control record, and named tests. Every funded source hit's OC primary owner equals the introduction wave; mixed-owner OCs/CRs are split before assignment. The declared introduction wave atomically removes the ordinary primary-use fingerprints, transitions `reserved` to `active` (or the M2 distribution-only `closed-no-channel` state), and records no more than that budget of exact product compatibility fingerprints. Control records do not consume product budget but remain exact/audited and must disappear at M6. The guard enforces fingerprints inside its roots; the pinned registry audit and named surface verifier enforce the same exact entries elsewhere.

Line numbers are diagnostic only. Owner waves remove ordinary OC fingerprints. Product alias literals may not be hidden by string fragments; fragments are X3 only inside detector fixtures. By I6 the compatibility registry is empty and only valid X fingerprints may remain.

**FP-I1**: ordinary current fingerprints must equal baseline exactly. Growth, same-count substitution, a new file, or a stale entry all fail. Compatibility fingerprints are a separate CR overlay and match their registry exactly except during their declared M1–M4 introduction wave.

**FP-I2**: when any ordinary hit is removed, its baseline entry is removed in the same change. Ordinary OC fingerprints shrink in M1–M5; X fingerprints shrink when debt disappears. M1 records complete preimage → scoped removal → post-M1 guard baseline before I1. Never reclassify OC to X merely to retain it.

**FP-I3 (compatibility introduction/relocation)**: only the declared introduction wave may atomically remove ordinary fingerprints, transition the reservation from `reserved` to `active` (or M2 distribution-only `closed-no-channel`), and create or relocate product compatibility fingerprints. Each funded source hit's OC primary owner equals that wave. Each resulting row keeps exactly one OC classification and adds its CR ID; it is not reassigned to M6. The full legacy literal/path remains in one exact X3 registry control record, new exact product locations are committed with the change, total product fingerprints cannot exceed the frozen product maximum, and named tests prove the frozen canonical target, legacy behavior/migration, warning where executable, and runtime/file/key enumeration. M2 target descriptors become literal/map-row references before edits without changing stable CR identity. All unregistered legacy hits fail. M6 deletes every CR control record, product compatibility fingerprint, parser/redirect/alias support, and legacy runtime/file/key exposure; terminal compatibility enumeration must be empty.

**FP-I4**: tests mutate the ordinary failures plus compatibility evasion: add to a baselined file;
equal-count user-facing substitution; remove without baseline shrink; add a new file; add/move an
unregistered or wrong-wave alias; exceed a product budget; construct a product alias from fragments;
double-fund a source coordinate; overlap a product fingerprint; or duplicate/move/stale an X3 control
record. A fail-closed M2 target/disposition also blocks introduction before any source edit.

**CR-I1**: each pre-M1 source hit coordinate funds at most one CR and each introduced product
compatibility fingerprint belongs to exactly one CR. CR coordinate sets are pairwise disjoint,
including reservations sharing a legacy form; aggregate maxima per form cannot exceed unique pre-M1
hits. Manifest arithmetic counts every hit once; the CR column only annotates it. Mutation tests reject
double-funded coordinates, overlapping product fingerprints, duplicated control records, or an
introduction wave different from a funded source OC's primary owner.

## 5. Stacked mission

| Field | Rule |
|-------|------|
| `slug` | Final kebab-case mission slug |
| `purpose` | One operator-facing line |
| `inputs` / `outputs` | Complete artifacts and evidence; no implicit dependency |
| `depends_on` | Explicit earlier slugs/milestone |
| `retires_oc` | Ordinary OC IDs; M1–M5 assignment table is sole primary-use owner; M6 has none |
| `introduces_compatibility` | CR IDs introduced by this M1–M4 wave; empty for M5/M6 |
| `removes_compatibility` | Empty for M1–M5; M6 lists every CR ID exactly once |
| `change_mode` | `bulk_edit` for M1–M6, each with a scoped occurrence map |
| `invariant_after` | I1..I6 below |
| `local_design_questions` | M1 empty. M2's exhaustive canonical operator-surface map is the sole later question; M2 owns every mapped command/serialized/API occurrence, supported public Python facade (with aggregate exact `doctrine.api.__all__` membership evidence and separate rows only for legacy-bearing members), public distribution/wheel surface, publication-evidence treatment, and producer/consumer, then freezes the contract before edits. M3–M5 exclude mapped hits. |
| `rollback` | Revert alone before dependents; after dependents, reverse landed suffix or forward-fix. M6 can restore aliases only while 3.x compatibility remains supported. |

Every out-of-repo deferral names surface, repo, owner, target milestone, tracking reference or downstream process, and rationale. No TBD remains at closeout. Every OC appears once in `retires_oc` across M1–M5 or has an explicit external deferral. Every CR appears once in its declared M1–M4 `introduces_compatibility` list and once in M6 `removes_compatibility`; every funded source OC owner equals that introduction wave, mixed-owner rows split, and this overlay never duplicates OC ownership.

## 6. Stack-level invariants

| Level | Required state |
|-------|----------------|
| I0 pre-M1 | Existing authority remains coherent; no half-flip. |
| I1 post-M1 | Charter Pack/Bundle and activation vocabulary agree across glossary/charter authorities; `docs/context/charter.md` and all active referrers are canonical while the registered old path redirects/warns; immutable X2 references remain historical text; `governance.charter` works with old selection-key reader warning; catalog metadata refreshed; complete pre-M1 fingerprint preimage and M1 delta recorded; post-M1 guard + compatibility registry armed. |
| I2 post-M2 | Authoritative operator map + set-equal CLI projection frozen; canonical CLI, serialized/API values including `charter:<kind>:<id>`, `charter_packs.org.packs`, and tracker ownership work; old active surfaces warn; fixture hashes use canonical-first/legacy fallback with rekey manifest; mapped consumers move or have owned milestones; immutable X2 history renders canonically. |
| I3 post-M3 | Built-in/org/project pack and overlay surfaces use Charter Pack; `.kittify/charter-packs/` is the sole write root; 3.x readers accept the registered `.kittify/doctrine/` legacy root with warning; collision-safe upgrade migration works; canonical directive ID works with old alias. |
| I4 post-M4 | The complete ADR skill/profile map is canonical, including both lifecycle aliases → `spk-charter-lifecycle`; old IDs warn through 3.x; overrides and generated agent copies migrate through owning flow. |
| I5 post-M5 | All remaining current human-facing prose uses new terms regardless directory; immutable history remains classified X2. |
| I6 post-M6 | Compatibility aliases/legacy paths/keys removed; canonical audit finds zero user-visible hits. Only classified X1/X2/X3 occurrences may remain. |

No state may forbid the old user-facing term before replacement authority is available. Each wave regenerates the manifest, shrinks ordinary fingerprints, performs only its registered compatibility relocations, and records invariant evidence before the next begins.
