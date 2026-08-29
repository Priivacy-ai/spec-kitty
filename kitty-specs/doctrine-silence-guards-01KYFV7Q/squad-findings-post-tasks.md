# Post-tasks adversarial squad — findings and disposition

**Date**: 2026-07-26 · **Point-cut**: post-tasks (anti-laziness) · **Mission**: A, doctrine-silence-guards-01KYFV7Q

**Question put to the squad**: *Which of Mission A's ten work packages can be marked done without
actually closing the silence it claims to close?*

**Lenses** (profile-loaded, read-only, bounded at four): `reviewer-renata` (fakeable DoDs, opus) ·
`debugger-debbie` (live-evidence reproduction, opus) · `paula-patterns` (decomposition and ownership,
sonnet) · `architect-alphonso` (seams and ordering, sonnet).

A mission made almost entirely of gates is maximally exposed to its own thesis. It shipped three
mechanisms that could not fail. The squad earned its tokens.

---

## Convergent findings — fixed in this branch

### 1. The ordering existed only as prose *(Paula BLOCKER, Renata BLOCKER — reproduced)*

All ten WPs carried `dependencies: []`; every lane carried `depends_on_lanes: []` and
`parallel_group: 0`. `_parse_dependencies_from_tasks_md` accepts `Depends on WPxx` or
`Dependencies: WPxx` inline — the manifest used a `### Dependencies` heading with prose beneath,
which matches neither. So the claim gate would have let any WP be claimed in any order, including
WP04 before WP03 and WP10 before WP05.

**This is the mission's own defect class in the mission's own artefacts**: a producer/consumer
mismatch where the prose says one thing and the machine-readable surface says nothing.

**Fixed** — every dependency rewritten to the parsed form. `lanes.json` now carries real
`depends_on_lanes` and `parallel_group` 0→4, so the claim gate enforces the order:
`WP02←WP01 · WP03←WP01 · WP04←WP03 · WP05←WP01 · WP06←WP01,WP05 · WP07←WP01,WP04 · WP08←WP04 · WP09←WP08 · WP10←WP01,WP05`.

**A second trap sat behind the first, and it is the same defect class again.** Rewriting the manifest
was not enough: `mission_finalize.py:481` treats an existing `dependencies` frontmatter field as
*explicit author intent* and refuses to overwrite it. The first finalize had written
`dependencies: []` into all ten files, and that tool-authored default then became indistinguishable
from a deliberate "this WP depends on nothing" — so three subsequent finalize runs reported
"Updated 0 WP files with dependencies" while the manifest parsed correctly the whole time. The fix
was to write the values into the frontmatter directly. **A silent default that hardens into an
authority is exactly what this mission exists to close**, and it cost four finalize cycles to see.
Worth filing upstream: the tool cannot distinguish "author said none" from "tool wrote none".

### 2. WP01's slot/producer definition was self-annihilating *(Renata BLOCKER)*

The adopted text read *"a slot is both a model field **and** a JSON-Schema property; a producer is
any writer under `src/` **or the generated schemas**."* Slots ⊆ schema properties, producers ⊇
generated schemas ⇒ **every slot has a producer by construction**. The lint returns the empty set on
any tree and its zero-entry allowlist passes vacuously. The gate meant to prevent a fourth inert
mechanism *was* the fourth inert mechanism.

**Fixed** — producer redefined as *a code path under `src/` that assigns the field on an object which
is subsequently serialised*; **the generated schemas are explicitly not producers**. Two live
calibration anchors named, chosen because they pull in opposite directions:
`point_in_time_marker` (schema property, no model — invisible under the old intersection reading) and
`structural_lint_config` (declared, read-only — flagged under a strict writer reading, while WP05
simultaneously defends it). WP01's docstring must adjudicate both, and WP01/WP05 may not land
contradictory verdicts on the same field.

### 3. A third of WP06 was already delivered *(Renata BLOCKER — reproduced)*

`tests/architectural/test_doctrine_artefact_layout.py:106` already reads
`parts[0] == kind.plural and parts[1] == _PACK_DIR`; `_ALLOWLIST` is already `frozenset()`;
`test_allowlist_is_empty` already exists. **17 passed.** The fix landed in `1a15bcf6c`.

My error, not a squad discovery about the code: the parent spec's SC-016 was inherited as Open and
this was the one figure the plan's "Measured ground truth" table did **not** re-measure.

**Fixed** — FR-007 and SC-006 withdrawn; T029/T030 struck; WP06 is the enum ratchet only.

### 4. WP07 could not meet its own success criterion inside its boundary *(Paula BLOCKER, Renata HIGH)*

`grep -rl "src/doctrine/graph\.yaml" src/` returns **17 files**; WP07 owned 9.
`InlineReferenceRejectedError` is defined in `src/doctrine/shared/exceptions.py` and the hint is
built in `src/doctrine/shared/errors.py` — **neither owned by any WP**, so T035 was unreachable.

