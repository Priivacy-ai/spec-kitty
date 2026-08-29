---
title: "Inline Reference Inventory — the six surfaces and their dispositions"
description: "Reproducible inventory of every inline relationship-bearing field under src/doctrine, classified into migrate / governance / raw-material, with the counting rule."
doc_status: active
updated: '2026-07-26'
related:
- docs/adr/3.x/2026-07-26-1-drg-edges-are-the-canonical-relationship-authority.md
- kitty-specs/doctrine-canonical-structure-remediation-01KYEYSD/spec.md
---
# Inline Reference Inventory

Derivation: `scripts/doctrine/inline_reference_inventory.py` (run with `PYTHONPATH=src`).
The numbers below are **generated**, not asserted. The gate for FR-015 imports that module
rather than restating a literal.

## Why this document exists

The inventory was hand-measured twice and wrong both times. That matters more than the
numbers, because the same two errors were about to be written into a migration:

1. The first count read only **top-level** `references:`. It missed **15 step-level entries**
   inside `steps[]`, across 13 step positions in 7 tactic files — and **4 of those files carry
   no top-level `references:` block at all**. A migration driven off "the files that have a
   `references:` block" would never have opened them, silently stripping 15 relationships.
2. Neither count knew there were **six** surfaces. Five siblings of `references:` exist, two of
   which are actively hazardous to touch (below).

A spec that hardcodes a count nobody can reproduce makes its own completion gate
unfalsifiable — it pins whatever the author happened to count that day. Hence a script.

## Measured inventory

```
files touched: 171
total entries: 761

field                               MIGRATE  GOVERNANCE   RAW
context-sources.additional                0          54     0
context-sources.directives               67           0     0
context-sources.doctrine-layers           0          47     0
context-sources.tactics                   0          19     0
directive-references                      0          68     0
directive_refs                           34           0     0
references                              414           0    14
steps[].references                       15           0     0
tactic-references                        29           0     0

TOTAL                                   559         188    14
```

Corroboration: three independent measurements agree on 559 — this script, and two adversarial
review lenses that reached it by *ablation* (deleting each surface from a tree copy and
observing the edge-count delta). The earlier figure of 414 is now explained: it is exactly the
top-level `references:` row, correct as far as it went and mistaken as a total.

## The three dispositions

### MIGRATE — 559 entries

Denote an artefact→artefact relationship that the extractor turns into a DRG edge. These move
to the authored-edge tier. Five fields, and they do **not** share a shape — a migration keyed
on "`{type, id}` dicts" silently misses 130 of them:

| Field | Entries | Shape |
| --- | --- | --- |
| `references` (top-level) | 414 | 357 `{type, id}` dicts + 57 resolvable path strings |
| `steps[].references` | 15 | `{type, id}` dicts nested inside steps |
| `context-sources.directives` | 67 | bare id list (agent profiles) |
| `directive_refs` | 34 | bare id list (paradigms) |
| `tactic-references` | 29 | `{id, rationale}` dicts (agent profiles) |

### GOVERNANCE — 188 entries — DO NOT MIGRATE

`directive-references` (68) and `context-sources.{additional, doctrine-layers, tactics}` (120)
on agent profiles. These produce **zero** DRG edges, so every graph-shaped assertion is blind
to them — and `directive-references` is the **seed set for the entire charter governance
closure**: `src/charter/activation/resolver.py` reads `profile.directive_references` and feeds it to
`resolve_references_transitively`, whose output populates the directives/tactics/styleguides
/toolguides/procedures rendered into the prompt an agent actually reads.

Deleting them would empty every profile-routed dispatch's governance while byte-identical
fragments, golden counts, and a zero-structured-entries gate all stayed green. That is this
mission's own defect class — silence — and it is why FR-013 must name its surfaces explicitly
instead of saying "all inline relationships".

