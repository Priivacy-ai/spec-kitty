# Methodology: Ordering, Invariants, Guards, Verification, Rollback

**Mission**: `retire-doctrine-term-01M0JMK9` · **WP03** · **Inputs**: accepted ADR
`docs/adr/3.x/2026-08-22-2-retire-doctrine-term-charter-is-the-canonical-vocabulary.md`, `inventory.md` (frozen base
`2621a56d06b9ae4e7da07ee206879c30a4d8b363`, TSV `3631531b…`, 49,050 rows, OC-01…OC-49, CR-01…CR-08), `data-model.md`,
`contracts/stacked-plan-schema.md`, `contracts/operator-surface-map-schema.md`, `contracts/inventory-schema.md`,
`contracts/adr-content-contract.md` · **Governing decisions**: `DM-01M0NDJ33GCKATG3H4BK4PAMNG` (full current-tree
extinction), `DM-01M0NMS9WPH33EPFCJQRTQVNSA` (`kitty-specs/` immutable archive = single fixed exclusion root),
`DM-01M0NMSD60JYG7K7V5MJCKJ3P8` (ephemeral manifest) · **Updated**: 2026-08-23

This document fixes the order, the invariants, the transition guard, the per-surface verifiers, the evidence model, and
the rollback rules for the downstream program. It sequences every inventory class exactly once at the transition level;
`stacked-plan.md` (WP04) writes the primary-owner assignment tables on top of it. Nothing here performs a rename (C-001).

## 1. Sequence and invariants (T009)

### 1.1 Strict order

`M1 charter-authority-flip → M2 charter-code-topology → M3 charter-packs-source → M4 charter-agent-assets →
M5 charter-current-tree-prose → M6 charter-compatibility-extinction`. No two waves run in parallel; a wave opens only
when the previous wave's invariant is verified on the wave's fresh base (§4.1). Every wave is `change_mode: bulk_edit`.

### 1.2 Transitions, retired classes, risk

OC ids, row counts and default owners are taken verbatim from `inventory.md` §3 (frozen base). A transition "retires" a
class when, after the wave, no row of that class survives at the wave-local audit other than registered 3.x
compatibility rows annotated `CR-##` (which M6 removes).

| Transition | Retires (OC: rows) | Rows | Risk (primary) | Establishes |
|---|---|---|---|---|
| I0→I1 **M1** | OC-01 glossary authorities 221 · OC-02 Charter Bundle 80 (incl. `governance:`→`doctrine:` selection key, CR-01) · OC-40 `docs/context/doctrine.md` pathname 1 | **302** | split authority (ADR says one thing, Charter/glossary another); generated Charter surfaces overwritten by the wrong writer; lossy `answers.yaml` serialization; generated `charter.yaml` partitions whose producers are M2/M4 are carried forward, not hand-edited | I1 |
| I1→I2 **M2** | OC-03 `.kittify/config.yaml` `doctrine.org.packs` block 2 (CR-04 seam) · OC-12 CLI 633 · OC-13 tracker 40 · OC-14 old-package build 56 · OC-15 old-package schemas/templates 48 · OC-16 `src/doctrine/**` code 815 · OC-17 `src/charter/**` consumers 1,657 · OC-18 generated manifests 54 · OC-19 specify_cli doctrine modules 312 · OC-20 other specify_cli consumers 413 · OC-21 kernel/runtime/glossary/mission_runtime 110 · OC-22 fixtures/controls/baselines 641 · OC-23 architectural gates 1,566 · OC-24 test code 6,076 · OC-25 CI workflows 173 · OC-27 scripts 51 · OC-28 root build/lint config 67 · OC-41 skills-tree pathnames 83 (relocate) · OC-42 `src/doctrine/**` pathnames 181 · OC-43 test pathnames 332 · OC-44 code pathnames 30 · OC-48 repo-ops pathnames 4 | **13,344** | collision with existing `src/charter/` modules (two-module split — `src/charter/offering/` + `src/charter/activation/` — boundary gates renamed, dependency direction preserved (`offering` MUST NOT import `activation`), never merged into facade modules); the top-level `LayerRule` losing the ability to express the offering↛activation edge once both live under one `charter` package (mitigated by re-homing `test_layer_rules.py`/`test_kernel_no_doctrine_import.py` and a new intra-package AST gate); import/build/wheel closure broken mid-slice; `files("doctrine")` resolution broken by a package-named shim; architectural gates (OC-23) and baselines (OC-22) red-wash or silently retarget | I2 |
| I2→I3 **M3** | OC-04 `.kittify/doctrine/**` + overrides 55 · OC-08 pack structure/manifests 42 · OC-45 overlay pathnames 14 | **111** | user-data loss or silent overwrite during root move; old root surviving a "completed" migration | I3 |
| I3→I4 **M4** | OC-06 built-in agent assets 171 · OC-07 built-in mission prompts 51 · OC-09 skill sources (IDs/content) 253 · OC-10 host agent-dir prompts 12 · OC-11 generated profile/skill API docs 75 · OC-46 `doctrine-daphne` / `018-…` pathnames 2 | **564** | installed/shared/override asset IDs derived by wildcard instead of the fixed mapping; old installed path after completion; generated docs not regenerated; the `018-…` activation ID carried forward from M1 must be re-activated through the engine | I4 |
| I4→I5 **M5** | OC-26 serialized docs data 611 · OC-29 ADRs 815 · OC-30 test-sanitation reports 27,990 · OC-31 plans/investigations 2,960 · OC-32 docs prose 1,660 · OC-33 research-outputs/kitty-ops 284 · OC-34 memory/evidence/mission-state history 320 · OC-35 root repo docs 14 · OC-47 docs pathnames 72 · OC-49 history pathnames 3 | **34,729** | a referrer to an archive path changed by editing the archive (forbidden); dangling links after file renames; generated docs data (OC-26) left stale | I5 |
| I5→I6 **M6** | no frozen-base class: every later-created compatibility product/control/fixture/baseline coordinate (CR-01…CR-08 products, OC-22-style control files created after the base, transition fingerprints), plus any detector literal | **0 base rows** | a surviving allowlist/baseline/exception masquerading as zero; an entrypoint with a different pathspec; evidence not bound to the final tree | I6 |