**Fixed** — WP07 gains both, plus `styleguides/models.py`, `common-docs-find.tactic.yaml`,
`brownfield-onboarding.paradigm.yaml`, `charter/schemas.py`, `calibration/walker.py`, and the
contract fixture that hard-pins the dead path in its regex.

### 5. My WP07-last sequencing rested on two phantoms *(Paula HIGH, Renata MEDIUM — reproduced)*

Of the three files I cited as an ownership collision: `drg/merge.py:29` says "shipped" as **prose**,
and `doctrine-daphne.agent.yaml:129` names the dead path **in order to forbid it**. Both are exactly
the cases T034/T037's discriminators must *not* flag — fixture material, not edits. Only
`agent_profiles/profile.py` was real, and it is WP04's file.

**Fixed** — WP04 takes that one line (T023a); WP07 depends on WP01+WP04 and the schedule cost of
running last is withdrawn.

### 6. The writer site was filed under the wrong concern *(Alphonso HIGH)*

**Note on the resulting seam.** Alphonso's fix collided with the ownership validator, which forbids
two WPs sharing a file. Since C-009 requires the model, the writer and the round-trip in **one
commit**, `extractor.py` had to belong to WP04 — so `_KIND_MAP` (T015) moved there too. WP03 is now
"the two consumer sites" (`query.py`, `charter/context.py`) and WP04 is "the extractor and the models
it serialises". That is a cleaner cut than the original four-site framing, which had grouped a field
concern with three kind concerns because they shared a filename.

`_edge_to_dict` never branches on `NodeKind` — Pydantic guarantees a valid enum before it runs. It is
a **field**-drop site, not a kind site, and WP03's own table gave it away by listing "Kinds lost: any
new field".

**Fixed** — T016 moved from WP03 to WP04, which now owns `extractor.py` and lands it in the same
commit as the model and round-trip.

### 7. "Absent on all three" was a static-read error *(Alphonso MEDIUM — reproduced)*

`AgentProfile` **does** declare `model_config` (`profile.py:254`), and sibling `ContextSources:181`
already uses `extra="forbid"`. Only `DRGNode`/`DRGEdge` lack it.

**Fixed** in the measured-ground-truth table. Worth noting the irony: the table's own preamble claims
every figure was executed.

### 8. NFR-001 claimed universality and was assigned to two WPs *(Renata HIGH)*

Eight gates ship across six WPs; only WP01/T004 and WP10/T053 carried explicit self-mutation
subtasks. Worse, NFR-001 never required the self-mutation test to invoke **the same callable** as the
shipped-tree assertion — without that it is a one-time proof, not a tripwire against later weakening.

**Fixed** — NFR-001 now names all six gate-adding WPs and requires the same-callable property.
WP06/T033 and WP09/T048 gain self-mutation subtasks.

### 9. WP10's meta-test permitted the vacuity it exists to close *(Renata HIGH)*

T052 said only "union of per-job collections vs the full collection". Computing that union with all
jobs *assumed to run* yields a complete union today, a green gate, and an untouched gap — the same
"scoped to the split, not the tree" error one level up, and it disarms T055's report-don't-mask
instruction on the way past.

**Fixed** — T052 must evaluate with every `changes.outputs.*` **false** and source from a real
`pytest --collect-only` subprocess, not declared globs.

### 10. WP09's gate was the cheapest fake in the mission *(Renata HIGH)*

After T047 retypes the one authored edge, the authored `applies` count is 0 — so a gate globbing the
wrong path finds zero and passes forever.

**Fixed** — T048 gains a positive floor (assert N fragment files scanned) and a planted-`applies`
self-mutation.

### 11. WP02's SC-011 had no owned artefact *(Renata HIGH)*

SC-011 requires demonstration against B2's real exemption set, but B2's `occurrence_map.yaml` was in
no WP's ownership — so the cheapest pass was a throwaway fixture labelled "B2's exemption set".

**Fixed** — B2's map added to WP02's `owned_files`.

---

## Accepted, not yet actioned

