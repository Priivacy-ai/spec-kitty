# Data Model: Complete Current-Tree Terminology Extinction

**Mission**: `retire-doctrine-term-01M0JMK9` · **Updated**: 2026-08-22

This planning mission defines five evidence entities: surface category, occurrence hit, occurrence class,
compatibility reservation, and stacked mission. It intentionally defines no runtime ledger/state
architecture.

## 1. Surface categories

Every hit belongs to exactly one primary category; audience does not remove it from scope. The immutable
`kitty-specs/` historical-archive root (`DM-01M0NMS9WPH33EPFCJQRTQVNSA`) is outside the audited tree by one
fixed pathspec; it is not a category, class, or exemption.

| ID | Category | Complete scope | Downstream owner default |
|---|---|---|---|
| S1 | CLI/operator routes | commands, subcommands, flags, help, errors, warnings | M2; temporary aliases removed M6 |
| S2 | glossary/authority | all glossary authorities, paths, referrers | M1 |
| S3 | current-tree prose/history | docs, ADRs, docs archives, evidence, READMEs, comments, current-tree history snapshots and filenames outside `kitty-specs/`; referrers to archive paths | M5 unless authority/executable |
| S4 | agent artifacts | skills, profiles, directives, prompts, overrides, generated/installed/shared assets | M4; aliases M6 |
| S5 | Charter authority | `.kittify/charter/` plus owning source/graph/interview/synthesis/generated surfaces | M1 |
| S6 | packs/project overlays | built-in/org/project packs and `.kittify/doctrine/` → `.kittify/charter-packs/` migration | M3; old-root compatibility M6 |
| S7 | code/build/test topology | public and non-public packages, modules, symbols, imports, tests, fixtures, build hooks, distribution metadata | M2; compatibility fixtures M6 |
| S8 | serialized/workflow/generated | keys, values, URNs, JSON/API/event renderers, workflows, templates, generated outputs | M2 unless M1/M3/M4 authority-owned; aliases M6 |
| S9 | repository operations | root docs, scripts, CI, release/config metadata, tracked pathnames | M2/M5 by role; compatibility M6 |
| S10 | tracker/ownership | tracker blocks, flags, fields, API payloads and consumers | M2; aliases M6 |

No X1/X2/X3 class exists. Internal, historical (outside `kitty-specs/`), intentional fixture/control,
generated, and metadata hits are work items. A compatibility literal remains an ordinary hit annotated by a reservation until M6.

## 2. Occurrence hit (`inventory-hits.tsv`)

One row represents one case-insensitive content match or one matching tracked pathname at the frozen
`base_commit`, outside `kitty-specs/`. The TSV is ephemeral evidence (`DM-01M0NMSD60JYG7K7V5MJCKJ3P8`):
generated and untracked, with its SHA-256, row count, and per-kind/S/OC counts pinned in committed
`inventory.md`.

| Field | Rule |
|---|---|
| `hit_id` | stable `H-C-######` or `H-P-######` after deterministic sort |
| `kind` | `content` or `pathname` |
| `path` | exact repo-relative path at `base_commit` |
| `line`, `column`, `ordinal` | positive for content; empty for pathname; ordinal disambiguates repeated matches |
| `match_sha256` | lowercase SHA-256 of the inventory contract's exact v1 domain-tagged, uint64-BE LP preimage; content uses lowercase tree-OID ASCII + raw path + uint64-BE line/column/ordinal + exact match, pathname uses the same tree/path with four explicit empty fields |
| `occurrence_class_id` | exactly one `OC-##`; never an X/exemption value |
| `surface_category` | exactly one `S1`…`S10` |
| `compatibility_registry_id` | nullable `CR-##`; annotation only, not second ownership |

**H-I1 (set equality)**: manifest content rows equal the forced-text `git grep` output (with the fixed
`:(exclude)kitty-specs/` pathspec) and pathname rows equal the NUL-safe `git ls-tree` output after the
`kitty-specs/` drop, from the checked no-pipeline subprocess contract. Set equality is undefined/failing if
grep returns >1, ls-tree returns nonzero, or return code and output disagree. No duplicate, omitted,
sampled, or synthetic row exists. It is proven by regenerating the TSV from the frozen base and matching
the recorded SHA-256 and counts.

**H-I2 (stable order)**: rows sort by `kind,path,line,column,ordinal`; rerun at one commit is byte-identical.
Two independent processes must also reproduce each row's canonical hash byte-for-byte, including hostile
path bytes and mixed-case content fixtures.

**H-I3 (terminal totality)**: every base hit is retired by one wave. I6 reruns against current `HEAD` with
the same fixed exclusion and requires zero rows from both audits; a historical base row is evidence, not
permission to remain.