Arithmetic: 302 + 13,344 + 111 + 564 + 34,729 + 0 = **49,050** = all TSV rows; the six retire sets are pairwise
disjoint and contain every OC-01…OC-49 exactly once (OC-05 and OC-50 are declared placeholders with zero rows). Per
surface this matches `inventory.md` §2: S1 633 (M2) · S2 222 (M1) · S3 34,118 (M5) · S4 572 (OC-41 → M2; rest → M4) ·
S5 82 (OC-02 → M1; OC-03 → M2) · S6 111 (M3) · S7 12,189 (M2) · S8 788 (OC-11 → M4; OC-15/OC-18 → M2; OC-26 → M5) ·
S9 295 (M2) · S10 40 (M2). **Re-derived 2026-08-23** after the whole-mission squad's live-code check
(`squad-findings-whole-mission.md`): OC-03 moved M1→M2 (its rows are the `doctrine.org.packs` CR-04 seam, not the
selection key, which is OC-02 `charter.yaml:2,19`), OC-41 moved M4→M2 (the skills tree is `doctrine` package data
resolved by `src/specify_cli/skills/registry.py` and gated by `release.yml:219-243`; M2 relocates it, M4 keeps the
IDs), and CR-07 introduction moved M3→M2 (code literals of the old root). Prior figures 304 / 13,259 / 111 / 647 are
the ones WP05 and the mission review reproduced; the TSV and hash are unchanged. `stacked-plan.md` may split a class
further (a new predicate above the existing rule) but may not move rows across these transition boundaries without
re-deriving this table.

### 1.3 Per-wave content of the transition

