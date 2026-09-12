---
description: "Work package task list for the doctrine silence guards mission"
---

# Work Packages: Doctrine Silence Guards

**Inputs**: [`spec.md`](spec.md) (FR-001…FR-013, NFR-001…005, C-001…006, SC-001…013), [`plan.md`](plan.md) (IC-01…IC-08)
**Prerequisites**: plan.md ✅
**Programme record**: [`doctrine-canonical-structure-remediation-01KYEYSD`](../doctrine-canonical-structure-remediation-01KYEYSD/plan.md)
**Working branch**: `remediation/doctrine-silence-guards` → draft PR to `main`; the operator merges.

**Tests**: mandatory. Every WP lands a **failing-first** test as its first commit (charter C-011).
For WP01, WP03 and WP04 the RED *is* the deliverable — it is the proof the silence existed.

**Organization**: subtasks (`Txxx`) roll up into work packages (`WPxx`). Subtasks are reference rows,
not checkboxes — record completion with `spec-kitty agent tasks mark-status <Txxx> --status done`.

> ⚠️ **Never run the full `tests/architectural/` directory** (C-003) — a known harness issue kills the
> session. Targeted single-file runs only. The 6 inherited `arch-adversarial` reds stay red (C-004).

---

## Work Package WP01: Zero-producer lint (Priority: P0) 🎯

**Goal**: A schema slot with nothing producing it fails a test.
**Independent Test**: Plant a producerless slot in a fixture tree → RED. Run against the shipped tree → GREEN.
**Prompt**: `/tasks/WP01-zero-producer-lint.md`
**Requirement Refs**: FR-001, NFR-001, C-001, SC-001

### Included Subtasks

T001 Define "slot" and "producer" in the module docstring; calibrate against the three known-inert historical cases
T002 Failing-first test: plant a producerless slot in a temp tree, assert the lint reports it
T003 Implement the lint in `tests/architectural/`
T004 Self-mutation test (NFR-001): the lint's own gate rejects a planted violation
T005 Assert GREEN on the shipped tree with a zero-entry allowlist

### Implementation Notes

This is **first** and it guards every WP after it. Rank 1 in the sequencing authority; the only thing
mechanically preventing a fourth inert register — the precedent is 3-for-3, one green for 162 days.

**Deferred planning question to settle in T001**: is a "slot" a model field, a JSON-Schema property,
or both? Recommendation: both, with the producer search spanning `src/` writers and the generated
schemas. Too narrow passes everything; too broad false-reds on legitimately read-only fields.

### Dependencies

**Depends on**: none — starting package.

### Risks & Mitigations

A lint whose definition is wrong is worse than none, because it looks like coverage. Mitigate by
calibrating against real historical inert slots, not invented fixtures.

---

## Work Package WP02: Occurrence-map field-path granularity (Priority: P1)

**Goal**: `do_not_change` can name a YAML field path inside a file that also carries migrating entries.
**Independent Test**: Express mission B2's real exemption set (188 GOVERNANCE + 14 RAW) in a map; assert legacy single-term maps still validate.
**Prompt**: `/tasks/WP02-occurrence-map-field-paths.md`
**Requirement Refs**: FR-002, C-005, SC-011

### Included Subtasks

T006 Failing-first test: a field-path exemption in a mixed file is currently inexpressible
T007 Extend `src/doctrine/schemas/occurrence-map.schema.yaml` with field-path granularity
T008 Update `src/specify_cli/bulk_edit/occurrence_map.py` loader + admissibility
T009 Update `src/specify_cli/bulk_edit/diff_check.py` compliance check
T010 [P] Update `src/doctrine/templates/occurrence-map-template.yaml` and its docs
T011 Backward-compatibility test: legacy single-term maps validate unchanged

### Implementation Notes

The guardrail cannot currently express its own mission. `exceptions` are path globs, but **all 17**
of B2's GOVERNANCE files also carry migrating entries and **5 of 7** RAW files do too, so no
file-level cut separates them.

C-005 is why this is here rather than in B2: deferring it converts a known defect into an invisible
one, and having B2 author its own guardrail would be self-validation.

### Dependencies

**Depends on WP01** — so the new schema slots are covered by the zero-producer lint.

