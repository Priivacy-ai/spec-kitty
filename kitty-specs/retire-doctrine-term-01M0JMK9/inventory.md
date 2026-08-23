# Inventory: Exhaustive Current-Tree Occurrence Inventory

**Mission**: `retire-doctrine-term-01M0JMK9` · **WP02** · **Contract**: `contracts/inventory-schema.md` · **Updated**: 2026-08-23

**Four-root regeneration (2026-08-23, `DM-01M0P6C8C7Q6SPBT412V39RPN0`).** This section reflects the inventory
regenerated at the same frozen base with the fixed exclusion set widened from the single `kitty-specs/` root
(`DM-01M0NMS9WPH33EPFCJQRTQVNSA`) to four fixed roots — `kitty-specs/`,
`.kittify/migrations/mission-state/quarantine/`, `kitty-ops/`, `.kittify/missions/` — per the operator's resolution
of `DM-01M0P6C8C7Q6SPBT412V39RPN0` (option 1: treat tracked serialized runtime records keyed to immutable archive
slugs or retired profile IDs as immutable historical records, amending `DM-01M0NMS9WPH33EPFCJQRTQVNSA`). The
regeneration used the §8 block below with `content_argv`/`pathname_audit` extended to four `:(exclude)<root>`
pathspecs / a four-root ls-tree prefix drop (the committed §8 block itself remains the frozen single-root
evidence for the original WP02/WP05 run — see the "Superseded-for-reproduction" note at §8). The regenerated
content count (**48,245**) and pathname count (**719**) were independently verified against the operator's
ground-truth figures before this section was written.

## 1. Frozen base, audits, reproduction

