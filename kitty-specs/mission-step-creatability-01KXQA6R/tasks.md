# Tasks: Mission-Type Creatability via Rich Step Model

**Mission**: mission-step-creatability-01KXQA6R | **Branch**: `feat/mission-step-creatability`
**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

7 work packages, 33 subtasks, sequenced **A→B→C** per the plan's IC map. Single-owner shared seams are binding (`step_projection.py`→WP01; `test_prompt_emptiness.py`→WP05; `extractor.py`→WP06). Agent profile: **python-pedro** (implementer). ATDD red-first through the pre-existing entry point.

## Dependency DAG

```
WP01 (cutover, no deps)
  ├─→ WP02 (documentation)   ┐
  ├─→ WP03 (research)        ├─→ WP05 (guards)
  └─→ WP04 (plan)            ┘   WP06 (graph-back)
WP07 (resolve-by-URN) ← WP01 + WP06
```
~2-3 lanes. **MVP / lane-a start: WP01.**

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Remove `MissionType.template_set` field | WP01 | |
| T002 | Drop the `template_set` overlay (keep `action_sequence`) | WP01 | |
| T003 | `step_projection.py`: sequence_index ordering + `iter_template_refs` helper | WP01 | |
| T004 | Shared `resolve_all_for_mission_type` cache + re-point the slot | WP01 | |
| T005 | Migrate CLI reads + add CLI test | WP01 | |
| T006 | Test migration (retire-only-template_set-method + field-pin reads) | WP01 | |
| T007 | Concern-A proofs (parity, loud-fail, one-walk) | WP01 | |
| T008 | documentation template refs (`spec`/`plan`) + per-type template_file | WP02 | [P] |
| T009 | Author documentation discover/audit/design prompts | WP02 | [P] |
| T010 | Author documentation generate/validate prompts | WP02 | [P] |
| T011 | Author documentation publish/accept prompts | WP02 | [P] |
| T012 | documentation template files (rename/replace to doc vocabulary) | WP02 | [P] |
| T013 | Verify documentation creatable (red-first) | WP02 | [P] |
| T014 | research template refs (`spec`/`plan`) + per-type template_file | WP03 | [P] |
| T015 | Author research scoping/methodology prompts | WP03 | [P] |
| T016 | Author research gathering/synthesis/output prompts | WP03 | [P] |
| T017 | research template files (rename/replace to research vocabulary) | WP03 | [P] |
| T018 | Verify research creatable (red-first) | WP03 | [P] |
| T019 | plan template refs (`spec`/`plan`) + per-type template_file | WP04 | [P] |
| T020 | Author-fresh plan scaffold template files (plan-domain, no code) | WP04 | [P] |
| T021 | Author plan specify/research prompts (author-fresh) | WP04 | [P] |
| T022 | Author plan plan/review prompts (author-fresh) | WP04 | [P] |
| T023 | Verify plan creatable + `/plan`-setup `plan` key resolves | WP04 | [P] |
| T024 | Shrink `_SEEDED_BLANK_STEPS`/xfails/golden-16 as content lands | WP05 | |
| T025 | Retire scaffold → positive non-empty assertion + substance hook | WP05 | |
| T026 | Cross-type `template_file` uniqueness guard (NFR-006) | WP05 | |
| T027 | New extractor pass (nodes + `instantiates` edges) via `iter_template_refs` | WP06 | |
| T028 | Regenerate graph; compute N; bump `_EXPECTED_NODE/EDGE_COUNT` | WP06 | |
| T029 | Positive instantiates assertion + arch-marker sweep | WP06 | |
| T030 | Verify 16 bare exemplars untouched; freshness green | WP06 | |
| T031 | Add resolve-by-URN function (signature stable) | WP07 | |
| T032 | by-URN==by-name + override-wins equivalence test | WP07 | |
| T033 | C-002 arch assertion (no scalar reference) | WP07 | |

---

## WP01 — Atomic `template_set` cutover (Concern A)

**Goal**: Retire the persisted `MissionType.template_set` field and source the projection from the step authority — behavior-preserving, a single atomic change (C-009). **Priority: P1a (lands first).**
**Independent test**: software-dev template resolution byte-identical; repo still constructs; a YAML-authored `template_set:` fails loud; one `mission-steps/` walk per `(type, pack_context)`.
**Prompt**: [tasks/WP01-atomic-template-set-cutover.md](./tasks/WP01-atomic-template-set-cutover.md) (~7 subtasks)
**Dependencies**: none.

- [x] T001 Remove `MissionType.template_set` field (models.py) (WP01)
- [x] T002 Drop the `template_set` overlay in `_inject_projected_fields` (:200-202); keep `action_sequence` (:199) (WP01)
- [x] T003 `step_projection.py` (sole owner): order steps by `sequence_index` + expose `iter_template_refs` (WP01)
- [x] T004 Shared `resolve_all_for_mission_type` cache + re-point `_resolve_template_set_slot` (WP01)
- [x] T005 Migrate CLI reads (:1491/:1509-1511) + add CLI test (WP01)
- [x] T006 Test migration: retire-only-template_set-method + field-pin reads incl. `:47` (WP01)
- [x] T007 Proofs: parity, pack-fails-loud, one-walk shared-cache (WP01)

## WP02 — Documentation content authoring (Concern B)