---

## Work Package WP03: Silent-kind-drop closure — consumer sites (Priority: P0)

**Goal**: An unknown kind fails loudly at the two consumer sites (`query.py`, `charter/context.py`). The two `extractor.py` sites moved to WP04 — see its notes.
**Independent Test**: Plant an unknown kind at each site; assert a raised error at every one.
**Prompt**: `/tasks/WP03-silent-kind-drop.md`
**Requirement Refs**: FR-003, NFR-004, C-002, SC-002

### Included Subtasks

T012 Failing-first test: plant an unknown kind at each of the four sites, assert current silence
T013 Close `src/doctrine/drg/query.py:230-242` — 16 buckets filled, 10 read out
T014 Close `src/charter/context.py:672-683` — 4 branches, no `else`. **Pin behaviourally** (see risks)
T017 Assert the graph invariant: 311 nodes / 774 edges unchanged (NFR-004)

### Implementation Notes

Measured, not inherited: `_KIND_MAP` drops **`anti_pattern`, `asset`, `glossary`, `glossary_pack`,
`glossary_scope`**. Verified that **no** artefact currently references any of them, so closing the map
is graph-neutral today — the drop is **latent, not harmless**. It goes live when mission C authors 2
anti-patterns and 4 assets.

### Dependencies

**Depends on WP01.** Blocks WP04, and blocks missions B1, B2 and C.

### Risks & Mitigations

**Collides with `#2532`** (decompose `charter/context.py`) — the missing `else` lives inside the module
being split. **Assert it behaviourally, not by code shape**, so the decomposition cannot drop it.
Cross-reference both issues.

If closing `_KIND_MAP` *does* move the graph count, that is a finding to ledger — not a number to bump.

---

## Work Package WP04: `extra="forbid"` + writers + round-trip (Priority: P0)

**Goal**: An unknown field on `DRGNode`, `DRGEdge` or `AgentProfile` is a load error, not silence.
**Independent Test**: Unknown field → raises. New field → survives write→read.
**Prompt**: `/tasks/WP04-extra-forbid-and-writers.md`
**Requirement Refs**: FR-004, C-001, SC-003

### Included Subtasks

T018 Failing-first test: an unknown field is currently accepted silently on all three models
T019 Add `model_config = ConfigDict(extra="forbid")` to `DRGNode` and `DRGEdge`
T020 Add the same to `AgentProfile`
T021 Round-trip test: a new `DRGEdge` field survives `_edge_to_dict` → read
T015 Close `src/doctrine/drg/migration/extractor.py:133-145` — `_KIND_MAP`, 11 of 16 kinds. **Moved here from WP03**: the ownership map forbids two WPs sharing `extractor.py`
T016 Close `src/doctrine/drg/migration/extractor.py:1210-1229` — the field-by-field writers. **Moved here from WP03**: `_edge_to_dict` never branches on `NodeKind`, so it is a *field*-drop site, not a kind site. Lands in the same commit as T019–T021
T022 Coverage gate proving the round-trip is exercised, per C-001
T023a Fix the dead `src/doctrine/graph.yaml` reference in `agent_profiles/profile.py` — this WP owns the file, so the one-line correction lands here instead of overlapping WP07's sweep

### Implementation Notes

**Model + writer + round-trip land in ONE commit.** This is the mechanism that makes B1's `impacts` /
`is_symmetric` and B2's `aliases` real rather than inert. Verified: none of the three models declares
`model_config` today, and the writers enumerate fields by hand.

### Dependencies

**Depends on WP03.** Blocks WP08, and blocks missions B1 and B2.

---

## Work Package WP05: Schema-generation integrity (Priority: P1)

**Goal**: `scripts/generate_schemas.py --check` exits 0 and runs in CI.
**Independent Test**: `--check` exits 0 on the reconciled tree; a model change without regeneration makes it exit 1.
**Prompt**: `/tasks/WP05-schema-generation-integrity.md`
**Requirement Refs**: FR-005, SC-004

### Included Subtasks