| Item | Value |
|---|---|
| `base_commit` (`target_tip`, `implementation-baseline.json`) | `2621a56d06b9ae4e7da07ee206879c30a4d8b363` |
| tree OID (`git rev-parse --verify <base>^{tree}`) | `26e6fdd2b8f0ee15c546bfac240a78ec154899f3` |
| content argv | `["git", "grep", "-a", "-i", "-n", "-o", "--column", "--full-name", "-z", "-e", "doctrine", "2621a56d06b9ae4e7da07ee206879c30a4d8b363", "--", ".", ":(exclude)kitty-specs/", ":(exclude).kittify/migrations/mission-state/quarantine/", ":(exclude)kitty-ops/", ":(exclude).kittify/missions/"]` |
| content raw rc / result | `0` / hits |
| content stdout SHA-256 | `6765e7527d698fff8a02f2f8b6a633fc8586fe15611a110eb420522920c9f59a` |
| content stderr SHA-256 (empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| pathname argv | `["git", "ls-tree", "-r", "-z", "--name-only", "2621a56d06b9ae4e7da07ee206879c30a4d8b363"]` (unchanged — the four-root drop is applied in-process after the raw ls-tree call, so this argv and its raw output are identical to the single-root run) |
| git version (this run) | `git version 2.43.0` — differs from the original WP02 run's recorded `2.52.0`; per the contract, the version is recorded on every reproduction and reconciled before comparing hashes. This regeneration's `git grep`/`ls-tree` NUL-framed output format matched byte-for-byte with the expected structural parse (self-tests §7 all PASS on this run), so the version difference did not affect the result |
| pathname raw rc | `0` (tracked paths 18256, unchanged) |
| pathname stdout SHA-256 | `0b2f3b782e72a9ae6d234057af16ad4a136709c1fee8418db5ba219568b3949c` (unchanged — see pathname argv note above) |
| pathname stderr SHA-256 (empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| **`inventory-hits.tsv` SHA-256** | **`d8a09ef14206381ca12c32641463468e954147509f4be7b46290ee9e33991c2c`** (supersedes the single-root `3631531b404cd379ce7b8d7a2dccb65cd7878f6cd65b95b922ae64d175013d2a`) |
| TSV bytes / rows | 9,106,281 / **48,964** (48,245 content + 719 pathname) |
| distinct paths with hits | 2,034 |
| reproduction command | `.venv/bin/python inventory-audit.py --base 2621a56d06b9ae4e7da07ee206879c30a4d8b363 --mode inventory --out inventory-hits.tsv --summary inventory-summary.json` (script = §8 block with `content_argv`/exclusion extended to the four fixed roots per the note above, run from the repo root with the mission dir as cwd-relative path) |
| self-tests | `… --selftest --base 2621a56d06b9ae4e7da07ee206879c30a4d8b363` → all PASS, `independent_hash_recompute_all_rows` PASS (48,964 rows) (§7) |

The TSV is **ephemeral evidence** (`DM-01M0NMSD60JYG7K7V5MJCKJ3P8`): generated into this directory, untracked via the
mission-local `.gitignore`, and pinned here by SHA-256 + counts. Set equality is proven by regenerating it from the
frozen base with the command above and matching the SHA-256/row counts byte-for-byte (WP05 repeats this independently).
Two independent processes produced byte-identical output; all 48,964 row hashes were recomputed by a second plain
implementation from the raw grep/ls-tree records (§7).

### Excluded-root orientation (non-contractual)

The four fixed exclusion roots (`kitty-specs/`, `.kittify/migrations/mission-state/quarantine/`, `kitty-ops/`,
`.kittify/missions/`; `DM-01M0NMS9WPH33EPFCJQRTQVNSA` amended by `DM-01M0P6C8C7Q6SPBT412V39RPN0`) are applied as
one `:(exclude)<root>` pathspec per root and as four ls-tree prefix drops. No pre-existing path under any of them
is edited or renamed by any wave; runtime may keep appending new records to the three non-archive roots. For
orientation only:

| Excluded root (not audited, not work) | Content records | Tracked paths | Pathnames containing the token |
|---|---|---|---|
| `kitty-specs/` | 39,167 | 10,936 | 1,070 |
| `.kittify/migrations/mission-state/quarantine/` | 54 | 13 | 3 |
| `kitty-ops/` | 22 | 346 | 0 |
| `.kittify/missions/` | 7 | 3 | 0 |
| **total** | **39,250** | **11,298** | **1,073** |

## 2. Manifest totals

| Kind | Rows |
|---|---|
| content | 48,245 |
| pathname | 719 |
| **total** | **48,964** |

| S | Category | Rows |
|---|---|---|
| S1 | CLI/operator routes | 633 |
| S2 | glossary/authority | 222 |
| S3 | current-tree prose/history | 34,032 |
| S4 | agent artifacts | 572 |
| S5 | Charter authority | 82 |
| S6 | packs/project overlays | 111 |
| S7 | code/build/test topology | 12,189 |
| S8 | serialized/workflow/generated | 788 |
| S9 | repository operations | 295 |
| S10 | tracker/ownership | 40 |

Max content `ordinal` observed: 1 (`-o --column` yields one record per match with a distinct column, so the
ordinal is always 1 on this tree; the field remains contractual and reproducible). Percent-encoding follows the contract's
unreserved set `[A-Za-z0-9._~-]` (and `%`) literally, so `/` appears as `%2F`; decoding is lossless.

## 3. Occurrence classes (rule-derived, ordered, first match wins, no catch-all)

Every row receives exactly one `OC-##` from the ordered predicate tables `CONTENT_RULES` / `PATHNAME_RULES` in the
embedded script (§8). Content rules apply to `kind=content`, pathname rules to `kind=pathname`. A row that matches no
rule is an audit error (there is no catch-all), so membership is exact and reconstructible: the member set of an OC is
**all TSV rows whose `occurrence_class_id` equals it**; the ID range below is the sorted span (ranges of different OCs
interleave because IDs follow the global `kind,path,line,column,ordinal` order). `Default owner` is the data-model §1
default; **primary ownership is assigned only in `stacked-plan.md` (WP04), which is the primary authority whenever it
differs from this column** (see OC-03, OC-41 below, corrected in the table to the post-squad reassignment — §4
amendment). Classes are split wherever the M1–M6 owner
or the semantic seam would differ (e.g. `src/doctrine/skills/**` (M4 assets) vs `src/doctrine/**` code (M2);
`packs/built-in/glossary_packs/**` (M1 glossary authority) vs other pack content (M3/M4)).

| OC | S | Default owner | Semantic seam / rule | Rows | Files | ID span | Examples |
|---|---|---|---|---|---|---|---|
| OC-01 | S2 | M1 | glossary authorities: docs context, project glossary YAML, built-in glossary pack, contextive data | 221 | 8 | `H-C-000395`…`H-C-038516` | `.kittify%2Fglossaries%2Fplanning-and-tracking.yaml` · `.kittify%2Fglossaries%2Fspec_kitty_core.yaml` |
| OC-02 | S5 | M1 | Charter Bundle authority: .kittify/charter/* (charter.md, charter.yaml, interview, graph.yml, synthesis) | 80 | 4 | `H-C-000208`…`H-C-000287` | `.kittify%2Fcharter%2Fcharter.md` · `.kittify%2Fcharter%2Fcharter.yaml` |
| OC-03 | S5 | M2 (rule default M1; reassigned post-squad — §4 amendment) | Charter selection/config seam: .kittify/config.yaml (governance.doctrine, org pack wiring) | 2 | 1 | `H-C-000288`…`H-C-000289` | `.kittify%2Fconfig.yaml` |
| OC-04 | S6 | M3 | project overlay root and overrides: .kittify/doctrine/**, .kittify/overrides/** | 55 | 13 | `H-C-000290`…`H-C-000622` | `.kittify%2Fdoctrine%2Fdirective%2FDIRECTIVE_terminus_retrospective_always_on.md` · `.kittify%2Fdoctrine%2Foverlays%2Fcalibration-documentation.yaml` |
| OC-06 | S4 | M4 | built-in agent assets: profiles, directives, tactics, procedures, styleguides, toolguides, paradigms | 171 | 69 | `H-C-034905`…`H-C-035172` | `packs%2Fbuilt-in%2Fagent_profiles%2FREADME.md` · `packs%2Fbuilt-in%2Fagent_profiles%2Fanalyst-annie.agent.yaml` |
| OC-07 | S4 | M4 | built-in mission prompts/governance profiles: packs/built-in/missions/** | 51 | 22 | `H-C-035028`…`H-C-035078` | `packs%2Fbuilt-in%2Fmissions%2FREADME.md` · `packs%2Fbuilt-in%2Fmissions%2Fbuilt_in_step_contracts%2Fresearch-scoping.step-contract.yaml` |
| OC-08 | S6 | M3 | built-in/internal pack structure: pack.yaml, pack-manifest, pack.md, *.graph.yaml, assets, packs/internal | 42 | 13 | `H-C-034897`…`H-C-035184` | `packs%2Fbuilt-in%2Fagent_profile.graph.yaml` · `packs%2Fbuilt-in%2Fassets%2FREADME.md` |
| OC-09 | S4 | M4 | skill sources: src/doctrine/skills/** (spk-doctrine-*, spec-kitty-charter-doctrine) | 253 | 35 | `H-C-038044`…`H-C-038296` | `src%2Fdoctrine%2Fskills%2FREADME.md` · `src%2Fdoctrine%2Fskills%2Fad-hoc-profile-load%2FSKILL.md` |
| OC-10 | S4 | M4 | agent command/prompt surfaces in host dirs (.claude, .github/prompts, .cursor, …) | 12 | 12 | `H-C-000001`…`H-C-000634` | `.agent%2Fworkflows%2Fspec-kitty-standalone.md` · `.amazonq%2Fprompts%2Fspec-kitty-standalone.md` |
| OC-11 | S8 | M4 | generated agent-profile/skill API docs: docs/api/agent_profiles/**, docs/api/skills/** | 75 | 24 | `H-C-001464`…`H-C-001691` | `docs%2Fapi%2Fagent_profiles%2Farchitect-alphonso.md` · `docs%2Fapi%2Fagent_profiles%2Fcurator-carla.md` |
| OC-12 | S1 | M2 | CLI routes/help/errors: src/specify_cli/cli/** (doctrine command group, charter subcommands, doctor, tracker flags) | 633 | 39 | `H-C-038650`…`H-C-039282` | `src%2Fspecify_cli%2Fcli%2Fcommands%2F__init__.py` · `src%2Fspecify_cli%2Fcli%2Fcommands%2F_cutover_doctor.py` |
| OC-13 | S10 | M2 | tracker ownership seam: src/specify_cli/tracker/** (doctrine mode/flags/fields) | 40 | 4 | `H-C-039813`…`H-C-039852` | `src%2Fspecify_cli%2Ftracker%2Fconfig.py` · `src%2Fspecify_cli%2Ftracker%2Flocal_service.py` |
| OC-14 | S7 | M2 | old source package distribution/build: src/doctrine/pyproject.toml, src/doctrine/hatch_build.py | 56 | 2 | `H-C-037712`…`H-C-037951` | `src%2Fdoctrine%2Fhatch_build.py` · `src%2Fdoctrine%2Fpyproject.toml` |
| OC-15 | S8 | M2 | old source package serialized schemas/templates: src/doctrine/schemas/**, src/doctrine/templates/** | 48 | 23 | `H-C-037965`…`H-C-038371` | `src%2Fdoctrine%2Fschemas%2FREADME.md` · `src%2Fdoctrine%2Fschemas%2Fagent-profile.schema.yaml` |
| OC-16 | S7 | M2 | old source package code/topology: src/doctrine/** (modules, symbols, imports, READMEs) | 815 | 91 | `H-C-037218`…`H-C-038389` | `src%2Fdoctrine%2FREADME.md` · `src%2Fdoctrine%2F__init__.py` |
| OC-17 | S7 | M2 | charter package consumers: src/charter/** (imports, facades, _doctrine_paths, doctrine_service_builder) | 1,657 | 95 | `H-C-035561`…`H-C-037217` | `src%2Fcharter%2FREADME.md` · `src%2Fcharter%2F__init__.py` |
| OC-18 | S8 | M2 | generated manifests: src/specify_cli/_completion_manifest.json, .kittify/agent_profiles_manifest.json | 54 | 2 | `H-C-000202`…`H-C-038564` | `.kittify%2Fagent_profiles_manifest.json` · `src%2Fspecify_cli%2F_completion_manifest.json` |
| OC-19 | S7 | M2 | specify_cli doctrine modules: doctrine/, doctrine_service_factory, doctrine_synthesizer, charter_runtime, drg_writers | 312 | 27 | `H-C-038584`…`H-C-039563` | `src%2Fspecify_cli%2Fcharter_runtime%2Ffreshness%2Fcomputer.py` · `src%2Fspecify_cli%2Fcharter_runtime%2Flint%2F__init__.py` |
| OC-20 | S7 | M2 | other specify_cli consumers: upgrade migrations, tool_surface, runtime, invocation, dossier, skills, … | 413 | 90 | `H-C-038565`…`H-C-039962` | `src%2Fspecify_cli%2Fbootstrap%2Fenv_file.py` · `src%2Fspecify_cli%2Fbulk_edit%2Foccurrence_map.py` |
| OC-21 | S7 | M2 | other packages: src/kernel, src/runtime, src/glossary, src/mission_runtime | 110 | 21 | `H-C-038390`…`H-C-038499` | `src%2Fglossary%2Fdrg_builder.py` · `src%2Fglossary%2Fentity_pages.py` |
| OC-22 | S7 | M2 | test fixtures/controls/baselines/allowlists (compatibility controls; M6 deletes the control machinery) | 641 | 28 | `H-C-040012`…`H-C-045123` | `tests%2Farchitectural%2F_baselines.yaml` · `tests%2Farchitectural%2F_fixtures%2Forg_packs%2Fexample_org%2Fdirectives%2Fsox-controls.directive.yaml` |
| OC-23 | S7 | M2 | architectural gate tests: tests/architectural/** (sole-door, census, wheel closure, dead-path sweeps) | 1,566 | 70 | `H-C-039999`…`H-C-041702` | `tests%2Farchitectural%2FREADME.md` · `tests%2Farchitectural%2F_dead_path_scan.py` |
| OC-24 | S7 | M2 | test code: tests/** (doctrine, charter, specify_cli, integration, …) | 6,076 | 641 | `H-C-039963`…`H-C-048245` | `tests%2FREADME.md` · `tests%2F_arch_shard_map.py` |
| OC-25 | S9 | M2 | CI workflows: .github/workflows/** | 173 | 13 | `H-C-000007`…`H-C-000179` | `.github%2Fworkflows%2Fcanonical-producer-lint.yml` · `.github%2Fworkflows%2Fci-quality.yml` |
| OC-26 | S8 | M5 | docs retrieval index, page inventory, ownership manifest, toc, redirect maps (serialized docs data) | 611 | 9 | `H-C-001692`…`H-C-035512` | `docs%2Fapi%2Ftoc.yml` · `docs%2Farchitecture%2F05_ownership_manifest.yaml` |
| OC-27 | S9 | M2 | scripts: scripts/** (schema generation, doctrine inventory scripts, docs tooling) | 51 | 8 | `H-C-035487`…`H-C-035560` | `scripts%2Fcheck_nfr_003_latency.py` · `scripts%2Fdocs%2Fplantuml_invoke.py` |
| OC-28 | S9 | M2 | root build/lint/config metadata: pyproject.toml, ruff.toml, pytest.ini, .gitignore, markdownlint, speedup workflow | 67 | 6 | `H-C-000180`…`H-C-035486` | `.gitignore` · `.kittify%2Ftest-suite-speedup-workflow.js` |
| OC-29 | S3 | M5 | ADRs: docs/adr/** | 815 | 65 | `H-C-000649`…`H-C-001463` | `docs%2Fadr%2F2.x%2F2026-02-23-1-doctrine-artifact-governance-model.md` · `docs%2Fadr%2F2.x%2F2026-02-23-2-living-glossary-context-and-curation-model.md` |
| OC-30 | S3 | M5 | test-sanitation evidence reports: docs/reports/** (census JSON, dispositions YAML) | 27,990 | 33 | `H-C-006905`…`H-C-034894` | `docs%2Freports%2Ftest-sanitation%2Fassertive-test-suite-sanitation-01KZME3P%2Faudit.py` · `docs%2Freports%2Ftest-sanitation%2Fassertive-test-suite-sanitation-01KZME3P%2Fdispositions%2FWP04.yaml` |
| OC-31 | S3 | M5 | plans/investigations/engineering notes: docs/plans/** | 2,960 | 190 | `H-C-003945`…`H-C-006904` | `docs%2Fplans%2F3-2-doc-publication%2F3-2-archive-migration-plan.md` · `docs%2Fplans%2F3-2-doc-publication%2F3-2-information-architecture.md` |
| OC-32 | S3 | M5 | docs prose (reference, guides, architecture, context, changelog, api command docs) | 1,660 | 115 | `H-C-001517`…`H-C-034896` | `docs%2Fapi%2Fbatch-api-contract.md` · `docs%2Fapi%2Fcharter-commands.md` |
| OC-33 | S3 | M5 | research outputs (`kitty-ops/**` was in scope; it is now a fixed exclusion root — its 22 rows left this class 2026-08-23, `DM-01M0P6C8`) | 262 | 36 | `H-C-035215`…`H-C-035476` | `research-outputs%2Fresearch%2Fdocling-graph-kitty-specs%2Fdata%2Fdocument-storage.json` · `research-outputs%2Fresearch%2Fdocling-graph-kitty-specs%2Fdata%2Froundtrip%2Fexports%2F000c8bca45c3d81615689518fcb0aaf1a000be17914a3a9acf048fc7d5226690%2F1-ffb8ef76e31fd879f754c61b51aa4e63224901117edae9f7bebebd8cf5118673.md` |
| OC-34 | S3 | M5 | project memory/evidence/mission-state history: .kittify/memory, evidence, metadata.yaml (`.kittify/missions/**` and `.kittify/migrations/mission-state/quarantine/**` were in scope; they are now fixed exclusion roots — their combined 61 rows left this class 2026-08-23, `DM-01M0P6C8`) | 259 | 21 | `H-C-000294`…`H-C-000571` | `.kittify%2Fevidence%2F01KTTCEAF0WTVAHYGND1D16R68%2Fevidence.md` · `.kittify%2Fevidence%2F01KTTCEAF0WTVAHYGND1D16R68%2Frecord.json` |
| OC-35 | S3 | M5 | root repository docs: AGENTS.md, CLAUDE.md, README.md, CONTRIBUTING.md, CHANGELOG.md | 14 | 1 | `H-C-000635`…`H-C-000648` | `AGENTS.md` |
| OC-40 | S2 | M1 | glossary authority pathname: docs/context/doctrine.md → docs/context/charter.md | 1 | 1 | `H-P-000037`…`H-P-000037` | `docs%2Fcontext%2Fdoctrine.md` |
| OC-41 | S4 | M2 (rule default M4; reassigned post-squad as a `relocate` — §4 amendment) | skill source pathnames: src/doctrine/skills/** | 83 | 83 | `H-P-000193`…`H-P-000275` | `src%2Fdoctrine%2Fskills%2FREADME.md` · `src%2Fdoctrine%2Fskills%2Fad-hoc-profile-load%2FSKILL.md` |
| OC-42 | S7 | M2 | old source package pathnames: src/doctrine/** | 181 | 181 | `H-P-000097`…`H-P-000360` | `src%2Fdoctrine%2FREADME.md` · `src%2Fdoctrine%2F__init__.py` |
| OC-43 | S7 | M2 | test pathnames: tests/** | 332 | 332 | `H-P-000388`…`H-P-000719` | `tests%2Farchitectural%2F_exemptions%2Fdoctrine.txt` · `tests%2Farchitectural%2Ffixtures%2Fdoctrine_boundary%2F__init__.py` |
| OC-44 | S7 | M2 | code pathnames: src/specify_cli/**, src/charter/**, src/kernel/**, src/runtime/** | 30 | 30 | `H-P-000094`…`H-P-000387` | `src%2Fcharter%2F_doctrine_paths.py` · `src%2Fcharter%2Faction_doctrine_bundle.py` |
| OC-45 | S6 | M3 | project overlay pathnames: .kittify/doctrine/** | 14 | 14 | `H-P-000004`…`H-P-000017` | `.kittify%2Fdoctrine%2Fdirective%2F.provenance%2FDIRECTIVE_evidence_logs_must_persist.yaml` · `.kittify%2Fdoctrine%2Fdirective%2F.provenance%2FDIRECTIVE_terminus_retrospective_always_on.yaml` |
| OC-46 | S4 | M4 | built-in agent asset pathnames: packs/built-in/** (doctrine-daphne, 018-doctrine-versioning-requirement) | 2 | 2 | `H-P-000091`…`H-P-000092` | `packs%2Fbuilt-in%2Fagent_profiles%2Fdoctrine-daphne.agent.yaml` · `packs%2Fbuilt-in%2Fdirectives%2F018-doctrine-versioning-requirement.directive.yaml` |
| OC-47 | S3 | M5 | docs pathnames: docs/** | 72 | 72 | `H-P-000018`…`H-P-000090` | `docs%2Fadr%2F2.x%2F2026-02-23-1-doctrine-artifact-governance-model.md` · `docs%2Fadr%2F3.x%2F2026-04-08-4-charter-doctrine-not-init-time.md` |
| OC-48 | S9 | M2 | repo-ops pathnames: .github/**, scripts/** | 4 | 4 | `H-P-000001`…`H-P-000093` | `.github%2Fworkflows%2Fdoctrine-charter-tests.yml` · `.github%2Fworkflows%2Fmodule-doctrine-fast.yml` |
| OC-49 | S3 | M5 | history pathnames: .kittify/migrations/**, .kittify/evidence/**, kitty-ops/**, research-outputs/** — **0 rows at this base** (all 3 frozen-base rows were under `.kittify/migrations/mission-state/quarantine/**`, now a fixed exclusion root, 2026-08-23 `DM-01M0P6C8`; the rule survives for any future non-excluded match, e.g. a `.kittify/migrations/` path outside the quarantine subtree or a `research-outputs/` pathname) | 0 | 0 | (none at this base) | (none at this base; formerly `.kittify%2Fmigrations%2Fmission-state%2Fquarantine%2Fc680177cc61d4709%2Fdoctrine-silence-guards-01KYFV7Q%2Fstatus.events.jsonl`) |

Notes on seams: OC-22 holds test fixtures, baselines and allowlists (e.g. `tests/doctrine/fixtures/content-manifest.json`,
`tests/architectural/_baselines.yaml`, `_inert_slots_baseline.yaml`) — compatibility *controls*: M2 renames/retargets them,
and M6 deletes the control machinery itself. OC-30 (`docs/reports/test-sanitation/**`) is 58% of all content rows
(census JSON/dispositions YAML of a past sanitation mission, outside the four fixed exclusion roots, hence M5 work). OC-26 is serialized
docs data regenerated by docs tooling (retrieval index, page inventory, ownership manifest, toc, redirect maps) — M5 owns
regeneration after prose rewrites. OC-11 is generated API docs for profiles/skills — regenerated by M4 after asset renames.

## 4. Compatibility-reservation candidates (3.x only; annotation, never exemption)

`compatibility_registry_id` annotates frozen-base source rows that fund one bounded 3.x alias/reader. Sources are
pairwise disjoint (ordered CR predicates, first match); each funds at most one CR; the source OC's default owner equals
the introduction wave. Later-created product/control coordinates (aliases, warnings, redirect paths, fixtures) are new
rows at the next wave-local audit and are **M6-removal work**, not duplicate ownership of these sources. Budgets are the
maximum number of product fingerprints a wave may introduce; M2 freezes exact coordinates in its topology map. Every CR
is removed by M6 (`removal_wave = M6`); I6 requires state `removed` and no surviving control/product hit.

| CR | Legacy form | Seam | Intro | Canonical target | Budget | Control record | Named tests | Source rows (files) | Source OCs |
|---|---|---|---|---|---|---|---|---|---|
| CR-01 | `governance.doctrine` | Charter selection key read by resolver/org-pack discovery | M1 | governance.charter (3.x reader warns on old key) | 3 | test registry row + warning assertion | `test_governance_doctrine_key_warns_and_maps`, `test_governance_charter_key_canonical` | 2 (1) raw-TSV tag; superseded — see §4 amendment | OC-03 raw-TSV tag; **CR-01's true source is OC-02 `.kittify/charter/charter.yaml:2,19`, and the raw OC-03 rows tagged here actually fund CR-04** — see §4 amendment (TSV bytes/hash/counts unchanged; only the ownership annotation is corrected) |
| CR-02 | `spec-kitty doctrine <subcommand>` | top-level CLI command group + eight subcommands | M2 | spec-kitty charter … (hidden alias group warns) | 10 | hidden alias registration + warning test | `test_doctrine_group_hidden_alias_warns`, `test_charter_group_canonical_routes` | 104 (1) | OC-12 |
| CR-03 | `--doctrine-mode / doctrine_mode / tracker doctrine block` | tracker ownership flag/field/output | M2 | --ownership-mode / ownership_mode / ownership block | 6 | tracker alias table + warning test | `test_tracker_doctrine_mode_alias_warns`, `test_tracker_ownership_mode_canonical` | 56 (5) | OC-12, OC-13 |
| CR-04 | `doctrine.org.packs` | org-pack config key | M2 | charter_packs.org.packs (3.x reader warns) | 3 | config-key alias table + warning test | `test_org_pack_config_doctrine_key_warns` | 50 (2) raw-TSV tag; **plus 2 (1) more (the OC-03 rows above) under the corrected model = 52 (3)** — see §4 amendment | OC-16, OC-17 raw-TSV tag; **corrected source also includes OC-03** (`.kittify/config.yaml:28-36` block) — see §4 amendment |
| CR-05 | `doctrine:<kind>:<id>` | DRG target URN prefix | M2 | charter:<kind>:<id> (3.x parser accepts+warns) | 4 | URN parser alias + warning test | `test_urn_doctrine_prefix_parsed_with_warning`, `test_urn_charter_prefix_canonical` | 105 (3) raw-TSV tag; superseded — see §4 amendment | OC-16, OC-17 raw-TSV tag; **corrected source is OC-16 (`drg/merge.py`, `drg/models.py`) + OC-19 producer rows `src/specify_cli/doctrine_synthesizer/apply.py:409,663`; `src/charter/drg.py` (OC-17, 62 rows) is dropped — it has no `doctrine:` literal** — see §4 amendment; exact re-sourced count is not yet re-derived from the TSV, `stacked-plan.md` §2.2 is authoritative for the composition |
| CR-06 | `import doctrine / doctrine.api` | Python package import path and public facade | M2 | src/charter/** modules (3.x shim package re-exports + DeprecationWarning) | 8 | shim module list + warning test | `test_doctrine_import_shim_warns`, `test_charter_api_is_canonical_surface` | 31 (2) | OC-16 |
| CR-07 | `.kittify/doctrine/` | project overlay root reader | M3 | .kittify/charter-packs/ (3.x old-root reader + migrator warns; removed M6) | 4 | old-root fixture + migration tests | `test_old_root_read_warns_and_migrates`, `test_completed_migration_has_no_old_root` | 18 (14) | OC-04, OC-45 |
| CR-08 | `spk-doctrine-* / spec-kitty-charter-doctrine / doctrine-daphne / 018-doctrine-versioning-requirement` | skill/profile/directive IDs | M4 | spk-charter-* / spk-charter-lifecycle / charter-daphne / 018-charter-versioning-requirement (3.x alias routes+warns) | 12 | ID alias table + routing warning tests | `test_skill_id_alias_routes_with_warning`, `test_profile_directive_alias_routes_with_warning` | 365 (85) | OC-06, OC-09, OC-41, OC-46 |

CR source membership = all TSV rows whose `compatibility_registry_id` equals the CR; exact file-level composition:

- **CR-01**: `.kittify%2Fconfig.yaml` (2) — raw-TSV tag, superseded: these 2 rows fund CR-04 under the corrected model; CR-01's true source (OC-02 `.kittify/charter/charter.yaml:2,19`) carries no raw CR tag in the TSV — see §4 amendment
- **CR-02**: `src%2Fspecify_cli%2Fcli%2Fcommands%2Fdoctrine.py` (104)
- **CR-03**: `src%2Fspecify_cli%2Ftracker%2Fconfig.py` (20), `src%2Fspecify_cli%2Fcli%2Fcommands%2Ftracker.py` (16), `src%2Fspecify_cli%2Ftracker%2Flocal_service.py` (11), `src%2Fspecify_cli%2Ftracker%2Fsaas_service.py` (8), `src%2Fspecify_cli%2Ftracker%2Fsaas_client.py` (1)
- **CR-04**: `src%2Fdoctrine%2Fdrg%2Forg_pack_config.py` (33), `src%2Fcharter%2Forg_pack_discovery.py` (17) — plus, under the corrected model, the 2 `.kittify%2Fconfig.yaml` rows listed under CR-01 above (see §4 amendment)
- **CR-05**: `src%2Fcharter%2Fdrg.py` (62), `src%2Fdoctrine%2Fdrg%2Fmerge.py` (30), `src%2Fdoctrine%2Fdrg%2Fmodels.py` (13) — raw-TSV tag, superseded: `drg.py`'s 62 rows are dropped (no `doctrine:` literal); the corrected source is `merge.py`/`models.py` plus `src/specify_cli/doctrine_synthesizer/apply.py:409,663` producer rows (OC-19), not yet re-derived from the TSV — see §4 amendment
- **CR-06**: `src%2Fdoctrine%2Fapi.py` (23), `src%2Fdoctrine%2F__init__.py` (8)
- **CR-07**: `.kittify%2Fdoctrine%2Fdirective%2FDIRECTIVE_terminus_retrospective_always_on.md` (2), `.kittify%2Fdoctrine%2Foverlays%2Fcalibration-documentation.yaml` (2), `.kittify%2Fdoctrine%2Foverlays%2Fcalibration-research.yaml` (2), `.kittify%2Fdoctrine%2Foverlays%2Fcalibration-software-dev.yaml` (2), `.kittify%2Fdoctrine%2Fdirective%2F.provenance%2FDIRECTIVE_evidence_logs_must_persist.yaml` (1), `.kittify%2Fdoctrine%2Fdirective%2F.provenance%2FDIRECTIVE_terminus_retrospective_always_on.yaml` (1), `.kittify%2Fdoctrine%2Fdirective%2FDIRECTIVE_evidence_logs_must_persist.md` (1), `.kittify%2Fdoctrine%2Foverlays%2Fcalibration-erp-custom.yaml` (1) … +6 more files (all rows with `compatibility_registry_id=CR-07` in the TSV)
- **CR-08**: `src%2Fdoctrine%2Fskills%2Fspec-kitty-charter-doctrine%2FSKILL.md` (89), `src%2Fdoctrine%2Fskills%2FREADME.md` (28), `src%2Fdoctrine%2Fskills%2Fspec-kitty-mission-system%2FSKILL.md` (23), `packs%2Fbuilt-in%2Fagent_profiles%2Fdoctrine-daphne.agent.yaml` (22), `src%2Fdoctrine%2Fskills%2Fspec-kitty-runtime-next%2FSKILL.md` (19), `src%2Fdoctrine%2Fskills%2Fspec-kitty-charter-doctrine%2Freferences%2Fdoctrine-artifact-structure.md` (15), `src%2Fdoctrine%2Fskills%2Fspec-kitty-spdd-reasons%2FSKILL.md` (12), `src%2Fdoctrine%2Fskills%2Fspk-meta-skill-map%2Freferences%2Fspk-skill-map.md` (11) … +77 more files (all rows with `compatibility_registry_id=CR-08` in the TSV)

State at frozen base: all `reserved`. No CR is proposed for M5 (prose) — prose has no compatibility channel — and none
for content rows of OC-01/OC-02 (glossary/Charter authority is cut over atomically by M1).

**Amendment (post-squad, 2026-08-23).** The whole-mission adversarial squad (`squad-findings-whole-mission.md`) checked
the CR seams against live code. `stacked-plan.md` §2.2 is the sole authority for CR source ownership; where it differs
from the TSV `compatibility_registry_id` annotation, the stacked plan supersedes the annotation (the TSV, its hash and
all counts are unchanged — the annotation column is orientation, never ownership). Re-sourcings: **CR-01**
`governance.doctrine` is the `governance:` → `doctrine:` key of `.kittify/charter/charter.yaml` (lines 2, 19; reader
`src/charter/org_pack_discovery.py:201`) = OC-02 rows (M1), not the `.kittify/config.yaml` rows; **CR-04**
`doctrine.org.packs` is the `.kittify/config.yaml` block (lines 28–36; reader `src/doctrine/drg/org_pack_config.py:577`,
writer `:464-481`) = OC-03 rows, whose owner is therefore M2 (the CR-04 seam), plus the OC-16/OC-17 reader/writer rows;
**CR-05** URN producer rows are `src/specify_cli/doctrine_synthesizer/apply.py:409,663` (OC-19), not `src/charter/drg.py`
(which has no `doctrine:` literal); **CR-07** is introduced by M2 (code literals of the old root, 66 files) and exercised by
M3 (data move). OC-41 (skill-tree pathnames) is owned by M2 as a `relocate`; OC-09 (skill-ID content) stays M4.

## 5. Scope statement

Every content occurrence and matching tracked pathname outside the four fixed exclusion roots at the frozen base is a
work item: internal code (`src/doctrine/**`, `src/charter/**`, `src/specify_cli/**`, `src/kernel/**`, `src/runtime/**`,
`src/glossary/**`), tests/fixtures/baselines, build/distribution metadata (`pyproject.toml`, `src/doctrine/pyproject.toml`,
`hatch_build.py`), CI/scripts, generated manifests, Charter/glossary sources, packs/overlays/skills/profiles/prompts/host
agent dirs, ADRs, docs, plans, reports, evidence, ops history, memory, and every matching filename. Nothing is
classified out; there is no X1/X2/X3, ignored, historical, internal, intentional, generated, or exempt value.
`kitty-specs/`, `.kittify/migrations/mission-state/quarantine/`, `kitty-ops/`, and `.kittify/missions/` are the four
fixed exclusion roots and no pre-existing path under any of them is edited or renamed (runtime may keep appending new
records to the latter three); the only other exclusion is Git object history outside `HEAD`.

## 6. Assignment-readiness statement

Classes are split wherever M1–M6 ownership would differ; each OC carries one semantic seam and one default owner, so
`stacked-plan.md` can assign every OC — and therefore every row — exactly once to M1…M6 with pairwise-disjoint owner
sets whose union is the complete manifest. A current-repository row cannot be externally deferred. If WP04 needs a finer
split (e.g. separating `tests/doctrine/**` from `tests/charter/**`), it adds a predicate above the current rule and the
row counts re-derive mechanically from the same TSV.

## 7. Self-tests (`--selftest`)

| Test | Result |
|---|---|
| `test_content_audit_accepts_rc1_empty_only` | PASS |
| `test_content_audit_rejects_git_rc_gt1` | PASS |
| `test_path_audit_propagates_ls_tree_failure` | PASS |
| `mutation_git_audit_failure_cannot_pass_zero` | PASS |
| `fixture_hostile_paths_and_repeated_mixed_case` | PASS |
| `fixture_two_process_byte_identical` | PASS |
| `test_inventory_match_sha256_byte_identical_reproduction` | PASS |
| `independent_hash_recompute_all_rows` | PASS (48,964 rows) |

Rerun 2026-08-23 against the four-fixed-root exclusion set (script extended per §8's amendment note); all eight
self-tests still PASS, with `independent_hash_recompute_all_rows` re-verifying all 48,964 rows byte-for-byte. The
mutation substitutes a failing git executable (`exit 3`) and an all-zero commit for each subprocess in both modes;
every combination raises `AuditError` before any zero count is recorded. The hostile-path fixture includes a colon+tab
filename, a non-ASCII filename, repeated mixed-case matches on one line, and an archived `kitty-specs/` file (excluded).
Terminal mode on the frozen base exits 1 (`hits`) with both counts reported; zero is unreachable until M6.

## 8. Audit procedure (verbatim; WP05 copies this block to regenerate)

**Superseded-for-reproduction annotation (post-squad, 2026-08-23).** This committed block is frozen evidence —
byte-identical to what WP02/WP05 ran to produce the **original single-root** `3631531b…` TSV and hash — and is
**not** rewritten here. It diverges from the hardened terminal-audit contract adopted after the whole-mission
squad's fold: this script's `content_argv`/`pathname_argv` use a cwd-relative pathspec (`"."`, `:(exclude)kitty-specs/`),
no `--full-tree`, and no toplevel-cwd guard. For **reproduction of the original single-root pinned evidence**,
this block remains authoritative and must be run unmodified. For the **M6 terminal zero audit** (and any wave-local
audit downstream of the fold), the hardened argv in `contracts/inventory-schema.md` (`:(top)` /
`:(top,exclude)<root>` per fixed exclusion root, `ls-tree --full-tree`, toplevel-only precondition, symlink-target
+ normalised-content passes) and the M6 entrypoint `scripts/audit_retired_term_zero.py` are authoritative instead
— never this block's argv.

**Four-root regeneration amendment (2026-08-23, `DM-01M0P6C8C7Q6SPBT412V39RPN0`).** §1's currently-pinned TSV
(SHA-256 `d8a09ef1…`, 48,964 rows) was produced from **this same block**, with only `content_argv` (three more
`:(exclude)<root>` pathspecs) and the pathname-audit drop predicate (three more prefix roots) extended to cover
the three newly-fixed exclusion roots the operator's resolution added alongside `kitty-specs/` —
`.kittify/migrations/mission-state/quarantine/`, `kitty-ops/`, `.kittify/missions/`. No other line of the script
changed; row IDs, `match_sha256` preimage construction, classification rule tables, and self-test logic are
identical to the block below. The extended script is not committed inline (the block below stays the frozen
single-root WP02/WP05 evidence per the annotation above); it is fully reconstructible by applying the same
three-pathspec/three-prefix extension used throughout this mission's contracts (`contracts/inventory-schema.md`
§"Fixed exclusion roots"). All eight self-tests (§7) re-ran PASS against the extended script, including
`independent_hash_recompute_all_rows` over all 48,964 rows.

```python
#!/usr/bin/env python3
"""Exhaustive current-tree occurrence inventory — mission retire-doctrine-term-01M0JMK9, WP02.

Implements `contracts/inventory-schema.md` exactly: two checked `subprocess.run` git calls (no shell
pipeline), fixed `kitty-specs/` exclusion root, rc/output consistency rules, NUL-safe parsing,
percent-encoded TSV paths, v1 domain-tagged `match_sha256`, deterministic sort/IDs, rule-derived
occurrence classes (no catch-all), compatibility-reservation annotation, and the named self-tests.

Usage:
  python inventory-audit.py --base <commit> --mode inventory --out inventory-hits.tsv --summary summary.json
  python inventory-audit.py --base <commit> --mode terminal
  python inventory-audit.py --selftest --base <commit>
Exit: 0 = ok (inventory) / zero (terminal); 1 = hits remain (terminal); 2 = audit/input/git error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
from collections import Counter, OrderedDict
from pathlib import Path

TOKEN = bytes((100, 111, 99, 116, 114, 105, 110, 101))
EXCLUDED_ROOT = b"kitty-specs/"
DOMAIN_TAG = b"spec-kitty.terminology-hit.sha256.v1\0"
HEADER = "hit_id\tkind\tpath\tline\tcolumn\tordinal\tmatch_sha256\toccurrence_class_id\tsurface_category\tcompatibility_registry_id\n"
_UNRESERVED = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._~-%")


class AuditError(Exception):
    """Audit/input/git error — distinct from 'hits remain'."""


# ----------------------------------------------------------------------------- git subprocesses
def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_argv(base_commit: str, git: str = "git") -> list[str]:
    return [git, "grep", "-a", "-i", "-n", "-o", "--column", "--full-name", "-z",
            "-e", TOKEN.decode("ascii"), base_commit, "--", ".", ":(exclude)kitty-specs/"]


def pathname_argv(base_commit: str, git: str = "git") -> list[str]:
    return [git, "ls-tree", "-r", "-z", "--name-only", base_commit]


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    except OSError as exc:  # missing/failing executable is an audit error
        raise AuditError(f"git executable failed: {exc}") from exc


def resolve_tree_oid(base_commit: str, cwd: Path, git: str = "git") -> str:
    proc = _run([git, "rev-parse", "--verify", f"{base_commit}^{{tree}}"], cwd)
    if proc.returncode != 0:
        raise AuditError(f"rev-parse --verify failed rc={proc.returncode}: {proc.stderr.decode(errors='replace').strip()}")
    oid = proc.stdout.strip().decode("ascii", errors="strict")
    if len(oid) not in (40, 64) or any(c not in "0123456789abcdef" for c in oid):
        raise AuditError(f"invalid tree OID {oid!r}")
    return oid


def content_audit(base_commit: str, cwd: Path, mode: str, git: str = "git") -> dict:
    """Return {'records': [(raw_path, line, column, match)], 'rc', 'argv', 'stdout_sha256', 'stderr_sha256'}."""
    argv = content_argv(base_commit, git)
    proc = _run(argv, cwd)
    if proc.stderr:
        sys.stderr.buffer.write(proc.stderr)  # pass captured stderr through unchanged
    rc = proc.returncode
    record = {"argv": argv, "rc": rc, "stdout_sha256": _sha(proc.stdout), "stderr_sha256": _sha(proc.stderr)}
    if rc < 0 or rc > 1:
        raise AuditError(f"content audit: git grep rc={rc} (audit error)")
    if rc == 1 and proc.stdout:
        raise AuditError("content audit: rc 1 with non-empty stdout (inconsistent)")
    if rc == 0 and not proc.stdout:
        raise AuditError("content audit: rc 0 with empty stdout (inconsistent)")
    records: list[tuple[bytes, int, int, bytes]] = []
    if rc == 0:
        prefix = base_commit.encode("ascii") + b":"
        raw = proc.stdout
        if not raw.endswith(b"\n"):
            raise AuditError("content audit: output truncated (no trailing LF)")
        for rec in raw[:-1].split(b"\n"):
            parts = rec.split(b"\0")
            if len(parts) != 4:
                raise AuditError(f"content audit: malformed record {rec[:80]!r}")
            revpath, line_b, col_b, match = parts
            if not revpath.startswith(prefix):
                raise AuditError(f"content audit: record lacks revision prefix {revpath[:80]!r}")
            path = revpath[len(prefix):]
            if not path or path.startswith(EXCLUDED_ROOT):
                raise AuditError(f"content audit: path violates exclusion/emptiness {path[:80]!r}")
            if not (line_b.isdigit() and col_b.isdigit()):
                raise AuditError(f"content audit: non-decimal coordinate {line_b!r}/{col_b!r}")
            line, col = int(line_b), int(col_b)
            if line < 1 or col < 1:
                raise AuditError("content audit: non-positive coordinate")
            if match.lower() != TOKEN:
                raise AuditError(f"content audit: match is not the token {match!r}")
            records.append((path, line, col, match))
    record["records"] = records
    record["mode_result"] = ("zero" if rc == 1 else "hits") if mode == "terminal" else "ok"
    return record


def pathname_audit(base_commit: str, cwd: Path, mode: str, git: str = "git") -> dict:
    argv = pathname_argv(base_commit, git)
    proc = _run(argv, cwd)
    if proc.stderr:
        sys.stderr.buffer.write(proc.stderr)
    rc = proc.returncode
    record = {"argv": argv, "rc": rc, "stdout_sha256": _sha(proc.stdout), "stderr_sha256": _sha(proc.stderr)}
    if rc != 0:
        raise AuditError(f"pathname audit: git ls-tree rc={rc} (audit error)")
    raw = proc.stdout
    if raw and not raw.endswith(b"\0"):
        raise AuditError("pathname audit: NUL framing missing")
    paths = raw.split(b"\0")[:-1] if raw else []
    excluded = [p for p in paths if p.startswith(EXCLUDED_ROOT)]
    remainder = [p for p in paths if not p.startswith(EXCLUDED_ROOT)]
    matches = [p for p in remainder if TOKEN in p.lower()]
    record.update({
        "tracked_paths": len(paths), "excluded_root_paths": len(excluded),
        "excluded_root_matches": sum(1 for p in excluded if TOKEN in p.lower()),
        "matches": matches,
        "mode_result": ("zero" if not matches else "hits") if mode == "terminal" else "ok",
    })
    return record


def excluded_root_content_orientation(base_commit: str, cwd: Path, git: str = "git") -> int:
    """Non-contractual orientation: content records inside the excluded root (separate, unaudited run)."""
    argv = [git, "grep", "-a", "-i", "-n", "-o", "--column", "--full-name", "-z", "-e", TOKEN.decode("ascii"),
            base_commit, "--", "kitty-specs/"]
    proc = _run(argv, cwd)
    if proc.returncode not in (0, 1):
        return -1
    return len([r for r in proc.stdout.split(b"\n") if r]) if proc.returncode == 0 else 0


# ----------------------------------------------------------------------------- rows
def percent_encode(path: bytes) -> str:
    return "".join(chr(b) if b in _UNRESERVED else f"%{b:02X}" for b in path)


def _lp(x: bytes) -> bytes:
    if len(x) > 2**64 - 1:
        raise AuditError("LP length overflow")
    return struct.pack(">Q", len(x)) + x


def _u64(v: int) -> bytes:
    if not (1 <= v <= 2**64 - 1):
        raise AuditError("coordinate out of range")
    return struct.pack(">Q", v)


def match_sha256(kind: str, tree_oid: str, raw_path: bytes, line: int | None, column: int | None,
                 ordinal: int | None, match: bytes) -> str:
    if kind == "content":
        fields = (_u64(line), _u64(column), _u64(ordinal), match)
    elif kind == "pathname":
        fields = (b"", b"", b"", b"")
    else:
        raise AuditError(f"bad kind {kind}")
    pre = DOMAIN_TAG + _lp(kind.encode("ascii")) + _lp(tree_oid.encode("ascii")) + _lp(raw_path)
    for f in fields:
        pre += _lp(f)
    return hashlib.sha256(pre).hexdigest()


# ----------------------------------------------------------------------------- classification
# (oc, surface, seam, default_owner) keyed by rule; predicates operate on (kind, path:str decoded latin-1).
def _sw(*prefixes: str):
    return lambda p: p.startswith(prefixes)


def _eq(*names: str):
    return lambda p: p in names


def _any(*preds):
    return lambda p: any(f(p) for f in preds)


AGENT_DIRS = (".agent/", ".agents/", ".amazonq/", ".augment/", ".claude/", ".cursor/", ".gemini/", ".kilocode/",
              ".kiro/", ".opencode/", ".qwen/", ".roo/", ".windsurf/", ".github/prompts/")
PACK_ASSET_DIRS = tuple(f"packs/built-in/{d}/" for d in
                        ("agent_profiles", "directives", "tactics", "procedures", "styleguides", "toolguides", "paradigms"))
ROOT_CONFIG = ("pyproject.toml", "ruff.toml", "pytest.ini", ".gitignore", ".markdownlint-cli2.jsonc", "uv.lock",
               ".kittify/test-suite-speedup-workflow.js", ".pre-commit-config.yaml", "Makefile", "mkdocs.yml")
ROOT_DOCS = ("AGENTS.md", "CLAUDE.md", "README.md", "CONTRIBUTING.md", "CHANGELOG.md", "SECURITY.md", "LICENSE")
DOCS_DATA = ("docs/development/3-2-docs-retrieval-index.yaml", "docs/development/3-2-page-inventory.yaml",
             "docs/architecture/05_ownership_manifest.yaml", "docs/architecture/explanation-toc.yml",
             "docs/development/toc.yml", "docs/api/toc.yml", "scripts/docs/redirect_map.yaml",
             "scripts/docs/redirect_baseline_urls.json", "scripts/docs/frontmatter_backfill_sections.yaml")

# Ordered rule table — first match wins; NO catch-all.
# Content rules (kind == content)
CONTENT_RULES: list[tuple[str, str, str, str, object]] = [
    ("OC-01", "S2", "glossary authorities: docs context, project glossary YAML, built-in glossary pack, contextive data", "M1",
     _any(_eq("docs/context/doctrine.md", ".kittify/traceability/contextive-map.yaml"),
          _sw(".kittify/glossaries/", "packs/built-in/glossary_packs/", "src/specify_cli/.contextive/"))),
    ("OC-02", "S5", "Charter Bundle authority: .kittify/charter/* (charter.md, charter.yaml, interview, graph.yml, synthesis)", "M1",
     _sw(".kittify/charter/")),
    ("OC-03", "S5", "Charter selection/config seam: .kittify/config.yaml (governance.doctrine, org pack wiring)", "M1",
     _eq(".kittify/config.yaml")),
    ("OC-04", "S6", "project overlay root and overrides: .kittify/doctrine/**, .kittify/overrides/**", "M3",
     _sw(".kittify/doctrine/", ".kittify/overrides/")),
    ("OC-05", "S2", "built-in glossary pack data (handled by OC-01)", "M1", lambda p: False),  # placeholder keeps IDs stable
    ("OC-06", "S4", "built-in agent assets: profiles, directives, tactics, procedures, styleguides, toolguides, paradigms", "M4",
     _sw(*PACK_ASSET_DIRS)),
    ("OC-07", "S4", "built-in mission prompts/governance profiles: packs/built-in/missions/**", "M4",
     _sw("packs/built-in/missions/")),
    ("OC-08", "S6", "built-in/internal pack structure: pack.yaml, pack-manifest, pack.md, *.graph.yaml, assets, packs/internal", "M3",
     _sw("packs/")),
    ("OC-09", "S4", "skill sources: src/doctrine/skills/** (spk-doctrine-*, spec-kitty-charter-doctrine)", "M4",
     _sw("src/doctrine/skills/")),
    ("OC-10", "S4", "agent command/prompt surfaces in host dirs (.claude, .github/prompts, .cursor, …)", "M4",
     _sw(*AGENT_DIRS)),
    ("OC-11", "S8", "generated agent-profile/skill API docs: docs/api/agent_profiles/**, docs/api/skills/**", "M4",
     _sw("docs/api/agent_profiles/", "docs/api/skills/")),
    ("OC-12", "S1", "CLI routes/help/errors: src/specify_cli/cli/** (doctrine command group, charter subcommands, doctor, tracker flags)", "M2",
     _sw("src/specify_cli/cli/")),
    ("OC-13", "S10", "tracker ownership seam: src/specify_cli/tracker/** (doctrine mode/flags/fields)", "M2",
     _sw("src/specify_cli/tracker/")),
    ("OC-14", "S7", "old source package distribution/build: src/doctrine/pyproject.toml, src/doctrine/hatch_build.py", "M2",
     _eq("src/doctrine/pyproject.toml", "src/doctrine/hatch_build.py")),
    ("OC-15", "S8", "old source package serialized schemas/templates: src/doctrine/schemas/**, src/doctrine/templates/**", "M2",
     _sw("src/doctrine/schemas/", "src/doctrine/templates/")),
    ("OC-16", "S7", "old source package code/topology: src/doctrine/** (modules, symbols, imports, READMEs)", "M2",
     _sw("src/doctrine/")),
    ("OC-17", "S7", "charter package consumers: src/charter/** (imports, facades, _doctrine_paths, doctrine_service_builder)", "M2",
     _sw("src/charter/")),
    ("OC-18", "S8", "generated manifests: src/specify_cli/_completion_manifest.json, .kittify/agent_profiles_manifest.json", "M2",
     _eq("src/specify_cli/_completion_manifest.json", ".kittify/agent_profiles_manifest.json")),
    ("OC-19", "S7", "specify_cli doctrine modules: doctrine/, doctrine_service_factory, doctrine_synthesizer, charter_runtime, drg_writers", "M2",
     _sw("src/specify_cli/doctrine/", "src/specify_cli/doctrine_synthesizer/", "src/specify_cli/charter_runtime/",
         "src/specify_cli/drg_writers/", "src/specify_cli/doctrine_service_factory.py")),
    ("OC-20", "S7", "other specify_cli consumers: upgrade migrations, tool_surface, runtime, invocation, dossier, skills, …", "M2",
     _sw("src/specify_cli/")),
    ("OC-21", "S7", "other packages: src/kernel, src/runtime, src/glossary, src/mission_runtime", "M2",
     _sw("src/kernel/", "src/runtime/", "src/glossary/", "src/mission_runtime/")),
    ("OC-22", "S7", "test fixtures/controls/baselines/allowlists (compatibility controls; M6 deletes the control machinery)", "M2",
     _any(_sw("tests/doctrine/fixtures/", "tests/architectural/fixtures/"),
          lambda p: p.startswith("tests/architectural/") and (p.endswith((".yaml", ".yml", ".json")) or "/fixtures/" in p),
          lambda p: p.startswith("tests/") and "/fixtures/" in p)),
    ("OC-23", "S7", "architectural gate tests: tests/architectural/** (sole-door, census, wheel closure, dead-path sweeps)", "M2",
     _sw("tests/architectural/")),
    ("OC-24", "S7", "test code: tests/** (doctrine, charter, specify_cli, integration, …)", "M2",
     _sw("tests/")),
    ("OC-25", "S9", "CI workflows: .github/workflows/**", "M2",
     _sw(".github/workflows/")),
    ("OC-26", "S8", "docs retrieval index, page inventory, ownership manifest, toc, redirect maps (serialized docs data)", "M5",
     _eq(*DOCS_DATA)),
    ("OC-27", "S9", "scripts: scripts/** (schema generation, doctrine inventory scripts, docs tooling)", "M2",
     _sw("scripts/")),
    ("OC-28", "S9", "root build/lint/config metadata: pyproject.toml, ruff.toml, pytest.ini, .gitignore, markdownlint, speedup workflow", "M2",
     _eq(*ROOT_CONFIG)),
    ("OC-29", "S3", "ADRs: docs/adr/**", "M5",
     _sw("docs/adr/")),
    ("OC-30", "S3", "test-sanitation evidence reports: docs/reports/** (census JSON, dispositions YAML)", "M5",
     _sw("docs/reports/")),
    ("OC-31", "S3", "plans/investigations/engineering notes: docs/plans/**", "M5",
     _sw("docs/plans/")),
    ("OC-32", "S3", "docs prose (reference, guides, architecture, context, changelog, api command docs)", "M5",
     _sw("docs/")),
    ("OC-33", "S3", "research outputs and ops history: research-outputs/**, kitty-ops/**", "M5",
     _sw("research-outputs/", "kitty-ops/")),
    ("OC-34", "S3", "project memory/evidence/mission-state history: .kittify/memory, evidence, missions, migrations, metadata.yaml", "M5",
     _any(_sw(".kittify/memory/", ".kittify/evidence/", ".kittify/missions/", ".kittify/migrations/"),
          _eq(".kittify/metadata.yaml"))),
    ("OC-35", "S3", "root repository docs: AGENTS.md, CLAUDE.md, README.md, CONTRIBUTING.md, CHANGELOG.md", "M5",
     _eq(*ROOT_DOCS)),
]
# Pathname rules (kind == pathname)
PATHNAME_RULES: list[tuple[str, str, str, str, object]] = [
    ("OC-40", "S2", "glossary authority pathname: docs/context/doctrine.md → docs/context/charter.md", "M1",
     _eq("docs/context/doctrine.md")),
    ("OC-41", "S4", "skill source pathnames: src/doctrine/skills/**", "M4", _sw("src/doctrine/skills/")),
    ("OC-42", "S7", "old source package pathnames: src/doctrine/**", "M2", _sw("src/doctrine/")),
    ("OC-43", "S7", "test pathnames: tests/**", "M2", _sw("tests/")),
    ("OC-44", "S7", "code pathnames: src/specify_cli/**, src/charter/**, src/kernel/**, src/runtime/**", "M2",
     _sw("src/")),
    ("OC-45", "S6", "project overlay pathnames: .kittify/doctrine/**", "M3", _sw(".kittify/doctrine/")),
    ("OC-46", "S4", "built-in agent asset pathnames: packs/built-in/** (doctrine-daphne, 018-doctrine-versioning-requirement)", "M4",
     _sw("packs/")),
    ("OC-47", "S3", "docs pathnames: docs/**", "M5", _sw("docs/")),
    ("OC-48", "S9", "repo-ops pathnames: .github/**, scripts/**", "M2", _sw(".github/", "scripts/")),
    ("OC-49", "S3", "history pathnames: .kittify/migrations/**, .kittify/evidence/**, kitty-ops/**, research-outputs/**", "M5",
     _sw(".kittify/migrations/", ".kittify/evidence/", "kitty-ops/", "research-outputs/")),
    ("OC-50", "S4", "host agent-dir pathnames", "M4", _sw(*AGENT_DIRS)),
]
RULES = {"content": CONTENT_RULES, "pathname": PATHNAME_RULES}

# Compatibility-reservation candidates (annotation only). Ordered; a hit funds at most one CR.
# (cr, legacy_form, seam, introduction_wave, canonical_target, budget, control_record, tests, source predicate(kind,path))
CR_RULES: list[tuple] = [
    ("CR-01", "governance.doctrine", "Charter selection key read by resolver/org-pack discovery", "M1",
     "governance.charter (3.x reader warns on old key)", 3, "test registry row + warning assertion",
     ["test_governance_doctrine_key_warns_and_maps", "test_governance_charter_key_canonical"],
     lambda k, p: k == "content" and p == ".kittify/config.yaml"),
    ("CR-02", "spec-kitty doctrine <subcommand>", "top-level CLI command group + eight subcommands", "M2",
     "spec-kitty charter … (hidden alias group warns)", 10, "hidden alias registration + warning test",
     ["test_doctrine_group_hidden_alias_warns", "test_charter_group_canonical_routes"],
     lambda k, p: k == "content" and p == "src/specify_cli/cli/commands/doctrine.py"),
    ("CR-03", "--doctrine-mode / doctrine_mode / tracker doctrine block", "tracker ownership flag/field/output", "M2",
     "--ownership-mode / ownership_mode / ownership block", 6, "tracker alias table + warning test",
     ["test_tracker_doctrine_mode_alias_warns", "test_tracker_ownership_mode_canonical"],
     lambda k, p: k == "content" and (p.startswith("src/specify_cli/tracker/") or p == "src/specify_cli/cli/commands/tracker.py")),
    ("CR-04", "doctrine.org.packs", "org-pack config key", "M2",
     "charter_packs.org.packs (3.x reader warns)", 3, "config-key alias table + warning test",
     ["test_org_pack_config_doctrine_key_warns"],
     lambda k, p: k == "content" and p in ("src/doctrine/drg/org_pack_config.py", "src/charter/org_pack_discovery.py")),
    ("CR-05", "doctrine:<kind>:<id>", "DRG target URN prefix", "M2",
     "charter:<kind>:<id> (3.x parser accepts+warns)", 4, "URN parser alias + warning test",
     ["test_urn_doctrine_prefix_parsed_with_warning", "test_urn_charter_prefix_canonical"],
     lambda k, p: k == "content" and p in ("src/doctrine/drg/models.py", "src/doctrine/drg/merge.py", "src/charter/drg.py")),
    ("CR-06", "import doctrine / doctrine.api", "Python package import path and public facade", "M2",
     "src/charter/** modules (3.x shim package re-exports + DeprecationWarning)", 8, "shim module list + warning test",
     ["test_doctrine_import_shim_warns", "test_charter_api_is_canonical_surface"],
     lambda k, p: k == "content" and p in ("src/doctrine/api.py", "src/doctrine/__init__.py")),
    ("CR-07", ".kittify/doctrine/", "project overlay root reader", "M3",
     ".kittify/charter-packs/ (3.x old-root reader + migrator warns; removed M6)", 4, "old-root fixture + migration tests",
     ["test_old_root_read_warns_and_migrates", "test_completed_migration_has_no_old_root"],
     lambda k, p: p.startswith(".kittify/doctrine/")),
    ("CR-08", "spk-doctrine-* / spec-kitty-charter-doctrine / doctrine-daphne / 018-doctrine-versioning-requirement",
     "skill/profile/directive IDs", "M4",
     "spk-charter-* / spk-charter-lifecycle / charter-daphne / 018-charter-versioning-requirement (3.x alias routes+warns)",
     12, "ID alias table + routing warning tests",
     ["test_skill_id_alias_routes_with_warning", "test_profile_directive_alias_routes_with_warning"],
     lambda k, p: (p.startswith("src/doctrine/skills/") or p.startswith("packs/built-in/agent_profiles/doctrine-daphne")
                   or p.startswith("packs/built-in/directives/018-doctrine"))),
]


def classify(kind: str, raw_path: bytes) -> tuple[str, str, str]:
    p = raw_path.decode("latin-1")
    for oc, surface, _seam, _owner, pred in RULES[kind]:
        if pred(p):
            cr = ""
            for cr_id, *_rest, src in CR_RULES:
                if src(kind, p):
                    cr = cr_id
                    break
            return oc, surface, cr
    raise AuditError(f"unclassified {kind} row (no rule matched, catch-all forbidden): {raw_path[:120]!r}")


# ----------------------------------------------------------------------------- build
def build_rows(base_commit: str, cwd: Path, git: str = "git") -> tuple[list[dict], dict]:
    tree_oid = resolve_tree_oid(base_commit, cwd, git)
    content = content_audit(base_commit, cwd, "inventory", git)
    paths = pathname_audit(base_commit, cwd, "inventory", git)
    ordinals: Counter = Counter()
    rows: list[dict] = []
    for path, line, col, match in content["records"]:
        ordinals[(path, line, col)] += 1
        o = ordinals[(path, line, col)]
        rows.append({"kind": "content", "raw_path": path, "line": line, "column": col, "ordinal": o, "match": match})
    for path in paths["matches"]:
        rows.append({"kind": "pathname", "raw_path": path, "line": None, "column": None, "ordinal": None, "match": b""})
    rows.sort(key=lambda r: (r["kind"], r["raw_path"], r["line"] or 0, r["column"] or 0, r["ordinal"] or 0))
    cc = pc = 0
    for r in rows:
        if r["kind"] == "content":
            cc += 1
            r["hit_id"] = f"H-C-{cc:06d}"
        else:
            pc += 1
            r["hit_id"] = f"H-P-{pc:06d}"
        r["match_sha256"] = match_sha256(r["kind"], tree_oid, r["raw_path"], r["line"], r["column"], r["ordinal"], r["match"])
        r["oc"], r["surface"], r["cr"] = classify(r["kind"], r["raw_path"])
    # set equality / duplicate checks
    coords = [(r["kind"], r["raw_path"], r["line"], r["column"], r["ordinal"]) for r in rows]
    if len(set(coords)) != len(coords):
        raise AuditError("duplicate coordinate")
    if cc != len(content["records"]) or pc != len(paths["matches"]):
        raise AuditError("row count differs from audit output (set inequality)")
    summary = {
        "base_commit": base_commit, "tree_oid": tree_oid,
        "content": {k: v for k, v in content.items() if k != "records"},
        "pathname": {k: v for k, v in paths.items() if k != "matches"},
        "counts": {"total": len(rows), "content": cc, "pathname": pc,
                   "by_surface": dict(sorted(Counter(r["surface"] for r in rows).items())),
                   "by_oc": dict(sorted(Counter(r["oc"] for r in rows).items())),
                   "by_cr": dict(sorted(Counter(r["cr"] for r in rows if r["cr"]).items())),
                   "by_oc_kind": {f"{oc}:{k}": n for (oc, k), n in sorted(Counter((r["oc"], r["kind"]) for r in rows).items())}},
    }
    return rows, summary


def render_tsv(rows: list[dict]) -> bytes:
    out = [HEADER]
    for r in rows:
        out.append("\t".join([
            r["hit_id"], r["kind"], percent_encode(r["raw_path"]),
            "" if r["line"] is None else str(r["line"]), "" if r["column"] is None else str(r["column"]),
            "" if r["ordinal"] is None else str(r["ordinal"]),
            r["match_sha256"], r["oc"], r["surface"], r["cr"]]) + "\n")
    return "".join(out).encode("utf-8")


def rule_tables_md(rows: list[dict]) -> str:
    by_oc = Counter(r["oc"] for r in rows)
    lines = ["| OC | S | Default owner | Rule / semantic seam | Rows |", "|---|---|---|---|---|"]
    for kind in ("content", "pathname"):
        for oc, s, seam, owner, _ in RULES[kind]:
            if by_oc.get(oc, 0) == 0:
                continue
            lines.append(f"| {oc} | {s} | {owner} | {seam} | {by_oc[oc]} |")
    return "\n".join(lines)


# ----------------------------------------------------------------------------- self-tests
def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _make_fixture(tmp: Path, with_token: bool) -> str:
    _git(tmp, "init", "-q")
    _git(tmp, "config", "user.email", "t@example.invalid")
    _git(tmp, "config", "user.name", "t")
    (tmp / "src" / "doctrine").mkdir(parents=True)
    (tmp / "kitty-specs" / "old-mission").mkdir(parents=True)
    (tmp / "kitty-specs" / "old-mission" / "spec.md").write_bytes(b"Doctrine inside archive\n")
    if with_token:
        (tmp / "src" / "doctrine" / "a.py").write_bytes(b"x = 'Doctrine DOCTRINE doctrine'\nimport doctrine\n")
        (tmp / "src" / "doctrine" / "we:ird\tname.txt").write_bytes(b"doctrine\n")
        (tmp / "src" / "doctrine" / b"non\xffutf8.md".decode("latin-1")).write_bytes(b"DoCtRiNe\n")
        (tmp / "src" / "doctrine" / "plain_module.py").write_bytes(b"pass\n")
    else:
        (tmp / "src" / "doctrine" / "a.py").write_bytes(b"x = 1\n")
    _git(tmp, "add", "-A")
    _git(tmp, "commit", "-q", "-m", "fixture")
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(tmp), check=True, stdout=subprocess.PIPE).stdout.decode().strip()


def selftest(real_base: str, real_cwd: Path) -> int:
    results: "OrderedDict[str, str]" = OrderedDict()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        empty = tmp / "empty"
        empty.mkdir()
        base0 = _make_fixture(empty, with_token=False)
        # test_content_audit_accepts_rc1_empty_only
        rec = content_audit(base0, empty, "terminal")
        results["test_content_audit_accepts_rc1_empty_only"] = "PASS" if (rec["rc"] == 1 and rec["mode_result"] == "zero") else "FAIL"
        # test_content_audit_rejects_git_rc_gt1 (invalid commit → rc 128)
        try:
            content_audit("0" * 40, empty, "terminal")
            results["test_content_audit_rejects_git_rc_gt1"] = "FAIL"
        except AuditError:
            results["test_content_audit_rejects_git_rc_gt1"] = "PASS"
        # test_path_audit_propagates_ls_tree_failure
        try:
            pathname_audit("0" * 40, empty, "terminal")
            results["test_path_audit_propagates_ls_tree_failure"] = "FAIL"
        except AuditError:
            results["test_path_audit_propagates_ls_tree_failure"] = "PASS"
        # mutation_git_audit_failure_cannot_pass_zero: failing git executable + invalid commit, both modes
        bad_git = tmp / "git-fails"
        bad_git.write_text("#!/bin/sh\nexit 3\n")
        bad_git.chmod(0o755)
        passed = True
        for mode in ("inventory", "terminal"):
            for git_exe, commit in ((str(bad_git), base0), ("git", "0" * 40)):
                try:
                    content_audit(commit, empty, mode, git_exe)
                    passed = False
                except AuditError:
                    pass
                try:
                    pathname_audit(commit, empty, mode, git_exe)
                    passed = False
                except AuditError:
                    pass
        results["mutation_git_audit_failure_cannot_pass_zero"] = "PASS" if passed else "FAIL"
        # hostile-path fixture: byte-identical reproduction across two processes + independent hash recompute
        fx = tmp / "fx"
        fx.mkdir()
        base1 = _make_fixture(fx, with_token=True)
        outs = []
        for i in range(2):
            out = tmp / f"fx-{i}.tsv"
            proc = subprocess.run([sys.executable, __file__, "--base", base1, "--mode", "inventory", "--out", str(out),
                                   "--cwd", str(fx)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                raise SystemExit(f"fixture inventory failed: {proc.stderr.decode(errors='replace')}")
            outs.append(out.read_bytes())
        fx_rows, _ = build_rows(base1, fx)
        kinds = Counter(r["kind"] for r in fx_rows)
        hostile_ok = any(b":" in r["raw_path"] for r in fx_rows) and any(b"\t" in r["raw_path"] for r in fx_rows) \
            and any(any(b > 127 for b in r["raw_path"]) for r in fx_rows) and kinds["pathname"] == 4 and kinds["content"] == 6
        results["fixture_hostile_paths_and_repeated_mixed_case"] = "PASS" if hostile_ok else f"FAIL {kinds}"
        results["fixture_two_process_byte_identical"] = "PASS" if outs[0] == outs[1] else "FAIL"
    # real tree: two independent processes byte-identical + independent recompute of hashes
    with tempfile.TemporaryDirectory() as d:
        outs = []
        for i in range(2):
            out = Path(d) / f"real-{i}.tsv"
            proc = subprocess.run([sys.executable, __file__, "--base", real_base, "--mode", "inventory", "--out", str(out),
                                   "--cwd", str(real_cwd)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                raise SystemExit(f"real inventory failed: {proc.stderr.decode(errors='replace')}")
            outs.append(out.read_bytes())
        results["test_inventory_match_sha256_byte_identical_reproduction"] = "PASS" if outs[0] == outs[1] else "FAIL"
        # independent recompute: re-derive hashes straight from grep/ls-tree records with a second, plain implementation
        tree = resolve_tree_oid(real_base, real_cwd)
        tsv_hashes = {}
        for line in outs[0].decode("utf-8").splitlines()[1:]:
            f = line.split("\t")
            tsv_hashes[(f[1], f[2], f[3], f[4], f[5])] = f[6]
        content = content_audit(real_base, real_cwd, "inventory")
        seen: Counter = Counter()
        mism = 0
        checked = 0
        for path, ln, col, match in content["records"]:
            seen[(path, ln, col)] += 1
            o = seen[(path, ln, col)]
            pre = DOMAIN_TAG + struct.pack(">Q", 7) + b"content" + struct.pack(">Q", len(tree)) + tree.encode() \
                + struct.pack(">Q", len(path)) + path
            for v in (ln, col, o):
                pre += struct.pack(">Q", 8) + struct.pack(">Q", v)
            pre += struct.pack(">Q", len(match)) + match
            h = hashlib.sha256(pre).hexdigest()
            checked += 1
            if tsv_hashes.get(("content", percent_encode(path), str(ln), str(col), str(o))) != h:
                mism += 1
        for path in pathname_audit(real_base, real_cwd, "inventory")["matches"]:
            pre = DOMAIN_TAG + struct.pack(">Q", 8) + b"pathname" + struct.pack(">Q", len(tree)) + tree.encode() \
                + struct.pack(">Q", len(path)) + path + struct.pack(">Q", 0) * 4
            h = hashlib.sha256(pre).hexdigest()
            checked += 1
            if tsv_hashes.get(("pathname", percent_encode(path), "", "", "")) != h:
                mism += 1
        results["independent_hash_recompute_all_rows"] = f"PASS ({checked} rows)" if mism == 0 and checked == len(tsv_hashes) else f"FAIL ({mism} mismatches)"
    for k, v in results.items():
        print(f"{k}: {v}")
    return 0 if all(v.startswith("PASS") for v in results.values()) else 2


# ----------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--mode", choices=("inventory", "terminal"), default="inventory")
    ap.add_argument("--out")
    ap.add_argument("--summary")
    ap.add_argument("--tables", action="store_true", help="print markdown OC table")
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--git", default="git")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    cwd = Path(a.cwd).resolve()
    try:
        if a.selftest:
            return selftest(a.base, cwd)
        if a.mode == "terminal":
            tree = resolve_tree_oid(a.base, cwd, a.git)
            c = content_audit(a.base, cwd, "terminal", a.git)
            p = pathname_audit(a.base, cwd, "terminal", a.git)
            att = {"mode": "terminal", "base_commit": a.base, "tree_oid": tree,
                   "content": {k: v for k, v in c.items() if k != "records"}, "content_hits": len(c["records"]),
                   "pathname": {k: v for k, v in p.items() if k != "matches"}, "pathname_hits": len(p["matches"]),
                   "result": "zero" if (c["mode_result"] == "zero" and p["mode_result"] == "zero") else "hits"}
            print(json.dumps(att, indent=1))
            return 0 if att["result"] == "zero" else 1
        rows, summary = build_rows(a.base, cwd, a.git)
        tsv = render_tsv(rows)
        summary["tsv_sha256"] = _sha(tsv)
        summary["tsv_bytes"] = len(tsv)
        summary["excluded_root_content_records"] = excluded_root_content_orientation(a.base, cwd, a.git)
        if a.out:
            tmp = Path(a.out).with_suffix(".tmp")
            tmp.write_bytes(tsv)
            os.replace(tmp, a.out)
        if a.summary:
            Path(a.summary).write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
        if a.tables:
            print(rule_tables_md(rows))
        if not a.out and not a.summary and not a.tables:
            print(json.dumps(summary["counts"], indent=1))
        return 0
    except AuditError as exc:
        print(f"AUDIT ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```
