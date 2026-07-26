# Mission Specification: Doctrine Silence Guards

**Created**: 2026-07-26
**Status**: Draft
**Programme**: Mission **A** of five, split from [`doctrine-canonical-structure-remediation-01KYEYSD`](../doctrine-canonical-structure-remediation-01KYEYSD/spec.md) — that spec is the requirements authority and carries the full FR→mission routing table.
**Order**: **First.** B1, B2 and D all gate on this mission (C-009, C-010).
**Governing ADRs**: [2026-07-26-1](../../docs/adr/3.x/2026-07-26-1-drg-edges-are-the-canonical-relationship-authority.md) · [-2](../../docs/adr/3.x/2026-07-26-2-doctrine-artefact-pack-layout-convention.md) · [-3](../../docs/adr/3.x/2026-07-26-3-impacts-edge-subsumes-in-tension-with.md)

## Context

The programme's root finding is that **the doctrine layer's failure mode is silence, not error**. A
misplaced artefact never loads. An unknown kind is dropped without a warning. An unknown field is
ignored, because the DRG models declare no `model_config` and the writers enumerate fields by hand.
A schema slot with no producer ships green and stays inert — three times in this repo, one of them
for 162 days behind passing tests.

This mission closes that class **before** anything new is added to the graph. That ordering is the
entire point. Missions B1 and B2 add `Relation.IMPACTS`, `is_symmetric` and `aliases`, and every one
of those would be silently deleted at extraction and regeneration if it landed first — the
programme's own defect class, reproduced by its remediation.

It is also, deliberately, mostly campsite work: six of the sequencing authority's top eight ranked
increments are campsite. Debt before functional change.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A schema slot cannot ship with nothing producing it (Priority: P1)

A maintainer adds a field to a doctrine model and a matching schema slot, wires no producer, and
ships. Today the tests stay green and the field is inert indefinitely. After this story a test fails
and names the slot.

**Why this priority**: It is the only mechanism preventing a fourth inert register, and it guards
every field the downstream missions add. Rank 1 in the sequencing authority; gates on nothing.

**Independent Test**: Plant a producerless slot in a fixture tree and assert RED; assert GREEN on the
shipped tree.

**Acceptance Scenarios**:

1. **Given** a schema slot no code path writes, **When** the lint runs, **Then** it fails and names the slot and the model that declares it.
2. **Given** the shipped tree, **When** the lint runs, **Then** it passes.
3. **Given** a slot with a producer but no coverage gate, **Then** the lint reports it — C-009 requires both in the same commit.

---

### User Story 2 - An unknown kind or field fails loudly instead of vanishing (Priority: P1)

A contributor introduces a kind or a field the code does not recognise. At four sites the kind is
silently bucketed away or dropped. On `DRGNode`, `DRGEdge` and `AgentProfile` the field is silently
ignored.

**Why this priority**: This is the mechanism that would delete B1's and B2's new fields. C-010 makes
it non-negotiable that it lands first.

**Independent Test**: Plant an unknown kind at each of the four sites and an unknown field on each of
the three models; assert a raised error at every one.

**Acceptance Scenarios**:

1. **Given** an unknown kind at `query.py:230-242`, `charter/context.py:672-683`, `extractor.py:133-145` (`_KIND_MAP`) or `extractor.py:1210-1229` (the writers), **When** it is processed, **Then** it fails loudly.
2. **Given** an unknown field on `DRGNode`, `DRGEdge` or `AgentProfile`, **When** it is loaded, **Then** it is a **load error**, not silence.
3. **Given** a new field on `DRGEdge`, **When** it is written and read back, **Then** it survives the round trip. The writers are field-by-field, so this is the assertion that matters.

**Measured, not inherited** — verified on this branch 2026-07-26. The sequencing authority's figures
were a static read; these were executed:

| Site | Shape | Kinds lost |
|---|---|---|
| `query.py:230-242` | 16 `NodeKind` buckets filled, **10 read out** into the result | 6 |
| `charter/context.py:672-683` | 4 kind branches, **no `else`** | 12 |
| `extractor.py:133-145` (`_KIND_MAP`) | **11 of 16** `NodeKind` members mapped | **5** — `anti_pattern`, `asset`, `glossary`, `glossary_pack`, `glossary_scope` |
| `extractor.py:1210-1229` | field-by-field `_node_to_dict` / `_edge_to_dict` | any new field |

The `_KIND_MAP` gap is not academic: **mission C authors 2 anti-patterns and 4 assets**, both of
which that map drops. Without this fix C's series would validate, load, and then partly not exist.

---

### User Story 3 - The org→DRG bridge stops losing edges (Priority: P1)

A pack author declares an edge from a built-in artefact to a pack artefact. The bridge returns `None`
with no warning and no conflict record. A bare built-in target id is blindly re-kinded to a node that
may not exist. A URN-shaped target dies with a raw pydantic error instead of a typed pack error.

**Why this priority**: ADR 2026-07-26-3 is explicit — the bridge fix "must land before or with the
`Relation.IMPACTS` migration, or the new relation inherits a silent-drop path". Adding vocabulary to
leaking infrastructure is how a closed defect class regrows.

**Independent Test**: Each of the three shapes produces a typed error or a conflict record, never silence.

**Acceptance Scenarios**:

1. **Given** a built-in-source → pack-target edge that cannot resolve, **Then** it fails loudly with a conflict record.
2. **Given** the `urn:profile:` `specializes_from` snippet documented in `CLAUDE.md`, **When** a reader follows it, **Then** it produces an edge rather than an inert declaration.
3. **Given** a URN-shaped target that cannot resolve, **Then** the error is a typed pack error.

---

### User Story 4 - Guidance names files that exist (Priority: P2)

An operator hits `InlineReferenceRejectedError` and is told to edit `src/doctrine/graph.yaml` — a
file sharded out of existence by #2680. An author reads two operator-facing `SKILL.md` files telling
them to read `src/doctrine/<kind>/shipped/` — a pack layer that has never existed on disk.

**Why this priority**: Guidance that cannot be followed is worse than none. The operator either
guesses or re-adds an inline reference, propagating the confusion the programme exists to reduce.

**Independent Test**: Gates assert zero occurrences of each dead path in operator-facing strings.

**Acceptance Scenarios**:

1. **Given** a rejected inline reference, **Then** the hint names an existing per-kind `<kind>.graph.yaml` fragment.
2. **Given** the `graph.yaml` gate, **Then** it does **not** flag `.kittify/doctrine/graph.yaml` (a live project-tier path) or the deliberate mentions that name the dead path in order to forbid it.
3. **Given** the `shipped/` gate, **Then** it does **not** flag the prose "shipped/packaged", and every relative cross-link in built-in markdown resolves on disk.

---

### User Story 5 - Generated schemas match their models (Priority: P2)

`scripts/generate_schemas.py --check` exists, **exits 1 today with 7 stale schemas**, and is
referenced nowhere in `.github/`. A contributor has no signal that their model change left the schema
behind.

**Why this priority**: A verified gap with a live instrument — but wiring it as-is puts a red gate on
the branch and invites someone to "fix" it by accepting a regeneration that deletes valid schema.

**Independent Test**: `--check` exits 0 on the reconciled tree; a deliberate model change makes it exit 1.

**Acceptance Scenarios**:

1. **Given** the reconciled tree, **When** `--check` runs in CI, **Then** it exits 0.
2. **Given** a model field added without regenerating, **Then** CI fails and names the stale schema.
3. **Given** `structural_lint_config`, **Then** the generator **emits** it — it is a real declared field the generator currently drops, and accepting its deletion would invalidate a shipped artefact.

### Edge Cases

- **The `graph.yaml` grep gate false-reds on correct code.** `.kittify/doctrine/graph.yaml` is a live
  project-tier path, and several sites name the dead path deliberately in order to forbid it. The
  gate needs both discriminators or it fails on correct code.