**Goal**: Make `documentation` creatable by authoring 7 step prompts + template refs on its own step names. **Priority: P1b.**
**Independent test**: `mission create --mission-type documentation` succeeds; all 7 prompts non-empty + substantive.
**Prompt**: [tasks/WP02-documentation-authoring.md](./tasks/WP02-documentation-authoring.md) (~6 subtasks)
**Dependencies**: WP01.

- [x] T008 documentation template refs (`artifact_key: spec` + `plan`) + per-type `template_file` (WP02)
- [x] T009 Author discover/audit/design prompts (promote from guidelines.md) (WP02)
- [x] T010 Author generate/validate prompts (WP02)
- [x] T011 Author publish/accept prompts (WP02)
- [x] T012 documentation template files → documentation vocabulary (WP02)
- [x] T013 Verify documentation creatable (red-first through creation path) (WP02)

## WP03 — Research content authoring (Concern B)

**Goal**: Make `research` creatable — 5 step prompts + template refs on its own step names. **Priority: P1b.**
**Independent test**: `mission create --mission-type research` succeeds; 5 prompts non-empty + substantive.
**Prompt**: [tasks/WP03-research-authoring.md](./tasks/WP03-research-authoring.md) (~5 subtasks)
**Dependencies**: WP01.

- [x] T014 research template refs (`spec`/`plan`) + per-type `template_file` (WP03)
- [x] T015 Author scoping/methodology prompts (promote) (WP03)
- [x] T016 Author gathering/synthesis/output prompts (WP03)
- [x] T017 research template files → research vocabulary (WP03)
- [x] T018 Verify research creatable (red-first) (WP03)

## WP04 — Plan content authoring (Concern B — HEAVIEST, author-fresh)

**Goal**: Make `plan` creatable — 4 step prompts **and** author-fresh scaffold template files (no guidelines source, empty `templates/`). **Priority: P1b.**
**Independent test**: `mission create --mission-type plan` succeeds AND `/plan`-setup resolves the `plan` key; plan-domain content (no software-dev clone).
**Prompt**: [tasks/WP04-plan-authoring.md](./tasks/WP04-plan-authoring.md) (~5 subtasks)
**Dependencies**: WP01.

- [x] T019 plan template refs (`spec`/`plan`) + per-type `template_file` (WP04)
- [x] T020 Author-fresh plan scaffold template files (plan-domain, no code) (WP04)
- [x] T021 Author specify/research prompts (author-fresh) (WP04)
- [x] T022 Author plan/review prompts (author-fresh) (WP04)
- [x] T023 Verify plan creatable + `/plan`-setup `plan` key resolves (WP04)

## WP05 — Guards: emptiness retirement + cross-type uniqueness (Concern B)

**Goal**: Keep the emptiness guard truthful, retire the scaffold, and assert cross-type `template_file` uniqueness. **Priority: P2.** Single owner of `test_prompt_emptiness.py` (C-011).
**Independent test**: emptiness census empty; positive non-empty assertion green; no two types share a `template_file`.
**Prompt**: [tasks/WP05-guards-emptiness-uniqueness.md](./tasks/WP05-guards-emptiness-uniqueness.md) (~3 subtasks)
**Dependencies**: WP02, WP03, WP04.

- [x] T024 Shrink `_SEEDED_BLANK_STEPS`/xfails/golden-16/`_SEQUENCE_STEPS_BY_TYPE` (WP05)
- [x] T025 Retire scaffold → positive non-empty assertion + reviewer-checklist substance hook (WP05)
- [x] T026 Cross-type `template_file` uniqueness guard test (NFR-006) (WP05)

## WP06 — Graph-back extractor pass + DRG re-baseline (Concern C)

**Goal**: Emit the `mission_type → step → template` chain into the shipped graph. **Priority: P2.** Single owner of `extractor.py` (C-012).
**Independent test**: shipped graph has the `instantiates` edges; DRG `280+N`/`757+N`, orphans=10; freshness green.
**Prompt**: [tasks/WP06-graph-back-extractor.md](./tasks/WP06-graph-back-extractor.md) (~4 subtasks)
**Dependencies**: WP01, WP02, WP03, WP04 (WP01 explicit — WP06 consumes its `iter_template_refs` helper; transitively covered but pinned for robustness).

- [x] T027 New extractor pass (nodes + `instantiates` edges) consuming `iter_template_refs` (WP06)
- [x] T028 Regenerate graph; compute N; bump `_EXPECTED_NODE/EDGE_COUNT` to `280+N`/`757+N` (WP06)
- [x] T029 Positive instantiates assertion + arch-marker sweep (WP06)
- [x] T030 Verify 16 bare exemplars untouched; freshness green (WP06)

## WP07 — Resolve-by-URN lane (Concern C)

**Goal**: Add URN-addressed resolution as a second lane alongside resolve-by-name. **Priority: P2.**
**Independent test**: by-URN == by-name for an authored template; override wins on the URN lane.
**Prompt**: [tasks/WP07-resolve-by-urn.md](./tasks/WP07-resolve-by-urn.md) (~3 subtasks)
**Dependencies**: WP01, WP06.

- [ ] T031 Add resolve-by-URN function (signature stable) (WP07)
- [ ] T032 by-URN==by-name + override-wins equivalence test (WP07)
- [ ] T033 C-002 arch assertion (no scalar `template_set` reference) (WP07)
