# Tasks: DRG completeness (#2843) — relation-description parity + activation-gate consolidation

**Mission**: `drg-relation-parity-activation-gate-01KY48PD` | **Branch**: `doctrine/drg-completeness-2843` (coord topology)
**Spec**: `spec.md` | **Plan**: `plan.md` | **Research**: `research.md` | **Contracts**: `contracts/`

Two parallel lanes: **Item B** (activation-gate live-bug fix — WP01→WP02/WP03) and **Item A**
(relation-description parity — WP04→WP05). Item A ∥ Item B (disjoint files). Red-first (NFR-001)
precedes the WP01 fix.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red-first characterization test: stem-form RED + canonical-id GREEN control (real corpus + repo config) | WP01 | [P] |
| T002 | Add `drg.py`-local singular→`ArtifactKind` constant | WP01 | |
| T003 | `filter_graph_by_activation`: build resolved canonical-URN map once (lift `_build_tension_active_urns`); `resolve_doctrine_root()` + `pack_roots[1:]`; skip-with-report on `UnknownArtifactIdError` | WP01 | |
| T004 | `_node_is_activated`: consume pre-resolved map, membership on full URN vs `node.urn` | WP01 | |
| T005 | Root-source pinning test (gate root == compiler-projection root); green characterization; ruff/mypy | WP01 | |
| T006 | Delete tension-scan trio; re-point tension consistency to consume the gate; verdicts unchanged | WP02 | |
| T007 | Re-point `_check_graph_kind_parity` KIND→per-ID (behavior upgrade) + own tests | WP02 | |
| T008 | Delete orphaned `_DRG_SINGULAR_TO_ACTIVATED_KINDS_MEMBER`; update dead-symbol/dead-module/arch baselines | WP02 | |
| T009 | `executor.py:182` before/after test (named observable) | WP03 | [P] |
| T010 | `reference_resolver.py:67` before/after test | WP03 | [P] |
| T011 | `compiler.py:1037` closure before/after test | WP03 | [P] |
| T012 | `_check_drg_cross_kind_refs:424` before/after test | WP03 | [P] |
| T013 | `context.py:928` before/after test | WP03 | [P] |
| T014 | Full `tests/charter/` + `tests/doctrine/` suite green — 0 net failures vs merge-base | WP03 | |
| T015 | Backfill `RELATION_DESCRIPTIONS` for the 12 members (`applies`≠`scope` adjudication; dormant vs overlay emission status) | WP04 | [P] |
| T016 | Convert `test_models.py` `=={3}` → `==set(Relation)` + non-empty over all | WP04 | |
| T017 | Extend `docs/context/doctrine.md` glossary prose (non-enforced paraphrase) | WP04 | |
| T018 | ruff/mypy/terminology/markdownlint on Item-A code + prose | WP04 | |
| T019 | Restructure `doctrine-relationships.md` → 15 per-relation `###` sections (7 new, split grouped `enhances/overrides/replaces`, trim Lineage/Delegation prose) | WP05 | |
| T020 | Widen `_SCOPED_RELATIONS` 3→15 | WP05 | |
| T021 | Update stale "other twelve out of scope / follow-up" docstrings (`test_relation_doc_parity.py` + doc "Tension vocabulary" prose) | WP05 | |
| T022 | Green `test_relation_doc_parity.py` (all 15 scoped) + terminology guard | WP05 | |

---

## Work Packages

### WP01 — Activation-gate canonical-URN correctness (IC-01) · Item B · Priority P1

- **Goal**: Route the per-ID activation gate through the existing `resolve_artifact_urn` so a populated `activated_directives` (config stems) no longer silently drops canonical directive nodes. Red-first.
- **Independent test**: `uv run pytest tests/charter/test_drg_activation_gate.py -q` — stem-form RED on merge-base, GREEN after; canonical-id control GREEN on merge-base.
- **Dependencies**: none (Item B root). **Prompt**: `tasks/WP01-activation-gate-canonical-urn.md`
- **Subtasks**: T001, T002, T003, T004, T005
- [ ] T001 Red-first characterization test: stem-form RED + canonical-id GREEN control (real corpus + repo config) (WP01)
- [ ] T002 Add `drg.py`-local singular→`ArtifactKind` constant (WP01)
- [ ] T003 `filter_graph_by_activation`: build resolved canonical-URN map once; `resolve_doctrine_root()` + `pack_roots[1:]`; skip-with-report on `UnknownArtifactIdError` (WP01)
- [ ] T004 `_node_is_activated`: consume pre-resolved map, membership on full URN vs `node.urn` (WP01)
- [ ] T005 Root-source pinning test; green characterization; ruff/mypy (WP01)

### WP02 — Workaround collapse (IC-02) · Item B · Priority P1