- **The `shipped/` gate matches prose.** 22 hits across 9 files, and at least one
  (`model-to-task_type.yaml`: "shipped/packaged") is not a path. A bare string match over-reports.
  *(The parent spec says 21 across 8 — re-derived here as 22 across 9.)*
- **`applies` is not a dead sink.** The comment at `drg/merge.py:97-98` is **wrong**:
  `charter_runtime/lint/checks/orphan.py` reads it and `charter/synthesizer/project_drg.py` produces
  it. Do not build an "`applies` is dead" gate on that comment. The single existing `applies` edge is
  `agent_profile:doctrine-daphne --applies--> procedure:onboard-external-agent-to-pack`, and it is
  that procedure's only inbound edge, which makes daphne's own operating procedure unreachable.
- **The four-site fix collides with `#2532`** (decompose `charter/context.py`) — the missing `else`
  lives inside the module being decomposed. Pin the fix **behaviourally**, not by code shape, so it
  survives the split.
- **Accepting a schema regeneration blindly destroys valid schema.** Three divergence classes, only
  one safe: retired `enhances`/`overrides` (safe — finishes a half-done excision);
  `structural_lint_config` (a **generator bug** — fix the generator); `point_in_time_marker`
  (declared in no model, used by a shipped artefact — **adjudicate**, do not regenerate blindly).
  Also a `reference` → `paradigm_reference` rename whose `$ref` targets must be verified.
- **The occurrence-map guardrail cannot express B2's own exemptions.** `exceptions` are path globs,
  but all 17 GOVERNANCE files also carry MIGRATE entries and 5 of 7 RAW files do too. Field-path
  granularity is required, and C-004 forbids deferring it to a follow-up.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Parent | Title | Priority | Status |
|----|----|-------|----------|--------|
| FR-001 | FR-029 | **Zero-producer lint.** A schema slot with no producer fails a test. Rank 1; gates nothing; guards every field B1 and B2 add. | High | Open |
| FR-002 | NFR-013 | **Occurrence-map field-path granularity.** Extend `occurrence-map.schema.yaml` so `do_not_change` can name a YAML field path inside a file that also migrates. Legacy single-term maps keep validating. | High | Open |
| FR-003 | FR-030 | **Four-site silent-kind-drop closure.** Unknown kinds fail loudly at all four sites. Collides with `#2532` — pin behaviourally. Unblocks `#2468`/`#2847`/`#2862`/`#2829`. | High | Open |
| FR-004 | FR-031 | **`extra="forbid"` + writers + round-trip** on `DRGNode`, `DRGEdge`, `AgentProfile`. Model + writer + round-trip test in **one commit**. | High | Open |
| FR-005 | — | **Schema-generation integrity.** Fix the generator's `structural_lint_config` drop, adjudicate `point_in_time_marker`, verify the `paradigm_reference` `$ref` targets, regenerate the 7 stale schemas, then wire `--check` into CI. | Medium | Open |
| FR-006 | FR-004 | **Freeze the reference-kind enums** with a ratchet on the four member sets, not only a comment. | High | Open |
| FR-007 | — | **Layout gate second segment.** Validate `parts[0] == kind.plural` **and** `parts[1] == built-in`. | Medium | Open |
| FR-008 | FR-005 | **Correct the unfollowable migration hint** — the hint and its contract fixture name an existing per-kind fragment. | High | Open |
| FR-009 | FR-006, FR-020 | **Correct the surviving `shipped/` references**, enforced by a gate: the earlier fix-by-inspection missed 21 of 27. | High | Open |
| FR-010 | FR-021 | **Fix the org→DRG bridge** — silent cross-layer drop, blind re-kinding of bare targets, raw pydantic on URN-shaped targets. | High | Open |
| FR-011 | FR-022 | **Fix the documented `specializes_from` example** in `CLAUDE.md` so it produces an edge. | Medium | Open |
| FR-012 | FR-023 | **Retype daphne's `applies` edge and gate the relation.** | Medium | Open |