T023 Failing-first test: `--check` exits 1 with 7 stale schemas
T024 **Fix the generator** so it emits `structural_lint_config` (a real declared field it drops)
T025 Adjudicate `point_in_time_marker` — declared in no model, used by a shipped artefact. Decide, record, do not regenerate blindly
T026 Verify the `reference` → `paradigm_reference` rename's `$ref` targets resolve
T027 Regenerate the 7 stale schemas
T027a **Clear WP05's 8 entries from `_inert_slots_baseline.json`.** WP01's lint independently found what T024 was already scoped to fix: the four schemas advertise `enhances` while the models **raise** on it (`_RETIRED_RELATIONSHIP_FIELDS`), so the schema documents a shape the loader rejects. `overrides` is the same defect, masked in the report by an unrelated name collision. **This WP cannot reach `done` with those entries outstanding** — SC-001a enforces it by test.

> `--check` is wired into CI by **WP10/T056**, which owns the workflow file.

### Implementation Notes

Three divergence classes, only one safe to accept: retired `enhances`/`overrides` (**accept** —
finishes a half-done excision); `structural_lint_config` (**generator bug — fix the generator**;
accepting the deletion invalidates `common-docs.styleguide.yaml`); `point_in_time_marker`
(**adjudicate**).

Wiring the gate before this reconciliation would put a red gate on the branch and invite someone to
"fix" it by accepting a regeneration that deletes valid schema.

### Dependencies

**Depends on WP01.** Independent of WP02/03/04. WP10 wires its CI step.

---

## Work Package WP06: Layout gate second segment + enum ratchet (Priority: P2)

**Goal**: A right-pack/wrong-type file is rejected; adding a reference-enum member fails a test.
**Independent Test**: A tactic under `assets/built-in/` is rejected; a planted enum member fails.
**Prompt**: `/tasks/WP06-structural-ratchets.md`
**Requirement Refs**: FR-006, FR-007, NFR-001, SC-005, SC-006

### Included Subtasks

T031 Failing-first test: a member added to a `<kind>_reference.type` enum currently passes
T032 Ratchet the four enums' member sets — **derive the baseline once, commit it as a literal**, then assert equality. A ratchet that re-reads the enums at test time cannot fail (charter `frozen-baseline-shrink-only-ratchet`)
T033 Self-mutation test (NFR-001): plant an enum member, assert RED — invoking the **same callable** as the shipped-tree assertion

> **T029/T030 withdrawn — already delivered.** `test_doctrine_artefact_layout.py:106` already reads
> `parts[0] == kind.plural and parts[1] == _PACK_DIR`, `_ALLOWLIST` is already `frozenset()`, and
> `test_allowlist_is_empty` already exists. Verified: **17 passed**; the fix landed in `1a15bcf6c`.
> The parent spec's SC-016 was inherited as Open without re-measuring — a planning error the squad
> caught. What remains here is the enum ratchet only.

### Dependencies

**Depends on WP01, WP05.** WP05 regenerates the four schemas whose enums this WP ratchets, so the baseline must be pinned after that lands.

---

## Work Package WP07: Followable guidance + discriminating gates (Priority: P2)

**Goal**: No source site names a path that does not exist, enforced by gates that do not false-red.
**Independent Test**: Both gates pass on the corrected tree and fail on a planted regression, without flagging the three known legitimate cases.
**Prompt**: `/tasks/WP07-followable-guidance.md`
**Requirement Refs**: FR-008, FR-009, NFR-003, SC-007, SC-008

### Included Subtasks

T034 Failing-first test for the dead `src/doctrine/graph.yaml` path, **with** its two discriminators
T035 Correct the `InlineReferenceRejectedError` hint and its contract fixture to name a real per-kind fragment
T036 Correct the ~10 remaining dead-path sites
T037 [P] Failing-first test for `<kind>/shipped/`, **with** its path-shape discriminator
T038 [P] Correct the 22 `shipped/` hits across 9 files, incl. two `SKILL.md` and a glossary term body
T039 Assert every relative cross-link in built-in markdown resolves on disk
T040 Discriminator fixtures: each gate would false-red without them (NFR-003)

### Implementation Notes

**Both gates need discriminators or they fail on correct code.** The `graph.yaml` gate must not flag
`.kittify/doctrine/graph.yaml` (a live project-tier path) or the sites naming the dead path *in order
to forbid it*. The `shipped/` gate must not flag the prose "shipped/packaged" in
`model-to-task_type.yaml`.