| # | Finding | Disposition |
|---|---|---|
| 12 | **The three historical inert cases are never named** (Renata HIGH). A calibration set that does not exist is unfalsifiable — the implementer picks three that flatter their definition. | T001 should **derive** the historical set mechanically and record it, rather than cite a count. Recorded here; fold at implementation. |
| 13 | **WP03's declared test surface runs no charter test** (Renata MEDIUM), while T014 changes `src/charter/activation/context.py`. There is also a frozen contract (`resolve-transitive-refs.contract.md:89`) stating unresolved entries are *recorded, not raised* — in direct tension with "make the shortfall loud". | Real, and the contract tension is the sharper half. Adjudicate before changing raise/record semantics. |
| 14 | **The `applies` rebuttal is half-true** (Renata MEDIUM). `orphan.py`'s `_ORPHAN_RULES` keys only on `directive` and `glossary_scope`; the one authored edge targets a **procedure**, so for *that* edge the "no traversal reads it" comment is correct. | Restate the edge case: wrong as a general invariant, right about this specific edge. WP09 should not build on the half-truth. |
| 15 | **SC-010's witness is unnamed** (Renata MEDIUM) — "a traversable inbound edge" is satisfiable by a relabel. | Name the target relation in FR-012 and a consumer function whose output changes. |
| 16 | **WP10 does not reconcile with two existing authorities** (Renata MEDIUM): `test_src_filter_coverage.py` and `test_ci_quality_path_filters.py` already exist, and the former was green while #2957's hole was open. | WP10 must argue why it is a new file rather than an extension, per single-canonical-authority. |
| 17 | **WP10 is arguably out of the mission's charter** (Alphonso MEDIUM) — joined by defect *shape*, not shared code, and it gates nothing downstream. | Operator call. Kept for now: the shape argument is the mission's whole thesis, and C-005 discourages spinning out what this mission found. |

## Not accepted

**WP07 should be split into three** (Paula MEDIUM). With the ownership gap closed and the phantom
sequencing withdrawn, WP07 is one coherent concern — "no guidance names a path that does not exist" —
with two gates sharing a discriminator design. Splitting would duplicate that design across WPs. Kept
as one, with the size acknowledged.

## 12. Debbie's addendum — the most consequential findings of the pass *(all reproduced)*

Her lens landed last and it revised WP10 from "soundest package in the mission" to *"right mechanism,
wrong scope, with an open greenwashing path."* Four things, all verified independently here:

- **One of my own claims was false.** The plan said "four test files were red on `main` while main CI
  reported green." Run `30212948549` concluded **failure** — confirmed via `gh run view`. A reviewer
  disproves that sentence in one command. The true and stronger claim is that the three `cli`-gated
  jobs were **skipped**, so the reds were *structurally uncollectable* rather than merely unnoticed.
  Corrected in the plan.
- **The gap is ~3.6× the scoped size.** Measured two ways that agree exactly (58 real per-job
  `--collect-only` runs; the repo's own `_gate_coverage.load_gates`): **950 of 2166 files, 14,870 of
  33,665 nodes (44%)** uncollected on that commit, across 21 roots. `cli` is one of 24 dorny groups
  with identical semantics — it was never special. Restated in FR-013/SC-013 with the baseline.
- **A sanctioned greenwashing path is already paved on WP10's route.** `test_gate_coverage.py`'s own
  assertion message ends *"regenerate the baseline with `--update-baseline`"* (`:603`, `:627`). Adding
  gating-awareness yields ~950 orphans and one documented command to erase them. WP10 is now required
  to be **baseline-free**.
- **SC-013 as worded was unachievable** — "union equals the full collection" is only satisfiable by
  dismantling a dorny topology that ~17 invariants pin. Narrowed to *every test node collected by ≥1
  job on a push to main*, implemented with the `|| github.event_name == 'push'` disjunct the workflow
  already uses twice (`:2747`, `:2972`). Note **node, not file**: three of #2957's four files hold a
  `slow` test that satisfies a file-level reading while their fast tests never run.

Also folded: the fix substrate already exists (`job_gating_groups` at `_gate_coverage.py:457`) so WP10
must extend `analyze()` rather than write a parser; the naive fix would red
`test_every_named_group_gates_a_test_running_job_live`; and WP10's own new test file is inert unless
registered in `tests/_arch_shard_map.py`.

She also falsified her own hypothesis rather than leaving it hanging: the `push`-vs-`pull_request`
nuance does **not** rescue the workflow — dorny gets no `base:`/`ref:`, so a default-branch push does
a genuine `git diff before..HEAD` with no true-for-all fallback. Recorded so it is not re-litigated.

## Open question that may be a separate P0

Debbie read job *conclusions*, not failure bodies, on run `30212948549`. **Whether the
`arch-adversarial` ×3 and `slow-tests` reds there are the six inherited reds C-004 protects is
unconfirmed.** If they are not, that is a separate P0 and the charter's Pre-existing Failure
Reporting Rule applies. C-003 forbids running `tests/architectural/` as a directory to check locally,
so this needs a targeted read of the run's failure output. **Not resolved here.**

## Still outstanding

Nothing — all four lenses reported. Her lens is live reproduction of the
four motivating defects; the other three lenses independently reproduced the measured figures
(`311/774`, `_KIND_MAP` 11/16, `query.py` 16→10, `context.py` no-`else`, `--check` exits 1 with 7
stale, `shipped/` 22 across 9, inventory 559/188/14), so the table is corroborated three ways. Her
findings are to be folded on arrival.

## What the squad did not change

Every figure in the plan's measured-ground-truth table reproduced exactly under independent
re-execution, in three separate lenses — **except** the layout gate, which was the one row never
measured. That is the lesson worth keeping: the table was honest wherever it was run, and wrong
exactly where it was inherited.