- **Goal**: Delete the tension-scan reimplementation so it consumes the one gate; re-point `_check_graph_kind_parity` KIND→per-ID (intended behavior upgrade); delete the orphaned constant.
- **Independent test**: tension-consistency verdicts unchanged; `_check_graph_kind_parity` per-ID tests green; dead-symbol/module + arch baselines green.
- **Dependencies**: WP01. **Prompt**: `tasks/WP02-workaround-collapse.md`
- **Subtasks**: T006, T007, T008
- [ ] T006 Delete tension-scan trio; re-point tension consistency to consume the gate; verdicts unchanged (WP02)
- [ ] T007 Re-point `_check_graph_kind_parity` KIND→per-ID (behavior upgrade) + own tests (WP02)
- [ ] T008 Delete orphaned `_DRG_SINGULAR_TO_ACTIVATED_KINDS_MEMBER`; update dead-symbol/dead-module/arch baselines (WP02)

### WP03 — Five-consumer regression net (IC-03) · Item B · Priority P1

- **Goal**: Prove the corrected gate does not regress any of the five `filter_graph_by_activation` consumers, each with a named observable — `None`-path byte-identical, populated-path corrected.
- **Independent test**: `uv run pytest tests/charter/ tests/doctrine/ -q` — 0 net failures vs merge-base.
- **Dependencies**: WP01 (soft: WP02 for the `_check_graph_kind_parity` interaction — see risks). **Prompt**: `tasks/WP03-consumer-regression-net.md`
- **Subtasks**: T009, T010, T011, T012, T013, T014
- [ ] T009 `executor.py:182` before/after test (named observable) (WP03)
- [ ] T010 `reference_resolver.py:67` before/after test (WP03)
- [ ] T011 `compiler.py:1037` closure before/after test (WP03)
- [ ] T012 `_check_drg_cross_kind_refs:424` before/after test (WP03)
- [ ] T013 `context.py:928` before/after test (WP03)
- [ ] T014 Full `tests/charter/` + `tests/doctrine/` suite green — 0 net failures vs merge-base (WP03)

### WP04 — Relation registry + completeness gate + glossary prose (IC-04 + IC-05b) · Item A · Priority P2

- **Goal**: Complete `RELATION_DESCRIPTIONS`, convert the code-side completeness gate, and extend the non-enforced glossary.
- **Independent test**: `uv run pytest tests/doctrine/drg/test_models.py -q` — `==set(Relation)` + non-empty.
- **Dependencies**: none (Item A root). **Prompt**: `tasks/WP04-relation-registry-and-prose.md`
- **Subtasks**: T015, T016, T017, T018
- [ ] T015 Backfill `RELATION_DESCRIPTIONS` for the 12 members (`applies`≠`scope` adjudication; dormant vs overlay emission status) (WP04)
- [ ] T016 Convert `test_models.py` `=={3}` → `==set(Relation)` + non-empty over all (WP04)
- [ ] T017 Extend `docs/context/doctrine.md` glossary prose (non-enforced) (WP04)
- [ ] T018 ruff/mypy/terminology/markdownlint on Item-A code + prose (WP04)

### WP05 — Doc parity surface restructure (IC-05a) · Item A · Priority P2

- **Goal**: Bring the single parity-enforced surface (`doctrine-relationships.md`) into lockstep and widen the parity test to all 15 relations.
- **Independent test**: `uv run pytest tests/doctrine/test_relation_doc_parity.py -q` — green with `_SCOPED_RELATIONS` = 15.
- **Dependencies**: WP04 (descriptions must exist first). **Prompt**: `tasks/WP05-doc-parity-restructure.md`
- **Subtasks**: T019, T020, T021, T022
- [ ] T019 Restructure `doctrine-relationships.md` → 15 per-relation sections (7 new, split grouped heading, trim prose) (WP05)
- [ ] T020 Widen `_SCOPED_RELATIONS` 3→15 (WP05)
- [ ] T021 Update stale non-goal docstrings (`test_relation_doc_parity.py` + doc "Tension vocabulary" prose) (WP05)
- [ ] T022 Green `test_relation_doc_parity.py` (all 15 scoped) + terminology guard (WP05)

---

## Dependencies & Lanes

```
Item B:  WP01 ──┬── WP02
                └── WP03
Item A:  WP04 ───── WP05
```

- **Item A ∥ Item B** — disjoint files (Item A: `doctrine/drg/models.py` + `docs/` + `tests/doctrine/*`; Item B: `charter/*` + `tests/charter/*`), no overlap.
- **MVP**: WP01 (closes the live correctness bug) is the highest-value slice; WP04 is the smallest independently-shippable Item-A slice.
- Coord topology; `finalize-tasks` computes `lanes.json` from these dependencies.

## Requirement coverage

- Item B: FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, C-001, C-002, C-003, C-004 → WP01/WP02/WP03
- Item A: FR-005, FR-006, FR-007, FR-008, NFR-003, C-006 → WP04/WP05
- NFR-004 (quality gates) → every WP.