The earlier fix-by-inspection missed 21 of 27 — which is why this is gated, not reviewed.

### Dependencies

**Depends on WP01, WP04.**

*(Corrected by the post-tasks squad.)* An earlier revision sequenced this WP **last** over a
three-file ownership collision. Two of the three were phantoms: `drg/merge.py:29` says "shipped" as
**prose**, and `doctrine-daphne.agent.yaml:129` names the dead path **in order to forbid it** — both
are exactly the cases T034/T037's discriminators must *not* flag, so they are fixture material, not
edits. Only `agent_profiles/profile.py` is real, and it is WP04's file, so **WP04 fixes that one
line (T023a)** and this WP depends on WP04.

---

## Work Package WP08: org→DRG bridge integrity (Priority: P0)

**Goal**: An unresolvable cross-layer edge fails loudly instead of vanishing.
**Independent Test**: Each of the three defect shapes produces a typed error or a conflict record.
**Prompt**: `/tasks/WP08-org-drg-bridge.md`
**Requirement Refs**: FR-010, FR-011, SC-009

### Included Subtasks

T041 Failing-first test: a built-in-source → pack-target edge currently returns `None` silently
T042 Emit a conflict record instead of `None`
T043 Stop blindly re-kinding a bare built-in target id to a node that may not exist
T044 Raise a typed pack error, not raw pydantic, on a URN-shaped target
T045 Fix the `CLAUDE.md` `specializes_from` snippet so it produces an edge (FR-011)

### Implementation Notes

ADR 2026-07-26-3 is explicit: the bridge fix **must land before or with** the `Relation.IMPACTS`
migration, or the new relation inherits a silent-drop path. Adding vocabulary to leaking
infrastructure is how a closed defect class regrows.

### Dependencies

**Depends on WP04.** Blocks WP09, and blocks mission B1.

---

## Work Package WP09: `applies` retype and relation gate (Priority: P2)

**Goal**: Daphne's operating procedure is reachable, and no future artefact authors a no-op `applies` edge.
**Independent Test**: `procedure:onboard-external-agent-to-pack` has a traversable inbound edge; a planted `applies` edge fails a gate.
**Prompt**: `/tasks/WP09-applies-retype.md`
**Requirement Refs**: FR-012, NFR-002, SC-010

### Included Subtasks

T046 Failing-first test: the procedure is currently unreachable
T047 Retype `agent_profile:doctrine-daphne --applies--> procedure:onboard-external-agent-to-pack`
T048 Gate: no newly-authored `applies` edge, built on measurement — with a **positive floor** (assert the gate scanned ≥ N fragment files) and a **planted-`applies` self-mutation**. After T047 the authored count is 0, so a gate globbing the wrong path passes forever
T049 Ledger the relation change against the golden counts (cardinality unchanged)

### Risks & Mitigations

**`applies` is not a dead sink.** The comment at `drg/merge.py:97-98` is **wrong** —
`charter_runtime/lint/checks/orphan.py` reads it and `charter/synthesizer/project_drg.py` produces it.
Build the gate on measurement, not on that comment. This is the one WP that changes a graph relation,
so it carries the single ledgered exception to NFR-004.

### Dependencies

**Depends on WP08.**

---

## Work Package WP10: CI collection completeness (Priority: P1)