## 3. Occurrence class (`OC-##`)

| Field | Rule |
|---|---|
| `id` | stable, never reused |
| `surface_category` | exactly one S category |
| `member_hit_ids` | non-empty exact set of manifest rows |
| `semantic_seam` | one owning behavior/authority/migration purpose |
| `representative_examples` | presentation only; never replaces membership |

Classes split whenever members require different M1–M6 owners. `stacked-plan.md` is the sole primary-owner
table and assigns every class—and therefore every member hit—exactly once to M1, M2, M3, M4, M5, or M6.
There is no external deferral for a current-repository hit.

## 4. Compatibility reservation (`CR-##`)

A reservation permits one bounded 3.x compatibility surface without exempting it from final removal.

| Field | Rule |
|---|---|
| `id` | stable `CR-##` |
| `legacy_form`, `semantic_seam` | full token/path and one meaning; no fragment construction |
| `source_hit_ids` | disjoint exact frozen-base hits; their OCs retain the M1–M4 introduction-wave primary owner and each funds at most one CR |
| `introduction_wave` | exactly one of M1–M4 and equal to source OC owner |
| `removal_wave` | literal M6 |
| `canonical_target` | fixed, or M2 topology-map row frozen before edits |
| `product_hit_budget` | maximum exact 3.x compatibility fingerprints |
| `control_record` | exact test/registry evidence deleted by M6 |
| `state` | `reserved|active|closed-no-channel|removed`; I6 requires `removed` and absent control/product hits |

Compatibility controls, fixtures, warnings, aliases, redirect paths, and tombstones are all manifest hits
when introduced after the frozen base: their new coordinates are M6-removal work and do not retroactively
duplicate or change the source OC's M1–M4 primary ownership. At each wave-local audit they receive exactly
one M6 cleanup assignment. M6 deletes the registry/baseline/allowlist machinery itself. Post-M6
negative tests build the token from numeric bytes.

## 5. Stacked mission

| Field | Rule |
|---|---|
| `slug`, `purpose`, `depends_on` | explicit, ordered M1→M6 |
| `inputs`, `outputs` | exact artifacts/maps/migrations/audits; no implicit dependency |
| `retires_oc` | exact disjoint OC list; union across M1–M6 equals all OCs |
| `introduces_compatibility` | M1–M4 CR list; empty M5/M6 |
| `removes_compatibility` | every CR exactly once in M6 |
| `change_mode` | `bulk_edit` for every downstream mission |
| `occurrence_map` | wave-local audit and exact owned hit set |
| `merge_gate`, `rollback` | named tests, zero conditions, reversible prefix/suffix strategy |
| `invariant_after` | exact I1…​I6 below |

## 6. Stack invariants

| Level | Required state |
|---|---|
| I0 | Existing 3.x authority coherent; no half-renamed state. |
| I1 | ADR and complete Charter/glossary authority graph record the override/canon; M1 hits gone; temporary transition guard armed. |
| I2 | Frozen internal+public topology map fully applied; `src/doctrine/` and every live code/internal/test/build pathname or symbol hit gone; registered 3.x aliases only. |
| I3 | Project overlay data verified at `.kittify/charter-packs/`; completed migrations have no `.kittify/doctrine/` root; conflicts remain pre-completion blockers. |
| I4 | Canonical skills/profiles/directives/prompts/generated/installed assets work; completed migrations have no old-named installed path; registered 3.x aliases only. |
| I5 | All remaining current-tree prose/history/ADR/docs/archive/evidence content, filenames, and referrers outside `kitty-specs/` use canonical vocabulary; `kitty-specs/` is byte-identical to its pre-M5 state. Git object history and that archive alone retain old bytes. |
| I6 | Every CR/alias/key/path/control/fixture removed; transition baselines/allowlists deleted; mandatory `scripts/audit_retired_term_zero.py` check `terminology-zero-current-tree` reports checked content/path counts = 0 (fixed `kitty-specs/` exclusion only) in external stdout attestation for one final commit/tree and is rerun by CI/release on the result tree. |

## 7. Migration safety model (planning level only)

M3/M4 require a bounded preflight manifest, backup, checked copy/move, verification, source removal, and
rollback—not a new runtime ledger architecture.

- absent destination: preserve content/mode at canonical destination, verify, then remove old path;
- identical destination: verify identity, then remove old path;
- divergent destination: hard-fail with both originals intact until operator resolution;
- any interruption before verification: rollback from backup and do not mark migration complete;
- completion marker/test cannot pass while any old-named path exists.

This preserves user data while implementing the operator's explicit pathname-extinction override.