1. **M1** makes the ADR override effective and executes the ADR contract's exact per-artifact Charter owner map —
   direct curation of `charter.md` and the human-owned `charter.yaml` `governance`/`directives`/`overrides`
   partitions; activation fields only through `charter activate`/`deactivate` + the shared activation engine
   (`ACTIVATION_YAML_KEYS`); `charter generate` only for `catalog`/`metadata` after source updates; the backup-backed,
   coordinate-exact `interview/answers.yaml` migration + serializer round-trip hardening before `charter interview`
   resumes ownership; `charter context --mark-loaded` for `context-state.json` only if present and hit; `charter
   synthesize`/`resynthesize` for `synthesis-manifest.yaml` only if inputs/manifest hit; repeated zero-consumer proof
   then deletion of obsolete `.kittify/charter/graph.yml`; every no-hit artifact records a verified no-op; `charter
   sync` is not a writer — then the glossary transaction (`docs/context/doctrine.md` → `docs/context/charter.md`,
   `.kittify/glossaries/spec_kitty_core.yaml`, `packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml`,
   all active referrers) under one semantic/hash/link parity gate (#2727 bound in by WP04), the `governance.doctrine`
   → `governance.charter` selection key with its 3.x reader (CR-01) — and **only then** arms the transition guard
   (§2).
2. **M2** freezes `canonical-operator-surface-map.md` + `canonical-cli-route-map.md` for every internal+public
   row/collision (sole bounded gate; the split of `src/doctrine/**` into `src/charter/offering/` (the pure offer
   catalogue) and `src/charter/activation/` (the current charter activation code) is fixed there), then executes that
   split with the one-way import rule preserved (`offering` MUST NOT import `activation`, C-004; `activation` MAY
   import `offering`) and boundary gates renamed (facade and implementation never merged); because both modules now
   live under one `charter` top-level package, re-homes `tests/architectural/test_layer_rules.py` (updated layer-chain
   literal) and `test_kernel_no_doctrine_import.py` into its own gate set and ships a new intra-package AST gate
   enforcing the offering↛activation edge as a hard exit criterion; relocates the skills tree (OC-41; IDs stay M4),
   renames every `.kittify/doctrine` code literal and introduces the dual-root reader/migrator (CR-07), retargets live
   architectural baselines, disposes of the dormant `spec-kitty-doctrine` manifest by map row, and updates
   symbols/imports/tests/fixtures/build hooks/distribution metadata/CLI (incl. nested routes and the `charter
   mission-type` collision)/API/config/workflow/metadata by dependency slice; introduces CR-02…CR-07 within budget;
   carries forward M3/M4/M5 values inside the generated manifests it owns.
3. **M3** preflight → backup → copy/move `.kittify/doctrine/` → `.kittify/charter-packs/` → verify → remove old root;
   divergent destination hard-fails with both intact; canonical writers use only the new root; exercises CR-07
   (introduced by M2) and lands its data-move tests.
4. **M4** applies the same preflight/backup/verify/conflict rule to every source, generated, installed, shared, and
   override skill/profile/directive/prompt/agent artifact, ID, and path using the fixed seven-ID mapping,
   `doctrine-daphne` → `charter-daphne`, `018-doctrine-versioning-requirement` →
   `018-charter-versioning-requirement` (no wildcard derivation) inside the skills tree M2 already relocated;
   re-activates the carried-forward `018-…` ID through `charter activate`/`deactivate`; regenerates
   `docs/api/agent_profiles|skills/**`; introduces CR-08.
5. **M5** rewrites/renames every remaining current-tree prose/history/ADR/docs/archive/evidence occurrence, filename,
   and referrer **outside `kitty-specs/`** — including the program's own ADR files under `docs/adr/` — and
   regenerates serialized docs data (OC-26). `kitty-specs/` stays byte-identical; a referrer that cites an archive
   path containing the token is re-cited by `mission_id`/mid8 or a token-free path. No CR is introduced (prose has no
   compatibility channel). The blind-rewrite rule applies to the retired term as the *domain* word only: a genuine
   English-word occurrence inside an external quotation, citation, or a historical record's title/body attributed to
   a source this program did not author is preserved (quote-preserving paraphrase-with-attribution, or excluded with
   a recorded rationale), never blind-rewritten — distinct from the already design-accepted ADR-title anachronism. M5
   also runs a bounded pre-edit gate before its first prose edit (mirroring M2's topology-map gate, not a design
   question): a proposed rename/re-cite map plus a sampled-diff review over OC-30/OC-31.
6. **M6** deletes every CR product/control/tombstone, alias, key, route, import shim, old-root reader/migrator,
   redirect, warning, distribution alias, compatibility fixture, transition fingerprint/baseline/allowlist record,
   replaces negative fixtures with numeric-byte construction, creates/uses `scripts/audit_retired_term_zero.py`, and
   passes both exact zero audits with the fixed `kitty-specs/` exclusion only (§3.4, §4).

### 1.4 Invariants I0–I6 (verbatim `data-model.md` §6)

| Level | Required state |
|---|---|
| I0 | Existing 3.x authority coherent; no half-renamed state. |
| I1 | ADR and complete Charter/glossary authority graph record the override/canon; M1 hits gone; temporary transition guard armed. |
| I2 | Frozen internal+public topology map fully applied; `src/doctrine/` and every live code/internal/test/build pathname or symbol hit gone; registered 3.x aliases only. |
| I3 | Project overlay data verified at `.kittify/charter-packs/`; completed migrations have no `.kittify/doctrine/` root; conflicts remain pre-completion blockers. |
| I4 | Canonical skills/profiles/directives/prompts/generated/installed assets work; completed migrations have no old-named installed path; registered 3.x aliases only. |
| I5 | All remaining current-tree prose/history/ADR/docs/archive/evidence content, filenames, and referrers outside `kitty-specs/` use canonical vocabulary; `kitty-specs/` is byte-identical to its pre-M5 state. Git object history and that archive alone retain old bytes. |
| I6 | Every CR/alias/key/path/control/fixture removed; transition baselines/allowlists deleted; mandatory `scripts/audit_retired_term_zero.py` check `terminology-zero-current-tree` reports checked content/path counts = 0 (fixed `kitty-specs/` exclusion only) in external stdout attestation for one final commit/tree and is rerun by CI/release on the result tree. |

There is no internal, historical, fixture, generated, metadata, test, supported-surface, or X1/X2/X3 terminal state.
The two fixed exclusions are Git object history outside `HEAD` and the immutable `kitty-specs/` archive root; the root
is an audit boundary, never a class, allowlist, or baseline. Reading rule for I1–I5 ("M1 hits gone", "no live …
hit"): a wave's invariant is stated over the rows **that wave or an earlier wave owns**; rows owned by later waves may
still be present at that level and are listed as carried-forward in the wave's occurrence map (e.g. I1 leaves the
generated `charter.yaml` catalog summaries produced by M2-owned code and the `018-…` activation ID renamed by M4 in
place). I6 is absolute: zero rows of any owner outside the fixed root.

## 2. Transition guard and compatibility lifecycle (T010)

### 2.1 Shrink-only fingerprints (armed at end of M1, deleted by M6)

| Element | Definition |
|---|---|
| Fingerprint (re-keyed 2026-08-23) | **tree-independent**, derived from the same checked subprocess procedure (`inventory.md` §8, hardened contract: toplevel-only, `:(top)` pathspec / `--full-tree` + prefix drop) at the wave's tip: for every audited path, (a) the occurrence count and (b) the multiset of `(case-preserved match bytes, SHA-256 of the containing line bytes)`; pathname rows contribute `(path, 1)`. `match_sha256` embeds the tree OID and is therefore **never** compared across trees (it proves reproduction within one tree, not shrink across two); coordinates `(line, column)` shift under unrelated edits and are not part of the key. Never a per-file count alone, never a regex over a file list |
| Baseline | the previous wave's closing fingerprint (derived from the TSV regenerated at that wave's result tree, SHA-256 of the TSV pinned in that wave's `occurrence_map`); M1's baseline is M1's own opening fingerprint (the frozen base `3631531b…` is planning evidence); the store lives untracked or inside the wave's own `kitty-specs/<wave-slug>-<mid8>/` directory — never a tracked token-bearing file elsewhere |
| Shrink-only rule | at every wave-local audit: (1) no path absent from the baseline (no new path); (2) per path, the occurrence count does not increase; (3) no `(path, line-hash)` pair absent from the baseline — except (a) rows whose `compatibility_registry_id` names a CR the wave is permitted to introduce and whose count is ≤ that CR's `product_hit_budget`, and (b) control coordinates registered in the CR's `control_record`. Any other new path, count increase, or new line-pair fails the gate |
| Enforcement | wave merge gate `test_transition_guard_shrink_only` (compares the wave's fingerprint vs the pinned baseline by path set, per-path counts and line-hash multisets); CI reruns it on the merge result tree |
| Named mutations that must fail | new hit (new `(path, line-hash)` pair or count increase, not CR-budgeted) · equal-count substitution (same per-path count, different line-hash multiset) · moved hit (rename that carries the token to a new path) · stale baseline (baseline TSV SHA-256 ≠ the pinned previous-wave value) · new file with the token · wrong-wave alias (CR product introduced by a wave other than its `introduction_wave`) · budget overflow (products > `product_hit_budget`) · overlap (a source row funding two CRs; a coordinate owned by two waves) · control error (control record missing/unregistered) · surviving detector literal after M6 (any stored token in a test/fixture/script rather than numeric bytes) |
| Deletion | M6 deletes the program's baseline store, allowlist/exception mechanics, and `test_transition_guard_shrink_only`'s baseline input (live architectural baselines retargeted by M2 are not the program's and stay), then switches the guard to exact zero mode (§3.4). No program baseline survives I6 (C-004) |

### 2.2 CR lifecycle (CR-01…CR-08; `inventory.md` §4)

| State | Meaning | Entered by |
|---|---|---|
| `reserved` | frozen-base source rows annotated; no product exists | WP02/WP04 (planning) |
| `active` | introduction wave landed the canonical target plus ≤ budget 3.x product fingerprints and the control record/tests | M1 (CR-01), M2 (CR-02…07 — CR-07's dual-root reader is code, introduced with the literals M2 renames; M3 exercises it), M4 (CR-08) |
| `closed-no-channel` | a CR whose introduction wave proves no 3.x consumer needs the alias (e.g. a route with zero callers): canonical target landed, zero products, control record records the proof | the introduction wave |
| `removed` | products, controls, tombstones, fixtures and registry row deleted; the CR's later-created coordinates are gone from the `HEAD` audit | M6 only |

Rules: the frozen-base **source** rows keep their introduction-wave OC owner (e.g. CR-02's 104 rows stay OC-12/M2);
each source funds at most one CR; product/control/tombstone coordinates created after the frozen base appear as new
rows at the next wave-local audit and receive exactly one **M6-removal** assignment — never duplicate ownership of the
source; M5 and M6 introduce no CR; I6 requires every CR `removed` with no surviving product/control hit. Rollback of an
`active` CR is the rollback of its wave (§4.3); rollback of `removed` is valid only before 4.0 publication.

### 2.3 Post-M6 negative tests

Every negative test and fixture that must refer to the retired token constructs it as
`bytes((100,111,99,116,114,105,110,101))` (or the equivalent numeric code points) and never stores the literal; the
tests assert the exact zero audits and the absence of every compatibility category. The same construction is used by
`scripts/audit_retired_term_zero.py`.

## 3. Verification matrix (T011)

### 3.1 One named verifier per surface category

| S | Category | Named verifier | Proves |
|---|---|---|---|
| S1 | CLI/operator routes | `test_cli_route_map_set_equal_and_canonical` (M2) + `test_doctrine_group_hidden_alias_warns` (CR-02) | every `surface_kind=cli` row in the frozen map has its canonical route; old group is a budgeted hidden alias (3.x) then absent (M6) |
| S2 | glossary/authority | `test_glossary_authority_parity` (M1) | docs context, project glossary YAML, built-in glossary pack and active referrers encode the same Charter Pack/Bundle/Active/Inactive meanings; hash/link parity; rollback-all on divergence |
| S3 | current-tree prose/history | `test_prose_history_closure_outside_archive` (M5) | no M5-owned audit row survives; no dangling link after renames; archive byte-identical (§3.5) |
| S4 | agent artifacts | `test_agent_asset_ids_fixed_mapping_and_no_old_installed_path` (M4) + `test_skill_id_alias_routes_with_warning` (CR-08) | fixed seven-ID + profile/directive mapping applied; installed/shared/override copies canonical; aliases route+warn in 3.x only |
| S5 | Charter authority | `test_charter_owner_map_executed` (M1) | every tracked Charter artifact and present runtime cache has its mapped owner action or verified no-op; regenerated hashes match; activation only via engine; answers migration named tests pass; `graph.yml` deleted after repeated zero-consumer proof |
| S6 | packs/project overlays | `test_old_root_read_warns_and_migrates` + `test_completed_migration_has_no_old_root` (M3, CR-07) | data preserved at `.kittify/charter-packs/`; divergent blocks; old root absent on completion |
| S7 | code/build/test topology | `test_topology_map_set_equality_and_closure` (M2) | map rows == M2-owned manifest hits == discovered producers/consumers; import/build/wheel/test closure; collisions resolved before first edit; no old live topology outside registered CR |
| S8 | serialized/workflow/generated | `test_serialized_surfaces_canonical_writers` (M2/M4/M5 by owner) | keys/URNs/templates/manifests/generated docs emit only canonical values; readers accept old forms only through budgeted CRs (CR-01/03/04/05) |
| S9 | repository operations | `test_repo_ops_canonical` (M2; M5 for prose parts) | CI workflows, scripts, root config/metadata, tracked pathnames canonical; workflow names/markers updated |
| S10 | tracker/ownership | `test_tracker_ownership_mode_canonical` + `test_tracker_doctrine_mode_alias_warns` (M2, CR-03) | `--ownership-mode`/`ownership_mode`/ownership block canonical; `field_owners` unchanged; alias warns in 3.x only |

### 3.2 Mandatory M1 cases

- every tracked Charter artifact (`charter.md`, `charter.yaml` partitions, `interview/answers.yaml`,
  `synthesis-manifest.yaml`, `graph.yml`) and the present runtime cache (`context-state.json`) listed with its exact
  owner/source input and action — direct edit, activation-engine command, sanctioned lossless answers migration,
  `charter generate` catalog/metadata, `charter context --mark-loaded`, `charter synthesize`, or **verified no-op**;
- answers migration named tests (`test_answers_migration_preserves_unknown_keys_and_all_answers`,
  `…_preserves_selected_assets_and_template_set`, `…_changes_only_frozen_target_bytes`,
  `…_failure_restores_preimage`, `test_interview_serializer_round_trips_extended_answers`) and the
  deletion/default-reset/empty-`selected_tactics` mutation failing;
- repeated zero-consumer proof (same frozen consumer audit) immediately before `.kittify/charter/graph.yml` deletion;
  a newly found consumer invalidates the dry run and must be added to the fixed map;
- glossary parity + `governance.doctrine` reader tests (`test_governance_doctrine_key_warns_and_maps`,
  `test_governance_charter_key_canonical`); guard armed last; M1 dry run raised zero operator questions.

### 3.3 Mandatory M2–M5 cases

| Wave | Mandatory cases |
|---|---|
| M2 | map set-equality (rows == M2 manifest hits == producers/consumers, CLI projection == `surface_kind=cli` rows incl. nested routes, map hash recorded); private + public topology both mapped; `src/charter/offering/` + `src/charter/activation/` named and every `src/charter/` collision (`__init__.py`, `pack_paths.py`, `provenance.py`, `resolver.py`, `template_catalog.py`, `versioning.py`, `errors.py`, `exceptions.py`, `primitives.py`; `Directive`, `DoctrineService`, `canonical_yaml`) `merge-existing` or exact `relocate` **before first edit**; boundary gates renamed and green; the new intra-package `charter.offering`-must-not-import-`charter.activation` AST gate green; `test_layer_rules.py`/`test_kernel_no_doctrine_import.py` re-homed and green; every `files("doctrine")` site and `.kittify/doctrine` code literal mapped; skills tree relocated with registry/wheel/release-gate retargets; import/build/wheel/test closure after each dependency slice; `src/doctrine/` directory absent; live architectural baselines retargeted, not deleted; CR-02…CR-07 within budget; later-wave rows carried forward and listed |
| M3 | absent destination (copy/move, verify, remove old); identical destination (verify, remove old); divergent destination (hard-fail, both intact, operator resolves); interruption before verification (rollback from backup, no completion marker); completed migration has no `.kittify/doctrine/` root; canonical writers never write the old root |
| M4 | same six cases for every source/generated/installed/shared/override asset; IDs/paths from the fixed mapping only; `docs/api/agent_profiles|skills/**` regenerated; no old-named installed path after completion |
| M5 | bounded pre-edit gate (rename/re-cite map + OC-30/OC-31 sampled-diff review) approved before the first prose edit; quotation/homograph-fidelity rule applied (external quotations/citations/historical-record titles-bodies preserved with attribution or excluded-with-rationale, never blind-rewritten); filename/referrer closure outside `kitty-specs/` (no dangling renamed reference; link check scoped `:(exclude)kitty-specs/` — the archive cites renamed paths by design; `docs/adr/3.x/index.md` and page inventory regenerated by the freshener); archive gate in its §3.5 test form; archive referrers re-cited by `mission_id`/mid8 or token-free path; OC-26 serialized docs data regenerated; OC-30 `docs/reports/test-sanitation/**` rename-in-place with `tests/architectural/test_marker_job_completeness.py` green; serialized historical records handled per the resolved `DM-01M0P6C8C7Q6SPBT412V39RPN0` |

### 3.4 Mandatory M6 cases

- every compatibility category removed: CR products/controls/tombstones, aliases, keys, routes, import shims, old-root
  reader/migrator, redirects, warnings, distribution aliases, compatibility fixtures, transition fingerprints/baselines,
  allowlists, exception lists — verified by `test_no_compatibility_machinery_remains` (registry empty; each CR
  `removed`);
- no exception machinery of any kind survives (no baseline input, no allowlist file, no skip marker, no X value);
- exact zero gate: the inventory contract's checked subprocess audits in `mode=terminal` over the final commit, **run
  at the repository toplevel only** (`git rev-parse --show-prefix` empty, else audit error), with the `:(top)`-anchored
  pathspec `':(top)' ':(top,exclude)kitty-specs/'` and `ls-tree --full-tree` + prefix drop — content raw rc 1 + empty
  stdout, pathname raw rc 0 + zero matches, symlink targets zero, normalised-content pass zero, wrapper exit 0; an
  entrypoint that omits that exclusion, adds any other, or accepts a subdirectory cwd fails;
- named failure cases `test_content_audit_accepts_rc1_empty_only`, `test_content_audit_rejects_git_rc_gt1`,
  `test_path_audit_propagates_ls_tree_failure`, `test_symlink_target_audited`,
  `test_no_homoglyph_or_format_char_evasion`, `mutation_git_audit_failure_cannot_pass_zero`,
  `mutation_subdir_cwd_cannot_pass_zero`;
- numeric-byte negative test (`test_retired_token_absent_numeric_bytes`) plus
  `test_no_detector_literal_remains` (no stored literal in tests/fixtures/scripts);
- `scripts/audit_retired_term_zero.py --commit <final-oid> --mode terminal --json -` required under check marker
  `terminology-zero-current-tree`; exit 0/1/2 semantics (2 = audit/input/git error incl. non-toplevel cwd; usage
  errors use a distinct code); stdout-only attestation (object format, resolved toplevel, `git --version`, lowercase
  commit/tree OIDs, argv/raw rcs, stdout/stderr hashes, counts, result); CI and release merge/publish gates rerun it on
  the result tree; any tree change invalidates prior evidence; no earlier working-tree or parent-commit zero result
  authorizes merge or publication; the release row (CI job + pre-publish step + required-check registration + 4.0
  bump/CHANGELOG) is M6 output.

### 3.5 Archive immutability check (every wave)

Each wave's merge gate includes `test_archive_root_byte_identical`, stated in the executable form of
`stacked-plan.md` §0 (DD-011, test form fixed 2026-08-23): the wave never edits, renames, or deletes a pre-existing
path under `kitty-specs/`. **Test**: `git diff --name-status $(git merge-base <target-branch> <wave-tip>) <wave-tip>
-- kitty-specs/` contains only `A` entries, all under the wave's own `kitty-specs/<wave-slug>-<mid8>/` (each M1–M6
wave is itself a Spec Kitty mission; during this planning mission only, this mission's own WP outputs). A whole-range
base→result diff on the target branch is **not** the test — unrelated missions routinely modify their own pre-existing
archive directories between a wave's base and its landing, and that is not the wave's doing. Any `M`/`D`/`R` entry or
an `A` outside the wave's own directory blocks the wave; the terminal audit still excludes the whole root.

## 4. Evidence and rollback (T012)

### 4.1 Wave-local snapshot and occurrence map

Each wave, before its first edit: `git fetch`, require the current target tip is incorporated, atomically persist its
own `implementation-baseline.json` (target ref, 40-char tip, implementation base, commands, timestamp, actor, wave id);
run the inventory-contract audits (same argv, same fixed exclusion, `mode=inventory`) at that tip; write the wave's
`occurrence_map` (TSV SHA-256 + counts, the wave's exact owned hit set as `OC`/`CR` membership derived by the same
ordered rule tables plus any finer predicates the stacked plan added); pin the previous wave's closing manifest as the
guard baseline. Ephemeral TSVs are regenerate-and-match evidence (`DM-01M0NMSD60JYG7K7V5MJCKJ3P8`).

### 4.2 Per-wave exact inputs/outputs/tests/gate

| Wave | Inputs | Outputs | Tests (named above) | Merge gate |
|---|---|---|---|---|
| M1 | accepted ADR; `inventory.md` OC-01/02/40 + CR-01 (OC-02 rows); `contracts/adr-content-contract.md` §6; canonical `issue-matrix.json` #2727 row; referrers of `docs/context/doctrine.md` | ADR-effective Charter/glossary graph; `governance.charter` + 3.x reader; token-literal-free answers migration script + hardened serializer; regenerated catalog/metadata (section-update entry path pinned); `graph.yml` deleted; referrers re-pointed; guard armed (store untracked / in M1's mission dir; baseline = M1 opening fingerprint); carried-forward list (M2/M4-owned generated rows); wave occurrence map | `test_charter_owner_map_executed`, `test_glossary_authority_parity` (fixed predicate), answers-migration tests, CR-01 tests, `test_transition_guard_shrink_only`, `test_archive_root_byte_identical` | all owner workflows regenerate consistently; M1-owned rows gone (later-wave rows carried forward); zero operator questions raised |
| M2 | I1 tree; OC-03, OC-12…OC-28 (M2 rows), OC-41/42/43/44/48; CR-02…CR-07; `contracts/operator-surface-map-schema.md`; live boundary gates incl. `test_layer_rules.py`/`test_kernel_no_doctrine_import.py`; skills registry/wheel/release gate | frozen `canonical-operator-surface-map.md` + `canonical-cli-route-map.md`; `src/doctrine/**` split into `src/charter/offering/` + `src/charter/activation/` with gates renamed and a new intra-package offering↛activation AST gate; `test_layer_rules.py`/`test_kernel_no_doctrine_import.py` re-homed; skills tree relocated; `.kittify/doctrine` literals renamed + dual-root reader (CR-07); baselines retargeted; dormant manifest disposed; renamed code/tests/build/CLI/API/config/workflow/metadata; CR-02…07 products/controls; occurrence map incl. carried-forward M3/M4/M5 values | `test_topology_map_set_equality_and_closure`, `test_cli_route_map_set_equal_and_canonical`, `test_charter_offering_does_not_import_activation`, CR-02…07 tests, renamed boundary gates, S8/S9/S10 verifiers, guard, archive check | no M1/M2-owned live executable/code hit or pathname outside registered CR; `src/doctrine/` absent; new AST gate green; map approved before first edit |
| M3 | I2 tree; OC-04/08/45 (CR-07 reader already present) | `.kittify/charter-packs/` canonical root + verified migrated data; CR-07 exercised; occurrence map | `test_old_root_read_warns_and_migrates`, `test_completed_migration_has_no_old_root`, six migration cases, guard, archive check | completed fixtures/projects have no old root; conflicts block |
| M4 | I3 tree; OC-06/07/09/10/11/46; CR-08; fixed ID mapping; carried-forward `018-…` activation ID | canonical source/generated/installed/shared agent assets (inside the tree M2 relocated); alias routing table; regenerated API docs; occurrence map | `test_agent_asset_ids_fixed_mapping_and_no_old_installed_path`, CR-08 tests, six migration cases, guard, archive check | completed installations have no old asset path; no M1–M4-owned row remains |
| M5 | I4 tree; OC-26/29/30/31/32/33/34/35/47/49 + post-base rows the rules give M5; `test_marker_job_completeness.py`; resolved `DM-01M0P6C8C7Q6SPBT412V39RPN0` | canonical prose/history/ADR/docs/evidence files and names outside `kitty-specs/`; OC-30 rename-in-place; regenerated serialized docs data; occurrence map | `test_prose_history_closure_outside_archive`, docs freshener `--check`, link check scoped outside the archive, guard, archive check | M5-owned audit rows zero; no dangling renamed refs outside the archive; archive gate test form (§3.5) |
| M6 | I5 tree; CR registry (all `active`/`closed-no-channel`); all later-created product/control coordinates | no aliases/keys/paths/controls/fixtures/program baselines/allowlists; numeric-byte negative tests; `scripts/audit_retired_term_zero.py` (toplevel-only, `:(top)`, `--full-tree`, symlink + normalised passes); external attestation; CI/release wiring + required check + 4.0 bump/CHANGELOG | §3.4 tests | checked content/path/symlink/normalised 0 bound to final commit/tree; CI/release rerun after any tree change; no earlier result authorizes publication |

### 4.3 Rollback

| Situation | Rule |
|---|---|
| wave fails its gate before landing | fix forward within the wave or revert the wave's commits; the guard baseline stays the previous wave's manifest |
| wave landed, dependents not yet landed | revert that one wave (git revert of its landed range); M1 rollback restores the authority graph and un-arms the guard |
| dependents landed | reverse the landed suffix (newest wave first) or forward-fix; never revert a middle wave alone (split authority) |
| M3/M4 migration failure | restore the verified backup (content + mode), leave both originals intact on divergence, do not mark complete; rerun after operator resolution |
| M6 before 4.0 publication | Git revert of M6 (aliases return) is valid; I6 cannot be claimed while either audit is nonzero |
| after 4.0 publication | release-level rollback only (yank/superseding release); no in-tree exception may be added to pass the gate |

### 4.4 Explicit rejection of runtime ledger architecture

The program needs bounded migration preflight (source/destination inventory), a backup, a checked copy/move, a
verification step, source removal, and evidence files — not a managed-path ledger, state store, dual-write layer, or
runtime reconciliation service. Any design that keeps the old root/path "registered" after completion is rejected
(R8/R9).

## 5. Closure

Every inventory class OC-01…OC-49 and every CR-01…CR-08 has exactly one transition (§1.2), a named risk (§1.2), a
named verifier (§3.1–§3.4), a guard rule (§2), and a rollback path (§4.3). No policy question remains open for M1, M3,
M4 or M6; M2's single bounded gate is the pre-edit topology-map approval (which now also fixes the
`src/charter/offering/` / `src/charter/activation/` split), and it cannot change scope, order, or the terminal
zero rule; M5 similarly carries a bounded pre-edit gate (rename/re-cite map + OC-30/OC-31 sampled-diff review,
mirroring M2's) that is not a design question, plus exactly one deferred
operator decision (`DM-01M0P6C8C7Q6SPBT412V39RPN0`, serialized historical records) that must be resolved before M5 is
specified — left deferred by operator decision; M6's single-fixed-`kitty-specs/`-exclusion terminal contract is
therefore contingent on that resolution (§1.2 Options 1/3 would require a scoped re-author of the M6 audit contract;
tracked in issue #3684) and is not represented as finalized here. I6 is equivalent to the exact audit results
(content, pathname, symlink-target, normalised-content) over `HEAD` at the repository toplevel with the single fixed
`kitty-specs/` exclusion — not a curated exception set.
