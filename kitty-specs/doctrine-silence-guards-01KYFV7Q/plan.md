# Implementation Plan: Doctrine Silence Guards

**Branch**: work lands on a branch off `main`; mission targets `main` | **Date**: 2026-07-26
**Spec**: [`spec.md`](spec.md)
**Programme record**: [`doctrine-canonical-structure-remediation-01KYEYSD`](../doctrine-canonical-structure-remediation-01KYEYSD/plan.md) — concern map, Phase 0 findings, ordering rationale
**Tracker**: [#2948](https://github.com/Priivacy-ai/spec-kitty/issues/2948) · epic [#2466](https://github.com/Priivacy-ai/spec-kitty/issues/2466)

## Summary

Close the **silence class** in the doctrine layer before anything new is added to the graph.

Every defect this programme found fails the same way: quietly. A misplaced artefact never loads. An
unknown kind is bucketed and dropped. An unknown field is ignored, because the DRG models declare no
`model_config` and the writers enumerate fields by hand. A schema slot with no producer ships green
and stays inert — three times in this repo, one for 162 days behind passing tests.

Ten work packages, all of them guards or campsite. **Nothing here changes graph content** — node,
edge and orphan counts move by exactly zero, with one ledgered exception (WP09's `applies` retype,
which changes a relation at constant cardinality).

This mission must land **first**. Missions B1 and B2 add `Relation.IMPACTS`, `is_symmetric` and
`aliases`; three of the four silent-drop sites fixed here would delete them at extraction and
regeneration, and the tests would stay green.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic v2, ruamel.yaml, typer, pytest, jsonschema
**Storage**: YAML doctrine artefacts under `src/doctrine/`; generated `*.graph.yaml` fragments; JSON Schema under `src/doctrine/schemas/`
**Testing**: pytest. Targeted single-file runs only — **never the full `tests/architectural/` directory** (C-003). ATDD red-first per WP; the reviewer verifies RED on the planning base and GREEN at the WP's final commit
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform CLI)
**Project Type**: single project
**Performance Goals**: no runtime regression; the new lints are test-time only and must not add measurable time to graph load
**Constraints**: zero graph-content change (NFR-004); every gate non-vacuous with a zero-entry allowlist (NFR-001); no `# noqa` / `# type: ignore` to pass ruff or mypy
**Scale/Scope**: 4 silent-drop sites · 3 pydantic models · 7 stale schemas · 4 reference enums · 22 `shipped/` hits across 9 files · **17** dead-`graph.yaml` carrier files (raw grep — the earlier "~10" implied a filtering that does not exist yet) · 16 `NodeKind` members · 1 CI collection-completeness gap · **~60–80 files total** (was ~55–70 before #2957 folded in; **5–7 agent-days**, was 4–6)

### Measured ground truth (executed on this branch, 2026-07-26)

Every figure below was run, not read. The sequencing authority's own concession is that *"nothing was
executed — every claim about how the existing codebase behaves is a careful static read"*, so these
supersede it where they differ.

| Fact | Value |
|---|---|
| `NodeKind` members | **16** |
| `extractor._KIND_MAP` entries | **11** — drops `anti_pattern`, `asset`, `glossary`, `glossary_pack`, `glossary_scope` |
| `query.py:230-242` | 16 buckets filled, **10 read out** → 6 kinds lost |
| `charter/context.py:672-683` | 4 kind branches, **no `else`** → 12 kinds lost |
| `DRGNode` / `DRGEdge` `model_config` | **absent on both** |
| `AgentProfile` `model_config` | **PRESENT** (`profile.py:254`) — sibling `ContextSources:181` already uses `extra="forbid"`. The earlier "absent on all three" was a static-read error; WP04's AgentProfile change is a one-line addition to an existing config |
| `generate_schemas.py --check` | **exits 1**, 7 stale schemas |
| `shipped/` references under `src/doctrine/` | **22 across 9 files** (≥1 is prose, not a path) |
| Graph baseline | 311 nodes / 774 edges; `applies` 1, `refines` 0 |

## Charter Check

*GATE: passed. Re-check before review.*

| Charter rule | How this mission satisfies it |
|---|---|
| Campsite cleaning (SO-2) | This mission **is** the campsite band — six of the sequencing authority's top eight ranked increments, scheduled before any functional change. |
| Architectural gate discipline (SO-5) | Every gate carries a self-mutation test that plants the real violation shape and asserts RED, plus a zero-entry allowlist. A gate-unmask cannot self-validate. |
| ATDD-first (C-011) | Each WP's first commit is a failing test. For WP01, WP03 and WP04 the RED *is* the deliverable — it is the proof the silence existed. |
| Single canonical authority | WP02 extends the occurrence-map schema rather than adding a second exemption mechanism; WP06 ratchets the existing enums rather than duplicating them. |
| Red-main discipline (SO-9) | The 6 inherited `arch-adversarial` reds stay red (C-004). No greenwashing, no retry-to-green. |
| Canonical sources (SO-6) | Requirement IDs use the repo's `FR-###` convention; scope derived from `scripts/doctrine/inline_reference_inventory.py`, never restated as a literal. |
| Git/workflow (SO-7) | One draft PR to `main`; the operator merges. Never `git push origin main`. |

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-silence-guards-01KYFV7Q/
├── spec.md            # FR-001..FR-013, NFR-001..005, C-001..006, SC-001..013
├── squad-findings-post-tasks.md   # post-tasks adversarial squad: findings + disposition
├── plan.md            # this file
├── tasks.md           # WP manifest
├── analysis-report.md # blocking at implement
└── tasks/             # per-WP prompt files
```

### Source Code (repository root)

```
src/doctrine/
├── drg/
│   ├── models.py            # DRGNode / DRGEdge — gain extra="forbid"        (WP04)
│   ├── query.py             # site 1: 16 bucketed, 10 read out               (WP03)
│   ├── merge.py             # org→DRG bridge: silent cross-layer drop        (WP08)
│   ├── org_pack_loader.py   # bare-target re-kinding, raw pydantic on URNs   (WP08)
│   └── migration/extractor.py  # _KIND_MAP (WP03) · field-by-field writers (WP04)
├── agent_profiles/profile.py   # AgentProfile — gains extra="forbid"         (WP04)
├── schemas/
│   ├── occurrence-map.schema.yaml   # gains field-path granularity           (WP02)
│   └── *.schema.yaml                # 7 stale                                (WP05)
└── skills/**, templates/**          # 22 `shipped/` hits                      (WP07)

src/charter/context.py               # site 2: 4 branches, no else            (WP03)
scripts/generate_schemas.py          # drops structural_lint_config           (WP05)
tests/architectural/                 # gates. NEVER run the whole directory
.github/workflows/ci-quality.yml     # --check wiring + collection gap        (WP10)
```

**Structure Decision**: existing layout, no new packages. The only new files are test modules under
`tests/architectural/` and the fixture trees their self-mutation tests plant.

## Implementation Concern Map

Concern IDs match the programme record, which owns IC-01…IC-08. `tasks.md` turns them into 10 WPs.

> **Post-tasks squad corrections are folded in.** Three mechanisms that could not fail were found and
> fixed; see [`squad-findings-post-tasks.md`](squad-findings-post-tasks.md) for the full record and
> the six accepted-but-unactioned items.

### IC-01 — Inert-slot prevention

- **Purpose**: Make it structurally impossible for a schema slot to ship with no producer.
- **Requirements**: FR-001, NFR-001, SC-001
- **Surfaces**: new `tests/architectural/` lint module
- **Depends on**: nothing — **must be first**
- **Risks**: The lint's own definition of "slot" and "producer" is the hard part. A definition too narrow passes everything; too broad false-reds on legitimately read-only fields. Calibrate against the three known-inert historical cases *and* the shipped tree, and record the definition in the module docstring.

### IC-02 — Bulk-edit guardrail granularity

- **Purpose**: `occurrence-map.schema.yaml` classifies by path glob, but mission B2's exemptions are field-scoped and every one of its 17 GOVERNANCE files also carries migrating entries. The guardrail cannot express its own mission.
- **Requirements**: FR-002, SC-011
- **Surfaces**: `src/doctrine/schemas/occurrence-map.schema.yaml`, `src/specify_cli/bulk_edit/{occurrence_map,diff_check}.py`, `src/doctrine/templates/occurrence-map-template.yaml`
- **Depends on**: nothing
- **Risks**: Backward compatibility — legacy single-term maps must keep validating. Prove it against B2's real exemption set (188 GOVERNANCE + 14 RAW), not a toy fixture.

### IC-03 — Silent-drop closure across the kind and field boundaries

- **Purpose**: Four sites drop an unknown *kind*; three models drop an unknown *field*. Both must close before any new edge field exists.
- **Requirements**: FR-003, FR-004, NFR-004, SC-002, SC-003
- **Surfaces**: `query.py:230-242`, `charter/context.py:672-683`, `extractor.py:133-145`, `extractor.py:1210-1229`, `drg/models.py`, `agent_profiles/profile.py`
- **Depends on**: IC-01. **Blocks missions B1, B2 and C.**
- **Risks**: Collides with `#2532` (decompose `charter/context.py`) — the missing `else` is inside the module being split. **Pin behaviourally, not by code shape**, so the decomposition cannot silently drop it. Model + writer + round-trip must land in **one commit**. Closing `_KIND_MAP` may surface previously-dropped kinds as new nodes — if the graph count moves, that is a finding, not a licence to bump the golden count.

### IC-04 — Schema generation integrity

- **Purpose**: `--check` exists, exits 1, and is wired to nothing. Wiring it as-is puts a red gate on the branch.
- **Requirements**: FR-005, SC-004
- **Surfaces**: `scripts/generate_schemas.py`, 7 `src/doctrine/schemas/*.yaml`, one workflow file
- **Depends on**: nothing
- **Risks**: Three divergence classes, only one safe. Retired `enhances`/`overrides` → **accept** (finishes a half-done excision). `structural_lint_config` → **generator bug, fix the generator**; accepting the deletion invalidates a shipped artefact. `point_in_time_marker` → declared in no model but used by a shipped artefact — **adjudicate, do not regenerate blindly**. Also verify the `reference` → `paradigm_reference` rename's `$ref` targets.

### IC-05 — Structural ratchets

- **Purpose**: The layout gate checks 1 of 2 mandatory path segments; the enum freeze is a comment, not a gate.
- **Requirements**: FR-006, FR-007, NFR-001, SC-005, SC-006
- **Surfaces**: `tests/architectural/test_doctrine_artefact_layout.py`, the four `<kind>_reference.type` enums
- **Depends on**: nothing
- **Risks**: The layout allowlist must stay at exactly 0 entries. The 17 mission-tier step contracts are a documented carve-out pinned *positively*, so the exception cannot hide a real stray.

### IC-06 — Followable guidance

- **Purpose**: The one hint pointing from the legacy surface to the canonical one names a file that no longer exists; a `shipped/` pack layer named in operator-facing guidance has never existed at all.
- **Requirements**: FR-008, FR-009, NFR-003, SC-007, SC-008
- **Surfaces**: `InlineReferenceRejectedError` + ~10 sites; 22 `shipped/` hits across 9 files including two `SKILL.md` and a glossary term body
- **Depends on**: nothing
- **Risks**: **Both gates need discriminators or they false-red on correct code.** The `graph.yaml` gate must not flag `.kittify/doctrine/graph.yaml` (live project-tier) or the sites that name the dead path *in order to forbid it*. The `shipped/` gate must not flag the prose "shipped/packaged". Each discriminator needs a fixture that would fail without it.

### IC-07 — org→DRG bridge integrity and relation hygiene

- **Purpose**: The bridge drops a built-in→pack edge with no warning and no conflict record, blindly re-kinds bare targets, and raises raw pydantic on URN-shaped ones. Adding vocabulary to a leaking bridge is how the defect class regrows.
- **Requirements**: FR-010, FR-011, FR-012, NFR-002, SC-009, SC-010
- **Surfaces**: `drg/merge.py`, `drg/org_pack_loader.py`, the `CLAUDE.md` `specializes_from` snippet, daphne's `applies` edge
- **Depends on**: IC-03. **Must land before mission B1** (ADR 2026-07-26-3, Negative consequences).
- **Risks**: **`applies` is not a dead sink** — the comment at `drg/merge.py:97-98` is wrong. `charter_runtime/lint/checks/orphan.py` reads it and `charter/synthesizer/project_drg.py` produces it. Build the gate on measurement, not on that comment. Retyping daphne's edge changes a live traversal result; ledger it.

### IC-08 — CI collection completeness *(folded in from [#2957](https://github.com/Priivacy-ai/spec-kitty/issues/2957), 2026-07-26)*

- **Purpose**: A frozen-contract test that no main-branch job collects is exactly as inert as a schema slot with no producer — IC-01 one layer up. This one has already fired.
- **⚠️ Corrected claim.** An earlier revision said "four test files were red on `main` @ `1a15bcf6c` while main CI reported green." **That is false** — run `30212948549` concluded **failure** (arch-adversarial ×3, slow-tests, quality-gate), and so did the previous twelve main runs. A reviewer disproves it with one `gh run view`. The true and stronger claim: the three `cli`-gated jobs were **skipped**, so those reds were not merely unnoticed — they were **structurally uncollectable**. Confirmed from the live log: `Filter cli = false → skipped fast-tests-cli, integration-tests-cli`, plus a third `cli`-gated job at `ci-quality.yml:2836`.
- **⚠️ Scale corrected — the gap is ~3.6× what FR-013 scoped.** Measured two independent ways (58 real `--collect-only` subprocess runs using each job's exact paths/ignores/markers, cross-checked against the repo's own `_gate_coverage.load_gates`): **950 of 2166 test files / 14,870 of 33,665 tests (44%) are collected by no job** on that commit, across 21 roots — `tests/charter` 132, `tests/sync` 103, `tests/agent` 75, `tests/status` 41. `cli` is not special; it is one of 24 dorny groups with identical semantics. Separately, only 12 files are collected by no `ci-quality.yml` job under *any* filter state, and all 12 are legitimately owned by `ci-windows.yml` / `release.yml` / `ui-e2e.yml` — **zero true orphans**.
- **Requirements**: FR-013, NFR-005, SC-013
- **Surfaces**: `.github/workflows/ci-quality.yml` (the `changes` paths-filter and the job `if:` conditions); a new `tests/architectural/` meta-test
- **Depends on**: IC-01 — the same anti-vacuity mechanic, and the lint should cover the meta-test's own slots
- **Mechanism, verified in-tree 2026-07-26**: `fast-tests-cli` and `integration-tests-cli` both gate on `needs.changes.outputs.cli == 'true'`, and the `cli` filter is `src/specify_cli/cli/**` + `tests/cli/**` + `tests/specify_cli/cli/**`. So on any main push whose diff misses those paths, **neither job runs and none of their tests are collected**. A red introduced by one merge stays invisible through every later green main run. The `fast-tests-core-misc` shard split compounds it: `specify-cli-rest` carries `--ignore=tests/specify_cli/cli`, `specify-cli-rest-2` does not include it, and `core-misc` ignores `tests/specify_cli` wholesale.
- **Risks**: **The shard-split's own completeness check was scoped to the split, not the tree.** Its comment records "Verified disjoint + union-complete locally: 3241 + 3079 == 6320 (today's real `specify-cli-rest` selection, unchanged)" — that verifies the *bin-split* preserved a selection which **already had the hole**. Any replacement check must diff against the **full** collection, or it reproduces the same vacuity. Second risk: the meta-test will surface currently-masked reds. Those are honest pre-existing reds under ADR `2026-07-17-1` — **report them, do not fix them here, and never satisfy the gate by reclassifying a red as expected.**

## Ordering within the mission

```
WP01 (zero-producer lint)  ─── first, guards everything
   │
   ├── WP03 (four-site kind-drop) ──► WP04 (extra="forbid" + writers + round-trip)
   │                                      │
   │                                      └──► WP08 (bridge) ──► WP09 (applies)
   │
   └── WP02, WP05, WP06, WP07, WP10  ── independent, parallelizable after WP01
```

**WP01 first** is C-001: the lint is what proves the later WPs' new gates are not themselves inert.
**WP03 before WP04** because closing the kind boundary before the field boundary means the
`extra="forbid"` work lands on a model whose kinds are already total. **WP08 before B1** is the ADR's
own requirement.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Extending the occurrence-map schema (WP02) inside a guards mission | The guardrail cannot express mission B2's exemptions, and B2 is two missions away | Deferring it is what C-005 forbids — it converts a known defect into an invisible one. Doing it in B2 would mean B2 authoring its own guardrail, which is self-validation. |
| Two path gates with hand-written discriminators (WP07) | The naive greps false-red on correct code — a live project-tier path, deliberate forbidding-mentions, and one prose match | A bare string gate would be simpler and would fail on day one, teaching the team to ignore it. |

## Validation

Per-WP: the WP's own targeted test files, plus `ruff` and `mypy --strict` clean on touched files.

Mission-level, before review:

```bash
PYTHONPATH=src python -m pytest tests/doctrine/ -q -p no:cacheprovider
PYTHONPATH=src python -m pytest tests/architectural/test_doctrine_artefact_layout.py -q
PYTHONPATH=src python -m pytest tests/architectural/test_no_legacy_terminology.py -q
PYTHONPATH=src python scripts/generate_schemas.py --check          # must exit 0 after WP05
PYTHONPATH=src python scripts/doctrine/inline_reference_inventory.py   # must be unchanged: 559/188/14
```

Graph invariant (NFR-004) — must report 311 nodes / 774 edges before **and** after, except WP09's
ledgered relation change:

```bash
PYTHONPATH=src python -c "
from doctrine.drg.loader import load_graph_or_dir; import pathlib, collections
g = load_graph_or_dir(pathlib.Path('src/doctrine'))
print(len(g.nodes), len(g.edges), collections.Counter(e.relation.value for e in g.edges))"
```

**Never run the full `tests/architectural/` directory** (C-003) — a known harness issue kills the
session. Targeted single-file runs only.

Docs gates, if any `.md` under `docs/` is touched — run the **whole** set; two sibling lockfiles have
separate generators and fixing one has broken the other before:

```bash
PYTHONPATH=. python scripts/docs/description_length_check.py --strict --repo-root .
PYTHONPATH=. python scripts/docs/freshen_adr_inventory.py --all
PYTHONPATH=. python scripts/docs/docs_index.py --write
PYTHONPATH=. python scripts/docs/check_docs_freshness.py
npx --no-install markdownlint-cli2 --config .markdownlint-cli2.jsonc "<changed .md>"
PYTHONPATH=src python -m pytest tests/docs/ -q -p no:cacheprovider
```

## Deferred planning questions

The plan interview ran non-interactively and recorded its questions as deferred. Two are worth
answering before implementation, and neither blocks WP01:

1. **What exactly is a "schema slot" for WP01's lint?** Model field, JSON-Schema property, or both? The answer sets the lint's blast radius. Recommend: both, with the producer search spanning `src/` writers and the generated schemas.
2. ~~**Does closing `_KIND_MAP` (WP03) surface new nodes?**~~ **Answered 2026-07-26 — no.** Swept every YAML under `src/doctrine/` for a reference naming one of the five dropped kinds (`anti_pattern`, `asset`, `glossary`, `glossary_pack`, `glossary_scope`): **zero hits**. So closing the map is graph-neutral today and NFR-004's 311 nodes / 774 edges holds unchanged.

   **But the drop is latent, not harmless** — and the reason it is currently silent is itself the finding. Nothing names those kinds *because the inline reference enums are frozen and `asset` was refused* (that refusal is what started this programme). The map's gap becomes live the moment an artefact legitimately references one, which is precisely what **mission C** does when it authors 2 anti-patterns and 4 assets. A graph-neutral fix now is a graph-corrupting omission two missions later.