**Goal**: Every test file is collected by at least one main-branch job, so a frozen-contract gate cannot go unrun on the branch it protects.
**Independent Test**: A meta-test diffs the union of job collections against the full collection and fails on a planted uncollected file.
**Prompt**: `/tasks/WP10-ci-collection-completeness.md`
**Requirement Refs**: FR-013, NFR-005, SC-013 · [#2957](https://github.com/Priivacy-ai/spec-kitty/issues/2957)

### Included Subtasks

T050 Failing-first test: the union of main-branch job collections currently omits `tests/specify_cli/cli/` and `tests/cli/`
T051 Root-cause the selection gap and record it — start from the `changes` paths-filter and the job `if:` conditions, not from the shard globs
T052 Implement the meta-test: union of per-job collections vs the **full** collection — evaluated with every `changes.outputs.*` **false** (the real main-push steady state) and sourced from a real `pytest --collect-only` subprocess, **not** declared globs. Computing the union with all jobs assumed to run reproduces the exact vacuity this WP exists to close
T053 Self-mutation test (NFR-005): plant an uncollected file, assert RED
T054 Close the gap so the union is complete
T055 Report whatever reds this newly surfaces as pre-existing — do **not** fix them here
T056 Wire `generate_schemas --check` into CI (WP05's SC-004 deliverable; this WP owns the workflow file)

### Implementation Notes

Verified in-tree 2026-07-26: `fast-tests-cli` and `integration-tests-cli` both gate on
`needs.changes.outputs.cli == 'true'`, and the `cli` filter covers only `src/specify_cli/cli/**`,
`tests/cli/**` and `tests/specify_cli/cli/**`. On any main push whose diff misses those paths,
**neither job runs**. The `fast-tests-core-misc` split compounds it: `specify-cli-rest` carries
`--ignore=tests/specify_cli/cli`, `specify-cli-rest-2` does not include it, and `core-misc` ignores
`tests/specify_cli` wholesale.

This is IC-01's defect class one layer up — an inert mechanism that looks like coverage — which is
why it belongs in this mission rather than a CI ticket.

### Dependencies

**Depends on WP01, WP05** — this WP owns `.github/workflows/ci-quality.yml`, so it wires the
schema `--check` step WP05 makes green.

### Risks & Mitigations

**The existing completeness check is scoped to the split, not the tree.** Its own comment says
"Verified disjoint + union-complete locally: 3241 + 3079 == 6320 (today's real `specify-cli-rest`
selection, unchanged)" — which verifies the bin-split preserved a selection that **already had the
hole**. Diff against the **full** collection or reproduce the same vacuity.

**T055 is a reporting subtask, not a fixing one.** The meta-test will surface currently-masked reds
(#2957 names four files). Those are honest pre-existing reds under ADR `2026-07-17-1`. Never satisfy
the gate by reclassifying a red as expected — that is the greenwashing the charter forbids.

---

## Dependency & Execution Summary

```
WP01 ─── first, guards everything
   ├── WP03 ──► WP04 ──┬─► WP08 ──► WP09
   │                   └─► WP07
   ├── WP05 ──┬─► WP10
   │          └─► WP06
   └── WP02
```

Every dependency is written in the form `spec-kitty tasks` parses (`Depends on WPxx`), so it reaches
`lanes.json` and the claim gate rather than living only in this diagram. The post-tasks squad found
the previous revision had all ten WPs at `dependencies: []` and every lane at `parallel_group: 0` —
the ordering existed only as prose. That is this mission's own defect class, in its own artefacts.

- **MVP scope**: WP01, WP03, WP04, WP08 — the four that unblock missions B1/B2/C. WP02/05/06/07/09/10 complete the mission but do not gate downstream work.
- **Parallelization**: after WP01, WP02/WP03/WP05/WP06 can run concurrently. WP07 is last by ownership, not by importance. WP03→WP04→WP08→WP09 is a strict chain.

## Requirements Coverage Summary

| Requirement | Covered By |
|---|---|
| FR-001 | WP01 |
| FR-002 | WP02 |
| FR-003 | WP03 |
| FR-004 | WP04 |
| FR-005 | WP05 |
| FR-006, FR-007 | WP06 |
| FR-008, FR-009 | WP07 |
| FR-010, FR-011 | WP08 |
| FR-012 | WP09 |
| FR-013 | WP10 |
| NFR-001 | WP01, WP06 |
| NFR-002 | WP09 |
| NFR-003 | WP07 |
| NFR-005 | WP10 |
| NFR-004 | WP03 (asserted), WP09 (single ledgered exception) |
| C-001 | WP01, WP02, WP04 |
| C-002 | WP03 (ordering constraint on the mission) |
| C-003, C-004 | all WPs (standing) |
| C-005 | WP02 |
| C-006 | all WPs (ATDD, standing) |
| SC-001…SC-012 | WP01…WP09 respectively, per the spec's Measurable Outcomes |
