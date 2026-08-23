# Stacked Plan: M1–M6 Terminology-Extinction Program

**Mission**: `retire-doctrine-term-01M0JMK9` · **WP04** · **Contract**: `contracts/stacked-plan-schema.md` ·
**Inputs**: accepted ADR `docs/adr/3.x/2026-08-22-2-retire-doctrine-term-charter-is-the-canonical-vocabulary.md`,
`inventory.md` (frozen base `2621a56d06b9ae4e7da07ee206879c30a4d8b363`, tree `26e6fdd2…`, TSV `3631531b…`, 49,050 rows,
OC-01…OC-49, CR-01…CR-08), `methodology.md` (§1.2 transitions, §2 guard/CR lifecycle, §3 verifiers, §4 evidence/rollback),
`data-model.md` §3–§7, `contracts/operator-surface-map-schema.md`, `contracts/adr-content-contract.md` §6/§8,
`contracts/inventory-schema.md`, canonical `issue-matrix.json` row `#2727` · **Governing decisions**:
`DM-01M0NDJ33GCKATG3H4BK4PAMNG` (full current-tree extinction), `DM-01M0NMS9WPH33EPFCJQRTQVNSA` (`kitty-specs/` immutable
archive = single fixed exclusion root), `DM-01M0NMSD60JYG7K7V5MJCKJ3P8` (ephemeral manifest) · **Updated**: 2026-08-23

This plan is the sole primary-owner table for the program: every frozen-base row is assigned exactly once to M1…M6 through
its occurrence class, every compatibility reservation has one introduction owner and one M6 removal, and each wave entry
is executable from the artifacts alone. Nothing here performs a rename (C-001).

## 0. Program-wide rules (apply to every wave)

- **Strict order** M1 → M2 → M3 → M4 → M5 → M6; `change_mode: bulk_edit`; each wave is its own Spec Kitty mission
  (`kitty-specs/<slug>-<mid8>/`) with `depends_on` = the previous wave's landed invariant.