### Non-Functional Requirements

| ID | Parent | Requirement | Priority |
|----|----|-------------|----------|
| NFR-001 | NFR-001 | **Every gate is non-vacuous.** Each carries a self-mutation test planting the real violation shape and asserting RED, plus a zero-entry allowlist. A gate-unmask cannot self-validate. | High |
| NFR-002 | NFR-012 | **No `applies` edge is authored** — enforced by a gate built on measurement, not on the wrong comment at `drg/merge.py:97-98`. | Medium |
| NFR-003 | — | **Both path gates carry their discriminators**, each proven by a fixture that would false-red without it. | High |
| NFR-004 | — | **No graph content change.** Node/edge/orphan counts move by exactly 0, except FR-012's `applies` retype — a ledgered relation change at constant cardinality. | High |

### Constraints

| ID | Constraint | Priority |
|----|------------|----------|
| C-001 | **C-009** — no new schema slot without a producer *and* a coverage gate in the same commit. FR-001 is the mechanism, and it binds itself. | High |
| C-002 | **C-010** — this mission lands before B1. `extractor.py:133-145` and `:1210-1229` would silently delete a new edge field. | High |
| C-003 | **C-007** — never run the full `tests/architectural/` suite; targeted single-file runs only. | High |
| C-004 | **C-006** — the 6 inherited `arch-adversarial` reds stay red. `quality-gate` fails only as their cascade. | High |
| C-005 | **C-004** — no structural defect found here is handed to a follow-up. This is why FR-002 is in scope. | High |
| C-006 | **Charter C-011** — ATDD: each WP lands a failing-first test as its first commit, RED on the planning base and GREEN at the WP's final commit. | High |

### Key Entities

- **Zero-producer lint**: a test asserting every declared schema slot has at least one writer.
- **Silent-drop site**: a branch that discards an unrecognised kind without raising or logging.
- **Occurrence map**: the DIRECTIVE_035 per-mission classification artefact; gains field-path granularity here.
- **Layout gate**: the architectural test pinning `<type>/<pack>/[<category>/]<name>`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (SC-021): The zero-producer lint fails on a planted producerless slot and passes on the shipped tree, so `aliases`, `impacts` and `is_symmetric` cannot ship inert.
- **SC-002** (SC-023): An unknown kind fails loudly at all four sites, proven by a planted unknown kind at each.
- **SC-003** (SC-022): An unknown field on `DRGNode`/`DRGEdge`/`AgentProfile` is a load error, and a round-trip test proves a new field survives write→read.
- **SC-004**: `scripts/generate_schemas.py --check` exits **0** and runs in CI. `structural_lint_config` is emitted; `point_in_time_marker` has a recorded adjudication.
- **SC-005** (SC-018): Adding a member to any of the four `<kind>_reference.type` enums fails a test.
- **SC-006** (SC-016): The layout gate validates both mandatory segments — a tactic under `assets/built-in/` is rejected. Allowlist: exactly 0 entries.
- **SC-007** (SC-003): Zero source sites instruct an operator to edit `src/doctrine/graph.yaml`, and the gate does not flag the live project-tier path or the forbidding-mentions.
- **SC-008** (SC-015): Zero `<kind>/shipped/` path references remain under `src/doctrine/`; every relative cross-link in built-in markdown resolves; the gate does not flag "shipped/packaged".
- **SC-009**: An unresolvable built-in→pack edge produces a conflict record, never `None`-with-silence. The `CLAUDE.md` snippet produces an edge.
- **SC-010**: `procedure:onboard-external-agent-to-pack` has a traversable inbound edge, and a gate rejects a newly-authored `applies` edge.
- **SC-011**: An occurrence map can mark a YAML field path `do_not_change` inside a file that also carries migrating entries — demonstrated against B2's real exemption set (188 GOVERNANCE + 14 RAW).
- **SC-012**: Node, edge and orphan counts are unchanged by this mission, except the single ledgered `applies` retype.