Their disposition is **out of scope for this mission**, retained as-is. Whether governance
seeding should eventually route through the graph is a separate question with its own
migration; it is not a relationship-residue cleanup.

### RAW_MATERIAL — 14 entries — KEEP

Path strings pointing at non-artefact files: `src/doctrine/skills/README.md`, `docs/adr/...`,
Divio templates, an action `index.yaml`. `_resolve_path_ref` fails closed on them by design
(NFR-003 of its own mission: never infer identity from an unrecognised path), they produce no
edge, and `src/doctrine/README.md` sanctions carrying raw reference material.

Forcing these into edges would invent relationships that do not exist — the same category
error as widening the reference-kind enum, which is the mistake that started this mission.

**The exemption is enumerated, not computed.** A predicate of the form "does not resolve to a
built-in artefact" is gameable two ways that are already present in the tree: point at an
artefact's markdown payload instead of its YAML (`POWERSHELL_SYNTAX.md` is a toolguide's
content), or point at a mission-tier kind (templates have an empty glob, so every
styleguide→template reference classifies as raw material). The gate therefore carries the 14
exact `(file, path)` pairs with a reason each, and changing the list requires a ledger line.

## Content the DRG cannot hold

Migrating an entry is not lossless. Three kinds of authored content have no edge equivalent:

| Content | Count | Status today |
| --- | --- | --- |
| Procedure `reason:` rationale | 68 | **Already dropped** by the extractor — `procedure.graph.yaml` contains 0 `reason:` lines, though `DRGEdge.reason` exists and the paradigm pass populates it |
| Tactic reference `name:` label | 219 | Never read. Schema marks it **required**, so the schema mandates information the canonical surface cannot store |
| Step provenance + authored order | 15 steps | Step-level edges are emitted from the *tactic's* URN, so "which step" is unrecoverable; edges are sorted by `(source, target, relation)`, so authored sequence is replaced by alphabetical |
| `when:` condition | 219 | **Preserved** — `DRGEdge.when` exists and is populated; verified 219 authored values → 219 `when:` lines, zero loss |

Operator decision (2026-07-26): **preserve the 68 rationales and the 219 labels**, accepting
that this breaks pure byte-identity. The correctness proof is therefore a *structured* diff
invariant — "the regenerated set differs from the baseline only in this enumerated, ledgered
set of additions" — not a byte comparison. Byte-identity would have actively pressured the
migrator into deleting authored content to make the proof pass.

## Relation inference is keyed on SOURCE kind

The relation an entry becomes is a function of the **source artefact's kind**, not the
reference's `type`. A migration keyed on ref type alone mis-types **118 of 372** structured
entries (32%):

| Source kind | Ref type | Relation |
| --- | --- | --- |
| directive | `directive` | `requires` |
| directive | anything else | `suggests` |
| tactic (top-level *and* step-level) | **any**, including `directive` | `suggests` (hardcoded) |
| paradigm | `directive` / `tactic` / `procedure` | `requires` |
| paradigm | anything else | `suggests` |
| procedure | `directive` / `tactic` / `procedure` | `requires` |
| procedure | anything else | `suggests` |
| styleguide / toolguide (path form) | any resolved | `suggests` |

Note the paradigm pass calls a helper named `_relation_for_procedure_ref_type`, whose
docstring describes procedures — misleading at that call site, and the kind of thing that
makes the per-ref-type misreading attractive.

### The 55 laundered inferences

55 entries become `tactic --suggests--> directive` purely because the tactic pass hardcodes
`SUGGESTS`. A directive is binding, so "suggests" is arguably wrong — and migrating them writes
an *inference artifact* down as though it were authored intent, after which it is
indistinguishable from a deliberate choice. FR-013's stated goal is that "authored intent and
edge type stop living in different files"; mechanising these would defeat it.

Operator decision (2026-07-26): **flag all 55 for human review** rather than mechanising them.
Wherever review changes a relation, the change is a ledgered deviation from the baseline.