- **Base capture** (methodology §4.1): fetch, require the target tip incorporated, atomically persist the wave's own
  `implementation-baseline.json`; run the inventory contract's checked no-pipeline audits (`inventory.md` §8 procedure
  with the hardened contract: toplevel-only, `:(top)`-anchored pathspec `':(top)' ':(top,exclude)kitty-specs/'`,
  `ls-tree --full-tree` + prefix drop, symlink-target and normalised-content passes, `mode=inventory`) at that tip; write
  the wave's `occurrence_map` (TSV SHA-256 + counts + exact owned hit set derived by the ordered OC/CR rule tables, plus
  any finer predicate the wave adds above an existing rule); pin the previous wave's closing manifest as the guard
  baseline. **Every wave's opening audit re-derives ownership by the rule tables** — rows created after the frozen base
  (e.g. this program's own ADR under `docs/adr/`, ~48 hits → OC-29/M5) fall to the owner the rules give them; M1's guard
  baseline is M1's own opening manifest, not the frozen-base `3631531b…`.
- **Wave gate semantics**: at a wave's closing audit, **no row owned by this wave or an earlier wave** remains outside
  registered CR products/controls; rows owned by later waves may remain and are listed as *carried-forward* in the wave's
  occurrence map (e.g. M1 carries forward `charter.yaml` catalog summaries emitted by M2-owned
  `src/charter/compiler.py:1449` and the `018-doctrine-versioning-requirement` activation ID renamed by M4/CR-08; M2
  carries forward M3/M4 values inside generated manifests it owns).
- **Archive gate** (executable form; methodology §3.5): no **pre-existing** path under `kitty-specs/` is edited, renamed,
  or deleted by the wave. Test form: `git diff --name-status $(git merge-base <target-branch> <wave-tip>) <wave-tip> --
  kitty-specs/` contains only `A` entries, all under the wave's own `kitty-specs/<wave-slug>-<mid8>/`. A whole-range
  base→result diff on the target branch is **not** the test (unrelated missions mutate their own archive directories).
  The terminal and wave-local audits still exclude the whole root. Referrers outside the root that cite an archive path
  containing the token are re-cited by `mission_id`/mid8 or a token-free path (M5); the archive path itself never
  changes.
- **Guard** (methodology §2.1, re-keyed 2026-08-23): tree-independent shrink-only fingerprint — per audited path, the
  occurrence count plus the multiset of `(case-preserved match, SHA-256 of the containing line bytes)`; "shrink" = per-path
  count non-increase, zero new paths, no new `(path, line-hash)` pair, except CR-budgeted products and registered controls
  of the wave's own CRs; `test_transition_guard_shrink_only` in every merge gate; the baseline store lives untracked or
  inside the wave's own `kitty-specs/<wave-slug>-<mid8>/` directory, never as a tracked token-bearing file elsewhere; M6
  deletes the store. (`match_sha256` embeds the tree OID and is never compared across trees.)
- **No current-repository deferral**, no X/exempt owner, no allowlist/baseline beyond the transition guard (deleted by M6).
- **Ownership re-derivation (post-squad, 2026-08-23)**: three classes moved across the methodology §1.2 transition
  boundaries after live-code checks, and §1.2 was re-derived accordingly — OC-03 (`.kittify/config.yaml`
  `doctrine.org.packs` block, the CR-04 seam) M1→**M2**; OC-41 (`src/doctrine/skills/**` pathnames) M4→**M2** as a
  `relocate` of the skills tree (skill-ID content OC-09 stays M4); CR-07 introduction M3→**M2** (code literals + dual-root
  reader; M3 moves the data). CR-01 sources are the OC-02 `governance:`→`doctrine:` rows of `charter.yaml`; CR-05 sources
  are the OC-19 URN producer rows. Sums: M1 302 · M2 13,344 · M3 111 · M4 564 · M5 34,729 · M6 0 = 49,050.
- **Rollback ladder** (methodology §4.3): fix forward or revert before landing; revert one wave before dependents land;
  reverse the landed suffix or forward-fix afterwards; M3/M4 restore verified backups; M6 revert valid only before 4.0
  publication; release-level rollback after.
- **Edit footprint vs ownership**: a wave's `owned_files_or_surfaces`/`retires_oc` columns name what the wave is
  the **primary owner of and must retire**, not a strict whitelist of every path the wave's diff may touch. A wave
  routinely edits rows another wave primarily owns to satisfy its own CR control/product registration or link
  closure — e.g. M1 implements the CR-01 3.x reader in `src/charter/org_pack_discovery.py:201` (an OC-17/M2-owned
  file) and re-points the 43 referrers of `docs/context/doctrine.md`, some of which live in `src/doctrine/skills/`
  (OC-09/M4), `tests/**` (OC-24/M2), and `docs/adr/**`/`docs/**` (OC-29/OC-32/M5). These cross-owned edits are
  legitimate when they are shrink-only under the wave's own guard, registered against the wave's own CR (never a
  duplicate ownership claim), or explicitly carried forward for the owning wave to retire later — never a
  free-standing rewrite of another wave's scope. Do not review a wave's diff against `owned_files_or_surfaces` as a
  strict edit whitelist; a diff outside it that meets one of the three conditions above is expected, not a defect,
  and flagging it as one produces false dangling-link/whitelist-review findings.

## 1. Wave entries (T013)

### M1 — `charter-authority-flip`

| Field | Value |
|---|---|
| `slug` | `charter-authority-flip` |
| `purpose` | Make the accepted ADR effective: record the override/canon in the complete Charter/glossary authority graph through the owning writers, cut over the selection key, arm the transition guard (I1). |
| `depends_on` | none (I0 verified on the wave's base) |
| `inputs` | accepted ADR; `inventory.md` OC-01/02/40 + CR-01 (sources = OC-02 `charter.yaml:2,19` `governance:`→`doctrine:` rows; reader `src/charter/org_pack_discovery.py:201`); `contracts/adr-content-contract.md` §3 (override text) §6 (per-artifact owner map) §8 (guard); `issue-matrix.json` `#2727` (bound, §3.1); `methodology.md` §1.3(1), §2.1, §3.2; the 43 referrers of `docs/context/doctrine.md` outside the archive (`docs/api/**` generated, `src/doctrine/skills/**`, tests, docs) |
| `outputs` | `charter.md` + human-owned `charter.yaml` partitions curated; activation partition via `charter activate`/`deactivate` only; `interview/answers.yaml` migrated by `scripts/migrate_charter_interview_answers.py` (token-literal-free: frozen replacements built from numeric bytes) + hardened serializer; `charter.yaml` catalog/metadata regenerated (M1 pins which `charter generate` entry path runs — `compiler.py:515-516` section update, not the `compiler.py:725` whole-document save — and verifies direct partitions byte-stable); `context-state.json` refreshed or verified no-op; `synthesis-manifest.yaml` resynthesised or verified no-op; `.kittify/charter/graph.yml` deleted after repeated zero-consumer proof; `docs/context/doctrine.md` → `docs/context/charter.md` + `.kittify/glossaries/spec_kitty_core.yaml` + `packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml` + active referrers (one transaction; parity predicate = term set + definitions + aliases keyed by term ID across the three authorities + link closure); referrers of `docs/context/doctrine.md` re-pointed (generated `docs/api/**` via their generators); `governance.doctrine` → `governance.charter` + 3.x reader (CR-01); guard baseline store (untracked or inside M1's own `kitty-specs/` mission dir) + `test_transition_guard_shrink_only` armed last; wave `occurrence_map` incl. carried-forward rows |
| `base_capture` | §0; opening guard baseline = M1's own opening manifest (rule-table re-derivation of the M1 tip; the frozen-base `3631531b…` is planning evidence) |
| `occurrence_map` | rows of OC-01 (221), OC-02 (80), OC-40 (1) = **302** (`inventory.md` member sets); carried-forward (not M1-owned): generated `charter.yaml` `catalog` summaries from `src/charter/compiler.py:1449` (M2), pack-source summaries (M4), `activated_directives: 018-doctrine-versioning-requirement` (M4/CR-08) |
| `retires_oc` | OC-01, OC-02, OC-40 |
| `introduces_compatibility` | CR-01 (`governance.doctrine`, budget 3) |
| `removes_compatibility` | none |
| `owned_files_or_surfaces` | `.kittify/charter/**` (via owners), `.kittify/config.yaml` activation keys via engine (its `doctrine.org.packs` block is OC-03/M2), `.kittify/glossaries/spec_kitty_core.yaml`, `docs/context/charter.md` (renamed from `doctrine.md`), `packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml`, active glossary referrers + referrers of `docs/context/doctrine.md`, `scripts/migrate_charter_interview_answers.py`, serializer round-trip code, guard baseline store + guard test |
| `tests` | `test_charter_owner_map_executed`, `test_glossary_authority_parity` (predicate above), `test_answers_migration_preserves_unknown_keys_and_all_answers`, `test_answers_migration_preserves_selected_assets_and_template_set`, `test_answers_migration_changes_only_frozen_target_bytes`, `test_answers_migration_failure_restores_preimage`, `test_interview_serializer_round_trips_extended_answers` (+ deletion/default-reset/empty-`selected_tactics` mutation must fail), `test_governance_doctrine_key_warns_and_maps`, `test_governance_charter_key_canonical`, `test_transition_guard_shrink_only`, `test_archive_root_byte_identical` |
| `merge_gate` | every Charter artifact has its mapped owner action or verified no-op and regenerated hashes match; three-authority glossary parity holds — divergence rolls back all three; no M1-owned row remains at the closing audit except CR-01 products ≤ 3 + control (carried-forward later-wave rows listed); guard armed; zero operator questions raised; archive gate |
| `rollback` | revert the wave before M2 lands: restore the authority graph (owner workflows re-run from the pre-M1 sources), restore `answers.yaml` preimage from backup, un-arm the guard; after M2 lands → reverse suffix |
| `change_mode` | `bulk_edit` |
| `invariant_after` | **I1** |
| `local_design_questions` | **0** (§3.1 dry run) |

### M2 — `charter-code-topology`

| Field | Value |
|---|---|
| `slug` | `charter-code-topology` |
| `purpose` | Freeze the exhaustive internal+public topology map, then merge/relocate `src/doctrine/**` into collision-free `src/charter/**` and rename every symbol/import/test/fixture/build hook/CLI/serialized/API/workflow/metadata coordinate (I2). |
| `depends_on` | M1 (I1 verified on M2's base) |
| `inputs` | I1 tree; `inventory.md` OC-03, OC-12…OC-25, OC-27, OC-28, OC-41/42/43/44/48 + CR-02…CR-07; `contracts/operator-surface-map-schema.md` (incl. the two-module split rule — `src/charter/offering/` + `src/charter/activation/` — collision set, `files("doctrine")` sites, `.kittify/doctrine` code literals, skills-tree relocate rows, dormant-manifest row, nested CLI routes + `charter mission-type` collision); ADR §5 fixed seams; `methodology.md` §1.3(2), §3.3; live gates `tests/architectural/test_runtime_charter_doctrine_boundary.py`, `test_charter_sole_door_resolver_imports.py`, `test_charter_facades_reexport_doctrine.py`, `test_shared_package_boundary.py`, `tests/architectural/test_layer_rules.py` (layer-chain literal `["kernel","doctrine","charter",...]`, to be re-homed), `tests/architectural/test_kernel_no_doctrine_import.py` (to be re-homed); `src/specify_cli/skills/registry.py:44,60,67`, `pyproject.toml:149,180-185`, `.github/workflows/release.yml:210-243`, `tests/doctrine/test_hatch_build.py` |
| `outputs` | frozen `canonical-operator-surface-map.md` (`MAP-###` rows, every collision `merge-existing`/`relocate`, the two module names/boundary fixed) + `canonical-cli-route-map.md` (sorted `surface_kind=cli` projection incl. nested routes, map hash); `src/doctrine/**` (the pure offer catalogue) split into **`src/charter/offering/`** and the current charter activation code (activation_engine, cascade, kind_vocabulary, etc.) into **`src/charter/activation/`** — two full modules, dependency direction preserved (`offering` MUST NOT import `activation`, C-004; `activation` MAY import `offering`); `tests/architectural/test_layer_rules.py` and `test_kernel_no_doctrine_import.py` re-homed into M2's gate set (layer-chain literal updated — the `doctrine` node is replaced by the intra-charter split); a NEW dedicated intra-package AST gate enforcing `charter.offering` must not import `charter.activation`, shipped as a hard M2 exit criterion; skills tree relocated (OC-41 pathnames; IDs untouched → M4) with registry/wheel/release-gate retargets; every `.kittify/doctrine` code literal renamed + dual-root reader/migrator (CR-07); renamed CLI group/subcommands/help/errors, tracker ownership flag/field/output, `charter_packs.org.packs` key (`.kittify/config.yaml` block OC-03 + reader/writer), `charter:<kind>:<id>` URN (producer `doctrine_synthesizer/apply.py:409,663`), package/distribution/wheel metadata, generated manifests, CI workflows, scripts, root config, tests; live architectural baselines/allowlists **retargeted** (never deleted); dormant `spec-kitty-doctrine` manifest disposed per its map row; CR-02…CR-07 products + controls; wave `occurrence_map` incl. carried-forward M3/M4/M5 values inside M2-owned generated manifests |
| `base_capture` | §0; guard baseline = M1 closing manifest |
| `occurrence_map` | OC-03 2 · OC-12 633 · OC-13 40 · OC-14 56 · OC-15 48 · OC-16 815 · OC-17 1,657 · OC-18 54 · OC-19 312 · OC-20 413 · OC-21 110 · OC-22 641 · OC-23 1,566 · OC-24 6,076 · OC-25 173 · OC-27 51 · OC-28 67 · OC-41 83 · OC-42 181 · OC-43 332 · OC-44 30 · OC-48 4 = **13,344** |
| `retires_oc` | OC-03, OC-12, OC-13, OC-14, OC-15, OC-16, OC-17, OC-18, OC-19, OC-20, OC-21, OC-22, OC-23, OC-24, OC-25, OC-27, OC-28, OC-41, OC-42, OC-43, OC-44, OC-48 |
| `introduces_compatibility` | CR-02 (CLI group, 10), CR-03 (tracker mode, 6), CR-04 (`doctrine.org.packs`, 3), CR-05 (URN prefix, 4), CR-06 (module-only import shim, 8), CR-07 (`.kittify/doctrine/` dual-root reader/migrator, 4 — introduced here, exercised by M3's data move) |
| `removes_compatibility` | none |
| `owned_files_or_surfaces` | `src/doctrine/**` (split into `src/charter/offering/` + `src/charter/activation/`; skills tree relocated), `src/charter/**`, `src/specify_cli/**` consumers (CLI, tracker, doctrine modules, upgrade, runtime, dossier, skills registry), `src/kernel/**`, `src/runtime/**`, `src/glossary/**`, `src/mission_runtime/**`, `tests/**` (code, architectural gates renamed, fixtures/baselines/allowlists retargeted, incl. `tests/architectural/test_layer_rules.py` + `test_kernel_no_doctrine_import.py` re-homed and the new intra-package offering↛activation AST gate), `.github/workflows/**`, `scripts/**`, `pyproject.toml`/`ruff.toml`/`pytest.ini`/`.gitignore`/markdownlint/speedup workflow, `src/doctrine/pyproject.toml` + `hatch_build.py` (explicit delete-vs-rename row), generated manifests (`_completion_manifest.json`, `.kittify/agent_profiles_manifest.json`), `.kittify/config.yaml` `doctrine.org.packs` block (OC-03), the two map files |
| `tests` | `test_topology_map_set_equality_and_closure`, `test_cli_route_map_set_equal_and_canonical`, `test_doctrine_group_hidden_alias_warns`, `test_charter_group_canonical_routes`, `test_tracker_doctrine_mode_alias_warns`, `test_tracker_ownership_mode_canonical`, `test_org_pack_config_doctrine_key_warns`, `test_urn_doctrine_prefix_parsed_with_warning`, `test_urn_charter_prefix_canonical`, `test_doctrine_import_shim_warns`, `test_charter_api_is_canonical_surface`, `test_old_root_read_warns_and_migrates` (reader part), `test_serialized_surfaces_canonical_writers`, `test_repo_ops_canonical`, renamed boundary gates green, `test_layer_rules.py`/`test_kernel_no_doctrine_import.py` green post-re-home, **new** `test_charter_offering_does_not_import_activation` (intra-package AST gate, hard M2 exit criterion), wheel/import/build closure per dependency slice, full `tests/architectural/` sweep, `test_transition_guard_shrink_only`, `test_archive_root_byte_identical` |
| `merge_gate` | map + CLI projection set-equal to every M2-owned manifest hit and every discovered producer/consumer, approved **before the first source edit**; no M2-owned (or M1-owned) live executable/code content hit or matching pathname outside registered CR-02…07 products at the closing audit (later-wave rows carried forward and listed); `src/doctrine/` directory absent; boundary gates green under the new names; the new `charter.offering` must-not-import `charter.activation` AST gate green (hard exit criterion, not a CR-budgeted exception); CR products within budget; archive gate |
| `rollback` | before M3 lands: revert by dependency slice (newest slice first), restoring import/build closure at each step; after M3+ lands: reverse suffix or forward-fix |
| `change_mode` | `bulk_edit` |
| `invariant_after` | **I2** |
| `local_design_questions` | **1 bounded, pre-edit**: approval of the complete topology map + CLI projection (§3.2); cannot change scope, order, or the terminal zero rule |

### M3 — `charter-packs-source`

| Field | Value |
|---|---|
| `slug` | `charter-packs-source` |
| `purpose` | Move project overlays/packs from `.kittify/doctrine/` to `.kittify/charter-packs/` with data preservation; canonical writers use only the new root; completed migration has no old root (I3). |
| `depends_on` | M2 |
| `inputs` | I2 tree (dual-root reader/migrator CR-07 already present from M2); `inventory.md` OC-04/08/45; ADR §5 (Charter Pack offer root), R8; `methodology.md` §1.3(3), §3.3, §4.4 |
| `outputs` | `.kittify/charter-packs/` canonical root with verified migrated data (fixtures/projects); built-in/internal pack structure files (`pack.yaml`, `pack-manifest`, `pack.md`, `*.graph.yaml`, `packs/internal`) canonical; CR-07 reader/migrator exercised and its data-move tests green; preflight manifest + backup + verification evidence; wave `occurrence_map` |
| `base_capture` | §0; guard baseline = M2 closing manifest |
| `occurrence_map` | OC-04 55 · OC-08 42 · OC-45 14 = **111** |
| `retires_oc` | OC-04, OC-08, OC-45 |
| `introduces_compatibility` | none (CR-07 is introduced by M2; M3 exercises it) |
| `removes_compatibility` | none |
| `owned_files_or_surfaces` | `.kittify/doctrine/**` → `.kittify/charter-packs/**`, `.kittify/overrides/**`, `packs/built-in/*.graph.yaml`, `packs/built-in/pack*.{yaml,md}`, `packs/built-in/assets/**`, `packs/internal/**`, overlay readers/writers, migration code + fixtures |
| `tests` | `test_old_root_read_warns_and_migrates`, `test_completed_migration_has_no_old_root`, six migration cases (absent / identical / divergent / interruption / backup rollback / completed old-path absence), `test_transition_guard_shrink_only`, `test_archive_root_byte_identical` |
| `merge_gate` | completed fixtures/projects have no `.kittify/doctrine/` root; divergent destinations block with both originals intact; no M3-owned (or earlier-wave-owned) row remains except CR-07 products ≤ 4 + control (carried-forward later-wave rows listed); archive gate |
| `rollback` | restore the verified backup (content + mode); never overwrite divergent data; before M4 lands revert the wave; after → reverse suffix/forward-fix |
| `change_mode` | `bulk_edit` |
| `invariant_after` | **I3** |
| `local_design_questions` | **0** (migration rule fixed: absent → copy/move-verify-remove; identical → verify-remove; divergent → hard-fail; no runtime ledger) |

### M4 — `charter-agent-assets`

| Field | Value |
|---|---|
| `slug` | `charter-agent-assets` |
| `purpose` | Rename every source, generated, installed, shared, and override skill/profile/directive/prompt/agent asset and ID to the fixed canonical mapping; completed installation has no old-named path (I4). |
| `depends_on` | M3 |
| `inputs` | I3 tree (skills tree already relocated by M2 — OC-41 pathnames retired; IDs untouched); `inventory.md` OC-06/07/09/10/11/46 + CR-08; ADR §5 fixed seven-ID mapping + `doctrine-daphne`→`charter-daphne` + `018-doctrine-versioning-requirement`→`018-charter-versioning-requirement`; R9; `methodology.md` §1.3(4), §3.3 |
| `outputs` | canonical skill sources (`spk-charter-*`, `spk-charter-lifecycle`), profiles/directives/tactics/procedures/styleguides/toolguides/paradigms, built-in mission prompts/step contracts, host agent-dir command/prompt surfaces (`.claude/`, `.github/prompts/`, `.cursor/`, `.agents/skills/`, …), regenerated `docs/api/agent_profiles/**` + `docs/api/skills/**`; installed/shared/override copies migrated with preflight/backup/verify/conflict rule; 3.x ID alias routing table (CR-08); wave `occurrence_map` |
| `base_capture` | §0; guard baseline = M3 closing manifest |
| `occurrence_map` | OC-06 171 · OC-07 51 · OC-09 253 · OC-10 12 · OC-11 75 · OC-46 2 = **564** |
| `retires_oc` | OC-06, OC-07, OC-09, OC-10, OC-11, OC-46 |
| `introduces_compatibility` | CR-08 (skill/profile/directive ID aliases, budget 12) |
| `removes_compatibility` | none |
| `owned_files_or_surfaces` | skill sources inside the relocated canonical skill tree (IDs/content OC-09; the tree location is M2's), `packs/built-in/agent_profiles/**`, `packs/built-in/directives/**` (incl. the two renamed files, OC-46), tactics/procedures/styleguides/toolguides/paradigms, `packs/built-in/missions/**`, host agent dirs, `docs/api/agent_profiles|skills/**` (generated), installer/skills manifest, alias table; the `charter.yaml` activation ID `018-…` re-activated through `charter activate`/`deactivate` (carried forward from M1) |
| `tests` | `test_agent_asset_ids_fixed_mapping_and_no_old_installed_path`, `test_skill_id_alias_routes_with_warning`, `test_profile_directive_alias_routes_with_warning`, six migration cases for installed/shared/override assets, generated-docs freshness, `test_transition_guard_shrink_only`, `test_archive_root_byte_identical` |
| `merge_gate` | every ID/path from the fixed mapping only (no wildcard derivation); completed installations have no old asset path; generated API docs regenerated; no M4-owned (or earlier-wave-owned, incl. M1's carried-forward activation ID) row remains except CR-08 products ≤ 12 + control; archive gate |
| `rollback` | restore backups/aliases within 3.x; before M5 lands revert the wave; after → reverse suffix/forward-fix |
| `change_mode` | `bulk_edit` |
| `invariant_after` | **I4** |
| `local_design_questions` | **0** (mapping and migration rule fixed) |

### M5 — `charter-current-tree-prose`

| Field | Value |
|---|---|
| `slug` | `charter-current-tree-prose` |
| `purpose` | Rewrite/rename every remaining current-tree prose/history/ADR/docs/evidence occurrence, filename, and referrer outside `kitty-specs/`; regenerate serialized docs data; leave the archive byte-identical (I5). |
| `depends_on` | M4 |
| `inputs` | I4 tree; `inventory.md` OC-26/29/30/31/32/33/34/35/47/49 plus rows created after the frozen base that the rule tables assign to M5 (e.g. this program's ADR, OC-29); R10; `methodology.md` §1.3(5), §3.3 (M5 row), §3.5; `tests/architectural/test_marker_job_completeness.py:82-85` (reads `docs/reports/test-sanitation/**/raw/wp07-route-manifest.yaml`, OC-30); deferred operator decision `DM-01M0P6C8C7Q6SPBT412V39RPN0` (serialized historical records keyed to archive slugs / retired profile IDs — `.kittify/migrations/mission-state/quarantine/**`, `kitty-ops/*.jsonl`, `.kittify/missions/**/retrospective.yaml`) |
| `outputs` | canonical ADR bodies/titles/files under `docs/adr/**` (incl. `2026-08-22-2-…` and `2026-07-15-1-…`, renamed), docs prose/reference/guides/architecture/context/changelog, plans/investigations, `docs/reports/**` (test-sanitation census/dispositions), `research-outputs/**`, `kitty-ops/**`, `.kittify/memory|evidence|missions|migrations/**`, `metadata.yaml`, root docs (`AGENTS.md`, `CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`), renamed docs/history pathnames (OC-47/49) with every referrer updated; regenerated retrieval index/page inventory/ownership manifest/toc/redirect maps (OC-26) via their generators (`freshen_adr_inventory`, docs tooling); OC-30 `docs/reports/test-sanitation/**` (27,990 rows) is **rename-in-place of historical evidence** — its producer ran on a historical suite, `audit.py` there is code-in-prose, path citations inside it will point at M2-renamed tests by design; archive referrers re-cited by `mission_id`/mid8 or token-free path; serialized historical records per `DM-01M0P6C8C7Q6SPBT412V39RPN0` once resolved; wave `occurrence_map` |
| `base_capture` | §0; guard baseline = M4 closing manifest |
| `occurrence_map` | OC-26 611 · OC-29 815 · OC-30 27,990 · OC-31 2,960 · OC-32 1,660 · OC-33 284 · OC-34 320 · OC-35 14 · OC-47 72 · OC-49 3 = **34,729** |
| `retires_oc` | OC-26, OC-29, OC-30, OC-31, OC-32, OC-33, OC-34, OC-35, OC-47, OC-49 |
| `introduces_compatibility` | none (prose has no compatibility channel) |
| `removes_compatibility` | none |
| `owned_files_or_surfaces` | everything in `retires_oc` plus the generators' outputs; never any path under `kitty-specs/` |
| `tests` | `test_prose_history_closure_outside_archive`, `freshen_adr_inventory --check`, docs link/freshness/SEO gates with the link check scoped `:(exclude)kitty-specs/` (the archive cites renamed paths by design), `test_marker_job_completeness` (OC-30 consumer) green, `test_serialized_surfaces_canonical_writers` (docs-data part), `test_transition_guard_shrink_only`, `test_archive_root_byte_identical` |
| `merge_gate` | pre-edit rename/re-cite map + OC-30/OC-31 sampled-diff review approved **before the first prose edit** (new bounded gate, see below); no M5-owned (or earlier-wave-owned) row remains at the closing audit except recorded quotation-fidelity exclusions; no dangling renamed reference outside `kitty-specs/`; generated docs data fresh; archive gate in its §0 test form (`git diff --name-status $(git merge-base <target> <tip>) <tip> -- kitty-specs/` → only `A` entries under M5's own mission dir) |
| `rollback` | before M6 lands revert the wave (renames are reversible); after → forward-fix |
| `change_mode` | `bulk_edit` |
| `invariant_after` | **I5** |
| `local_design_questions` | **1 deferred operator decision** — `DM-01M0P6C8C7Q6SPBT412V39RPN0` (disposition of tracked serialized runtime records keyed to immutable archive slugs or retired profile IDs: exclude alongside `kitty-specs/` / untrack after backup / schema-aware rewrite); it is the **only** M5 question and must be resolved before M5 is specified; no history exemption beyond the fixed root otherwise; re-cite rule fixed |

**Quotation/homograph-fidelity rule.** M5's blind-rewrite rule applies to genuine occurrences of the retired term as
the *domain* word — it does not license distorting an external quotation or citation. Where `doctrine` appears
inside a quoted excerpt, a citation, or a historical record's title/body attributed to a source outside this
program (e.g. a quoted spec, RFC, book, or third-party text embedded in prose), M5 preserves it — quote-preserving
paraphrase-with-attribution, or exclude the passage from the rewrite scope with a recorded rationale — rather than
rewriting the source's words. This is distinct from the already design-accepted ADR-title anachronism (the
program's own prior-ADR titles/files are rewritten by design); it is specifically about fidelity to text this
program did not author. The exact-zero audit still requires the retired token to be zero at I6 for genuine
occurrences; a preserved quotation that must retain the literal token is handled as an M5 exclusion-with-rationale
row in the occurrence map, never as a silent skip.

**M5 pre-edit dry-run gate.** M5 (34,729 rows, including the 27,990-row OC-30 in-place rewrite) currently has no
pre-edit gate, unlike M2's bounded topology-map approval. M5 adds a mirrored bounded gate before its first prose
edit: a proposed rename/re-cite map (legacy path/title → canonical path/title, quotation-fidelity exclusions
flagged) plus a sampled-diff review over OC-30 and OC-31 (the two largest, highest-risk classes — historical
evidence rename-in-place and plans/investigations prose) — approved before the first edit lands, the same way M2's
map approval precedes M2's first source edit. This is a new bounded gate, not a design question: it cannot change
scope, order, or the terminal zero rule, and it does not add to M5's `local_design_questions` count above.

### M6 — `charter-compatibility-extinction`

| Field | Value |
|---|---|
| `slug` | `charter-compatibility-extinction` |
| `purpose` | Remove every compatibility alias/key/path/control/fixture/baseline/allowlist and transition-guard record, replace detector literals with numeric-byte construction, and prove both exact zero audits over `HEAD` with the single fixed `kitty-specs/` exclusion (I6; 4.0 boundary). |
| `depends_on` | M5 |
| `inputs` | I5 tree; CR registry (CR-01…CR-08 all `active`/`closed-no-channel`); every later-created product/control/tombstone coordinate from the M1–M5 wave-local audits; guard baseline store; `contracts/inventory-schema.md` terminal contract; `methodology.md` §2.3, §3.4 |
| `outputs` | no aliases/keys/routes/import shims/old-root reader-migrator/redirects/warnings/distribution aliases/compatibility fixtures/tombstones; the transition guard baseline store + allowlist/exception mechanics **that the program introduced** deleted (live architectural baselines/allowlists retargeted by M2 are untouched); negative tests rewritten with `bytes((100,111,99,116,114,105,110,101))`; `scripts/audit_retired_term_zero.py` (token-literal-free, toplevel-only, `:(top)` pathspec, `--full-tree`, symlink-target + normalised-content passes, `--commit <oid> --mode terminal --json -`, exit 0/1/2); external stdout attestation (toplevel, `git --version`, commit + tree OIDs, argv, raw rcs, output hashes, counts, result) for the final commit/tree under check marker `terminology-zero-current-tree`; **release row**: the check wired into `.github/workflows/ci-quality.yml` (job name `terminology-zero-current-tree`) and into `release.yml` before publish, registered as a required check on the protected branch, the 4.0 version bump + `CHANGELOG.md` breaking-change entry (3.x aliases removed), and the dormant-manifest disposition inherited from M2's map row; wave `occurrence_map` (zero frozen-base rows) |
| `base_capture` | §0; the closing audit is `mode=terminal` on the exact final commit; any tree change invalidates evidence and CI/release rerun it on the merge/publish result tree |
| `occurrence_map` | **0 frozen-base rows**; owned set = every later-created compatibility product/control coordinate (CR-01…CR-08 products, control records, fixtures, tombstones, transition fingerprints/baselines) + any surviving detector literal |
| `retires_oc` | none from the frozen base (all 44 populated OCs are retired by M1–M5) |
| `introduces_compatibility` | none |
| `removes_compatibility` | CR-01, CR-02, CR-03, CR-04, CR-05, CR-06, CR-07, CR-08 (each exactly once; state → `removed`) |
| `owned_files_or_surfaces` | CR product/control/fixture/tombstone files, alias tables, shim modules, old-root reader/migrator, redirect maps, guard baseline store, `tests/**` negative fixtures, `scripts/audit_retired_term_zero.py`, CI/release gate wiring for the check marker |
| `tests` | `test_no_compatibility_machinery_remains`, `test_content_audit_accepts_rc1_empty_only`, `test_content_audit_rejects_git_rc_gt1`, `test_path_audit_propagates_ls_tree_failure`, `test_symlink_target_audited`, `test_no_homoglyph_or_format_char_evasion`, `mutation_git_audit_failure_cannot_pass_zero`, `mutation_subdir_cwd_cannot_pass_zero`, `test_retired_token_absent_numeric_bytes`, `test_no_detector_literal_remains`, `test_archive_root_byte_identical` |
| `merge_gate` | `python scripts/audit_retired_term_zero.py --commit <final-commit-oid> --mode terminal --json -` run at the repository toplevel exits 0 (content raw rc 1 + empty stdout with `':(top)' ':(top,exclude)kitty-specs/'`; pathname raw rc 0 + zero matches after the `kitty-specs/` drop on `--full-tree`; symlink targets zero; normalised-content pass zero; exit 1 = hits, 2 = audit/git/input error incl. non-toplevel cwd); attestation binds the resolved commit + tree OIDs; required external check `terminology-zero-current-tree` on the merge/publish result tree — no earlier working-tree or parent-commit zero result authorizes merge/publication; an entrypoint that omits the fixed exclusion or adds any other fails; no program-introduced baseline/allowlist/skip/X survives; CR registry empty; archive gate |
| `rollback` | before 4.0 publication: Git revert of M6 (aliases return; I6 not claimable while either audit is nonzero); after publication: release-level rollback only; no in-tree exception may be added to pass the gate |
| `change_mode` | `bulk_edit` |
| `invariant_after` | **I6** |
| `local_design_questions` | **0** (no exception question) |

**Contingency note (operator decision: leave `DM-01M0P6C8` deferred).** M6's single-fixed-`kitty-specs/`-exclusion
terminal contract above is **not** a finalized exclusion set — it is contingent on M5's deferred operator decision
`DM-01M0P6C8C7Q6SPBT412V39RPN0` (disposition of tracked serialized runtime records outside `kitty-specs/`:
quarantine `status.events.jsonl`, `kitty-ops/*.jsonl`, `.kittify/missions/**/retrospective.yaml`). If that decision
resolves to Option 1 (exclude alongside `kitty-specs/`) or Option 3 (schema-aware rewrite), M6's terminal audit
contract (and this table's `purpose`/`merge_gate` fields) require a scoped re-author before I6 can be claimed;
Option 2 (untrack after backup) does not change the exclusion set. Do not treat I6's exclusion set as finalized
until `DM-01M0P6C8` resolves; tracked upstream in issue #3684.

## 2. Assignment tables (T014)

### 2.1 One row per OC — exactly one M1–M6 primary owner

Membership = all rows of `inventory-hits.tsv` (SHA-256 `3631531b…`) whose `occurrence_class_id` equals the OC;
counts, files and ID spans are `inventory.md` §3. `OC-05` and `OC-50` are declared ids with zero rows (unused placeholders).

| OC | S | Seam (short) | Rows | Files | ID span | Owner |
|---|---|---|---|---|---|---|
| OC-01 | S2 | glossary authorities (docs context, project YAML, built-in pack, contextive) | 221 | 8 | `H-C-000395`…`H-C-038599` | **M1** |
| OC-02 | S5 | Charter Bundle `.kittify/charter/*` | 80 | 4 | `H-C-000208`…`H-C-000287` | **M1** |
| OC-03 | S5 | `.kittify/config.yaml` `doctrine.org.packs` block (CR-04 seam; live check 2026-08-23) | 2 | 1 | `H-C-000288`…`H-C-000289` | **M2** (moved from the M1 default: the rows are the org-pack config seam, not the selection key — see §0) |
| OC-04 | S6 | project overlay root `.kittify/doctrine/**`, overrides | 55 | 13 | `H-C-000290`…`H-C-000683` | **M3** |
| OC-06 | S4 | built-in agent assets | 171 | 69 | `H-C-034988`…`H-C-035255` | **M4** |
| OC-07 | S4 | built-in mission prompts/step contracts | 51 | 22 | `H-C-035111`…`H-C-035161` | **M4** |
| OC-08 | S6 | pack structure/manifests/assets, `packs/internal` | 42 | 13 | `H-C-034980`…`H-C-035267` | **M3** |
| OC-09 | S4 | skill sources `src/doctrine/skills/**` | 253 | 35 | `H-C-038127`…`H-C-038379` | **M4** |
| OC-10 | S4 | host agent-dir prompts | 12 | 12 | `H-C-000001`…`H-C-000695` | **M4** |
| OC-11 | S8 | generated profile/skill API docs | 75 | 24 | `H-C-001525`…`H-C-001752` | **M4** |
| OC-12 | S1 | CLI routes/help/errors | 633 | 39 | `H-C-038733`…`H-C-039365` | **M2** |
| OC-13 | S10 | tracker ownership seam | 40 | 4 | `H-C-039896`…`H-C-039935` | **M2** |
| OC-14 | S7 | old package build/distribution | 56 | 2 | `H-C-037795`…`H-C-038034` | **M2** |
| OC-15 | S8 | old package schemas/templates | 48 | 23 | `H-C-038048`…`H-C-038454` | **M2** |
| OC-16 | S7 | `src/doctrine/**` code | 815 | 91 | `H-C-037301`…`H-C-038472` | **M2** |
| OC-17 | S7 | `src/charter/**` consumers | 1,657 | 95 | `H-C-035644`…`H-C-037300` | **M2** |
| OC-18 | S8 | generated manifests | 54 | 2 | `H-C-000202`…`H-C-038647` | **M2** |
| OC-19 | S7 | specify_cli doctrine modules | 312 | 27 | `H-C-038667`…`H-C-039646` | **M2** |
| OC-20 | S7 | other specify_cli consumers | 413 | 90 | `H-C-038648`…`H-C-040045` | **M2** |
| OC-21 | S7 | kernel/runtime/glossary/mission_runtime | 110 | 21 | `H-C-038473`…`H-C-038582` | **M2** |
| OC-22 | S7 | test fixtures/controls/baselines/allowlists | 641 | 28 | `H-C-040095`…`H-C-045206` | **M2** (control machinery itself deleted by M6 as later-created/retargeted coordinates) |
| OC-23 | S7 | architectural gate tests | 1,566 | 70 | `H-C-040082`…`H-C-041785` | **M2** |
| OC-24 | S7 | test code | 6,076 | 641 | `H-C-040046`…`H-C-048328` | **M2** |
| OC-25 | S9 | CI workflows | 173 | 13 | `H-C-000007`…`H-C-000179` | **M2** |
| OC-26 | S8 | serialized docs data (index, inventory, manifest, toc, redirects) | 611 | 9 | `H-C-001753`…`H-C-035595` | **M5** |
| OC-27 | S9 | scripts | 51 | 8 | `H-C-035570`…`H-C-035643` | **M2** |
| OC-28 | S9 | root build/lint/config metadata | 67 | 6 | `H-C-000180`…`H-C-035569` | **M2** |
| OC-29 | S3 | ADRs | 815 | 65 | `H-C-000710`…`H-C-001524` | **M5** |
| OC-30 | S3 | test-sanitation evidence reports | 27,990 | 33 | `H-C-006966`…`H-C-034955` | **M5** |
| OC-31 | S3 | plans/investigations | 2,960 | 190 | `H-C-004006`…`H-C-006965` | **M5** |
| OC-32 | S3 | docs prose | 1,660 | 115 | `H-C-001578`…`H-C-034957` | **M5** |
| OC-33 | S3 | research-outputs, kitty-ops | 284 | 51 | `H-C-034958`…`H-C-035559` | **M5** |
| OC-34 | S3 | memory/evidence/mission-state history | 320 | 28 | `H-C-000294`…`H-C-000632` | **M5** |
| OC-35 | S3 | root repository docs | 14 | 1 | `H-C-000696`…`H-C-000709` | **M5** |
| OC-40 | S2 | pathname `docs/context/doctrine.md` | 1 | 1 | `H-P-000040` | **M1** |
| OC-41 | S4 | skill source pathnames (`src/doctrine/skills/**` tree) | 83 | 83 | `H-P-000196`…`H-P-000278` | **M2** (moved from the M4 default: the tree is `doctrine` package data resolved by `src/specify_cli/skills/registry.py:44,60,67`, shipped by `pyproject.toml:180-185`, counted by `release.yml:226` — M2 relocates it; skill IDs/content OC-09 stay M4) |
| OC-42 | S7 | `src/doctrine/**` pathnames | 181 | 181 | `H-P-000100`…`H-P-000363` | **M2** |
| OC-43 | S7 | test pathnames | 332 | 332 | `H-P-000391`…`H-P-000722` | **M2** |
| OC-44 | S7 | code pathnames | 30 | 30 | `H-P-000097`…`H-P-000390` | **M2** |
| OC-45 | S6 | project overlay pathnames | 14 | 14 | `H-P-000004`…`H-P-000017` | **M3** |
| OC-46 | S4 | `doctrine-daphne`, `018-…` pathnames | 2 | 2 | `H-P-000094`…`H-P-000095` | **M4** |
| OC-47 | S3 | docs pathnames | 72 | 72 | `H-P-000021`…`H-P-000093` | **M5** |
| OC-48 | S9 | repo-ops pathnames | 4 | 4 | `H-P-000001`…`H-P-000096` | **M2** |
| OC-49 | S3 | history pathnames | 3 | 3 | `H-P-000018`…`H-P-000020` | **M5** |

Every owner equals the `inventory.md` default owner except OC-03 (M1→M2) and OC-41 (M4→M2), moved after the
2026-08-23 live-code check and re-derived in `methodology.md` §1.2 (§0 "Ownership re-derivation"). No row has an
external deferral or X/exempt owner.

### 2.2 One row per CR — source ownership, introduction, removal

Sources are pairwise disjoint (`inventory.md` §4, single TSV column); each source row keeps its OC's primary owner
(table 2.1) and funds at most one CR; `introduction_wave` equals that owner; later-created product/control/tombstone
coordinates are **distinct M6-removal work**, never duplicate ownership of the sources. No coordinate is double-owned
and no source is double-funded.

| CR | Legacy form → canonical target | Source OCs (rows) | Source owner = intro | Budget | Control record | Named tests | Removal |
|---|---|---|---|---|---|---|---|
| CR-01 | `governance.doctrine` → `governance.charter` (3.x reader warns) | OC-02 (`.kittify/charter/charter.yaml:2,19` `governance:`→`doctrine:` key; reader `src/charter/org_pack_discovery.py:201`) — re-sourced 2026-08-23; the TSV's CR-01 annotation on `.kittify/config.yaml` rows is superseded (those rows are CR-04) | M1 | 3 | registry row + warning assertion | `test_governance_doctrine_key_warns_and_maps`, `test_governance_charter_key_canonical` | M6 |
| CR-02 | `spec-kitty doctrine <sub>` → `spec-kitty charter …` (hidden alias group warns) | OC-12 (104) | M2 | 10 | hidden alias registration + warning test | `test_doctrine_group_hidden_alias_warns`, `test_charter_group_canonical_routes` | M6 |
| CR-03 | `--doctrine-mode`/`doctrine_mode`/tracker block → `--ownership-mode`/`ownership_mode`/ownership block | OC-12, OC-13 (56) | M2 | 6 | tracker alias table + warning test | `test_tracker_doctrine_mode_alias_warns`, `test_tracker_ownership_mode_canonical` | M6 |
| CR-04 | `doctrine.org.packs` → `charter_packs.org.packs` | OC-03 (`.kittify/config.yaml:28-36` block, 2) + OC-16, OC-17 (reader `src/doctrine/drg/org_pack_config.py:577`, writer `:464-481`, 50) — re-sourced 2026-08-23 | M2 | 3 | config-key alias table + warning test | `test_org_pack_config_doctrine_key_warns` | M6 |
| CR-05 | `doctrine:<kind>:<id>` → `charter:<kind>:<id>` | OC-19 producer rows `src/specify_cli/doctrine_synthesizer/apply.py:409,663` + OC-16 `drg/merge.py`, `drg/models.py` (the TSV's `src/charter/drg.py` annotation is superseded — that file has no `doctrine:` literal); external consumer `spec_kitty_events` conformance fixture named as an M2 map row with owner/milestone | M2 | 4 | URN parser alias + warning test | `test_urn_doctrine_prefix_parsed_with_warning`, `test_urn_charter_prefix_canonical` | M6 |
| CR-06 | `import doctrine`/`doctrine.api` → `src/charter/offering/` (module-only shim re-exports + DeprecationWarning; every `importlib.resources.files("doctrine")` site retargeted before the shim lands) | OC-16 (31) | M2 | 8 | shim module list + warning test | `test_doctrine_import_shim_warns`, `test_charter_api_is_canonical_surface` | M6 |
| CR-07 | `.kittify/doctrine/` → `.kittify/charter-packs/` (dual-root reader + migrator warns) | code-literal rows of OC-17/19/20 (66 files, e.g. `src/charter/_doctrine_paths.py:30`, `_doctrine_collect.py:243,348,564,1017`, `calibration/walker.py:365,413`, `mission_loader/command.py:258`, `bulk_edit/occurrence_map.py:57`, `cli/commands/doctrine.py:602`) — introduced by **M2**; the OC-04/OC-45 data rows are M3's move (re-sourced 2026-08-23) | M2 (exercised by M3) | 4 | old-root fixture + migration tests | `test_old_root_read_warns_and_migrates`, `test_completed_migration_has_no_old_root` | M6 |
| CR-08 | `spk-doctrine-*`/`spec-kitty-charter-doctrine`/`doctrine-daphne`/`018-doctrine-versioning-requirement` → `spk-charter-*`/`spk-charter-lifecycle`/`charter-daphne`/`018-charter-versioning-requirement` (alias routes + warns) | OC-06, OC-09, OC-41, OC-46 (365) | M4 | 12 | ID alias table + routing warning tests | `test_skill_id_alias_routes_with_warning`, `test_profile_directive_alias_routes_with_warning` | M6 |

Introduction lists: M1 {CR-01}; M2 {CR-02, CR-03, CR-04, CR-05, CR-06, CR-07}; M3 {}; M4 {CR-08}; M5 {}; M6 {} — each
CR once; each introduction wave equals its source rows' owner (CR-01 → OC-02/M1; CR-04 → OC-03/OC-16/OC-17/M2; CR-07 →
OC-17/19/20 code literals/M2). Removal list: M6 {CR-01…CR-08} — each CR once. State machine and rules:
`methodology.md` §2.2.

### 2.3 Arithmetic — disjoint union equals the manifest

| Wave | Owned OCs | Rows |
|---|---|---|
| M1 | OC-01, OC-02, OC-40 | 221 + 80 + 1 = **302** |
| M2 | OC-03, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 41, 42, 43, 44, 48 | 2 + 633 + 40 + 56 + 48 + 815 + 1,657 + 54 + 312 + 413 + 110 + 641 + 1,566 + 6,076 + 173 + 51 + 67 + 83 + 181 + 332 + 30 + 4 = **13,344** |
| M3 | OC-04, OC-08, OC-45 | 55 + 42 + 14 = **111** |
| M4 | OC-06, OC-07, OC-09, OC-10, OC-11, OC-46 | 171 + 51 + 253 + 12 + 75 + 2 = **564** |
| M5 | OC-26, 29, 30, 31, 32, 33, 34, 35, 47, 49 | 611 + 815 + 27,990 + 2,960 + 1,660 + 284 + 320 + 14 + 72 + 3 = **34,729** |
| M6 | none (frozen base) | **0** |
| **Union** | 44 populated OCs, each listed exactly once | **49,050** = 48,328 content + 722 pathname = all TSV rows |

Pairwise disjointness follows from each OC appearing in exactly one wave list above (checked by enumeration: 3 + 22 + 3
+ 6 + 10 + 0 = 44 = the number of populated classes in `inventory.md` §3). Per surface the union reproduces
`inventory.md` §2: S1 633 (M2) · S2 222 (M1) · S3 34,118 (M5) · S4 572 (OC-41 M2 83 + the rest M4 489) · S5 82 (OC-02 M1
80 + OC-03 M2 2) · S6 111 (M3) · S7 12,189 (M2) · S8 788 (OC-11 M4 75 + OC-15 M2 48 + OC-18 M2 54 + OC-26 M5 611) · S9
295 (M2) · S10 40 (M2). The partition is identical to `methodology.md` §1.2 (re-derived 2026-08-23: OC-03 M1→M2,
OC-41 M4→M2). Before that re-derivation the sums were 304 / 13,259 / 111 / 647 / 34,729 / 0 — the figures WP05 and the
mission review re-derived from the regenerated TSV; the TSV and its hash are unchanged.

### 2.4 Cross-wave input/output joins and merge gates

| Join | Producer → consumer | Artifact handed over | Gate at the handoff |
|---|---|---|---|
| ADR → M1 | WP01 → M1 | accepted ADR + `contracts/adr-content-contract.md` §6 owner map + override text | ADR `Accepted`, registered; M1 raises zero questions |
| `issue-matrix.json` `#2727` → M1 | WP04 → M1 | glossary-authority slice bound into M1 (§3.1); issue closure stays with the issue's owner | three-authority parity is one rollback gate; cannot be split or deferred |
| M1 → M2 | authority graph + guard baseline (M1 closing manifest) + M1's carried-forward list (generated `charter.yaml` rows owned by M2/M4) | I1 verified on M2's base; guard armed |
| M2 → M3 | canonical code topology incl. `src/charter/offering/` + `src/charter/activation/`, relocated skills tree, dual-root reader/migrator (CR-07 active, data still at the old root) | I2; map hash recorded; no M1/M2-owned live code hit outside CR-02…07; boundary gates green; offering↛activation AST gate green |
| M3 → M4 | canonical pack root; pack-structure files canonical | I3; no old root in completed fixtures |
| M4 → M5 | canonical asset IDs/paths; generated API docs fresh | I4; no old installed path |
| M5 → M6 | canonical prose/history outside the archive; CR registry all `active`/`closed-no-channel`; accumulated later-created product/control coordinates listed in M1–M5 occurrence maps; `DM-01M0P6C8C7Q6SPBT412V39RPN0` resolved and applied | I5; no pre-existing archive path changed |
| M6 → release | `scripts/audit_retired_term_zero.py` attestation (resolved final commit + tree OIDs, toplevel, git version); CI job `terminology-zero-current-tree` in `ci-quality.yml` + pre-publish step in `release.yml`; required-check registration; 4.0 version bump + `CHANGELOG.md` breaking-change entry | check `terminology-zero-current-tree` exit 0 on the merge/publish result tree; no earlier working-tree or parent-commit result authorizes publication |

Every wave's merge gate additionally includes `test_transition_guard_shrink_only` (baseline = previous wave's closing
manifest) and `test_archive_root_byte_identical` (§0 archive gate), and re-runs the inventory audits at its result tree.

## 3. Dry runs (T015)

### 3.1 M1 zero-decision dry run

Inputs consumed: ADR §3 override text (verbatim), §5 vocabulary, §6 owner map; `inventory.md` OC-01/02/03/40 rows;
`issue-matrix.json` `#2727`. Each Charter artifact maps to exactly one fixed action (`contracts/adr-content-contract.md`
§6) — no choice is left to the wave:

| Artifact / partition | Action in the dry run | Evidence produced |
|---|---|---|
| `.kittify/charter/charter.md` | direct curation by the Charter conversation (`charter generate` never overwrites it) | diff limited to terminology + override section; hash recorded |
| `charter.yaml` `governance` / `directives` / `overrides` | direct policy edit via the `charter_yaml_io` round-trip section contract | byte-stable non-target partitions |
| `charter.yaml` `activated_*` / `activated_kinds` / `mission_type_activations` | only `spec-kitty charter activate` / `deactivate` (activation engine, key set from `ACTIVATION_YAML_KEYS`); interview promotion/default seeding delegate to the same writer | engine log; no direct edit |
| `charter.yaml` `catalog` / `metadata` | update owning pack/profile/directive sources, then `spec-kitty charter generate` | regenerated partitions; direct partitions byte-stable |
| `interview/answers.yaml` | `scripts/migrate_charter_interview_answers.py` (backup outside the audited tree, frozen coordinate replacements only, parse before/after, temp+fsync+atomic rename, preimage retained until merge) then serializer round-trip hardening; `charter interview` resumes ownership only after the five named tests pass | preimage hash; semantic-preservation check |
| `context-state.json` | present? audit; hit → `charter context --action <a> --mark-loaded` per registered action; no hit → verified no-op | no-op record or refresh log |
| `synthesis-manifest.yaml` | inputs/manifest hit → update inputs, `charter synthesize`/`resynthesize`; else verified no-op | no-op record or manifest hash |
| `.kittify/charter/graph.yml` | repeat the frozen zero-consumer audit; zero → delete file + referrers as obsolete snapshot; a new consumer invalidates the dry run and must be added to the map before execution | consumer-audit output |
| glossary transaction | `docs/context/doctrine.md` → `docs/context/charter.md`, `.kittify/glossaries/spec_kitty_core.yaml`, `packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml`, active referrers — one commit, one semantic/hash/link parity gate; divergence rolls back all three; `#2727` consumed (closure stays with its owner) | parity report |
| selection key | `governance.doctrine` → `governance.charter` in `.kittify/charter/charter.yaml:2,19` (reader `src/charter/org_pack_discovery.py:201`); 3.x reader warns on the old key (CR-01, ≤ 3 products, control record) | CR-01 tests |
| referrers of `docs/context/doctrine.md` | 43 outside the archive re-pointed: generated `docs/api/**` by re-running their generators; the rest edited in place | link closure |
| generated partitions owned by later waves | `catalog` summaries emitted by `src/charter/compiler.py:1449` (M2), pack-source summaries (M4), `activated_directives: 018-doctrine-versioning-requirement` (M4/CR-08) → **carried forward**, listed in M1's occurrence map; not hand-edited | carried-forward list |
| guard | arm last: tree-independent per-path fingerprint (§0); baseline store untracked or inside M1's own `kitty-specs/` mission dir; baseline = M1's own opening manifest; `test_transition_guard_shrink_only` wired into the merge gate | baseline hash |
| `charter sync` | not a writer — not invoked as an owner | — |

Result: tracked authority state + glossary authorities + override + selection migration + guard produced with
**`local_design_questions = 0`** (the parity predicate, guard-store location, `charter generate` entry path, and
token-literal-free migration script are fixed above, not left to the wave); every artifact has an action or a verified
no-op; no M1-owned row (302) remains at the closing audit except CR-01 products; later-wave rows are carried forward.
Rollback: revert the wave; restore the answers preimage; un-arm the guard.

### 3.2 M2 bounded pre-edit topology-map dry run

1. Capture base; run the audits; derive the M2 occurrence map (13,344 frozen-base rows = table 2.3, plus any rows the
   rule tables assign to M2 at M2's tip, minus rows M1 already retired).
2. Build `canonical-operator-surface-map.md`: one `MAP-###` row per M2-owned OC/hit group with `surface_kind ∈
   {package, module, file, directory, symbol, import, test, fixture, build-hook, cli, serialized, api, event, workflow,
   distribution, wheel, metadata}`, exact `legacy_coordinate` → `canonical_coordinate`, `collision_disposition ∈ {none,
   merge-existing, relocate}` (never unresolved/TBD), complete producers/readers/writers/consumers, `compatibility ∈
   {none, 3x-warning-alias, 3x-read-migration, closed-no-channel}` + CR id, tests/build evidence/removal test, `owner=M2`,
   `removal_owner=M6` for compatibility rows. Mandatory rows: CLI group with every nested route (4 direct commands;
   `pack`/`org`/`mission-type`/`asset` subgroups; 3 `validate` routes) + `doctor` route + the `charter mission-type`
   collision disposition; `governance.doctrine` as an M1-owned cross-reference only; org-pack config (CR-04 seam),
   tracker block/flag/output, target URN (producer `doctrine_synthesizer/apply.py:409,663`; external `spec_kitty_events`
   fixture with owner/milestone), enums, JSON/event aliases, fixture/rekey flows; every private/public module/symbol/
   import under `src/doctrine/**`; the two-module split (`src/charter/offering/` = the pure offer catalogue,
   `src/charter/activation/` = the current charter activation code) and the enumerated collision set (`__init__.py`,
   `pack_paths.py`, `provenance.py`, `resolver.py`, `template_catalog.py`, `versioning.py`, `errors.py`,
   `exceptions.py`, `primitives.py`; `Directive`, `DoctrineService`, `canonical_yaml`) with the boundary gates renamed;
   every `importlib.resources.files("doctrine")` site; every `.kittify/doctrine` code literal + the dual-root reader
   (CR-07); the skills-tree relocate rows (registry, wheel artifacts, release count gate); live architectural
   baselines/allowlists as retargeted rows; exact `doctrine.api.__all__`, re-exports, factories/loaders/services and all
   consumers; `spec-kitty-doctrine` dormant manifest delete-vs-rename row and wheel-closure consumers;
   workflow/CI/script/generated-template/build-system coordinates; the `test_layer_rules.py` +
   `test_kernel_no_doctrine_import.py` re-home rows (updated layer-chain literal) and the new intra-package
   `charter.offering`-must-not-import-`charter.activation` AST gate as a mandatory map row, not an optional add-on.
3. Resolve every collision with the existing `src/charter/` aggregate to `merge-existing` (exact target module inside
   `src/charter/offering/` or `src/charter/activation/` / facade) or exact `relocate` — **before the first source
   edit**; unresolved rows block; the one-way import rule (`offering` MUST NOT import `activation`) and the renamed
   boundary gates, plus the new intra-package AST gate, must be green in the dry run.
4. Emit `canonical-cli-route-map.md` = sorted projection of `surface_kind=cli` rows with the authoritative map hash;
   must be set-equal to the CLI rows.
5. Prove set equality: map rows == M2 manifest hits == discovered producers/consumers.
6. Approval of the frozen map is M2's **only** local gate (`local_design_questions = 1`); it cannot change scope,
   order, or the terminal zero rule. Then edit by dependency slice with closure checks; CR-02…06 within budget; M2
   cannot close while any old live code/executable hit or matching pathname remains outside registered CR rows.

### 3.3 M3–M6 fixed gates (no design questions)

- **M3/M4**: preflight manifest → backup → absent destination: copy/move, verify, remove old; identical: verify, remove
  old; divergent: hard-fail with both originals intact until operator resolution; interruption before verification:
  restore backup, no completion marker; completion requires old-named root/path absent. Bounded migration evidence, not a
  runtime ledger (R8/R9; methodology §4.4).
- **M5**: no history exemption beyond the fixed `kitty-specs/` root, which it never edits or renames; re-cite rule for
  archive referrers; generated docs data regenerated; OC-30 rename-in-place; link check scoped outside the archive;
  filename/referrer closure. One deferred operator decision (`DM-01M0P6C8C7Q6SPBT412V39RPN0`, serialized historical
  records) must be resolved before M5 is specified.
- **M6**: no exception question; removes the complete CR/control/product/fixture set + the program's guard
  baseline/allowlist machinery (live architectural baselines untouched); numeric-byte negative tests; checked zero
  content/path/symlink/normalised audits (contract pathspec only, toplevel only) bound to the exact final commit/tree;
  CI/release rerun `scripts/audit_retired_term_zero.py` under `terminology-zero-current-tree` on the merge/publish
  result tree; attestation is external stdout, never a tracked write; the release row (CI/release wiring, required
  check, 4.0 bump + CHANGELOG) is part of M6's outputs.

## 4. Requirement coverage

| Requirement | Where satisfied |
|---|---|
| FR-009 deterministic inputs/outputs/dependencies/ownership/tests/gates/rollback | §1 (all 17 schema fields per wave), §2.4 |
| FR-010 M1 zero decisions; M2 bounded topology gate | §3.1, §3.2; `local_design_questions` rows |
| NFR-003 100% hits one owner; 100% missions complete contracts; zero unresolved cross-wave inputs | §2.1, §2.3, §1, §2.4 |
| SC-003 every hit once; every CR one introduction + M6 removal | §2.1–§2.3, §2.2 |
| SC-004 M1 dry run zero decisions; M2 pre-edit gate; I6 exact audits, no surviving exception machinery | §3, M6 entry |
| C-001 | planning artifact only; no rename performed |

Forbidden terminal states — X1/X2/X3, "user-visible only", supported-surface-only, immutable current-tree outside the fixed
root, runtime managed-path ledger — appear in this plan only as rejections.
